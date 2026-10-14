"""Prancha comparativa dos logos, para o gate da escolha. Uso: uv run python -m scripts.marca.prancha

Fica em cache/ (fora do git) e não é publicada: o nome é confidencial até o compliance.
"""

import base64
import io
import sys
from html import escape
from pathlib import Path

from PIL import Image

from scripts.comum.ambiente import RAIZ, terreno_dir

from .paleta import DESTINO as PALETA_JSON
from .paleta import FONTES_LOGO, FONTES_OURO, FONTES_PRETO, Paleta
from .tokens import tema

DESTINO = RAIZ / "cache" / "marca" / "prancha.html"

DESCRICOES = {
    "P0": "Produto — logo preliminar: marquise em arco, pipa de kitesurf, sol e reflexo; ouro sobre creme.",
    "E1": "Marca-mãe — arco e pilar em relevo sobre parede clara.",
    "E2": "Marca-mãe — arco e pilar em pedra, luz de fim de tarde.",
    "E3": "Marca-mãe — arco e pilar sobre fundo escuro, com palavras-chave laterais.",
    "E4": "Marca-mãe — “N” monolítico, prancha do ecossistema (Américas, Brasil Urbano).",
    "E5": "Marca-mãe — arco e pilar, preto, assinatura “Cidades que inspiram gerações”.",
    "E6": "Marca-mãe — arco e pilar grande, preto, sem tagline.",
}

COMBINACOES = [
    ("Combinação A — produto como está",
     "Símbolo do P0 (marquise, pipa e sol) no produto; arco e pilar (E1/E6) só na assinatura da marca-mãe. Duas marcas visualmente distintas."),
    ("Combinação B — família única",
     "Arco e pilar da marca-mãe também no produto, com pipa e sol como elemento secundário do Cumbuco. Endossa a marca-mãe a cada uso."),
    ("Combinação C — mistura",
     "A curva da marquise do P0 trocada pelo arco da marca-mãe, mantendo pipa e sol. Produto próprio com o DNA da mãe."),
]

_PERGUNTAS = [
    "Qual símbolo do produto: A, B, C ou outra mistura (diga quais ids)?",
    "Serifada de “ALTERNATIVA”: Cinzel ou Marcellus?",
    "Sans das sub-linhas: Jost ou Montserrat?",
]


def miniatura(caminho: Path, lado: int = 900) -> str:
    img = Image.open(caminho).convert("RGB")
    img.thumbnail((lado, lado))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _ficha(t: dict[str, str], modo: str) -> str:
    v = ";".join(f"--{k}:{c}" for k, c in t.items())
    return f"""<div class="ficha" style="{v}">
  <div class="rotulo">Quadra 07 · Lote 04 · {modo}</div>
  <div class="titulo">Q07L04</div>
  <div class="linha"><span>Área</span><b>365,61 m²</b></div>
  <div class="linha"><span>Frente</span><b>12,37 m</b></div>
  <button>Quero este lote</button>
  <p class="nota">Texto secundário na tinta-2 e realce no <em>sol-texto</em>.</p>
</div>"""


