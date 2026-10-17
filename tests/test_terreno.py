import math

import numpy as np
import pytest

from scripts.loteamento.relevo import Grade
from scripts.loteamento.terreno import (TerrenoCfg, ajustar_datum, amostrar_grade, compor_perto, cota_plato,
                                        Relevo, costurar, disco_mar, encaixar, malha_entorno, reamostrar, separar_mar)

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


def test_entorno_tem_furo_no_perto_e_fica_no_raio():
    dem = _grade(lambda x, y: 10.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    v, f = malha_entorno(dem, buraco=(-90.0, -90.0, 90.0, 90.0), centro=(0.0, 0.0), raio=500.0)
    centros = [np.mean([v[i][:2] for i in t], axis=0) for t in f]
    assert not any(abs(cx) < 90 and abs(cy) < 90 for cx, cy in centros)
    assert all(math.hypot(x, y) <= 500.0 + 0.01 for x, y, _ in v)  # vértices arredondados ao centímetro
    assert len(f) > 0 and all(len(t) == 3 for t in f)


def test_borda_do_entorno_e_redonda_nao_em_escada():
    # a borda do mundo a 4 km aparecia em degraus de 30 m: as células cortadas pelo círculo entram,
    # com os cantos de fora trazidos ao círculo pelo raio (cota amostrada na superfície da malha)
    dem = _grade(lambda x, y: 10.0 + 0.01 * x, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    v, f = malha_entorno(dem, buraco=(-90.0, -90.0, 90.0, 90.0), centro=(0.0, 0.0), raio=500.0)
    dist = [math.hypot(x, y) for x, y, _ in v]
    assert max(dist) <= 500.0 + 0.01  # vértices arredondados ao centímetro
    # Toda aresta de contorno (usada por uma face só) que não é do furo está no círculo.
    arestas: dict[tuple[int, int], int] = {}
    for t in f:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            arestas[(min(a, b), max(a, b))] = arestas.get((min(a, b), max(a, b)), 0) + 1
    contorno = [e for e, n in arestas.items() if n == 1 and not all(abs(v[k][0]) <= 90 and abs(v[k][1]) <= 90 for k in e)]
    assert len(contorno) >= 60
    assert all(abs(dist[k] - 500.0) < 0.01 for e in contorno for k in e)
    for x, y, z in v:  # a cota do canto trazido vem da superfície
        assert z == pytest.approx(10.0 + 0.01 * x, abs=0.02)


def test_borda_do_perto_e_linear_entre_nos_do_entorno():
    f = lambda x, y: 10.0 + 0.001 * x * x + 0.02 * y  # noqa: E731 — curvo: só os nós de 30 m coincidem
    dem = _grade(f, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    lev = reamostrar(_grade(lambda x, y: 30.0), encaixar((-240.0, -240.0, 240.0, 240.0), 30.0), 10.0)
    g = compor_perto(lev, dem, [QUADRADO], 22.0, CFG)  # borda a 190 m > alcance + transição
    for k in range(g.nx):  # linha de baixo: a aresta do entorno é reta entre nós de 30 m
        x = g.x0 + k * g.passo
        a = math.floor(x / 30.0) * 30.0
        linear = f(a, g.y0) + (f(a + 30.0, g.y0) - f(a, g.y0)) * (x - a) / 30.0
        assert g.z[0][k] == pytest.approx(linear, abs=0.01)


def test_disco_do_mar_no_nivel():
    v, f = disco_mar((10.0, 20.0), 4000.0, 1.5, n=32)
    assert all(z == 1.5 for _, _, z in v) and len(f) == 32


def test_plato_tem_folga_antes_do_talude():
    # vias e verdes desenhados na borda: o talude só começa depois da folga
    lev = _grade(lambda x, y: 40.0)
    dem = _grade(lambda x, y: 40.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    cfg = TerrenoCfg(**{**CFG.__dict__, "plato_folga": 10.0})
    g = compor_perto(lev, dem, [QUADRADO], 22.0, cfg)
    assert g.z[30][36] == pytest.approx(22.0)  # (60, 0): 10 m fora da poligonal, ainda platô
    assert g.z[30][38] > 22.0  # (80, 0): já no talude


def test_mar_nao_passa_da_borda_da_terra():
    # revisão final: o disco no raio cheio aparecia como serrilhado azul além da escada das células;
    # com a borda da terra no círculo, o disco do mar vai ao raio cheio e a terra o cobre até lá
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union

    dem = _grade(lambda x, y: 10.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    v, f = malha_entorno(dem, buraco=(-90.0, -90.0, 90.0, 90.0), centro=(0.0, 0.0), raio=500.0)
    terra = unary_union([Polygon([v[k][:2] for k in t]) for t in f])
    r = 500.0 - 0.5  # meio metro para dentro do contorno do mar
    for k in range(360):
        assert terra.contains(Point(r * math.cos(math.radians(k)), r * math.sin(math.radians(k))))  # terra (ou fundo) embaixo


def test_relevo_usa_o_perto_dentro_e_o_longe_fora():
    perto = Grade(0.0, 0.0, 10.0, 11, 11, [[50.0] * 11 for _ in range(11)])
    longe = _grade(lambda x, y: 7.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    r = Relevo(perto, longe)
    assert r.cota(55.0, 55.0) == 50.0 and r.cota(100.0, 100.0) == 50.0  # borda é do perto
    assert r.cota(130.0, 55.0) == 7.0


def test_relevo_segue_os_triangulos_da_malha_nao_o_bilinear():
    # revisão final: faixas afundavam e árvores flutuavam — o bilinear difere dos 2 triângulos da célula
    perto = Grade(0.0, 0.0, 10.0, 2, 2, [[0.0, 0.0], [0.0, 8.0]])  # z[j][i]: só o canto (10, 10) alto
    longe = _grade(lambda x, y: 0.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    r = Relevo(perto, longe)
    # malha: [a, a+1, a+nx+1] e [a, a+nx+1, a+nx] — diagonal de (0,0) a (10,10)
    assert r.cota(7.5, 2.5) == pytest.approx(2.0)  # triângulo de baixo: 8 · ty
    assert r.cota(2.5, 7.5) == pytest.approx(2.0)  # triângulo de cima: 8 · tx
    assert r.cota(5.0, 5.0) == pytest.approx(4.0)  # na diagonal (o bilinear daria 2,0)


def test_entorno_em_janelas_reparte_as_celulas_sem_repetir():
    from scripts.entorno.tiles import janelas

    dem = Grade(0.0, 0.0, 30.0, 11, 11, [[1.0] * 11 for _ in range(11)])
    buraco, centro, raio = (120.0, 120.0, 180.0, 180.0), (150.0, 150.0), 1e9
    _, inteiro = malha_entorno(dem, buraco, centro, raio)
    total = 0
    for jan in janelas((0.0, 0.0, 300.0, 300.0), 30.0).values():
        _, f = malha_entorno(dem, buraco, centro, raio, jan)
        total += len(f)
    assert total == len(inteiro)


def test_faixa_livre_fica_no_chao_natural_mesmo_perto_do_plato():
    # a CE passa a 10 m do platô: sem `livre`, o talude a levantava (a lombada na entrada)
    from shapely.geometry import box

    lev = _grade(lambda x, y: 10.0)
    dem = _grade(lambda x, y: 10.0, passo=30.0, x0=-600.0, y0=-600.0, n=41)
    sem = np.array(compor_perto(lev, dem, [QUADRADO], 22.0, CFG).z)
    com = np.array(compor_perto(lev, dem, [QUADRADO], 22.0, CFG, livre=box(55, -300, 75, 300)).z)
    j, i = 30, 36  # nó (60, 0)
    assert sem[j, i] > 10.5 and com[j, i] == pytest.approx(10.0)


def test_corredor_do_acesso_desce_com_o_perfil_e_emenda_no_entorno():
    from shapely.geometry import box

    from scripts.loteamento.acesso import Acesso, perfil_vertical
    from scripts.loteamento.terreno import aplicar_acesso
    from tests.test_acesso import CFG as ACFG

    a = Acesso(c0=(0.0, 0.0), d=(0.0, 1.0), s_ini=10.0, s_fim=100.0,
               pvis=[(10.0, 21.0), (20.0, 21.0), (80.0, 4.4), (100.0, 4.0)])
    g = aplicar_acesso(_grade(lambda x, y: 10.0), a, ACFG, box(-10.5, 10, 10.5, 100), talude=20.0)
    z = np.array(g.z)
    zs = perfil_vertical(a.pvis, ACFG.curva_vertical)
    assert z[35, 30] == pytest.approx(zs(50) - 0.5, abs=0.01)  # nó (0, 50): chão sob a pista
    assert z[35, 35] == pytest.approx(10.0)  # nó (50, 50): longe, o chão de antes
    assert abs(np.diff(z, axis=1)).max() < 6.0  # talude, sem paredão


def test_costurar_poe_a_borda_do_perto_na_reta_do_longe_e_deixa_o_miolo():
    longe = _grade(lambda x, y: 0.05 * x + (3.0 if x == 30.0 else 0.0), passo=30.0, x0=-120.0, y0=-120.0, n=9)
    perto = _grade(lambda x, y: 7.0, x0=0.0, y0=0.0, n=13)  # 10 m, de (0,0) a (120,120): nós do longe a cada 3
    z = np.array(costurar(perto, longe).z)
    for i in range(13):  # sul: a reta entre os nós do longe
        x = i * 10.0
        esperado = amostrar_grade(longe, np.array([x]), np.array([0.0]))[0]
        assert z[0][i] == pytest.approx(esperado, abs=0.01)
    assert z[6][6] == 7.0  # a 6 nós da borda, nada mudou
    assert abs(np.diff(z[:, 6])).max() < abs(7.0 - amostrar_grade(longe, np.array([60.0]), np.array([0.0]))[0]) + 0.01
