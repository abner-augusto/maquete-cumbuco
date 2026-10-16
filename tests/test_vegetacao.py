import random

import pytest
from shapely.geometry import Point, Polygon

from scripts.entorno.vegetacao import area_livre, canteiros, instancias, pontos_zona


class Plano:
    def cota(self, x, y):
        return 10.0 if x >= 0 else -2.0  # a oeste, mar


def test_pontos_zona_densidade_e_dentro():
    zona = Polygon([(0, 0), (200, 0), (200, 200), (0, 200)])
    pts = pontos_zona(zona, 100.0, {"cajueiro": 0.5, "arbusto": 0.5}, random.Random(1))
    assert 300 < len(pts) < 500  # ~40 000 m² / 100 m²
    assert all(zona.contains(Point(x, y)) for x, y, _ in pts)
    assert {e for _, _, e in pts} == {"cajueiro", "arbusto"}


def test_canteiros_so_em_faixa_estreita():
    faixa = [(0.0, 0.0), (120.0, 0.0), (120.0, 4.0), (0.0, 4.0)]
    praca = [(0.0, 50.0), (50.0, 50.0), (50.0, 100.0), (0.0, 100.0)]
    pts = canteiros([faixa, praca])
    assert pts and all(0 <= x <= 120 and 1.0 <= y <= 3.0 for x, y in pts)  # no eixo do canteiro
    assert 8 <= len(pts) <= 12  # um coqueiro a cada ~12 m
    assert min(abs(a[0] - b[0]) for a in pts for b in pts if a != b) >= 6.0


def test_instancias_com_cota_e_sem_mar():
    pts = [(5.0, 5.0, "coqueiro"), (-5.0, 5.0, "coqueiro")]
    inst = instancias(pts, Plano(), -1.29, random.Random(1))
    (x_dm, y_dm, z_cm, esc, rot), = [inst["coqueiro"][i:i + 5] for i in range(0, len(inst["coqueiro"]), 5)]
    assert (x_dm, y_dm, z_cm) == (50, 50, 1000) and 80 <= esc <= 120 and 0 <= rot < 360
    assert inst["arbusto"] == [] and inst["cajueiro"] == []


def test_canteiros_ficam_no_topo_dos_verdes():
    from scripts.comum.ambiente import RAIZ
    from scripts.entorno.vegetacao import OFFSET_CANTEIRO
    from scripts.loteamento.placa import PlacaCfg

    assert OFFSET_CANTEIRO == PlacaCfg.carregar(RAIZ / "scripts" / "loteamento" / "cena.toml").alturas["Verdes"]


def test_area_livre_tira_o_masterplan_e_o_plato():
    base = {"centro": [0.0, 0.0], "vias": [], "predios": [], "areas": []}
    plato = Polygon([(-10, -10), (10, -10), (10, 10), (-10, 10)])
    gleba = Polygon([(100, -50), (300, -50), (300, 50), (100, 50)])
    livre = area_livre(base, 500.0, plato, gleba)
    assert not livre.contains(Point(0, 0))      # platô da Fase 1
    assert not livre.contains(Point(200, 0))    # fases do masterplan, sem árvore por cima
    assert livre.contains(Point(-200, 0))       # mata do entorno
    assert not livre.contains(Point(600, 0))    # fora do raio
