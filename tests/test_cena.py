import ezdxf
import pytest
from shapely.geometry import Polygon, box

from scripts.loteamento.cena import CenaCfg, achar_lagoa, aneis_da_layer, montar
from scripts.loteamento.geometria import area
from scripts.loteamento.relevo import Grade

E0, N0 = 500_000.0, 9_600_000.0
from scripts.loteamento.placa import PlacaCfg

CFG = CenaCfg(camadas={"Vias": ["VIA"], "APP": ["APP"]}, lagoa_camadas=["APP"],
              lagoa_texto="LAGOA AZUL", tolerancia=0.05)
PLACA = PlacaCfg(alturas={"Pista": 0.0, "ChaoPlato": 0.0, "Calcadas": 0.25, "Verdes": 0.25,
                          "Institucional": 0.25, "Fundo": 0.25, "APP": 0.25, "Juntas": 0.25,
                          "lote": 0.40, "Lagoa": -0.30})
JANELAS = {"00": (-10.0, -10.0, 400.0, 200.0)}


def _ret(x, y, w, h):
    return [(E0 + x, N0 + y), (E0 + x + w, N0 + y), (E0 + x + w, N0 + y + h), (E0 + x, N0 + y + h)]


def _local(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


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
PLATO = [_local(0, 0, 100, 100), _local(200, 0, 100, 100)]


def _area_topo(o, z):
    v = o["vertices"]
    return sum(Polygon([v[i][:2] for i in f]).area for f in o["faces"] if all(abs(v[i][2] - z) < 1e-6 for i in f))


def test_circulo_vira_anel(msp):
    aneis = aneis_da_layer(msp, ["VIA"], E0, N0)
    assert len(aneis) == 2
    assert sorted(round(area(a)) for a in aneis) == [314, 10000]


def test_lagoa_e_o_menor_poligono_com_o_texto(msp):
    assert round(area(achar_lagoa(msp, CFG, E0, N0))) == 1600


def test_montar_placa_lotes_e_terreno_em_janelas(msp):
    por_nome = {o["nome"]: o for o in montar(msp, GRADE, LOTES, CFG, PLACA, PLATO, JANELAS, E0, N0)["objetos"]}
    assert {"Pista", "APP", "Lagoa", "Q01L01", "Juntas", "ChaoPlato", "Terreno_00"} <= set(por_nome)
    assert por_nome["Q01L01"]["material"] == "lote_residencial"
    assert por_nome["Q01L01"]["origem"] == pytest.approx([5.0, 10.0, 10.4])
    assert max(p[2] for p in por_nome["Lagoa"]["vertices"]) == pytest.approx(9.7)
    assert _area_topo(por_nome["Lagoa"], 9.7) == pytest.approx(1600, rel=0.01)
    assert _area_topo(por_nome["ChaoPlato"], 10.0) == pytest.approx(314, rel=0.02)  # a ilha da rotatória (PLACA do teste: 0,0)


def test_ilha_da_lagoa_e_app_e_o_resto_e_agua():
    doc = ezdxf.new()
    m = doc.modelspace()
    m.add_lwpolyline(_ret(230, 30, 40, 40), close=True, dxfattribs={"layer": "APP"})  # a lagoa
    m.add_lwpolyline(_ret(250, 50, 10, 10), close=True, dxfattribs={"layer": "APP"})  # ilha
    m.add_text("LAGOA AZUL", dxfattribs={"layer": "TXT", "insert": (E0 + 238, N0 + 38)})
    por_nome = {o["nome"]: o for o in montar(m, GRADE, LOTES, CFG, PLACA, PLATO, JANELAS, E0, N0)["objetos"]}
    assert _area_topo(por_nome["APP"], 10.25) == pytest.approx(100, rel=0.01)
    assert _area_topo(por_nome["Lagoa"], 9.7) == pytest.approx(1600 - 100, rel=0.01)


def test_terreno_nao_entra_na_placa(msp):
    por_nome = {o["nome"]: o for o in montar(msp, GRADE, LOTES, CFG, PLACA, PLATO, JANELAS, E0, N0)["objetos"]}
    t = por_nome["Terreno_00"]
    placa = box(0, 0, 100, 100).union(box(200, 0, 300, 100))
    assert not any(placa.contains(Polygon([t["vertices"][i][:2] for i in f]).centroid) for f in t["faces"])


def test_cfg_carrega_do_toml():
    from scripts.comum.ambiente import RAIZ

    cfg = CenaCfg.carregar(RAIZ / "scripts" / "loteamento" / "cena.toml")
    placa = PlacaCfg.carregar(RAIZ / "scripts" / "loteamento" / "cena.toml")
    assert "Vias" in cfg.camadas
    assert placa.alturas["lote"] > placa.alturas["Calcadas"] > placa.alturas["Pista"] > placa.alturas["Lagoa"]


def test_plato_e_a_uniao_dos_aneis_nao_um_desenho_com_furos(msp):
    # revisão: aneis_do_plato traz a poligonal, as áreas e os lotes; o lote dentro da poligonal virava furo
    com_lote = PLATO + [[tuple(p) for p in LOTES[0]["poligono"]]]
    por_nome = {o["nome"]: o for o in montar(msp, GRADE, LOTES, CFG, PLACA, com_lote, JANELAS, E0, N0)["objetos"]}
    assert _area_topo(por_nome["Q01L01"], 10.4) == pytest.approx(9.7 * 19.7, rel=0.01)


def test_pecas_da_placa_sem_malhas(msp):
    from scripts.loteamento.cena import pecas_da_placa

    pecas, plato = pecas_da_placa(msp, LOTES, CFG, PLACA, PLATO, E0, N0)
    assert {"Q01L01", "Pista", "Lagoa"} <= set(pecas)
    assert plato.area == pytest.approx(20000, rel=1e-3)


def test_pegada_abre_furo_na_placa(msp):
    pegada = box(40, 40, 60, 60)  # no meio da via
    por_nome = {o["nome"]: o for o in montar(msp, GRADE, LOTES, CFG, PLACA, PLATO, JANELAS, E0, N0,
                                             pegadas=pegada)["objetos"]}
    for o in por_nome.values():
        v = o["vertices"]
        for f in o["faces"]:
            if len({round(v[i][2], 3) for i in f}) == 1:  # topo
                assert not pegada.buffer(-0.01).contains(Polygon([v[i][:2] for i in f]).centroid), o["nome"]


def test_pegada_sobre_lote_falha_nomeando(msp):
    with pytest.raises(ValueError, match="Q01L01"):
        montar(msp, GRADE, LOTES, CFG, PLACA, PLATO, JANELAS, E0, N0, pegadas=box(2, 2, 8, 8))


def test_main_sem_marcos_avisa_e_segue(tmp_path, monkeypatch, capsys):
    from scripts.loteamento import cena

    monkeypatch.setattr(cena, "MARCOS_JSON", tmp_path / "nao-existe.json")
    assert cena.pegadas_dos_marcos() is None
    assert "sem marcos" in capsys.readouterr().out
