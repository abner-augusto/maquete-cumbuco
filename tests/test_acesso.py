import math

import numpy as np
import pytest
from shapely.geometry import LineString, Point, Polygon, box

from scripts.loteamento.acesso import AcessoCfg, Acesso, eixo_da_faixa, perfil_vertical, pecas_acesso, perfil_acesso
from scripts.loteamento.placa import partes

CFG = AcessoCfg(camada_via="VIA", recuo_inicio=6.0, secao=[2.0, 7.0, 3.0, 7.0, 2.0], raio_boca=15.0, patamar=20.0,
                patamar_inclinacao=0.02, curva_vertical=20.0, rampa_max=0.18, passo=2.0, folga_ce=5.0,
                ilha_base=10.0, ilha_comprimento=15.0, ilha_recuo=3.0)


def test_perfil_vertical_continuo_e_com_as_rampas_certas():
    z = perfil_vertical([(0.0, 20.0), (40.0, 20.0), (140.0, 5.0), (160.0, 4.6)], 20.0)
    assert z(-10) == z(0) == pytest.approx(20.0) and z(29.99) == pytest.approx(20.0)  # plano até a curva
    assert (z(80) - z(70)) / 10 == pytest.approx(-0.15)  # rampa no meio
    assert (z(158) - z(152)) / 6 == pytest.approx(-0.02)  # patamar
    s = np.linspace(-5, 170, 3501)
    dz = np.diff([z(x) for x in s]) / np.diff(s)
    assert np.abs(np.diff(dz)).max() < 0.01  # sem quebra: a inclinação muda aos poucos (curva vertical)
    assert z(40) == pytest.approx(20.0 - 0.15 * 10 / 2 / 2, abs=1e-6)  # no PVI, a parábola passa L·Δg/8 abaixo


def test_perfil_acesso_poe_o_patamar_e_confere_a_rampa():
    pvis, rampa = perfil_acesso(48.0, 177.0, 21.0, 4.2, CFG)
    assert pvis[0] == (48.0, 21.0) and pvis[-1] == (177.0, 4.2)
    assert pvis[-2] == (157.0, pytest.approx(4.6))  # patamar de 20 m a 2%
    assert rampa == pytest.approx((4.6 - 21.0) / (157.0 - 58.0))
    with pytest.raises(SystemExit, match="rampa"):
        perfil_acesso(48.0, 90.0, 21.0, 4.2, CFG)


def test_eixo_da_faixa_sai_da_rotatoria():
    faixa = Polygon([(20, -6), (150, -6), (150, 6), (20, 6)])
    c0, d, s_ini, s_fim = eixo_da_faixa(faixa, [(0.0, 0.0, 17.5), (500.0, 500.0, 9.0)])
    assert c0 == pytest.approx((0.0, 0.0)) and d == pytest.approx((1.0, 0.0))
    assert (s_ini, s_fim) == (pytest.approx(20.0), pytest.approx(150.0))


def test_eixo_recua_o_comeco_para_dentro_do_braco():
    # a faixa do DWG começa num corte inclinado e o braço da rotatória também: o acesso começa reto,
    # `recuo` m antes do ponto mais recuado da faixa, onde o braço já é reto (sem triângulo vazio no canto)
    faixa = Polygon([(26, -6), (150, -6), (150, 6), (20, 6)])
    _, _, s_ini, s_fim = eixo_da_faixa(faixa, [(0.0, 0.0, 17.5)], recuo=6.0)
    assert (s_ini, s_fim) == (pytest.approx(14.0), pytest.approx(150.0))


A =Acesso(c0=(0.0, 0.0), d=(0.0, 1.0), s_ini=10.0, s_fim=100.0, pvis=[(10.0, 21.0), (100.0, 4.0)])
CE = box(-300, 100, 300, 109)


def _peca_em(pecas, x, y):
    return [k for k, g in pecas.items() if g.buffer(1e-6).contains(Point(x, y))]


def test_secao_da_avenida():
    p = pecas_acesso(A, CE, CFG)
    # eixo em y (s), x = −t: a seção corta x de 10,5 a −10,5
    corte = [(x, _peca_em(p, x, 50)) for x in (9.5, 5.0, 0.0, -5.0, -9.5, 11.0)]
    assert corte == [(9.5, ["AcessoCalcadas"]), (5.0, ["AcessoPista"]), (0.0, ["AcessoCanteiro"]),
                     (-5.0, ["AcessoPista"]), (-9.5, ["AcessoCalcadas"]), (11.0, [])]


