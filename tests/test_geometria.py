import math

import ezdxf
import pytest

from scripts.loteamento.geometria import (
    area, centroide, contem, extensao, indice_frente, pontos_de, poligono_fechado, rumo_para_fora, segmentos,
)

E0, N0 = 500_000.0, 9_600_000.0


def _lw(pontos, close=True, fmt="xy"):
    msp = ezdxf.new().modelspace()
    return msp.add_lwpolyline(pontos, format=fmt, close=close)


def test_retangulo_em_coordenadas_utm():
    e = _lw([(E0, N0), (E0 + 10, N0), (E0 + 10, N0 + 20), (E0, N0 + 20)])
    pts = pontos_de(e)
    assert area(pts) == pytest.approx(200.0, abs=1e-6)
    assert centroide(pts) == pytest.approx((E0 + 5, N0 + 10))
    assert [round(s[2], 6) for s in segmentos(e)] == [10, 20, 10, 20]
    assert extensao(pts) == (E0, N0, E0 + 10, N0 + 20)


def test_aberta_com_ponto_final_igual_conta_como_fechada():
    e = _lw([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)], close=False)
    assert poligono_fechado(e)
    assert len(pontos_de(e)) == 4
    assert len(segmentos(e)) == 4


def test_aberta_de_verdade_nao_e_poligono():
    assert not poligono_fechado(_lw([(0, 0), (10, 0), (10, 10)], close=False))


def test_frente_em_arco_soma_o_segmento_circular():
    b = 0.2  # aresta de baixo vira arco para fora (sentido anti-horário)
    e = _lw([(0, 0, b), (30, 0, 0), (30, 20, 0), (0, 20, 0)], fmt="xyb")
    theta = 4 * math.atan(b)
    r = 30 / (2 * math.sin(theta / 2))
    segmento_circular = r * r / 2 * (theta - math.sin(theta))
    assert area(pontos_de(e)) == pytest.approx(600 + segmento_circular, rel=1e-3)
    assert segmentos(e)[0][2] == pytest.approx(r * theta, rel=1e-9)


def test_contem():
    q = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert contem(q, (5, 5))
    assert not contem(q, (15, 5))


def test_indice_frente_e_o_lado_mais_proximo_da_via():
    e = _lw([(0, 0), (10, 0), (10, 20), (0, 20)])
    via = [(-5, -3), (50, -3)]
    assert indice_frente(segmentos(e), [via]) == 0


@pytest.mark.parametrize("lado, rumo", [(0, 180.0), (1, 90.0), (2, 0.0), (3, 270.0)])
def test_rumo_para_fora_aponta_do_lote_para_a_rua(lado, rumo):
    pts = [(0, 0), (10, 0), (10, 20), (0, 20)]
    e = _lw(pts)
    assert rumo_para_fora(segmentos(e)[lado], pts) == pytest.approx(rumo)
