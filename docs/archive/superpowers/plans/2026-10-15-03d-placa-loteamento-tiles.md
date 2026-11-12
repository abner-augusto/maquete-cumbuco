# Plano 3d — Placa do loteamento em volume, chão em tiles e masterplan pintado

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar as camadas drapeadas do loteamento por uma placa em volume sem sobreposição (fim do z-fighting, luz e sombra, pivô por lote), cortar o chão em 4 tiles de 4096 px e pintar o masterplan das fases 2–10 em segundo plano.

**Architecture:** Mesmo método dos planos 3 e 4: Python puro calcula a geometria e grava JSON de cena; o Blender só constrói e exporta. `placa.py` particiona o platô em shapely e levanta as peças (topo + paredes por regra única). `chao.py` recorta a grade do terreno perto só nas células da borda da placa. `tiles.py` define as 4 janelas usadas tanto pelas malhas (`Entorno_ij`, `Terreno_ij`) quanto pelas imagens (`mapa_ij.jpg`). `masterplan.py` rasteriza a página 5 do `MASTER URBANO.pdf`, registra-a na poligonal do DWG e a mistura nos tiles.

**Tech Stack:** Python 3.12+ (uv), shapely 2, numpy, scipy (cKDTree), mapbox-earcut, Pillow, ezdxf, PyMuPDF (novo), Blender 5.2 em `-b`.

**Spec:** `docs/superpowers/specs/2026-10-15-placa-loteamento-tiles-design.md`

## Global Constraints

- Docs, mensagens de commit, textos e nomes de domínio em português do Brasil.
- O modelo é gerado por script: corrigir o script e rodar de novo; nunca editar o `.blend` gerado.
- Nenhum número entra à mão no front: `dados/` e `cache/` são regenerados pelos scripts.
- "Alternativa" não aparece em nada gerado ou publicado.
- `loteamento.glb` ≤ 8 MB, `entorno.glb` ≤ 8 MB; nenhum `.blend1` na pasta do terreno.
- Ids de lote `Q<quadra>L<lote>` inalterados; 347 lotes no `loteamento.glb`.
- Alturas (relativas à cota do platô): pista 0; calçadas, verdes, institucional, fundo, APP e juntas +0,25; lote +0,40 (recuo 0,15 m por lado); lagoa −0,30; paredes até −1,0.
- Tiles: 4096 px no lado maior, margem de 2 px, JPEG qualidade 85.
- Masterplan: segundo plano, saturação 0,35, opacidade 0,55; resíduo do registro ≤ 2 m; desligável por `masterplan = false`.
- Rodar tudo com `uv run` a partir da raiz do repo; Blender pelo `BLENDER` do `.env`.

## Review Focus

1. **Lote sem área depois da lagoa** (desenho em que a lagoa engole um lote): o script falha nomeando o lote, em vez de exportar 346 objetos. Teste na Task 2.
2. **Lote estreito demais para o recuo** (largura < 0,30 m em algum trecho, recuo vazio): o lote sai sem recuo, sem exceção. Teste na Task 2.
3. **Furos que não são pista nem água**: a ilha da rotatória (círculo dentro de `Vias`) vira `ChaoPlato`, não pista; a ilha da lagoa (anel de APP dentro dela) vira `APP`, não água. Testes nas Tasks 2 e 5.
4. **Coqueiros dos canteiros enterrados** 0,25 m nos verdes que subiram: o offset dos canteiros passa a ser a altura de `Verdes` da placa. Teste na Task 5.
5. **Prévia e caixa dos lotes com o pivô novo**: com a origem do objeto no centro do lote, ler `v.co` dá coordenada local e a prévia enquadra no lugar errado; a prévia usa coordenadas de mundo. Teste do pivô no GLB na Task 7.

---

### Task 1: Janelas dos tiles e entorno em 4 pedaços

**Files:**
- Create: `scripts/entorno/tiles.py`
- Modify: `scripts/loteamento/terreno.py` (`malha_entorno`, `main`)
- Modify: `scripts/entorno/vegetacao.py:110` (nível do mar pelo nome do objeto)
- Test: `tests/test_tiles.py`, `tests/test_terreno.py`

**Interfaces:**
- Produces: `Ext = tuple[float, float, float, float]`; `linhas_de_corte(ext: Ext, passo: float) -> tuple[float, float]`; `janelas(ext: Ext, passo: float) -> dict[str, Ext]` com chaves `"00"`, `"01"`, `"10"`, `"11"` (1º dígito oeste/leste, 2º sul/norte); `da_janela(janela: Ext, x: float, y: float) -> bool`; `ext_da_grade(g: Grade) -> Ext`; `com_margem(janela: Ext, px: int, margem_px: int) -> Ext`; `malha_entorno(dem, buraco, centro, raio, janela: Ext | None = None)`. `entorno.json` passa a ter `Entorno_00…11` e `Mar`.

- [ ] **Step 1: Write the failing tests**

`tests/test_tiles.py`:

```python
import pytest

from scripts.entorno.tiles import com_margem, da_janela, janelas, linhas_de_corte

EXT = (-4050.0, -3960.0, 3990.0, 4050.0)  # recorte real (mapa.json do Plano 4)


def test_linhas_caem_em_nos_da_grade_perto_do_meio():
    xc, yc = linhas_de_corte(EXT, 30.0)
    assert (xc, yc) == (-30.0, 60.0)
    assert (xc - EXT[0]) % 30 == 0 and (yc - EXT[1]) % 30 == 0
    assert xc % 10 == 0 and yc % 10 == 0  # também nó da grade perto (10 m, múltiplos absolutos de 30)


def test_quatro_janelas_cobrem_o_recorte_sem_fresta():
    js = janelas(EXT, 30.0)
    assert sorted(js) == ["00", "01", "10", "11"]
    area = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in js.values())
    assert area == pytest.approx((EXT[2] - EXT[0]) * (EXT[3] - EXT[1]))
    assert js["00"][2] == js["10"][0] and js["00"][3] == js["01"][1]


def test_ponto_na_linha_pertence_a_uma_janela_so():
    js = janelas(EXT, 30.0)
    assert sum(da_janela(j, -30.0, 60.0) for j in js.values()) == 1


def test_margem_e_de_k_pixels_exatos():
    j = (0.0, 0.0, 4092.0, 2000.0)
    x0, y0, x1, y1 = com_margem(j, 4096, 2)
    mpp = (x1 - x0) / 4096  # rasterizar usa o lado maior
    assert (0.0 - x0) / mpp == pytest.approx(2.0)
```

Em `tests/test_terreno.py`, ao fim:

```python
def test_entorno_em_janelas_reparte_as_celulas_sem_repetir():
    from scripts.entorno.tiles import janelas

    dem = Grade(0.0, 0.0, 30.0, 11, 11, [[1.0] * 11 for _ in range(11)])
    buraco, centro, raio = (120.0, 120.0, 180.0, 180.0), (150.0, 150.0), 1e9
    _, inteiro = malha_entorno(dem, buraco, centro, raio)
    total = 0
    for jan in janelas((0.0, 0.0, 300.0, 300.0), 30.0).values():
        _, f = malha_entorno(dem, buraco, centro, raio, jan)
        total += len(f)
    assert total == len(inteiro)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_tiles.py tests/test_terreno.py -q`
Expected: FAIL (`ModuleNotFoundError: scripts.entorno.tiles`; `malha_entorno() takes 4 positional arguments`).

- [ ] **Step 3: Implement**

`scripts/entorno/tiles.py`:

```python
"""Corte do recorte do chão em 2×2 tiles. As linhas caem em nós da grade, então nenhuma célula
(e nenhum triângulo) é partida. Chave "ij": i = 0 oeste / 1 leste, j = 0 sul / 1 norte."""

Ext = tuple[float, float, float, float]


def linhas_de_corte(ext: Ext, passo: float) -> tuple[float, float]:
    x0, y0, x1, y1 = ext
    return (x0 + round((x1 - x0) / 2 / passo) * passo, y0 + round((y1 - y0) / 2 / passo) * passo)


def janelas(ext: Ext, passo: float) -> dict[str, Ext]:
    x0, y0, x1, y1 = ext
    xc, yc = linhas_de_corte(ext, passo)
    xs, ys = ((x0, xc), (xc, x1)), ((y0, yc), (yc, y1))
    return {f"{i}{j}": (xs[i][0], ys[j][0], xs[i][1], ys[j][1]) for i in range(2) for j in range(2)}


def da_janela(janela: Ext, x: float, y: float) -> bool:
    """Borda oeste e sul incluídas, leste e norte não: cada ponto cai numa janela só."""
    x0, y0, x1, y1 = janela
    return x0 <= x < x1 and y0 <= y < y1


def ext_da_grade(g) -> Ext:
    return (g.x0, g.y0, g.x0 + g.passo * (g.nx - 1), g.y0 + g.passo * (g.ny - 1))


def com_margem(janela: Ext, px: int, margem_px: int) -> Ext:
    """Janela aumentada em `margem_px` pixels de cada lado, para a imagem de `px` no lado maior.
    O UV usa esta extensão: o texel da borda já tem o conteúdo do vizinho e o filtro não abre costura."""
    x0, y0, x1, y1 = janela
    m = max(x1 - x0, y1 - y0) / (px - 2 * margem_px) * margem_px
    return (x0 - m, y0 - m, x1 + m, y1 + m)
```

Em `scripts/loteamento/terreno.py`, `malha_entorno` ganha `janela` e filtra pelo centro da célula:

```python
def malha_entorno(dem: Grade, buraco: tuple[float, float, float, float], centro: tuple[float, float],
                  raio: float, janela: tuple[float, float, float, float] | None = None
                  ) -> tuple[list[list[float]], list[list[int]]]:
    """Grade do Copernicus em triângulos: células com os 4 cantos no raio e fora do `buraco`
    (o terreno perto). O buraco cai em linhas da grade, então cada célula está toda dentro ou fora.
    Com `janela`, só as células cujo centro cai nela (tiles.da_janela)."""
```

e, dentro do laço, logo depois de calcular `xb, yb`:

```python
            if janela is not None and not da_janela(janela, (xa + xb) / 2, (ya + yb) / 2):
                continue
```

com `from scripts.entorno.tiles import da_janela, ext_da_grade, janelas` no topo. No `main`, troque a montagem de `DESTINO_ENTORNO`:

