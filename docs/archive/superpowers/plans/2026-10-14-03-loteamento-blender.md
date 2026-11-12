# Plano 3 — Loteamento no Blender: relevo, lotes, vias e lagoa

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar por script o modelo 3D da Fase 1 (terreno com o relevo das curvas de nível, um objeto por lote com o nome `Q07L04`, vias, calçadas, áreas verdes, APP e lagoa) e exportar `loteamento.glb` e `loteamento.blend` para `6-PROJETOS/10-MAQUETE INTERATIVA/`.

**Architecture:** O método do Benevides: Python puro faz toda a geometria e grava um JSON de cena; o Blender só constrói malhas a partir dele e exporta. `relevo.py` cota as curvas de nível do masterplan pelos rótulos e gera uma grade de 5 m. `malha.py` triangula polígonos com furos, refina até arestas de 6 m e assenta os vértices no relevo. `cena.py` junta tudo em `cache/cena/loteamento.json`. `scripts/blender/gerar_loteamento.py` roda dentro do Blender em modo `-b`, e `scripts/loteamento/blender.py` o chama e confere o GLB.

**Tech Stack:** Python 3.12+, uv, ezdxf, NumPy, SciPy (interpolação), mapbox-earcut (triangulação), Blender 5.2 (`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`), pytest.

**Spec:** `docs/superpowers/specs/2026-10-14-maquete-cumbuco-design.md` (§7.1 passos 3–4, §7.4)
**Consome:** `dados/lotes.json`, `dados/georref.json` (Plano 1), `cache/dxf/planta-venda.dxf`, `cache/dxf/masterplan-r05.dxf`.

## Achados que fixam o plano (14/10/2026)

- As curvas de nível estão no **masterplan R05**, layers `TOP-C-MESTRA` (POLYLINE, 5 em 5 m) e `TOP-C-INTER` (1 em 1 m), **com z = 0**: a cota vem dos TEXT da layer `TOP-C-MESTRA` ("25", "30", "35"…). Na área da Fase 1 há 185 mestras, 348 intermediárias e 95 rótulos.
- A topografia do masterplan está nas **mesmas coordenadas** da planta de venda (os vértices de `TOP-BORDO DE TERRA` coincidem a 0,000 m). Só as layers `AR-*` do masterplan estão deslocadas; elas não são usadas aqui.
- A "LAGOA AZUL" (texto em `ESP-TXT`) cai dentro de um polígono de 3.671 m² da layer `APP_30`. A água é o menor polígono fechado das layers de lagoa que contém esse texto.
- Layers da planta de venda: vias `AR-CNT-VIA-INT` (28 polígonos e 3 círculos de rotatória) e `AR-CNT-VIA-011`; calçadas `AR-CNT-PAS-INT`; verdes `AR-CNT-VRD-INT` e `AR-CNT-VRD-EXT`; institucional `AR-CNT-INT`; fundo de terras `AR-CNT-FND-TER`; APP `APP_30`; poligonal `AR-CNT-POL`.

## Global Constraints

- Nada é modelado à mão: ajuste é mudar parâmetro ou script e rodar de novo; o `.blend` gerado nunca é editado.
- Coordenadas locais: (E − E0, N − N0) em metros a partir de `dados/georref.json`. No Blender, x = leste, y = norte, z = cota; o exportador glTF (`export_yup=True`) entrega x = leste, y = cota, z = −norte, como o contrato do plano-mestre.
- **Um objeto por lote**, com o nome igual ao id do `lotes.json` (`Q07L04`, `QHL01`); 347 objetos, nem mais nem menos.
- Sem exagero vertical.
- Saídas finais em `TERRENO_DIR/6-PROJETOS/10-MAQUETE INTERATIVA/` (`loteamento.glb`, `loteamento.blend`); intermediários em `cache/cena/` (gitignored).
- Peso alvo do `loteamento.glb` sem compressão: até 8 MB (a compressão meshopt e o orçamento de 15 MB ficam no Plano 5).
- Docs e commits em português do Brasil.

## Review Focus

1. **Curva intermediária cotada errado** (por exemplo 30 numa encosta entre 30 e 35) faz degrau no terreno. Teste na Task 1.
2. **Polígono com furo** (via em volta de uma quadra, rotatória com ilha) triangulado como cheio cobre a quadra de asfalto. Teste na Task 2.
3. **Refino que deixa vértice solto no meio de aresta** (T-junction) abre fresta no terreno. Teste na Task 2.
4. **Lote faltando ou sobrando no GLB**, ou com nome trocado: o clique do front não acha a Ficha. Teste na Task 4.
5. **Área fora das curvas** (borda do recorte) sem cota vira NaN e quebra a malha. Teste na Task 1.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `scripts/loteamento/relevo.py` | `Curva`, `cotar_mestras`, `cotar_intermediarias`, `Grade`, `gerar_grade`, CLI → `cache/cena/relevo.json` |
| `scripts/loteamento/malha.py` | `simplificar`, `aninhar`, `triangular`, `refinar`, `drapear` |
| `scripts/loteamento/cena.py` | `CenaCfg`, `aneis_da_layer`, `achar_lagoa`, `montar`, CLI → `cache/cena/loteamento.json` |
| `scripts/loteamento/cena.toml` | Papel → layers da cena, offsets, tolerâncias |
| `scripts/blender/gerar_loteamento.py` | Roda no Blender: JSON → malhas, materiais, `.blend`, GLB, prévia |
| `scripts/loteamento/blender.py` | `nos_do_glb`, `conferir_glb`, `rodar_blender`, CLI |
| `tests/test_relevo.py`, `test_malha.py`, `test_cena.py`, `test_blender.py` | Um por módulo |

---

### Task 1: Relevo pelas curvas de nível

**Files:**
- Create: `scripts/loteamento/relevo.py`, `tests/test_relevo.py`
- Modify: `pyproject.toml` (scipy)

