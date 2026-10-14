import ezdxf
import pytest

from scripts.loteamento.cena import CenaCfg, achar_lagoa, aneis_da_layer, montar
from scripts.loteamento.geometria import area
from scripts.loteamento.relevo import Grade

E0, N0 = 500_000.0, 9_600_000.0
CFG = CenaCfg(
    camadas={"Vias": ["VIA"], "APP": ["APP"]},
    lagoa_camadas=["APP"],
    lagoa_texto="LAGOA AZUL",
    offsets={"Vias": 0.06, "APP": 0.03, "lote": 0.15},
    tolerancia=0.05,
    max_aresta=6.0,
)


def _ret(x, y, w, h):
    return [(E0 + x, N0 + y), (E0 + x + w, N0 + y), (E0 + x + w, N0 + y + h), (E0 + x, N0 + y + h)]


@pytest.fixture
def msp():
    doc = ezdxf.new()
    m = doc.modelspace()
    m.add_lwpolyline(_ret(0, 0, 100, 100), close=True, dxfattribs={"layer": "VIA"})
    m.add_circle((E0 + 50, N0 + 50), 10, dxfattribs={"layer": "VIA"})  # ilha da rotatória
    m.add_lwpolyline(_ret(200, 0, 100, 100), close=True, dxfattribs={"layer": "APP"})
    m.add_lwpolyline(_ret(230, 30, 40, 40), close=True, dxfattribs={"layer": "APP"})  # a lagoa
    m.add_text("LAGOA AZUL", dxfattribs={"layer": "TXT", "insert": (E0 + 250, N0 + 50)})
    return m


GRADE = Grade(-10.0, -10.0, 10.0, 40, 20, [[10.0] * 40 for _ in range(20)])
LOTES = [{"id": "Q01L01", "tipo": "residencial", "poligono": [[0, 0], [10, 0], [10, 20], [0, 20]]}]


def test_circulo_vira_anel(msp):
    aneis = aneis_da_layer(msp, ["VIA"], E0, N0)
    assert len(aneis) == 2
    assert sorted(round(area(a)) for a in aneis) == [314, 10000]


def test_lagoa_e_o_menor_poligono_com_o_texto(msp):
    lagoa = achar_lagoa(msp, CFG, E0, N0)
    assert round(area(lagoa)) == 1600


def test_montar_objetos_com_furos_e_lotes_nomeados(msp):
    cena = montar(msp, GRADE, LOTES, CFG, E0, N0)
    por_nome = {o["nome"]: o for o in cena["objetos"]}
    assert {"Terreno", "Vias", "APP", "Lagoa", "Q01L01"} <= set(por_nome)
    vias = por_nome["Vias"]
    a = sum(area([vias["vertices"][i][:2] for i in f]) for f in vias["faces"])
    assert a == pytest.approx(10000 - 314.16, rel=0.01)  # a ilha fica de fora
    app = por_nome["APP"]
    a_app = sum(area([app["vertices"][i][:2] for i in f]) for f in app["faces"])
    assert a_app == pytest.approx(10000 - 1600, rel=0.01)  # a lagoa é furo da APP
    assert por_nome["Q01L01"]["material"] == "lote_residencial"
    assert all(v[2] == pytest.approx(10.15) for v in por_nome["Q01L01"]["vertices"])
    assert all(v[2] == pytest.approx(10.0) for v in por_nome["Lagoa"]["vertices"])


def test_cfg_carrega_do_toml():
    from scripts.comum.ambiente import RAIZ

    cfg = CenaCfg.carregar(RAIZ / "scripts" / "loteamento" / "cena.toml")
    assert "Vias" in cfg.camadas and cfg.offsets["lote"] > max(v for k, v in cfg.offsets.items() if k != "lote")
