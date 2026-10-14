"""Assinaturas da marca em SVG (símbolo, produto, marca-mãe) nas quatro variantes, uma pasta por família de nome.

Uso: uv run python -m scripts.marca.composicoes
"""

import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTFont

from scripts.comum.ambiente import RAIZ

from .familias import FAMILIAS, Familia, Linha
from .fontes import garantir
from .letreiro import contorno, fonte
from .paleta import DESTINO as PALETA_JSON
from .paleta import Paleta
from .simbolo import LARGURA, Parametros, svg_simbolo

DESTINO = RAIZ / "marca" / "svg"
VARIANTES = ("positivo", "negativo", "mono-escuro", "mono-claro")
_MARGEM = 24.0
# O vão entre a fita e o pilar define o tamanho mínimo: abaixo disso ele some.
VAO_MIN_PX = 0.5
VAO_MIN_MM = 0.1


@dataclass(frozen=True)
class Tipos:
    serifada: TTFont
    sans_leve: TTFont
    sans: TTFont

    @classmethod
    def padrao(cls) -> "Tipos":
        cinzel, jost = str(garantir("Cinzel[wght].ttf")), str(garantir("Jost[wght].ttf"))
        return cls(fonte(cinzel, 400), fonte(jost, 300), fonte(jost, 400))


@dataclass(frozen=True)
class Peca:
    svg: str
    largura: float
    altura: float
    escala: float = 0.0  # escala do símbolo dentro da peça (0 = sem símbolo)


def cores_da_variante(p: Paleta, v: str) -> tuple[str, str]:
    return {
        "positivo": (p.ouro, p.bronze),
        "negativo": (p.ouro_claro, p.ouro_claro),
        "mono-escuro": (p.preto, p.preto),
        "mono-claro": ("#FFFFFF", "#FFFFFF"),
    }[v]


def _texto(tt: TTFont, s: str, largura_alvo: float, espacamento: float, cor: str) -> Peca:
    medida = contorno(tt, s, 100, espacamento)
    l = contorno(tt, s, 100 * largura_alvo / medida.largura, espacamento)
    return Peca(f'<path transform="translate(0 {l.topo:.2f})" fill="{cor}" d="{l.d}"/>', l.largura, l.topo)


def _filete(largura: float, cor: str) -> Peca:
    lo, meio = 7.0, largura / 2
    return Peca(
        f'<g fill="{cor}"><rect x="0" y="{lo - 0.75:g}" width="{meio - 2 * lo:g}" height="1.5"/>'
        f'<path d="M{meio - lo:g} {lo:g} L{meio:g} 0 L{meio + lo:g} {lo:g} L{meio:g} {2 * lo:g} Z"/>'
        f'<rect x="{meio + 2 * lo:g}" y="{lo - 0.75:g}" width="{meio - 2 * lo:g}" height="1.5"/></g>',
        largura, 2 * lo,
    )


def _simbolo(altura: float, cor: str) -> Peca:
    p = Parametros()
    k = altura / p.pilar_topo
    return Peca(f'<g transform="scale({k:.5f})">{svg_simbolo(p, cor)}</g>', LARGURA * k, altura, k)


def _pilha(pecas: list[Peca], vaos: list[float]) -> Peca:
    largura = max(pc.largura for pc in pecas)
    y, partes = 0.0, []
    for i, pc in enumerate(pecas):
        partes.append(f'<g transform="translate({(largura - pc.largura) / 2:.2f} {y:.2f})">{pc.svg}</g>')
        y += pc.altura + (vaos[i] if i < len(vaos) else 0)
    return Peca("".join(partes), largura, y, max(pc.escala for pc in pecas))


def _pilha_esquerda(pecas: list[Peca], vaos: list[float]) -> Peca:
    largura = max(pc.largura for pc in pecas)
    y, partes = 0.0, []
    for i, pc in enumerate(pecas):
        partes.append(f'<g transform="translate(0 {y:.2f})">{pc.svg}</g>')
        y += pc.altura + (vaos[i] if i < len(vaos) else 0)
    return Peca("".join(partes), largura, y, max(pc.escala for pc in pecas))


def _lado_a_lado(a: Peca, b: Peca, vao: float) -> Peca:
    altura = max(a.altura, b.altura)
    return Peca(
        f'<g transform="translate(0 {(altura - a.altura) / 2:.2f})">{a.svg}</g>'
        f'<g transform="translate({a.largura + vao:.2f} {(altura - b.altura) / 2:.2f})">{b.svg}</g>',
        a.largura + vao + b.largura, altura, max(a.escala, b.escala),
    )


def _documento(pc: Peca) -> str:
    w, h = pc.largura + 2 * _MARGEM, pc.altura + 2 * _MARGEM
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.2f} {h:.2f}" width="{w:.0f}" height="{h:.0f}">'
        f'<g transform="translate({_MARGEM:g} {_MARGEM:g})">{pc.svg}</g></svg>\n'
    )


def simbolo(t: Tipos, f: Familia, cs: str, ct: str) -> Peca:
    return _simbolo(384.0, cs)