**Interfaces:**
- Produces: `Curva(pontos: list[Ponto], z: float | None = None)`; `cotar_mestras(mestras: list[Curva], rotulos: list[tuple[Ponto, float]], raio: float = 25.0) -> int` (preenche `z`, devolve quantas ficaram sem cota); `cotar_intermediarias(inters: list[Curva], mestras: list[Curva], passo: float = 1.0) -> None`; `Grade(x0, y0, passo, nx, ny, z: list[list[float]])` com `cota(x, y) -> float` (bilinear, com a borda presa) e `para_json()/de_json()`; `gerar_grade(curvas: list[Curva], ext: tuple[float, float, float, float], passo: float) -> Grade`

**Estratégia:** cada rótulo vota na mestra mais próxima (até `raio`); a cota da mestra é o voto mais comum. A intermediária toma a mestra cotada mais próxima (z1, d1) e a mais próxima com cota diferente (z2, d2); z = z1 + (z2 − z1)·d1/(d1 + d2), arredondado ao `passo` e mantido estritamente entre z1 e z2. A grade interpola linearmente (Delaunay) os vértices cotados e usa o vizinho mais próximo fora do casco, para nunca dar NaN.

- [ ] **Step 1: Dependência**

Run: `uv add scipy`

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_relevo.py`:
```python
import math

import pytest

from scripts.loteamento.relevo import Curva, Grade, cotar_intermediarias, cotar_mestras, gerar_grade


def _horizontal(y, x0=0.0, x1=100.0, n=11):
    return Curva([(x0 + (x1 - x0) * i / (n - 1), y) for i in range(n)])


def test_rotulo_cota_a_mestra_mais_proxima():
    m30, m35 = _horizontal(0), _horizontal(50)
    sem = cotar_mestras([m30, m35], [((40, 1.0), 30.0), ((60, 49.0), 35.0), ((70, 48.5), 35.0)])
    assert (m30.z, m35.z, sem) == (30.0, 35.0, 0)


def test_mestra_sem_rotulo_fica_sem_cota():
    m = _horizontal(0)
    assert cotar_mestras([m], [((50, 200.0), 30.0)]) == 1 and m.z is None


def test_intermediarias_entre_30_e_35():
    m30, m35 = Curva(_horizontal(0).pontos, 30.0), Curva(_horizontal(50).pontos, 35.0)
    inters = [_horizontal(y) for y in (10, 20, 30, 40)]
    cotar_intermediarias(inters, [m30, m35])
    assert [c.z for c in inters] == [31.0, 32.0, 33.0, 34.0]


def test_intermediaria_colada_na_mestra_nao_vira_a_mestra():
    m30, m35 = Curva(_horizontal(0).pontos, 30.0), Curva(_horizontal(50).pontos, 35.0)
    c = _horizontal(1)  # quase em cima da de 30
    cotar_intermediarias([c], [m30, m35])
    assert c.z == 31.0


def test_grade_reproduz_um_plano_e_nao_tem_nan_fora_das_curvas():
    curvas = [Curva(_horizontal(y).pontos, 30.0 + y / 10) for y in range(0, 60, 10)]
    g = gerar_grade(curvas, (-50.0, -50.0, 150.0, 120.0), 5.0)
    assert g.cota(50, 25) == pytest.approx(32.5, abs=0.01)
    assert all(not math.isnan(v) for linha in g.z for v in linha)
    assert g.cota(-1000, -1000) == pytest.approx(g.z[0][0])  # borda presa


def test_grade_ida_e_volta_json():
    g = Grade(0.0, 0.0, 5.0, 2, 2, [[1.0, 2.0], [3.0, 4.0]])
    assert Grade.de_json(g.para_json()) == g
    assert g.cota(2.5, 2.5) == pytest.approx(2.5)
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_relevo.py -q`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 4: Implementar `scripts/loteamento/relevo.py`**

```python
"""Relevo da Fase 1: curvas de nível do masterplan cotadas pelos rótulos, em grade regular.

Uso: uv run python -m scripts.loteamento.relevo
"""

import json
import math
import sys
from collections import Counter
from dataclasses import dataclass, field

import ezdxf
import numpy as np
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

from scripts.comum.ambiente import RAIZ

Ponto = tuple[float, float]
DXF = RAIZ / "cache" / "dxf" / "masterplan-r05.dxf"
DESTINO = RAIZ / "cache" / "cena" / "relevo.json"
MARGEM = 150.0  # metros de terreno além da poligonal
PASSO_GRADE = 5.0


@dataclass
class Curva:
    pontos: list[Ponto]
    z: float | None = None


