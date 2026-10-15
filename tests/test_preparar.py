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


def test_tiles_sem_costura_na_linha_de_corte(tmp_path):
    from PIL import Image

    from scripts.entorno.preparar import gerar_tiles

    faixa = Polygon([(-100, -5), (100, -5), (100, 5), (-100, 5)])  # cruza a linha vertical x = 0
    tiles = gerar_tiles([("via_principal", faixa)], (-120.0, -120.0, 120.0, 120.0), 30.0, 64, 2, tmp_path)
    assert sorted(tiles) == ["00", "01", "10", "11"]

    def cor(k, x, y):
        t = tiles[k]
        x0, y0, x1, y1 = t["ext"]
        img = Image.open(t["arquivo"]).convert("RGB")
        return img.getpixel((int((x - x0) / (x1 - x0) * img.width), int((y1 - y) / (y1 - y0) * img.height)))

    # o mesmo ponto do mundo, na margem do vizinho, tem a mesma cor dos dois lados
    for x in (-0.5, 0.5):
        a, b = cor("01", x, 2.0), cor("11", x, 2.0)
        assert sum(abs(p - q) for p, q in zip(a, b)) < 30
    assert all(max(Image.open(t["arquivo"]).size) == 64 for t in tiles.values())


@pytest.mark.parametrize("anel", [QUAD[0], QUAD[0][::-1]], ids=["anti-horario", "horario"])
def test_extrudar_normais_para_fora_e_teto_para_cima(anel):
    import numpy as np

    v, f = extrudar([anel], Plano(5.0), 4.0)
    a = np.array(v, dtype=float)
    centro = np.array([5.0, 5.0])
    for i, j, k in f:
        n = np.cross(a[j] - a[i], a[k] - a[i])
        if abs(n[2]) > 1e-9:
            assert n[2] > 0  # teto
        else:
            meio = (a[i, :2] + a[j, :2] + a[k, :2]) / 3
            assert np.dot(n[:2], meio - centro) > 0  # parede para fora
