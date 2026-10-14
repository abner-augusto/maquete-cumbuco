import math

import pytest

from scripts.loteamento.relevo import Curva, Grade, cotar_intermediarias, cotar_mestras, gerar_grade


def _horizontal(y, x0=0.0, x1=100.0, n=11):
    return Curva([(x0 + (x1 - x0) * i / (n - 1), y) for i in range(n)])


def test_rotulo_cota_a_mestra_mais_proxima():
    m30, m35 = _horizontal(0), _horizontal(50)
    sem = cotar_mestras([m30, m35], [((40, 1.0), 30.0), ((60, 49.0), 35.0), ((70, 48.5), 35.0)])
    assert (m30.z, m35.z, sem) == (30.0, 35.0, 0)


def test_mestra_sem_rotulo_fica_sem_cota():
    m = _horizontal(0)
    assert cotar_mestras([m], [((50, 200.0), 30.0)]) == 1 and m.z is None


def test_intermediarias_entre_30_e_35():
    m30, m35 = Curva(_horizontal(0).pontos, 30.0), Curva(_horizontal(50).pontos, 35.0)
    inters = [_horizontal(y) for y in (10, 20, 30, 40)]
    cotar_intermediarias(inters, [m30, m35])
    assert [c.z for c in inters] == [31.0, 32.0, 33.0, 34.0]


def test_intermediaria_colada_na_mestra_nao_vira_a_mestra():
    m30, m35 = Curva(_horizontal(0).pontos, 30.0), Curva(_horizontal(50).pontos, 35.0)
    c = _horizontal(1)  # quase em cima da de 30
    cotar_intermediarias([c], [m30, m35])
    assert c.z == 31.0


def test_grade_reproduz_um_plano_e_nao_tem_nan_fora_das_curvas():
    curvas = [Curva(_horizontal(y).pontos, 30.0 + y / 10) for y in range(0, 60, 10)]
    g = gerar_grade(curvas, (-50.0, -50.0, 150.0, 120.0), 5.0)
    assert g.cota(50, 25) == pytest.approx(32.5, abs=0.01)
    assert all(not math.isnan(v) for linha in g.z for v in linha)
    assert g.cota(-1000, -1000) == pytest.approx(g.z[0][0])  # borda presa


def test_grade_ida_e_volta_json():
    g = Grade(0.0, 0.0, 5.0, 2, 2, [[1.0, 2.0], [3.0, 4.0]])
    assert Grade.de_json(g.para_json()) == g
    assert g.cota(2.5, 2.5) == pytest.approx(2.5)


# Curvas reais: as mestras vêm em pedaços cortados no rótulo, e há topos fechados sem rótulo.


def test_rotulo_no_vao_entre_dois_pedacos_cota_os_dois():
    a, b = _horizontal(0, 0, 48), _horizontal(0, 52, 100)
    assert cotar_mestras([a, b], [((50, 0.5), 30.0)]) == 0
    assert a.z == b.z == 30.0


def test_pedaco_sem_rotulo_herda_a_cota_pela_ponta():
    a, b = _horizontal(0, 0, 100), _horizontal(0, 105, 300)
    assert cotar_mestras([a, b], [((10, 0.5), 30.0)]) == 0
    assert b.z == 30.0


def test_topo_fechado_sem_rotulo_pega_o_multiplo_de_5_da_curva_vizinha():
    from scripts.loteamento.relevo import completar_mestras

    topo = Curva([(40, 40), (60, 40), (60, 60), (40, 60), (40, 40)])
    vizinha = Curva(_horizontal(30).pontos, 34.0)  # intermediária logo abaixo do topo
    completar_mestras([topo], [vizinha], 5.0)
    assert topo.z == 35.0


# O loteamento é terraplenado: dentro da poligonal o relevo é suavizado (as dunas do
# levantamento furavam vias e lotes); fora dela, fica o natural.


def test_suavizar_dentro_tira_a_duna_so_dentro_da_poligonal():
    from scripts.loteamento.relevo import suavizar_dentro

    z = [[10.0] * 41 for _ in range(41)]
    z[20][20] = 30.0  # duna dentro
    z[2][2] = 30.0  # duna fora
    g = Grade(0.0, 0.0, 5.0, 41, 41, z)
    poligonal = [(60.0, 60.0), (140.0, 60.0), (140.0, 140.0), (60.0, 140.0)]
    s = suavizar_dentro(g, [poligonal], sigma=10.0, transicao=10.0)
    assert s.z[20][20] < 15.0
    assert s.z[2][2] == 30.0