def _dist_polilinha(p: Ponto, pts: list[Ponto]) -> float:
    px, py = p
    melhor = math.inf
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        melhor = min(melhor, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return melhor


def cotar_mestras(mestras: list[Curva], rotulos: list[tuple[Ponto, float]], raio: float = 25.0) -> int:
    votos: list[Counter] = [Counter() for _ in mestras]
    for p, z in rotulos:
        d, i = min((_dist_polilinha(p, c.pontos), i) for i, c in enumerate(mestras))
        if d <= raio:
            votos[i][z] += 1
    for c, v in zip(mestras, votos):
        c.z = v.most_common(1)[0][0] if v else None
    return sum(1 for c in mestras if c.z is None)


def cotar_intermediarias(inters: list[Curva], mestras: list[Curva], passo: float = 1.0) -> None:
    cotadas = [m for m in mestras if m.z is not None]
    for c in inters:
        p = c.pontos[len(c.pontos) // 2]
        dists = sorted((_dist_polilinha(p, m.pontos), m.z) for m in cotadas)
        if not dists:
            continue
        d1, z1 = dists[0]
        outra = next(((d, z) for d, z in dists if z != z1), None)
        if outra is None:
            continue
        d2, z2 = outra
        z = z1 + (z2 - z1) * d1 / (d1 + d2)
        z = round(z / passo) * passo
        sinal = 1 if z2 > z1 else -1
        if (z - z1) * sinal < passo:
            z = z1 + sinal * passo
        if (z2 - z) * sinal < passo:
            z = z2 - sinal * passo
        c.z = float(z)


@dataclass
class Grade:
    x0: float
    y0: float
    passo: float
    nx: int
    ny: int
    z: list[list[float]] = field(repr=False)  # z[j][i], j ao longo de y

    def cota(self, x: float, y: float) -> float:
        fx = min(max((x - self.x0) / self.passo, 0.0), self.nx - 1.0)
        fy = min(max((y - self.y0) / self.passo, 0.0), self.ny - 1.0)
        i, j = min(int(fx), self.nx - 2), min(int(fy), self.ny - 2)
        tx, ty = fx - i, fy - j
        z = self.z
        return (z[j][i] * (1 - tx) + z[j][i + 1] * tx) * (1 - ty) + (z[j + 1][i] * (1 - tx) + z[j + 1][i + 1] * tx) * ty

    def para_json(self) -> dict:
        return {"x0": self.x0, "y0": self.y0, "passo": self.passo, "nx": self.nx, "ny": self.ny, "z": self.z}

    @classmethod
    def de_json(cls, d: dict) -> "Grade":
        return cls(d["x0"], d["y0"], d["passo"], d["nx"], d["ny"], d["z"])


def gerar_grade(curvas: list[Curva], ext: tuple[float, float, float, float], passo: float) -> Grade:
    pts = np.array([(x, y) for c in curvas if c.z is not None for x, y in c.pontos])
    zs = np.array([c.z for c in curvas if c.z is not None for _ in c.pontos])
    xmin, ymin, xmax, ymax = ext
    nx, ny = int(math.ceil((xmax - xmin) / passo)) + 1, int(math.ceil((ymax - ymin) / passo)) + 1
    gx, gy = np.meshgrid(xmin + passo * np.arange(nx), ymin + passo * np.arange(ny))
    z = LinearNDInterpolator(pts, zs)(gx, gy)
    vazio = np.isnan(z)
    if vazio.any():
        z[vazio] = NearestNDInterpolator(pts, zs)(gx[vazio], gy[vazio])
    return Grade(float(xmin), float(ymin), float(passo), nx, ny, np.round(z, 2).tolist())


def _densificar(pts: list[Ponto], passo: float = 10.0) -> list[Ponto]:
    saida = [pts[0]]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) // passo))
        saida += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(1, n + 1)]
    return saida


