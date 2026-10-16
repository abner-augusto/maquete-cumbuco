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


def _prolongar(linha: LineString, d: float, base: float = 3000.0) -> LineString:
    """A linha com as pontas esticadas `d` m. A direção é a média dos últimos `base` m de orla
    (da ponta até o ponto a `base` m dela, pela linha), não a do último trecho, que no OSM costuma
    dobrar num espigão ou na foz: fora do entorno o mar segue o rumo geral da orla."""
    c = list(linha.coords)
    b = min(base, linha.length / 2)

    def ponta(a, de):
        v = np.subtract(a, de)
        return tuple(np.add(a, v / (np.linalg.norm(v) or 1.0) * d))

    inicio = ponta(c[0], linha.interpolate(b).coords[0])
    fim = ponta(c[-1], linha.interpolate(linha.length - b).coords[0])
    return LineString([inicio, *c, fim])


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
    está em `agua` (rios e lagoas do OSM): o resto é a costa em escada do Copernicus e vira terra.
    A água que fica (a lagoa da foz) entra no mar da conta: a margem dela segue o polígono do OSM. `celula` (m) mede as faixas; uma grade fina que encosta numa grossa
    usa a célula da grossa, e as duas coincidem perto da costa (sem dente na emenda)."""
    gx, gy = np.meshgrid(g.x0 + g.passo * np.arange(g.nx), g.y0 + g.passo * np.arange(g.ny))
    z0 = np.array(g.z, dtype=float)
    if agua is not None:
        baixo = z0 < nivel
        partes = [p for p in getattr(agua, "geoms", [agua])
                  if shapely.contains_xy(p, gx[baixo], gy[baixo]).any()]
        mar = unary_union([mar, *partes])
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
    z = np.where(no_mar, z_mar, z_terra)
    return Grade(g.x0, g.y0, g.passo, g.nx, g.ny, np.round(z, 2).tolist())


def malha_mar(centro: tuple[float, float], raio: float, mar: BaseGeometry, alcance: float,
              nivel: float) -> tuple[list[list[float]], list[list[int]]]:
    """Plano da água: o disco do entorno (sob a terra, para rios e foz no nível do mar) mais o mar
    aberto até `alcance`, só do lado do mar. Visto rente, o mar chega perto do horizonte em vez de
    acabar na borda do entorno; do lado da terra não sobra água além do entorno."""
    from .malha import triangular

    g = Point(centro).buffer(raio, 96).union(mar.intersection(Point(centro).buffer(alcance, 96)))
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    for parte in getattr(g, "geoms", [g]):
        parte = shapely.geometry.polygon.orient(parte, 1.0)  # externo anti-horário: face para cima
        verts, tris = triangular(list(parte.exterior.coords)[:-1], [list(i.coords)[:-1] for i in parte.interiors])
        base = len(vertices)
        vertices += [[round(x, 2), round(y, 2), nivel] for x, y in verts]
        for a, b, c in tris:
            (xa, ya), (xb, yb), (xc, yc) = verts[a], verts[b], verts[c]
            ccw = (xb - xa) * (yc - ya) - (yb - ya) * (xc - xa) > 0
            faces.append([base + a, base + b, base + c] if ccw else [base + a, base + c, base + b])
    return vertices, faces