def test_boca_abre_em_curva_ate_a_ce():
    p = pecas_acesso(A, CE, CFG)
    tudo = p["AcessoPista"].union(p["AcessoCalcadas"]).union(p["AcessoCanteiro"])
    assert tudo.contains(Point(13, 99.5)) and tudo.contains(Point(-13, 99.5))  # abre perto da CE
    assert not tudo.contains(Point(13, 80)) and not tudo.contains(Point(-13, 80))  # antes da curva, não
    assert not tudo.intersects(CE.buffer(-0.01))  # não entra na CE
    assert _peca_em(p, 20.0, 99.9) == ["AcessoCalcadas"]  # a calçada acompanha a curva


def test_canteiro_termina_em_ilha_triangular():
    p = pecas_acesso(A, CE, CFG)
    assert _peca_em(p, 4.0, 96.5) == ["AcessoCanteiro"]  # base da ilha (10 m) a 3 m da CE
    assert _peca_em(p, 4.0, 80.0) == ["AcessoPista"]  # antes da ilha, o canteiro tem 3 m
    assert _peca_em(p, 0.0, 98.5) == ["AcessoPista"]  # entre a ilha e a CE, pista


def test_montar_acesso_desce_pelo_perfil_com_arestas_curtas():
    from scripts.loteamento.acesso import montar_acesso, perfil_vertical

    a = Acesso(c0=(0.0, 0.0), d=(0.0, 1.0), s_ini=10.0, s_fim=100.0,
               pvis=[(10.0, 21.0), (20.0, 21.0), (80.0, 4.4), (100.0, 4.0)])
    objs = {o["nome"]: o for o in montar_acesso(a, pecas_acesso(a, CE, CFG), {}, 21.0, -1.0, CFG)}
    assert set(objs) == {"AcessoPista", "AcessoCalcadas", "AcessoCanteiro"}
    zs = perfil_vertical(a.pvis, CFG.curva_vertical)
    pista = objs["AcessoPista"]
    topo = [f for f in pista["faces"] if len({round(pista["vertices"][i][2], 3) for i in f}) and
            all(abs(pista["vertices"][i][2] - zs(min(max(pista["vertices"][i][1], 10), 100))) < 1e-3 for i in f)]
    assert len(topo) > 100  # o topo da pista está no perfil
    for f in topo:  # a cota só varia ao longo do eixo (y aqui): basta o triângulo ser curto nessa direção
        ys = [pista["vertices"][i][1] for i in f]
        assert max(ys) - min(ys) <= CFG.passo * 1.01
    assert len(pista["faces"]) < 3000  # sem explosão de triângulos
    calc = objs["AcessoCalcadas"]["vertices"]
    meio_fio = [v for v in calc if 49 < v[1] < 51 and abs(v[2] - (zs(v[1]) + 0.25)) < 0.01]
    assert len(meio_fio) >= 4  # o topo da calçada fica 0,25 acima do perfil
    assert min(v[2] for v in calc) == pytest.approx(4.0 - 1.0, abs=0.01)  # a saia desce 1 m abaixo do perfil


def test_faixa_e_o_anel_comprido_da_camada():
    from scripts.loteamento.acesso import faixa_comprida

    rotatoria = [(-30.0, -30.0), (30.0, -30.0), (30.0, 30.0), (-30.0, 30.0)]
    faixa = [(30.0, -6.0), (160.0, -6.0), (160.0, 6.0), (30.0, 6.0)]
    assert faixa_comprida([rotatoria, faixa]).equals(Polygon(faixa))
    with pytest.raises(SystemExit, match="faixa"):
        faixa_comprida([rotatoria])


