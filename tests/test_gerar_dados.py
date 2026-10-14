import json

from scripts.loteamento.gerar_dados import gerar
from scripts.loteamento.saida import Config

CFG = Config(False, "t.xls", "SET26", "2026-09", 0.005)


def test_gera_os_tres_arquivos(tmp_path, doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    rel = gerar(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico, CFG, tmp_path)
    assert rel.erros == []
    assert len(json.loads((tmp_path / "lotes.json").read_text(encoding="utf-8"))["lotes"]) == 3
    assert json.loads((tmp_path / "georref.json").read_text(encoding="utf-8"))["crs"] == "EPSG:31984"
    assert (tmp_path / "relatorio-conferencia.md").exists()


def test_erro_de_conferencia_nao_grava_lotes_json(tmp_path, doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    tabela = dict(tabela_sintetica)
    del tabela["QHL01"]
    rel = gerar(doc_sintetico, mapa_sintetico, tabela, iptu_sintetico, CFG, tmp_path)
    assert rel.erros
    assert not (tmp_path / "lotes.json").exists()
    assert "QHL01: no desenho e não na tabela" in (tmp_path / "relatorio-conferencia.md").read_text(encoding="utf-8")


def test_erro_de_extracao_vai_para_o_relatorio(tmp_path, doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    msp = doc_sintetico.modelspace()
    for t in list(msp.query('TEXT[layer=="NUM_LOTE"]')):
        msp.delete_entity(t)
    rel = gerar(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico, CFG, tmp_path)
    assert any("0 rótulos" in e for e in rel.erros)
    assert not (tmp_path / "lotes.json").exists()


def test_lotes_json_antigo_e_apagado_quando_ha_erro(tmp_path, doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    (tmp_path / "lotes.json").write_text("{}", encoding="utf-8")
    tabela = dict(tabela_sintetica)
    del tabela["QHL01"]
    gerar(doc_sintetico, mapa_sintetico, tabela, iptu_sintetico, CFG, tmp_path)
    assert not (tmp_path / "lotes.json").exists()
