"""Terreno perto com o furo da placa: a grade de 10 m de sempre (dois triângulos por célula, a mesma
superfície em que vegetação e prédios se assentam), menos a placa. Só a célula que cruza o contorno
é recortada; a borda do furo coincide com o contorno da placa por construção."""

from shapely.geometry import box
from shapely.geometry.base import BaseGeometry
from shapely.prepared import prep

from scripts.entorno.tiles import Ext, da_janela

from .malha import triangular
from .placa import aneis_orientados, partes
from .relevo import Grade


def malha_perto(grade: Grade, placa: BaseGeometry, janela: Ext) -> tuple[list[list[float]], list[list[int]]]:
    pp = prep(placa)
    indice: dict[tuple[float, float], int] = {}
    vs: list[list[float]] = []
    fs: list[list[int]] = []

    def no(x: float, y: float) -> int:
        k = (round(x, 3), round(y, 3))
        if k not in indice:
            indice[k] = len(vs)
            vs.append([k[0], k[1], round(grade.cota_malha(x, y), 2)])
        return indice[k]

    for j in range(grade.ny - 1):
        for i in range(grade.nx - 1):
            xa, ya = grade.x0 + i * grade.passo, grade.y0 + j * grade.passo
            xb, yb = xa + grade.passo, ya + grade.passo
            if not da_janela(janela, (xa + xb) / 2, (ya + yb) / 2):
                continue
            celula = box(xa, ya, xb, yb)
            if pp.contains(celula):
                continue
            if not pp.intersects(celula):
                a, b, c, d = no(xa, ya), no(xb, ya), no(xb, yb), no(xa, yb)
                fs += [[a, b, c], [a, c, d]]  # a diagonal de Grade.cota_malha
                continue
            for p in partes(celula.difference(placa)):
                ext, furos = aneis_orientados(p)
                v, t = triangular(ext, furos)
                ids = [no(x, y) for x, y in v]
                for a, b, c in t:
                    (x1, y1), (x2, y2), (x3, y3) = v[a], v[b], v[c]
                    ccw = (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1) > 0
                    fs.append([ids[a], ids[b], ids[c]] if ccw else [ids[a], ids[c], ids[b]])
    return vs, fs
