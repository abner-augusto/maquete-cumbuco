# Plano 3c — Relevo simplificado: platô, morro e entorno de 4 km

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar o relevo detalhado do loteamento por um platô plano com talude, o morro em volta pelas curvas do levantamento suavizadas e o entorno até 4 km pelo Copernicus GLO-30, e exportar `loteamento.glb` (terreno perto, áreas, lagoa, lotes) e o novo `entorno.glb` (`Entorno` e `Mar`), costurados sem degrau.

**Architecture:** Continua o método do Plano 3: Python puro faz a geometria e grava JSON; o Blender só constrói e exporta. `scripts/entorno/dem.py` baixa o tile do Copernicus e o reamostra numa grade local de 30 m (`cache/cena/dem.json`). `scripts/loteamento/terreno.py` compõe a grade perto de 10 m (platô, talude, levantamento suavizado, transição ao Copernicus) em `cache/cena/terreno.json` e a cena do entorno em `cache/cena/entorno.json`. `cena.py` passa a assentar tudo na grade perto. A borda da grade perto cai nas linhas da grade de 30 m e já é Copernicus puro, então as duas malhas se encontram nas mesmas cotas.

**Tech Stack:** Python 3.12+, uv, NumPy, SciPy (`gaussian_filter`, `distance_transform_edt`, `label`, `map_coordinates`), rasterio e pyproj (novos), ezdxf, Blender 5.2, pytest.

**Spec:** `docs/superpowers/specs/2026-10-14-relevo-plato-entorno-design.md` (spec-mãe: `2026-10-14-maquete-cumbuco-design.md` §7.1.3 e §7.2)
**Consome:** `cache/cena/relevo.json` (Plano 3, `relevo.py`), `cache/dxf/planta-venda.dxf`, `dados/lotes.json`, `dados/georref.json`.

## Achados que fixam o plano (14/10/2026)

- Origem local E 534600 / N 9595100 (UTM 24S) ≈ lon −38,689, lat −3,662. O raio de 4 km cabe no tile `Copernicus_DSM_COG_10_S04_00_W039_00_DEM` (lat −4..−3, lon −39..−38), público em `https://copernicus-dem-30m.s3.amazonaws.com/<TILE>/<TILE>.tif`, sem login.
- Lotes entre 17 e 27 m no levantamento; médias por quadra de 19,8 a 25 m. A leste o terreno desce a 5 m; ao norte do multifamiliar o levantamento sobe a ~34 m.
- O Copernicus é DSM em EGM2008; o mar vale ~0. O levantamento tem a referência dele: a diferença é medida, não suposta.
- Peso: grade de 30 m num círculo de 4 km ≈ 56 mil nós e 111 mil triângulos ≈ 2,7 MB. A grade perto a 10 m (poligonal ± 430 m) ≈ 28 mil nós, metade dos triângulos do terreno atual.

## Global Constraints

- Nada é modelado à mão: ajuste é parâmetro (`cena.toml`, tabela `[terreno]`) ou script; `.blend` gerado nunca é editado.
- Coordenadas locais (E − E0, N − N0); no Blender x = leste, y = norte, z = cota; glTF com `export_yup=True`.
- **Um objeto por lote** com o id do `lotes.json`; 347 no `loteamento.glb`, nem mais nem menos.
- Sem exagero vertical.
- Platô plano único na poligonal `AR-CNT-POL`; cota = mediana do levantamento sob os lotes, a 0,5 m, salvo `plato_cota` no `cena.toml`.
- Raio do entorno: 4 km a partir do centro da caixa dos lotes.
- `entorno.glb` < 3 MB e `loteamento.glb` ≤ 8 MB sem compressão (meshopt fica no Plano 5).
- O mar é a malha `Mar` com material `mar` provisório; o front troca por shader (Plano 5).
- Saídas em `TERRENO_DIR/6-PROJETOS/10-MAQUETE INTERATIVA/` (`loteamento.glb/.blend`, `entorno.glb/.blend`), sem `.blend1`; intermediários em `cache/`.
- Docs e commits em português do Brasil.

## Review Focus

1. **Ajuste de datum com sinal trocado** sobe ou desce o entorno inteiro e abre um degrau na transição. Teste na Task 2 (`test_ajustar_datum_devolve_o_deslocamento`).
2. **Fresta ou degrau na costura** entre `Terreno` (10 m) e `Entorno` (30 m). Teste na Task 3 (`test_borda_do_perto_e_linear_entre_nos_do_entorno`).
3. **Baixio no continente tratado como mar** (o plano da água aparece no meio do mato). Teste na Task 2 (`test_separar_mar_so_agua_ligada_a_borda`).
4. **Degrau onde o levantamento acaba** (faixa norte sem curvas): a troca levantamento → Copernicus tem de ser gradual também nessa borda. Teste na Task 2 (`test_borda_da_cobertura_do_levantamento_sem_degrau`).
5. **Download interrompido** deixa um `.tif` truncado que vira cache. Teste na Task 1 (`test_baixar_grava_por_arquivo_parcial`).

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `scripts/entorno/__init__.py` | pacote |
| `scripts/entorno/dem.py` | `baixar`, `amostrar`, `grade_dem`, CLI → `cache/cena/dem.json` |
| `scripts/loteamento/relevo.py` | `Grade` aceita NaN (JSON `null`); `gerar_grade(..., preencher=False)`; `MARGEM` 450; sai `suavizar_dentro` |
| `scripts/loteamento/terreno.py` | `TerrenoCfg`, `encaixar`, `amostrar_grade`, `reamostrar`, `cota_plato`, `ajustar_datum`, `separar_mar`, `compor_perto`, `malha_entorno`, `disco_mar`, CLI → `terreno.json`, `entorno.json` |
| `scripts/loteamento/cena.py` | assenta na grade perto (`terreno.json`); sai suavização e rebaixo; `fundo_lagoa` |
| `scripts/loteamento/cena.toml` | sai `poligonal/sigma/transicao/rebaixo`; entra `fundo_lagoa` e a tabela `[terreno]` |
| `scripts/blender/gerar_loteamento.py` | materiais `entorno` e `mar`; contexto só para a prévia; prévia sem lotes |
| `scripts/loteamento/blender.py` | roda entorno e loteamento; `conferir_entorno` |
| `tests/test_dem.py`, `tests/test_terreno.py` | novos; `test_relevo.py`, `test_cena.py`, `test_blender.py` ajustados |