def main() -> int:
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    xs = [x for l in lotes for x, _ in l["poligono"]]
    ys = [y for l in lotes for _, y in l["poligono"]]
    ext = (min(xs) - MARGEM, min(ys) - MARGEM, max(xs) + MARGEM, max(ys) + MARGEM)
    perto = lambda pts: any(ext[0] - 50 <= x <= ext[2] + 50 and ext[1] - 50 <= y <= ext[3] + 50 for x, y in pts)  # noqa: E731

    msp = ezdxf.readfile(DXF).modelspace()
    local = lambda e: [(p.x - e0, p.y - n0) for p in e.points()]  # noqa: E731
    mestras = [Curva(_densificar(pts)) for e in msp.query('POLYLINE[layer=="TOP-C-MESTRA"]') if perto(pts := local(e))]
    inters = [Curva(_densificar(pts)) for e in msp.query('POLYLINE[layer=="TOP-C-INTER"]') if perto(pts := local(e))]
    rotulos = []
    for t in msp.query('TEXT[layer=="TOP-C-MESTRA"]'):
        try:
            rotulos.append(((t.dxf.insert.x - e0, t.dxf.insert.y - n0), float(t.dxf.text.replace(",", "."))))
        except ValueError:
            continue
    sem = cotar_mestras(mestras, rotulos)
    cotar_intermediarias(inters, mestras)
    grade = gerar_grade(mestras + inters, ext, PASSO_GRADE)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(grade.para_json()), encoding="utf-8")
    zs = [v for linha in grade.z for v in linha]
    print(
        f"mestras {len(mestras)} ({sem} sem cota) · intermediárias {len(inters)} "
        f"({sum(c.z is None for c in inters)} sem cota) · grade {grade.nx}×{grade.ny} · cota {min(zs):.1f}–{max(zs):.1f} m"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_relevo.py -q`
Expected: 6 passed

- [ ] **Step 6: Rodar com as curvas reais**

Run: `uv run python -m scripts.loteamento.relevo`
Expected: uma linha com as contagens. Aceite até 10% de mestras sem cota (rótulo fora do recorte); acima disso, leia onde estão os rótulos antes de mexer no `raio`. A faixa de cota deve ficar dentro da dos rótulos (cerca de 5 a 45 m).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock scripts/loteamento/relevo.py tests/test_relevo.py
git commit -m "feat(cena): relevo pelas curvas de nível cotadas pelos rótulos"
```

---

### Task 2: Malha: triangulação com furos, refino e assentamento

**Files:**
- Create: `scripts/loteamento/malha.py`, `tests/test_malha.py`
- Modify: `pyproject.toml` (mapbox-earcut)

**Interfaces:**
- Consumes: `Grade` (Task 1), `geometria.contem`, `geometria.area`
- Produces: `simplificar(anel: list[Ponto], tol: float) -> list[Ponto]`; `aninhar(aneis: list[list[Ponto]]) -> list[tuple[list[Ponto], list[list[Ponto]]]]`; `triangular(externo, furos) -> tuple[list[Ponto], list[tuple[int, int, int]]]`; `refinar(verts, tris, max_aresta: float) -> tuple[list[Ponto], list[tuple[int, int, int]]]`; `drapear(verts, grade, offset: float) -> list[list[float]]`

- [ ] **Step 1: Dependência**

Run: `uv add mapbox-earcut`

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_malha.py`:
```python
from collections import Counter

import pytest

from scripts.loteamento.geometria import area
from scripts.loteamento.malha import aninhar, drapear, refinar, simplificar, triangular
from scripts.loteamento.relevo import Grade

QUADRADO = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
FURO = [(40.0, 40.0), (60.0, 40.0), (60.0, 60.0), (40.0, 60.0)]


def _area_tris(verts, tris):
    return sum(area([verts[a], verts[b], verts[c]]) for a, b, c in tris)


def test_simplificar_tira_ponto_colinear_e_mantem_cantos():
    anel = [(0.0, 0.0), (50.0, 0.001), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
    assert simplificar(anel, 0.05) == QUADRADO


def test_aninhar_reconhece_furo_e_ilha_dentro_do_furo():
    ilha = [(45.0, 45.0), (55.0, 45.0), (55.0, 55.0), (45.0, 55.0)]
    grupos = aninhar([FURO, QUADRADO, ilha])
    externos = sorted(area(e) for e, _ in grupos)
    assert externos == [100.0, 10000.0]
    grande = next(f for e, f in grupos if area(e) == 10000.0)
    assert grande == [FURO]


def test_triangular_respeita_o_furo():
    verts, tris = triangular(QUADRADO, [FURO])
    assert _area_tris(verts, tris) == pytest.approx(10000 - 400)


def test_refinar_limita_aresta_preserva_area_e_nao_deixa_frestas():
    verts, tris = refinar(*triangular(QUADRADO, []), 10.0)
    assert _area_tris(verts, tris) == pytest.approx(10000)
    arestas = Counter(tuple(sorted(e)) for a, b, c in tris for e in ((a, b), (b, c), (c, a)))
    for (i, j), n in arestas.items():
        (xa, ya), (xb, yb) = verts[i], verts[j]
        assert ((xa - xb) ** 2 + (ya - yb) ** 2) ** 0.5 <= 10.0 + 1e-9
        if n == 1:  # aresta de borda: tem de estar no contorno do quadrado
            assert xa == xb in (0.0, 100.0) or ya == yb in (0.0, 100.0)
        else:
            assert n == 2


def test_drapear_soma_offset_a_cota():
    g = Grade(0.0, 0.0, 10.0, 2, 2, [[10.0, 20.0], [10.0, 20.0]])
    assert drapear([(5.0, 5.0)], g, 0.1) == [[5.0, 5.0, 15.1]]
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_malha.py -q`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 4: Implementar `scripts/loteamento/malha.py`**

```python
"""Malhas da cena: polígonos (com furos) → triângulos refinados e assentados no relevo."""

import math

import mapbox_earcut
import numpy as np

from .geometria import Ponto, area, contem
from .relevo import Grade

Tri = tuple[int, int, int]


def _dist_reta(p: Ponto, a: Ponto, b: Ponto) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy)
    return math.hypot(px - ax, py - ay) if n == 0 else abs(dy * (px - ax) - dx * (py - ay)) / n


def _dp(pts: list[Ponto], tol: float) -> list[Ponto]:
    if len(pts) < 3:
        return pts
    i, d = max(((k, _dist_reta(pts[k], pts[0], pts[-1])) for k in range(1, len(pts) - 1)), key=lambda t: t[1])
    if d <= tol:
        return [pts[0], pts[-1]]
    return _dp(pts[: i + 1], tol)[:-1] + _dp(pts[i:], tol)


def simplificar(anel: list[Ponto], tol: float) -> list[Ponto]:
    """Douglas–Peucker num anel fechado, partindo do vértice mais distante do primeiro."""
    if len(anel) <= 4:
        return list(anel)
    k = max(range(len(anel)), key=lambda i: math.dist(anel[0], anel[i]))
    ida = _dp(anel[: k + 1], tol)
    volta = _dp(anel[k:] + anel[:1], tol)
    return ida[:-1] + volta[:-1]


def aninhar(aneis: list[list[Ponto]]) -> list[tuple[list[Ponto], list[list[Ponto]]]]:
    """Profundidade par = contorno externo; ímpar = furo do anel imediatamente de fora."""
    ordem = sorted(aneis, key=area, reverse=True)
    pais: list[int | None] = []
    for i, anel in enumerate(ordem):
        de_fora = [j for j in range(i) if contem(ordem[j], anel[0])]
        pais.append(de_fora[-1] if de_fora else None)
    profundidade = []
    for i, pai in enumerate(pais):
        profundidade.append(0 if pai is None else profundidade[pai] + 1)
    grupos = {i: (ordem[i], []) for i, p in enumerate(profundidade) if p % 2 == 0}
    for i, p in enumerate(profundidade):
        if p % 2 == 1:
            grupos[pais[i]][1].append(ordem[i])
    return list(grupos.values())


def triangular(externo: list[Ponto], furos: list[list[Ponto]]) -> tuple[list[Ponto], list[Tri]]:
    aneis = [externo, *furos]
    verts = [p for a in aneis for p in a]
    fins = np.cumsum([len(a) for a in aneis]).astype(np.uint32)
    idx = mapbox_earcut.triangulate_float64(np.array(verts, dtype=np.float64), fins)
    return verts, [tuple(int(v) for v in idx[k : k + 3]) for k in range(0, len(idx), 3)]


def refinar(verts: list[Ponto], tris: list[Tri], max_aresta: float) -> tuple[list[Ponto], list[Tri]]:
    """Divide toda aresta maior que max_aresta no meio (o meio é compartilhado: sem T-junction)."""
    verts = list(verts)
    tris = list(tris)
    while True:
        longa = lambda a, b: math.dist(verts[a], verts[b]) > max_aresta  # noqa: E731
        meios: dict[tuple[int, int], int] = {}

        def meio(a: int, b: int) -> int:
            k = (min(a, b), max(a, b))
            if k not in meios:
                (xa, ya), (xb, yb) = verts[a], verts[b]
                verts.append(((xa + xb) / 2, (ya + yb) / 2))
                meios[k] = len(verts) - 1
            return meios[k]

        divide = {tuple(sorted(e)) for a, b, c in tris for e in ((a, b), (b, c), (c, a)) if longa(*e)}
        if not divide:
            return verts, tris
        novos: list[Tri] = []
        for t in tris:
            # gira o triângulo para pôr as arestas divididas na frente, mantendo a orientação
            for r in range(3):
                a, b, c = t[r:] + t[:r]
                s = [tuple(sorted(e)) in divide for e in ((a, b), (b, c), (c, a))]
                if s in ([False, False, False], [True, True, True], [True, False, False], [True, True, False]):
                    break
            if s == [False, False, False]:
                novos.append((a, b, c))
            elif s == [True, True, True]:
                m1, m2, m3 = meio(a, b), meio(b, c), meio(c, a)
                novos += [(a, m1, m3), (m1, b, m2), (m3, m2, c), (m1, m2, m3)]
            elif s == [True, False, False]:
                m1 = meio(a, b)
                novos += [(a, m1, c), (m1, b, c)]
            else:  # [True, True, False]
                m1, m2 = meio(a, b), meio(b, c)
                novos += [(m1, b, m2), (a, m1, m2), (a, m2, c)]
        tris = novos


def drapear(verts: list[Ponto], grade: Grade, offset: float) -> list[list[float]]:
    return [[round(x, 2), round(y, 2), round(grade.cota(x, y) + offset, 2)] for x, y in verts]
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_malha.py -q`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock scripts/loteamento/malha.py tests/test_malha.py
git commit -m "feat(cena): triangulação com furos, refino conforme e assentamento no relevo"
```

---

### Task 3: Cena do loteamento em JSON

**Files:**
- Create: `scripts/loteamento/cena.py`, `scripts/loteamento/cena.toml`, `tests/test_cena.py`
- Gera (fora do git): `cache/cena/loteamento.json`

**Interfaces:**
- Consumes: `relevo.Grade`, `malha.*`, `geometria.pontos_de`, `geometria.poligono_fechado`, `geometria.contem`, `geometria.area`, `dados/lotes.json`, `dados/georref.json`
- Produces: `CenaCfg` (`camadas: dict[str, list[str]]`, `lagoa_camadas: list[str]`, `lagoa_texto: str`, `offsets: dict[str, float]`, `tolerancia: float`, `max_aresta: float`) e `CenaCfg.carregar(caminho)`; `aneis_da_layer(msp, layers, e0, n0) -> list[list[Ponto]]` (LWPOLYLINE fechada e CIRCLE); `achar_lagoa(msp, cfg, e0, n0) -> list[Ponto] | None`; `montar(msp, grade, lotes: list[dict], cfg, e0, n0) -> dict` (`{"objetos": [{"nome", "material", "vertices", "faces"}]}`)

**Objetos da cena:** `Terreno` (grade inteira, material `terreno`); um objeto por papel de área (`Vias`, `Calcadas`, `Verdes`, `Institucional`, `Fundo`, `APP`), cada um juntando todos os polígonos do papel; `Lagoa` (plana, na menor cota da margem); e um objeto por lote, com o nome do id e o material `lote_residencial` ou `lote_uso_misto`.

- [ ] **Step 1: Criar `scripts/loteamento/cena.toml`**

```toml
# Papel → layers do PLANTA VENDA.dwg usadas na cena 3D (inventário em dados/inventario-layers.md).
tolerancia = 0.05   # m, simplificação dos contornos
max_aresta = 6.0    # m, refino para acompanhar o relevo
lagoa_camadas = ["APP_30"]
lagoa_texto = "LAGOA AZUL"

[camadas]
Vias = ["AR-CNT-VIA-INT", "AR-CNT-VIA-011"]
Calcadas = ["AR-CNT-PAS-INT"]
Verdes = ["AR-CNT-VRD-INT", "AR-CNT-VRD-EXT"]
Institucional = ["AR-CNT-INT"]
Fundo = ["AR-CNT-FND-TER"]
APP = ["APP_30"]

[offsets]   # m acima do terreno, para não brigar com ele (z-fighting)
Vias = 0.06
Calcadas = 0.10
Verdes = 0.04
Institucional = 0.04
Fundo = 0.04
APP = 0.03
lote = 0.15
```

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_cena.py`:
```python
import ezdxf
import pytest

from scripts.loteamento.cena import CenaCfg, achar_lagoa, aneis_da_layer, montar
from scripts.loteamento.geometria import area
from scripts.loteamento.relevo import Grade

E0, N0 = 500_000.0, 9_600_000.0
CFG = CenaCfg(
    camadas={"Vias": ["VIA"], "APP": ["APP"]},
    lagoa_camadas=["APP"],
    lagoa_texto="LAGOA AZUL",
    offsets={"Vias": 0.06, "APP": 0.03, "lote": 0.15},
    tolerancia=0.05,
    max_aresta=6.0,
)


def _ret(x, y, w, h):
    return [(E0 + x, N0 + y), (E0 + x + w, N0 + y), (E0 + x + w, N0 + y + h), (E0 + x, N0 + y + h)]


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


def test_circulo_vira_anel(msp):
    aneis = aneis_da_layer(msp, ["VIA"], E0, N0)
    assert len(aneis) == 2
    assert sorted(round(area(a)) for a in aneis) == [314, 10000]


def test_lagoa_e_o_menor_poligono_com_o_texto(msp):
    lagoa = achar_lagoa(msp, CFG, E0, N0)
    assert round(area(lagoa)) == 1600


def test_montar_objetos_com_furos_e_lotes_nomeados(msp):
    cena = montar(msp, GRADE, LOTES, CFG, E0, N0)
    por_nome = {o["nome"]: o for o in cena["objetos"]}
    assert {"Terreno", "Vias", "APP", "Lagoa", "Q01L01"} <= set(por_nome)
    vias = por_nome["Vias"]
    a = sum(area([vias["vertices"][i][:2] for i in f]) for f in vias["faces"])
    assert a == pytest.approx(10000 - 314.16, rel=0.01)  # a ilha fica de fora
    app = por_nome["APP"]
    a_app = sum(area([app["vertices"][i][:2] for i in f]) for f in app["faces"])
    assert a_app == pytest.approx(10000 - 1600, rel=0.01)  # a lagoa é furo da APP
    assert por_nome["Q01L01"]["material"] == "lote_residencial"
    assert all(v[2] == pytest.approx(10.15) for v in por_nome["Q01L01"]["vertices"])
    assert all(v[2] == pytest.approx(10.0) for v in por_nome["Lagoa"]["vertices"])


def test_cfg_carrega_do_toml():
    from scripts.comum.ambiente import RAIZ

    cfg = CenaCfg.carregar(RAIZ / "scripts" / "loteamento" / "cena.toml")
    assert "Vias" in cfg.camadas and cfg.offsets["lote"] > max(v for k, v in cfg.offsets.items() if k != "lote")
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_cena.py -q`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 4: Implementar `scripts/loteamento/cena.py`**

```python
"""Cena 3D do loteamento em JSON (malhas prontas). O Blender só constrói o que está aqui.

Uso: uv run python -m scripts.loteamento.cena
"""

import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import ezdxf
from ezdxf import path as ezpath

from scripts.comum.ambiente import RAIZ

from .geometria import Ponto, area, contem, poligono_fechado, pontos_de
from .malha import aninhar, drapear, refinar, simplificar, triangular
from .relevo import DESTINO as RELEVO_JSON
from .relevo import Grade

DXF = RAIZ / "cache" / "dxf" / "planta-venda.dxf"
CFG_TOML = RAIZ / "scripts" / "loteamento" / "cena.toml"
DESTINO = RAIZ / "cache" / "cena" / "loteamento.json"


@dataclass(frozen=True)
class CenaCfg:
    camadas: dict[str, list[str]]
    lagoa_camadas: list[str]
    lagoa_texto: str
    offsets: dict[str, float]
    tolerancia: float
    max_aresta: float

    @classmethod
    def carregar(cls, caminho: Path) -> "CenaCfg":
        return cls(**tomllib.loads(caminho.read_text(encoding="utf-8")))


def aneis_da_layer(msp, layers: list[str], e0: float, n0: float) -> list[list[Ponto]]:
    aneis = []
    for e in msp:
        if e.dxf.layer not in layers:
            continue
        if e.dxftype() == "LWPOLYLINE" and poligono_fechado(e):
            pts = pontos_de(e, 0.1)
        elif e.dxftype() == "CIRCLE":
            pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(distance=0.1)][:-1]
        else:
            continue
        aneis.append([(x - e0, y - n0) for x, y in pts])
    return aneis


