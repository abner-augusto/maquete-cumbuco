# Plano 4 — Entorno, vegetação e pontos

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vestir o entorno de 4 km: vias e áreas do OSM pintadas no relevo, vias principais perto do loteamento em faixa 3D, prédios extrudados, vegetação instanciada (coqueiro, cajueiro, arbusto de restinga) e os 15 pontos aprovados com coordenada do OSM, minutos de carro e candidatos de foto livre.

**Architecture:** Derivado do pipeline `scripts/entorno` do Manoa (`$REPOS_DIR/cv_espelho_vendas`), mas sobre o relevo do Plano 3c em vez de um plano. `extrair.py` baixa OSM (Overpass) e Overture e grava `cache/entorno/base.json` em coordenadas locais (pyproj, origem do `georref.json`). `preparar.py` monta o mapa do chão (imagem de 2 m/px pintada com vias e áreas, aplicada por UV ao `Entorno` e ao `Terreno`) e a cena de detalhe (`ViasPrincipais` em faixa 3D até 1,5 km e `Predios` até 1,5 km), assentadas pelo `Relevo` (grade perto + Copernicus ajustado). `vegetacao.py` grava as instâncias com cota; o Blender gera as três espécies. `scripts/pontos/pontos.py` casa cada ponto da curadoria no OSM (Nominatim), calcula os minutos de carro no grafo viário e lista fotos candidatas do Wikimedia Commons.

**Tech Stack:** Python 3.12+, uv, shapely, overturemaps, pyproj, Pillow, NumPy, Blender 5.2, pytest.

**Spec:** `docs/superpowers/specs/2026-10-14-maquete-cumbuco-design.md` (§7.2 Entorno, §7.3 Vegetação, Pontos e Mídia) e `2026-10-14-relevo-plato-entorno-design.md` (relevo e mar).
**Consome:** `cache/cena/terreno.json`, `entorno.json` (3c), `cache/cena/loteamento.json`, `dados/georref.json`, `dados/lotes.json`, `cache/dxf/planta-venda.dxf`, `scripts/pontos/curadoria.json` (15 pontos aprovados em 14/10/2026).

## Decisões do usuário (14/10/2026)

- Pontos: busca até o Pecém (22 km), 15 escolhidos e aprovados (`scripts/pontos/curadoria.json`).
- Chão: **mistura** — vias principais perto do loteamento em faixa 3D (como no Manoa); ruas locais, internas das quadras e o resto das vias e áreas **pintados no relevo**.
- Fotos: Wikimedia Commons com licença livre (ou próprias), aprovadas pelo usuário ⛔; foto do Google não entra (termos de uso). A coordenada publicada vem do OSM; o `place_id` do Google fica só na curadoria.

## Global Constraints

- Coordenadas locais: (E − E0, N − N0) do `dados/georref.json` (EPSG:31984) — a mesma projeção do loteamento; nada de equirretangular.
- Nada é modelado nem digitado à mão em `dados/`: `pontos.json` sai do script; a curadoria (`scripts/pontos/curadoria.json`) é a única fonte editada.
- Sem exagero vertical; tudo assentado no relevo do 3c (`Relevo`).
- Saídas em `TERRENO_DIR/6-PROJETOS/10-MAQUETE INTERATIVA/`: `entorno.glb/.blend` (com `Entorno`, `Mar`, `ViasPrincipais`, `Predios`), `loteamento.glb/.blend`, `vegetacao.glb`, `vegetacao.json`; sem `.blend1`. Intermediários em `cache/`.
- Orçamento sem compressão: `entorno.glb` ≤ 8 MB, `loteamento.glb` ≤ 8 MB, `vegetacao.glb` ≤ 0,5 MB (meshopt no Plano 5).
- Foto só com licença livre (CC BY, CC BY-SA, CC0, domínio público), nunca NC nem ND; crédito e licença no `pontos.json`.
- Atribuição: © OpenStreetMap contributors (ODbL), Overture Maps Foundation, Copernicus DEM (© DLR/Airbus, ESA), Wikimedia Commons (autor e licença por foto).
- Rede: Overpass, Overture, Nominatim (1 req/s, User-Agent sem e-mail) e Commons, sempre com cache em `cache/`; testes não usam rede.
- Docs e commits em português do Brasil.

## Review Focus

1. **Projeção desalinhada** (vias do OSM deslocadas metros do loteamento): `Projecao` tem de devolver (0, 0) na origem do `georref.json` e ida e volta exata. Teste na Task 1.
2. **Download parcial ou vazio do Overpass/Overture** gera camada vazia em silêncio: `montar_base` falha com mensagem se vias ou prédios vierem zerados. Teste na Task 1.
3. **Prédio flutuando ou enterrado na encosta**: base na menor cota sob a pegada menos 0,3 m. Teste na Task 3.
4. **Ponto casado com homônimo longe** (outra "Praia do Pecém"): o casamento no OSM aceita só resultado a até 2 km da referência. Teste na Task 5.
5. **Foto com licença não livre** (NC/ND) entrando no site. Teste na Task 5.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `scripts/entorno/entorno.toml` | raios, resolução do mapa, cores |
| `scripts/entorno/osm.py` | `Projecao`, `overpass`, `linha_osm`, `poligono_osm`, `aneis`, `tipo_area` |
| `scripts/entorno/extrair.py` | `EntornoCfg`, `baixar_overture`, `montar_base`, CLI → `cache/entorno/base.json` |
| `scripts/loteamento/terreno.py` | + `Relevo`, `DESTINO_LONGE`, `aneis_do_plato` |
| `scripts/entorno/mapa.py` | `rasterizar` (camadas → imagem) |
| `scripts/entorno/preparar.py` | camadas do mapa, `faixas_principais`, `extrudar`, `altura_predio`, CLI → `mapa.jpg`, `mapa.json`, `cache/cena/entorno-detalhe.json` |
| `scripts/entorno/vegetacao.py` | `pontos_zona`, `canteiros`, `instancias`, CLI → `cache/entorno/vegetacao.json` |
| `scripts/blender/gerar_vegetacao.py` | espécies no Blender → `vegetacao.glb` |
| `scripts/pontos/pontos.py` | `escolher_osm`, `grafo_carro`, `minutos`, `licenca_livre`, `faixa`, `galeria`, CLI → `dados/pontos.json`, `cache/pontos/fotos-candidatas.html` |
| `scripts/blender/gerar_loteamento.py` | UV e material com textura; `suave` por objeto; `export_texcoords` |
| `scripts/loteamento/blender.py` | `com_mapa`, `juntar_cenas`, roda entorno + vegetação + loteamento; `conferir_entorno` com os objetos novos |
| `tests/test_osm.py`, `test_extrair.py`, `test_mapa.py`, `test_preparar.py`, `test_vegetacao.py`, `test_pontos.py` | um por módulo; `test_terreno.py`, `test_blender.py` ganham casos |

---

### Task 1: OSM e Overture em coordenadas locais

**Files:**
- Create: `scripts/entorno/entorno.toml`, `scripts/entorno/osm.py`, `scripts/entorno/extrair.py`, `tests/test_osm.py`, `tests/test_extrair.py`
- Modify: `pyproject.toml` (shapely, overturemaps)

**Interfaces:**
- Consumes: `dados/georref.json`; `scripts.entorno.dem.centro_dos_lotes() -> (x, y)`.
- Produces: `osm.Projecao(e0, n0)` com `xy(lon, lat) -> (x, y)` e `lonlat(x, y) -> (lon, lat)`; `osm.overpass(consulta, cache, refazer=False) -> dict`; `osm.poligono_osm(proj, elemento) -> Polygon | MultiPolygon | None`; `osm.aneis(geom) -> list[list[list[list[float]]]]` (cada polígono `[externo, *furos]`); `osm.tipo_area(tags) -> str | None`; `extrair.EntornoCfg` (`carregar()`); `extrair.BASE` = `cache/entorno/base.json` com `{"centro": [x, y], "raio_vias", "raio_predios", "vias": [{osm, classe, nome, largura, pontos}], "areas": [{osm, tipo, tags, poligonos}], "predios": [{id, fonte, altura, niveis, area_m2, poligonos}], "fontes": {...}}`; `extrair.MALHA` = `cache/entorno/malha-regional.json` (Overpass bruto, para os minutos).

- [ ] **Step 1: Dependências e configuração**

Run: `uv add shapely overturemaps`
Expected: entram no `pyproject.toml`; `uv run python -c "import shapely, overturemaps"` sai sem erro.

`scripts/entorno/entorno.toml`:

```toml
# Entorno (Plano 4). Raios em metros, a partir do centro da caixa dos lotes.
raio_vias = 4000            # vias e áreas do OSM (mapa pintado no relevo)
raio_faixas = 1500          # vias principais em faixa 3D, perto do loteamento
raio_predios = 1500         # prédios extrudados (Overture)
raio_vegetacao = 2000       # instâncias de vegetação
raio_malha_regional = 25000 # malha viária para os minutos de carro (Pecém, Fortaleza)
mapa_px = 4096              # lado da imagem do chão (~2 m/px no recorte de 8 km)
```

- [ ] **Step 2: Escrever os testes**

`tests/test_osm.py`:

```python
import pytest
from shapely.geometry import Polygon

from scripts.entorno.osm import Projecao, aneis, poligono_osm, tipo_area

E0, N0 = 534600.0, 9595100.0


def test_projecao_volta_a_origem_e_ida_e_volta():
    p = Projecao(E0, N0)
    lon, lat = p.lonlat(0.0, 0.0)
    assert p.xy(lon, lat) == pytest.approx((0.0, 0.0), abs=1e-6)
    assert p.xy(*p.lonlat(1234.5, -987.0)) == pytest.approx((1234.5, -987.0), abs=1e-6)
    assert -38.70 < lon < -38.68 and -3.67 < lat < -3.65


def _geo(p, pts):
    return [{"lon": lon, "lat": lat} for lon, lat in (p.lonlat(x, y) for x, y in pts)]


def test_poligono_osm_way_fechado_e_relacao_com_furo():
    p = Projecao(E0, N0)
    quad = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    furo = [(40, 40), (60, 40), (60, 60), (40, 60), (40, 40)]
    w = poligono_osm(p, {"type": "way", "geometry": _geo(p, quad)})
    assert w.area == pytest.approx(10000, rel=1e-6)
    r = poligono_osm(p, {"type": "relation", "members": [
        {"type": "way", "role": "outer", "geometry": _geo(p, quad[:3])},
        {"type": "way", "role": "", "geometry": _geo(p, quad[2:])},
        {"type": "way", "role": "inner", "geometry": _geo(p, furo)}]})
    assert r.area == pytest.approx(10000 - 400, rel=1e-6)
    assert poligono_osm(p, {"type": "way", "geometry": _geo(p, quad[:3])}) is None  # aberto


def test_aneis_externo_e_furos():
    g = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], [[(4, 4), (6, 4), (6, 6), (4, 6)]])
    (p,) = aneis(g)
    assert len(p) == 2 and p[0][0] == [0.0, 0.0]


@pytest.mark.parametrize("tags,tipo", [
    ({"natural": "water"}, "agua"), ({"natural": "beach"}, "areia"), ({"natural": "sand"}, "areia"),
    ({"natural": "scrub"}, "verde"), ({"leisure": "park"}, "lazer"), ({"amenity": "parking"}, "estacionamento"),
    ({"landuse": "residential"}, "uso:residential"), ({"building": "yes"}, None)])
def test_tipo_area(tags, tipo):
    assert tipo_area(tags) == tipo
```