---

### Task 1: Copernicus na grade local

**Files:**
- Create: `scripts/entorno/__init__.py`, `scripts/entorno/dem.py`, `tests/test_dem.py`
- Modify: `pyproject.toml` (rasterio, pyproj)

**Interfaces:**
- Consumes: `scripts.loteamento.relevo.Grade(x0, y0, passo, nx, ny, z)`.
- Produces: `dem.DESTINO` (`cache/cena/dem.json`, `Grade` de 30 m, nós em múltiplos de 30 m, cotas brutas EGM2008); `baixar(url, destino) -> Path`; `amostrar(tif, e, n, crs="EPSG:31984") -> np.ndarray`; `grade_dem(tif, e0, n0, centro, raio, passo) -> Grade`; `RAIO = 4000.0`, `PASSO = 30.0`.

- [ ] **Step 1: Dependências**

Run: `uv add rasterio pyproj`
Expected: as duas entram em `pyproject.toml`; `uv run python -c "import rasterio, pyproj"` sai sem erro.

- [ ] **Step 2: Escrever os testes**

`tests/test_dem.py`:

```python
import math

import numpy as np
import pytest
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

from scripts.entorno.dem import amostrar, baixar, grade_dem

E0, N0 = 534600.0, 9595100.0
LON0, LAT0, PX = -38.75, -3.60, 1 / 3600


def _cota(lon, lat):
    return 1000.0 * (lon - LON0) + 500.0 * (lat - LAT0)  # plano: o bilinear reproduz exato


@pytest.fixture
def tif(tmp_path):
    n = 400
    cols, lins = np.meshgrid(np.arange(n), np.arange(n))
    z = _cota(LON0 + (cols + 0.5) * PX, LAT0 - (lins + 0.5) * PX).astype("float32")
    z[0, 0] = -32767.0  # nodata no canto
    caminho = tmp_path / "dem.tif"
    with rasterio.open(caminho, "w", driver="GTiff", width=n, height=n, count=1, dtype="float32",
                       crs="EPSG:4326", transform=from_origin(LON0, LAT0, PX, PX), nodata=-32767.0) as d:
        d.write(z, 1)
    return caminho


def test_amostrar_reproduz_o_plano_no_ponto_utm(tif):
    e = np.array([E0, E0 + 1234.5]); n = np.array([N0, N0 - 987.0])
    lon, lat = Transformer.from_crs("EPSG:31984", "EPSG:4326", always_xy=True).transform(e, n)
    assert amostrar(tif, e, n) == pytest.approx(_cota(lon, lat), abs=1e-3)


def test_amostrar_nodata_vira_zero(tif):
    lon, lat = LON0 + 0.5 * PX, LAT0 - 0.5 * PX  # centro do pixel nodata
    e, n = Transformer.from_crs("EPSG:4326", "EPSG:31984", always_xy=True).transform(lon, lat)
    assert amostrar(tif, np.array([e]), np.array([n]))[0] == pytest.approx(0.0, abs=1e-6)


def test_grade_dem_nos_em_multiplos_do_passo_e_cobre_o_raio(tif):
    g = grade_dem(tif, E0, N0, centro=(17.0, -42.0), raio=300.0, passo=30.0)
    assert g.x0 % 30 == 0 and g.y0 % 30 == 0
    assert g.x0 <= 17 - 300 and g.x0 + g.passo * (g.nx - 1) >= 17 + 300
    assert g.y0 <= -42 - 300 and g.y0 + g.passo * (g.ny - 1) >= -42 + 300
    lon, lat = Transformer.from_crs("EPSG:31984", "EPSG:4326", always_xy=True).transform(E0 + g.x0, N0 + g.y0)
    assert g.z[0][0] == pytest.approx(_cota(lon, lat), abs=0.01)


def test_baixar_grava_por_arquivo_parcial(tmp_path):
    origem = tmp_path / "origem.tif"
    origem.write_bytes(b"x" * 1000)
    destino = tmp_path / "cache" / "t.tif"
    assert baixar(origem.as_uri(), destino) == destino and destino.read_bytes() == b"x" * 1000
    assert not destino.with_suffix(".part").exists()
    origem.write_bytes(b"y")
    baixar(origem.as_uri(), destino)  # já existe: não baixa de novo
    assert destino.read_bytes() == b"x" * 1000
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_dem.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'scripts.entorno'`.

- [ ] **Step 4: Implementar**

`scripts/entorno/__init__.py` vazio. `scripts/entorno/dem.py`:

```python
"""Relevo macro do entorno: Copernicus GLO-30 (DSM, 30 m) reamostrado na grade local.

Uso: uv run python -m scripts.entorno.dem
"""

import json
import math
import shutil
import sys
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window
from scipy.ndimage import map_coordinates

from scripts.comum.ambiente import RAIZ
from scripts.loteamento.relevo import Grade

TILE = "Copernicus_DSM_COG_10_S04_00_W039_00_DEM"
URL = f"https://copernicus-dem-30m.s3.amazonaws.com/{TILE}/{TILE}.tif"
CACHE = RAIZ / "cache" / "dem" / f"{TILE}.tif"
DESTINO = RAIZ / "cache" / "cena" / "dem.json"
CRS_LOCAL = "EPSG:31984"
RAIO = 4000.0  # m a partir do centro dos lotes
PASSO = 30.0  # m, a resolução do Copernicus


def baixar(url: str = URL, destino: Path = CACHE) -> Path:
    """Baixa uma vez; grava em .part e renomeia, para um download cortado não virar cache."""
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    parte = destino.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=600) as r, open(parte, "wb") as f:
        shutil.copyfileobj(r, f)
    parte.replace(destino)
    return destino


def amostrar(tif: Path, e: np.ndarray, n: np.ndarray, crs: str = CRS_LOCAL) -> np.ndarray:
    """Cota bilinear do raster nos pontos (E, N) de `crs`; nodata vira 0 (mar)."""
    with rasterio.open(tif) as src:
        lon, lat = Transformer.from_crs(crs, src.crs, always_xy=True).transform(np.asarray(e), np.asarray(n))
        col, lin = ~src.transform * (np.asarray(lon), np.asarray(lat))
        c0 = max(int(math.floor(np.min(col))) - 2, 0)
        r0 = max(int(math.floor(np.min(lin))) - 2, 0)
        c1 = min(int(math.ceil(np.max(col))) + 2, src.width)
        r1 = min(int(math.ceil(np.max(lin))) + 2, src.height)
        a = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0)).astype(float)
        if src.nodata is not None:
            a[a == src.nodata] = 0.0
    return map_coordinates(a, [np.asarray(lin) - r0 - 0.5, np.asarray(col) - c0 - 0.5], order=1, mode="nearest")


def grade_dem(tif: Path, e0: float, n0: float, centro: tuple[float, float],
              raio: float = RAIO, passo: float = PASSO) -> Grade:
    """Grade local (x = E − E0, y = N − N0) de `passo` m, nós em múltiplos de `passo`, cobrindo o raio."""
    x0 = math.floor((centro[0] - raio) / passo) * passo
    y0 = math.floor((centro[1] - raio) / passo) * passo
    nx = int(math.ceil((centro[0] + raio - x0) / passo)) + 1
    ny = int(math.ceil((centro[1] + raio - y0) / passo)) + 1
    gx, gy = np.meshgrid(x0 + passo * np.arange(nx), y0 + passo * np.arange(ny))
    z = amostrar(tif, (gx + e0).ravel(), (gy + n0).ravel()).reshape(gx.shape)
    return Grade(float(x0), float(y0), float(passo), nx, ny, np.round(z, 2).tolist())


def centro_dos_lotes() -> tuple[float, float]:
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    xs = [x for l in lotes for x, _ in l["poligono"]]
    ys = [y for l in lotes for _, y in l["poligono"]]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    tif = baixar()
    g = grade_dem(tif, georref["origem"]["E"], georref["origem"]["N"], centro_dos_lotes())
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(g.para_json()), encoding="utf-8")
    zs = [v for linha in g.z for v in linha]
    print(f"Copernicus {tif.name} · grade {g.nx}×{g.ny} de {g.passo:.0f} m · cota {min(zs):.1f}–{max(zs):.1f} m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_dem.py -q`
Expected: 4 passed.

- [ ] **Step 6: Rodar no dado real**

Run: `uv run python -m scripts.entorno.dem`
Expected: baixa o tile (dezenas de MB) para `cache/dem/`; imprime grade ~268×268 de 30 m e cota de ~0 (mar) a algumas dezenas de metros.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock scripts/entorno tests/test_dem.py
git commit -m "feat(entorno): Copernicus GLO-30 reamostrado na grade local de 30 m"
```

---

### Task 2: Composição do terreno perto

**Files:**
- Create: `scripts/loteamento/terreno.py`, `tests/test_terreno.py`
- Modify: `scripts/loteamento/relevo.py` (`Grade` com NaN, `preencher`, `MARGEM`; remove `suavizar_dentro`), `tests/test_relevo.py` (remove `test_suavizar_dentro_tira_a_duna_so_dentro_da_poligonal`; novo teste de NaN), `scripts/loteamento/cena.toml` (tabela `[terreno]`), `scripts/loteamento/cena.py` (`CenaCfg.carregar` ignora `[terreno]`)

**Interfaces:**
- Consumes: `Grade`, `relevo.mascara(grade, aneis) -> np.ndarray[bool]`, `geometria.centroide`.
- Produces (em `terreno.py`): `TerrenoCfg(poligonal, talude, sigma, alcance, transicao, raio, mar_rebaixo, passo_perto, plato_cota=None)` com `carregar(caminho)`; `encaixar(ext, passo) -> ext`; `amostrar_grade(g, xs, ys) -> np.ndarray`; `reamostrar(g, ext, passo) -> Grade`; `cota_plato(lev, lotes, passo=0.5) -> float`; `ajustar_datum(lev, dem, onde) -> float`; `separar_mar(dem, nivel=0.0, rebaixo=1.0) -> Grade`; `compor_perto(lev, dem, poligonal, cota, cfg) -> Grade`.

- [ ] **Step 1: Testes de `relevo.py`**

Em `tests/test_relevo.py`, apagar `test_suavizar_dentro_tira_a_duna_so_dentro_da_poligonal` e acrescentar:

```python
def test_grade_sem_preencher_deixa_nan_fora_das_curvas_e_vai_ao_json():
    curvas = [Curva(_horizontal(y).pontos, 30.0 + y / 10) for y in range(0, 60, 10)]
    g = gerar_grade(curvas, (-50.0, -50.0, 150.0, 120.0), 5.0, preencher=False)
    assert math.isnan(g.z[0][0]) and not math.isnan(g.z[15][20])
    volta = Grade.de_json(json.loads(json.dumps(g.para_json())))  # JSON padrão: null, não NaN
    assert "NaN" not in json.dumps(g.para_json()) and math.isnan(volta.z[0][0])
```

(com `import json` no topo do arquivo).

- [ ] **Step 2: Testes de `terreno.py`**

`tests/test_terreno.py`:

```python
import math

import numpy as np
import pytest

from scripts.loteamento.relevo import Grade
from scripts.loteamento.terreno import (TerrenoCfg, ajustar_datum, amostrar_grade, compor_perto, cota_plato,
                                        encaixar, reamostrar, separar_mar)

CFG = TerrenoCfg(poligonal=["POL"], talude=20.0, sigma=25.0, alcance=100.0, transicao=50.0, raio=4000.0,
                 mar_rebaixo=1.0, passo_perto=10.0)
