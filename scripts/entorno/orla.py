"""A orla regional: uma faixa simplificada da costa do Porto do Pecém à Praia de Iracema, para ver
de longe onde o loteamento fica. Relevo do Copernicus em grade grossa e chão pintado só com o
OSM (áreas e vias), num GLB próprio que o front carrega depois do entorno.

A faixa vai `orla_profundidade` m terra adentro da linha de costa e abraça o disco do entorno. A
borda de terra desbota pelo alfa dos vértices (a névoa não serve: de longe, a costa e a borda de
terra estão à mesma distância da câmera); a borda do mar fica inteira e some sob a água.

Uso: uv run python -m scripts.entorno.orla [--refazer]
"""

import argparse
import json
import math
import sys
from collections.abc import Callable

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from scripts.comum.ambiente import RAIZ
from scripts.loteamento.cena import CFG_TOML
from scripts.loteamento.costa import costa_suave, mar_da_costa
from scripts.loteamento.relevo import Grade
from scripts.loteamento.terreno import DESTINO_ENTORNO, DESTINO_LONGE, TerrenoCfg

from . import dem
from .extrair import CACHE, EntornoCfg
from .mapa import rasterizar
from .osm import Projecao, linha_osm, overpass, poligono_osm, tipo_area
from .tiles import da_janela, janelas

COSTA_REGIONAL = CACHE / "orla-costa.json"
DESTINO = RAIZ / "cache" / "cena" / "orla.json"
MAPA_JSON = CACHE / "orla-mapa.json"
PONTOS = RAIZ / "dados" / "pontos.json"

# Classes do OSM que entram no mapa da orla, com a largura pintada (m). De longe, a ~10 m/px, a
# largura real some: a via ganha a largura mínima que ainda se lê.
VIAS = {
    "motorway": ("via_principal", 30), "trunk": ("via_principal", 26), "primary": ("via_principal", 22),
    "secondary": ("via_principal", 18), "tertiary": ("via_local", 14), "unclassified": ("via_local", 10),
    "residential": ("via_local", 10), "living_street": ("via_local", 8),
    "motorway_link": ("via_principal", 14), "trunk_link": ("via_principal", 14),
    "primary_link": ("via_principal", 12), "secondary_link": ("via_principal", 12), "tertiary_link": ("via_local", 10),
}
URBANO = {"residential", "commercial", "retail", "industrial", "construction", "railway", "military"}
ORDEM_AREAS = ["urbano", "verde", "lazer", "areia", "estacionamento", "agua"]  # de baixo para cima


def recorte_entre(a: tuple[float, float], b: tuple[float, float], margem: float, largura: float = 1e6) -> Polygon:
    """Faixa perpendicular ao eixo a→b que guarda o trecho entre as duas pontas, mais `margem`."""
    ux, uy = np.subtract(b, a) / math.dist(a, b)
    vx, vy = -uy, ux
    t0, t1 = -margem, math.dist(a, b) + margem
    canto = lambda t, s: (a[0] + ux * t + vx * s, a[1] + uy * t + vy * s)  # noqa: E731
    return Polygon([canto(t0, -largura), canto(t1, -largura), canto(t1, largura), canto(t0, largura)])


def faixa_da_orla(costa: list[LineString], mar: BaseGeometry, centro: tuple[float, float], raio: float,
                  profundidade: float, a: tuple[float, float], b: tuple[float, float], margem: float,
                  folga_disco: float) -> BaseGeometry:
    """Terra até `profundidade` m da costa, entre as pontas `a` e `b`, mais o disco do entorno com
    `folga_disco`: a borda do disco fica dentro da faixa, onde ela ainda não desbotou."""
    perto = unary_union(costa).buffer(profundidade, 16).union(Point(centro).buffer(raio + folga_disco, 128))
    return perto.difference(mar).intersection(recorte_entre(a, b, margem)).buffer(0)