`tests/test_extrair.py`:

```python
import pytest

from scripts.entorno.extrair import EntornoCfg, montar_base
from scripts.entorno.osm import Projecao

P = Projecao(534600.0, 9595100.0)
CFG = EntornoCfg(raio_vias=500.0, raio_faixas=300.0, raio_predios=300.0, raio_vegetacao=400.0,
                 raio_malha_regional=5000.0, mapa_px=256)


def _geo(pts):
    return [{"lon": lon, "lat": lat} for lon, lat in (P.lonlat(x, y) for x, y in pts)]


def _quad(x, y, l):
    return [(x, y), (x + l, y), (x + l, y + l), (x, y + l), (x, y)]


VIAS = {"elements": [
    {"type": "way", "id": 1, "tags": {"highway": "primary", "name": "CE-090"}, "geometry": _geo([(-900, 0), (900, 0)])},
    {"type": "way", "id": 2, "tags": {"highway": "steps"}, "geometry": _geo([(0, 0), (0, 50)])}]}
AREAS = {"elements": [{"type": "way", "id": 3, "tags": {"natural": "scrub"}, "geometry": _geo(_quad(10, 10, 50))}]}
PREDIOS = {"release": "x", "feicoes": [
    {"id": "a", "geometria": {"type": "Polygon", "coordinates": [[list(P.lonlat(x, y)) for x, y in _quad(20, 20, 10)]]},
     "fonte": "OpenStreetMap", "altura": None, "niveis": 2, "classe": None, "nome": None},
    {"id": "longe", "geometria": {"type": "Polygon", "coordinates": [[list(P.lonlat(x, y)) for x, y in _quad(900, 900, 10)]]},
     "fonte": "x", "altura": None, "niveis": None, "classe": None, "nome": None}]}


def test_montar_base_recorta_vias_no_raio_e_filtra_classes():
    b = montar_base(P, (0.0, 0.0), CFG, VIAS, AREAS, PREDIOS)
    (v,) = b["vias"]
    assert v["classe"] == "primary" and v["nome"] == "CE-090"
    assert min(x for x, _ in v["pontos"]) == pytest.approx(-500, abs=0.5)  # cortada no raio
    assert b["areas"][0]["tipo"] == "verde" and b["areas"][0]["tags"] == {"natural": "scrub"}
    assert [p["id"] for p in b["predios"]] == ["a"] and b["predios"][0]["area_m2"] == pytest.approx(100, rel=1e-3)


def test_montar_base_recusa_download_vazio():
    with pytest.raises(SystemExit, match="Nenhuma via"):
        montar_base(P, (0.0, 0.0), CFG, {"elements": []}, AREAS, PREDIOS)
    with pytest.raises(SystemExit, match="Nenhum prédio"):
        montar_base(P, (0.0, 0.0), CFG, VIAS, AREAS, {"release": "x", "feicoes": []})
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_osm.py tests/test_extrair.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'scripts.entorno.osm'`.

- [ ] **Step 4: Implementar `osm.py`**

```python
"""OSM e projeção local: Overpass com cache; geometrias em metros, x = leste, y = norte, a partir
da origem de dados/georref.json (a mesma do loteamento)."""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union

CRS_LOCAL = "EPSG:31984"
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
AGENTE = "maquete-cumbuco/0.1 (maquete de vendas; scripts/entorno)"


class Projecao:
    """lon/lat ↔ coordenadas locais da cena (UTM 24S menos a origem)."""

    def __init__(self, e0: float, n0: float):
        self.e0, self.n0 = e0, n0
        self._ida = Transformer.from_crs("EPSG:4326", CRS_LOCAL, always_xy=True)
        self._volta = Transformer.from_crs(CRS_LOCAL, "EPSG:4326", always_xy=True)

    def xy(self, lon: float, lat: float) -> tuple[float, float]:
        e, n = self._ida.transform(lon, lat)
        return e - self.e0, n - self.n0

    def lonlat(self, x: float, y: float) -> tuple[float, float]:
        return self._volta.transform(x + self.e0, y + self.n0)


def overpass(consulta: str, cache: Path, refazer: bool = False) -> dict:
    """Consulta com cache em disco; tenta os espelhos em rodízio, com espera crescente."""
    if cache.exists() and not refazer:
        return json.loads(cache.read_text(encoding="utf-8"))
    corpo = urllib.parse.urlencode({"data": consulta}).encode()
    erros = []
    for tentativa in range(3):
        for url in OVERPASS:
            try:
                req = urllib.request.Request(url, corpo, {"User-Agent": AGENTE})
                with urllib.request.urlopen(req, timeout=200) as r:
                    texto = r.read().decode("utf-8")
                dados = json.loads(texto)
            except (OSError, ValueError) as e:
                erros.append(f"{url}: {e}")
                continue
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(texto, encoding="utf-8")
            return dados
        time.sleep(15 * (tentativa + 1))
    raise SystemExit("Overpass indisponível:\n  " + "\n  ".join(erros[-3:]))


def linha_osm(proj: Projecao, geometria: list[dict]) -> list[tuple[float, float]]:
    return [proj.xy(g["lon"], g["lat"]) for g in geometria]


def poligono_osm(proj: Projecao, elemento: dict):
    """Way fechado ou relação multipolygon → polígono em metros; None se não fecha."""
    if elemento["type"] == "way":
        pts = linha_osm(proj, elemento.get("geometry") or [])
        if len(pts) < 4 or pts[0] != pts[-1]:
            return None
        g = Polygon(pts)
        return g if g.is_valid else g.buffer(0)

    def juntar(papel: str):
        linhas = [LineString(linha_osm(proj, m["geometry"])) for m in elemento.get("members", [])
                  if m.get("type") == "way" and (m.get("role") or "outer") == papel and len(m.get("geometry") or []) >= 2]
        return unary_union(list(polygonize(unary_union(linhas)))) if linhas else Polygon()

    g = juntar("outer").difference(juntar("inner"))
    return None if g.is_empty else g


def aneis(geom) -> list[list[list[list[float]]]]:
    partes = getattr(geom, "geoms", [geom])
    return [[[[round(x, 2), round(y, 2)] for x, y in p.exterior.coords]]
            + [[[round(x, 2), round(y, 2)] for x, y in i.coords] for i in p.interiors]
            for p in partes if p.geom_type == "Polygon" and not p.is_empty]


def tipo_area(tags: dict) -> str | None:
    if tags.get("natural") == "water" or "water" in tags or tags.get("waterway") == "riverbank":
        return "agua"
    if tags.get("natural") in {"beach", "sand", "dune"}:
        return "areia"
    if tags.get("leisure") in {"park", "garden", "pitch", "playground", "sports_centre", "stadium"}:
        return "lazer"
    if tags.get("natural") in {"wood", "scrub", "grassland", "wetland", "heath"} or tags.get("landuse") in {
            "forest", "grass", "meadow", "recreation_ground", "village_green", "farmland", "orchard"}:
        return "verde"
    if tags.get("amenity") == "parking":
        return "estacionamento"
    if "landuse" in tags:
        return "uso:" + tags["landuse"]
    return None
```

- [ ] **Step 5: Implementar `extrair.py`**

