import pytest
from shapely.geometry import Point, Polygon

from scripts.entorno.preparar import altura_predio, extrudar


class Plano:
    def __init__(self, z):
        self.z = z

    def cota(self, x, y):
        return self.z


class Rampa:
    def cota(self, x, y):
        return x / 10


QUAD = [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]


def test_extrudar_caixa_no_plano():
    v, f = extrudar(QUAD, Plano(5.0), 4.0)
    assert sorted({round(z, 2) for _, _, z in v}) == [4.7, 9.0]
    assert len(f) == 2 + 4 * 2  # teto + 4 paredes


def test_extrudar_na_encosta_nao_flutua():
    v, _ = extrudar(QUAD, Rampa(), 4.0)
    assert min(z for _, _, z in v) == pytest.approx(0.0 - 0.3)  # base na menor cota sob a pegada
    assert max(z for _, _, z in v) == pytest.approx(0.5 + 4.0)  # teto na cota média + altura


def test_altura_predio_pela_fonte_ou_pela_area():
    assert altura_predio({"altura": 12.3, "niveis": None}, 50) == 12.3
    assert altura_predio({"altura": None, "niveis": 3}, 50) == 9.5
    assert altura_predio({"altura": None, "niveis": None}, 50) == 3.2
    assert altura_predio({"altura": None, "niveis": None}, 2000) == 8.0


def test_faixa_3d_pelo_eixo_segue_o_relevo():
    # a triangulação do polígono unido dava diagonais de até 800 m (394 mil triângulos refinados)
    from scripts.entorno.preparar import faixa_3d

    v, f = faixa_3d([[0, 0], [100, 0]], 10.0, Rampa(), 0.3, passo=5.0)
    assert len(f) == 4 * 20  # uma seção a cada 5 m, com vértice no eixo (o relevo dobra no meio da faixa)
    assert sorted({round(y, 6) for _, y, _ in v}) == [-5.0, 0.0, 5.0]
    assert all(z == pytest.approx(x / 10 + 0.3) for x, _, z in v)


def test_faixa_3d_corta_dentro_do_plato():
    from scripts.entorno.preparar import faixa_3d

    plato = Polygon([(40, -20), (60, -20), (60, 20), (40, 20)])
    v, f = faixa_3d([[0, 0], [100, 0]], 10.0, Plano(1.0), 0.3, passo=5.0, fora=plato)
    centros = [sum(v[i][0] for i in t) / 3 for t in f]
    assert f and not any(42 < c < 58 for c in centros)