QUADRADO = [(-50.0, -50.0), (50.0, -50.0), (50.0, 50.0), (-50.0, 50.0)]


def _grade(f, x0=-300.0, y0=-300.0, passo=10.0, n=61):
    return Grade(x0, y0, passo, n, n, [[f(x0 + i * passo, y0 + j * passo) for i in range(n)] for j in range(n)])


def test_encaixar_vai_para_fora_em_multiplos():
    assert encaixar((-41.0, 13.0, 59.0, 60.0), 30.0) == (-60.0, 0.0, 60.0, 60.0)


def test_amostrar_grade_bilinear_e_presa_na_borda():
    g = _grade(lambda x, y: 2 * x + y)
    assert amostrar_grade(g, np.array([12.5, -1000.0]), np.array([3.0, 0.0])) == pytest.approx([28.0, -600.0])


def test_cota_plato_mediana_dos_lotes_a_meio_metro():
    g = _grade(lambda x, y: 20.0 + x / 100)
    lotes = [{"poligono": [[x, 0], [x + 10, 0], [x + 10, 10], [x, 10]]} for x in (0, 30, 60)]
    assert cota_plato(g, lotes) == 20.5  # centróides em 5, 35, 65 → 20.05, 20.35, 20.65 → 20.35 → 20.5