```python
"""Etapa 1 do entorno: OSM (Overpass) e prédios do Overture em coordenadas locais.

Uso: uv run python -m scripts.entorno.extrair [--refazer]

Cache em cache/entorno/. Atribuição exigida no app: © OpenStreetMap contributors (ODbL),
Overture Maps Foundation (e as fontes de cada prédio: OSM, Google Open Buildings, Microsoft).
"""

import argparse
import json
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

from shapely import wkb
from shapely.geometry import LineString, Point, Polygon, mapping, shape
from shapely.ops import unary_union

from scripts.comum.ambiente import RAIZ
from scripts.entorno.dem import centro_dos_lotes

from .osm import Projecao, aneis, linha_osm, overpass, poligono_osm, tipo_area

CFG_TOML = RAIZ / "scripts" / "entorno" / "entorno.toml"
CACHE = RAIZ / "cache" / "entorno"
BASE = CACHE / "base.json"
MALHA = CACHE / "malha-regional.json"

# Vias que entram na maquete; trilhas soltas, escadas e acessos internos poluem sem servir.
VIAS = {
    "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary",
    "secondary_link", "tertiary", "tertiary_link", "unclassified", "residential", "living_street",
    "service", "pedestrian", "track", "footway", "cycleway", "path",
}


@dataclass(frozen=True)
class EntornoCfg:
    raio_vias: float
    raio_faixas: float
    raio_predios: float
    raio_vegetacao: float
    raio_malha_regional: float
    mapa_px: int

    @classmethod
    def carregar(cls) -> "EntornoCfg":
        return cls(**tomllib.loads(CFG_TOML.read_text(encoding="utf-8")))


def baixar_overture(bbox: tuple[float, float, float, float], cache, refazer: bool = False) -> dict:
    if cache.exists() and not refazer:
        return json.loads(cache.read_text(encoding="utf-8"))
    from overturemaps import core

    release = core.get_latest_release()
    feicoes = []
    for lote in core.record_batch_reader("building", bbox=bbox, release=release):
        for linha in lote.to_pylist():
            fontes = linha.get("sources") or []
            nomes = linha.get("names") or {}
            feicoes.append({"id": linha["id"], "geometria": mapping(wkb.loads(linha["geometry"])),
                            "fonte": fontes[0]["dataset"] if fontes else None, "altura": linha.get("height"),
                            "niveis": linha.get("num_floors"), "classe": linha.get("class"),
                            "nome": nomes.get("primary")})
    dados = {"release": release, "feicoes": feicoes}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dados), encoding="utf-8")
    return dados


def montar_base(proj: Projecao, centro: tuple[float, float], cfg: EntornoCfg,
                osm_vias: dict, osm_areas: dict, overture: dict) -> dict:
    """Recorta e converte; falha alto se um download veio vazio (Overpass às vezes devolve 0)."""
    cvias = Point(centro).buffer(cfg.raio_vias, 128)
    cpredios = Point(centro).buffer(cfg.raio_predios, 128)
    vias = []
    for e in osm_vias["elements"]:
        tags = e.get("tags", {})
        if tags.get("highway") not in VIAS or not e.get("geometry"):
            continue
        cortada = LineString(linha_osm(proj, e["geometry"])).intersection(cvias)
        for t in getattr(cortada, "geoms", [cortada]):
            if t.is_empty or t.geom_type != "LineString":
                continue
            vias.append({"osm": e["id"], "classe": tags["highway"], "nome": tags.get("name"),
                         "largura": tags.get("width"),
                         "pontos": [[round(x, 2), round(y, 2)] for x, y in t.coords]})
    areas = []
    for e in osm_areas["elements"]:
        tipo = tipo_area(e.get("tags", {}))
        g = poligono_osm(proj, e) if tipo else None
        if g is None:
            continue
        g = g.intersection(cvias)
        if g.is_empty or g.area < 1:
            continue
        tags = e.get("tags", {})
        areas.append({"osm": f"{e['type']}/{e['id']}", "tipo": tipo, "nome": tags.get("name"),
                      "tags": {k: tags[k] for k in ("natural", "wetland", "landuse", "leisure") if k in tags},
                      "poligonos": aneis(g)})
    predios = []
    for f in overture["feicoes"]:
        g = shape(f["geometria"])
        if g.geom_type not in {"Polygon", "MultiPolygon"}:
            continue
        partes = getattr(g, "geoms", [g])
        local = unary_union([Polygon([proj.xy(*c[:2]) for c in p.exterior.coords],
                                     [[proj.xy(*c[:2]) for c in i.coords] for i in p.interiors]) for p in partes])
        if not cpredios.contains(local.centroid):
            continue
        predios.append({"id": f["id"], "fonte": f["fonte"], "altura": f["altura"], "niveis": f["niveis"],
                        "area_m2": round(local.area, 1), "poligonos": aneis(local)})
    if not vias:
        raise SystemExit("Nenhuma via no raio: o download do Overpass veio vazio? Rode com --refazer.")
    if not predios:
        raise SystemExit("Nenhum prédio no raio: o download do Overture veio vazio? Rode com --refazer.")
    return {"centro": [round(centro[0], 2), round(centro[1], 2)], "raio_vias": cfg.raio_vias,
            "raio_predios": cfg.raio_predios, "vias": vias, "areas": areas, "predios": predios,
            "fontes": {"overture_release": overture.get("release")}}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--refazer", action="store_true", help="ignora o cache e baixa de novo")
    refazer = ap.parse_args().refazer
    cfg = EntornoCfg.carregar()
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    proj = Projecao(georref["origem"]["E"], georref["origem"]["N"])
    centro = centro_dos_lotes()
    lon0, lat0 = proj.lonlat(*centro)
    cerca = f"(around:{cfg.raio_vias:.0f},{lat0},{lon0})"
    osm_vias = overpass(f"[out:json][timeout:180];way[highway]{cerca};out geom;", CACHE / "osm-vias.json", refazer)
    osm_areas = overpass(
        "[out:json][timeout:180];("
        f"wr[landuse]{cerca};wr[leisure]{cerca};wr[natural]{cerca};wr[water]{cerca};wr[amenity=parking]{cerca};"
        ");out geom;", CACHE / "osm-areas.json", refazer)
    overpass("[out:json][timeout:180];way[highway~\"^(motorway|trunk|primary|secondary|tertiary|unclassified)(_link)?$\"]"
             f"(around:{cfg.raio_malha_regional:.0f},{lat0},{lon0});out geom;", MALHA, refazer)
    (lo0, la0), (lo1, la1) = (proj.lonlat(centro[0] - cfg.raio_predios, centro[1] - cfg.raio_predios),
                              proj.lonlat(centro[0] + cfg.raio_predios, centro[1] + cfg.raio_predios))
    overture = baixar_overture((lo0, la0, lo1, la1), CACHE / "overture-predios.json", refazer)
    base = montar_base(proj, centro, cfg, osm_vias, osm_areas, overture)
    base["fontes"]["osm_timestamp"] = osm_vias.get("osm3s", {}).get("timestamp_osm_base")
    base["gerado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    BASE.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
    print(f"vias {len(base['vias'])} {dict(Counter(v['classe'] for v in base['vias']).most_common(6))}")
    print(f"áreas {len(base['areas'])} {dict(Counter(a['tipo'] for a in base['areas']).most_common(6))}")
    print(f"prédios {len(base['predios'])} (Overture {base['fontes']['overture_release']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Rodar e ver passar**

Run: `uv run pytest tests/test_osm.py tests/test_extrair.py -q`
Expected: tudo passa.

- [ ] **Step 7: Rodar no dado real**

Run: `uv run python -m scripts.entorno.extrair`
Expected: baixa e imprime vias (centenas a milhares de trechos; `residential` e `track` dominando), áreas e prédios (alguns milhares no raio de 1,5 km). Anotar as contagens no ledger.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock scripts/entorno/entorno.toml scripts/entorno/osm.py scripts/entorno/extrair.py tests/test_osm.py tests/test_extrair.py
git commit -m "feat(entorno): OSM e Overture em coordenadas locais"
```

---

### Task 2: Relevo da cena e mapa pintado no chão

**Files:**
- Create: `scripts/entorno/mapa.py`, `tests/test_mapa.py`
- Modify: `scripts/loteamento/terreno.py` (`Relevo`, `DESTINO_LONGE`, `aneis_do_plato`), `tests/test_terreno.py`

**Interfaces:**
- Consumes: Task 1 (`base.json`); `terreno.compor_perto` e as grades do 3c.
- Produces: `terreno.Relevo(perto, longe)` com `cota(x, y) -> float` e `Relevo.carregar()`; `terreno.DESTINO_LONGE` (`cache/cena/longe.json`); `terreno.aneis_do_plato(msp, cfg_terreno, lotes, e0, n0) -> list[list[Ponto]]`; `mapa.CORES: dict[str, tuple[int, int, int]]`; `mapa.rasterizar(camadas: list[tuple[str, geom]], ext, px) -> PIL.Image` (camadas de baixo para cima; `ext = (x0, y0, x1, y1)`; linha 0 da imagem = y1).

- [ ] **Step 1: Testes**

Em `tests/test_terreno.py`:

```python
from scripts.loteamento.terreno import Relevo


def test_relevo_usa_o_perto_dentro_e_o_longe_fora():
    perto = Grade(0.0, 0.0, 10.0, 11, 11, [[50.0] * 11 for _ in range(11)])
    longe = _grade(lambda x, y: 7.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    r = Relevo(perto, longe)
    assert r.cota(55.0, 55.0) == 50.0 and r.cota(100.0, 100.0) == 50.0  # borda é do perto
    assert r.cota(130.0, 55.0) == 7.0
```

`tests/test_mapa.py`:

```python
from shapely.geometry import LineString, Polygon

from scripts.entorno.mapa import CORES, rasterizar

EXT = (0.0, 0.0, 100.0, 100.0)


def test_area_com_furo_e_via_por_cima():
    verde = Polygon([(10, 10), (90, 10), (90, 90), (10, 90)], [[(40, 40), (60, 40), (60, 60), (40, 60)]])
    via = LineString([(0, 80), (100, 80)]).buffer(3)
    img = rasterizar([("verde", verde), ("via_local", via)], EXT, 100)
    px = lambda x, y: img.getpixel((int(x), int(100 - y)))  # noqa: E731 — linha 0 é o norte
    assert px(20, 20) == CORES["verde"]
    assert px(50, 50) == CORES["solo"]  # furo
    assert px(5, 5) == CORES["solo"]
    assert px(50, 80) == CORES["via_local"]  # via por cima do verde
    assert img.size == (100, 100)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_terreno.py tests/test_mapa.py -q`
Expected: FAIL com `ImportError: cannot import name 'Relevo'` e `ModuleNotFoundError: scripts.entorno.mapa`.

- [ ] **Step 3: `terreno.py`**

Acrescentar (antes de `main`):

```python
DESTINO_LONGE = RAIZ / "cache" / "cena" / "longe.json"


class Relevo:
    """Cota do chão da cena: a grade perto onde ela existe (borda incluída), o Copernicus ajustado fora.
    A borda do perto coincide com o longe (costura do 3c), então a troca não tem degrau."""

    def __init__(self, perto: Grade, longe: Grade):
        self.perto, self.longe = perto, longe
        self._x1 = perto.x0 + perto.passo * (perto.nx - 1)
        self._y1 = perto.y0 + perto.passo * (perto.ny - 1)

    def cota(self, x: float, y: float) -> float:
        p = self.perto
        if p.x0 <= x <= self._x1 and p.y0 <= y <= self._y1:
            return p.cota(x, y)
        return self.longe.cota(x, y)

    @classmethod
    def carregar(cls) -> "Relevo":
        ler = lambda c: Grade.de_json(json.loads(c.read_text(encoding="utf-8")))  # noqa: E731
        return cls(ler(DESTINO_PERTO), ler(DESTINO_LONGE))


def aneis_do_plato(msp, cfg: TerrenoCfg, lotes: list[dict], e0: float, n0: float) -> list[list[Ponto]]:
    """Poligonal + todas as áreas da cena + lotes: o que fica plano (e fora do entorno)."""
    camadas = [l for ls in CenaCfg.carregar(CFG_TOML).camadas.values() for l in ls]
    return (aneis_da_layer(msp, cfg.poligonal, e0, n0) + aneis_da_layer(msp, camadas, e0, n0)
            + [[tuple(p) for p in l["poligono"]] for l in lotes])
```

Em `main`, trocar o bloco que monta `plato` por `plato = aneis_do_plato(msp, cfg, lotes, e0, n0)` (a `poligonal` continua lida para a extensão) e gravar o longe junto com o perto: `DESTINO_LONGE.write_text(json.dumps(longe.para_json()), encoding="utf-8")`.

- [ ] **Step 4: `mapa.py`**

```python
"""Mapa do chão: vias e áreas do OSM pintadas numa imagem aplicada por UV ao relevo."""

from PIL import Image, ImageDraw

# Cores de cena (ambiente, não marca), sRGB. O solo é a cor do terreno do Blender (0.86, 0.80, 0.68).
CORES = {
    "solo": (219, 204, 173),
    "verde": (171, 180, 138),
    "lazer": (178, 190, 142),
    "areia": (234, 223, 195),
    "agua": (122, 160, 168),
    "estacionamento": (200, 195, 184),
    "via_local": (160, 156, 150),
    "via_principal": (118, 116, 118),
}


def _partes(geom):
    return [p for p in getattr(geom, "geoms", [geom]) if p.geom_type == "Polygon" and not p.is_empty]


def rasterizar(camadas: list[tuple[str, object]], ext: tuple[float, float, float, float], px: int) -> Image.Image:
    """Camadas de baixo para cima; cada uma com a cor de CORES[nome]. `px` é o lado maior."""
    x0, y0, x1, y1 = ext
    escala = px / max(x1 - x0, y1 - y0)
    tam = (round((x1 - x0) * escala), round((y1 - y0) * escala))
    img = Image.new("RGB", tam, CORES["solo"])
    para_px = lambda coords: [((x - x0) * escala, (y1 - y) * escala) for x, y in coords]  # noqa: E731
    for nome, geom in camadas:
        mascara = Image.new("1", tam, 0)
        dr = ImageDraw.Draw(mascara)
        for p in _partes(geom):
            dr.polygon(para_px(p.exterior.coords), fill=1)
            for furo in p.interiors:
                dr.polygon(para_px(furo.coords), fill=0)
        img.paste(CORES[nome], (0, 0, *tam), mascara)
    return img
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest -q`
Expected: tudo passa.