```python
    entorno = [{"nome": f"Entorno_{k}", "material": "entorno", "vertices": v, "faces": f}
               for k, jan in janelas(ext_da_grade(longe), longe.passo).items()
               for v, f in [malha_entorno(longe, ext, centro, cfg.raio, jan)]]
    vm, fm = disco_mar(centro, raio_do_mar(cfg.raio, longe.passo), round(delta, 2))
    ...
    DESTINO_ENTORNO.write_text(json.dumps({"objetos": [
        *entorno, {"nome": "Mar", "material": "mar", "vertices": vm, "faces": fm},
    ]}), encoding="utf-8")
```

e o print usa `sum(len(o['faces']) for o in entorno)`.

Em `scripts/entorno/vegetacao.py`, a leitura do nível do mar deixa de depender da posição:

```python
    nivel = next(o for o in json.loads(DESTINO_ENTORNO.read_text(encoding="utf-8"))["objetos"]
                 if o["nome"] == "Mar")["vertices"][0][2]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q`
Expected: os testes novos passam. Os de `test_blender.py` que citam `"Entorno"` continuam passando (só mudam na Task 7).

- [ ] **Step 5: Commit**

```bash
git add scripts/entorno/tiles.py scripts/loteamento/terreno.py scripts/entorno/vegetacao.py tests/test_tiles.py tests/test_terreno.py
git commit -m "feat(tiles): janelas 2×2 em nós da grade; entorno em quatro pedaços"
```

---

### Task 2: Partição do platô

**Files:**
- Create: `scripts/loteamento/placa.py`
- Modify: `scripts/loteamento/cena.toml` (seção `[placa]`)
- Test: `tests/test_placa.py`

**Interfaces:**
- Consumes: `aninhar`, `simplificar` (`malha.py`).
- Produces: `PlacaCfg(alturas: dict[str, float], recuo_lote: float = 0.15, fundo: float = -1.0, fresta_max: float = 2.0)` com `PlacaCfg.carregar(caminho: Path)`; `partes(g) -> list[Polygon]`; `poligonos(aneis: list[list[Ponto]], tol: float = 0.0) -> BaseGeometry`; `particionar(plato, papeis: dict[str, BaseGeometry], lotes: dict[str, BaseGeometry], lagoa: BaseGeometry | None, cfg: PlacaCfg) -> dict[str, BaseGeometry]`, com chaves `Lagoa`, ids de lote, `Juntas`, `Calcadas`, `Verdes`, `Institucional`, `Fundo`, `APP`, `Pista`, `ChaoPlato` (só as não vazias, exceto lotes, que nunca faltam).

- [ ] **Step 1: Write the failing tests**

`tests/test_placa.py`:

```python
import itertools

import pytest
from shapely.geometry import Point, Polygon, box

from scripts.loteamento.placa import PlacaCfg, particionar, partes, poligonos

ALTURAS = {"Pista": 0.0, "ChaoPlato": 0.0, "Calcadas": 0.25, "Verdes": 0.25, "Institucional": 0.25,
           "Fundo": 0.25, "APP": 0.25, "Juntas": 0.25, "lote": 0.40, "Lagoa": -0.30}
CFG = PlacaCfg(alturas=ALTURAS)
PLATO = box(0, 0, 100, 100)


def _cenario():
    papeis = {
        "Vias": box(0, 35, 100, 65),
        "Calcadas": box(0, 35, 100, 42).union(box(0, 58, 100, 65)),
        "Verdes": box(50, 65, 100, 100),
    }
    lotes = {"Q01L01": box(10, 65, 30, 90), "Q01L02": box(40, 60, 60, 90)}  # o 2º invade calçada e verde
    return papeis, lotes


def test_pecas_nao_se_sobrepoem_e_cobrem_o_plato():
    papeis, lotes = _cenario()
    pecas = particionar(PLATO, papeis, lotes, None, CFG)
    for (a, ga), (b, gb) in itertools.combinations(pecas.items(), 2):
        assert ga.intersection(gb).area < 0.01, (a, b)
    assert sum(g.area for g in pecas.values()) == pytest.approx(PLATO.area, rel=1e-3)


def test_prioridade_lote_calcada_verde_pista():
    papeis, lotes = _cenario()
    pecas = particionar(PLATO, papeis, lotes, None, CFG)
    assert pecas["Pista"].area == pytest.approx(100 * 16, rel=1e-3)  # entre as calçadas
    assert pecas["Calcadas"].intersection(box(40, 60, 60, 65)).area < 0.01  # o lote ganhou da calçada


def test_lote_vira_recuo_e_junta():
    papeis, lotes = _cenario()
    pecas = particionar(PLATO, papeis, lotes, None, CFG)
    assert pecas["Q01L01"].area == pytest.approx(19.7 * 24.7, rel=1e-3)
    assert pecas["Juntas"].intersection(box(10, 65, 30, 90)).area == pytest.approx(500 - 19.7 * 24.7, rel=1e-3)


def test_lote_estreito_fica_sem_recuo():
    pecas = particionar(PLATO, {}, {"Q01L01": box(10, 10, 10.25, 30)}, None, CFG)
    assert pecas["Q01L01"].area == pytest.approx(0.25 * 20, rel=1e-3)


def test_lote_engolido_pela_lagoa_falha_com_o_nome():
    with pytest.raises(ValueError, match="Q01L01"):
        particionar(PLATO, {}, {"Q01L01": box(10, 10, 20, 20)}, box(0, 0, 50, 50), CFG)


def test_fresta_pequena_junto_da_via_vira_pista_e_o_resto_chao():
    papeis = {"Vias": box(0, 40, 100, 60), "Calcadas": box(0, 60, 99, 61.5),  # fresta de 1 × 1,5 m na ponta
              "Verdes": box(0, 61.5, 100, 100)}
    pecas = particionar(PLATO, papeis, {}, None, CFG)
    assert pecas["Pista"].area == pytest.approx(100 * 20 + 1.5, rel=1e-4)
    assert pecas["ChaoPlato"].area == pytest.approx(100 * 40, rel=1e-4)  # grande demais para fresta


def test_ilha_da_rotatoria_e_chao_nao_pista():
    anel = [(0.0, 40.0), (100.0, 40.0), (100.0, 60.0), (0.0, 60.0)]
    ilha = list(Point(50, 50).buffer(5).exterior.coords)[:-1]
    vias = poligonos([anel, ilha])
    pecas = particionar(PLATO, {"Vias": vias}, {}, None, CFG)
    assert pecas["Pista"].intersection(Point(50, 50).buffer(4)).area < 0.01
    assert pecas["ChaoPlato"].contains(Point(50, 50))


def test_partes_ignora_linhas_e_pontos():
    from shapely.geometry import GeometryCollection, LineString

    g = GeometryCollection([box(0, 0, 1, 1), LineString([(0, 0), (5, 5)]), Point(3, 3)])
    assert [p.area for p in partes(g)] == [1.0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_placa.py -q`
Expected: FAIL (`ModuleNotFoundError: scripts.loteamento.placa`).

- [ ] **Step 3: Implement**

`scripts/loteamento/placa.py`:

```python
"""Placa do loteamento: o platô partido em peças sem sobreposição e levantado em volume.

Cada metro quadrado do platô pertence a uma peça só, por prioridade; por isso nada briga na vista.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

import shapely
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .geometria import Ponto
from .malha import aninhar, simplificar

PRECISAO = 0.001  # m: a partição é arredondada a 1 mm, sem lascas numéricas
ORDEM = ["Calcadas", "Verdes", "Institucional", "Fundo", "APP"]  # depois da lagoa e dos lotes, antes da pista


@dataclass(frozen=True)
class PlacaCfg:
    alturas: dict[str, float]  # topo relativo à cota do platô, por peça; "lote" vale para todos os lotes
    recuo_lote: float = 0.15
    fundo: float = -1.0  # base das paredes (meio-fio, margem e saia)
    fresta_max: float = 2.0  # m²: fresta encostada na via vira pista

    @classmethod
    def carregar(cls, caminho: Path) -> "PlacaCfg":
        return cls(**tomllib.loads(caminho.read_text(encoding="utf-8"))["placa"])


def partes(g: BaseGeometry) -> list[Polygon]:
    """Só os polígonos com área (diferenças do shapely deixam linhas e pontos soltos)."""
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g] if g.area > 1e-6 else []
    return [p for q in g.geoms for p in partes(q)]


def _limpa(g: BaseGeometry) -> BaseGeometry:
    return unary_union(partes(shapely.set_precision(g, PRECISAO)))


def poligonos(aneis: list[list[Ponto]], tol: float = 0.0) -> BaseGeometry:
    """Anéis de uma layer → polígonos com furos (o anel de dentro é furo do de fora)."""
    aneis = [simplificar(a, tol) if tol else list(a) for a in aneis if len(a) >= 3]
    return unary_union([Polygon(e, furos).buffer(0) for e, furos in aninhar(aneis)])


def particionar(plato: BaseGeometry, papeis: dict[str, BaseGeometry], lotes: dict[str, BaseGeometry],
                lagoa: BaseGeometry | None, cfg: PlacaCfg) -> dict[str, BaseGeometry]:
    pecas: dict[str, BaseGeometry] = {}
    ocupado: list[BaseGeometry] = []

    def tomar(nome: str, g: BaseGeometry) -> BaseGeometry:
        g = _limpa(g.intersection(plato).difference(unary_union(ocupado)) if ocupado else g.intersection(plato))
        if not g.is_empty:
            pecas[nome] = g
            ocupado.append(g)
        return g

    if lagoa is not None:
        tomar("Lagoa", lagoa)
    for id_, g in lotes.items():
        if tomar(id_, g).is_empty:
            raise ValueError(f"lote {id_} sem área na placa (coberto pela lagoa ou fora do platô)")
    for papel in ORDEM:
        if papel in papeis:
            tomar(papel, papeis[papel])
    resto = _limpa(plato.difference(unary_union(ocupado)))
    pista = resto.intersection(papeis.get("Vias", Polygon()))
    frestas = [p for p in partes(resto.difference(pista))
               if p.area < cfg.fresta_max and p.buffer(0.01).intersects(pista)]
    tomar("Pista", unary_union([pista, *frestas]))
    tomar("ChaoPlato", plato)
    juntas = []
    for id_ in lotes:
        lote = pecas[id_]
        recuado = _limpa(lote.buffer(-cfg.recuo_lote, join_style="mitre"))
        if recuado.is_empty:
            continue  # estreito demais para o recuo: fica inteiro
        juntas.append(lote.difference(recuado))
        pecas[id_] = recuado
    if juntas:
        pecas["Juntas"] = _limpa(unary_union(juntas))
    return pecas
```

Em `scripts/loteamento/cena.toml`, no fim:

```toml
[placa]   # a placa em volume (scripts/loteamento/placa.py); alturas relativas à cota do platô
recuo_lote = 0.15   # m de cada lado: a junta entre lotes vizinhos tem o dobro
fundo = -1.0        # m, base das paredes: meio-fio, margem da lagoa e saia da borda
fresta_max = 2.0    # m², fresta entre peças encostada na via vira pista

[placa.alturas]
Pista = 0.0
ChaoPlato = 0.0
Calcadas = 0.25
Verdes = 0.25
Institucional = 0.25
Fundo = 0.25
APP = 0.25
Juntas = 0.25
lote = 0.40
Lagoa = -0.30
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_placa.py -q`
Expected: PASS. (`test_cfg_carrega_do_toml` em `test_cena.py` pode quebrar com a seção nova; corrija na Task 5, onde o `CenaCfg` muda.)

- [ ] **Step 5: Commit**

```bash
git add scripts/loteamento/placa.py scripts/loteamento/cena.toml tests/test_placa.py
git commit -m "feat(placa): partição do platô sem sobreposição, com recuo e junta dos lotes"
```

---

### Task 3: Volume da placa

**Files:**
- Modify: `scripts/loteamento/placa.py`
- Test: `tests/test_placa.py`

**Interfaces:**
- Consumes: `partes`, `PlacaCfg`, `particionar` (Task 2); `triangular` (`malha.py`).
- Produces: `aneis_orientados(p: Polygon) -> tuple[list[Ponto], list[list[Ponto]]]`; `topo(g, z: float) -> tuple[list[list[float]], list[list[int]]]` (faces com normal +z); `paredes(g, z_topo: float, z_base: float, cobertura: BaseGeometry) -> tuple[list[list[float]], list[list[int]]]` (normais para fora da peça); `altura(nome: str, cfg: PlacaCfg) -> float`; `montar_placa(pecas: dict, cfg: PlacaCfg, cota: float, materiais_lote: dict[str, str]) -> list[dict]` — objetos de cena `{"nome", "material", "vertices", "faces", "suave": False}`, e lotes com `"origem": [cx, cy, z_topo]`.

- [ ] **Step 1: Write the failing tests**

Acrescente a `tests/test_placa.py`:

```python
import numpy as np

from scripts.loteamento.placa import altura, montar_placa, paredes, topo


def _normais(v, f):
    v = np.array(v, dtype=float)
    return [np.cross(v[b] - v[a], v[c] - v[a]) for a, b, c in f]


def test_topo_plano_com_normal_para_cima_e_furo():
    g = box(0, 0, 10, 10).difference(box(4, 4, 6, 6))
    v, f = topo(g, 5.0)
    assert {p[2] for p in v} == {5.0}
    assert all(n[2] > 0 for n in _normais(v, f))
    assert sum(abs(n[2]) / 2 for n in _normais(v, f)) == pytest.approx(96.0)


def test_parede_so_onde_o_vizinho_nao_cobre_e_para_fora():
    a, b = box(0, 0, 10, 10), box(10, 0, 20, 10)  # b encosta no lado leste de a
    v, f = paredes(a, 0.25, -1.0, b)
    assert len(f) == 3 * 2  # oeste, sul, norte
    assert not any(abs(v[k][0] - 10) < 0.01 and abs(v[k + 2][0] - 10) < 0.01 for k in range(0, len(v), 4))
    centro = np.array([5.0, 5.0])
    for (i, j, k), n in zip(f, _normais(v, f)):
        meio = (np.array(v[i][:2]) + np.array(v[k][:2])) / 2
        assert np.dot(n[:2], meio - centro) > 0
    assert min(p[2] for p in v) == -1.0 and max(p[2] for p in v) == 0.25


def test_parede_do_furo_aponta_para_dentro_do_furo():
    g = box(0, 0, 10, 10).difference(box(4, 4, 6, 6))
    v, f = paredes(g, 0.0, -1.0, Polygon())
    for (i, j, k), n in zip(f, _normais(v, f)):
        meio = (np.array(v[i][:2]) + np.array(v[k][:2])) / 2
        if 3.9 < meio[0] < 6.1 and 3.9 < meio[1] < 6.1:
            assert np.dot(n[:2], np.array([5.0, 5.0]) - meio) > 0  # normal para o centro do furo


def test_montar_placa_materiais_origem_e_meio_fio():
    papeis, lotes = _cenario()
    pecas = particionar(PLATO, papeis, lotes, None, CFG)
    objs = {o["nome"]: o for o in montar_placa(pecas, CFG, 21.0, {"Q01L01": "lote_residencial",
                                                                   "Q01L02": "lote_uso_misto"})}
    assert objs["Pista"]["material"] == "vias" and objs["ChaoPlato"]["material"] == "terreno"
    assert objs["Q01L01"]["material"] == "lote_residencial" and objs["Juntas"]["material"] == "juntas"
    assert objs["Q01L01"]["origem"] == pytest.approx([20.0, 77.5, 21.4])
    assert all(o["suave"] is False for o in objs.values())
    assert max(p[2] for p in objs["Calcadas"]["vertices"]) == pytest.approx(21.25)
    assert altura("Q09L09", CFG) == 0.40
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_placa.py -q`
Expected: FAIL (`ImportError: cannot import name 'altura'`).

- [ ] **Step 3: Implement**

Acrescente a `scripts/loteamento/placa.py` (imports novos: `from shapely.geometry import LineString, Point`, `from shapely.geometry.polygon import orient`, `from shapely.strtree import STRtree`, `from .malha import triangular`):

```python
MATERIAL = {"Pista": "vias", "ChaoPlato": "terreno", "Calcadas": "calcadas", "Verdes": "verdes",
            "Institucional": "institucional", "Fundo": "fundo", "APP": "app", "Juntas": "juntas", "Lagoa": "agua"}


def aneis_orientados(p: Polygon) -> tuple[list[Ponto], list[list[Ponto]]]:
    p = orient(p, 1.0)  # externo anti-horário, furos horários: a peça fica sempre à esquerda
    return list(p.exterior.coords)[:-1], [list(i.coords)[:-1] for i in p.interiors]


def _ccw(a: Ponto, b: Ponto, c: Ponto) -> bool:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 0


def topo(g: BaseGeometry, z: float) -> tuple[list[list[float]], list[list[int]]]:
    vs: list[list[float]] = []
    fs: list[list[int]] = []
    for p in partes(g):
        ext, furos = aneis_orientados(p)
        v, t = triangular(ext, furos)
        base = len(vs)
        vs += [[round(x, 3), round(y, 3), round(z, 3)] for x, y in v]
        fs += [[base + a, base + b, base + c] if _ccw(v[a], v[b], v[c]) else [base + a, base + c, base + b]
               for a, b, c in t]
    return vs, fs


def _linhas(g: BaseGeometry) -> list[LineString]:
    if g.is_empty:
        return []
    if isinstance(g, LineString):
        return [g]
    return [l for q in getattr(g, "geoms", []) for l in _linhas(q)]


def paredes(g: BaseGeometry, z_topo: float, z_base: float,
            cobertura: BaseGeometry) -> tuple[list[list[float]], list[list[int]]]:
    """Parede vertical do topo à base no trecho do contorno que `cobertura` (as peças de topo igual
    ou mais alto) não encosta. A normal aponta para fora da peça."""
    cob = None if cobertura.is_empty else cobertura.buffer(0.005)
    vs: list[list[float]] = []
    fs: list[list[int]] = []
    for p in partes(g):
        for anel in [p.exterior, *p.interiors]:
            linha = LineString(anel.coords)
            for seg in _linhas(linha if cob is None else linha.difference(cob)):
                cs = list(seg.coords)
                for a, b in zip(cs, cs[1:]):
                    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    n = (dx * dx + dy * dy) ** 0.5
                    if n < 1e-6:
                        continue
                    if p.contains(Point(mx + dy / n * 0.01, my - dx / n * 0.01)):
                        a, b = b, a  # a direita de a→b tem de ser o lado de fora
                    k = len(vs)
                    vs += [[round(a[0], 3), round(a[1], 3), z_topo], [round(a[0], 3), round(a[1], 3), z_base],
                           [round(b[0], 3), round(b[1], 3), z_base], [round(b[0], 3), round(b[1], 3), z_topo]]
                    fs += [[k, k + 1, k + 2], [k, k + 2, k + 3]]
    return vs, fs


def altura(nome: str, cfg: PlacaCfg) -> float:
    return cfg.alturas["lote"] if nome.startswith("Q") else cfg.alturas[nome]


def montar_placa(pecas: dict[str, BaseGeometry], cfg: PlacaCfg, cota: float,
                 materiais_lote: dict[str, str]) -> list[dict]:
    nomes = list(pecas)
    arvore = STRtree([pecas[n] for n in nomes])
    objetos = []
    for nome in nomes:
        g, h = pecas[nome], altura(nome, cfg)
        vizinhos = [nomes[i] for i in arvore.query(g.buffer(0.01))
                    if nomes[i] != nome and altura(nomes[i], cfg) >= h]
        cobertura = unary_union([pecas[n] for n in vizinhos]) if vizinhos else Polygon()
        vt, ft = topo(g, cota + h)
        vp, fp = paredes(g, round(cota + h, 3), round(cota + cfg.fundo, 3), cobertura)
        obj = {"nome": nome, "material": materiais_lote.get(nome) or MATERIAL[nome],
               "vertices": vt + vp, "faces": ft + [[a + len(vt), b + len(vt), c + len(vt)] for a, b, c in fp],
               "suave": False}
        if nome.startswith("Q"):
            x0, y0, x1, y1 = g.bounds
            obj["origem"] = [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3), round(cota + h, 3)]
        objetos.append(obj)
    return objetos
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_placa.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/loteamento/placa.py tests/test_placa.py
git commit -m "feat(placa): topo plano, paredes por regra única (meio-fio, margem, saia) e pivô dos lotes"
```

---

### Task 4: Terreno perto com furo

**Files:**
- Create: `scripts/loteamento/chao.py`
- Test: `tests/test_chao.py`

**Interfaces:**
- Consumes: `Grade.cota_malha` (`relevo.py`), `da_janela` (`tiles.py`), `partes`, `aneis_orientados` (`placa.py`), `triangular` (`malha.py`).
- Produces: `malha_perto(grade: Grade, placa: BaseGeometry, janela: Ext) -> tuple[list[list[float]], list[list[int]]]`.

- [ ] **Step 1: Write the failing tests**

`tests/test_chao.py`:

```python
import numpy as np
import pytest
from shapely.geometry import Polygon, box

from scripts.loteamento.chao import malha_perto
from scripts.loteamento.relevo import Grade

GRADE = Grade(0.0, 0.0, 10.0, 11, 11, [[float(i + j) for i in range(11)] for j in range(11)])
PLACA = box(25, 25, 55, 55)
JANELA = (0.0, 0.0, 100.0, 100.0)


def _tris(v, f):
    return [[v[a], v[b], v[c]] for a, b, c in f]


def test_nenhum_triangulo_dentro_da_placa_e_area_certa():
    v, f = malha_perto(GRADE, PLACA, JANELA)
    tris = _tris(v, f)
    assert not any(PLACA.contains(Polygon([p[:2] for p in t]).centroid) for t in tris)
    area = sum(Polygon([p[:2] for p in t]).area for t in tris)
    assert area == pytest.approx(100 * 100 - 30 * 30, rel=1e-3)


def test_celula_longe_da_placa_e_a_da_grade():
    v, f = malha_perto(GRADE, PLACA, JANELA)
    tris = {tuple(sorted(tuple(p[:2]) for p in t)) for t in _tris(v, f)}
    assert tuple(sorted([(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])) in tris  # diagonal (i,j)-(i+1,j+1)
    assert tuple(sorted([(0.0, 0.0), (10.0, 10.0), (0.0, 10.0)])) in tris


def test_cotas_na_superficie_da_malha_e_normais_para_cima():
    v, f = malha_perto(GRADE, PLACA, JANELA)
    assert all(z == pytest.approx(GRADE.cota_malha(x, y), abs=0.01) for x, y, z in v)
    a = np.array(v, dtype=float)
    assert all(np.cross(a[j] - a[i], a[k] - a[i])[2] > 0 for i, j, k in f)


def test_janelas_repartem_o_terreno():
    total = sum(len(malha_perto(GRADE, PLACA, j)[1])
                for j in [(0, 0, 50, 50), (50, 0, 100, 50), (0, 50, 50, 100), (50, 50, 100, 100)])
    assert total == len(malha_perto(GRADE, PLACA, JANELA)[1])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_chao.py -q`
Expected: FAIL (`ModuleNotFoundError: scripts.loteamento.chao`).

- [ ] **Step 3: Implement**

`scripts/loteamento/chao.py`:

```python
"""Terreno perto com o furo da placa: a grade de 10 m de sempre (dois triângulos por célula, a mesma
superfície em que vegetação e prédios se assentam), menos a placa. Só a célula que cruza o contorno
é recortada; a borda do furo coincide com o contorno da placa por construção."""

from shapely.geometry import box
from shapely.geometry.base import BaseGeometry
from shapely.prepared import prep

from scripts.entorno.tiles import Ext, da_janela

from .malha import triangular
from .placa import aneis_orientados, partes
from .relevo import Grade


def malha_perto(grade: Grade, placa: BaseGeometry, janela: Ext) -> tuple[list[list[float]], list[list[int]]]:
    pp = prep(placa)
    indice: dict[tuple[float, float], int] = {}
    vs: list[list[float]] = []
    fs: list[list[int]] = []

    def no(x: float, y: float) -> int:
        k = (round(x, 3), round(y, 3))
        if k not in indice:
            indice[k] = len(vs)
            vs.append([k[0], k[1], round(grade.cota_malha(x, y), 2)])
        return indice[k]

    for j in range(grade.ny - 1):
        for i in range(grade.nx - 1):
            xa, ya = grade.x0 + i * grade.passo, grade.y0 + j * grade.passo
            xb, yb = xa + grade.passo, ya + grade.passo
            if not da_janela(janela, (xa + xb) / 2, (ya + yb) / 2):
                continue
            celula = box(xa, ya, xb, yb)
            if pp.contains(celula):
                continue
            if not pp.intersects(celula):
                a, b, c, d = no(xa, ya), no(xb, ya), no(xb, yb), no(xa, yb)
                fs += [[a, b, c], [a, c, d]]  # a diagonal de Grade.cota_malha
                continue
            for p in partes(celula.difference(placa)):
                ext, furos = aneis_orientados(p)
                v, t = triangular(ext, furos)
                ids = [no(x, y) for x, y in v]
                for a, b, c in t:
                    (xa_, ya_), (xb_, yb_), (xc_, yc_) = v[a], v[b], v[c]
                    ccw = (xb_ - xa_) * (yc_ - ya_) - (yb_ - ya_) * (xc_ - xa_) > 0
                    fs.append([ids[a], ids[b], ids[c]] if ccw else [ids[a], ids[c], ids[b]])
    return vs, fs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_chao.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/loteamento/chao.py tests/test_chao.py
git commit -m "feat(chao): terreno perto com o furo da placa, recortando só as células da borda"
```

---

### Task 5: Cena com a placa e o chão

**Files:**
- Modify: `scripts/loteamento/cena.py` (`CenaCfg`, `montar`, `main`; remove `_malha` e `_terreno`)
- Modify: `scripts/loteamento/cena.toml` (remove `[offsets]`, `max_aresta`, `fundo_lagoa`)
- Modify: `scripts/entorno/vegetacao.py` (offset dos canteiros)
- Test: `tests/test_cena.py` (reescrito), `tests/test_vegetacao.py`

**Interfaces:**
- Consumes: `PlacaCfg`, `poligonos`, `particionar`, `montar_placa` (Tasks 2–3); `malha_perto` (Task 4); `janelas`, `ext_da_grade` (Task 1).
- Produces: `CenaCfg(camadas, lagoa_camadas, lagoa_texto, tolerancia)`; `montar(msp, grade: Grade, lotes: list[dict], cfg: CenaCfg, placa_cfg: PlacaCfg, plato_aneis: list[list[Ponto]], janelas_: dict[str, Ext], e0: float, n0: float) -> dict`. `cache/cena/loteamento.json` passa a ter as peças da placa, `Juntas`, os lotes (com `origem`) e `Terreno_00…11`.

- [ ] **Step 1: Rewrite the tests**

Substitua de `CFG = CenaCfg(` até o fim de `tests/test_cena.py` por:

```python
from scripts.loteamento.placa import PlacaCfg

CFG = CenaCfg(camadas={"Vias": ["VIA"], "APP": ["APP"]}, lagoa_camadas=["APP"],
              lagoa_texto="LAGOA AZUL", tolerancia=0.05)
PLACA = PlacaCfg(alturas={"Pista": 0.0, "ChaoPlato": 0.0, "Calcadas": 0.25, "Verdes": 0.25,
                          "Institucional": 0.25, "Fundo": 0.25, "APP": 0.25, "Juntas": 0.25,
                          "lote": 0.40, "Lagoa": -0.30})
JANELAS = {"00": (-10.0, -10.0, 400.0, 200.0)}


def _ret(x, y, w, h):
    return [(E0 + x, N0 + y), (E0 + x + w, N0 + y), (E0 + x + w, N0 + y + h), (E0 + x, N0 + y + h)]


def _local(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


@pytest.fixture
def msp():
    doc = ezdxf.new()
    m = doc.modelspace()
    m.add_lwpolyline(_ret(0, 0, 100, 100), close=True, dxfattribs={"layer": "VIA"})
    m.add_circle((E0 + 50, N0 + 50), 10, dxfattribs={"layer": "VIA"})  # ilha da rotatória
    m.add_lwpolyline(_ret(200, 0, 100, 100), close=True, dxfattribs={"layer": "APP"})
    m.add_lwpolyline(_ret(230, 30, 40, 40), close=True, dxfattribs={"layer": "APP"})  # a lagoa
    m.add_text("LAGOA AZUL", dxfattribs={"layer": "TXT", "insert": (E0 + 250, N0 + 50)})
    return m


GRADE = Grade(-10.0, -10.0, 10.0, 40, 20, [[10.0] * 40 for _ in range(20)])
LOTES = [{"id": "Q01L01", "tipo": "residencial", "poligono": [[0, 0], [10, 0], [10, 20], [0, 20]]}]
PLATO = [_local(0, 0, 100, 100), _local(200, 0, 100, 100)]


def test_circulo_vira_anel(msp):
    aneis = aneis_da_layer(msp, ["VIA"], E0, N0)
    assert len(aneis) == 2
    assert sorted(round(area(a)) for a in aneis) == [314, 10000]


def test_lagoa_e_o_menor_poligono_com_o_texto(msp):
    assert round(area(achar_lagoa(msp, CFG, E0, N0))) == 1600


def test_montar_placa_lotes_e_terreno_em_janelas(msp):
    por_nome = {o["nome"]: o for o in montar(msp, GRADE, LOTES, CFG, PLACA, PLATO, JANELAS, E0, N0)["objetos"]}
    assert {"Pista", "APP", "Lagoa", "Q01L01", "Juntas", "ChaoPlato", "Terreno_00"} <= set(por_nome)
    assert por_nome["Q01L01"]["material"] == "lote_residencial"
    assert por_nome["Q01L01"]["origem"] == pytest.approx([5.0, 10.0, 10.4])
    assert max(p[2] for p in por_nome["Lagoa"]["vertices"]) == pytest.approx(9.7)
    assert por_nome["ChaoPlato"]["material"] == "terreno"  # a ilha da rotatória


def test_ilha_da_lagoa_e_app_e_o_resto_e_agua():
    doc = ezdxf.new()
    m = doc.modelspace()
    m.add_lwpolyline(_ret(230, 30, 40, 40), close=True, dxfattribs={"layer": "APP"})  # a lagoa
    m.add_lwpolyline(_ret(250, 50, 10, 10), close=True, dxfattribs={"layer": "APP"})  # ilha
    m.add_text("LAGOA AZUL", dxfattribs={"layer": "TXT", "insert": (E0 + 238, N0 + 38)})
    por_nome = {o["nome"]: o for o in montar(m, GRADE, LOTES, CFG, PLACA, PLATO, JANELAS, E0, N0)["objetos"]}
    from shapely.geometry import Polygon

    def area_topo(o, z):
        v = o["vertices"]
        return sum(Polygon([v[i][:2] for i in f]).area for f in o["faces"]
                   if all(abs(v[i][2] - z) < 1e-6 for i in f))

    assert area_topo(por_nome["APP"], 10.25) == pytest.approx(100, rel=0.01)
    assert area_topo(por_nome["Lagoa"], 9.7) == pytest.approx(1600 - 100, rel=0.01)


def test_terreno_nao_entra_na_placa(msp):
    from shapely.geometry import Polygon, box

    por_nome = {o["nome"]: o for o in montar(msp, GRADE, LOTES, CFG, PLACA, PLATO, JANELAS, E0, N0)["objetos"]}
    t = por_nome["Terreno_00"]
    placa = box(0, 0, 100, 100).union(box(200, 0, 300, 100))
    assert not any(placa.contains(Polygon([t["vertices"][i][:2] for i in f]).centroid) for f in t["faces"])


def test_cfg_carrega_do_toml():
    from scripts.comum.ambiente import RAIZ

    cfg = CenaCfg.carregar(RAIZ / "scripts" / "loteamento" / "cena.toml")
    placa = PlacaCfg.carregar(RAIZ / "scripts" / "loteamento" / "cena.toml")
    assert "Vias" in cfg.camadas
    assert placa.alturas["lote"] > placa.alturas["Calcadas"] > placa.alturas["Pista"] > placa.alturas["Lagoa"]
```