def html_prancha(imagens: dict[str, str], p: Paleta, t: dict) -> str:
    cartoes = "\n".join(
        f'<figure><img src="{imagens[i]}" alt="{i}"><figcaption><b>{i}</b> {escape(DESCRICOES[i])}</figcaption></figure>'
        for i in FONTES_LOGO
    )
    combos = "\n".join(f"<div class='combo'><h3>{escape(n)}</h3><p>{escape(d)}</p></div>" for n, d in COMBINACOES)
    cores = "\n".join(
        f'<div class="cor"><span style="background:{c}"></span>{n}<code>{c}</code></div>'
        for n, c in (("Ouro claro", p.ouro_claro), ("Ouro", p.ouro), ("Bronze", p.bronze), ("Creme", p.creme), ("Preto", p.preto))
    )
    fontes = "\n".join(
        f'<div class="amostra" style="font-family:\'{f}\'"><small>{f}</small><div class="{cls}">{txt}</div></div>'
        for f, cls, txt in (
            ("Cinzel", "serif", "ALTERNATIVA"), ("Marcellus", "serif", "ALTERNATIVA"),
            ("Jost", "sans", "RESIDENCIAL · CUMBUCO"), ("Montserrat", "sans", "RESIDENCIAL · CUMBUCO"),
        )
    )
    perguntas = "\n".join(f"<li>{escape(q)}</li>" for q in _PERGUNTAS)
    origem = f"Ouros e creme medidos em {', '.join(FONTES_OURO)}; preto em {', '.join(FONTES_PRETO)} (os demais estudos são cenas que contaminam a cor)."
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Prancha de marca</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&family=Marcellus&family=Jost:wght@300;400;500&family=Montserrat:wght@300;400;500&display=swap">
<style>
body {{ margin:0; background:{p.creme}; color:{p.preto}; font-family:Jost, system-ui, sans-serif; }}
main {{ max-width:1200px; margin:0 auto; padding:32px 16px 64px; }}
h1 {{ font-family:Cinzel, serif; letter-spacing:.2em; font-weight:600; }}
h2 {{ margin-top:48px; border-bottom:1px solid {p.bronze}; padding-bottom:6px; font-weight:500; }}
.grade {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:16px; }}
figure {{ margin:0; background:#fff; border-radius:10px; overflow:hidden; }}
figure img {{ width:100%; display:block; }}
figcaption {{ padding:10px 12px; font-size:14px; }}
.combo {{ background:#fff; border-radius:10px; padding:4px 16px; margin-bottom:12px; }}
.cores {{ display:flex; flex-wrap:wrap; gap:16px; }}
.cor span {{ display:block; width:120px; height:72px; border-radius:8px; border:1px solid #0002; }}
.cor code {{ display:block; }}
.amostra {{ background:#fff; border-radius:10px; padding:12px 16px; margin-bottom:12px; overflow:hidden; }}
.amostra .serif {{ font-size:clamp(32px, 7vw, 56px); letter-spacing:.18em; }}
.amostra .sans {{ font-size:clamp(14px, 3vw, 24px); letter-spacing:.45em; font-weight:300; }}
.fichas {{ display:flex; flex-wrap:wrap; gap:16px; }}
.ficha {{ width:320px; max-width:100%; background:var(--papel); color:var(--tinta); border:1px solid var(--filete); border-radius:18px; padding:20px; }}
.ficha .rotulo {{ color:var(--tinta-3); font-size:12px; letter-spacing:.2em; text-transform:uppercase; }}
.ficha .titulo {{ font-family:Cinzel, serif; font-size:32px; color:var(--acento); }}
.ficha .linha {{ display:flex; justify-content:space-between; border-top:1px solid var(--filete); padding:8px 0; color:var(--tinta-2); }}
.ficha .linha b {{ color:var(--tinta); }}
.ficha button {{ width:100%; margin-top:12px; padding:12px; border:0; border-radius:10px; background:var(--acento); color:var(--acento-contraste); font-size:16px; }}
.ficha em {{ color:var(--sol-texto); font-style:normal; }}
.nota {{ color:var(--tinta-2); font-size:13px; }}
.gate {{ background:{p.preto}; color:{p.creme}; border-radius:10px; padding:8px 24px; }}
</style></head>
<body><main>
<h1>Prancha de marca</h1>
<p>Confidencial — não publicar até a assinatura do compliance do nome.</p>
<h2>Insumos</h2>
<div class="grade">
{cartoes}
</div>
<h2>Combinações</h2>
{combos}
<h2>Tipografia (fontes abertas)</h2>
{fontes}
<h2>Paleta medida</h2>
<p>{escape(origem)}</p>
<div class="cores">
{cores}
</div>
<h2>Tema aplicado</h2>
<div class="fichas">
{_ficha(t["claro"], "claro")}
{_ficha(t["escuro"], "escuro")}
</div>
<h2>Para decidir</h2>
<div class="gate"><ol>
{perguntas}
</ol></div>
</main></body></html>
"""


def main() -> int:
    terreno = terreno_dir()
    p = Paleta.carregar(PALETA_JSON)
    imagens = {i: miniatura(terreno / rel) for i, rel in FONTES_LOGO.items()}
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(html_prancha(imagens, p, tema(p)), encoding="utf-8")
    print(DESTINO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