- [ ] **Step 6: Regerar o terreno**

Run: `uv run python -m scripts.loteamento.terreno`
Expected: mesma linha de antes (platô 21,0 m, delta −1,29 m) e `cache/cena/longe.json` gravado.

- [ ] **Step 7: Commit**

```bash
git add scripts/loteamento/terreno.py scripts/entorno/mapa.py tests/test_terreno.py tests/test_mapa.py
git commit -m "feat(entorno): relevo da cena (perto + Copernicus) e mapa pintado no chão"
```

---

### Task 3: Preparação — mapa, faixas principais e prédios

**Files:**
- Create: `scripts/entorno/preparar.py`, `tests/test_preparar.py`

**Interfaces:**
- Consumes: Task 1 (`BASE`, `EntornoCfg`), Task 2 (`Relevo`, `aneis_do_plato`, `rasterizar`, `CORES`); `malha.triangular`, `malha.refinar`, `malha.drapear`.
- Produces: `preparar.VIAS_CLASSES: dict[str, tuple[str, float]]` (classe → grupo, largura); `preparar.altura_predio(p, area) -> float`; `preparar.extrudar(aneis, relevo, altura) -> (vertices, faces)`; `preparar.faixas_principais(vias, centro, raio, fora) -> geom`; `preparar.malha_de(geom, relevo, offset, max_aresta) -> (vertices, faces)`; arquivos `cache/entorno/mapa.jpg`, `cache/entorno/mapa.json` (`{"arquivo": "<caminho absoluto>", "ext": [x0, y0, x1, y1], "px": [w, h]}`) e `cache/cena/entorno-detalhe.json` (`{"objetos": [ViasPrincipais, Predios]}`; `Predios` com `"suave": false`).

- [ ] **Step 1: Testes**

`tests/test_preparar.py`:

```python
import pytest
from shapely.geometry import Point, Polygon

from scripts.entorno.preparar import altura_predio, extrudar, faixas_principais, malha_de


class Plano:
    def __init__(self, z):
        self.z = z

    def cota(self, x, y):
        return self.z


class Rampa:
    def cota(self, x, y):
        return x / 10


QUAD = [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]


def test_extrudar_caixa_no_plano():
    v, f = extrudar(QUAD, Plano(5.0), 4.0)
    assert sorted({round(z, 2) for _, _, z in v}) == [4.7, 9.0]
    assert len(f) == 2 + 4 * 2  # teto + 4 paredes


def test_extrudar_na_encosta_nao_flutua():
    v, _ = extrudar(QUAD, Rampa(), 4.0)
    assert min(z for _, _, z in v) == pytest.approx(0.0 - 0.3)  # base na menor cota sob a pegada
    assert max(z for _, _, z in v) == pytest.approx(0.5 + 4.0)  # teto na cota média + altura


def test_altura_predio_pela_fonte_ou_pela_area():
    assert altura_predio({"altura": 12.3, "niveis": None}, 50) == 12.3
    assert altura_predio({"altura": None, "niveis": 3}, 50) == 9.5
    assert altura_predio({"altura": None, "niveis": None}, 50) == 3.2
    assert altura_predio({"altura": None, "niveis": None}, 2000) == 8.0


def test_faixas_principais_so_no_raio_e_fora_do_plato():
    vias = [{"classe": "primary", "largura": None, "pontos": [[-500, 0], [500, 0]]},
            {"classe": "residential", "largura": None, "pontos": [[0, -500], [0, 500]]}]
    plato = Polygon([(-50, -50), (50, -50), (50, 50), (-50, 50)])
    g = faixas_principais(vias, (0.0, 0.0), 300.0, plato)
    assert g.bounds[0] == pytest.approx(-300, abs=1) and g.bounds[2] == pytest.approx(300, abs=1)
    assert not g.intersects(Point(0, 0)) and not g.intersects(Point(0, 200))  # residencial é pintada


def test_malha_de_assenta_com_offset():
    v, f = malha_de(Polygon([(0, 0), (20, 0), (20, 20), (0, 20)]), Plano(3.0), 0.3, 8.0)
    assert f and all(z == pytest.approx(3.3) for _, _, z in v)
    assert max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for t in f for a, b in
               [(v[t[0]], v[t[1]]), (v[t[1]], v[t[2]])]) <= 8.0 * 1.5  # refinada
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_preparar.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'scripts.entorno.preparar'`.

- [ ] **Step 3: Implementar**

`scripts/entorno/preparar.py`:

```python
"""Etapa 2 do entorno: mapa do chão (vias e áreas pintadas), vias principais perto do loteamento
em faixa 3D e prédios extrudados, tudo assentado no relevo da cena.

Uso: uv run python -m scripts.entorno.preparar
"""

import json
import sys

import ezdxf
import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from scripts.comum.ambiente import RAIZ
from scripts.loteamento.cena import CFG_TOML, DXF
from scripts.loteamento.malha import drapear, refinar, triangular
from scripts.loteamento.terreno import DESTINO_LONGE, Relevo, TerrenoCfg, aneis_do_plato

from .extrair import BASE, CACHE, EntornoCfg
from .mapa import rasterizar

MAPA_JPG = CACHE / "mapa.jpg"
MAPA_JSON = CACHE / "mapa.json"
DETALHE = RAIZ / "cache" / "cena" / "entorno-detalhe.json"
AREA_MINIMA_PREDIO_M2 = 8.0  # abaixo disso, ruído das pegadas por ML
OFFSET_FAIXA = 0.3  # m acima do relevo
MAX_ARESTA_FAIXA = 5.0  # m: segue o relevo de perto

# classe OSM -> (grupo, largura padrão em metros)
VIAS_CLASSES = {
    "motorway": ("via_principal", 14), "trunk": ("via_principal", 12), "primary": ("via_principal", 10),
    "secondary": ("via_principal", 9), "tertiary": ("via_principal", 8), "motorway_link": ("via_principal", 7),
    "trunk_link": ("via_principal", 7), "primary_link": ("via_principal", 7),
    "secondary_link": ("via_principal", 7), "tertiary_link": ("via_principal", 7),
    "unclassified": ("via_local", 6), "residential": ("via_local", 6), "living_street": ("via_local", 5),
    "service": ("via_local", 4), "track": ("via_local", 3), "pedestrian": ("via_local", 4),
    "footway": ("via_local", 2), "cycleway": ("via_local", 2), "path": ("via_local", 1.5),
}
ORDEM_AREAS = ["verde", "lazer", "areia", "estacionamento", "agua"]  # de baixo para cima


def _poligono(aneis):
    return Polygon(aneis[0], aneis[1:])


def _largura(via, padrao):
    try:
        return float(str(via["largura"]).replace(",", ".").split()[0])
    except (KeyError, TypeError, ValueError, IndexError):
        return padrao


def altura_predio(p: dict, area: float) -> float:
    if p.get("altura"):
        return round(float(p["altura"]), 2)
    if p.get("niveis"):
        return round(float(p["niveis"]) * 3.0 + 0.5, 2)
    if area < 60:
        return 3.2
    if area < 250:
        return 4.0
    if area < 1000:
        return 6.0
    return 8.0  # galpões, atacado, shopping


def extrudar(aneis: list, relevo, altura: float) -> tuple[list[list[float]], list[list[int]]]:
    """Caixa de teto plano: base na menor cota sob a pegada − 0,3 m (não flutua na encosta),
    teto na cota média + altura."""
    externo = [tuple(p) for p in aneis[0][:-1]] if aneis[0][0] == aneis[0][-1] else [tuple(p) for p in aneis[0]]
    furos = [[tuple(p) for p in (f[:-1] if f[0] == f[-1] else f)] for f in aneis[1:]]
    cotas = [relevo.cota(x, y) for x, y in externo]
    base, topo = min(cotas) - 0.3, sum(cotas) / len(cotas) + altura
    vt, tt = triangular(externo, furos)
    vertices = [[round(x, 2), round(y, 2), round(topo, 2)] for x, y in vt]
    faces = [list(t) for t in tt]
    for anel in [externo, *furos]:
        for a, b in zip(anel, anel[1:] + anel[:1]):
            i = len(vertices)
            vertices += [[round(a[0], 2), round(a[1], 2), round(base, 2)], [round(b[0], 2), round(b[1], 2), round(base, 2)],
                         [round(b[0], 2), round(b[1], 2), round(topo, 2)], [round(a[0], 2), round(a[1], 2), round(topo, 2)]]
            faces += [[i, i + 1, i + 2], [i, i + 2, i + 3]]
    return vertices, faces


def faixas(vias: list[dict], grupo: str) -> object:
    return unary_union([LineString(v["pontos"]).buffer(_largura(v, VIAS_CLASSES[v["classe"]][1]) / 2, quad_segs=3)
                        for v in vias if VIAS_CLASSES.get(v["classe"], ("", 0))[0] == grupo])


def faixas_principais(vias: list[dict], centro: tuple[float, float], raio: float, fora) -> object:
    """Vias principais em faixa 3D: só no raio perto do loteamento e fora do platô."""
    return faixas(vias, "via_principal").intersection(Point(centro).buffer(raio, 128)).difference(fora).simplify(0.2)


def malha_de(geom, relevo, offset: float, max_aresta: float) -> tuple[list[list[float]], list[list[int]]]:
    vertices, faces = [], []
    for p in getattr(geom, "geoms", [geom]):
        if p.geom_type != "Polygon" or p.is_empty:
            continue
        v, t = triangular(list(p.exterior.coords)[:-1], [list(i.coords)[:-1] for i in p.interiors])
        v, t = refinar(v, t, max_aresta)
        base = len(vertices)
        vertices += drapear(v, relevo, offset)
        faces += [[base + a, base + b, base + c] for a, b, c in t]
    return vertices, faces


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = EntornoCfg.carregar()
    base = json.loads(BASE.read_text(encoding="utf-8"))
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    plato = unary_union([Polygon(a).buffer(0) for a in aneis_do_plato(
        ezdxf.readfile(DXF).modelspace(), TerrenoCfg.carregar(CFG_TOML), lotes,
        georref["origem"]["E"], georref["origem"]["N"]) if len(a) >= 3])
    relevo = Relevo.carregar()
    centro = tuple(base["centro"])
    longe = json.loads(DESTINO_LONGE.read_text(encoding="utf-8"))
    ext = (longe["x0"], longe["y0"], longe["x0"] + longe["passo"] * (longe["nx"] - 1),
           longe["y0"] + longe["passo"] * (longe["ny"] - 1))

    camadas = []
    for tipo in ORDEM_AREAS:
        g = unary_union([_poligono(p).buffer(0) for a in base["areas"] if a["tipo"] == tipo for p in a["poligonos"]])
        if not g.is_empty:
            camadas.append((tipo, g))
    camadas += [("via_local", faixas(base["vias"], "via_local")), ("via_principal", faixas(base["vias"], "via_principal")),
                ("solo", plato)]  # o platô fica liso: o loteamento é desenhado por cima
    img = rasterizar(camadas, ext, cfg.mapa_px)
    img.save(MAPA_JPG, quality=85)
    MAPA_JSON.write_text(json.dumps({"arquivo": str(MAPA_JPG), "ext": list(ext), "px": list(img.size)}), encoding="utf-8")

    fora = plato.buffer(10)
    vf, ff = malha_de(faixas_principais(base["vias"], centro, cfg.raio_faixas, fora), relevo, OFFSET_FAIXA, MAX_ARESTA_FAIXA)
    vp, fp, n = [], [], 0
    for p in base["predios"]:
        g = unary_union([_poligono(q) for q in p["poligonos"]]).buffer(0).simplify(0.2)
        if g.area < AREA_MINIMA_PREDIO_M2 or g.intersects(fora):
            continue
        for parte in getattr(g, "geoms", [g]):
            aneis = [list(parte.exterior.coords)] + [list(i.coords) for i in parte.interiors]
            v, f = extrudar(aneis, relevo, altura_predio(p, parte.area))
            fp += [[a + len(vp), b + len(vp), c + len(vp)] for a, b, c in f]
            vp += v
        n += 1
    DETALHE.write_text(json.dumps({"objetos": [
        {"nome": "ViasPrincipais", "material": "via_principal_osm", "vertices": vf, "faces": ff},
        {"nome": "Predios", "material": "predio", "vertices": vp, "faces": fp, "suave": False},
    ]}), encoding="utf-8")
    print(f"mapa {img.size[0]}×{img.size[1]} px ({(ext[2] - ext[0]) / img.size[0]:.1f} m/px) · "
          f"faixas {len(ff)} tri · prédios {n} ({len(fp)} tri) · cota média do relevo nos prédios "
          f"{np.mean([z for _, _, z in vp]) if vp else 0:.1f} m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest -q`