def test_ajustar_datum_devolve_o_deslocamento():
    lev = _grade(lambda x, y: 10.0 + x / 50)
    dem = _grade(lambda x, y: 7.0 + x / 50, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    onde = np.ones((lev.ny, lev.nx), dtype=bool)
    assert ajustar_datum(lev, dem, onde) == pytest.approx(3.0, abs=1e-6)


def test_separar_mar_so_agua_ligada_a_borda():
    z = [[5.0] * 9 for _ in range(9)]
    for j in range(9):
        z[j][0] = z[j][1] = -0.5  # mar a oeste, encostado na borda
    z[4][6] = -0.3  # baixio no continente
    s = separar_mar(Grade(0.0, 0.0, 30.0, 9, 9, z), nivel=0.0, rebaixo=1.0)
    assert s.z[4][0] == pytest.approx(-1.0) and s.z[4][1] == pytest.approx(-1.0)
    assert s.z[4][6] > 0.0 and s.z[4][4] == 5.0


def test_plato_plano_dentro_e_talude_continuo():
    lev = _grade(lambda x, y: 25.0 + 5 * math.sin(x / 40) * math.cos(y / 30))  # dunas
    dem = _grade(lambda x, y: 18.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    g = compor_perto(lev, dem, [QUADRADO], 22.0, CFG)
    z = np.array(g.z)
    gx, gy = np.meshgrid(g.x0 + g.passo * np.arange(g.nx), g.y0 + g.passo * np.arange(g.ny))
    dentro = (abs(gx) <= 50) & (abs(gy) <= 50)
    assert np.allclose(z[dentro], 22.0)
    assert max(abs(np.diff(z, axis=0)).max(), abs(np.diff(z, axis=1)).max()) < 5.0  # nada de degrau


def test_longe_da_poligonal_e_so_copernicus():
    lev = _grade(lambda x, y: 30.0)
    dem = _grade(lambda x, y: 10.0 + x / 100, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    g = compor_perto(lev, dem, [QUADRADO], 22.0, CFG)
    # (290, 0): a 240 m da poligonal > alcance + transição = 150 m
    assert g.z[30][59] == pytest.approx(10.0 + 290 / 100, abs=1e-6)


def test_borda_da_cobertura_do_levantamento_sem_degrau():
    lev = _grade(lambda x, y: 30.0 if y < 60 else float("nan"))  # levantamento acaba em y = 60
    dem = _grade(lambda x, y: 18.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    cfg = TerrenoCfg(**{**CFG.__dict__, "alcance": 1000.0})
    z = np.array(compor_perto(lev, dem, [QUADRADO], 22.0, cfg).z)
    coluna = z[:, 55]  # x = 250, longe do platô: só levantamento × Copernicus
    assert abs(np.diff(coluna)).max() < 6.0  # 12 m de diferença espalhados, não num degrau


def test_reamostrar_mantem_nan_fora_do_levantamento():
    lev = _grade(lambda x, y: 30.0 if x < 0 else float("nan"), passo=5.0, x0=-100.0, y0=-100.0, n=41)
    r = reamostrar(lev, (-200.0, -200.0, 200.0, 200.0), 10.0)
    assert r.nx == 41 and r.z[20][12] == pytest.approx(30.0) and math.isnan(r.z[20][35]) and math.isnan(r.z[0][0])
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_relevo.py tests/test_terreno.py -q`
Expected: FAIL (`gerar_grade() got an unexpected keyword argument 'preencher'`; `ModuleNotFoundError: scripts.loteamento.terreno`).

- [ ] **Step 4: `relevo.py`**

- `MARGEM = 450.0` (o levantamento precisa ir até alcance + transição da poligonal).
- `Grade.para_json`: `"z": [[None if v is None or math.isnan(v) else v for v in linha] for linha in self.z]`.
- `Grade.de_json`: `[[math.nan if v is None else v for v in linha] for linha in d["z"]]`.
- `gerar_grade(curvas, ext, passo, preencher: bool = True)`: o preenchimento por vizinho mais próximo só quando `preencher`.
- `main`: `gerar_grade(mestras + inters, ext, PASSO_GRADE, preencher=False)`; o print de cota usa só valores não-NaN (`[v for linha in grade.z for v in linha if not math.isnan(v)]`) e informa a fração coberta.
- Apagar `suavizar_dentro` e o import de `distance_transform_edt, gaussian_filter` se ficar sem uso.

- [ ] **Step 5: `cena.toml` e `CenaCfg.carregar`**

Acrescentar ao fim de `cena.toml`:

```toml
[terreno]   # platô, morro e entorno (scripts/loteamento/terreno.py)
poligonal = ["AR-CNT-POL"]
# plato_cota = 21.5   # sem esta linha: mediana do levantamento sob os lotes, a 0,5 m
talude = 20.0        # m, do platô ao morro
sigma = 25.0         # m, suavização do levantamento: só as formas grandes
alcance = 300.0      # m da poligonal com o levantamento inteiro
transicao = 100.0    # m do levantamento ao Copernicus
raio = 4000.0        # m do entorno, a partir do centro dos lotes
mar_rebaixo = 1.0    # m que o fundo do mar desce abaixo do plano da água
passo_perto = 10.0   # m da grade do terreno perto (múltiplo do passo do Copernicus)
```

Em `CenaCfg.carregar`: `d = tomllib.loads(...); d.pop("terreno", None); return cls(**d)`.

- [ ] **Step 6: `terreno.py` (funções)**

```python
"""Terreno da cena: platô do loteamento, morro pelo levantamento suavizado e entorno pelo Copernicus.

Uso: uv run python -m scripts.loteamento.terreno
"""

import json
import math
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, label, map_coordinates

from .geometria import Ponto, centroide
from .relevo import Grade, mascara


@dataclass(frozen=True)
class TerrenoCfg:
    poligonal: list[str]
    talude: float
    sigma: float
    alcance: float
    transicao: float
    raio: float
    mar_rebaixo: float
    passo_perto: float
    plato_cota: float | None = None

    @classmethod
    def carregar(cls, caminho: Path) -> "TerrenoCfg":
        return cls(**tomllib.loads(caminho.read_text(encoding="utf-8"))["terreno"])


def encaixar(ext: tuple[float, float, float, float], passo: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = ext
    return (math.floor(x0 / passo) * passo, math.floor(y0 / passo) * passo,
            math.ceil(x1 / passo) * passo, math.ceil(y1 / passo) * passo)


def _nos(g: Grade) -> tuple[np.ndarray, np.ndarray]:
    return np.meshgrid(g.x0 + g.passo * np.arange(g.nx), g.y0 + g.passo * np.arange(g.ny))


def amostrar_grade(g: Grade, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Bilinear presa na borda (como Grade.cota), vetorizada; NaN da grade se propaga."""
    fx = np.clip((np.asarray(xs) - g.x0) / g.passo, 0, g.nx - 1)
    fy = np.clip((np.asarray(ys) - g.y0) / g.passo, 0, g.ny - 1)
    return map_coordinates(np.array(g.z, dtype=float), [fy, fx], order=1, mode="nearest")


def reamostrar(g: Grade, ext: tuple[float, float, float, float], passo: float) -> Grade:
    """`g` numa grade nova; fora de `g` (ou onde ela é NaN) fica NaN."""
    x0, y0, x1, y1 = ext
    nx, ny = int(round((x1 - x0) / passo)) + 1, int(round((y1 - y0) / passo)) + 1
    gx, gy = np.meshgrid(x0 + passo * np.arange(nx), y0 + passo * np.arange(ny))
    z = amostrar_grade(g, gx, gy)
    fora = (gx < g.x0) | (gx > g.x0 + g.passo * (g.nx - 1)) | (gy < g.y0) | (gy > g.y0 + g.passo * (g.ny - 1))
    z[fora] = np.nan
    return Grade(float(x0), float(y0), float(passo), nx, ny, z.tolist())


def cota_plato(lev: Grade, lotes: list[dict], passo: float = 0.5) -> float:
    """Mediana do levantamento nos centróides dos lotes, arredondada a `passo`."""
    zs = [lev.cota(*centroide([tuple(p) for p in l["poligono"]])) for l in lotes]
    zs = [z for z in zs if not math.isnan(z)]
    return float(round(float(np.median(zs)) / passo) * passo)


def ajustar_datum(lev: Grade, dem: Grade, onde: np.ndarray) -> float:
    """Mediana de (levantamento − Copernicus) nos nós de `lev` marcados em `onde` que têm levantamento."""
    z = np.array(lev.z, dtype=float)
    gx, gy = _nos(lev)
    d = amostrar_grade(dem, gx, gy)
    ok = onde & ~np.isnan(z)
    return float(np.median(z[ok] - d[ok]))


def separar_mar(dem: Grade, nivel: float = 0.0, rebaixo: float = 1.0) -> Grade:
    """Água ligada à borda com cota ≤ `nivel` é mar: desce a `nivel − rebaixo`. Baixio isolado
    no continente sobe a `nivel + 0,2`, para o plano do mar não aparecer nele."""
    z = np.array(dem.z, dtype=float)
    rotulo, _ = label(z <= nivel)
    borda = set(np.unique(np.concatenate([rotulo[0], rotulo[-1], rotulo[:, 0], rotulo[:, -1]]))) - {0}
    mar = np.isin(rotulo, list(borda))
    z = np.where(mar, nivel - rebaixo, np.where(rotulo > 0, nivel + 0.2, z))
    return Grade(dem.x0, dem.y0, dem.passo, dem.nx, dem.ny, np.round(z, 2).tolist())


def _distancia_fora(g: Grade, aneis: list[list[Ponto]]) -> np.ndarray:
    """Metros de cada nó até a área dos anéis (0 dentro)."""
    return distance_transform_edt(~mascara(g, aneis)) * g.passo


def compor_perto(lev: Grade, dem: Grade, poligonal: list[list[Ponto]], cota: float, cfg: TerrenoCfg) -> Grade:
    """Platô na cota dentro da poligonal; talude de `cfg.talude` m; depois o levantamento suavizado
    (σ = `cfg.sigma`) até `cfg.alcance` m, passando ao Copernicus em `cfg.transicao` m. Onde o
    levantamento acaba, a troca também é gradual (peso pela cobertura suavizada)."""
    z = np.array(lev.z, dtype=float)
    tem = ~np.isnan(z)
    s = cfg.sigma / lev.passo
    soma = gaussian_filter(np.where(tem, z, 0.0), s, mode="nearest")
    cobertura = gaussian_filter(tem.astype(float), s, mode="nearest")
    suave = np.divide(soma, cobertura, out=np.zeros_like(soma), where=cobertura > 1e-6)
    gx, gy = _nos(lev)
    longe = amostrar_grade(dem, gx, gy)
    dist = _distancia_fora(lev, poligonal)
    peso = np.clip((cfg.alcance + cfg.transicao - dist) / cfg.transicao, 0.0, 1.0) * np.clip(cobertura, 0.0, 1.0)
    base = peso * suave + (1.0 - peso) * longe
    t = np.clip(dist / cfg.talude, 0.0, 1.0)
    final = (1.0 - t) * cota + t * base
    return Grade(lev.x0, lev.y0, lev.passo, lev.nx, lev.ny, np.round(final, 2).tolist())
```

- [ ] **Step 7: Rodar e ver passar**

Run: `uv run pytest -q`
Expected: tudo passa (a suíte toda: o teste de `suavizar_dentro` saiu, `test_cfg_carrega_do_toml` continua passando com a tabela nova).

- [ ] **Step 8: Commit**

```bash
git add scripts/loteamento/relevo.py scripts/loteamento/terreno.py scripts/loteamento/cena.toml scripts/loteamento/cena.py tests/test_relevo.py tests/test_terreno.py
git commit -m "feat(terreno): platô, talude, levantamento suavizado e transição ao Copernicus"
```

---

### Task 3: Entorno, mar e cena no terreno novo

**Files:**
- Modify: `scripts/loteamento/terreno.py` (`malha_entorno`, `disco_mar`, `main`), `scripts/loteamento/cena.py`, `scripts/loteamento/cena.toml`, `tests/test_terreno.py`, `tests/test_cena.py`

**Interfaces:**
- Consumes: Task 2 (`compor_perto`, `separar_mar`, `ajustar_datum`, `reamostrar`, `encaixar`, `cota_plato`, `TerrenoCfg`); Task 1 (`dem.DESTINO`, `dem.centro_dos_lotes`); `cena.aneis_da_layer`, `cena.DXF`, `cena.CFG_TOML`.
- Produces: `terreno.DESTINO_PERTO` (`cache/cena/terreno.json`, `Grade` de 10 m sem NaN), `terreno.DESTINO_ENTORNO` (`cache/cena/entorno.json`, `{"objetos": [Entorno, Mar]}` no formato de `loteamento.json`, materiais `entorno` e `mar`); `malha_entorno(dem, buraco, centro, raio) -> (vertices, faces)`; `disco_mar(centro, raio, nivel, n=96) -> (vertices, faces)`; `cena.TERRENO_JSON`; `CenaCfg.fundo_lagoa` (substitui `rebaixo`; saem `poligonal`, `sigma`, `transicao`).

- [ ] **Step 1: Testes**

Em `tests/test_terreno.py`:

```python
from scripts.loteamento.terreno import disco_mar, malha_entorno


def test_entorno_tem_furo_no_perto_e_fica_no_raio():
    dem = _grade(lambda x, y: 10.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    v, f = malha_entorno(dem, buraco=(-90.0, -90.0, 90.0, 90.0), centro=(0.0, 0.0), raio=500.0)
    centros = [np.mean([v[i][:2] for i in t], axis=0) for t in f]
    assert not any(abs(cx) < 90 and abs(cy) < 90 for cx, cy in centros)
    assert all(math.hypot(x, y) <= 500.0 + 1e-6 for x, y, _ in v)
    assert len(f) > 0 and all(len(t) == 3 for t in f)


def test_borda_do_perto_e_linear_entre_nos_do_entorno():
    f = lambda x, y: 10.0 + 0.001 * x * x + 0.02 * y  # noqa: E731 — curvo: só os nós de 30 m coincidem
    dem = _grade(f, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    lev = reamostrar(_grade(lambda x, y: 30.0), encaixar((-240.0, -240.0, 240.0, 240.0), 30.0), 10.0)
    g = compor_perto(lev, dem, [QUADRADO], 22.0, CFG)  # borda a 190 m > alcance + transição
    for k in range(g.nx):  # linha de baixo: a aresta do entorno é reta entre nós de 30 m
        x = g.x0 + k * g.passo
        a = math.floor(x / 30.0) * 30.0
        linear = f(a, g.y0) + (f(a + 30.0, g.y0) - f(a, g.y0)) * (x - a) / 30.0
        assert g.z[0][k] == pytest.approx(linear, abs=0.01)


def test_disco_do_mar_no_nivel():
    v, f = disco_mar((10.0, 20.0), 4000.0, 1.5, n=32)
    assert all(z == 1.5 for _, _, z in v) and len(f) == 32
```

Em `tests/test_cena.py`: apagar `test_terreno_rebaixado_sob_a_poligonal`; em `test_lagoa_que_e_a_propria_app_fica_so_agua` nada muda (usa `CFG` com `fundo_lagoa` padrão 0,6).

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_terreno.py tests/test_cena.py -q`
Expected: FAIL com `ImportError: cannot import name 'disco_mar'`.

- [ ] **Step 3: Implementar em `terreno.py`**

```python
def malha_entorno(dem: Grade, buraco: tuple[float, float, float, float], centro: tuple[float, float],
                  raio: float) -> tuple[list[list[float]], list[list[int]]]:
    """Grade do Copernicus em triângulos: células com os 4 cantos no raio e fora do `buraco`
    (o terreno perto). O buraco cai em linhas da grade, então cada célula está toda dentro ou fora."""
    bx0, by0, bx1, by1 = buraco
    z = dem.z
    indice: dict[tuple[int, int], int] = {}
    vertices: list[list[float]] = []
    faces: list[list[int]] = []

    def no(i: int, j: int) -> int:
        if (i, j) not in indice:
            indice[(i, j)] = len(vertices)
            vertices.append([round(dem.x0 + i * dem.passo, 2), round(dem.y0 + j * dem.passo, 2), z[j][i]])
        return indice[(i, j)]

    for j in range(dem.ny - 1):
        for i in range(dem.nx - 1):
            xa, ya = dem.x0 + i * dem.passo, dem.y0 + j * dem.passo
            xb, yb = xa + dem.passo, ya + dem.passo
            if bx0 <= xa and xb <= bx1 and by0 <= ya and yb <= by1:
                continue
            if any(math.hypot(x - centro[0], y - centro[1]) > raio for x in (xa, xb) for y in (ya, yb)):
                continue
            a, b, c, d = no(i, j), no(i + 1, j), no(i + 1, j + 1), no(i, j + 1)
            faces += [[a, b, c], [a, c, d]]
    return vertices, faces


def disco_mar(centro: tuple[float, float], raio: float, nivel: float, n: int = 96) -> tuple[list[list[float]], list[list[int]]]:
    """Plano da água: disco no raio do entorno; a terra acima do nível o esconde."""
    cx, cy = centro
    v = [[round(cx, 2), round(cy, 2), nivel]] + [
        [round(cx + raio * math.cos(2 * math.pi * k / n), 2), round(cy + raio * math.sin(2 * math.pi * k / n), 2), nivel]
        for k in range(n)]
    return v, [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)]
```

`main` (com `RAIZ`, `ezdxf`, `cena.aneis_da_layer`, `cena.DXF`, `cena.CFG_TOML`, `relevo.DESTINO as RELEVO_JSON`, `scripts.entorno.dem` importados no topo do módulo; `cena.py` não importa `terreno.py`, então não há ciclo):

```python
DESTINO_PERTO = RAIZ / "cache" / "cena" / "terreno.json"
DESTINO_ENTORNO = RAIZ / "cache" / "cena" / "entorno.json"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = TerrenoCfg.carregar(CFG_TOML)
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    lev = Grade.de_json(json.loads(RELEVO_JSON.read_text(encoding="utf-8")))
    bruto = Grade.de_json(json.loads(dem.DESTINO.read_text(encoding="utf-8")))
    poligonal = aneis_da_layer(ezdxf.readfile(DXF).modelspace(), cfg.poligonal, e0, n0)
    xs = [x for a in poligonal for x, _ in a]
    ys = [y for a in poligonal for _, y in a]
    folga = cfg.alcance + cfg.transicao + bruto.passo  # a borda do perto já é Copernicus puro
    ext = encaixar((min(xs) - folga, min(ys) - folga, max(xs) + folga, max(ys) + folga), bruto.passo)
    perto_lev = reamostrar(lev, ext, cfg.passo_perto)
    fora = _distancia_fora(perto_lev, poligonal) > cfg.talude
    com_mar = separar_mar(bruto, 0.0, cfg.mar_rebaixo)
    delta = ajustar_datum(perto_lev, com_mar, fora)
    longe = Grade(bruto.x0, bruto.y0, bruto.passo, bruto.nx, bruto.ny,
                  (np.array(com_mar.z, dtype=float) + delta).round(2).tolist())
    cota = cfg.plato_cota if cfg.plato_cota is not None else cota_plato(lev, lotes)
    perto = compor_perto(perto_lev, longe, poligonal, cota, cfg)
    centro = dem.centro_dos_lotes()
    v, f = malha_entorno(longe, ext, centro, cfg.raio)
    vm, fm = disco_mar(centro, cfg.raio, round(delta, 2))
    DESTINO_PERTO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO_PERTO.write_text(json.dumps(perto.para_json()), encoding="utf-8")
    DESTINO_ENTORNO.write_text(json.dumps({"objetos": [
        {"nome": "Entorno", "material": "entorno", "vertices": v, "faces": f},
        {"nome": "Mar", "material": "mar", "vertices": vm, "faces": fm},
    ]}), encoding="utf-8")
    print(f"platô {cota:.1f} m · levantamento − Copernicus = {delta:+.2f} m (mar nessa cota) · "
          f"perto {perto.nx}×{perto.ny} de {perto.passo:.0f} m · entorno {len(f)} triângulos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: `cena.py` e `cena.toml` no terreno novo**

- `cena.py`: `TERRENO_JSON = RAIZ / "cache" / "cena" / "terreno.json"`; `main` lê `TERRENO_JSON` no lugar de `RELEVO_JSON`. Em `CenaCfg`, saem `poligonal`, `sigma`, `transicao`, `rebaixo`; entra `fundo_lagoa: float = 0.6  # terreno dentro da lagoa fica este tanto abaixo da água`.
- `_terreno(grade, fundo=None)`: sai o parâmetro `sob/rebaixo` (o platô já está na grade); fica só o recorte da lagoa.
- `montar`: sai o bloco `poligonal`/`suavizar_dentro`; `objetos = [_terreno(grade, (lagoa, nivel - cfg.fundo_lagoa) if lagoa else None)]`; imports sem `suavizar_dentro`.
- `cena.toml`: saem `poligonal`, `sigma`, `transicao`, `rebaixo` do topo (e o comentário da terraplenagem); entra `fundo_lagoa = 0.6   # m, terreno dentro da lagoa abaixo da água`.

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest -q`
Expected: tudo passa.

- [ ] **Step 6: Rodar no dado real**

Run: `uv run python -m scripts.loteamento.relevo && uv run python -m scripts.loteamento.terreno && uv run python -m scripts.loteamento.cena`
Expected: `relevo` informa a fração coberta pelas curvas; `terreno` imprime platô ~21–22 m, o delta do datum (um valor de poucos metros; anotar no ledger) e ~110 mil triângulos no entorno; `cena` imprime 355 objetos (347 lotes) e um `Terreno` com bem menos triângulos que os 83 mil de antes.

- [ ] **Step 7: Commit**

```bash
git add scripts/loteamento/terreno.py scripts/loteamento/cena.py scripts/loteamento/cena.toml tests/test_terreno.py tests/test_cena.py
git commit -m "feat(terreno): entorno de 4 km e mar costurados ao terreno perto; cena no platô"
```

---

### Task 4: Blender, GLBs e documentação

**Files:**
- Modify: `scripts/blender/gerar_loteamento.py`, `scripts/loteamento/blender.py`, `tests/test_blender.py`, `docs/superpowers/plans/2026-10-14-00-plano-mestre.md`, `docs/superpowers/specs/2026-10-14-maquete-cumbuco-design.md`

**Interfaces:**
- Consumes: `terreno.DESTINO_ENTORNO`, `cena.DESTINO` (formato `{"objetos": [{nome, material, vertices, faces}]}`).
- Produces: `entorno.glb`/`entorno.blend` e `loteamento.glb`/`loteamento.blend` na pasta da maquete; `blender.conferir_entorno(nomes, mb) -> list[str]`; `LIMITE_ENTORNO_MB = 3.0`; prévias `cache/cena/previa.png`, `-perto`, `-lagoa`, `-entorno`.

- [ ] **Step 1: Testes**

Em `tests/test_blender.py`:

```python
from scripts.loteamento.blender import conferir_entorno


def test_conferir_entorno_acusa_falta_e_peso():
    assert conferir_entorno(["Entorno", "Mar"], 2.7) == []
    assert conferir_entorno(["Entorno"], 3.4) == ["objeto do entorno faltando no GLB: Mar",
                                                  "entorno.glb com 3.4 MB (alvo 3.0 MB)"]


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_contexto_entra_so_na_previa(tmp_path):
    lote = {"objetos": [{"nome": "Q01L01", "material": "lote_residencial",
                         "vertices": [[0, 0, 1], [5, 0, 1], [0, 5, 1]], "faces": [[0, 1, 2]]}]}
    ctx = {"objetos": [{"nome": "Mar", "material": "mar",
                        "vertices": [[-50, -50, 0], [50, -50, 0], [0, 50, 0]], "faces": [[0, 1, 2]]}]}
    (tmp_path / "l.json").write_text(json.dumps(lote), encoding="utf-8")
    (tmp_path / "c.json").write_text(json.dumps(ctx), encoding="utf-8")
    rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / "l.json"), str(tmp_path / "l.blend"),
                  str(tmp_path / "l.glb"), str(tmp_path / "p.png"), str(tmp_path / "c.json"))
    assert nos_do_glb(tmp_path / "l.glb") == ["Q01L01"]
    assert (tmp_path / "p-entorno.png").exists() and (tmp_path / "p.png").exists()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_blender.py -q`
Expected: FAIL com `ImportError: cannot import name 'conferir_entorno'`.

- [ ] **Step 3: `gerar_loteamento.py`**

- Argumentos: `cena.json saida.blend saida.glb [previa.png] [contexto.json]`; `CONTEXTO = Path(args[4]) if len(args) > 4 else None`.
- `MATERIAIS` ganha `"entorno": ((0.80, 0.74, 0.62), 0.95)` e `"mar": ((0.18, 0.42, 0.55), 0.2)`.
- `construir(dados, nome="Loteamento")`: o nome da coleção vira parâmetro.
- `main`: salva o `.blend` e exporta o GLB como hoje (só a coleção principal); depois, se `CONTEXTO`, `construir(json.loads(CONTEXTO.read_text(...)), "Contexto")`; então a prévia. O contexto não entra no `.blend` nem no GLB.
- `previa(destino, col, ctx=None)`: com lotes na coleção, as vistas de hoje (geral pelos lotes, `-perto`, `-lagoa`); sem lotes, a vista geral pela caixa de todos os vértices da coleção; com `ctx`, mais a vista `-entorno` pela caixa dos vértices do contexto (`raio * 1.1`, como a geral). `_vista` já usa `clip_end = distancia * 10`.

- [ ] **Step 4: `blender.py`**

```python
LIMITE_ENTORNO_MB = 3.0


def conferir_entorno(nomes: list[str], mb: float) -> list[str]:
    erros = [f"objeto do entorno faltando no GLB: {n}" for n in ("Entorno", "Mar") if n not in nomes]
    if mb > LIMITE_ENTORNO_MB:
        erros.append(f"entorno.glb com {mb} MB (alvo {LIMITE_ENTORNO_MB} MB)")
    return erros
```

`main`: primeiro `rodar_blender(blender, SCRIPT, str(ENTORNO_JSON), str(destino / "entorno.blend"), str(destino / "entorno.glb"))` e `conferir_entorno(nos_do_glb(...), resumo["glb_mb"])`; depois o loteamento como hoje, passando `str(PREVIA), str(ENTORNO_JSON)`. Imprime os dois resumos e todos os erros; sai 1 se houver erro. `ENTORNO_JSON` vem de `terreno.DESTINO_ENTORNO`.

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest -q`
Expected: tudo passa.

- [ ] **Step 6: Gerar as saídas reais**

Run: `uv run python -m scripts.loteamento.blender`
Expected: saída 0; resumo do entorno com 2 objetos e < 3 MB; resumo do loteamento com 355 objetos e ≤ 8 MB; na pasta da maquete `entorno.glb`, `entorno.blend`, `loteamento.glb`, `loteamento.blend` e nenhum `.blend1`. Abrir `cache/cena/previa-entorno.png` e `previa.png` (leitura de imagem, não GUI): platô plano visível, morro em volta, mar na direção da costa.

- [ ] **Step 7: Documentação**

- Plano-mestre: linha nova `| 3c | Relevo simplificado (2026-10-14-03c-relevo-plato-entorno.md) | Platô, morro pelo levantamento suavizado, Copernicus até 4 km, entorno.glb (Entorno, Mar) | 3 | — |`; na linha do Plano 4, "raio de 2,5 km" → "raio de 4 km; o relevo do entorno já vem do 3c".
- Spec-mãe: §7.1.3 passa a citar o platô e a spec `2026-10-14-relevo-plato-entorno-design.md`; §7.2 "raio de cerca de 2,5 km" → "raio de 4 km (relevo e mar do Plano 3c)".

- [ ] **Step 8: Commit**

```bash
git add scripts/blender/gerar_loteamento.py scripts/loteamento/blender.py tests/test_blender.py docs/superpowers
git commit -m "feat(blender): entorno.glb e prévia com o entorno; plano-mestre com o 3c"
```
