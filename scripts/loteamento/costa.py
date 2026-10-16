"""Linha de costa do OSM imposta ao relevo: o plano do mar corta a terra sobre a linha, não na
escada das células de 30 m do Copernicus.

Perto da costa a cota vira a distância com sinal até a linha vezes a inclinação da praia (a
mesma dos dois lados), e a interpolação bilinear de uma função afim é exata: o contorno da água
segue a linha dentro de cada célula. Mais longe, a terra volta ao relevo e o fundo desce até o
rebaixo do mar.
"""

import numpy as np
import shapely
from shapely.geometry import LineString, MultiLineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import split, unary_union

from scripts.comum.ambiente import RAIZ

from .relevo import Grade

OSM_AREAS = RAIZ / "cache" / "entorno" / "osm-areas.json"


def agua_do_osm(e0: float, n0: float) -> BaseGeometry | None:
    """Rios e lagoas do cache do entorno (as áreas `agua` do OSM), em coordenadas locais."""
    import json

    from scripts.entorno.osm import Projecao, poligono_osm, tipo_area

    if not OSM_AREAS.exists():
        return None
    proj = Projecao(e0, n0)
    partes = [poligono_osm(proj, e) for e in json.loads(OSM_AREAS.read_text(encoding="utf-8"))["elements"]
              if tipo_area(e.get("tags", {})) == "agua"]
    return unary_union([p for p in partes if p is not None])


def linhas_de_costa(e0: float, n0: float) -> list[LineString]:
    """`natural=coastline` do cache do entorno, em coordenadas locais; vazio sem o cache."""
    import json

    from scripts.entorno.osm import Projecao, linha_osm

    if not OSM_AREAS.exists():
        return []
    proj = Projecao(e0, n0)
    return [LineString(linha_osm(proj, e["geometry"]))
            for e in json.loads(OSM_AREAS.read_text(encoding="utf-8"))["elements"]
            if e.get("tags", {}).get("natural") == "coastline" and len(e.get("geometry") or []) > 1]


def _prolongar(linha: LineString, d: float) -> LineString:
    c = list(linha.coords)

    def ponta(a, b):
        v = np.subtract(a, b)
        return tuple(np.add(a, v / (np.linalg.norm(v) or 1.0) * d))

    return LineString([ponta(c[0], c[1]), *c, ponta(c[-1], c[-2])])


def mar_da_costa(linhas: list[LineString], centro: tuple[float, float], raio: float) -> BaseGeometry:
    """Polígono do mar num disco de `raio`. Convenção do OSM: terra à esquerda do sentido da
    linha, água à direita. Cada trecho é prolongado nas pontas até sair do disco."""
    disco = Point(centro).buffer(raio, 256)
    # directed: o sentido de cada via do OSM diz de que lado está a terra
    juntas = shapely.line_merge(MultiLineString([list(l.coords) for l in linhas]), directed=True)
    trechos = [t for t in getattr(juntas, "geoms", [juntas]) if t.length > 0]
    pedacos = split(disco, unary_union([_prolongar(t, 2 * raio) for t in trechos])).geoms
    voto = [0] * len(pedacos)
    for t in trechos:
        for lado, sinal in ((-1.0, 1), (1.0, -1)):  # offset negativo = à direita
            ao_lado = t.offset_curve(lado * 1.0)
            for k in np.linspace(0.05, 0.95, 19):
                p = ao_lado.interpolate(k, normalized=True)
                for i, pd in enumerate(pedacos):
                    if pd.contains(p):
                        voto[i] += sinal
    return unary_union([pd for pd, v in zip(pedacos, voto) if v > 0])


def costa_suave(g: Grade, mar: BaseGeometry, nivel: float, praia: float, fundo: float, rebaixo: float,
                celula: float | None = None, agua: BaseGeometry | None = None) -> Grade:
    """Cota de `g` com a costa de `mar`: rampa de `praia` (m/m) dos dois lados até 1,5 célula da
    linha; além disso o fundo desce a `fundo` até `nivel − rebaixo` e a terra volta ao relevo até
    4,5 células (a duna além disso fica como está). Abaixo do nível terra adentro só fica o que
    está em `agua` (rios e lagoas do OSM): o resto é a costa em escada do Copernicus e vira terra. `celula` (m) mede as faixas; uma grade fina que encosta numa grossa
    usa a célula da grossa, e as duas coincidem perto da costa (sem dente na emenda)."""
    gx, gy = np.meshgrid(g.x0 + g.passo * np.arange(g.nx), g.y0 + g.passo * np.arange(g.ny))
    z0 = np.array(g.z, dtype=float)
    no_mar = shapely.contains_xy(mar, gx, gy)
    linha = mar.boundary
    d = shapely.distance(linha, shapely.points(gx, gy))
    celula = celula or g.passo
    perto = 1.5 * celula
    rampa = nivel + d * praia
    z_mar = nivel - np.minimum(np.minimum(d, perto) * praia + np.maximum(d - perto, 0.0) * fundo, rebaixo)
    # De 1,5 a 4,5 células, da rampa ao relevo (acima da água): sem degrau e sem aplainar a duna.
    w = np.clip((d - perto) / (2 * perto), 0.0, 1.0)
    z_terra = (1 - w) * rampa + w * np.maximum(z0, nivel + 0.2)
    rio = (z0 < nivel) & shapely.contains_xy(agua, gx, gy) if agua is not None else np.zeros_like(no_mar)
    z = np.where(no_mar, z_mar, np.where(rio, z0, z_terra))
    return Grade(g.x0, g.y0, g.passo, g.nx, g.ny, np.round(z, 2).tolist())
