import json
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


# Topos e fundos de duna são curvas fechadas aninhadas: a cota vem do anel que as contém,
# um passo além, no sentido em que o relevo vinha (revisão final: 115 anéis repetiam a cota do pai).


def _anel(r, z=None, cx=0.0, cy=0.0, n=36):
    pts = [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return Curva(pts + pts[:1], z, fechada=True)


def test_aneis_dentro_de_morro_sobem():
    from scripts.loteamento.relevo import cotar_aneis

    m25, m30 = _anel(200, 25.0), _anel(150, 30.0)
    i1, i2 = _anel(100), _anel(60)
    cotar_aneis([m25, m30], [i1, i2])
    assert (i1.z, i2.z) == (31.0, 32.0)


def test_aneis_dentro_de_cova_descem():
    from scripts.loteamento.relevo import cotar_aneis

    m30, m25 = _anel(200, 30.0), _anel(150, 25.0)
    i1, i2 = _anel(100), _anel(60)
    cotar_aneis([m30, m25], [i1, i2])
    assert (i1.z, i2.z) == (24.0, 23.0)


def test_mestra_fechada_sem_rotulo_no_topo_da_cadeia():
    from scripts.loteamento.relevo import cotar_aneis

    m15, m20 = _anel(300, 15.0), _anel(250, 20.0)
    inters = [_anel(r) for r in (200, 150, 100, 60)]
    topo = _anel(30)
    cotar_aneis([m15, m20, topo], inters)
    assert [c.z for c in inters] + [topo.z] == [21.0, 22.0, 23.0, 24.0, 25.0]


def test_anel_solto_segue_o_sentido_das_curvas_de_fora():
    from scripts.loteamento.relevo import cotar_aneis

    m20, i21 = Curva(_horizontal(100, -200, 300).pontos, 20.0), Curva(_horizontal(150, -200, 300).pontos, 21.0)
    duna = _anel(20, cx=50, cy=200)
    cotar_aneis([m20], [i21, duna])
    assert duna.z == 22.0


def test_anel_fechado_nao_herda_cota_pela_ponta():
    a = _horizontal(0, 0, 100)
    ilha = _anel(10, cx=112, cy=0)  # primeiro vértice a 2 m da ponta da mestra cotada
    cotar_mestras([a, ilha], [((10, 0.5), 30.0)])
    assert ilha.z is None


def test_curva_fechada_do_dxf_volta_ao_inicio_e_densifica_o_fecho():
    import ezdxf

    from scripts.loteamento.relevo import curva_do_dxf

    e = ezdxf.new().modelspace().add_polyline2d([(1000, 2000), (1100, 2000), (1100, 2100)], close=True)
    c = curva_do_dxf(e, 1000.0, 2000.0)
    assert c.fechada and c.pontos[0] == c.pontos[-1] == (0.0, 0.0)
    assert max(math.dist(a, b) for a, b in zip(c.pontos, c.pontos[1:])) < 20.0  # o fecho de 141 m foi dividido


def test_anel_intermediario_nao_pula_a_mestra():
    from scripts.loteamento.relevo import cotar_aneis

    m25, i29 = _anel(200, 25.0), _anel(150, 29.0)  # dentro da 29 só cabe 28: a 30 seria mestra
    i = _anel(100)
    cotar_aneis([m25], [i29, i])
    assert i.z == 28.0


def test_intermediaria_longa_cota_onde_esta_entre_as_mestras():
    # revisão final: curva aberta de km, cotada pelo meio, longe das mestras carregadas
    m30, m35 = Curva(_horizontal(0).pontos, 30.0), Curva(_horizontal(50).pontos, 35.0)
    longa = Curva([(float(x), 10.0) for x in range(0, 5001, 10)])
    cotar_intermediarias([longa], [m30, m35])
    assert longa.z == 31.0


def test_anel_solto_no_vao_entre_mestras_fica_entre_elas():
    from scripts.loteamento.relevo import cotar_aneis

    m20, m25 = Curva(_horizontal(100, -200, 300).pontos, 20.0), Curva(_horizontal(200, -200, 300).pontos, 25.0)
    duna, dentro = _anel(20, cx=50, cy=135), _anel(10, cx=50, cy=135)  # mais perto da 20
    cotar_aneis([m20, m25], [duna, dentro])
    assert (duna.z, dentro.z) == (21.0, 22.0)


def _arco(r, z, cx=0.0, cy=0.0):
    """Mestra fechada cortada no rótulo: arco aberto com um vão de uns 4 m."""
    return Curva([(cx + r * math.cos(t / 20 * 6.0), cy + r * math.sin(t / 20 * 6.0)) for t in range(21)], z)


def test_curva_cotada_dentro_do_anel_manda_o_sentido():
    from scripts.loteamento.relevo import cotar_aneis

    m25 = _anel(300, 25.0)
    inters = [_anel(250), _anel(200)]
    cotar_aneis([m25, _arco(50, 20.0)], inters)  # fundo de 20 lá dentro: é cova
    assert [c.z for c in inters] == [24.0, 23.0]


def test_topo_cotado_la_dentro_puxa_a_cadeia_ate_ele():
    from scripts.loteamento.relevo import cotar_aneis

    m25 = _anel(300, 25.0)
    inters = [_anel(r) for r in (250, 200, 150, 120, 100)]
    cotar_aneis([m25, _arco(30, 35.0)], inters)  # a 30 não foi desenhada: a cadeia segue subindo até o topo
    assert [c.z for c in inters] == [26.0, 27.0, 28.0, 29.0, 31.0]


def test_grade_sem_preencher_deixa_nan_fora_das_curvas_e_vai_ao_json():
    curvas = [Curva(_horizontal(y).pontos, 30.0 + y / 10) for y in range(0, 60, 10)]
    g = gerar_grade(curvas, (-50.0, -50.0, 150.0, 120.0), 5.0, preencher=False)
    assert math.isnan(g.z[0][0]) and not math.isnan(g.z[15][20])
    volta = Grade.de_json(json.loads(json.dumps(g.para_json())))  # JSON padrão: null, não NaN
    assert "NaN" not in json.dumps(g.para_json()) and math.isnan(volta.z[0][0])
