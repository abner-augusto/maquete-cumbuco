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
from scipy.ndimage import distance_transform_edt, gaussian_filter

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


def _pontas(c: Curva) -> tuple[Ponto, Ponto]:
    return c.pontos[0], c.pontos[-1]


def cotar_mestras(
    mestras: list[Curva], rotulos: list[tuple[Ponto, float]], raio: float = 25.0,
    raio_curto: float = 6.0, emenda: float = 6.0,
) -> int:
    """Cota as mestras pelos rótulos. No desenho a mestra é cortada no rótulo, então o rótulo cota
    todo pedaço a até `raio_curto` (além do mais próximo, até `raio`), e o pedaço sem rótulo herda
    a cota do pedaço cotado cuja ponta está a até `emenda`."""
    votos: list[Counter] = [Counter() for _ in mestras]
    for p, z in rotulos:
        dists = [(_dist_polilinha(p, c.pontos), i) for i, c in enumerate(mestras)]
        d, i = min(dists)
        if d <= raio:
            votos[i][z] += 1
        for dj, j in dists:
            if j != i and dj <= raio_curto:
                votos[j][z] += 1
    for c, v in zip(mestras, votos):
        c.z = v.most_common(1)[0][0] if v else None
    mudou = True
    while mudou:
        mudou = False
        for c in (c for c in mestras if c.z is None):
            vizinha = next(
                (m for m in mestras if m.z is not None
                 and min(math.dist(a, b) for a in _pontas(c) for b in _pontas(m)) <= emenda),
                None,
            )
            if vizinha:
                c.z, mudou = vizinha.z, True
    return sum(1 for c in mestras if c.z is None)


def completar_mestras(mestras: list[Curva], cotadas: list[Curva], intervalo: float = 5.0) -> None:
    """Mestra que nem rótulo nem emenda cotaram (topo de duna fechado): múltiplo de `intervalo`
    mais próximo da cota da curva cotada mais perto."""
    for m in (m for m in mestras if m.z is None):
        p = m.pontos[len(m.pontos) // 2]
        _, z = min(((_dist_polilinha(p, c.pontos), c.z) for c in cotadas if c is not m), default=(0, None))
        if z is not None:
            m.z = float(round(z / intervalo) * intervalo)


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


def mascara(grade: Grade, aneis: list[list[Ponto]]) -> np.ndarray:
    """Pontos da grade dentro de algum dos anéis (z[j][i] → mascara[j, i]); par-ímpar, vetorizado."""
    gx, gy = np.meshgrid(grade.x0 + grade.passo * np.arange(grade.nx), grade.y0 + grade.passo * np.arange(grade.ny))
    dentro = np.zeros(gx.shape, dtype=bool)
    for anel in aneis:
        impar = np.zeros(gx.shape, dtype=bool)
        for (x0, y0), (x1, y1) in zip(anel, anel[1:] + anel[:1]):
            if y0 == y1:
                continue
            cruza = (y0 > gy) != (y1 > gy)
            impar ^= cruza & (gx < (x1 - x0) * (gy - y0) / (y1 - y0) + x0)
        dentro |= impar
    return dentro


def suavizar_dentro(grade: Grade, aneis: list[list[Ponto]], sigma: float, transicao: float) -> Grade:
    """Relevo terraplenado: suave dentro dos anéis, natural fora, com transição em `transicao` metros."""
    z = np.array(grade.z, dtype=float)
    dentro = mascara(grade, aneis)
    suave = gaussian_filter(z, sigma / grade.passo, mode="nearest")
    dist = distance_transform_edt(~dentro) * grade.passo
    peso = np.clip(1.0 - dist / transicao, 0.0, 1.0)
    z2 = peso * suave + (1.0 - peso) * z
    return Grade(grade.x0, grade.y0, grade.passo, grade.nx, grade.ny, np.round(z2, 2).tolist())


def _densificar(pts: list[Ponto], passo: float = 10.0) -> list[Ponto]:
    saida = [pts[0]]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) // passo))
        saida += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(1, n + 1)]
    return saida


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
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
    completar_mestras(mestras, [c for c in mestras + inters if c.z is not None])
    cotar_intermediarias(inters, mestras)  # de novo, agora com os topos cotados
    grade = gerar_grade(mestras + inters, ext, PASSO_GRADE)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(grade.para_json()), encoding="utf-8")
    zs = [v for linha in grade.z for v in linha]
    print(
        f"mestras {len(mestras)} ({sem} sem rótulo nem emenda, completadas pela vizinha; "
        f"{sum(c.z is None for c in mestras)} sem cota) · intermediárias {len(inters)} "
        f"({sum(c.z is None for c in inters)} sem cota) · grade {grade.nx}×{grade.ny} · cota {min(zs):.1f}–{max(zs):.1f} m"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
