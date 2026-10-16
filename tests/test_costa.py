import numpy as np
import pytest
from shapely.geometry import LineString, Point

from scripts.loteamento.costa import costa_suave, mar_da_costa
from scripts.loteamento.relevo import Grade
from scripts.loteamento.terreno import amostrar_grade


def test_mar_fica_a_direita_da_linha_de_costa_do_osm():
    # Convenção do OSM: terra à esquerda do sentido da linha. Indo para leste, o mar é o sul.
    mar = mar_da_costa([LineString([(-1000, 0), (0, 10), (1000, 0)])], (0.0, 0.0), 3000.0)
    assert mar.contains(Point(0, -500)) and not mar.contains(Point(0, 500))
    assert mar.contains(Point(2500, -100))  # a linha é prolongada até o fim do disco


def _grade(z=8.0, n=21, passo=30.0):
    return Grade(-300.0, -300.0, passo, n, n, [[z] * n for _ in range(n)])


def test_costa_suave_poe_a_cota_do_mar_sobre_a_linha_de_costa():
    # Costa oblíqua à grade: o contorno da água tem que seguir a linha, não a escada das células.
    costa = LineString([(-400, -100), (400, 60)])
    mar = mar_da_costa([costa], (0.0, 0.0), 1000.0)
    g = costa_suave(_grade(), mar, nivel=0.0, praia=0.05, fundo=0.1, rebaixo=5.0)
    t = np.linspace(0.15, 0.85, 40)  # dentro da grade (±300 m)
    xs, ys = -400 + 800 * t, -100 + 160 * t
    assert np.abs(amostrar_grade(g, xs, ys)).max() < 0.05
    assert g.cota(0, -250) == pytest.approx(-5.0)        # fundo longe da costa
    assert g.cota(0, 280) == pytest.approx(8.0)          # terra longe: cota original
    z = np.array(g.z)
    assert max(abs(np.diff(z, axis=0)).max(), abs(np.diff(z, axis=1)).max()) < 3.5  # rampa, sem degrau


def test_costa_suave_mantem_rio_ligado_ao_mar_longe_da_costa():
    costa = LineString([(-400, -100), (400, -100)])
    mar = mar_da_costa([costa], (0.0, 0.0), 1000.0)
    g0 = _grade()
    z = np.array(g0.z)
    z[15:, 10] = -5.0  # rio: água que o separar_mar já pôs no nível do mar, terra adentro
    g = costa_suave(Grade(g0.x0, g0.y0, g0.passo, g0.nx, g0.ny, z.tolist()), mar, 0.0, 0.05, 0.1, 5.0)
    assert g.cota(0, 240) == pytest.approx(-5.0)
