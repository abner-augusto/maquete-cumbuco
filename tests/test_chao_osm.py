from shapely.geometry import Polygon

from scripts.entorno.preparar import camadas_do_chao
from scripts.loteamento.terreno import ZONA_LAGOA

LAGUNA = [[(0, 0), (200, 0), (200, 200), (0, 200), (0, 0)]]
BASE = {"areas": [{"tipo": "agua", "poligonos": [LAGUNA]}]}
VIA = {"classe": "primary", "pontos": [(-500, 100), (500, 100)], "largura": "10"}


def _camada(camadas, nome):
    return next((g for n, g in camadas if n == nome), None)


def test_com_a_lagoa_do_masterplan_a_agua_do_osm_recua_e_sem_ela_fica_inteira():
    plato = Polygon([(1000, 1000), (1100, 1000), (1100, 1100)])
    lagoa = (Polygon([(-50, -50), (250, -50), (250, 250), (-50, 250)]),)
    assert _camada(camadas_do_chao(BASE, [], plato, lagoa), "agua") is None  # a lagoa cobre a água toda
    inteira = _camada(camadas_do_chao(BASE, [], plato), "agua")
    assert inteira.area == Polygon(LAGUNA[0]).area and ZONA_LAGOA > 0


def test_o_chao_so_com_osm_leva_as_vias_que_o_masterplan_cortou():
    plato = Polygon([(1000, 1000), (1100, 1000), (1100, 1100)])
    assert _camada(camadas_do_chao(BASE, [VIA], plato), "via_principal").area > 0
    assert _camada(camadas_do_chao(BASE, [], plato), "via_principal").is_empty
