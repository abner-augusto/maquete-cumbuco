import itertools

import numpy as np
import pytest
from shapely.geometry import Point, Polygon, box

from scripts.loteamento.placa import PlacaCfg, altura, montar_placa, paredes, particionar, partes, poligonos, topo

ALTURAS = {"Pista": 0.0, "ChaoPlato": 0.0, "Calcadas": 0.25, "Verdes": 0.25, "Institucional": 0.25,
           "Fundo": 0.25, "APP": 0.25, "Juntas": 0.25, "lote": 0.40, "Lagoa": -0.30}
CFG = PlacaCfg(alturas=ALTURAS)
PLATO = box(0, 0, 100, 100)


def _cenario():
    papeis = {
        "Vias": box(0, 35, 100, 65),
        "Calcadas": box(0, 35, 100, 42).union(box(0, 58, 100, 65)),
        "Verdes": box(50, 65, 100, 100),
    }
    lotes = {"Q01L01": box(10, 65, 30, 90), "Q01L02": box(40, 60, 60, 90)}  # o 2º invade calçada e verde
    return papeis, lotes


def test_pecas_nao_se_sobrepoem_e_cobrem_o_plato():
    papeis, lotes = _cenario()
    pecas = particionar(PLATO, papeis, lotes, None, CFG)
    for (a, ga), (b, gb) in itertools.combinations(pecas.items(), 2):
        assert ga.intersection(gb).area < 0.01, (a, b)
    assert sum(g.area for g in pecas.values()) == pytest.approx(PLATO.area, rel=1e-3)


def test_prioridade_lote_calcada_verde_pista():
    papeis, lotes = _cenario()
    pecas = particionar(PLATO, papeis, lotes, None, CFG)
    assert pecas["Pista"].area == pytest.approx(100 * 16, rel=1e-3)  # entre as calçadas
    assert pecas["Calcadas"].intersection(box(40, 60, 60, 65)).area < 0.01  # o lote ganhou da calçada


def test_lote_vira_recuo_e_junta():
    papeis, lotes = _cenario()
    pecas = particionar(PLATO, papeis, lotes, None, CFG)
    assert pecas["Q01L01"].area == pytest.approx(19.7 * 24.7, rel=1e-3)
    assert pecas["Juntas"].intersection(box(10, 65, 30, 90)).area == pytest.approx(500 - 19.7 * 24.7, rel=1e-3)


def test_lote_estreito_fica_sem_recuo():
    pecas = particionar(PLATO, {}, {"Q01L01": box(10, 10, 10.25, 30)}, None, CFG)
    assert pecas["Q01L01"].area == pytest.approx(0.25 * 20, rel=1e-3)


def test_lote_engolido_pela_lagoa_falha_com_o_nome():
    with pytest.raises(ValueError, match="Q01L01"):
        particionar(PLATO, {}, {"Q01L01": box(10, 10, 20, 20)}, box(0, 0, 50, 50), CFG)


def test_fresta_pequena_junto_da_via_vira_pista_e_o_resto_chao():
    papeis = {"Vias": box(0, 40, 100, 60), "Calcadas": box(0, 60, 99, 61.5),  # fresta de 1 × 1,5 m na ponta
              "Verdes": box(0, 61.5, 100, 100)}
    pecas = particionar(PLATO, papeis, {}, None, CFG)
    assert pecas["Pista"].area == pytest.approx(100 * 20 + 1.5, rel=1e-4)
    assert pecas["ChaoPlato"].area == pytest.approx(100 * 40, rel=1e-4)  # grande demais para fresta


def test_ilha_da_rotatoria_e_chao_nao_pista():
    anel = [(0.0, 40.0), (100.0, 40.0), (100.0, 60.0), (0.0, 60.0)]
    ilha = list(Point(50, 50).buffer(5).exterior.coords)[:-1]
    vias = poligonos([anel, ilha])
    pecas = particionar(PLATO, {"Vias": vias}, {}, None, CFG)
    assert pecas["Pista"].intersection(Point(50, 50).buffer(4)).area < 0.01
    assert pecas["ChaoPlato"].contains(Point(50, 50))


def test_partes_ignora_linhas_e_pontos():
    from shapely.geometry import GeometryCollection, LineString

    g = GeometryCollection([box(0, 0, 1, 1), LineString([(0, 0), (5, 5)]), Point(3, 3)])
    assert [p.area for p in partes(g)] == [1.0]


def _normais(v, f):
    v = np.array(v, dtype=float)
    return [np.cross(v[b] - v[a], v[c] - v[a]) for a, b, c in f]


def test_topo_plano_com_normal_para_cima_e_furo():
    g = box(0, 0, 10, 10).difference(box(4, 4, 6, 6))
    v, f = topo(g, 5.0)
    assert {p[2] for p in v} == {5.0}
    assert all(n[2] > 0 for n in _normais(v, f))
    assert sum(abs(n[2]) / 2 for n in _normais(v, f)) == pytest.approx(96.0)


def test_parede_so_onde_o_vizinho_nao_cobre_e_para_fora():
    a, b = box(0, 0, 10, 10), box(10, 0, 20, 10)  # b encosta no lado leste de a
    v, f = paredes(a, 0.25, -1.0, b)
    assert len(f) == 3 * 2  # oeste, sul, norte
    assert not any(abs(v[k][0] - 10) < 0.01 and abs(v[k + 2][0] - 10) < 0.01 for k in range(0, len(v), 4))
    centro = np.array([5.0, 5.0])
    for (i, j, k), n in zip(f, _normais(v, f)):
        meio = (np.array(v[i][:2]) + np.array(v[k][:2])) / 2
        assert np.dot(n[:2], meio - centro) > 0
    assert min(p[2] for p in v) == -1.0 and max(p[2] for p in v) == 0.25


def test_parede_do_furo_aponta_para_dentro_do_furo():
    g = box(0, 0, 10, 10).difference(box(4, 4, 6, 6))
    v, f = paredes(g, 0.0, -1.0, Polygon())
    for (i, j, k), n in zip(f, _normais(v, f)):
        meio = (np.array(v[i][:2]) + np.array(v[k][:2])) / 2
        if 3.9 < meio[0] < 6.1 and 3.9 < meio[1] < 6.1:
            assert np.dot(n[:2], np.array([5.0, 5.0]) - meio) > 0  # normal para o centro do furo


def test_montar_placa_materiais_origem_e_meio_fio():
    papeis, lotes = _cenario()
    pecas = particionar(PLATO, papeis, lotes, None, CFG)
    objs = {o["nome"]: o for o in montar_placa(pecas, CFG, 21.0, {"Q01L01": "lote_residencial",
                                                                   "Q01L02": "lote_uso_misto"})}
    assert objs["Pista"]["material"] == "vias" and objs["ChaoPlato"]["material"] == "terreno"
    assert objs["Q01L01"]["material"] == "lote_residencial" and objs["Juntas"]["material"] == "juntas"
    assert objs["Q01L01"]["origem"] == pytest.approx([20.0, 77.5, 21.4])
    assert all(o["suave"] is False for o in objs.values())
    assert max(p[2] for p in objs["Calcadas"]["vertices"]) == pytest.approx(21.25)
    assert altura("Q09L09", CFG) == 0.40
