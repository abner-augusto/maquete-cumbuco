"""Brandbook preliminar em HTML autocontido e PDF. Uso: uv run python -m scripts.marca.brandbook"""

import base64
import re
import sys
from html import escape
from pathlib import Path

from scripts.comum.ambiente import RAIZ

from .composicoes import VARIANTES, Tipos, composicoes_da, fracao_protecao, minimos
from .familias import ATIVA, FAMILIAS, Familia
from .composicoes import DESTINO as SVG_DIR
from .fontes import garantir
from .paleta import DESTINO as PALETA_JSON
from .paleta import Paleta
from .tokens import CHAVES, tema

DESTINO = RAIZ / "marca" / "brandbook"

# Iguais ao base.css do espelho (o Plano 5 usa o mesmo arquivo). Fixas: não mudam com a marca.
STATUS = {
    "Disponível": "#2E9E5B",
    "Reservado": "#E2B021",
    "Vendido": "#B0625A",
    "Bloqueado": "#8B8F93",
    "Sem informação": "#94A3B8",
}
EQUIVALENTES = {"Cinzel": "Trajan Pro 3 (Adobe)", "Jost": "Futura PT (ParaType)"}

_FUNDO = {"positivo": "creme", "negativo": "preto", "mono-escuro": "creme", "mono-claro": "bronze"}


class _Usos:
    """Entrega cada SVG com ids renomeados a cada uso: a mesma assinatura aparece em várias seções."""

    def __init__(self, svgs: dict[str, str]):
        self._svgs, self._n = svgs, 0

    def __getitem__(self, nome: str) -> str:
        self._n += 1
        pre = f"u{self._n}-"
        return re.sub(r'id="([^"]+)"', rf'id="{pre}\1"', self._svgs[nome]).replace("url(#", f"url(#{pre}")


def _secao(titulo: str, corpo: str) -> str:
    return f"<section><h2>{escape(titulo)}</h2>{corpo}</section>"


