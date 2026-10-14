import math

import numpy as np
import pytest

from scripts.loteamento.relevo import Grade
from scripts.loteamento.terreno import (TerrenoCfg, ajustar_datum, amostrar_grade, compor_perto, cota_plato,
                                        encaixar, reamostrar, separar_mar)

CFG = TerrenoCfg(poligonal=["POL"], talude=20.0, sigma=25.0, alcance=100.0, transicao=50.0, raio=4000.0,
                 mar_rebaixo=1.0, passo_perto=10.0)
QUADRADO = [(-50.0, -50.0), (50.0, -50.0), (50.0, 50.0), (-50.0, 50.0)]


def _grade(f, x0=-300.0, y0=-300.0, passo=10.0, n=61):
    return Grade(x0, y0, passo, n, n, [[f(x0 + i * passo, y0 + j * passo) for i in range(n)] for j in range(n)])


def test_encaixar_vai_para_fora_em_multiplos():
    assert encaixar((-41.0, 13.0, 59.0, 60.0), 30.0) == (-60.0, 0.0, 60.0, 60.0)


def test_amostrar_grade_bilinear_e_presa_na_borda():
    g = _grade(lambda x, y: 2 * x + y)
    assert amostrar_grade(g, np.array([12.5, -1000.0]), np.array([3.0, 0.0])) == pytest.approx([28.0, -600.0])


def test_cota_plato_mediana_dos_lotes_a_meio_metro():
    g = _grade(lambda x, y: 20.0 + x / 100)
    lotes = [{"poligono": [[x, 0], [x + 10, 0], [x + 10, 10], [x, 10]]} for x in (0, 30, 60)]
    assert cota_plato(g, lotes) == 20.5  # centróides em 5, 35, 65 → 20.05, 20.35, 20.65 → 20.35 → 20.5


def test_ajustar_datum_devolve_o_deslocamento():
    lev = _grade(lambda x, y: 10.0 + x / 50)
    dem = _grade(lambda x, y: 7.0 + x / 50, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    onde = np.ones((lev.ny, lev.nx), dtype=bool)
    assert ajustar_datum(lev, dem, onde) == pytest.approx(3.0, abs=1e-6)


def test_separar_mar_so_agua_ligada_a_borda():
    z = [[5.0] * 9 for _ in range(9)]
    for j in range(9):
        z[j][0] = z[j][1] = -0.5  # mar a oeste, encostado na borda
    z[4][6] = -0.3  # baixio no continente
    s = separar_mar(Grade(0.0, 0.0, 30.0, 9, 9, z), nivel=0.0, rebaixo=1.0)
    assert s.z[4][0] == pytest.approx(-1.0) and s.z[4][1] == pytest.approx(-1.0)
    assert s.z[4][6] > 0.0 and s.z[4][4] == 5.0


def test_plato_plano_dentro_e_talude_continuo():
    lev = _grade(lambda x, y: 25.0 + 5 * math.sin(x / 40) * math.cos(y / 30))  # dunas
    dem = _grade(lambda x, y: 18.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    g = compor_perto(lev, dem, [QUADRADO], 22.0, CFG)
    z = np.array(g.z)
    gx, gy = np.meshgrid(g.x0 + g.passo * np.arange(g.nx), g.y0 + g.passo * np.arange(g.ny))
    dentro = (abs(gx) < 50) & (abs(gy) < 50)  # nó sobre a borda: lado indefinido
    assert np.allclose(z[dentro], 22.0)
    assert max(abs(np.diff(z, axis=0)).max(), abs(np.diff(z, axis=1)).max()) < 5.0  # nada de degrau


def test_longe_da_poligonal_e_so_copernicus():
    lev = _grade(lambda x, y: 30.0)
    dem = _grade(lambda x, y: 10.0 + x / 100, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    g = compor_perto(lev, dem, [QUADRADO], 22.0, CFG)
    # (290, 0): a 240 m da poligonal > alcance + transição = 150 m
    assert g.z[30][59] == pytest.approx(10.0 + 290 / 100, abs=1e-6)


def test_borda_da_cobertura_do_levantamento_sem_degrau():
    lev = _grade(lambda x, y: 30.0 if y < 60 else float("nan"))  # levantamento acaba em y = 60
    dem = _grade(lambda x, y: 18.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    cfg = TerrenoCfg(**{**CFG.__dict__, "alcance": 1000.0})
    z = np.array(compor_perto(lev, dem, [QUADRADO], 22.0, cfg).z)
    coluna = z[:, 55]  # x = 250, longe do platô: só levantamento × Copernicus
    assert abs(np.diff(coluna)).max() < 6.0  # 12 m de diferença espalhados, não num degrau


def test_reamostrar_mantem_nan_fora_do_levantamento():
    lev = _grade(lambda x, y: 30.0 if x < 0 else float("nan"), passo=5.0, x0=-100.0, y0=-100.0, n=41)
    r = reamostrar(lev, (-200.0, -200.0, 200.0, 200.0), 10.0)
    assert r.nx == 41 and r.z[20][12] == pytest.approx(30.0) and math.isnan(r.z[20][35]) and math.isnan(r.z[0][0])