def alfa_da_borda(pontos: np.ndarray, faixa: BaseGeometry, mar: BaseGeometry, desbote: float) -> np.ndarray:
    """0 na borda de terra da faixa, 1 a `desbote` m dela; a borda que encosta no mar não conta."""
    borda = faixa.boundary.difference(mar.buffer(1.0))
    if borda.is_empty:
        return np.ones(len(pontos))
    d = shapely.distance(borda, shapely.points(pontos[:, 0], pontos[:, 1]))
    fora = ~shapely.contains_xy(faixa.buffer(1e-6), pontos[:, 0], pontos[:, 1]) & ~shapely.contains_xy(mar, pontos[:, 0], pontos[:, 1])
    return np.where(fora, 0.0, np.clip(d / desbote, 0.0, 1.0))


def malha_orla(g: Grade, faixa: BaseGeometry, centro: tuple[float, float], raio: float,
               cota_dentro: Callable[[float, float], float], afundar: float,
               janela: tuple[float, float, float, float] | None = None
               ) -> tuple[list[list[float]], list[list[int]], np.ndarray]:
    """Células da grade com o centro na faixa, menos as que caem inteiras no disco do entorno. O
    vértice sob o disco fica `afundar` m abaixo da superfície dele (`cota_dentro`): não fura o
    terreno detalhado. Devolve vértices, faces e os (x, y) dos vértices."""
    cx = g.x0 + g.passo * (np.arange(g.nx - 1) + 0.5)
    cy = g.y0 + g.passo * (np.arange(g.ny - 1) + 0.5)
    mx, my = np.meshgrid(cx, cy)
    na_faixa = shapely.contains_xy(faixa, mx, my)
    indice: dict[tuple[int, int], int] = {}
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    dentro = lambda x, y: math.hypot(x - centro[0], y - centro[1]) < raio  # noqa: E731

    def no(i: int, j: int) -> int:
        if (i, j) not in indice:
            indice[(i, j)] = len(vertices)
            x, y = g.x0 + i * g.passo, g.y0 + j * g.passo
            z = cota_dentro(x, y) - afundar if dentro(x, y) else g.z[j][i]
            vertices.append([round(x, 2), round(y, 2), round(z, 2)])
        return indice[(i, j)]

    for j in range(g.ny - 1):
        for i in range(g.nx - 1):
            if not na_faixa[j, i]:
                continue
            xa, ya = g.x0 + i * g.passo, g.y0 + j * g.passo
            xb, yb = xa + g.passo, ya + g.passo
            if janela is not None and not da_janela(janela, (xa + xb) / 2, (ya + yb) / 2):
                continue
            if all(dentro(x, y) for x in (xa, xb) for y in (ya, yb)):
                continue
            a, b, c, d = no(i, j), no(i + 1, j), no(i + 1, j + 1), no(i, j + 1)
            faces += [[a, b, c], [a, c, d]]
    xy = np.array([v[:2] for v in vertices]) if vertices else np.zeros((0, 2))
    return vertices, faces, xy


def linhas_da_costa_regional(proj: Projecao) -> list[LineString]:
    if not COSTA_REGIONAL.exists():
        return []
    return [LineString(linha_osm(proj, e["geometry"]))
            for e in json.loads(COSTA_REGIONAL.read_text(encoding="utf-8"))["elements"]
            if len(e.get("geometry") or []) > 1]


def pontas(cfg: EntornoCfg) -> tuple[tuple[float, float], tuple[float, float]]:
    """As pontas da faixa: os pontos de referência nomeados no entorno.toml (dados/pontos.json)."""
    pontos = {p["nome"]: p for p in json.loads(PONTOS.read_text(encoding="utf-8"))["pontos"]}
    try:
        return tuple((pontos[n]["x"], pontos[n]["y"]) for n in (cfg.orla_de, cfg.orla_ate))  # type: ignore[return-value]
    except KeyError as e:
        raise SystemExit(f"orla: ponto {e} não está em dados/pontos.json") from e


