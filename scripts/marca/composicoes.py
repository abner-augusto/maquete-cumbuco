"""Assinaturas da marca em SVG (símbolo, produto, marca-mãe) nas quatro variantes. Uso: uv run python -m scripts.marca.composicoes"""

import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTFont

from scripts.comum.ambiente import RAIZ

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
    return Peca(f'<path transform="translate(0 {l.altura_maiuscula:.2f})" fill="{cor}" d="{l.d}"/>', l.largura, l.altura_maiuscula)


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


def simbolo(t: Tipos, cs: str, ct: str) -> Peca:
    return _simbolo(384.0, cs)


def produto_vertical(t: Tipos, cs: str, ct: str) -> Peca:
    return _pilha(
        [
            _simbolo(384.0, cs),
            _texto(t.serifada, "ALTERNATIVA", 1100, 0.18, ct),
            _filete(520, ct),
            _texto(t.sans_leve, "RESIDENCIAL", 560, 0.5, ct),
            _texto(t.sans, "CUMBUCO", 480, 0.55, ct),
        ],
        [70, 34, 34, 26],
    )


def produto_horizontal(t: Tipos, cs: str, ct: str) -> Peca:
    texto = _pilha_esquerda(
        [
            _texto(t.serifada, "ALTERNATIVA", 900, 0.18, ct),
            _filete(900, ct),
            _texto(t.sans_leve, "RESIDENCIAL · CUMBUCO", 900, 0.35, ct),
        ],
        [26, 26],
    )
    return _lado_a_lado(_simbolo(texto.altura * 1.1, cs), texto, 60)


def assinatura_mae(t: Tipos, cs: str, ct: str) -> Peca:
    texto = _pilha_esquerda(
        [_texto(t.serifada, "ALTERNATIVA", 900, 0.18, ct), _texto(t.sans_leve, "DESENVOLVIMENTO URBANO", 900, 0.3, ct)],
        [30],
    )
    return _lado_a_lado(_simbolo(texto.altura * 1.1, cs), texto, 60)


COMPOSICOES: dict[str, Callable[[Tipos, str, str], Peca]] = {
    "simbolo": simbolo,
    "produto-vertical": produto_vertical,
    "produto-horizontal": produto_horizontal,
    "assinatura-mae": assinatura_mae,
}


def minimos(t: Tipos) -> dict[str, tuple[int, int]]:
    """Largura mínima (px, mm) de cada composição para o vão entre fita e pilar continuar visível."""
    vao = Parametros().vao
    saida = {}
    for nome, compor in COMPOSICOES.items():
        pc = compor(t, "#000000", "#000000")
        largura, vao_unidades = pc.largura + 2 * _MARGEM, vao * pc.escala
        px = math.ceil(VAO_MIN_PX * largura / vao_unidades / 5) * 5
        saida[nome] = (px, math.ceil(VAO_MIN_MM * largura / vao_unidades))
    return saida


def fracao_protecao(t: Tipos) -> float:
    """x da área de proteção (largura do pilar) como fração da largura do produto horizontal."""
    pc = produto_horizontal(t, "#000000", "#000000")
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


def gerar(p: Paleta, tipos: Tipos, destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for nome, compor in COMPOSICOES.items():
        for v in VARIANTES:
            arq = destino / f"{nome}-{v}.svg"
            svg = _documento(compor(tipos, *cores_da_variante(p, v)))
            arq.write_text(_id_proprio(svg, f"{nome}-{v}"), encoding="utf-8")
            arquivos.append(arq)
    fav = destino / "favicon.svg"
    fav.write_text(_id_proprio(_favicon(p), "favicon"), encoding="utf-8")
    return [*arquivos, fav]


def main() -> int:
    for a in gerar(Paleta.carregar(PALETA_JSON), Tipos.padrao(), DESTINO):
        print(a.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