Expected: tudo passa.

- [ ] **Step 5: Rodar no dado real**

Run: `uv run python -m scripts.entorno.preparar`
Expected: mapa ~4096×4096 px (~2 m/px); faixas com alguns milhares de triângulos; prédios na casa dos milhares. Abrir `cache/entorno/mapa.jpg` (leitura de imagem): vias do Icaraí/Tabuba e do Cumbuco visíveis, platô liso, costa coerente com o mar do 3c.

- [ ] **Step 6: Commit**

```bash
git add scripts/entorno/preparar.py tests/test_preparar.py
git commit -m "feat(entorno): mapa do chão, vias principais em faixa 3D e prédios no relevo"
```

---

### Task 4: Vegetação

**Files:**
- Create: `scripts/entorno/vegetacao.py`, `tests/test_vegetacao.py`, `scripts/blender/gerar_vegetacao.py`

**Interfaces:**
- Consumes: Task 1 (`BASE`, `EntornoCfg`), Task 2 (`Relevo`, `aneis_do_plato`), Task 3 (`faixas`); `cena.aneis_da_layer` e `CenaCfg.camadas["Verdes"]`; nível do mar = z do primeiro vértice do objeto `Mar` em `cache/cena/entorno.json`.
- Produces: `vegetacao.ESPECIES = ("coqueiro", "cajueiro", "arbusto")`; `vegetacao.pontos_zona(zona, m2, mistura, sorte) -> list[tuple[x, y, especie]]`; `vegetacao.canteiros(aneis, largura_max=8.0, passo=12.0) -> list[tuple[x, y]]`; `vegetacao.instancias(pontos, relevo, nivel_mar, sorte, offset=0.0) -> dict[especie, list[list[int]]]`; `cache/entorno/vegetacao.json` (`{"versao": 1, "campos": ["x_dm", "y_dm", "z_cm", "escala_pct", "rotacao_graus"], "especies": {esp: {"n", "instancias": [planos]}}}`); `vegetacao.glb` com `VEG_coqueiro`, `VEG_cajueiro`, `VEG_arbusto` (base em z = 0, metros).

- [ ] **Step 1: Testes**

`tests/test_vegetacao.py`:

```python
import random

import pytest
from shapely.geometry import Point, Polygon

from scripts.entorno.vegetacao import canteiros, instancias, pontos_zona


class Plano:
    def cota(self, x, y):
        return 10.0 if x >= 0 else -2.0  # a oeste, mar


def test_pontos_zona_densidade_e_dentro():
    zona = Polygon([(0, 0), (200, 0), (200, 200), (0, 200)])
    pts = pontos_zona(zona, 100.0, {"cajueiro": 0.5, "arbusto": 0.5}, random.Random(1))
    assert 300 < len(pts) < 500  # ~40 000 m² / 100 m²
    assert all(zona.contains(Point(x, y)) for x, y, _ in pts)
    assert {e for _, _, e in pts} == {"cajueiro", "arbusto"}


def test_canteiros_so_em_faixa_estreita():
    faixa = [(0.0, 0.0), (120.0, 0.0), (120.0, 4.0), (0.0, 4.0)]
    praca = [(0.0, 50.0), (50.0, 50.0), (50.0, 100.0), (0.0, 100.0)]
    pts = canteiros([faixa, praca])
    assert pts and all(0 <= x <= 120 and 1.0 <= y <= 3.0 for x, y in pts)  # no eixo do canteiro
    assert 8 <= len(pts) <= 12  # um coqueiro a cada ~12 m
    assert min(abs(a[0] - b[0]) for a in pts for b in pts if a != b) >= 6.0


def test_instancias_com_cota_e_sem_mar():
    pts = [(5.0, 5.0, "coqueiro"), (-5.0, 5.0, "coqueiro")]
    inst = instancias(pts, Plano(), -1.29, random.Random(1))
    (x_dm, y_dm, z_cm, esc, rot), = [inst["coqueiro"][i:i + 5] for i in range(0, len(inst["coqueiro"]), 5)]
    assert (x_dm, y_dm, z_cm) == (50, 50, 1000) and 80 <= esc <= 120 and 0 <= rot < 360
    assert inst["arbusto"] == [] and inst["cajueiro"] == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_vegetacao.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'scripts.entorno.vegetacao'`.

- [ ] **Step 3: `vegetacao.py`**