def _sub_linha(t: Tipos, linha: Linha, ct: str) -> Peca:
    texto, peso, largura, espacamento = linha
    return _texto(t.sans_leve if peso == "leve" else t.sans, texto, largura, espacamento, ct)


def produto_vertical(t: Tipos, f: Familia, cs: str, ct: str) -> Peca:
    pecas, vaos = [_simbolo(384.0, cs)], [70.0]
    if f.sobre_nome:
        pecas.append(_texto(t.sans_leve, f.sobre_nome, 480, 0.5, ct))
        vaos.append(26.0)
    pecas += [_texto(t.serifada, f.nome, 1100, 0.18, ct), _filete(520, ct)]
    vaos += [34.0, 34.0]
    for i, linha in enumerate(f.produto):
        pecas.append(_sub_linha(t, linha, ct))
        if i < len(f.produto) - 1:
            vaos.append(26.0)
    return _pilha(pecas, vaos)


def produto_horizontal(t: Tipos, f: Familia, cs: str, ct: str) -> Peca:
    pecas, vaos = [], []
    if f.sobre_nome:
        pecas.append(_texto(t.sans_leve, f.sobre_nome, 380, 0.5, ct))
        vaos.append(22.0)
    pecas += [
        _texto(t.serifada, f.nome, 900, 0.18, ct),
        _filete(900, ct),
        _texto(t.sans_leve, f.produto_linha, 900, 0.35, ct),
    ]
    vaos += [26.0, 26.0]
    texto = _pilha_esquerda(pecas, vaos)
    return _lado_a_lado(_simbolo(texto.altura * 1.1, cs), texto, 60)


def assinatura_mae(t: Tipos, f: Familia, cs: str, ct: str) -> Peca:
    texto = _pilha_esquerda(
        [_texto(t.serifada, f.nome, 900, 0.18, ct), _texto(t.sans_leve, f.mae or "", 900, 0.3, ct)],
        [30],
    )
    return _lado_a_lado(_simbolo(texto.altura * 1.1, cs), texto, 60)


COMPOSICOES: dict[str, Callable[[Tipos, Familia, str, str], Peca]] = {
    "simbolo": simbolo,
    "produto-vertical": produto_vertical,
    "produto-horizontal": produto_horizontal,
    "assinatura-mae": assinatura_mae,
}


def composicoes_da(f: Familia) -> dict[str, Callable[[Tipos, Familia, str, str], Peca]]:
    """Composições que a família tem: sem marca-mãe, sem assinatura da marca-mãe."""
    return {n: c for n, c in COMPOSICOES.items() if n != "assinatura-mae" or f.mae}


def minimos(t: Tipos, f: Familia) -> dict[str, tuple[int, int]]:
    """Largura mínima (px, mm) de cada composição para o vão entre fita e pilar continuar visível."""
    vao = Parametros().vao
    saida = {}
    for nome, compor in composicoes_da(f).items():
        pc = compor(t, f, "#000000", "#000000")
        largura, vao_unidades = pc.largura + 2 * _MARGEM, vao * pc.escala
        px = math.ceil(VAO_MIN_PX * largura / vao_unidades / 5) * 5
        saida[nome] = (px, math.ceil(VAO_MIN_MM * largura / vao_unidades))
    return saida


def fracao_protecao(t: Tipos, f: Familia) -> float:
    """x da área de proteção (largura do pilar) como fração da largura do produto horizontal."""
    pc = produto_horizontal(t, f, "#000000", "#000000")
    x0, x1 = Parametros().pilar_x
    return (x1 - x0) * pc.escala / (pc.largura + 2 * _MARGEM)


def _id_proprio(svg: str, sufixo: str) -> str:
    return svg.replace('id="vao"', f'id="vao-{sufixo}"').replace("url(#vao)", f"url(#vao-{sufixo})")


def _favicon(p: Paleta) -> str:
    s = _simbolo(384.0, p.ouro_claro)
    lado = s.largura * 1.2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lado:.2f} {lado:.2f}">'
        f'<rect width="{lado:.2f}" height="{lado:.2f}" rx="{lado * 0.18:.2f}" fill="{p.preto}"/>'
        f'<g transform="translate({(lado - s.largura) / 2:.2f} {(lado - s.altura) / 2:.2f})">{s.svg}</g></svg>\n'
    )


def gerar(p: Paleta, tipos: Tipos, destino: Path, f: Familia) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for nome, compor in composicoes_da(f).items():
        for v in VARIANTES:
            arq = destino / f"{nome}-{v}.svg"
            svg = _documento(compor(tipos, f, *cores_da_variante(p, v)))
            arq.write_text(_id_proprio(svg, f"{nome}-{v}"), encoding="utf-8")
            arquivos.append(arq)
    fav = destino / "favicon.svg"
    fav.write_text(_id_proprio(_favicon(p), "favicon"), encoding="utf-8")
    return [*arquivos, fav]


def main() -> int:
    p, tipos = Paleta.carregar(PALETA_JSON), Tipos.padrao()
    for f in FAMILIAS.values():
        for a in gerar(p, tipos, DESTINO / f.chave, f):
            print(a.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