def html(
    p: Paleta, t: dict, svgs: dict[str, str], fontes_b64: dict[str, str],
    minimo: dict[str, tuple[int, int]], x_protecao: float, f: Familia,
) -> str:
    svgs = _Usos(svgs)
    fundo = {"creme": p.creme, "preto": p.preto, "bronze": p.bronze}
    faces = "\n".join(
        f'@font-face {{ font-family:"{n}"; src:url(data:font/ttf;base64,{b}) format("truetype"); font-weight:100 900; }}'
        for n, b in fontes_b64.items()
    )
    if f.mae:
        arquitetura = (
            f"<p>O produto <b>{escape(f.titulo)}</b> vem em destaque; a marca-mãe <b>{escape(f.titulo_mae or '')}</b> "
            "assina de forma discreta (rodapé, carimbo). As duas usam o mesmo símbolo de arco e pilar.</p>"
            f'<div class="par"><div class="caixa" style="background:{p.creme}">{svgs["produto-vertical-positivo"]}</div>'
            f'<div class="caixa" style="background:{p.creme}">{svgs["assinatura-mae-positivo"]}</div></div>'
        )
    else:
        arquitetura = (
            f"<p>A marca é o produto <b>{escape(f.titulo)}</b>, com o símbolo de arco e pilar. "
            "Nesta fase não há assinatura de marca-mãe.</p>"
            f'<div class="caixa" style="background:{p.creme}">{svgs["produto-vertical-positivo"]}</div>'
        )
    versoes = '<div class="grade">' + "".join(
        f'<figure><div class="caixa" style="background:{fundo[_FUNDO[v]]}">{svgs[f"{c}-{v}"]}</div>'
        f"<figcaption>{c} · {v}</figcaption></figure>"
        for c in composicoes_da(f) for v in VARIANTES
    ) + "</div>"
    protecao = (
        "<p>Em volta da assinatura, deixe livre no mínimo <b>x</b>, a largura do pilar do símbolo. "
        "Nenhum texto, borda ou imagem entra nessa área. A linha tracejada marca esse limite em escala.</p>"
        f'<div class="protecao" style="background:{p.creme}"><div class="area" style="padding:{100 * x_protecao / (1 + 2 * x_protecao):.2f}%">'
        f'{svgs["produto-horizontal-positivo"]}</div></div>'
    )
    rotulos = {
        "simbolo": "Símbolo", "produto-vertical": "Produto vertical",
        "produto-horizontal": "Produto horizontal", "assinatura-mae": "Assinatura da marca-mãe",
    }
    tabela_minimo = (
        "<p>Largura mínima para o vão entre a fita e o pilar continuar visível (meio pixel na tela, "
        "0,1 mm no impresso). Abaixo disso, use o símbolo sozinho em tamanho maior ou o nome sem símbolo.</p>"
        "<table><tr><th>Versão (largura)</th><th>Tela</th><th>Impresso</th></tr>"
        + "".join(f"<tr><td>{rotulos[n]}</td><td>{px} px</td><td>{mm} mm</td></tr>" for n, (px, mm) in minimo.items())
        + "</table>"
    )
    erros = [
        ("Distorcer", "transform:scaleX(1.5)"),
        ("Recolorir", "filter:hue-rotate(160deg) saturate(3)"),
        ("Aplicar efeitos", "filter:drop-shadow(6px 6px 4px #000)"),
        ("Girar", "transform:rotate(-12deg)"),
    ]
    incorretos = '<div class="grade">' + "".join(
        f'<figure class="errado"><div class="caixa" style="background:{p.creme}"><div style="{estilo}">'
        f'{svgs["simbolo-positivo"]}</div></div><figcaption>✕ {n}</figcaption></figure>'
        for n, estilo in erros
    ) + (
        f'<figure class="errado"><div class="caixa" style="background:repeating-linear-gradient(45deg,{p.ouro},{p.ouro} 8px,{p.creme} 8px,{p.creme} 16px)">'
        f'{svgs["simbolo-positivo"]}</div><figcaption>✕ Fundo sem contraste</figcaption></figure></div>'
    )
    cores = "".join(
        f'<div class="cor"><span style="background:{c}"></span><b>{n}</b><code>{c}</code></div>'
        for n, c in (("Ouro claro", p.ouro_claro), ("Ouro", p.ouro), ("Bronze", p.bronze), ("Creme", p.creme), ("Preto", p.preto))
    )
    tokens = "".join(
        f"<tr><td><code>--tema-{k}</code></td><td><i style='background:{t['claro'][k]}'></i>{t['claro'][k]}</td>"
        f"<td><i style='background:{t['escuro'][k]}'></i>{t['escuro'][k]}</td></tr>"
        for k in CHAVES
    )
    paleta = (
        f'<div class="cores">{cores}</div><p>Medida nos estudos da marca (ouros e creme no logo preliminar, preto no '
        f"fundo de estúdio). O tema do site deriva dela com contraste de leitura garantido.</p>"
        f"<table class='tokens'><tr><th>Token</th><th>Claro</th><th>Escuro</th></tr>{tokens}</table>"
    )
    tipografia = (
        '<div class="amostra" style="font-family:Cinzel"><small>Cinzel — nomes e títulos</small>'
        f'<div style="font-size:48px;letter-spacing:.18em">{escape(f.nome)}</div></div>'
        '<div class="amostra" style="font-family:Jost"><small>Jost — sub-linhas, texto e interface</small>'
        '<div style="font-size:22px;letter-spacing:.45em;font-weight:300">RESIDENCIAL · CUMBUCO</div>'
        '<p style="font-size:16px">Quadra 07, lote 04: 365,61 m² com frente de 12,37 m.</p></div>'
        "<p>As duas são fontes abertas (SIL Open Font License). Equivalentes profissionais, se a Brasil Urbano "
        "quiser licenciar: " + ", ".join(f"{escape(a)} → <b>{escape(b)}</b>" for a, b in EQUIVALENTES.items()) + ".</p>"
    )
    status = "".join(f'<div class="cor"><span style="background:{c}"></span><b>{n}</b><code>{c}</code></div>' for n, c in STATUS.items())
    status_txt = f'<div class="cores">{status}</div><p>Fixas em qualquer empreendimento: não seguem a marca, para o corretor ler o mapa igual em todos.</p>'
    rodape = (
        "Preliminar e confidencial: o nome aguarda o registro. Versão guardada para validação com o marketing."
        if f.confidencial else "Preliminar."
    )
    secoes = "".join(
        _secao(n, c)
        for n, c in (
            ("Arquitetura de marca", arquitetura), ("Versões", versoes), ("Área de proteção", protecao),
            ("Tamanho mínimo", tabela_minimo), ("Usos incorretos", incorretos), ("Paleta", paleta),
            ("Tipografia", tipografia), ("Cores de status", status_txt),
        )
    )
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Brandbook preliminar</title>
<style>
{faces}
@page {{ size: A4; margin: 14mm; }}
body {{ margin:0; background:{p.creme}; color:{t['claro']['tinta']}; font-family:Jost, system-ui, sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:32px 16px 64px; }}
header h1 {{ font-family:Cinzel, serif; font-weight:400; letter-spacing:.2em; color:{t['claro']['acento']}; }}
section {{ break-before:page; padding-top:8px; }}
h2 {{ font-family:Cinzel, serif; font-weight:400; letter-spacing:.12em; border-bottom:1px solid {p.bronze}; padding-bottom:6px; }}
.caixa {{ border-radius:10px; padding:24px; display:flex; align-items:center; justify-content:center; min-height:120px; }}
.caixa svg {{ max-width:100%; max-height:220px; height:auto; }}
.par {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.grade {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(230px, 1fr)); gap:12px; }}
figure {{ margin:0; }} figcaption {{ font-size:12px; color:{t['claro']['tinta-2']}; padding-top:4px; }}
.errado figcaption {{ color:#B0625A; font-weight:500; }}
.protecao {{ padding:24px; border-radius:10px; }}
.protecao .area {{ border:1px dashed {p.bronze}; }}
.protecao svg {{ display:block; width:100%; height:auto; }}
.cores {{ display:flex; flex-wrap:wrap; gap:16px; }}
.cor span {{ display:block; width:120px; height:64px; border-radius:8px; border:1px solid #0002; }}
.cor b, .cor code {{ display:block; font-size:13px; }}
table {{ border-collapse:collapse; margin:12px 0; }} td, th {{ padding:4px 10px; border-bottom:1px solid {t['claro']['filete']}; text-align:left; font-size:13px; }}
.tokens i {{ display:inline-block; width:14px; height:14px; border-radius:3px; margin-right:6px; vertical-align:middle; border:1px solid #0002; }}
.amostra {{ background:#fff; border-radius:10px; padding:12px 16px; margin-bottom:12px; }}
footer {{ margin-top:48px; font-size:12px; color:{t['claro']['tinta-3']}; }}
@media (max-width:640px) {{ .par {{ grid-template-columns:1fr; }} }}
</style></head>
<body><main>
<header><h1>Brandbook preliminar</h1><p>{escape(" · ".join(x for x in (f.titulo, f.titulo_mae) if x))}</p></header>
{secoes}
<footer>{rodape} Gerado por scripts/marca/brandbook.py.</footer>
</main></body></html>
"""


def pdf(origem: Path, destino: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        pagina = navegador.new_page()
        pagina.goto(origem.as_uri())
        pagina.wait_for_load_state("networkidle")
        pagina.pdf(path=str(destino), format="A4", print_background=True)
        navegador.close()


def main() -> int:
    p, tipos = Paleta.carregar(PALETA_JSON), Tipos.padrao()
    fontes_b64 = {
        "Cinzel": base64.b64encode(garantir("Cinzel[wght].ttf").read_bytes()).decode("ascii"),
        "Jost": base64.b64encode(garantir("Jost[wght].ttf").read_bytes()).decode("ascii"),
    }
    for f in FAMILIAS.values():
        svgs = {a.stem: a.read_text(encoding="utf-8") for a in (SVG_DIR / f.chave).glob("*.svg")}
        destino = DESTINO / f.chave
        destino.mkdir(parents=True, exist_ok=True)
        pagina = destino / "index.html"
        conteudo = html(p, tema(p), svgs, fontes_b64, minimos(tipos, f), fracao_protecao(tipos, f), f)
        pagina.write_text(conteudo, encoding="utf-8")
        pdf(pagina, destino / "brandbook.pdf")
        print(pagina, destino / "brandbook.pdf", "(ativa)" if f.chave == ATIVA else "", sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
