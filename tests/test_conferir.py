from dataclasses import replace

from scripts.loteamento.conferir import conferir, escrever_relatorio
from scripts.loteamento.extrair import extrair_lotes
from scripts.loteamento.fontes import LinhaPreco


def _lotes(doc, mapa):
    return extrair_lotes(doc, mapa)


def test_tudo_confere_com_aviso_de_iptu(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    rel = conferir(_lotes(doc_sintetico, mapa_sintetico), tabela_sintetica, iptu_sintetico, False, 0.005)
    assert rel.erros == []
    assert rel.avisos == ["QHL01: sem inscrição de IPTU"]
    assert rel.contagens == {"desenho": 3, "tabela": 3, "iptu": 2}


def test_lote_faltando_dos_dois_lados(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    tabela = dict(tabela_sintetica)
    del tabela["Q01L02"]
    tabela["Q09L09"] = LinhaPreco(100.0, "A", 1.0, 100.0)
    rel = conferir(_lotes(doc_sintetico, mapa_sintetico), tabela, iptu_sintetico, False, 0.005)
    assert "Q01L02: no desenho e não na tabela" in rel.erros
    assert "Q09L09: na tabela e não no desenho" in rel.erros


def test_area_fora_da_tolerancia(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    tabela = dict(tabela_sintetica, Q01L01=replace(tabela_sintetica["Q01L01"], area_m2=202.0))
    rel = conferir(_lotes(doc_sintetico, mapa_sintetico), tabela, iptu_sintetico, False, 0.005)
    assert rel.erros == ["Q01L01: área do desenho 200.00 m² × tabela 202.00 m² (-0.99%)"]


def test_area_dentro_da_tolerancia_passa(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    tabela = dict(tabela_sintetica, Q01L01=replace(tabela_sintetica["Q01L01"], area_m2=200.9))
    assert conferir(_lotes(doc_sintetico, mapa_sintetico), tabela, iptu_sintetico, False, 0.005).erros == []


def test_preco_obrigatorio_so_com_precos_ligados(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    tabela = dict(tabela_sintetica, Q01L01=replace(tabela_sintetica["Q01L01"], preco_total=0.0))
    lotes = _lotes(doc_sintetico, mapa_sintetico)
    assert conferir(lotes, tabela, iptu_sintetico, False, 0.005).erros == []
    assert conferir(lotes, tabela, iptu_sintetico, True, 0.005).erros == ["Q01L01: sem preço na tabela"]


def test_area_escrita_no_desenho_divergente_e_aviso(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    lotes = _lotes(doc_sintetico, mapa_sintetico)
    lotes["Q01L01"] = replace(lotes["Q01L01"], area_cad=210.0)
    lotes["Q01L02"] = replace(lotes["Q01L02"], area_cad=200.4)
    rel = conferir(lotes, tabela_sintetica, iptu_sintetico, False, 0.005)
    assert rel.erros == []
    assert "Q01L01: área escrita no desenho 210.00 m² × polígono 200.00 m² (-4.76%)" in rel.avisos
    assert not any(a.startswith("Q01L02") for a in rel.avisos)


def test_relatorio_markdown(tmp_path, doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    rel = conferir(_lotes(doc_sintetico, mapa_sintetico), tabela_sintetica, iptu_sintetico, False, 0.005)
    destino = tmp_path / "r.md"
    escrever_relatorio(rel, destino)
    texto = destino.read_text(encoding="utf-8")
    assert "| desenho | 3 |" in texto
    assert "## Erros (0)" in texto
    assert "- QHL01: sem inscrição de IPTU" in texto


def test_frente_curta_e_aviso(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    lotes = _lotes(doc_sintetico, mapa_sintetico)
    lotes["Q01L01"] = replace(lotes["Q01L01"], frente_m=0.88)
    rel = conferir(lotes, tabela_sintetica, iptu_sintetico, False, 0.005)
    assert "Q01L01: frente de 0.88 m (menos de 5 m), conferir no desenho" in rel.avisos