Em `tests/test_vegetacao.py`, acrescente:

```python
def test_canteiros_ficam_no_topo_dos_verdes():
    from scripts.comum.ambiente import RAIZ
    from scripts.entorno.vegetacao import OFFSET_CANTEIRO
    from scripts.loteamento.placa import PlacaCfg

    assert OFFSET_CANTEIRO == PlacaCfg.carregar(RAIZ / "scripts" / "loteamento" / "cena.toml").alturas["Verdes"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cena.py tests/test_vegetacao.py -q`
Expected: FAIL (`CenaCfg.__init__() got an unexpected keyword` / `montar()` com assinatura velha / `OFFSET_CANTEIRO` inexistente).

- [ ] **Step 3: Implement**

Em `scripts/loteamento/cena.py`:

```python
@dataclass(frozen=True)
class CenaCfg:
    camadas: dict[str, list[str]]
    lagoa_camadas: list[str]
    lagoa_texto: str
    tolerancia: float

    @classmethod
    def carregar(cls, caminho: Path) -> "CenaCfg":
        d = tomllib.loads(caminho.read_text(encoding="utf-8"))
        return cls(**{k: d[k] for k in ("camadas", "lagoa_camadas", "lagoa_texto", "tolerancia")})
```

Apague `_malha` e `_terreno`. Novo `montar`:

```python
def montar(msp, grade: Grade, lotes: list[dict], cfg: CenaCfg, placa_cfg: PlacaCfg,
           plato_aneis: list[list[Ponto]], janelas_: dict[str, Ext], e0: float, n0: float) -> dict:
    plato = poligonos(plato_aneis)
    cota = grade.cota_malha(*plato.representative_point().coords[0])  # o platô é plano
    lagoa = achar_lagoa(msp, cfg, e0, n0)
    papeis = {}
    for papel, layers in cfg.camadas.items():
        aneis = [a for a in aneis_da_layer(msp, layers, e0, n0) if a != lagoa]  # a lagoa é peça própria
        if aneis:
            papeis[papel] = poligonos(aneis, cfg.tolerancia)
    agua = None
    if lagoa:
        # a ilha (anel de APP dentro da lagoa) é APP; a APP que contém a lagoa perde para a água pela prioridade
        ilhas = [Polygon(a).buffer(0) for ls in [cfg.lagoa_camadas] for a in aneis_da_layer(msp, ls, e0, n0)
                 if a != lagoa and contem(lagoa, a[0]) and area(a) < area(lagoa)]
        agua = Polygon(simplificar(lagoa, cfg.tolerancia)).buffer(0).difference(unary_union(ilhas))
    lotes_g = {l["id"]: Polygon(l["poligono"]).buffer(0) for l in lotes}
    pecas = particionar(plato, papeis, lotes_g, agua, placa_cfg)
    objetos = montar_placa(pecas, placa_cfg, cota, {l["id"]: f"lote_{l['tipo']}" for l in lotes})
    for k, jan in janelas_.items():
        v, f = malha_perto(grade, plato, jan)
        if f:
            objetos.append({"nome": f"Terreno_{k}", "material": "terreno", "vertices": v, "faces": f})
    return {"objetos": objetos}
```

Imports: `from shapely.geometry import Polygon`, `from shapely.ops import unary_union`, `from .geometria import area, contem` (junto aos que já existem), `from scripts.entorno.tiles import Ext, ext_da_grade, janelas`, `from .chao import malha_perto`, `from .placa import PlacaCfg, montar_placa, particionar, poligonos`; tire `drapear`, `refinar`, `triangular`, `aninhar`, `mascara` e `np` se ficarem sem uso.

Novo `main` (import local de `terreno` para não criar ciclo: `terreno.py` importa de `cena.py`):

```python
def main() -> int:
    from .terreno import DESTINO_LONGE, TerrenoCfg, aneis_do_plato  # terreno importa cena: import local

    sys.stdout.reconfigure(encoding="utf-8")
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    grade = Grade.de_json(json.loads(TERRENO_JSON.read_text(encoding="utf-8")))
    longe = Grade.de_json(json.loads(DESTINO_LONGE.read_text(encoding="utf-8")))
    msp = ezdxf.readfile(DXF).modelspace()
    plato = aneis_do_plato(msp, TerrenoCfg.carregar(CFG_TOML), lotes, e0, n0)
    cena = montar(msp, grade, lotes, CenaCfg.carregar(CFG_TOML), PlacaCfg.carregar(CFG_TOML), plato,
                  janelas(ext_da_grade(longe), longe.passo), e0, n0)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(cena), encoding="utf-8")
    tris = {o["nome"]: len(o["faces"]) for o in cena["objetos"]}
    lotes_n = sum(1 for n in tris if n.startswith("Q"))
    print(f"{len(tris)} objetos ({lotes_n} lotes) · {sum(tris.values())} triângulos · "
          + ", ".join(f"{n} {t}" for n, t in tris.items() if not n.startswith("Q")))
    return 0
```

Em `scripts/loteamento/cena.toml`, apague `max_aresta`, `fundo_lagoa` e a seção `[offsets]` inteira (comentário incluído).

Em `scripts/entorno/vegetacao.py`, no topo do módulo:

```python
OFFSET_CANTEIRO = PlacaCfg.carregar(CFG_TOML).alturas["Verdes"]  # coqueiro no topo do verde da placa
```

com `from scripts.loteamento.placa import PlacaCfg`, e troque `offset=0.08` por `offset=OFFSET_CANTEIRO`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q`
Expected: PASS (exceto os de `test_blender.py` que dependem de `com_mapa`, ainda inalterados e passando).

- [ ] **Step 5: Gerar a cena real e conferir os números**

Run: `uv run python -m scripts.loteamento.terreno && uv run python -m scripts.loteamento.cena`
Expected: saída 0; "355+ objetos (347 lotes)"; `Pista`, `Calcadas`, `Verdes`, `Juntas`, `ChaoPlato`, `Lagoa`, `Terreno_00…11` listados. Se um lote falhar com "sem área na placa", pare e reporte o id (não contorne).

- [ ] **Step 6: Commit**

```bash
git add scripts/loteamento/cena.py scripts/loteamento/cena.toml scripts/entorno/vegetacao.py tests/test_cena.py tests/test_vegetacao.py
git commit -m "feat(cena): loteamento como placa em volume sobre o terreno com furo, em quatro janelas"
```

---

### Task 6: Mapa do chão em tiles

**Files:**
- Modify: `scripts/entorno/extrair.py` (`EntornoCfg`)
- Modify: `scripts/entorno/entorno.toml`
- Modify: `scripts/entorno/preparar.py` (`gerar_tiles`, `main`)
- Test: `tests/test_preparar.py`, `tests/test_entorno_extrair.py`

**Interfaces:**
- Consumes: `janelas`, `com_margem` (Task 1); `rasterizar` (`mapa.py`).
- Produces: `EntornoCfg(..., tile_px: int, tile_margem_px: int = 2, masterplan: bool = True, masterplan_saturacao: float = 0.35, masterplan_opacidade: float = 0.55)`; `gerar_tiles(camadas, ext: Ext, passo: float, px: int, margem_px: int, pasta: Path, pos=None) -> dict[str, dict]` com `{k: {"arquivo", "ext", "janela", "px"}}`; `pos(img, ext_m) -> Image` é o gancho do masterplan (Task 8). `cache/entorno/mapa.json` = `{"tiles": {...}}`.

- [ ] **Step 1: Write the failing tests**

Em `tests/test_entorno_extrair.py`, troque `mapa_px=256` por `tile_px=256`.

Em `tests/test_preparar.py`:

```python
def test_tiles_sem_costura_na_linha_de_corte(tmp_path):
    from PIL import Image

    from scripts.entorno.preparar import gerar_tiles

    faixa = Polygon([(-100, -5), (100, -5), (100, 5), (-100, 5)])  # cruza a linha vertical x = 0
    tiles = gerar_tiles([("via_principal", faixa)], (-120.0, -120.0, 120.0, 120.0), 30.0, 64, 2, tmp_path)
    assert sorted(tiles) == ["00", "01", "10", "11"]

    def cor(k, x, y):
        t = tiles[k]
        x0, y0, x1, y1 = t["ext"]
        img = Image.open(t["arquivo"]).convert("RGB")
        return img.getpixel((int((x - x0) / (x1 - x0) * img.width), int((y1 - y) / (y1 - y0) * img.height)))

    # o mesmo ponto do mundo, na margem do vizinho, tem a mesma cor dos dois lados
    for x in (-0.5, 0.5):
        a, b = cor("01", x, 2.0), cor("11", x, 2.0)
        assert sum(abs(p - q) for p, q in zip(a, b)) < 30
    assert all(max(Image.open(t["arquivo"]).size) == 64 for t in tiles.values())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_preparar.py tests/test_entorno_extrair.py -q`
Expected: FAIL (`cannot import name 'gerar_tiles'`; `unexpected keyword argument 'tile_px'`).

- [ ] **Step 3: Implement**

`EntornoCfg` em `scripts/entorno/extrair.py`:

```python
@dataclass(frozen=True)
class EntornoCfg:
    raio_vias: float
    raio_faixas: float
    raio_predios: float
    raio_vegetacao: float
    raio_malha_regional: float
    tile_px: int
    tile_margem_px: int = 2
    masterplan: bool = True
    masterplan_saturacao: float = 0.35
    masterplan_opacidade: float = 0.55
