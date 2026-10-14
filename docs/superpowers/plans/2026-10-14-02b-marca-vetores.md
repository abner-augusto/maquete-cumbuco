# Plano 2b — Marca: símbolo, assinaturas em SVG e brandbook

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesenhar por script o símbolo de arco e pilar do estudo E5, compor as assinaturas do produto e da marca-mãe com letreiros em contorno (Cinzel e Jost), exportar as variantes em SVG e gerar o brandbook preliminar em HTML e PDF.

**Architecture:** Pacote `scripts/marca/` ganha cinco módulos. `fontes.py` baixa as fontes OFL de um commit fixo do `google/fonts` e confere o SHA-256. `letreiro.py` converte texto em contorno SVG com fontTools. `simbolo.py` gera o símbolo como polígonos a partir de parâmetros nomeados (o Abner ajusta um número e roda de novo, como no Benevides) e faz a sobreposição com o E5 para conferência. `composicoes.py` monta símbolo, produto e marca-mãe nas quatro variantes de cor. `brandbook.py` gera um HTML autocontido e o PDF pelo Chromium do Playwright.

**Tech Stack:** Python 3.12+, uv, fontTools, Pillow, Playwright (Python), pytest.

**Spec:** `docs/superpowers/specs/2026-10-14-maquete-cumbuco-design.md` (§4 Marca)
**Plano anterior:** `docs/superpowers/plans/2026-10-14-02-marca.md` (paleta, tokens, prancha)

**Decisão do gate do 2a (14/10/2026):** fontes Cinzel e Jost; tema claro e escuro; símbolo = **E5** (arco e pilar). Interpretação registrada: o E5 vira o símbolo das duas marcas (combinação B, família única); pipa e sol do P0 ficam fora até o Abner pedir.

## Global Constraints

- Nome confidencial: brandbook com `noindex`, sem publicação; nada sai do repo sem ok explícito.
- Nenhuma geometria nem cor digitada no SVG à mão: tudo sai dos scripts, a partir de `marca/paleta.json` e dos parâmetros de `simbolo.Parametros`.
- Os SVGs não têm `<text>`: todo letreiro é contorno, para abrir igual em qualquer máquina.
- Fontes OFL baixadas para `cache/fontes/` (gitignored), de um commit fixo, com SHA-256 conferido.
- O repo não copia arquivo do cliente; o E5 é lido de `TERRENO_DIR` só para a sobreposição de conferência (em `cache/`).
- Docs, UI e commits em português do Brasil.

## Review Focus

1. **Fita sobre o pilar:** o vão (recorte) entre a fita e o pilar some se a máscara usar o espaço de coordenadas errado depois do `scale`. Teste na Task 3 (raster: fita acesa, vão apagado, pilar aceso).
2. **Letra sem glifo** (`Ç`, `Õ`, `·`) sairia em branco sem aviso. Teste na Task 2.
3. **Download corrompido ou trocado** das fontes. Teste na Task 1 (hash errado não grava).
4. **Cor fora da paleta** num SVG gerado. Teste na Task 4.
5. **Brandbook que depende da internet** (fonte ou imagem externa) quebra offline e no PDF. Teste na Task 5 (sem `http`).

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `scripts/marca/fontes.py` | `FONTES`, `baixar`, `garantir`, CLI |
| `scripts/marca/letreiro.py` | `fonte`, `Letreiro`, `contorno` |
| `scripts/marca/simbolo.py` | `Parametros`, `formas`, `svg_simbolo`, `raster`, `sobrepor`, CLI de comparação com o E5 |
| `scripts/marca/composicoes.py` | `Tipos`, `VARIANTES`, composições, `gerar`, CLI → `marca/svg/` |
| `scripts/marca/brandbook.py` | `STATUS`, `html`, `pdf`, CLI → `marca/brandbook/` |
| `tests/conftest.py` | + fixture `fonte_teste` (fonte TTF mínima feita com FontBuilder) |
| `tests/test_fontes_ofl.py`, `test_letreiro.py`, `test_simbolo.py`, `test_composicoes.py`, `test_brandbook.py` | Um por módulo |

---

### Task 1: Fontes OFL com hash

**Files:**
- Create: `scripts/marca/fontes.py`, `tests/test_fontes_ofl.py`
- Modify: `pyproject.toml` (fontTools)

**Interfaces:**
- Produces: `COMMIT: str`; `FONTES: dict[str, tuple[str, str]]` (nome do arquivo → URL, SHA-256); `PASTA = RAIZ / "cache" / "fontes"`; `baixar(url: str, destino: Path, sha256: str) -> Path`; `garantir(nome: str, pasta: Path = PASTA) -> Path`

- [ ] **Step 1: Dependência**

Run: `uv add fonttools`

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_fontes_ofl.py`:
```python
import hashlib

import pytest

from scripts.marca.fontes import FONTES, baixar


def _origem(tmp_path, conteudo=b"fonte"):
    o = tmp_path / "origem.ttf"
    o.write_bytes(conteudo)
    return o.as_uri(), hashlib.sha256(conteudo).hexdigest()


def test_baixa_e_confere_hash(tmp_path):
    url, sha = _origem(tmp_path)
    destino = tmp_path / "cache" / "f.ttf"
    assert baixar(url, destino, sha).read_bytes() == b"fonte"


