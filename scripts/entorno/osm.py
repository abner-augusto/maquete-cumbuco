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
            if "error" in dados.get("remark", ""):  # 200 com lista vazia e o erro só na observação
                erros.append(f"{url}: {dados['remark']}")
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
