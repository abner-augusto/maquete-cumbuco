import numpy as np
import pytest
from shapely.geometry import Polygon, box

from scripts.loteamento.chao import malha_perto
from scripts.loteamento.relevo import Grade

GRADE = Grade(0.0, 0.0, 10.0, 11, 11, [[float(i + j) for i in range(11)] for j in range(11)])
PLACA = box(25, 25, 55, 55)
JANELA = (0.0, 0.0, 100.0, 100.0)


def _tris(v, f):
    return [[v[a], v[b], v[c]] for a, b, c in f]


def test_nenhum_triangulo_dentro_da_placa_e_area_certa():
    v, f = malha_perto(GRADE, PLACA, JANELA)
    tris = _tris(v, f)
    assert not any(PLACA.contains(Polygon([p[:2] for p in t]).centroid) for t in tris)
    area = sum(Polygon([p[:2] for p in t]).area for t in tris)
    assert area == pytest.approx(100 * 100 - 30 * 30, rel=1e-3)


def test_celula_longe_da_placa_e_a_da_grade():
    v, f = malha_perto(GRADE, PLACA, JANELA)
    tris = {tuple(sorted(tuple(p[:2]) for p in t)) for t in _tris(v, f)}
    assert tuple(sorted([(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])) in tris  # diagonal (i,j)-(i+1,j+1)
    assert tuple(sorted([(0.0, 0.0), (10.0, 10.0), (0.0, 10.0)])) in tris


def test_cotas_na_superficie_da_malha_e_normais_para_cima():
    v, f = malha_perto(GRADE, PLACA, JANELA)
    assert all(z == pytest.approx(GRADE.cota_malha(x, y), abs=0.01) for x, y, z in v)
    a = np.array(v, dtype=float)
    assert all(np.cross(a[j] - a[i], a[k] - a[i])[2] > 0 for i, j, k in f)


def test_janelas_repartem_o_terreno():
    total = sum(len(malha_perto(GRADE, PLACA, j)[1])
                for j in [(0, 0, 50, 50), (50, 0, 100, 50), (0, 50, 50, 100), (50, 50, 100, 100)])
    assert total == len(malha_perto(GRADE, PLACA, JANELA)[1])
