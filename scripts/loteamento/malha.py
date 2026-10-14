"""Malhas da cena: polígonos (com furos) → triângulos refinados e assentados no relevo."""

import math

import mapbox_earcut
import numpy as np

from .geometria import Ponto, _dist_ponto_segmento, area, contem
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


def _dentro(fora: list[Ponto], anel: list[Ponto], tol: float = 0.01) -> bool:
    """O anel inteiro dentro de `fora` (vértice na borda conta como dentro) e não todo colado na
    borda. Anel que cruza a borda, ou que só a repete, é outro contorno do mesmo desenho, não furo."""
    lados = list(zip(fora, fora[1:] + fora[:1]))
    na_borda = [min(_dist_ponto_segmento(p, a, b) for a, b in lados) <= tol for p in anel]
    return all(b or contem(fora, p) for p, b in zip(anel, na_borda)) and not all(na_borda)


def aninhar(aneis: list[list[Ponto]]) -> list[tuple[list[Ponto], list[list[Ponto]]]]:
    """Profundidade par = contorno externo; ímpar = furo do anel imediatamente de fora."""
    ordem = sorted(aneis, key=area, reverse=True)
    pais: list[int | None] = []
    for i, anel in enumerate(ordem):
        de_fora = [j for j in range(i) if contem(ordem[j], anel[0]) and _dentro(ordem[j], anel)]
        pais.append(de_fora[-1] if de_fora else None)
    profundidade: list[int] = []
    for pai in pais:
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
        divide = {
            tuple(sorted(e)) for a, b, c in tris for e in ((a, b), (b, c), (c, a))
            if math.dist(verts[e[0]], verts[e[1]]) > max_aresta
        }
        if not divide:
            return verts, tris
        meios: dict[tuple[int, int], int] = {}

        def meio(a: int, b: int) -> int:
            k = (min(a, b), max(a, b))
            if k not in meios:
                (xa, ya), (xb, yb) = verts[a], verts[b]
                verts.append(((xa + xb) / 2, (ya + yb) / 2))
                meios[k] = len(verts) - 1
            return meios[k]

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
