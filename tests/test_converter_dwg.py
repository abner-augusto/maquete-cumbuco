from pathlib import Path

from scripts.loteamento.converter_dwg import FONTES, script_dxfout


def test_script_dxfout_exporta_2013_com_precisao_maxima():
    scr = script_dxfout(Path(r"C:\cache\dxf\planta-venda.dxf"))
    linhas = scr.splitlines()
    assert linhas[0] == "FILEDIA 0"
    assert linhas[1] == '_.DXFOUT "C:\\cache\\dxf\\planta-venda.dxf" _V 2013 16'
    assert scr.isascii()


def test_fontes_apontam_para_dwg_do_urbanismo():
    assert FONTES["planta-venda"] == "6-PROJETOS/01-URBANISMO/DWG/PLANTA VENDA.dwg"
    assert FONTES["masterplan-r05"].endswith("MASTERPLAN GERAL-R05,.dwg")