def test_hash_errado_nao_grava(tmp_path):
    url, _ = _origem(tmp_path)
    destino = tmp_path / "f.ttf"
    with pytest.raises(ValueError, match="SHA-256"):
        baixar(url, destino, "0" * 64)
    assert not destino.exists()


def test_arquivo_presente_com_hash_certo_nao_baixa_de_novo(tmp_path):
    destino = tmp_path / "f.ttf"
    destino.write_bytes(b"fonte")
    sha = hashlib.sha256(b"fonte").hexdigest()
    assert baixar("file:///nao/existe.ttf", destino, sha) == destino


def test_fontes_fixas_em_commit_com_licenca():
    assert {"Cinzel[wght].ttf", "Jost[wght].ttf", "Cinzel-OFL.txt", "Jost-OFL.txt"} == set(FONTES)
    for url, sha in FONTES.values():
        assert "/main/" not in url and len(sha) == 64
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_fontes_ofl.py -q`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 4: Implementar `scripts/marca/fontes.py`**

```python
"""Fontes OFL (Cinzel, Jost) de um commit fixo do google/fonts. Uso: uv run python -m scripts.marca.fontes"""

import hashlib
import sys
import urllib.request
from pathlib import Path

from scripts.comum.ambiente import RAIZ

COMMIT = "4a943f60f1e99b2e5a2778aa34ba82adf77e4615"
_BASE = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}/ofl"
FONTES = {
    "Cinzel[wght].ttf": (f"{_BASE}/cinzel/Cinzel%5Bwght%5D.ttf", "f4d83d34d1f6c741193e4acf4b3dff9531e5a67b6aa65228d00a7db72a4e0f34"),
    "Jost[wght].ttf": (f"{_BASE}/jost/Jost%5Bwght%5D.ttf", "6343b70971000b04c5d401c96ae08ce371086135e999d5e1e1413039c0213076"),
    "Cinzel-OFL.txt": (f"{_BASE}/cinzel/OFL.txt", "f2b3029aba64c378bf0963b62945eee15e564fe4330b934c8f2eb058282b5e83"),
    "Jost-OFL.txt": (f"{_BASE}/jost/OFL.txt", "1af3438a4d5f0ed2bdbc5751a5a67ebf6d537334161184b7fbb68503ef0ea0c5"),
}
PASTA = RAIZ / "cache" / "fontes"