def achar_lagoa(msp, cfg: CenaCfg, e0: float, n0: float) -> list[Ponto] | None:
    alvos = [
        (t.dxf.insert.x - e0, t.dxf.insert.y - n0)
        for t in msp.query("TEXT MTEXT")
        if cfg.lagoa_texto in (t.dxf.text if t.dxftype() == "TEXT" else t.plain_text()).upper()
    ]
    candidatos = [a for a in aneis_da_layer(msp, cfg.lagoa_camadas, e0, n0) if any(contem(a, p) for p in alvos)]
    return min(candidatos, key=area) if candidatos else None


def _malha(grupos, grade: Grade, offset: float, cfg: CenaCfg) -> tuple[list[list[float]], list[list[int]]]:
    vertices, faces = [], []
    for externo, furos in grupos:
        v, t = triangular(simplificar(externo, cfg.tolerancia), [simplificar(f, cfg.tolerancia) for f in furos])
        v, t = refinar(v, t, cfg.max_aresta)
        base = len(vertices)
        vertices += drapear(v, grade, offset)
        faces += [[base + a, base + b, base + c] for a, b, c in t]
    return vertices, faces


def _terreno(grade: Grade) -> dict:
    vs = [[round(grade.x0 + i * grade.passo, 2), round(grade.y0 + j * grade.passo, 2), grade.z[j][i]]
          for j in range(grade.ny) for i in range(grade.nx)]
    fs = []
    for j in range(grade.ny - 1):
        for i in range(grade.nx - 1):
            a = j * grade.nx + i
            fs += [[a, a + 1, a + grade.nx + 1], [a, a + grade.nx + 1, a + grade.nx]]
    return {"nome": "Terreno", "material": "terreno", "vertices": vs, "faces": fs}