```

`scripts/entorno/entorno.toml`: troque a linha `mapa_px` por

```toml
tile_px = 4096              # lado maior de cada um dos 4 tiles do chão (~1 m/px no recorte de 8 km)
tile_margem_px = 2          # pixels a mais de borda: o filtro da GPU não abre costura entre tiles
masterplan = false          # fases 2–10 pintadas em segundo plano (liga na Task 8 do Plano 3d)
masterplan_saturacao = 0.35
masterplan_opacidade = 0.55
```

Em `scripts/entorno/preparar.py`, apague `MAPA_JPG` e acrescente:

```python
def gerar_tiles(camadas, ext: Ext, passo: float, px: int, margem_px: int, pasta: Path, pos=None) -> dict[str, dict]:
    """Um JPEG por janela, com `margem_px` de borda; `pos(img, ext_m)` pinta por cima (o masterplan)."""
    tiles = {}
    for k, jan in janelas(ext, passo).items():
        ext_m = com_margem(jan, px, margem_px)
        img = rasterizar(camadas, ext_m, px)
        if pos is not None:
            img = pos(img, ext_m)
        arquivo = pasta / f"mapa_{k}.jpg"
        img.save(arquivo, quality=85)
        tiles[k] = {"arquivo": str(arquivo), "ext": list(ext_m), "janela": list(jan), "px": list(img.size)}
    return tiles
```

(imports: `from pathlib import Path`, `from .tiles import Ext, com_margem, janelas`). No `main`, troque as três linhas do mapa por:

```python
    tiles = gerar_tiles(camadas, ext, longe["passo"], cfg.tile_px, cfg.tile_margem_px, CACHE)
    MAPA_JSON.write_text(json.dumps({"tiles": tiles}), encoding="utf-8")
```

e o print: `f"tiles {len(tiles)} × {cfg.tile_px} px ({(ext[2] - ext[0]) / 2 / cfg.tile_px:.2f} m/px) · "`. Apague `cache/entorno/mapa.jpg` (velho).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q`
Expected: PASS, exceto `test_blender.py::test_com_mapa…` se ele ler `mapa.json` real (não lê; usa dict fixo) — deve passar.

- [ ] **Step 5: Gerar os tiles reais**

Run: `uv run python -m scripts.entorno.preparar`
Expected: 4 arquivos `cache/entorno/mapa_00.jpg … mapa_11.jpg`, ≈1 m/px; abra um com Read e confira vias e áreas.

- [ ] **Step 6: Commit**

```bash
git add scripts/entorno/extrair.py scripts/entorno/entorno.toml scripts/entorno/preparar.py tests/test_preparar.py tests/test_entorno_extrair.py
git commit -m "feat(entorno): mapa do chão em 4 tiles de 4096 px com margem contra costura"
```

---

### Task 7: Blender — tiles, pivô e peças da placa

**Files:**
- Modify: `scripts/loteamento/blender.py` (`com_tiles`, `OBJETOS_ENTORNO`, `main`)
- Modify: `scripts/blender/gerar_loteamento.py` (`MATERIAIS`, `material_textura`, `construir`, `previa`)
- Test: `tests/test_blender.py`

**Interfaces:**
- Consumes: `mapa.json` `{"tiles": …}` (Task 6); objetos de cena com `origem` e `suave` (Task 3); `Entorno_ij`/`Terreno_ij` (Tasks 1, 5).
- Produces: `com_tiles(dados: dict, tiles: dict[str, dict], prefixos: tuple[str, ...]) -> dict`; `OBJETOS_ENTORNO = ("Entorno_00", "Entorno_01", "Entorno_10", "Entorno_11", "Mar", "ViasPrincipais", "Predios")`; nó de lote no GLB com `translation` = origem em (x, z, −y).

- [ ] **Step 1: Write the failing tests**

Em `tests/test_blender.py`: troque `com_mapa` por `com_tiles` no import; substitua `test_com_mapa_poe_textura_so_nos_nomes_pedidos`, `test_conferir_entorno_acusa_peso` e `test_conferir_entorno_exige_os_objetos_novos` por:

```python
ENTORNO_OK = ["Entorno_00", "Entorno_01", "Entorno_10", "Entorno_11", "Mar", "ViasPrincipais", "Predios"]


def test_com_tiles_poe_a_imagem_do_tile_pelo_sufixo():
    dados = {"objetos": [{"nome": "Terreno_10", "material": "terreno"}, {"nome": "Q01L01", "material": "x"},
                         {"nome": "Mar", "material": "mar"}]}
    tiles = {"10": {"arquivo": "C:/m10.jpg", "ext": [0, 0, 10, 10], "janela": [0, 0, 9, 9], "px": [8, 8]}}
    novo = com_tiles(dados, tiles, ("Terreno",))
    assert novo["objetos"][0]["textura"] == {"arquivo": "C:/m10.jpg", "ext": [0, 0, 10, 10]}
    assert novo["objetos"][0]["material"] == "chao"
    assert "textura" not in novo["objetos"][1] and "textura" not in novo["objetos"][2]
    assert "textura" not in dados["objetos"][0]


def test_conferir_entorno_exige_os_quatro_pedacos_e_o_peso():
    assert conferir_entorno(ENTORNO_OK, 5.0) == []
    assert conferir_entorno(ENTORNO_OK, 8.4) == ["entorno.glb com 8.4 MB (alvo 8.0 MB)"]
    assert conferir_entorno(["Entorno_00", "Mar", "ViasPrincipais", "Predios"], 5.0) == [
        f"objeto do entorno faltando no GLB: Entorno_{k}" for k in ("01", "10", "11")]


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_lote_sai_com_pivo_no_centro(tmp_path):
    cena = {"objetos": [{"nome": "Q01L01", "material": "lote_residencial", "suave": False, "origem": [5.0, 10.0, 21.4],
                         "vertices": [[0, 0, 21.4], [10, 0, 21.4], [10, 20, 21.4], [0, 20, 21.4]],
                         "faces": [[0, 1, 2], [0, 2, 3]]}]}
    (tmp_path / "c.json").write_text(json.dumps(cena), encoding="utf-8")
    rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / "c.json"), str(tmp_path / "c.blend"), str(tmp_path / "c.glb"))
    dados = (tmp_path / "c.glb").read_bytes()
    gltf = json.loads(dados[20:20 + struct.unpack_from("<I", dados, 12)[0]])
    no = next(n for n in gltf["nodes"] if n["name"] == "Q01L01")
    assert no["translation"] == pytest.approx([5.0, 21.4, -10.0], abs=1e-4)
```

No `test_textura_vira_uv_e_imagem_no_glb`, troque `"Entorno"` por `"Entorno_00"`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_blender.py -q`
Expected: FAIL (`cannot import name 'com_tiles'`; pivô em `[0, 0, 0]`).

- [ ] **Step 3: Implement**

`scripts/loteamento/blender.py`:

```python
OBJETOS_ENTORNO = ("Entorno_00", "Entorno_01", "Entorno_10", "Entorno_11", "Mar", "ViasPrincipais", "Predios")


def com_tiles(dados: dict, tiles: dict[str, dict], prefixos: tuple[str, ...]) -> dict:
    """Cópia da cena com o chão pintado: `<prefixo>_<k>` recebe a imagem do tile k (material `chao`)."""
    def textura(nome: str) -> dict | None:
        pre, _, k = nome.rpartition("_")
        t = tiles.get(k) if pre in prefixos else None
        return {"arquivo": t["arquivo"], "ext": t["ext"]} if t else None

    return {"objetos": [{**o, "material": "chao", "textura": t} if (t := textura(o["nome"])) else o
                        for o in dados["objetos"]]}
```

Apague `com_mapa`. No `main`:

```python
    tiles = ler(MAPA_JSON)["tiles"]
    cena_entorno.write_text(json.dumps(com_tiles(juntar_cenas(ler(ENTORNO_JSON), ler(DETALHE)), tiles, ("Entorno",))),
                            encoding="utf-8")
    cena_lote.write_text(json.dumps(com_tiles(ler(CENA_JSON), tiles, ("Terreno",))), encoding="utf-8")
```

`scripts/blender/gerar_loteamento.py`:

- Em `MATERIAIS`, acrescente `"juntas": ((0.72, 0.70, 0.66), 0.9),`.
- `material_textura`: o nome passa a ser por arquivo, para cada tile ter o seu:

```python
def material_textura(arquivo: str) -> bpy.types.Material:
    """Chão pintado: a imagem do tile na cor base (o glTF leva a imagem embutida). Um material por tile."""
    nome = "chao_" + Path(arquivo).stem
```

- Em `construir`, antes de `me.from_pydata`:

```python
        ox, oy, oz = o.get("origem", (0.0, 0.0, 0.0))
        verts = [(x - ox, y - oy, z - oz) for x, y, z in o["vertices"]]
