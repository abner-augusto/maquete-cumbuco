import pytest

from scripts.loteamento.georref import CRS, georref_json, origem, para_local, parece_utm_24s


def test_reconhece_utm_24s_de_caucaia():
    assert parece_utm_24s((517_000.0, 9_597_000.0, 519_500.0, 9_599_000.0))


@pytest.mark.parametrize("ext", [(0, 0, 500, 300), (-38.8, -3.7, -38.7, -3.6), (517_000, 7_400_000, 518_000, 7_401_000)])
def test_rejeita_coordenadas_locais_geograficas_ou_de_outro_lugar(ext):
    assert not parece_utm_24s(ext)


def test_origem_e_o_centro_arredondado_a_100m():
    assert origem((517_010.0, 9_597_020.0, 519_480.0, 9_598_990.0)) == (518_200.0, 9_598_000.0)


def test_para_local():
    assert para_local([(518_210.123, 9_598_005.456)], 518_200.0, 9_598_000.0) == [[10.12, 5.46]]


def test_georref_json():
    assert georref_json(1.0, 2.0) == {"crs": CRS, "origem": {"E": 1.0, "N": 2.0}}