```python
"""Vegetação: posições das três espécies para o front instanciar (vegetacao.glb), já com a cota
do relevo. Zonas do OSM no raio da vegetação e coqueiros nos canteiros estreitos da Fase 1.

Uso: uv run python -m scripts.entorno.vegetacao
"""

import json
import math
import random
import sys

import ezdxf
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

from scripts.comum.ambiente import RAIZ
from scripts.loteamento.cena import CFG_TOML, DXF, CenaCfg, aneis_da_layer
from scripts.loteamento.terreno import DESTINO_ENTORNO, Relevo, TerrenoCfg, aneis_do_plato

from .extrair import BASE, CACHE, EntornoCfg
from .preparar import faixas

DESTINO = CACHE / "vegetacao.json"
ESPECIES = ("coqueiro", "cajueiro", "arbusto")
ESCALA = {"coqueiro": (0.8, 1.2), "cajueiro": (0.75, 1.25), "arbusto": (0.7, 1.3)}
# Zona OSM -> (m² por árvore, mistura). Em sobreposição vale a primeira. Densidades para ler
# como mata a 1 km de câmera, não para contar árvores.
ZONAS = [
    ("mata", lambda t: t.get("landuse") == "forest" or t.get("natural") == "wood", 120,
     {"cajueiro": 0.7, "coqueiro": 0.3}),
    ("restinga", lambda t: t.get("natural") in ("scrub", "heath", "grassland"), 80,
     {"arbusto": 0.8, "cajueiro": 0.2}),
    ("varzea", lambda t: t.get("natural") == "wetland", 70, {"coqueiro": 0.5, "arbusto": 0.5}),
    ("parque", lambda t: t.get("leisure") in ("park", "garden")
     or t.get("landuse") in ("recreation_ground", "village_green"), 250, {"cajueiro": 0.6, "coqueiro": 0.4}),
    ("quintais", lambda t: t.get("landuse") == "residential", 500, {"coqueiro": 0.5, "cajueiro": 0.5}),
    ("campo", lambda t: t.get("landuse") in ("grass", "meadow", "farmland", "orchard"), 900, {"cajueiro": 1.0}),
]


def pontos_zona(zona, m2: float, mistura: dict[str, float], sorte: random.Random) -> list[tuple[float, float, str]]:
    """Grade com sorteio dentro de cada célula: uma árvore a cada `m2`."""
    if zona.is_empty:
        return []
    dentro = prep(zona)
    passo = math.sqrt(m2)
    x0, y0, x1, y1 = zona.bounds
    nomes, pesos = zip(*mistura.items())
    pts = []
    for i in range(int((x1 - x0) / passo) + 1):
        for j in range(int((y1 - y0) / passo) + 1):
            x, y = x0 + (i + sorte.random()) * passo, y0 + (j + sorte.random()) * passo
            if dentro.contains(Point(x, y)):
                pts.append((x, y, sorte.choices(nomes, pesos)[0]))
    return pts


def canteiros(aneis: list[list[tuple[float, float]]], largura_max: float = 8.0, passo: float = 12.0) -> list[tuple[float, float]]:
    """Coqueiros no eixo dos canteiros: anel estreito (2·área/perímetro < largura_max) e comprido.
    Pontos na borda a cada `passo`, levados meia largura para dentro; vizinhos a < passo/2 viram um."""
    pts: list[tuple[float, float]] = []
    for anel in aneis:
        p = Polygon(anel).buffer(0)
        if p.is_empty or p.length == 0:
            continue
        largura = 2 * p.area / p.length
        if largura >= largura_max or p.length < 4 * passo:
            continue
        borda = p.exterior
        for k in range(int(borda.length / passo)):
            a, b = borda.interpolate(k * passo), borda.interpolate(k * passo + 0.5)
            dx, dy = b.x - a.x, b.y - a.y
            n = math.hypot(dx, dy) or 1.0
            for s in (1, -1):
                c = (a.x - s * dy / n * largura / 2, a.y + s * dx / n * largura / 2)
                if p.contains(Point(c)) and all(math.dist(c, q) >= passo / 2 for q in pts):
                    pts.append(c)
    return pts


def instancias(pontos: list[tuple[float, float, str]], relevo, nivel_mar: float, sorte: random.Random,
               offset: float = 0.0) -> dict[str, list[int]]:
    """Planos [x_dm, y_dm, z_cm, escala_pct, rotacao_graus] por espécie, embaralhados (as N
    primeiras são uma amostra uniforme: o app escolhe N pelo aparelho). Ponto no mar sai."""
    saida = {e: [] for e in ESPECIES}
    for x, y, esp in pontos:
        z = relevo.cota(x, y)
        if z <= nivel_mar + 0.5:
            continue
        lo, hi = ESCALA[esp]
        saida[esp].append([round(x * 10), round(y * 10), round((z + offset) * 100),
                           round(sorte.uniform(lo, hi) * 100), sorte.randrange(360)])
    for lista in saida.values():
        sorte.shuffle(lista)
    return {e: [c for inst in v for c in inst] for e, v in saida.items()}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = EntornoCfg.carregar()
    base = json.loads(BASE.read_text(encoding="utf-8"))
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    msp = ezdxf.readfile(DXF).modelspace()
    plato = unary_union([Polygon(a).buffer(0) for a in aneis_do_plato(msp, TerrenoCfg.carregar(CFG_TOML), lotes, e0, n0)
                         if len(a) >= 3])
    relevo = Relevo.carregar()
    nivel = json.loads(DESTINO_ENTORNO.read_text(encoding="utf-8"))["objetos"][1]["vertices"][0][2]
    poligono = lambda a: Polygon(a[0], a[1:]).buffer(0)  # noqa: E731
    livre = Point(base["centro"]).buffer(cfg.raio_vegetacao, 128).difference(unary_union([
        plato.buffer(5), faixas(base["vias"], "via_principal").buffer(2), faixas(base["vias"], "via_local").buffer(1),
        *[poligono(p).buffer(1.5) for pr in base["predios"] for p in pr["poligonos"]],
        *[poligono(p) for a in base["areas"] if a["tipo"] in ("agua", "estacionamento", "areia") for p in a["poligonos"]],
    ]))
    sorte = random.Random(4)
    pts, ja, por_zona = [], Polygon(), {}
    for nome, regra, m2, mistura in ZONAS:
        g = unary_union([poligono(p) for a in base["areas"] if regra(a["tags"]) for p in a["poligonos"]])
        zona = g.difference(ja).intersection(livre)
        ja = ja.union(g)
        novos = pontos_zona(zona, m2, mistura, sorte)
        por_zona[nome] = len(novos)
        pts += novos
    verdes = aneis_da_layer(msp, CenaCfg.carregar(CFG_TOML).camadas["Verdes"], e0, n0)
    inst = instancias(pts, relevo, nivel, sorte)
    cant = instancias([(x, y, "coqueiro") for x, y in canteiros(verdes)], relevo, nivel, sorte, offset=0.08)
    inst["coqueiro"] = cant["coqueiro"] + inst["coqueiro"]  # os da Fase 1 primeiro: sempre aparecem
    DESTINO.write_text(json.dumps({
        "versao": 1,
        "referencial": "x = leste, y = norte em dm; z = cota em cm (sem exagero); no glTF, (x, z, -y)",
        "modelos": "vegetacao.glb (malhas VEG_<especie>, base em z = 0, em metros)",
        "campos": ["x_dm", "y_dm", "z_cm", "escala_pct", "rotacao_graus"],
        "canteiros_fase1": len(cant["coqueiro"]) // 5,
        "especies": {e: {"n": len(v) // 5, "instancias": v} for e, v in inst.items()},
    }, separators=(",", ":")), encoding="utf-8")
    print(f"vegetação por zona {por_zona} · canteiros da Fase 1 {len(cant['coqueiro']) // 5} coqueiros · "
          f"por espécie { {e: len(v) // 5 for e, v in inst.items()} } · {DESTINO.stat().st_size / 1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: `scripts/blender/gerar_vegetacao.py`**

Copiar `$REPOS_DIR/cv_espelho_vendas/scripts/entorno/gerar_vegetacao.py` e adaptar, nesta ordem:

1. Docstring: "Vegetação do entorno (Plano 4): gera as três espécies estilizadas (coqueiro, cajueiro, arbusto de restinga) que o front instancia nas posições de `vegetacao.json`. `blender -b --factory-startup --python-exit-code 1 -P gerar_vegetacao.py -- saida.glb`."
2. Trocar `RAIZ`, `PASTA`, `P`, `AUTORIA` e `GLB` por `GLB = Path(sys.argv[sys.argv.index("--") + 1])` (com `import sys`); sem `.blend` de autoria.
3. Cores: `COPA_CAJUEIRO, COPA_CAJUEIRO_2 = "#7F8D66", "#8E9B72"`, `FRONDE = "#8A9A63"`, `ARBUSTO = "#97A27A"`, `TRONCO = "#8C7D68"`.
4. `main()` com três espécies, mantendo `Especie`, `material_vegetacao` e o export como estão:

```python
    # Coqueiro: estipe fino de ~12 m, levemente inclinado na coroa, nove folhas compridas e caídas.
    e = Especie("coqueiro")
    e.prisma(0.2, 12.0, lados=4)
    topo = Vector((0, 0, 12.0))
    e.copa(topo, 0.7, 0.8, FRONDE)
    for k in range(9):
        e.lamina(2 * math.pi * k / 9 + 0.2, topo, 4.5, 2.4, 1.0, FRONDE)
    coqueiro = e.objeto(mat, col)

    # Cajueiro: tronco curto e copa larga e baixa em dois volumes, ~6 m.
    e = Especie("cajueiro")
    e.prisma(0.3, 1.8)
    e.copa((0, 0, 3.4), 3.6, 0.55, COPA_CAJUEIRO)
    e.copa((1.6, 0.9, 4.2), 2.4, 0.6, COPA_CAJUEIRO_2)
    cajueiro = e.objeto(mat, col)

    # Arbusto de restinga: volume baixo e largo, ~1,5 m.
    e = Especie("arbusto")
    e.copa((0, 0, 0.7), 1.6, 0.55, ARBUSTO)
    arbusto = e.objeto(mat, col)

    obs = [coqueiro, cajueiro, arbusto]
```

5. Fim: sem salvar `.blend`; imprimir `"RESUMO " + json.dumps({"objetos": len(obs), "glb_mb": round(GLB.stat().st_size / 1e6, 3), "altura_m": {...}})` (formato que `blender.rodar_blender` lê).

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest -q`
Expected: tudo passa.

- [ ] **Step 6: Rodar no dado real**

Run: `uv run python -m scripts.entorno.vegetacao`
Expected: instâncias por zona e por espécie (milhares), coqueiros nos canteiros da Fase 1 (dezenas a centenas), arquivo de alguns MB.

- [ ] **Step 7: Commit**

```bash
git add scripts/entorno/vegetacao.py scripts/blender/gerar_vegetacao.py tests/test_vegetacao.py
git commit -m "feat(entorno): vegetação instanciada (coqueiro, cajueiro, arbusto) com cota do relevo"
```

---

### Task 5: Pontos — OSM, minutos de carro e fotos livres

**Files:**
- Create: `scripts/pontos/__init__.py`, `scripts/pontos/pontos.py`, `tests/test_pontos.py`

**Interfaces:**
- Consumes: `scripts/pontos/curadoria.json` (`pontos[]`: `nome`, `categoria`, `ref_lat`, `ref_lon`; opcionais `osm` = `"node/123"`/`"way/123"`/`"relation/123"` para forçar o elemento e `foto` = `"File:…"` aprovada); `extrair.MALHA`, `extrair.BASE`; `osm.Projecao`, `osm.overpass`.
- Produces: `pontos.distancia_m(lat1, lon1, lat2, lon2) -> float`; `pontos.escolher_osm(resultados, ref_lat, ref_lon, max_m=2000.0) -> dict | None`; `pontos.grafo_carro(elementos, proj) -> (xy, grafo)`; `pontos.minutos(grafo, xy, origem_xy, alvo_xy) -> int`; `pontos.licenca_livre(nome) -> bool`; `pontos.faixa(dist_m, limite=3000.0) -> str`; `pontos.galeria(candidatos) -> str` (HTML); `dados/pontos.json` (`{"versao": 1, "origem": {"x": 0, "y": 0}, "pontos": [{nome, categoria, lat, lon, x, y, km, minutos_carro, faixa, osm, foto, credito, licenca, licenca_url, fonte_foto}]}`); `dados/pontos/fotos/<slug>.jpg` (só fotos aprovadas); `cache/pontos/fotos-candidatas.html`.

- [ ] **Step 1: Testes**

`tests/test_pontos.py`:

```python
import pytest

from scripts.entorno.osm import Projecao
from scripts.pontos.pontos import (distancia_m, escolher_osm, faixa, galeria, grafo_carro, licenca_livre, minutos,
                                   slug)

P = Projecao(534600.0, 9595100.0)


def test_escolher_osm_pega_o_mais_perto_e_recusa_homonimo_longe():
    rs = [{"lat": "-3.60", "lon": "-38.80", "osm_type": "way", "osm_id": 1},
          {"lat": "-3.6601", "lon": "-38.6901", "osm_type": "node", "osm_id": 2}]
    assert escolher_osm(rs, -3.66, -38.69)["osm_id"] == 2
    assert escolher_osm(rs[:1], -3.66, -38.69) is None  # a 15 km: outro lugar com o mesmo nome


@pytest.mark.parametrize("nome,livre", [
    ("CC BY-SA 4.0", True), ("CC BY 2.0", True), ("CC0", True), ("Public domain", True),
    ("CC BY-NC-SA 4.0", False), ("CC BY-ND 3.0", False), ("Copyrighted", False), ("", False)])
def test_licenca_livre(nome, livre):
    assert licenca_livre(nome) is livre


def test_faixa_e_distancia():
    assert faixa(2999) == "proximo" and faixa(3001) == "distante"
    assert distancia_m(-3.66, -38.69, -3.66, -38.68) == pytest.approx(1110, rel=0.01)


def _way(i, nos, pts, highway="primary", **tags):
    return {"type": "way", "id": i, "nodes": nos, "tags": {"highway": highway, **tags},
            "geometry": [{"lon": lon, "lat": lat} for lon, lat in (P.lonlat(x, y) for x, y in pts)]}


def test_minutos_de_carro_pelo_grafo_com_mao_unica():
    elementos = [_way(1, [1, 2], [(0, 0), (5000, 0)]),  # 5 km a 50 km/h = 6 min
                 _way(2, [2, 3], [(5000, 0), (5000, 1000)], oneway="yes")]  # 1 km só para o norte
    xy, g = grafo_carro(elementos, P)
    assert minutos(g, xy, (0, 0), (5000, 0)) == 6 + 1  # + 1 min de manobra
    assert minutos(g, xy, (0, 0), (5000, 1000)) == 9  # 6 + 1,2 + 1 = 8,2, arredondado para cima
    assert minutos(g, xy, (5000, 1000), (0, 0)) is None  # contramão, sem rota


def test_galeria_mostra_credito_e_licenca():
    html = galeria({"Praia do Cumbuco": [{"titulo": "File:A.jpg", "miniatura": "https://x/a.jpg",
                                          "autor": "Fulano", "licenca": "CC BY-SA 4.0", "pagina": "https://c/A"}]})
    assert "Praia do Cumbuco" in html and "File:A.jpg" in html and "CC BY-SA 4.0" in html and "Fulano" in html


def test_slug():
    assert slug("Lagoa do Cauípe") == "lagoa-do-cauipe"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_pontos.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'scripts.pontos'`.

- [ ] **Step 3: Implementar**

`scripts/pontos/__init__.py` vazio. `scripts/pontos/pontos.py`:

