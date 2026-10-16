import math

import numpy as np
from shapely.geometry import LineString, Point, box

from scripts.entorno.orla import alfa_da_borda, faixa_da_orla, malha_orla, recorte_entre
from scripts.loteamento.relevo import Grade

# Costa reta em y = 1000, percorrida para oeste: no OSM a terra fica à esquerda, ao sul.
COSTA = [LineString([(20000, 1000), (-20000, 1000)])]
MAR = box(-50000, 1000, 50000, 50000)
A, B = (-10000.0, 1000.0), (10000.0, 1000.0)


def test_recorte_entre_guarda_so_o_trecho_entre_as_pontas_com_margem():
    r = recorte_entre(A, B, 1000.0)
    assert r.contains(Point(0, -3000))
    assert r.contains(Point(10900, 0))
    assert not r.contains(Point(11200, 0))
    assert not r.contains(Point(-11200, 0))


def test_faixa_e_terra_ate_a_profundidade_e_abraca_o_disco():
    f = faixa_da_orla(COSTA, MAR, (0.0, -2000.0), 4000.0, 3000.0, A, B, 1000.0, folga_disco=500.0)
    assert f.contains(Point(8000, 0))           # terra perto da costa
    assert not f.contains(Point(8000, 1500))    # mar
    assert not f.contains(Point(8000, -2500))   # além da profundidade, longe do disco
    assert f.contains(Point(0, -6300))          # o disco do entorno (4 km + folga) fica dentro
    assert not f.contains(Point(0, -6700))


def test_alfa_some_na_borda_de_terra_e_fica_inteiro_na_costa():
    f = faixa_da_orla(COSTA, MAR, (0.0, -20000.0), 1.0, 3000.0, A, B, 1000.0, folga_disco=0.0)
    a = alfa_da_borda(np.array([[0.0, 990.0], [0.0, -2000.0], [0.0, -1990.0 + 0.0]]), f, MAR, 1000.0)
    assert a[0] == 1.0          # na costa: a borda do mar não desbota
    assert a[1] == 0.0          # na borda de terra
    assert 0.0 < a[2] < 0.05


def test_malha_nao_repete_o_disco_e_afunda_o_que_fica_sob_ele():
    g = Grade(-1000.0, -1000.0, 100.0, 21, 21, [[5.0] * 21 for _ in range(21)])
    faixa = box(-1000, -1000, 1000, 1000)
    v, f, _ = malha_orla(g, faixa, (0.0, 0.0), 450.0, lambda x, y: 3.0, afundar=0.5)
    pts = np.array(v)
    for t1, t2 in zip(f[::2], f[1::2]):  # cada célula são dois triângulos
        assert max(math.hypot(*pts[k][:2]) for k in {*t1, *t2}) > 450.0  # nenhuma célula toda no disco
    dentro = [p for p in v if math.hypot(p[0], p[1]) < 450.0]
    assert dentro and all(p[2] == 2.5 for p in dentro)
    fora = [p for p in v if math.hypot(p[0], p[1]) > 450.0]
    assert all(p[2] == 5.0 for p in fora)
