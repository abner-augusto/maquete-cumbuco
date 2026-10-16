import dataclasses

import pytest

from scripts.loteamento.extrair import ExtracaoErro, MapaLayers, extrair_lotes
from tests.conftest import AREA_H1, E0, N0, _ret
from scripts.loteamento.geometria import area


def test_extrai_tres_lotes_com_ids_canonicos(doc_sintetico, mapa_sintetico):
    lotes = extrair_lotes(doc_sintetico, mapa_sintetico)
    assert set(lotes) == {"Q01L01", "Q01L02", "QHL01"}
    l1 = lotes["Q01L01"]
    assert (l1.quadra, l1.lote) == ("01", "01")
    assert l1.lados_m == [10.0, 20.0, 10.0, 20.0]
    assert l1.frente_m == 10.0
    assert area(lotes["QHL01"].pontos) == pytest.approx(AREA_H1, rel=1e-3)
    assert lotes["QHL01"].frente_m > 30  # frente em arco é mais longa que a corda


def test_lote_sem_rotulo_e_erro_com_handle(doc_sintetico, mapa_sintetico):
    msp = doc_sintetico.modelspace()
    texto = next(e for e in msp.query('TEXT[layer=="NUM_LOTE"]') if e.dxf.text == "1")
    msp.delete_entity(texto)
    with pytest.raises(ExtracaoErro) as exc:
        extrair_lotes(doc_sintetico, mapa_sintetico)
    assert any("0 rótulos" in e and "lote" in e for e in exc.value.erros)


def test_lote_com_dois_rotulos_e_erro(doc_sintetico, mapa_sintetico):
    doc_sintetico.modelspace().add_text("9", dxfattribs={"layer": "NUM_LOTE", "insert": (E0 + 3, N0 + 3)})
    with pytest.raises(ExtracaoErro) as exc:
        extrair_lotes(doc_sintetico, mapa_sintetico)
    assert any("2 rótulos" in e for e in exc.value.erros)


def test_lote_fora_de_quadra_e_erro(doc_sintetico, mapa_sintetico):
    msp = doc_sintetico.modelspace()
    msp.add_lwpolyline([(E0 + 100, N0), (E0 + 110, N0), (E0 + 110, N0 + 10), (E0 + 100, N0 + 10)], close=True, dxfattribs={"layer": "LOTES"})
    msp.add_text("5", dxfattribs={"layer": "NUM_LOTE", "insert": (E0 + 105, N0 + 5)})
    with pytest.raises(ExtracaoErro) as exc:
        extrair_lotes(doc_sintetico, mapa_sintetico)
    assert any("0 quadras" in e for e in exc.value.erros)


def test_mapa_carrega_do_toml(tmp_path):
    p = tmp_path / "layers.toml"
    p.write_text('lotes="A"\nrotulo_lote="B"\nquadras="C"\nrotulo_quadra="D"\nmeio_fio="E"\n', encoding="utf-8")
    assert MapaLayers.carregar(p) == MapaLayers("A", "B", "C", "D", "E")


# No DWG real: blocos com atributo (o ATTRIB herda a layer "0"), quadras sem rótulo
# (área institucional, administrativo) e lotes de uso misto identificados por texto.


def test_mapa_carrega_uso_misto_e_area(tmp_path):
    p = tmp_path / "layers.toml"
    p.write_text(
        'lotes="A"\nrotulo_lote="B"\nquadras="C"\nrotulo_quadra="D"\nmeio_fio="E"\narea_lote="F"\n'
        '[uso_misto]\nQML01 = { layer = "MLF", texto = "LOTE MULTIFAMILIAR-01" }\n',
        encoding="utf-8",
    )
    m = MapaLayers.carregar(p)
    assert m.area_lote == "F"
    assert m.uso_misto == (("QML01", "MLF", "LOTE MULTIFAMILIAR-01"),)


def test_rotulo_por_atributo_na_layer_do_bloco(doc_sintetico, mapa_sintetico):
    msp = doc_sintetico.modelspace()
    ref = next(e for e in msp.query("INSERT") if e.dxf.name == "NUMERO")
    for a in ref.attribs:
        a.dxf.layer = "0"
    assert "Q01L02" in extrair_lotes(doc_sintetico, mapa_sintetico)


def test_quadra_sem_rotulo_sem_lotes_e_ignorada(doc_sintetico, mapa_sintetico):
    doc_sintetico.modelspace().add_lwpolyline(_ret(200, 0, 20, 20), close=True, dxfattribs={"layer": "QUADRAS"})
    assert len(extrair_lotes(doc_sintetico, mapa_sintetico)) == 3