```python
"""Pontos de interesse: coordenada do OSM (Nominatim, casado pela referência da curadoria),
minutos de carro no grafo viário do OSM e fotos livres do Wikimedia Commons.

Uso: uv run python -m scripts.pontos.pontos

Escreve dados/pontos.json e cache/pontos/fotos-candidatas.html (galeria para aprovar fotos:
a escolhida vai como "foto": "File:…" no ponto da curadoria, e o script a baixa na próxima vez).
Minutos: modelo simples de argumento de venda (velocidade fixa por classe, mão única, + 1 min de
manobra), como no Manoa.
"""

import heapq
import html
import json
import math
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

from scripts.comum.ambiente import RAIZ
from scripts.entorno.extrair import BASE, MALHA
from scripts.entorno.osm import AGENTE, Projecao, overpass

CURADORIA = RAIZ / "scripts" / "pontos" / "curadoria.json"
DESTINO = RAIZ / "dados" / "pontos.json"
FOTOS = RAIZ / "dados" / "pontos" / "fotos"
CACHE = RAIZ / "cache" / "pontos"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
COMMONS = "https://commons.wikimedia.org/w/api.php"
CARRO_KMH = {
    "motorway": 80, "trunk": 60, "primary": 50, "secondary": 40, "tertiary": 35, "motorway_link": 35,
    "trunk_link": 35, "primary_link": 30, "secondary_link": 30, "tertiary_link": 25, "unclassified": 30,
    "residential": 25, "living_street": 15, "service": 15, "track": 15,
}
MANOBRA_MIN = 1
PE_M_MIN = 75  # do ponto ao grafo e do grafo ao destino, a pé


def slug(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371008.8 * math.asin(math.sqrt(a))


def escolher_osm(resultados: list[dict], ref_lat: float, ref_lon: float, max_m: float = 2000.0) -> dict | None:
    """O resultado do OSM mais perto da referência da curadoria; nada além de `max_m` (homônimo)."""
    perto = [(distancia_m(ref_lat, ref_lon, float(r["lat"]), float(r["lon"])), r) for r in resultados]
    perto = [(d, r) for d, r in perto if d <= max_m]
    return min(perto, key=lambda t: t[0])[1] if perto else None


def faixa(dist_m: float, limite: float = 3000.0) -> str:
    return "proximo" if dist_m <= limite else "distante"


def licenca_livre(nome: str) -> bool:
    n = (nome or "").upper()
    if "NC" in n.replace("-", " ").split() or "-NC" in n or "-ND" in n or " ND" in n:
        return False
    return n.startswith(("CC BY", "CC0", "PUBLIC DOMAIN", "PD"))


def grafo_carro(elementos: list[dict], proj: Projecao) -> tuple[dict, dict]:
    xy, grafo = {}, {}
    for w in elementos:
        tags = w.get("tags", {})
        classe = tags.get("highway")
        if classe not in CARRO_KMH or "nodes" not in w or "geometry" not in w:
            continue
        if tags.get("motor_vehicle") == "no" or tags.get("access") in ("no", "private"):
            continue
        for n, g in zip(w["nodes"], w["geometry"]):
            xy[n] = proj.xy(g["lon"], g["lat"])
        mao = tags.get("oneway") or ("yes" if tags.get("junction") == "roundabout" else None)
        for a, b in zip(w["nodes"], w["nodes"][1:]):
            t = math.dist(xy[a], xy[b]) / (CARRO_KMH[classe] * 1000 / 60)
            if mao != "-1":
                grafo.setdefault(a, []).append((b, t))
            if mao not in ("yes", "1", "true", "-1"):
                grafo.setdefault(b, []).append((a, t))
            if mao == "-1":
                grafo.setdefault(b, []).append((a, t))
    return xy, grafo


def minutos(grafo: dict, xy: dict, origem: tuple[float, float], alvo: tuple[float, float]) -> int | None:
    nos = list(xy)
    perto = lambda p: min(nos, key=lambda n: math.dist(xy[n], p))  # noqa: E731
    a, b = perto(origem), perto(alvo)
    tempo, fila = {a: 0.0}, [(0.0, a)]
    while fila:
        t, n = heapq.heappop(fila)
        if n == b:
            ponta = (math.dist(xy[a], origem) + math.dist(xy[b], alvo)) / PE_M_MIN
            return math.ceil(t + ponta + MANOBRA_MIN)
        if t > tempo[n]:
            continue
        for v, dt in grafo.get(n, []):
            if t + dt < tempo.get(v, math.inf):
                tempo[v] = t + dt
                heapq.heappush(fila, (t + dt, v))
    return None


def _get(url: str, params: dict, cache) -> dict | list:
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(req, timeout=60) as r:
        dados = json.loads(r.read())
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    time.sleep(1.1)  # política de uso do Nominatim e boa educação com o Commons
    return dados


def _sem_html(texto: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", texto or "")).strip()


def candidatos_commons(nome: str, lat: float, lon: float) -> list[dict]:
    """Arquivos do Commons perto do ponto (2 km) e pelo nome, só com licença livre."""
    comum = {"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|extmetadata",
             "iiurlwidth": 1600}
    perto = _get(COMMONS, {**comum, "generator": "geosearch", "ggscoord": f"{lat}|{lon}", "ggsradius": 2000,
                           "ggsnamespace": 6, "ggslimit": 20}, CACHE / "commons" / f"{slug(nome)}-geo.json")
    busca = _get(COMMONS, {**comum, "generator": "search", "gsrsearch": f"{nome} Ceará", "gsrnamespace": 6,
                           "gsrlimit": 20}, CACHE / "commons" / f"{slug(nome)}-busca.json")
    vistos, saida = set(), []
    for dados in (perto, busca):
        for pg in (dados.get("query", {}).get("pages", {}) or {}).values():
            info = (pg.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})
            lic = meta.get("LicenseShortName", {}).get("value", "")
            if pg["title"] in vistos or not licenca_livre(lic) or not info.get("thumburl"):
                continue
            vistos.add(pg["title"])
            saida.append({"titulo": pg["title"], "miniatura": info["thumburl"], "pagina": info.get("descriptionurl"),
                          "autor": _sem_html(meta.get("Artist", {}).get("value", "")), "licenca": lic,
                          "licenca_url": meta.get("LicenseUrl", {}).get("value")})
    return saida


def galeria(candidatos: dict[str, list[dict]]) -> str:
    blocos = []
    for nome, cs in candidatos.items():
        itens = "".join(
            f'<figure><img src="{html.escape(c["miniatura"])}" loading="lazy" width="320">'
            f'<figcaption><b>{html.escape(c["titulo"])}</b><br>{html.escape(c["autor"])} · '
            f'{html.escape(c["licenca"])} · <a href="{html.escape(c.get("pagina") or "")}">página</a></figcaption></figure>'
            for c in cs) or "<p>sem foto livre encontrada</p>"
        blocos.append(f"<section><h2>{html.escape(nome)}</h2>{itens}</section>")
    return ("<!doctype html><meta charset=utf-8><title>Fotos candidatas</title>"
            "<style>body{font:14px sans-serif;margin:16px}figure{display:inline-block;width:330px;vertical-align:top}"
            "img{max-width:320px}</style><h1>Fotos candidatas (Wikimedia Commons, licença livre)</h1>"
            + "".join(blocos))


def coordenada_osm(p: dict) -> dict:
    if p.get("osm"):
        tipo, ident = p["osm"].split("/")
        el = overpass(f"[out:json];{tipo}({ident});out center;", CACHE / "osm" / f"{tipo}-{ident}.json")["elements"][0]
        return {"lat": el.get("lat") or el["center"]["lat"], "lon": el.get("lon") or el["center"]["lon"],
                "osm_type": tipo, "osm_id": int(ident)}
    caixa = 0.05
    rs = _get(NOMINATIM, {"q": p["nome"], "format": "jsonv2", "limit": 10, "bounded": 1,
                          "viewbox": f"{p['ref_lon'] - caixa},{p['ref_lat'] + caixa},{p['ref_lon'] + caixa},{p['ref_lat'] - caixa}"},
              CACHE / "nominatim" / f"{slug(p['nome'])}.json")
    r = escolher_osm(rs, p["ref_lat"], p["ref_lon"])
    if r is None:
        raise SystemExit(f"{p['nome']}: sem elemento do OSM a até 2 km da referência; "
                         f"ponha \"osm\": \"node/…\" na curadoria")
    return {"lat": float(r["lat"]), "lon": float(r["lon"]), "osm_type": r["osm_type"], "osm_id": r["osm_id"]}


def baixar_foto(p: dict, cand: list[dict]) -> dict:
    escolhida = next((c for c in cand if c["titulo"] == p["foto"]), None)
    if escolhida is None:
        raise SystemExit(f"{p['nome']}: foto {p['foto']} não está entre as candidatas livres")
    destino = FOTOS / f"{slug(p['nome'])}.jpg"
    if not destino.exists():
        FOTOS.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(escolhida["miniatura"], headers={"User-Agent": AGENTE})
        with urllib.request.urlopen(req, timeout=120) as r:
            destino.write_bytes(r.read())
    return {"foto": f"pontos/fotos/{destino.name}", "credito": escolhida["autor"], "licenca": escolhida["licenca"],
            "licenca_url": escolhida["licenca_url"], "fonte_foto": escolhida["pagina"]}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    proj = Projecao(georref["origem"]["E"], georref["origem"]["N"])
    cur = json.loads(CURADORIA.read_text(encoding="utf-8"))
    centro = tuple(json.loads(BASE.read_text(encoding="utf-8"))["centro"])
    xy, grafo = grafo_carro(json.loads(MALHA.read_text(encoding="utf-8"))["elements"]
                            + json.loads((MALHA.parent / "osm-vias.json").read_text(encoding="utf-8"))["elements"], proj)
    pontos, candidatos = [], {}
    for p in cur["pontos"]:
        c = coordenada_osm(p)
        x, y = proj.xy(c["lon"], c["lat"])
        dist = math.dist((x, y), centro)
        cand = candidatos_commons(p["nome"], c["lat"], c["lon"])
        candidatos[p["nome"]] = cand
        foto = baixar_foto(p, cand) if p.get("foto") else {k: None for k in
                                                           ("foto", "credito", "licenca", "licenca_url", "fonte_foto")}
        m = minutos(grafo, xy, centro, (x, y))
        if m is None:
            raise SystemExit(f"{p['nome']}: sem rota de carro no grafo")
        pontos.append({"nome": p["nome"], "categoria": p["categoria"], "lat": round(c["lat"], 6), "lon": round(c["lon"], 6),
                       "x": round(x, 1), "y": round(y, 1), "km": round(dist / 1000, 1), "minutos_carro": m,
                       "faixa": faixa(dist), "osm": f"{c['osm_type']}/{c['osm_id']}", **foto})
        print(f"{p['nome'][:30]:30s} {dist / 1000:5.1f} km {m:3d} min  {pontos[-1]['faixa']:8s} "
              f"{len(cand):2d} fotos livres  ref↔OSM {distancia_m(p['ref_lat'], p['ref_lon'], c['lat'], c['lon']):5.0f} m")
    DESTINO.write_text(json.dumps({"versao": 1, "origem": {"x": 0, "y": 0},
                                   "fontes": "coordenadas © OpenStreetMap contributors (ODbL); fotos: Wikimedia Commons (autor e licença por ponto)",
                                   "pontos": pontos}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (CACHE / "fotos-candidatas.html").write_text(galeria(candidatos), encoding="utf-8")
    print(f"{len(pontos)} pontos → {DESTINO.relative_to(RAIZ)}; galeria → cache/pontos/fotos-candidatas.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest -q`
