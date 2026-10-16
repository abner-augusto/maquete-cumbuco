import json

from scripts.loteamento.extrair import extrair_lotes
from scripts.loteamento.saida import Config, carregar_config, montar_lotes_json
from tests.conftest import E0, N0

CFG = Config(mostrar_precos=False, tabela_arquivo="t.xls", tabela_nome="SET26", tabela_referencia="2026-09", tolerancia_area=0.005)


def test_carregar_config(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"mostrarPrecos": True, "tabelaPrecos": {"arquivo": "a", "nome": "n", "referencia": "r"}, "toleranciaArea": 0.01}), encoding="utf-8")
    assert carregar_config(p) == Config(True, "a", "n", "r", 0.01)


def test_lotes_json_sem_precos_nao_vaza_preco(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    j = montar_lotes_json(extrair_lotes(doc_sintetico, mapa_sintetico), tabela_sintetica, iptu_sintetico, CFG, E0, N0)
    texto = json.dumps(j)
    assert j["precos"] is None
    assert "preco" not in texto.replace('"precos": null', "")
    assert "276000" not in texto and "1380" not in texto


def test_lotes_json_com_precos(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    cfg = Config(True, "t.xls", "SET26", "2026-09", 0.005)
    j = montar_lotes_json(extrair_lotes(doc_sintetico, mapa_sintetico), tabela_sintetica, iptu_sintetico, cfg, E0, N0)
    assert j["precos"] == {"tabela": "SET26", "referencia": "2026-09"}
    l1 = j["lotes"][0]
    assert l1["id"] == "Q01L01"
    assert l1["preco"] == {"total": 276000.0, "m2": 1380.0, "classificacao": "A"}


def test_formato_do_lote(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    j = montar_lotes_json(extrair_lotes(doc_sintetico, mapa_sintetico), tabela_sintetica, iptu_sintetico, CFG, E0, N0)
    assert [l["id"] for l in j["lotes"]] == ["Q01L01", "Q01L02", "QHL01"]
    l1, h1 = j["lotes"][0], j["lotes"][2]
    assert l1 == {
        "id": "Q01L01", "quadra": "01", "lote": "01", "tipo": "residencial", "area_m2": 200.0,
        "lados_m": [10.0, 20.0, 10.0, 20.0], "frente_m": 10.0, "frente_rumo": 180.0,
        "poligono": [[0.0, 0.0], [10.0, 0.0], [10.0, 20.0], [0.0, 20.0]], "inscricao_iptu": "138321-3",
    }
    assert h1["tipo"] == "uso_misto" and "inscricao_iptu" not in h1