def _sha(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def baixar(url: str, destino: Path, sha256: str) -> Path:
    if destino.exists() and _sha(destino.read_bytes()) == sha256:
        return destino
    with urllib.request.urlopen(url, timeout=60) as r:
        dados = r.read()
    if _sha(dados) != sha256:
        raise ValueError(f"SHA-256 diferente do esperado para {url}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(dados)
    return destino


def garantir(nome: str, pasta: Path = PASTA) -> Path:
    url, sha = FONTES[nome]
    return baixar(url, pasta / nome, sha)


def main() -> int:
    for nome in FONTES:
        print(garantir(nome))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Rodar e ver passar; baixar as reais**

Run: `uv run pytest tests/test_fontes_ofl.py -q` → 4 passed. Depois `uv run python -m scripts.marca.fontes` → quatro caminhos em `cache/fontes/`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock scripts/marca/fontes.py tests/test_fontes_ofl.py
git commit -m "feat(marca): fontes Cinzel e Jost de commit fixo com SHA-256"
```

---

### Task 2: Letreiro em contorno

**Files:**
- Create: `scripts/marca/letreiro.py`, `tests/test_letreiro.py`
- Modify: `tests/conftest.py` (fixture `fonte_teste`)

**Interfaces:**
- Produces: `fonte(caminho: str, peso: int) -> TTFont` (instancia o eixo `wght` se a fonte for variável; com cache); `Letreiro(d: str, largura: float, altura_maiuscula: float)` (frozen); `contorno(tt, texto: str, tamanho: float, espacamento: float = 0.0) -> Letreiro`. O `d` tem a linha de base em y = 0 e as maiúsculas em y negativo (eixo y do SVG). `espacamento` é fração do tamanho, somada entre letras (não depois da última). Sem kerning: os letreiros da marca são caixa-alta espaçada.

- [ ] **Step 1: Fixture da fonte mínima**

Acrescentar a `tests/conftest.py`:
```python
@pytest.fixture
def fonte_teste(tmp_path):
    """TTF mínima: toda letra de A a Z, Ç, Õ e · é um retângulo 500×700 com avanço 600; espaço avança 300."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    caneta = TTGlyphPen(None)
    caneta.moveTo((0, 0)); caneta.lineTo((0, 700)); caneta.lineTo((500, 700)); caneta.lineTo((500, 0)); caneta.closePath()
    caixa = caneta.glyph()
    vazio = TTGlyphPen(None).glyph()
    letras = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + ["Ç", "Õ", "·"]
    nomes = [f"g{ord(c)}" for c in letras]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef", "space", *nomes])
    fb.setupCharacterMap({32: "space", **{ord(c): n for c, n in zip(letras, nomes)}})
    fb.setupGlyf({".notdef": vazio, "space": vazio, **{n: caixa for n in nomes}})
    fb.setupHorizontalMetrics({".notdef": (500, 0), "space": (300, 0), **{n: (600, 0) for n in nomes}})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Teste", "styleName": "Regular"})
    fb.setupOS2(sCapHeight=700, sTypoAscender=800, sTypoDescender=-200)
    fb.setupPost()
    caminho = tmp_path / "teste.ttf"
    fb.save(str(caminho))
    return caminho
```

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_letreiro.py`:
```python
import pytest

from scripts.marca.letreiro import contorno, fonte


def test_largura_altura_e_eixo_y_do_svg(fonte_teste):
    l = contorno(fonte(str(fonte_teste), 400), "AB", 100)
    assert l.largura == pytest.approx(120)
    assert l.altura_maiuscula == pytest.approx(70)
    assert l.d.startswith("M") and "-70" in l.d  # topo da letra acima da linha de base


def test_espacamento_entre_letras_nao_depois_da_ultima(fonte_teste):
    tt = fonte(str(fonte_teste), 400)
    assert contorno(tt, "AB", 100, 0.5).largura == pytest.approx(120 + 50)
    assert contorno(tt, "A B", 100, 0.5).largura == pytest.approx(60 + 30 + 60 + 2 * 50)


def test_glifo_ausente_explica(fonte_teste):
    with pytest.raises(ValueError, match="glifo ausente: 'é'"):
        contorno(fonte(str(fonte_teste), 400), "Aé", 100)
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_letreiro.py -q`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 4: Implementar `scripts/marca/letreiro.py`**

```python
"""Texto → contorno SVG com fontTools (letreiros da marca sem depender de fonte instalada)."""

from dataclasses import dataclass
from functools import lru_cache

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


@lru_cache(maxsize=None)
def fonte(caminho: str, peso: int) -> TTFont:
    tt = TTFont(caminho)
    if "fvar" in tt:
        tt = instantiateVariableFont(tt, {"wght": peso})
    return tt


@dataclass(frozen=True)
class Letreiro:
    d: str
    largura: float
    altura_maiuscula: float


def _num(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def contorno(tt: TTFont, texto: str, tamanho: float, espacamento: float = 0.0) -> Letreiro:
    glifos = tt.getGlyphSet()
    cmap = tt.getBestCmap()
    k = tamanho / tt["head"].unitsPerEm
    caneta = SVGPathPen(glifos, ntos=_num)
    x = 0.0
    for i, letra in enumerate(texto):
        if ord(letra) not in cmap:
            raise ValueError(f"glifo ausente: {letra!r}")
        g = glifos[cmap[ord(letra)]]
        g.draw(TransformPen(caneta, (k, 0, 0, -k, x, 0)))
        x += g.width * k
        if i < len(texto) - 1:
            x += espacamento * tamanho
    return Letreiro(caneta.getCommands(), x, tt["OS/2"].sCapHeight * k)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_letreiro.py -q`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/marca/letreiro.py tests/test_letreiro.py tests/conftest.py
git commit -m "feat(marca): letreiro em contorno SVG com fontTools"
```

---

### Task 3: Símbolo de arco e pilar

**Files:**
- Create: `scripts/marca/simbolo.py`, `tests/test_simbolo.py`
- Gera (fora do git): `cache/marca/comparacao-simbolo.png`

**Medidas do E5** (imagem 1536×1024): base em y = 452 px, pé esquerdo da fita em x = 352, crista perto de (660, 262), pé direito em x = 1154, perna interna nascendo em x ≈ 680 com aba para a esquerda até x ≈ 576, pilar de x ≈ 864 a 1000 com topo em y = 144. Em unidades do símbolo (largura 1000 = 802 px; y para cima a partir da base), isso dá a caixa 1000 × 384 e os padrões de `Parametros`.

**Interfaces:**
- Consumes: `scripts.loteamento.geometria.contem` (só no teste)
- Produces: `Ponto`; `Parametros` (frozen, com os padrões abaixo); `LARGURA = 1000.0`; `formas(p) -> dict[str, list[Ponto]]` (`fita`, `perna`, `pilar`; y para cima); `svg_simbolo(p, cor: str, id_mascara: str = "vao") -> str` (fragmento `<g>` em coordenadas do SVG, caixa 0..1000 × 0..`p.pilar_topo`); `raster(p, largura_px: int) -> Image.Image` (modo L, 255 = tinta); `CAIXA_E5 = (352, 144, 1154, 452)`; `sobrepor(referencia: Image.Image, mascara: Image.Image) -> Image.Image`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_simbolo.py`:
```python
import xml.etree.ElementTree as ET

from PIL import Image

from scripts.loteamento.geometria import contem
from scripts.marca.simbolo import LARGURA, Parametros, _curva_topo, formas, raster, sobrepor, svg_simbolo

P = Parametros()


def test_caixa_do_simbolo():
    pts = [pt for f in formas(P).values() for pt in f]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    assert min(xs) >= 0 and max(xs) <= LARGURA + 1e-6
    assert min(ys) >= 0 and max(ys) == P.pilar_topo


def test_topo_da_perna_fica_dentro_da_fita():
    assert contem(formas(P)["fita"], P.perna_topo)


def test_fita_passa_na_frente_do_pilar_com_vao():
    escala = 1.0
    img = raster(P, int(LARGURA * escala))
    x = (P.pilar_x[0] + P.pilar_x[1]) / 2
    topo = min(_curva_topo(P), key=lambda pt: abs(pt[0] - x))  # ponto da borda de cima da fita nesse x
    linha = lambda y: int(P.pilar_topo - y)  # noqa: E731 — raster tem y para baixo
    assert img.getpixel((int(x), linha(topo[1] - 3))) == 255  # fita
    abaixo = topo[1] - P.espessura_maxima(x) - P.vao / 2
    assert img.getpixel((int(x), linha(abaixo))) == 0  # vão recortado no pilar
    assert img.getpixel((int(x), linha(abaixo - 3 * P.vao))) == 255  # pilar


def test_svg_valido_com_mascara_e_sem_texto():
    frag = svg_simbolo(P, "#B38F59")
    doc = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {P.pilar_topo:g}">{frag}</svg>'
    raiz = ET.fromstring(doc)
    tags = {e.tag.split("}")[1] for e in raiz.iter()}
    assert "mask" in tags and "text" not in tags
    assert "#B38F59" in frag


def test_sobrepor_tinge_a_mascara():
    ref = Image.new("RGB", (10, 10), (255, 255, 255))
    m = Image.new("L", (10, 10), 0)
    m.putpixel((2, 2), 255)
    out = sobrepor(ref, m)
    r, g, b = out.getpixel((2, 2))[:3]
    assert r > g and r > b
    assert out.getpixel((5, 5))[:3] != (r, g, b)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_simbolo.py -q`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Implementar `scripts/marca/simbolo.py`**

```python
"""Símbolo de arco e pilar (estudo E5), redesenhado por parâmetros.

Unidades: largura 1000, y para cima a partir da base. Ajuste um número em Parametros e rode de novo;
a sobreposição com o E5 sai em cache/marca/comparacao-simbolo.png.
Uso: uv run python -m scripts.marca.simbolo
"""

import math
import sys
from dataclasses import dataclass

from PIL import Image, ImageChops, ImageDraw

from scripts.comum.ambiente import RAIZ, terreno_dir

Ponto = tuple[float, float]
LARGURA = 1000.0
CAIXA_E5 = (352, 144, 1154, 452)  # x0, y0, x1, y1 em px da imagem do E5
COMPARACAO = RAIZ / "cache" / "marca" / "comparacao-simbolo.png"


@dataclass(frozen=True)
class Parametros:
    crista: Ponto = (384.0, 237.0)
    ctrl_subida: tuple[Ponto, Ponto] = ((150.0, 140.0), (260.0, 237.0))
    ctrl_descida: tuple[Ponto, Ponto] = ((560.0, 237.0), (720.0, 40.0))
    espessura_pe: float = 3.0
    espessura_crista: float = 26.0
    perna_topo: Ponto = (495.0, 205.0)  # dentro da fita
    perna_largura_topo: float = 12.0
    perna_pe: float = 424.0  # x onde a perna toca a base
    perna_aba: float = 279.0  # x onde a aba da perna termina na base
    pilar_x: tuple[float, float] = (638.0, 808.0)
    pilar_topo: float = 384.0
    pilar_ombro: float = 300.0  # altura do lado direito do pilar; o topo desce em quarto de elipse
    vao: float = 9.0  # recorte entre a fita e o pilar

    def espessura(self, u: float) -> float:
        """Espessura da fita no parâmetro u ∈ [0, 1] (pé, crista, pé)."""
        return self.espessura_pe + (self.espessura_crista - self.espessura_pe) * math.sin(math.pi * u) ** 1.5

    def espessura_maxima(self, x: float) -> float:
        """Espessura da fita perto da abscissa x (para o teste do vão)."""
        topo = _curva_topo(self)
        i = min(range(len(topo)), key=lambda k: abs(topo[k][0] - x))
        return self.espessura(i / (len(topo) - 1))


def _bezier(p0: Ponto, p1: Ponto, p2: Ponto, p3: Ponto, n: int) -> list[Ponto]:
    pts = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t**2, t**3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return pts


def _curva_topo(p: Parametros, n: int = 120) -> list[Ponto]:
    subida = _bezier((0.0, 0.0), *p.ctrl_subida, p.crista, n)
    descida = _bezier(p.crista, *p.ctrl_descida, (LARGURA, 0.0), n)
    return subida + descida[1:]


def _fita(p: Parametros) -> list[Ponto]:
    topo = _curva_topo(p)
    baixo = []
    for i, (x, y) in enumerate(topo):
        (xa, ya), (xb, yb) = topo[max(i - 1, 0)], topo[min(i + 1, len(topo) - 1)]
        tx, ty = xb - xa, yb - ya
        norma = math.hypot(tx, ty) or 1.0
        nx, ny = ty / norma, -tx / norma  # normal para baixo de uma curva que anda para a direita
        e = p.espessura(i / (len(topo) - 1))
        baixo.append((min(max(x + nx * e, 0.0), LARGURA), max(y + ny * e, 0.0)))
    return topo + baixo[::-1]


def _perna(p: Parametros) -> list[Ponto]:
    tx, ty = p.perna_topo
    w = p.perna_largura_topo
    direita = _bezier((tx + w / 2, ty), (tx - 10, ty - 70), (p.perna_pe + 5, 40.0), (p.perna_pe, 0.0), 40)
    esquerda = _bezier((p.perna_aba, 0.0), (p.perna_pe - 60, 2.0), (tx - 60, ty - 90), (tx - w / 2, ty), 40)
    return direita + esquerda


def _pilar(p: Parametros) -> list[Ponto]:
    x0, x1 = p.pilar_x
    rx, ry = x1 - x0, p.pilar_topo - p.pilar_ombro
    topo = [(x0 + rx * math.cos(a), p.pilar_ombro + ry * math.sin(a)) for a in (math.pi / 2 * (1 - i / 40) for i in range(41))]
    return [(x0, 0.0), *topo, (x1, 0.0)]


def formas(p: Parametros) -> dict[str, list[Ponto]]:
    return {"fita": _fita(p), "perna": _perna(p), "pilar": _pilar(p)}


def _d(pts: list[Ponto], altura: float) -> str:
    return "M" + " L".join(f"{x:.1f} {altura - y:.1f}" for x, y in pts) + " Z"


def svg_simbolo(p: Parametros, cor: str, id_mascara: str = "vao") -> str:
    f = formas(p)
    h = p.pilar_topo
    fita = _d(f["fita"], h)
    return (
        f'<g fill="{cor}">'
        f'<defs><mask id="{id_mascara}" maskUnits="userSpaceOnUse" x="-50" y="-50" width="{LARGURA + 100:g}" height="{h + 100:g}">'
        f'<rect x="-50" y="-50" width="{LARGURA + 100:g}" height="{h + 100:g}" fill="white"/>'
        f'<path d="{fita}" fill="black" stroke="black" stroke-width="{2 * p.vao:g}" stroke-linejoin="round"/>'
        f"</mask></defs>"
        f'<path d="{_d(f["pilar"], h)}" mask="url(#{id_mascara})"/>'
        f'<path d="{_d(f["perna"], h)}"/>'
        f'<path d="{fita}"/>'
        f"</g>"
    )


def raster(p: Parametros, largura_px: int) -> Image.Image:
    k = largura_px / LARGURA
    h = p.pilar_topo
    img = Image.new("L", (largura_px, math.ceil(h * k) + 1), 0)
    dr = ImageDraw.Draw(img)
    px = lambda pts: [(x * k, (h - y) * k) for x, y in pts]  # noqa: E731
    f = formas(p)
    dr.polygon(px(f["pilar"]), fill=255)
    fita = px(f["fita"])
    dr.line(fita + fita[:1], fill=0, width=max(1, round(2 * p.vao * k)), joint="curve")
    dr.polygon(fita, fill=0)
    dr.polygon(px(f["perna"]), fill=255)
    dr.polygon(fita, fill=255)
    return img


def sobrepor(referencia: Image.Image, mascara: Image.Image) -> Image.Image:
    base = referencia.convert("L").convert("RGB")
    vermelho = Image.new("RGB", base.size, (230, 40, 40))
    alfa = mascara.resize(base.size).point(lambda v: int(v * 0.55))
    return Image.composite(vermelho, base, alfa)


def main() -> int:
    from .paleta import FONTES_LOGO

    e5 = Image.open(terreno_dir() / FONTES_LOGO["E5"]).crop(CAIXA_E5)
    largura = 1000
    ref = e5.resize((largura, round(e5.height * largura / e5.width)))
    COMPARACAO.parent.mkdir(parents=True, exist_ok=True)
    sobrepor(ref, raster(Parametros(), largura)).save(COMPARACAO)
    m = raster(Parametros(), largura).resize(ref.size)
    print(f"{COMPARACAO} (tinta do símbolo: {ImageChops.difference(m, m).getbbox() is None and 'ok'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_simbolo.py -q`
Expected: 5 passed

- [ ] **Step 5: Comparação com o E5**

Run: `uv run python -m scripts.marca.simbolo` e abrir `cache/marca/comparacao-simbolo.png` com o Read.
Expected: o símbolo em vermelho por cima do E5 em cinza. Ajuste **só** os padrões de `Parametros` até as massas coincidirem (pés, crista, perna, pilar); a fita é desenho, não traçado, e o E5 tem perspectiva e relevo. Rode os testes depois de cada ajuste.

- [ ] **Step 6: Commit**

```bash
git add scripts/marca/simbolo.py tests/test_simbolo.py
git commit -m "feat(marca): símbolo de arco e pilar gerado por parâmetros"
```

---

### Task 4: Assinaturas em SVG

**Files:**
- Create: `scripts/marca/composicoes.py`, `tests/test_composicoes.py`
- Gera (commitado): `marca/svg/*.svg`

**Interfaces:**
- Consumes: `letreiro.*`, `simbolo.Parametros`, `simbolo.svg_simbolo`, `Paleta`, `fontes.garantir`
- Produces: `Tipos(serifada, sans_leve, sans)` (TTFont); `VARIANTES: tuple[str, ...]` = (`positivo`, `negativo`, `mono-escuro`, `mono-claro`); `cores_da_variante(p: Paleta, v: str) -> tuple[str, str]` (símbolo, texto); `COMPOSICOES: dict[str, Callable]` com `simbolo`, `produto-vertical`, `produto-horizontal`, `assinatura-mae`; `gerar(p: Paleta, tipos: Tipos, destino: Path) -> list[Path]`

**Letreiros:** "ALTERNATIVA" em Cinzel 400, espaçamento 0,18; "RESIDENCIAL" em Jost 300, 0,5; "CUMBUCO" em Jost 400, 0,55; "DESENVOLVIMENTO URBANO" em Jost 300, 0,35; filete com losango no centro entre o nome e as sub-linhas.

**Variantes:** positivo = símbolo ouro e texto bronze (fundo claro); negativo = ouro claro (fundo escuro); mono-escuro = preto; mono-claro = `#FFFFFF`. Todas com fundo transparente. Mais `favicon.svg`: símbolo em ouro claro sobre quadrado arredondado preto.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_composicoes.py`:
```python
import re
import xml.etree.ElementTree as ET

from scripts.marca.composicoes import COMPOSICOES, VARIANTES, Tipos, cores_da_variante, gerar
from scripts.marca.letreiro import fonte
from scripts.marca.paleta import Paleta

P = Paleta(ouro_claro="#E3C89C", ouro="#B38F59", bronze="#735222", creme="#EAE3D8", preto="#08090A")


def _tipos(caminho):
    tt = fonte(str(caminho), 400)
    return Tipos(serifada=tt, sans_leve=tt, sans=tt)


def _caixa(raiz):
    return [float(v) for v in raiz.get("viewBox").split()]


def test_gera_toda_composicao_em_toda_variante_mais_favicon(tmp_path, fonte_teste):
    arquivos = gerar(P, _tipos(fonte_teste), tmp_path)
    nomes = {a.name for a in arquivos}
    assert {f"{c}-{v}.svg" for c in COMPOSICOES for v in VARIANTES} | {"favicon.svg"} == nomes


def test_svgs_validos_sem_texto_e_so_com_cores_da_paleta(tmp_path, fonte_teste):
    permitidas = {P.ouro, P.ouro_claro, P.bronze, P.preto, "#FFFFFF", "white", "black"}
    for a in gerar(P, _tipos(fonte_teste), tmp_path):
        texto = a.read_text(encoding="utf-8")
        raiz = ET.fromstring(texto)
        assert not [e for e in raiz.iter() if e.tag.endswith("}text")], a.name
        cores = set(re.findall(r'(?:fill|stroke)="([^"]+)"', texto)) - {"none"}
        assert cores <= permitidas, (a.name, cores - permitidas)
        x, y, w, h = _caixa(raiz)
        assert w > 0 and h > 0


def test_proporcoes(tmp_path, fonte_teste):
    gerar(P, _tipos(fonte_teste), tmp_path)
    caixa = lambda n: _caixa(ET.parse(tmp_path / f"{n}-positivo.svg").getroot())  # noqa: E731
    _, _, w, h = caixa("produto-horizontal")
    assert w > 2 * h
    _, _, w, h = caixa("produto-vertical")
    assert h > 0.6 * w


def test_cores_da_variante():
    assert cores_da_variante(P, "positivo") == (P.ouro, P.bronze)
    assert cores_da_variante(P, "negativo") == (P.ouro_claro, P.ouro_claro)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_composicoes.py -q`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Implementar `scripts/marca/composicoes.py`**

```python
"""Assinaturas da marca em SVG (símbolo, produto, marca-mãe) nas quatro variantes. Uso: uv run python -m scripts.marca.composicoes"""

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
    return Peca(f'<g transform="scale({k:.5f})">{svg_simbolo(p, cor)}</g>', LARGURA * k, altura)


def _pilha(pecas: list[Peca], vaos: list[float]) -> Peca:
    largura = max(pc.largura for pc in pecas)
    y, partes = 0.0, []
    for i, pc in enumerate(pecas):
        partes.append(f'<g transform="translate({(largura - pc.largura) / 2:.2f} {y:.2f})">{pc.svg}</g>')
        y += pc.altura + (vaos[i] if i < len(vaos) else 0)
    return Peca("".join(partes), largura, y)


def _pilha_esquerda(pecas: list[Peca], vaos: list[float]) -> Peca:
    largura = max(pc.largura for pc in pecas)
    y, partes = 0.0, []
    for i, pc in enumerate(pecas):
        partes.append(f'<g transform="translate(0 {y:.2f})">{pc.svg}</g>')
        y += pc.altura + (vaos[i] if i < len(vaos) else 0)
    return Peca("".join(partes), largura, y)


def _lado_a_lado(a: Peca, b: Peca, vao: float) -> Peca:
    altura = max(a.altura, b.altura)
    return Peca(
        f'<g transform="translate(0 {(altura - a.altura) / 2:.2f})">{a.svg}</g>'
        f'<g transform="translate({a.largura + vao:.2f} {(altura - b.altura) / 2:.2f})">{b.svg}</g>',
        a.largura + vao + b.largura, altura,
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
            arq.write_text(_documento(compor(tipos, *cores_da_variante(p, v))), encoding="utf-8")
            arquivos.append(arq)
    fav = destino / "favicon.svg"
    fav.write_text(_favicon(p), encoding="utf-8")
    return [*arquivos, fav]


def main() -> int:
    for a in gerar(Paleta.carregar(PALETA_JSON), Tipos.padrao(), DESTINO):
        print(a.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_composicoes.py -q`
Expected: 4 passed

- [ ] **Step 5: Gerar com as fontes reais e olhar**

Run: `uv run python -m scripts.marca.composicoes` → 17 arquivos em `marca/svg/`. Renderize `produto-vertical-positivo.svg` e `produto-horizontal-negativo.svg` para PNG pelo Chromium do Playwright (o mesmo da Task 5) e confira com o Read: letreiros legíveis, símbolo inteiro, nada cortado pela margem.

- [ ] **Step 6: Commit**

```bash
git add scripts/marca/composicoes.py tests/test_composicoes.py marca/svg
git commit -m "feat(marca): assinaturas do produto e da marca-mãe em SVG"
```

---

### Task 5: Brandbook HTML e PDF

**Files:**
- Create: `scripts/marca/brandbook.py`, `tests/test_brandbook.py`
- Modify: `pyproject.toml` (playwright no grupo dev)
- Gera (commitado): `marca/brandbook/index.html`, `marca/brandbook/brandbook.pdf`

**Interfaces:**
- Consumes: `Paleta`, `tokens.tema`, `tokens.CHAVES`, `marca/svg/*.svg`, `fontes.garantir`
- Produces: `STATUS: dict[str, str]`; `EQUIVALENTES: dict[str, str]`; `html(p: Paleta, t: dict, svgs: dict[str, str], fontes_b64: dict[str, str]) -> str`; `pdf(origem: Path, destino: Path) -> None`

**Seções:** 1 Arquitetura de marca; 2 Versões (4 composições × 4 variantes, cada uma sobre o fundo certo); 3 Área de proteção (x = largura do pilar); 4 Tamanho mínimo; 5 Usos incorretos (distorcer, recolorir, efeito, fundo poluído); 6 Paleta e tema (claro e escuro); 7 Tipografia (Cinzel, Jost e as profissionais equivalentes); 8 Cores de status (fixas, fora da marca).

- [ ] **Step 1: Dependência e navegador**

Run: `uv add --dev playwright` e `uv run playwright install chromium`

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_brandbook.py`:
```python
from scripts.marca.brandbook import EQUIVALENTES, STATUS, html
from scripts.marca.paleta import Paleta
from scripts.marca.tokens import tema

P = Paleta(ouro_claro="#E3C89C", ouro="#B38F59", bronze="#735222", creme="#EAE3D8", preto="#08090A")
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0 L10 10 Z"/></svg>'
NOMES = [f"{c}-{v}" for c in ("simbolo", "produto-vertical", "produto-horizontal", "assinatura-mae")
         for v in ("positivo", "negativo", "mono-escuro", "mono-claro")]


def _html():
    return html(P, tema(P), {n: SVG for n in NOMES}, {"Cinzel": "AAAA", "Jost": "BBBB"})


def test_tem_as_oito_secoes():
    h = _html()
    for titulo in ("Arquitetura de marca", "Versões", "Área de proteção", "Tamanho mínimo",
                   "Usos incorretos", "Paleta", "Tipografia", "Cores de status"):
        assert f">{titulo}<" in h, titulo


def test_cores_status_e_equivalentes():
    h = _html()
    for c in (P.ouro_claro, P.ouro, P.bronze, P.creme, P.preto, *STATUS.values()):
        assert c in h
    for profissional in EQUIVALENTES.values():
        assert profissional in h


def test_autocontido_e_confidencial():
    h = _html()
    assert "http://" not in h.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "https://" not in h
    assert '<meta name="robots" content="noindex, nofollow">' in h
    assert "@font-face" in h and "data:font/ttf;base64,AAAA" in h
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_brandbook.py -q`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 4: Implementar `scripts/marca/brandbook.py`**

```python
"""Brandbook preliminar em HTML autocontido e PDF. Uso: uv run python -m scripts.marca.brandbook"""

import base64
import sys
from html import escape
from pathlib import Path

from scripts.comum.ambiente import RAIZ

from .composicoes import COMPOSICOES, DESTINO as SVG_DIR, VARIANTES
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


def _secao(titulo: str, corpo: str) -> str:
    return f"<section><h2>{escape(titulo)}</h2>{corpo}</section>"


def html(p: Paleta, t: dict, svgs: dict[str, str], fontes_b64: dict[str, str]) -> str:
    fundo = {"creme": p.creme, "preto": p.preto, "bronze": p.bronze}
    faces = "\n".join(
        f'@font-face {{ font-family:"{n}"; src:url(data:font/ttf;base64,{b}) format("truetype"); font-weight:100 900; }}'
        for n, b in fontes_b64.items()
    )
    arquitetura = (
        "<p>O produto <b>Alternativa Residencial Cumbuco</b> vem em destaque; a marca-mãe <b>Alternativa Desenvolvimento "
        "Urbano</b> assina de forma discreta (rodapé, carimbo). As duas usam o mesmo símbolo de arco e pilar.</p>"
        f'<div class="par"><div class="caixa" style="background:{p.creme}">{svgs["produto-vertical-positivo"]}</div>'
        f'<div class="caixa" style="background:{p.creme}">{svgs["assinatura-mae-positivo"]}</div></div>'
    )
    versoes = '<div class="grade">' + "".join(
        f'<figure><div class="caixa" style="background:{fundo[_FUNDO[v]]}">{svgs[f"{c}-{v}"]}</div>'
        f"<figcaption>{c} · {v}</figcaption></figure>"
        for c in COMPOSICOES for v in VARIANTES
    ) + "</div>"
    protecao = (
        "<p>Em volta da assinatura, deixe livre no mínimo <b>x</b>, a largura do pilar do símbolo. "
        "Nenhum texto, borda ou imagem entra nessa área.</p>"
        f'<div class="protecao" style="background:{p.creme}"><div class="x">{svgs["produto-horizontal-positivo"]}</div></div>'
    )
    minimo = (
        "<table><tr><th>Versão</th><th>Tela</th><th>Impresso</th></tr>"
        "<tr><td>Símbolo</td><td>16 px</td><td>6 mm</td></tr>"
        "<tr><td>Produto horizontal (largura)</td><td>140 px</td><td>35 mm</td></tr>"
        "<tr><td>Produto vertical (largura)</td><td>96 px</td><td>24 mm</td></tr>"
        "<tr><td>Assinatura da marca-mãe (largura)</td><td>120 px</td><td>30 mm</td></tr></table>"
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
        '<div style="font-size:48px;letter-spacing:.18em">ALTERNATIVA</div></div>'
        '<div class="amostra" style="font-family:Jost"><small>Jost — sub-linhas, texto e interface</small>'
        '<div style="font-size:22px;letter-spacing:.45em;font-weight:300">RESIDENCIAL · CUMBUCO</div>'
        '<p style="font-size:16px">Lote de 365,61 m² com frente de 12,37 m, a 10 minutos da praia do Cumbuco.</p></div>'
        "<p>As duas são fontes abertas (SIL Open Font License). Equivalentes profissionais, se a Brasil Urbano "
        "quiser licenciar: " + ", ".join(f"{escape(a)} → <b>{escape(b)}</b>" for a, b in EQUIVALENTES.items()) + ".</p>"
    )
    status = "".join(f'<div class="cor"><span style="background:{c}"></span><b>{n}</b><code>{c}</code></div>' for n, c in STATUS.items())
    status_txt = f'<div class="cores">{status}</div><p>Fixas em qualquer empreendimento: não seguem a marca, para o corretor ler o mapa igual em todos.</p>'
    secoes = "".join(
        _secao(n, c)
        for n, c in (
            ("Arquitetura de marca", arquitetura), ("Versões", versoes), ("Área de proteção", protecao),
            ("Tamanho mínimo", minimo), ("Usos incorretos", incorretos), ("Paleta", paleta),
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
.protecao {{ padding:40px; border-radius:10px; }}
.protecao .x {{ outline:1px dashed {p.bronze}; outline-offset:24px; }}
.protecao svg {{ width:100%; height:auto; }}
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
<header><h1>Brandbook preliminar</h1><p>Alternativa Residencial Cumbuco · Alternativa Desenvolvimento Urbano</p></header>
{secoes}
<footer>Preliminar e confidencial: o nome aguarda a assinatura do compliance. Gerado por scripts/marca/brandbook.py.</footer>
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
    p = Paleta.carregar(PALETA_JSON)
    svgs = {a.stem: a.read_text(encoding="utf-8") for a in SVG_DIR.glob("*.svg")}
    fontes_b64 = {
        "Cinzel": base64.b64encode(garantir("Cinzel[wght].ttf").read_bytes()).decode("ascii"),
        "Jost": base64.b64encode(garantir("Jost[wght].ttf").read_bytes()).decode("ascii"),
    }
    DESTINO.mkdir(parents=True, exist_ok=True)
    pagina = DESTINO / "index.html"
    pagina.write_text(html(p, tema(p), svgs, fontes_b64), encoding="utf-8")
    pdf(pagina, DESTINO / "brandbook.pdf")
    print(pagina, DESTINO / "brandbook.pdf", sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

O SVG embutido várias vezes repete o `id` da máscara (`vao`). Navegadores resolvem a primeira ocorrência, que tem a mesma geometria em todos os símbolos de mesma escala, mas as escalas diferem entre composições. Por isso, `main` troca o id de cada SVG antes de embutir: `svgs = {n: s.replace('id="vao"', f'id="vao-{n}"').replace("url(#vao)", f"url(#vao-{n})") for n, s in svgs.items()}`. Inclua essa linha logo depois de ler os SVGs e um teste em `tests/test_brandbook.py`:

```python
def test_ids_de_mascara_unicos_no_html():
    import re
    from scripts.marca.brandbook import ids_unicos

    svg = '<svg><mask id="vao"/><path mask="url(#vao)"/></svg>'
    h = "".join(ids_unicos({"a": svg, "b": svg}).values())
    ids = re.findall(r'id="([^"]+)"', h)
    assert len(ids) == len(set(ids)) == 2
```

com `def ids_unicos(svgs: dict[str, str]) -> dict[str, str]` em `brandbook.py` fazendo a troca acima, e `main` chamando `ids_unicos` antes de `html`.

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest -q`
Expected: a suíte inteira passa.

- [ ] **Step 6: Gerar e conferir**

Run: `uv run python -m scripts.marca.brandbook`
Expected: `marca/brandbook/index.html` e `brandbook.pdf`. Gere um PNG da primeira e da terceira página (Playwright, `page.screenshot`) e confira com o Read: fontes Cinzel e Jost aplicadas (não a serifada padrão), SVGs inteiros, uma seção por página no PDF.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock scripts/marca/brandbook.py tests/test_brandbook.py marca/brandbook
git commit -m "feat(marca): brandbook preliminar em HTML e PDF"
```

---

### Task 6: ⛔ Gate — revisão visual do Abner

Mostre ao Abner, numa só sessão (preferência dele: revisão visual em lote): `cache/marca/comparacao-simbolo.png`, `marca/brandbook/brandbook.pdf` e os SVGs principais. Perguntas: o símbolo está fiel ao E5 ou ajusto quais parâmetros (crista, espessura, pilar)? As assinaturas e as cores das variantes estão certas? Ajustes voltam como mudança em `Parametros`, nos tamanhos de `composicoes.py` ou na paleta, nunca em SVG editado à mão.

---

## Fim do Plano 2b

**Entregue:** `marca/svg/` (16 assinaturas e o favicon), `marca/brandbook/index.html` e `brandbook.pdf`, tudo reproduzível com `scripts.marca.fontes`, `composicoes` e `brandbook`.

**Próximo:** Plano 3 (modelagem do loteamento no Blender), que consome `dados/lotes.json` e `georref.json`.