Expected: tudo passa.

- [ ] **Step 5: Rodar no dado real**

Run: `uv run python -m scripts.pontos.pontos`
Expected: uma linha por ponto com km, minutos, faixa (Icaraí `proximo`, os demais `distante`), número de fotos livres e a distância referência↔OSM (poucos metros a centenas). Um ponto sem casamento pede `"osm": "…"` na curadoria: resolver procurando o elemento no OSM perto da referência (Overpass `nwr(around:500,lat,lon)[name~"…"]`) e ledger. `dados/pontos.json` com 15 pontos e `foto: null`.

- [ ] **Step 6: Commit**

```bash
git add scripts/pontos tests/test_pontos.py dados/pontos.json
git commit -m "feat(pontos): pontos no OSM, minutos de carro e fotos livres candidatas"
```

---

### Task 6: Blender, GLBs e documentação

**Files:**
- Modify: `scripts/blender/gerar_loteamento.py`, `scripts/loteamento/blender.py`, `tests/test_blender.py`, `docs/superpowers/plans/2026-10-14-00-plano-mestre.md`

**Interfaces:**
- Consumes: `preparar.MAPA_JSON`, `preparar.DETALHE`, `vegetacao.DESTINO`, `terreno.DESTINO_ENTORNO`, `cena.DESTINO`; `gerar_vegetacao.py`.
- Produces: `blender.com_mapa(dados, mapa, nomes) -> dict`; `blender.juntar_cenas(*dados) -> dict`; `conferir_entorno` exige `Entorno`, `Mar`, `ViasPrincipais`, `Predios`; `LIMITE_ENTORNO_MB = 8.0`; `LIMITE_VEGETACAO_MB = 0.5`; saídas finais na pasta da maquete.

- [ ] **Step 1: Testes**

Em `tests/test_blender.py` (o import do módulo ganha `com_mapa, juntar_cenas`; `test_conferir_entorno_acusa_falta_e_peso` do 3c sai, substituído pelo teste abaixo e por `assert conferir_entorno(["Entorno", "Mar", "ViasPrincipais", "Predios"], 8.4) == ["entorno.glb com 8.4 MB (alvo 8.0 MB)"]`):

```python
def test_com_mapa_poe_textura_so_nos_nomes_pedidos():
    dados = {"objetos": [{"nome": "Entorno", "material": "entorno"}, {"nome": "Mar", "material": "mar"}]}
    mapa = {"arquivo": "C:/m.jpg", "ext": [0, 0, 10, 10], "px": [8, 8]}
    novo = com_mapa(dados, mapa, {"Entorno"})
    assert novo["objetos"][0]["textura"] == {"arquivo": "C:/m.jpg", "ext": [0, 0, 10, 10]}
    assert novo["objetos"][0]["material"] == "chao" and "textura" not in novo["objetos"][1]
    assert "textura" not in dados["objetos"][0]  # não altera a entrada


def test_juntar_cenas():
    assert [o["nome"] for o in juntar_cenas({"objetos": [{"nome": "A"}]}, {"objetos": [{"nome": "B"}]})["objetos"]] == ["A", "B"]


def test_conferir_entorno_exige_os_objetos_novos():
    assert conferir_entorno(["Entorno", "Mar", "ViasPrincipais", "Predios"], 5.0) == []
    assert conferir_entorno(["Entorno", "Mar"], 5.0) == ["objeto do entorno faltando no GLB: ViasPrincipais",
                                                         "objeto do entorno faltando no GLB: Predios"]


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_textura_vira_uv_e_imagem_no_glb(tmp_path):
    from PIL import Image

    Image.new("RGB", (8, 8), (200, 100, 50)).save(tmp_path / "m.jpg")
    cena = {"objetos": [{"nome": "Entorno", "material": "chao", "vertices": [[0, 0, 0], [10, 0, 0], [0, 10, 0]],
                         "faces": [[0, 1, 2]], "textura": {"arquivo": str(tmp_path / "m.jpg"), "ext": [0, 0, 10, 10]}},
                        {"nome": "Predios", "material": "predio", "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 1]],
                         "faces": [[0, 1, 2]], "suave": False}]}
    (tmp_path / "c.json").write_text(json.dumps(cena), encoding="utf-8")
    rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / "c.json"), str(tmp_path / "c.blend"), str(tmp_path / "c.glb"))
    dados = (tmp_path / "c.glb").read_bytes()
    tamanho = struct.unpack_from("<I", dados, 12)[0]
    gltf = json.loads(dados[20:20 + tamanho])
    assert gltf.get("images") and gltf.get("textures")
    assert any("TEXCOORD_0" in p["attributes"] for m in gltf["meshes"] for p in m["primitives"])
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_blender.py -q`
Expected: FAIL com `ImportError: cannot import name 'com_mapa'`.

- [ ] **Step 3: `gerar_loteamento.py`**

- `MATERIAIS` ganha `"predio": ((0.90, 0.88, 0.84), 0.85)` e `"via_principal_osm": ((0.47, 0.46, 0.47), 0.9)`.
- Função nova:

```python
def material_textura(arquivo: str) -> bpy.types.Material:
    """Chão pintado: a imagem do mapa na cor base (o glTF leva a imagem embutida)."""
    nome = "chao"
    if nome in bpy.data.materials:
        return bpy.data.materials[nome]
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(arquivo, check_existing=True)
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    return m
```

- Em `construir`, depois de `me.update()`:

```python
        if "textura" in o:
            x0, y0, x1, y1 = o["textura"]["ext"]
            uv = me.uv_layers.new(name="UVMap")
            for loop in me.loops:
                co = me.vertices[loop.vertex_index].co
                uv.data[loop.index].uv = ((co.x - x0) / (x1 - x0), (co.y - y0) / (y1 - y0))
            me.materials.append(material_textura(o["textura"]["arquivo"]))
        else:
            me.materials.append(material(o["material"]))
        if o.get("suave", True):
            me.shade_smooth()  # glTF compartilha o vértice entre triângulos
```

(substitui as linhas antigas de `materials.append` e `shade_smooth`; prédios ficam facetados).
- No export: `export_texcoords=True`.

- [ ] **Step 4: `blender.py`**

```python
from scripts.entorno.preparar import DETALHE, MAPA_JSON
from scripts.entorno.vegetacao import DESTINO as VEGETACAO_JSON

LIMITE_ENTORNO_MB = 8.0
LIMITE_VEGETACAO_MB = 0.5
SCRIPT_VEGETACAO = RAIZ / "scripts" / "blender" / "gerar_vegetacao.py"
OBJETOS_ENTORNO = ("Entorno", "Mar", "ViasPrincipais", "Predios")


def com_mapa(dados: dict, mapa: dict, nomes: set[str]) -> dict:
    """Cópia da cena com o chão pintado (material `chao`) nos objetos `nomes`."""
    tex = {"arquivo": mapa["arquivo"], "ext": mapa["ext"]}
    return {"objetos": [{**o, "material": "chao", "textura": tex} if o["nome"] in nomes else o
                        for o in dados["objetos"]]}


def juntar_cenas(*cenas: dict) -> dict:
    return {"objetos": [o for c in cenas for o in c["objetos"]]}
```

`conferir_entorno` passa a iterar `OBJETOS_ENTORNO` (mensagem igual). `main`:

```python
    ler = lambda c: json.loads(c.read_text(encoding="utf-8"))  # noqa: E731
    mapa = ler(MAPA_JSON)
    cena_entorno = RAIZ / "cache" / "cena" / "entorno-completo.json"
    cena_entorno.write_text(json.dumps(com_mapa(juntar_cenas(ler(ENTORNO_JSON), ler(DETALHE)), mapa, {"Entorno"})),
                            encoding="utf-8")
    cena_lote = RAIZ / "cache" / "cena" / "loteamento-mapa.json"
    cena_lote.write_text(json.dumps(com_mapa(ler(CENA_JSON), mapa, {"Terreno"})), encoding="utf-8")
```

e roda: entorno com `cena_entorno` → `entorno.glb/.blend` (`conferir_entorno`); vegetação com `rodar_blender(blender, SCRIPT_VEGETACAO, str(destino / "vegetacao.glb"))` (erro se `glb_mb > LIMITE_VEGETACAO_MB`); loteamento com `cena_lote` e contexto `cena_entorno` (prévias); copia `VEGETACAO_JSON` para `destino / "vegetacao.json"` (`shutil.copy2`). Imprime os três resumos.

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest -q`
Expected: tudo passa.

- [ ] **Step 6: Gerar as saídas reais**

Run: `uv run python -m scripts.loteamento.cena && uv run python -m scripts.loteamento.blender`
Expected: saída 0; `entorno.glb` ≤ 8 MB com os 4 objetos; `vegetacao.glb` ≤ 0,5 MB; `loteamento.glb` ≤ 8 MB com 355 objetos; na pasta da maquete também `vegetacao.json`, nenhum `.blend1`. Ler `cache/cena/previa-entorno.png` e `previa.png`: vias pintadas no chão, faixas principais perto do loteamento, prédios assentados, mar limpo.

- [ ] **Step 7: Documentação**

Plano-mestre: linha do Plano 4 passa a citar `2026-10-14-04-entorno-vegetacao-pontos.md` e as entregas (`entorno.glb` com mapa pintado, faixas e prédios; `vegetacao.glb/.json`; `dados/pontos.json`); em "Contratos entre planos", acrescentar:

- **`dados/pontos.json`:** `{"versao": 1, "pontos": [{nome, categoria, lat, lon, x, y, km, minutos_carro, faixa ("proximo" até 3 km, "distante"), osm, foto, credito, licenca, licenca_url, fonte_foto}]}`; `foto` relativo a `dados/` ou `null` até a aprovação.
- **`vegetacao.json`:** campos `x_dm, y_dm, z_cm, escala_pct, rotacao_graus` por espécie (`coqueiro`, `cajueiro`, `arbusto`), embaralhados; malhas `VEG_<especie>` no `vegetacao.glb`.

- [ ] **Step 8: Commit**

```bash
git add scripts/blender/gerar_loteamento.py scripts/loteamento/blender.py tests/test_blender.py docs/superpowers/plans/2026-10-14-00-plano-mestre.md
git commit -m "feat(blender): entorno com mapa pintado, faixas, prédios e vegetação; plano-mestre com o 4"
```

---

## Depois do plano (gate ⛔)

Fotos: o usuário olha `cache/pontos/fotos-candidatas.html` (na sessão de revisão visual) e escolhe uma por ponto; a escolha entra como `"foto": "File:…"` na curadoria e `uv run python -m scripts.pontos.pontos` baixa e credita. Ponto sem foto livre fica sem foto até haver foto própria.