def test_area_cad_do_bloco_de_area(doc_sintetico, mapa_sintetico):
    doc = doc_sintetico
    bloco = doc.blocks.new("BL_AREA")
    bloco.add_attdef("AMBIENTE", (0, 0))
    bloco.add_attdef("AREA", (0, -1))
    ref = doc.modelspace().add_blockref("BL_AREA", (E0 + 4, N0 + 4), dxfattribs={"layer": "AREAS"})
    ref.add_auto_attribs({"AMBIENTE": "", "AREA": "200.00"})
    mapa = dataclasses.replace(mapa_sintetico, area_lote="AREAS")
    lotes = extrair_lotes(doc, mapa)
    assert lotes["Q01L01"].area_cad == 200.0
    assert lotes["Q01L02"].area_cad is None


def test_lote_de_uso_misto_pelo_texto(doc_sintetico, mapa_sintetico):
    msp = doc_sintetico.modelspace()
    msp.add_lwpolyline(_ret(0, 40, 40, 50), close=True, dxfattribs={"layer": "MLF"})
    msp.add_mtext("LOTE MULTIFAMILIAR-01\\PA=2.000,00m²", dxfattribs={"layer": "TXT", "insert": (E0 + 20, N0 + 60)})
    mapa = dataclasses.replace(mapa_sintetico, uso_misto=(("QML01", "MLF", "LOTE MULTIFAMILIAR-01"),))
    m1 = extrair_lotes(doc_sintetico, mapa)["QML01"]
    assert (m1.quadra, m1.lote) == ("M", "01")
    assert area(m1.pontos) == pytest.approx(2000.0)


def test_uso_misto_sem_poligono_e_erro(doc_sintetico, mapa_sintetico):
    mapa = dataclasses.replace(mapa_sintetico, uso_misto=(("QML02", "MLF", "LOTE MULTIFAMILIAR-02"),))
    with pytest.raises(ExtracaoErro) as exc:
        extrair_lotes(doc_sintetico, mapa)
    assert any("QML02" in e and "0 polígonos" in e for e in exc.value.erros)


# Revisão final: frente pela borda de fechamento da via, segmentos degenerados,
# polilinha de lote aberta e rótulo órfão.


def test_frente_usa_a_aresta_de_fechamento_da_via(doc_sintetico, mapa_sintetico):
    msp = doc_sintetico.modelspace()
    for e in list(msp.query('LWPOLYLINE[layer=="MEIO_FIO"]')):
        msp.delete_entity(e)
    # Via fechada cuja aresta de fechamento (último → primeiro ponto) corre ao sul dos lotes.
    msp.add_lwpolyline(
        [(E0 + 65, N0 - 8), (E0 + 65, N0 - 300), (E0 - 500, N0 - 300), (E0 - 500, N0 - 8)],
        close=True, dxfattribs={"layer": "MEIO_FIO"},
    )
    lote = extrair_lotes(doc_sintetico, mapa_sintetico)["Q01L01"]
    assert lote.frente_m == 10.0
    assert lote.frente_rumo == pytest.approx(180.0)  # a rua corre ao sul


def test_segmento_degenerado_nao_vira_frente(doc_sintetico, mapa_sintetico):
    msp = doc_sintetico.modelspace()
    lote = next(e for e in msp.query('LWPOLYLINE[layer=="LOTES"]') if e.get_points("xy")[0] == (E0, N0))
    # vértice extra a 2 cm do canto sudoeste, junto ao meio-fio
    lote.set_points([(E0, N0 - 0.02), (E0, N0), (E0 + 10, N0), (E0 + 10, N0 + 20), (E0, N0 + 20)], format="xy")
    assert extrair_lotes(doc_sintetico, mapa_sintetico)["Q01L01"].frente_m == 10.0


def test_polilinha_de_lote_aberta_e_erro_com_handle(doc_sintetico, mapa_sintetico):
    e = doc_sintetico.modelspace().add_lwpolyline(
        [(E0 + 2, N0 + 30), (E0 + 8, N0 + 30), (E0 + 8, N0 + 35)], dxfattribs={"layer": "LOTES"}
    )
    with pytest.raises(ExtracaoErro) as exc:
        extrair_lotes(doc_sintetico, mapa_sintetico)
    assert any(e.dxf.handle in m and "aberta" in m for m in exc.value.erros)


def test_rotulo_de_lote_fora_de_qualquer_lote_e_erro(doc_sintetico, mapa_sintetico):
    doc_sintetico.modelspace().add_text("7", dxfattribs={"layer": "NUM_LOTE", "insert": (E0 + 300, N0 + 300)})
    with pytest.raises(ExtracaoErro) as exc:
        extrair_lotes(doc_sintetico, mapa_sintetico)
    assert any("rótulo de lote '7'" in m and "fora de qualquer lote" in m for m in exc.value.erros)
