import math

import numpy as np
import pytest

from scripts.entorno.masterplan import Semelhanca
from scripts.marcos.encaixe import ancora, escolher_circulo, girar, icp_rigido


def test_girar_e_desgirar_em_torno_do_pivo():
    p = np.array([[50.0, 60.0], [0.0, 0.0]])
    ida = girar(p, (40.56, 45.98), 28.0)
    assert girar(ida, (40.56, 45.98), -28.0) == pytest.approx(p)
    assert girar(np.array([[40.56, 45.98]]), (40.56, 45.98), 28.0) == pytest.approx(np.array([[40.56, 45.98]]))


def test_escolhe_o_circulo_pelo_raio_e_pela_distancia():
    circulos = [(176.2, 124.9, 17.5), (-14.0, 333.9, 12.5), (77.2, -1.6, 9.0)]
    assert escolher_circulo(circulos, 17.4, 360.6, (-57.2, -154.7)) == (176.2, 124.9, 17.5)


def test_nenhum_ou_dois_circulos_falham():
    with pytest.raises(SystemExit, match="círculo"):
        escolher_circulo([(0.0, 0.0, 5.0)], 17.4, 360.6, (100.0, 0.0))
    with pytest.raises(SystemExit, match="círculo"):
        escolher_circulo([(0.0, 0.0, 17.0), (0.0, 0.0, 18.0)], 17.4, 100.0, (100.0, 0.0))


def test_ancora_leva_os_dois_pares():
    t = Semelhanca(1.0, math.radians(37.0), 120.0, -45.0)
    ilha, clube = np.array([58.0, 413.0]), np.array([45.0, 55.0])
    a = ancora(ilha, clube, t.aplicar(ilha[None])[0], t.aplicar(clube[None])[0])
    assert a.s == 1.0
    assert math.degrees(a.theta) == pytest.approx(37.0, abs=1e-6)
    assert (a.tx, a.ty) == pytest.approx((120.0, -45.0), abs=1e-6)


def test_icp_rigido_corrige_um_erro_pequeno_e_ignora_sobra():
    ts = np.linspace(0, 2 * math.pi, 400, endpoint=False)
    destino = np.c_[80 * np.cos(ts) + 10 * np.cos(3 * ts), 50 * np.sin(ts)]
    certa = Semelhanca(1.0, math.radians(2.0), 3.0, -2.0)
    origem = certa.inversa(destino)
    sobra = np.array([[500.0, 500.0], [510.0, 500.0]])  # pedaço de rua que o DWG não tem
    achada, residuo = icp_rigido(np.vstack([origem, sobra]), destino, Semelhanca(1.0, 0.0, 0.0, 0.0))
    assert math.degrees(achada.theta) == pytest.approx(2.0, abs=0.1)
    assert (achada.tx, achada.ty) == pytest.approx((3.0, -2.0), abs=0.1)
    assert residuo < 0.1