def caixa_lonlat(proj: Projecao, ext: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = ext
    lons, lats = zip(*(proj.lonlat(x, y) for x in (x0, x1) for y in (y0, y1)))
    return min(lats), min(lons), max(lats), max(lons)


def baixar_costa(proj: Projecao, cfg: EntornoCfg, refazer: bool = False) -> dict:
    """A linha de costa de toda a orla: o mar da cena (terreno.py) segue ela além do entorno."""
    a, b = pontas(cfg)
    m = cfg.orla_margem + cfg.orla_profundidade
    s, w, n, e = caixa_lonlat(proj, (min(a[0], b[0]) - m, min(a[1], b[1]) - m, max(a[0], b[0]) + m, max(a[1], b[1]) + m))
    return overpass(f"[out:json][timeout:180];way[natural=coastline]({s},{w},{n},{e});out geom;", COSTA_REGIONAL, refazer)


def _poly_overpass(proj: Projecao, g: BaseGeometry) -> str:
    casca = g.convex_hull if g.geom_type != "Polygon" else Polygon(g.exterior)
    casca = casca.buffer(300).simplify(300)
    return " ".join(f"{lat:.5f} {lon:.5f}" for lon, lat in (proj.lonlat(x, y) for x, y in list(casca.exterior.coords)[:-1]))


def camadas_do_mapa(proj: Projecao, areas: dict, vias: dict, faixa: BaseGeometry) -> list[tuple[str, BaseGeometry]]:
    por_tipo: dict[str, list] = {t: [] for t in ORDEM_AREAS}
    for e in areas["elements"]:
        tags = e.get("tags", {})
        tipo = tipo_area(tags)
        if tipo and tipo.startswith("uso:"):
            tipo = "urbano" if tipo[4:] in URBANO else None
        g = poligono_osm(proj, e) if tipo in por_tipo else None
        if g is not None and not g.is_empty:
            por_tipo[tipo].append(g.buffer(0))
    camadas = [(t, unary_union(gs).intersection(faixa.buffer(500))) for t, gs in por_tipo.items() if gs]
    for grupo in ("via_local", "via_principal"):
        linhas = [LineString(linha_osm(proj, e["geometry"])).buffer(VIAS[e["tags"]["highway"]][1] / 2, 2)
                  for e in vias["elements"]
                  if VIAS.get(e.get("tags", {}).get("highway"), ("",))[0] == grupo and len(e.get("geometry") or []) > 1]
        if linhas:
            camadas.append((grupo, unary_union(linhas).intersection(faixa.buffer(500))))
    return camadas


def gerar_tiles(camadas, ext, passo: float, px: int) -> dict[str, dict]:
    tiles = {}
    for k, jan in janelas(ext, passo).items():
        img = rasterizar(camadas, jan, px)
        arquivo = CACHE / f"orla_{k}.jpg"
        img.save(arquivo, quality=82)
        tiles[k] = {"arquivo": str(arquivo), "ext": list(jan), "janela": list(jan), "px": list(img.size)}
    return tiles


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--refazer", action="store_true", help="ignora o cache do Overpass")
    refazer = ap.parse_args().refazer
    cfg, tcfg = EntornoCfg.carregar(), TerrenoCfg.carregar(CFG_TOML)
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    proj = Projecao(e0, n0)
    centro = dem.centro_dos_lotes()
    baixar_costa(proj, cfg, refazer)
    costa = linhas_da_costa_regional(proj)
    if not costa:
        raise SystemExit("orla: sem linha de costa no cache (o Overpass veio vazio? rode com --refazer)")
    a, b = pontas(cfg)
    mar = mar_da_costa(costa, centro, tcfg.mar_alcance)
    faixa = faixa_da_orla(costa, mar, centro, tcfg.raio, cfg.orla_profundidade, a, b, cfg.orla_margem,
                          folga_disco=cfg.orla_desbote)

    # OSM só dentro da faixa: a consulta por polígono não traz Fortaleza inteira.
    poly = _poly_overpass(proj, faixa)
    areas = overpass("[out:json][timeout:300];("
                     f"wr[landuse](poly:\"{poly}\");wr[leisure](poly:\"{poly}\");wr[natural](poly:\"{poly}\");"
                     f"wr[water](poly:\"{poly}\");wr[amenity=parking](poly:\"{poly}\"););out geom;",
                     CACHE / "orla-areas.json", refazer)
    classes = "|".join(VIAS)
    vias = overpass(f"[out:json][timeout:300];way[highway~\"^({classes})$\"](poly:\"{poly}\");out geom;",
                    CACHE / "orla-vias.json", refazer)

    # Relevo: o Copernicus na grade grossa, a costa do OSM imposta e o mesmo datum do entorno.
    passo = cfg.orla_passo
    x0, y0, x1, y1 = faixa.bounds
    x0, y0 = math.floor(x0 / passo) * passo, math.floor(y0 / passo) * passo
    nx, ny = int(math.ceil((x1 - x0) / passo)) + 1, int(math.ceil((y1 - y0) / passo)) + 1
    gx, gy = np.meshgrid(x0 + passo * np.arange(nx), y0 + passo * np.arange(ny))
    lon, lat = zip(proj.lonlat(x0, y0), proj.lonlat(x0 + passo * (nx - 1), y0 + passo * (ny - 1)))
    if not (-39 <= min(lon) and max(lon) <= -38 and -4 <= min(lat) and max(lat) <= -3):
        raise SystemExit(f"orla: a caixa {lon} {lat} sai do tile {dem.TILE} do Copernicus")
    bruto = dem.amostrar(dem.baixar(), (gx + e0).ravel(), (gy + n0).ravel()).reshape(gx.shape)
    g = costa_suave(Grade(float(x0), float(y0), float(passo), nx, ny, np.round(bruto, 2).tolist()), mar, 0.0,
                    tcfg.praia_inclinacao, tcfg.fundo_inclinacao, tcfg.mar_rebaixo, celula=passo)
    nivel = next(o for o in json.loads(DESTINO_ENTORNO.read_text(encoding="utf-8"))["objetos"]
                 if o["nome"] == "Mar")["vertices"][0][2]
    g = Grade(g.x0, g.y0, g.passo, g.nx, g.ny, (np.array(g.z) + nivel).round(2).tolist())
    longe = Grade.de_json(json.loads(DESTINO_LONGE.read_text(encoding="utf-8")))

    # A malha cobre a faixa e uma célula e meia de mar: a rampa da praia desce sob a água.
    cobre = faixa.union(faixa.buffer(1.5 * passo).intersection(mar))
    ext = (g.x0, g.y0, g.x0 + passo * (nx - 1), g.y0 + passo * (ny - 1))
    tiles = gerar_tiles(camadas_do_mapa(proj, areas, vias, faixa), ext, passo, cfg.orla_tile_px)
    MAPA_JSON.write_text(json.dumps({"tiles": tiles}), encoding="utf-8")
    objetos, tri = [], 0
    for k, jan in janelas(ext, passo).items():
        v, f, xy = malha_orla(g, cobre, centro, tcfg.raio, longe.cota_malha, cfg.orla_afundar, jan)
        if not f:
            continue
        alfa = alfa_da_borda(xy, faixa, mar, cfg.orla_desbote)
        objetos.append({"nome": f"Orla_{k}", "material": "chao", "vertices": v, "faces": f,
                        "alfa": [round(float(x), 3) for x in alfa]})
        tri += len(f)
    DESTINO.write_text(json.dumps({"objetos": objetos}), encoding="utf-8")
    comp = max(math.dist(centro, p) for p in faixa.exterior.coords) if faixa.geom_type == "Polygon" else 0
    print(f"orla {faixa.area / 1e6:.0f} km² · alcance {comp / 1000:.1f} km · {tri} triângulos · "
          f"áreas {len(areas['elements'])} · vias {len(vias['elements'])} · tiles {len(tiles)} × {cfg.orla_tile_px} px "
          f"({(ext[2] - ext[0]) / 2 / cfg.orla_tile_px:.1f} m/px)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
