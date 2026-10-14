"""Geometria plana dos polígonos do DXF. Calcula relativo ao 1º ponto para não perder precisão em UTM."""

import math

from ezdxf import path

Ponto = tuple[float, float]
_EPS = 1e-6


def poligono_fechado(e) -> bool:
    if e.dxftype() != "LWPOLYLINE":
        return False
    if e.closed:
        return True
    pts = e.get_points("xy")
    return len(pts) >= 4 and math.dist(pts[0], pts[-1]) < _EPS


def pontos_de(e, distancia: float = 0.01) -> list[Ponto]:
    pts = [(v.x, v.y) for v in path.make_path(e).flattening(distance=distancia)]
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) < _EPS:
        pts = pts[:-1]
    return pts


def _relativos(pts: list[Ponto]) -> tuple[Ponto, list[Ponto]]:
    ox, oy = pts[0]
    return (ox, oy), [(x - ox, y - oy) for x, y in pts]


def area(pts: list[Ponto]) -> float:
    _, r = _relativos(pts)
    s = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]))
    return abs(s) / 2


def centroide(pts: list[Ponto]) -> Ponto:
    (ox, oy), r = _relativos(pts)
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]):
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    a /= 2
    return (ox + cx / (6 * a), oy + cy / (6 * a))


def contem(pts: list[Ponto], p: Ponto) -> bool:
    x, y = p
    dentro = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            dentro = not dentro
    return dentro


def extensao(pts: list[Ponto]) -> tuple[float, float, float, float]:
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def segmentos(e) -> list[tuple[Ponto, Ponto, float]]:
    pts = list(e.get_points("xyb"))
    if len(pts) > 1 and math.dist(pts[0][:2], pts[-1][:2]) < _EPS:
        pts = pts[:-1]
    saida = []
    for i, (x0, y0, b) in enumerate(pts):
        x1, y1, _ = pts[(i + 1) % len(pts)]
        corda = math.dist((x0, y0), (x1, y1))
        if abs(b) < 1e-12:
            comprimento = corda
        else:
            theta = 4 * math.atan(abs(b))
            comprimento = corda / (2 * math.sin(theta / 2)) * theta
        saida.append(((x0, y0), (x1, y1), comprimento))
    return saida


def _dist_ponto_segmento(p: Ponto, a: Ponto, b: Ponto) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def indice_frente(segs: list[tuple[Ponto, Ponto, float]], vias: list[list[Ponto]]) -> int:
    def distancia(seg) -> float:
        (x0, y0), (x1, y1), _ = seg
        meio = ((x0 + x1) / 2, (y0 + y1) / 2)
        return min(_dist_ponto_segmento(meio, a, b) for via in vias for a, b in zip(via, via[1:]))

    return min(range(len(segs)), key=lambda i: distancia(segs[i]))