def montar(msp, grade: Grade, lotes: list[dict], cfg: CenaCfg, e0: float, n0: float) -> dict:
    objetos = [_terreno(grade)]
    lagoa = achar_lagoa(msp, cfg, e0, n0)
    for papel, layers in cfg.camadas.items():
        aneis = aneis_da_layer(msp, layers, e0, n0)
        if not aneis:
            continue
        v, f = _malha(aninhar(aneis), grade, cfg.offsets[papel], cfg)
        objetos.append({"nome": papel, "material": papel.lower(), "vertices": v, "faces": f})
    if lagoa:
        nivel = min(grade.cota(x, y) for x, y in lagoa)
        v, t = triangular(simplificar(lagoa, cfg.tolerancia), [])
        objetos.append({"nome": "Lagoa", "material": "agua",
                        "vertices": [[round(x, 2), round(y, 2), round(nivel, 2)] for x, y in v],
                        "faces": [list(f) for f in t]})
    for l in lotes:
        anel = [(x, y) for x, y in l["poligono"]]
        v, f = _malha([(anel, [])], grade, cfg.offsets["lote"], cfg)
        objetos.append({"nome": l["id"], "material": f"lote_{l['tipo']}", "vertices": v, "faces": f})
    return {"objetos": objetos}


def main() -> int:
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    grade = Grade.de_json(json.loads(RELEVO_JSON.read_text(encoding="utf-8")))
    cena = montar(ezdxf.readfile(DXF).modelspace(), grade, lotes, CenaCfg.carregar(CFG_TOML), e0, n0)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(cena), encoding="utf-8")
    tris = {o["nome"]: len(o["faces"]) for o in cena["objetos"]}
    lotes_n = sum(1 for n in tris if n.startswith("Q"))
    print(f"{len(tris)} objetos ({lotes_n} lotes) · {sum(tris.values())} triângulos · "
          + ", ".join(f"{n} {t}" for n, t in tris.items() if not n.startswith("Q")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_cena.py -q`
Expected: 4 passed

- [ ] **Step 6: Gerar a cena real**

Run: `uv run python -m scripts.loteamento.cena`
Expected: 347 lotes e os objetos de área, com algumas centenas de milhares de triângulos no total. Se `Lagoa` faltar, o texto não caiu em nenhum polígono das `lagoa_camadas`: ajuste o `cena.toml` (não o código).

- [ ] **Step 7: Commit**

```bash
git add scripts/loteamento/cena.py scripts/loteamento/cena.toml tests/test_cena.py
git commit -m "feat(cena): cena do loteamento em JSON (terreno, áreas, lagoa e lotes)"
```

---

### Task 4: Blender: construir, exportar e conferir

**Files:**
- Create: `scripts/blender/gerar_loteamento.py`, `scripts/loteamento/blender.py`, `tests/test_blender.py`
- Modify: `.env.example` (`BLENDER`)
- Gera: `TERRENO_DIR/6-PROJETOS/10-MAQUETE INTERATIVA/loteamento.glb` e `loteamento.blend`; `cache/cena/previa.png`

**Interfaces:**
- Consumes: `cache/cena/loteamento.json`, `dados/lotes.json`, `ambiente.*`
- Produces: `nos_do_glb(caminho: Path) -> list[str]`; `conferir_glb(nomes: list[str], ids: list[str]) -> list[str]` (erros); `rodar_blender(blender: Path, script: Path, *args: str) -> dict` (o resumo JSON que o script imprime na linha `RESUMO {...}`)

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_blender.py`:
```python
import json
import struct
from pathlib import Path

import pytest

from scripts.loteamento.blender import BLENDER_PADRAO, SCRIPT, conferir_glb, nos_do_glb, rodar_blender


def _glb(caminho: Path, nomes: list[str]) -> None:
    js = json.dumps({"asset": {"version": "2.0"}, "nodes": [{"name": n} for n in nomes]}).encode()
    js += b" " * (-len(js) % 4)
    caminho.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js)) + struct.pack("<II", len(js), 0x4E4F534A) + js)


def test_nos_do_glb(tmp_path):
    _glb(tmp_path / "a.glb", ["Terreno", "Q01L01"])
    assert nos_do_glb(tmp_path / "a.glb") == ["Terreno", "Q01L01"]


def test_conferir_glb_acusa_falta_e_sobra():
    erros = conferir_glb(["Terreno", "Q01L01", "Q09L09"], ["Q01L01", "Q01L02"])
    assert erros == ["lote sem objeto no GLB: Q01L02", "objeto de lote sem linha no lotes.json: Q09L09"]


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_blender_constroi_e_exporta_com_os_nomes(tmp_path):
    cena = {"objetos": [
        {"nome": "Terreno", "material": "terreno", "vertices": [[0, 0, 0], [10, 0, 0], [0, 10, 1]], "faces": [[0, 1, 2]]},
        {"nome": "Q01L01", "material": "lote_residencial", "vertices": [[0, 0, 1], [5, 0, 1], [0, 5, 1]], "faces": [[0, 1, 2]]},
    ]}
    (tmp_path / "cena.json").write_text(json.dumps(cena), encoding="utf-8")
    resumo = rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / "cena.json"), str(tmp_path / "l.blend"), str(tmp_path / "l.glb"))
    assert set(nos_do_glb(tmp_path / "l.glb")) == {"Terreno", "Q01L01"}
    assert (tmp_path / "l.blend").exists() and resumo["objetos"] == 2
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_blender.py -q`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Implementar `scripts/blender/gerar_loteamento.py`** (roda dentro do Blender)

```python
"""Constrói o loteamento a partir de cache/cena/loteamento.json. Roda dentro do Blender:

    blender -b --factory-startup --python-exit-code 1 -P gerar_loteamento.py -- cena.json saida.blend saida.glb [previa.png]

Não calcula geometria: só cria malhas, materiais e exporta. Ajuste é no Python de fora.
"""

import json
import math
import sys
from pathlib import Path

import bpy

args = sys.argv[sys.argv.index("--") + 1 :]
CENA, BLEND, GLB = (Path(a) for a in args[:3])
PREVIA = Path(args[3]) if len(args) > 3 else None

# Cores de cena (ambiente, não marca): sRGB 0–1 e rugosidade.
MATERIAIS = {
    "terreno": ((0.86, 0.80, 0.68), 0.95),
    "vias": ((0.42, 0.42, 0.44), 0.9),
    "calcadas": ((0.82, 0.80, 0.76), 0.9),
    "verdes": ((0.52, 0.62, 0.40), 0.95),
    "institucional": ((0.66, 0.70, 0.56), 0.95),
    "fundo": ((0.60, 0.66, 0.48), 0.95),
    "app": ((0.44, 0.56, 0.38), 0.95),
    "agua": ((0.30, 0.55, 0.62), 0.15),
    "lote_residencial": ((0.93, 0.89, 0.80), 0.8),
    "lote_uso_misto": ((0.85, 0.76, 0.62), 0.8),
}


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material(nome: str) -> bpy.types.Material:
    if nome in bpy.data.materials:
        return bpy.data.materials[nome]
    cor, rug = MATERIAIS.get(nome, ((1.0, 0.0, 1.0), 0.5))
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*(_linear(c) for c in cor), 1.0)
    bsdf.inputs["Roughness"].default_value = rug
    m.diffuse_color = (*(_linear(c) for c in cor), 1.0)
    return m


def construir(dados: dict) -> bpy.types.Collection:
    col = bpy.data.collections.new("Loteamento")
    bpy.context.scene.collection.children.link(col)
    for o in dados["objetos"]:
        me = bpy.data.meshes.new(o["nome"])
        me.from_pydata(o["vertices"], [], o["faces"])
        me.validate()
        me.update()
        me.materials.append(material(o["material"]))
        if o["nome"] == "Terreno":
            me.shade_smooth()
        ob = bpy.data.objects.new(o["nome"], me)
        col.objects.link(ob)
    return col


def previa(destino: Path) -> None:
    cena = bpy.context.scene
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cena.collection.objects.link(cam)
    cam.location = (-650.0, -900.0, 650.0)
    cam.rotation_euler = (math.radians(58), 0.0, math.radians(-35))
    cam.data.lens = 35
    cena.camera = cam
    try:
        cena.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    cena.display.shading.color_type = "MATERIAL"
    cena.render.resolution_x, cena.render.resolution_y = 1600, 1000
    cena.render.filepath = str(destino)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dados = json.loads(CENA.read_text(encoding="utf-8"))
    col = construir(dados)
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    bpy.ops.object.select_all(action="DESELECT")
    for ob in col.objects:
        ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True, export_texcoords=False)
    if PREVIA:
        previa(PREVIA)
    tris = sum(len(p.vertices) - 2 for ob in col.objects for p in ob.data.polygons)
    print("RESUMO " + json.dumps({"objetos": len(col.objects), "triangulos": tris,
                                   "glb_mb": round(GLB.stat().st_size / 1e6, 2)}))


main()
```

- [ ] **Step 4: Implementar `scripts/loteamento/blender.py`**

```python
"""Roda o Blender sobre a cena do loteamento e confere o GLB. Uso: uv run python -m scripts.loteamento.blender"""

import json
import struct
import subprocess
import sys
from pathlib import Path

from scripts.comum.ambiente import RAIZ, ler_env, terreno_dir

from .cena import DESTINO as CENA_JSON

BLENDER_PADRAO = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
SCRIPT = RAIZ / "scripts" / "blender" / "gerar_loteamento.py"
PASTA_MAQUETE = "6-PROJETOS/10-MAQUETE INTERATIVA"
PREVIA = RAIZ / "cache" / "cena" / "previa.png"
LIMITE_MB = 8.0


def nos_do_glb(caminho: Path) -> list[str]:
    dados = caminho.read_bytes()
    tamanho, tipo = struct.unpack_from("<II", dados, 12)
    if tipo != 0x4E4F534A:
        raise ValueError(f"{caminho}: primeiro bloco do GLB não é JSON")
    gltf = json.loads(dados[20 : 20 + tamanho])
    return [n.get("name", "") for n in gltf.get("nodes", [])]


def conferir_glb(nomes: list[str], ids: list[str]) -> list[str]:
    lotes_glb = {n for n in nomes if n.startswith("Q")}
    erros = [f"lote sem objeto no GLB: {i}" for i in sorted(set(ids) - lotes_glb)]
    erros += [f"objeto de lote sem linha no lotes.json: {n}" for n in sorted(lotes_glb - set(ids))]
    return erros


def rodar_blender(blender: Path, script: Path, *args: str) -> dict:
    r = subprocess.run(
        [str(blender), "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(script), "--", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
    )
    linha = next((l for l in r.stdout.splitlines() if l.startswith("RESUMO ")), None)
    if r.returncode != 0 or linha is None:
        raise RuntimeError(f"Blender falhou (código {r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return json.loads(linha[len("RESUMO "):])


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    blender = Path(ler_env(RAIZ / ".env").get("BLENDER", BLENDER_PADRAO))
    destino = terreno_dir() / PASTA_MAQUETE
    glb, blend = destino / "loteamento.glb", destino / "loteamento.blend"
    resumo = rodar_blender(blender, SCRIPT, str(CENA_JSON), str(blend), str(glb), str(PREVIA))
    ids = [l["id"] for l in json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]]
    erros = conferir_glb(nos_do_glb(glb), ids)
    if resumo["glb_mb"] > LIMITE_MB:
        erros.append(f"loteamento.glb com {resumo['glb_mb']} MB (alvo {LIMITE_MB} MB)")
    print(json.dumps(resumo, ensure_ascii=False), *erros, sep="\n")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
```

Acrescentar ao `.env.example` (e ao `.env`):
```
BLENDER=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_blender.py -q`
Expected: 3 passed (o terceiro roda o Blender de verdade, alguns segundos).

- [ ] **Step 6: Gerar o loteamento real**

Run, em ordem: `uv run python -m scripts.loteamento.relevo`, `uv run python -m scripts.loteamento.cena`, `uv run python -m scripts.loteamento.blender`
Expected: saída 0, resumo com `objetos` = 347 + os objetos de área, `glb_mb` ≤ 8, e os arquivos em `6-PROJETOS/10-MAQUETE INTERATIVA/`. Abra `cache/cena/previa.png` com o Read e confira: relevo sem degraus, vias com as quadras vazadas, lagoa no lugar, lotes por cima do terreno. Problema de geometria volta para o script certo (relevo, malha ou cena), nunca para o `.blend`.

- [ ] **Step 7: Commit**

```bash
git add scripts/blender/gerar_loteamento.py scripts/loteamento/blender.py tests/test_blender.py .env.example
git commit -m "feat(cena): loteamento no Blender, GLB e .blend na pasta do terreno"
```

Os `.blend` e GLB ficam na pasta do terreno (fora do git). Antes de qualquer sync com o Drive, rodar `python sync_drive_viabilidades.py --check --json` na raiz das viabilidades e mostrar o `plan` ao Abner (regra do `AGENTS.md` de lá).

---

## Fim do Plano 3

**Entregue:** `loteamento.glb` e `loteamento.blend` reproduzíveis por `relevo` → `cena` → `blender`, com 347 objetos de lote nomeados pelo id.

**Próximo:** Plano 3b (marcos: estande pelo KMZ e pela v10c, portaria pelo `.blend` existente, clube pelo estudo de 2024), escrito depois de investigar essas fontes; e o Plano 4 (entorno), que costura o Copernicus na borda desta grade.
