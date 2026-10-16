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
    tile_px: int
    tile_margem_px: int = 2
    masterplan: bool = True
    masterplan_saturacao: float = 0.35
    masterplan_opacidade: float = 0.55
    raio_predios_orla: float = 0.0  # na faixa da orla, prédios até este raio (0: só raio_predios)
    orla_m: float = 0.0             # largura da faixa da orla, a partir da linha de costa do OSM

    @property
    def raio_download_predios(self) -> float:
        return max(self.raio_predios, self.raio_predios_orla)

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


def quebra_mares(proj: Projecao, osm: dict, centro: tuple[float, float], raio: float,
                 largura: float = 8.0) -> list:
    """Quebra-mares e espigões do OSM no raio, como polígonos (anéis): o que vem como linha
    ganha `largura` de pedra; way fechado e multipolygon ficam como estão."""
    circulo = Point(centro).buffer(raio, 128)
    partes = []
    for e in osm["elements"]:
        g = poligono_osm(proj, e)
        if g is None and e["type"] == "way" and len(e.get("geometry") or []) >= 2:
            g = LineString(linha_osm(proj, e["geometry"])).buffer(largura / 2, cap_style="flat", join_style="mitre")
        if g is not None and not g.is_empty:
            partes.append(g.intersection(circulo))
    return aneis(unary_union(partes)) if partes else []


def montar_base(proj: Projecao, centro: tuple[float, float], cfg: EntornoCfg,
                osm_vias: dict, osm_areas: dict, overture: dict) -> dict:
    """Recorta e converte; falha alto se um download veio vazio (Overpass às vezes devolve 0)."""
    cvias = Point(centro).buffer(cfg.raio_vias, 128)
    cpredios = Point(centro).buffer(cfg.raio_predios, 128)
    if cfg.raio_predios_orla > cfg.raio_predios and cfg.orla_m > 0:
        costa = unary_union([LineString(linha_osm(proj, e["geometry"])) for e in osm_areas["elements"]
                             if e.get("tags", {}).get("natural") == "coastline" and len(e.get("geometry") or []) > 1])
        if not costa.is_empty:
            orla = costa.buffer(cfg.orla_m).intersection(Point(centro).buffer(cfg.raio_predios_orla, 128))
            cpredios = cpredios.union(orla)
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
    if not areas:
        raise SystemExit("Nenhuma área no raio: o download do Overpass veio vazio? Rode com --refazer.")
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
    r = cfg.raio_download_predios
    (lo0, la0), (lo1, la1) = (proj.lonlat(centro[0] - r, centro[1] - r), proj.lonlat(centro[0] + r, centro[1] + r))
    # o raio entra no nome: ampliar a faixa baixa de novo sem precisar do --refazer
    overture = baixar_overture((lo0, la0, lo1, la1), CACHE / f"overture-predios-{r:.0f}.json", refazer)
    base = montar_base(proj, centro, cfg, osm_vias, osm_areas, overture)
    osm_qm = overpass(f"[out:json][timeout:120];wr[man_made~\"^(breakwater|groyne)$\"]{cerca};out geom;",
                      CACHE / "osm-quebra-mar.json", refazer)
    base["quebra_mares"] = quebra_mares(proj, osm_qm, centro, cfg.raio_vias)
    base["fontes"]["osm_timestamp"] = osm_vias.get("osm3s", {}).get("timestamp_osm_base")
    base["gerado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    BASE.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
    print(f"vias {len(base['vias'])} {dict(Counter(v['classe'] for v in base['vias']).most_common(6))}")
    print(f"áreas {len(base['areas'])} {dict(Counter(a['tipo'] for a in base['areas']).most_common(6))}")
    print(f"prédios {len(base['predios'])} (Overture {base['fontes']['overture_release']}) · "
          f"quebra-mares {len(base['quebra_mares'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