```

  use `me.from_pydata(verts, [], o["faces"])`; o UV do tile continua pelas coordenadas absolutas: troque `co = me.vertices[...].co` por `x, y = o["vertices"][loop.vertex_index][:2]` e use `x`, `y` na fórmula; depois de criar o objeto, `ob.location = (ox, oy, oz)`.
- Em `previa` e `_caixa`, use coordenadas de mundo: troque cada `v.co` por `ob.matrix_world @ v.co` (para isso, monte as listas como `[ob.matrix_world @ v.co for ob in … for v in ob.data.vertices]`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 5: Gerar tudo e olhar as prévias**

Run: `uv run python -m scripts.entorno.vegetacao && uv run python -m scripts.loteamento.blender`
Expected: saída 0; `entorno.glb` e `loteamento.glb` ≤ 8 MB; 347 lotes. Leia com Read `cache/cena/previa.png`, `previa-perto.png`, `previa-lagoa.png`, `previa-entorno.png`, e confira:
- nenhum serrilhado na via de acesso norte nem entre via, calçada e verde;
- meio-fio e juntas dos lotes com sombra na vista perto;
- borda da placa lida como bandeja sobre o talude, sem fresta para o terreno;
- chão dos tiles sem costura visível nas linhas x = −30 e y = 60;
- coqueiros dos canteiros sobre os verdes.

Se algo falhar, corrija o script responsável e rode de novo; não edite o `.blend`.

- [ ] **Step 6: Commit**

```bash
git add scripts/loteamento/blender.py scripts/blender/gerar_loteamento.py tests/test_blender.py
git commit -m "feat(blender): chão em tiles, pivô dos lotes e peças da placa sem suavização"
```

---

### Task 8: Masterplan das fases 2–10 em segundo plano

**Files:**
- Create: `scripts/entorno/masterplan.py`
- Modify: `scripts/entorno/preparar.py` (gancho `pos`), `scripts/entorno/entorno.toml` (`masterplan = true`), `pyproject.toml` (PyMuPDF)
- Test: `tests/test_masterplan.py`

**Interfaces:**
- Consumes: `gerar_tiles(..., pos=...)` (Task 6); `aneis_da_layer` (`cena.py`); `TerrenoCfg`, `aneis_do_plato` (`terreno.py`).
- Produces: `Semelhanca(s, theta, tx, ty)` com `.aplicar(pts)` e `.inversa(pts)`; `amostrar(contorno: np.ndarray, passo: float) -> np.ndarray`; `umeyama(a, b) -> Semelhanca`; `registrar(origem: np.ndarray, destino: np.ndarray, passo: float = 2.0, iteracoes: int = 50) -> tuple[Semelhanca, float]`; `poligonal_gleba(msp, e0, n0, ref: tuple[float, float]) -> list[Ponto]`; `escolher_contorno(caminhos: list[np.ndarray], alvo: np.ndarray) -> np.ndarray`; `pintar(tile, ext_m, mp_img, meta: dict, mascara, saturacao: float, opacidade: float) -> Image`; `cache/entorno/masterplan.png` + `masterplan.json` `{"arquivo", "clip", "px_por_pt", "transf": {s, theta, tx, ty}, "residuo_m", "gleba"}`.

- [ ] **Step 1: Dependência**

Run: `uv add pymupdf`
Expected: `pyproject.toml` com `pymupdf`; `uv run python -c "import fitz"` sem erro.

- [ ] **Step 2: Sondagem do contorno no PDF (não comitar)**

Rode no scratchpad, com o caminho do PDF em `TERRENO_DIR/2-LEVANTAMENTOS/PLANTAS_BASE/MASTER URBANO.pdf`, página índice 4 ("MASTERPLAN"):

```python
import fitz, numpy as np
from shapely.geometry import Polygon
p = fitz.open(PDF)[4]
cands = []
for d in p.get_drawings():
    pts = []
    for it in d["items"]:
        if it[0] == "l": pts += [it[1], it[2]]
        elif it[0] == "c": pts += [it[1], it[4]]
    if len(pts) >= 50:
        a = np.array([(q.x, q.y) for q in pts])
        if d.get("closePath") or np.hypot(*(a[0] - a[-1])) < 0.5:
            g = Polygon(a).buffer(0)
            cands.append((g.area, len(a), 4 * np.pi * g.area / g.length ** 2, d.get("color"), g.bounds))
for c in sorted(cands, reverse=True)[:15]: print(c)
```

Compare com a poligonal do DWG (674 vértices, compacidade `4πA/P²` = 4π·3.493.048/9903,8² ≈ 0,447). Expected: um candidato com compacidade ≈ 0,45 entre os de maior área. **Se nenhum casar** (contorno partido em vários caminhos), pare: a Task 8 é opcional pela spec; deixe `masterplan = false`, registre o achado no relatório e siga para a Task 9.

- [ ] **Step 3: Write the failing tests**

`tests/test_masterplan.py`:

```python
import math

import numpy as np
import pytest
from PIL import Image
from shapely.geometry import Polygon, box

from scripts.entorno.masterplan import Semelhanca, escolher_contorno, pintar, poligonal_gleba, registrar


def _estrela(n=120):
    """Contorno radial sem simetria de rotação nem autointerseção."""
    ts = [2 * math.pi * k / n for k in range(n)]
    return np.array([((1000 + 300 * math.sin(3 * t) + 150 * math.cos(5 * t + 0.7)) * math.cos(t),
                      (1000 + 300 * math.sin(3 * t) + 150 * math.cos(5 * t + 0.7)) * math.sin(t)) for t in ts])


def test_registro_devolve_a_semelhanca_conhecida():
    destino = _estrela()
    t = Semelhanca(s=6.75, theta=math.radians(5), tx=100.0, ty=-50.0)
    origem = t.inversa(destino)  # o contorno "no PDF"
    achada, residuo = registrar(origem, destino)
    assert achada.s == pytest.approx(6.75, rel=1e-3)
    assert math.degrees(achada.theta) == pytest.approx(5.0, abs=0.05)
    assert (achada.tx, achada.ty) == pytest.approx((100.0, -50.0), abs=1.0)
    assert residuo < 0.5


def test_inversa_desfaz_aplicar():
    t = Semelhanca(2.0, 0.7, 10.0, -3.0)
    p = np.array([[1.0, 2.0], [-5.0, 4.0]])
    assert t.inversa(t.aplicar(p)) == pytest.approx(p)


def test_escolhe_o_contorno_com_a_forma_da_gleba():
    alvo = _estrela()
    quadrado = np.array([[0, 0], [3000, 0], [3000, 3000], [0, 3000]], dtype=float)
    parecido = Semelhanca(0.1, 1.0, 5.0, 5.0).aplicar(alvo)
    assert escolher_contorno([quadrado, parecido], alvo) is parecido


def test_poligonal_e_a_copia_que_contem_a_referencia():
    import ezdxf

    doc = ezdxf.new()
    m = doc.modelspace()
    anel = [(100 * math.cos(2 * math.pi * k / 674), 100 * math.sin(2 * math.pi * k / 674)) for k in range(674)]
    for dx in (0.0, 5000.0):
        m.add_lwpolyline([(x + dx + 1000, y + 1000) for x, y in anel], close=True, dxfattribs={"layer": "POLIGONAL"})
    g = poligonal_gleba(m, 1000.0, 1000.0, (0.0, 0.0))
    assert len(g) == 674 and Polygon(g).contains(Polygon([(-1, -1), (1, -1), (1, 1)]))


def test_pintar_so_dentro_da_mascara_e_apagado():
    tile = Image.new("RGB", (100, 100), (219, 204, 173))
    mp = Image.new("RGB", (100, 100), (255, 0, 0))
    meta = {"clip": [0, 0, 100, 100], "px_por_pt": 1.0, "transf": {"s": 1.0, "theta": 0.0, "tx": 0.0, "ty": 0.0}}
    # PDF com y para baixo: o ponto do mundo (x, y) é (x, -y) no PDF; a imagem cobre y de 0 a -100
    ext = (0.0, -100.0, 100.0, 0.0)
    out = pintar(tile, ext, mp, meta, box(0, -100, 50, 0), saturacao=0.35, opacidade=0.55)
    esq, dir_ = out.getpixel((25, 50)), out.getpixel((75, 50))
    assert dir_ == (219, 204, 173)
    assert esq != (219, 204, 173) and esq[0] < 255  # misturado, não vermelho puro
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_masterplan.py -q`
Expected: FAIL (`ModuleNotFoundError: scripts.entorno.masterplan`).

- [ ] **Step 5: Implement**

`scripts/entorno/masterplan.py`:

```python
"""Masterplan das fases 2–10 pintado no chão, em segundo plano.

Fonte: página 5 ("MASTERPLAN") do MASTER URBANO.pdf (plano b), em vetor. O registro é a semelhança
que leva a poligonal desenhada no PDF à poligonal do DWG R05. O PDF tem y para baixo: o contorno
entra como (x, −y), senão a semelhança teria de ser um espelho.

Uso: uv run python -m scripts.entorno.masterplan
"""

import json
import math
import sys
from dataclasses import asdict, dataclass

import ezdxf
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from scipy.spatial import cKDTree
from shapely.geometry import Polygon

from scripts.comum.ambiente import RAIZ, terreno_dir
from scripts.loteamento.cena import DXF as DXF_VENDA
from scripts.loteamento.cena import aneis_da_layer
from scripts.loteamento.geometria import Ponto, centroide
from scripts.loteamento.placa import partes

from .extrair import CACHE

PDF = "2-LEVANTAMENTOS/PLANTAS_BASE/MASTER URBANO.pdf"
PAGINA = 4  # a 5ª, "MASTERPLAN"
DXF_R05 = RAIZ / "cache" / "dxf" / "masterplan-r05.dxf"
PNG = CACHE / "masterplan.png"
META = CACHE / "masterplan.json"
PX_POR_M = 2.0  # resolução do raster: 0,5 m/px, o dobro dos tiles
RESIDUO_MAX = 2.0  # m, mediana


@dataclass(frozen=True)
class Semelhanca:
    s: float
    theta: float
    tx: float
    ty: float

    def _r(self) -> np.ndarray:
        c, s = math.cos(self.theta), math.sin(self.theta)
        return np.array([[c, -s], [s, c]])

    def aplicar(self, pts: np.ndarray) -> np.ndarray:
        return self.s * np.asarray(pts, dtype=float) @ self._r().T + [self.tx, self.ty]

    def inversa(self, pts: np.ndarray) -> np.ndarray:
        return (np.asarray(pts, dtype=float) - [self.tx, self.ty]) @ self._r() / self.s


def amostrar(contorno: np.ndarray, passo: float) -> np.ndarray:
    fechado = np.vstack([contorno, contorno[:1]])
    seg = np.diff(fechado, axis=0)
    comp = np.hypot(seg[:, 0], seg[:, 1])
    acum = np.concatenate([[0.0], np.cumsum(comp)])
    t = np.arange(0.0, acum[-1], passo)
    i = np.clip(np.searchsorted(acum, t, side="right") - 1, 0, len(seg) - 1)
    f = ((t - acum[i]) / np.where(comp[i] > 0, comp[i], 1.0))[:, None]
    return fechado[i] + seg[i] * f


def umeyama(a: np.ndarray, b: np.ndarray) -> Semelhanca:
    """Semelhança de mínimos quadrados a → b, sem espelho."""
    ma, mb = a.mean(0), b.mean(0)
    da, db = a - ma, b - mb
    u, d, vt = np.linalg.svd(db.T @ da / len(a))
    sinal = np.diag([1.0, np.sign(np.linalg.det(u @ vt))])
    r = u @ sinal @ vt
    s = float(np.trace(np.diag(d) @ sinal) / (da ** 2).sum(1).mean())
    t = mb - s * r @ ma
    return Semelhanca(s, math.atan2(r[1, 0], r[0, 0]), float(t[0]), float(t[1]))


def registrar(origem: np.ndarray, destino: np.ndarray, passo: float = 2.0,
              iteracoes: int = 50) -> tuple[Semelhanca, float]:
    s0 = math.sqrt(Polygon(destino).area / Polygon(origem).area)
    dest = amostrar(destino, passo)
    orig = amostrar(origem, passo / s0)
    arvore = cKDTree(dest)
    co, cd = orig.mean(0), dest.mean(0)
    melhor, erro = None, math.inf
    for graus in range(360):
        r = math.radians(graus)
        c, s = math.cos(r), math.sin(r)
        t = cd - s0 * np.array([[c, -s], [s, c]]) @ co
        cand = Semelhanca(s0, r, float(t[0]), float(t[1]))
        e = float(np.median(arvore.query(cand.aplicar(orig))[0]))
        if e < erro:
            melhor, erro = cand, e
    for _ in range(iteracoes):
        _, i = arvore.query(melhor.aplicar(orig))
        melhor = umeyama(orig, dest[i])
    return melhor, float(np.median(arvore.query(melhor.aplicar(orig))[0]))