def test_plato_perde_os_aneis_da_faixa():
    from scripts.loteamento.acesso import sem_faixa

    lote = [(-50.0, -50.0), (-20.0, -50.0), (-20.0, 50.0), (-50.0, 50.0)]
    pista = [(-2.0, 20.0), (2.0, 20.0), (2.0, 90.0), (-2.0, 90.0)]  # dentro do corredor
    calcada = [(4.0, 10.0), (6.0, 10.0), (6.0, 100.0), (4.0, 100.0)]
    gleba = [(-50.0, -50.0), (0.0, -50.0), (0.0, 0.0), (6.0, 0.0), (6.0, 110.0), (-6.0, 110.0), (-6.0, 10.0),
             (-50.0, 10.0)]  # a poligonal com a língua do acesso até a CE
    fica = sem_faixa([lote, pista, calcada, gleba], A, CFG)
    assert len(fica) == 2 and Polygon(fica[0]).equals(Polygon(lote))
    sobra = Polygon(fica[1])
    assert not sobra.contains(Point(0, 50)) and 3000 < sobra.area < 3100  # a língua some no corredor


def test_plato_vai_ate_o_comeco_do_acesso():
    from scripts.loteamento.acesso import sem_faixa

    braco = [(-10.5, 0.0), (10.5, 0.0), (10.5, 30.0), (-10.5, 30.0)]  # o braço da rotatória segue pela faixa
    fica = Polygon(sem_faixa([braco], A, CFG)[0])
    assert fica.contains(Point(0, 9.8)) and fica.contains(Point(-10.0, 9.8))  # sem fresta antes de s_ini
    assert fica.area == pytest.approx(21.0 * 10.0, abs=0.5)


def test_ce_e_a_rodovia_que_o_eixo_cruza_primeiro():
    from scripts.loteamento.acesso import faixa_ce

    vias = [{"classe": "secondary", "nome": "CE", "pontos": [[-300, 104.5], [0, 104.5]]},
            {"classe": "secondary", "nome": "CE", "pontos": [[0, 104.5], [300, 104.5]]},  # mesma rodovia
            {"classe": "secondary", "nome": "Outra", "pontos": [[-300, 200], [300, 200]]},
            {"classe": "residential", "nome": "Rua", "pontos": [[-300, 50], [300, 50]]}]
    faixa, s = faixa_ce(vias, (0.0, 0.0), (0.0, 1.0), 600.0, {"secondary": 9.0})
    assert s == pytest.approx(100.0) and faixa.contains(Point(250, 104.5)) and not faixa.contains(Point(0, 200))
    livre, _ = faixa_ce(vias, (0.0, 0.0), (0.0, 1.0), 600.0, {"secondary": 9.0}, folga=5.0)
    assert livre.contains(Point(0, 96)) and not livre.contains(Point(0, 94))


def _ce_obliqua(graus=38.0):
    # borda da CE passando por (0, 100), girada `graus` em relação à perpendicular do eixo
    from shapely import affinity

    return affinity.rotate(box(-400, 100, 400, 109), graus, origin=(0, 100))


def test_boca_obliqua_abre_igual_dos_dois_lados():
    from shapely.geometry import LineString as L
    from shapely import affinity

    ce = _ce_obliqua()
    p = pecas_acesso(A, ce, CFG)
    tudo = p["AcessoPista"].union(p["AcessoCalcadas"])
    borda = affinity.rotate(L([(-400, 100), (400, 100)]), 38.0, origin=(0, 100))
    contato = tudo.intersection(borda.buffer(0.05))
    lados = [contato.intersection(box(0, -1e3, 1e3, 1e3)), contato.intersection(box(-1e3, -1e3, 0, 1e3))]
    largos = [g.length if g.length else math.dist(*[c[:2] for c in g.envelope.exterior.coords[:2]]) for g in lados]
    ext = [max(abs(x) for x, _ in g.envelope.exterior.coords) for g in lados]
    assert ext[0] == pytest.approx(ext[1], rel=0.15)  # a boca abre o mesmo tanto ao longo da CE nos dois lados
    assert min(ext) > 10.5 / math.cos(math.radians(38)) + 10  # e abre de verdade além da avenida


def test_calcada_acompanha_a_curva_e_termina_afinando_na_ce():
    ce = _ce_obliqua()
    p = pecas_acesso(A, ce, CFG)
    calc = p["AcessoCalcadas"]
    assert not calc.intersects(ce.buffer(-0.01))
    toque = calc.intersection(ce.buffer(0.05))
    assert toque.area < 2.0  # só a ponta afinada encosta na CE, sem dente correndo ao longo dela
    assert len(partes(calc)) == 2  # uma calçada de cada lado, sem pedaço solto