def _compacidade(c: np.ndarray) -> float:
    g = Polygon(c).buffer(0)
    return 4 * math.pi * g.area / g.length ** 2


def escolher_contorno(caminhos: list[np.ndarray], alvo: np.ndarray) -> np.ndarray:
    """O caminho cuja forma (compacidade, invariante à semelhança) mais se parece com a da gleba,
    entre os 10 de maior área."""
    grandes = sorted(caminhos, key=lambda c: Polygon(c).buffer(0).area, reverse=True)[:10]
    ka = _compacidade(alvo)
    return min(grandes, key=lambda c: abs(_compacidade(c) - ka))


def caminhos_fechados(pagina, min_pontos: int = 50) -> list[np.ndarray]:
    saida = []
    for d in pagina.get_drawings():
        pts = []
        for it in d["items"]:
            if it[0] == "l":
                pts += [it[1], it[2]]
            elif it[0] == "c":
                pts += [it[1], it[4]]
        if len(pts) < min_pontos:
            continue
        a = np.array([(q.x, q.y) for q in pts])
        if d.get("closePath") or math.hypot(*(a[0] - a[-1])) < 0.5:
            saida.append(a)
    return saida


def poligonal_gleba(msp, e0: float, n0: float, ref: Ponto) -> list[Ponto]:
    """A cópia da poligonal da gleba (o R05 a repete em vários deslocamentos) que contém `ref`."""
    copias = [a for a in aneis_da_layer(msp, ["POLIGONAL"], e0, n0) if len(a) >= 600]
    dentro = [a for a in copias if Polygon(a).buffer(0).contains(Polygon([ref, (ref[0] + 0.1, ref[1]),
                                                                          (ref[0], ref[1] + 0.1)]))]
    if len(dentro) != 1:
        raise SystemExit(f"poligonal da gleba: {len(dentro)} cópias contêm a Fase 1 (esperado 1)")
    return dentro[0]


def _afim(f) -> tuple[float, ...]:
    """Coeficientes do Image.AFFINE a partir de f(u, v) → (x, y) no raster de entrada."""
    o = np.array(f(0.0, 0.0))
    a, b = np.array(f(1.0, 0.0)) - o, np.array(f(0.0, 1.0)) - o
    return (a[0], b[0], o[0], a[1], b[1], o[1])


def _mascara(geom, ext_m, tam) -> Image.Image:
    x0, y0, x1, y1 = ext_m
    w, h = tam
    m = Image.new("L", tam, 0)
    dr = ImageDraw.Draw(m)
    px = lambda cs: [((x - x0) / (x1 - x0) * w, (y1 - y) / (y1 - y0) * h) for x, y in cs]  # noqa: E731
    for p in partes(geom):
        dr.polygon(px(p.exterior.coords), fill=255)
        for furo in p.interiors:
            dr.polygon(px(furo.coords), fill=0)
    return m


def pintar(tile: Image.Image, ext_m, mp_img: Image.Image, meta: dict, mascara,
           saturacao: float, opacidade: float) -> Image.Image:
    w, h = tile.size
    x0, y0, x1, y1 = ext_m
    T = Semelhanca(**meta["transf"])
    k = meta["px_por_pt"]
    cx0, cy0 = meta["clip"][:2]

    def f(u: float, v: float) -> tuple[float, float]:
        X, Y = x0 + u * (x1 - x0) / w, y1 - v * (y1 - y0) / h
        xp, ym = T.inversa(np.array([[X, Y]]))[0]
        return ((xp - cx0) * k, (-ym - cy0) * k)

    mp = mp_img.convert("RGB").transform((w, h), Image.AFFINE, _afim(f), resample=Image.BILINEAR,
                                         fillcolor=(255, 255, 255))
    mp = ImageEnhance.Color(mp).enhance(saturacao).filter(ImageFilter.GaussianBlur(0.8))
    alfa = _mascara(mascara, ext_m, (w, h)).point(lambda a: round(a * opacidade))
    return Image.composite(mp, tile, alfa)


def main() -> int:
    import fitz

    sys.stdout.reconfigure(encoding="utf-8")
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    pol_venda = aneis_da_layer(ezdxf.readfile(DXF_VENDA).modelspace(), ["AR-CNT-POL"], e0, n0)
    gleba = poligonal_gleba(ezdxf.readfile(DXF_R05).modelspace(), e0, n0, centroide(pol_venda[0]))
    alvo = np.array(gleba)
    pagina = fitz.open(terreno_dir() / PDF)[PAGINA]
    contorno = escolher_contorno(caminhos_fechados(pagina), alvo)
    T, residuo = registrar(contorno * [1.0, -1.0], alvo)
    print(f"masterplan: {T.s:.3f} m/pt · rotação {math.degrees(T.theta):+.2f}° · resíduo mediano {residuo:.2f} m")
    if residuo > RESIDUO_MAX:
        raise SystemExit(f"resíduo {residuo:.2f} m acima de {RESIDUO_MAX} m: contorno errado no PDF?")
    xs, ys = contorno[:, 0], contorno[:, 1]
    clip = fitz.Rect(xs.min() - 5, ys.min() - 5, xs.max() + 5, ys.max() + 5)
    k = PX_POR_M * T.s
    pix = pagina.get_pixmap(matrix=fitz.Matrix(k, k), clip=clip, alpha=False)
    Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(PNG)
    META.write_text(json.dumps({"arquivo": str(PNG), "clip": [clip.x0, clip.y0, clip.x1, clip.y1], "px_por_pt": k,
                                "transf": asdict(T), "residuo_m": residuo, "gleba": [list(p) for p in gleba]}),
                    encoding="utf-8")
    print(f"raster {pix.width}×{pix.height} px ({1 / PX_POR_M:.1f} m/px) → {PNG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Em `scripts/entorno/preparar.py`, no `main`, antes de `gerar_tiles`:

```python
    pos = None
    if cfg.masterplan:
        from .masterplan import META, pintar

        if not META.exists():
            raise SystemExit("masterplan = true sem cache: rode uv run python -m scripts.entorno.masterplan")
        meta = json.loads(META.read_text(encoding="utf-8"))
        mp_img = Image.open(meta["arquivo"])
        tcfg = TerrenoCfg.carregar(CFG_TOML)
        mascara = Polygon(meta["gleba"]).buffer(0).difference(plato.buffer(tcfg.plato_folga + tcfg.talude))
        pos = lambda img, ext_m: pintar(img, ext_m, mp_img, meta, mascara,  # noqa: E731
                                        cfg.masterplan_saturacao, cfg.masterplan_opacidade)
```

passe `pos=pos` a `gerar_tiles` e importe `from PIL import Image`. Em `entorno.toml`, `masterplan = true` (e tire "(liga na Task 8…)" do comentário).

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 7: Gerar e conferir**

Run: `uv run python -m scripts.entorno.masterplan && uv run python -m scripts.entorno.preparar && uv run python -m scripts.loteamento.blender`
Expected: resíduo ≤ 2 m impresso; tiles com as fases 2–10 apagadas em volta da Fase 1; Read em `cache/cena/previa.png` e `previa-entorno.png`: o masterplan lê como fundo, a placa da Fase 1 domina, nada do traçado antigo da Fase 1 encosta na placa. Se o masterplan competir com a placa, baixe `masterplan_opacidade` no TOML e rode `preparar` + `blender` de novo.

- [ ] **Step 8: Commit**

```bash
git add scripts/entorno/masterplan.py scripts/entorno/preparar.py scripts/entorno/entorno.toml pyproject.toml uv.lock tests/test_masterplan.py
git commit -m "feat(entorno): masterplan das fases 2–10 do PDF, registrado na poligonal e pintado em segundo plano"
```

---

### Task 9: Documentação e fechamento

**Files:**
- Modify: `docs/superpowers/plans/2026-10-14-00-plano-mestre.md`
- Modify: `docs/superpowers/specs/2026-10-15-placa-loteamento-tiles-design.md` (linhas de corte reais)

- [ ] **Step 1: Plano-mestre**

Na tabela, depois da linha do 3c, acrescente:

```markdown
| 3d | Placa em volume e chão em tiles (`2026-10-15-03d-placa-loteamento-tiles.md`) | Loteamento como placa sem sobreposição (pista, meio-fio, juntas, lagoa, saia), terreno com furo, chão em 4 tiles de 4096 px, masterplan das fases 2–10 em segundo plano; GLBs dos marcos convertidos (`scripts/marcos/conversao/`) | 3c, 4 | — |
```

Em "Contratos entre planos", acrescente:

```markdown
- **Objetos do chão:** `Entorno_<ij>` (`entorno.glb`) e `Terreno_<ij>` (`loteamento.glb`), `i` 0/1 = oeste/leste, `j` 0/1 = sul/norte; cada um com o material `chao_mapa_<ij>` do seu tile. `cache/entorno/mapa.json` = `{"tiles": {ij: {arquivo, ext, janela, px}}}`.
- **Pivô dos lotes:** a origem de cada objeto `Q…` é o centro da caixa do topo do lote (topo a +0,40 m do platô); no glTF, `translation` = (x, z, −y).
- **Marcos:** `clube - sem mobiliario.glb` e `portaria e rotatoria.glb` em `10-MAQUETE INTERATIVA/`; o clube está girado +28° em torno de `PIVOT` (40,56; 45,98) em relação à portaria (detalhes em `scripts/marcos/conversao/README.md`).
```

- [ ] **Step 2: Spec**

Na seção 2 da spec, troque "x = −30 e y = 30 nos dados atuais (o script calcula)" por "x = −30 e y = 60 nos dados atuais (o script calcula)".

- [ ] **Step 3: Verificação final**

Run: `uv run pytest -q`
Expected: tudo passa. Confirme também que `6-PROJETOS/10-MAQUETE INTERATIVA/` não tem `.blend1`.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-10-14-00-plano-mestre.md docs/superpowers/specs/2026-10-15-placa-loteamento-tiles-design.md
git commit -m "docs: plano-mestre com o 3d (placa, tiles, masterplan) e contratos do chão, pivô e marcos"
```
