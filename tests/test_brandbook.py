import re

from scripts.marca.brandbook import EQUIVALENTES, STATUS, html
from scripts.marca.familias import FAMILIAS
from scripts.marca.paleta import Paleta
from scripts.marca.tokens import tema

P = Paleta(ouro_claro="#E3C89C", ouro="#B38F59", bronze="#735222", creme="#EAE3D8", preto="#08090A")
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0 L10 10 Z"/></svg>'
NOMES = [f"{c}-{v}" for c in ("simbolo", "produto-vertical", "produto-horizontal", "assinatura-mae")
         for v in ("positivo", "negativo", "mono-escuro", "mono-claro")]


MINIMOS = {"simbolo": (60, 12), "produto-vertical": (90, 20), "produto-horizontal": (180, 40), "assinatura-mae": (170, 38)}


def _html(svgs=None, familia="alternativa"):
    return html(P, tema(P), svgs or {n: SVG for n in NOMES}, {"Cinzel": "AAAA", "Jost": "BBBB"}, MINIMOS, 0.1, FAMILIAS[familia])


def test_tem_as_oito_secoes():
    h = _html()
    for titulo in ("Arquitetura de marca", "Versões", "Área de proteção", "Tamanho mínimo",
                   "Usos incorretos", "Paleta", "Tipografia", "Cores de status"):
        assert f">{titulo}<" in h, titulo


def test_cores_status_e_equivalentes():
    h = _html()
    for c in (P.ouro_claro, P.ouro, P.bronze, P.creme, P.preto, *STATUS.values()):
        assert c in h
    for profissional in EQUIVALENTES.values():
        assert profissional in h


def test_autocontido_e_confidencial():
    h = _html()
    assert "http://" not in h.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "https://" not in h
    assert '<meta name="robots" content="noindex, nofollow">' in h
    assert "@font-face" in h and "data:font/ttf;base64,AAAA" in h


def test_assinatura_repetida_no_html_nao_repete_id():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><mask id="vao"/><path mask="url(#vao)"/></svg>'
    h = _html({n: svg for n in NOMES})
    ids = re.findall(r'id="([^"]+)"', h)
    assert len(ids) == len(set(ids))
    assert set(re.findall(r"url\(#([^)]+)\)", h)) == set(ids)  # toda máscara referida existe


def test_tamanho_minimo_vem_da_geometria():
    h = _html()
    assert "<td>60 px</td><td>12 mm</td>" in h and "<td>180 px</td><td>40 mm</td>" in h


def test_area_de_protecao_desenhada_com_x():
    # x = 10% da largura da assinatura → padding p = x/(1+2x) da caixa tracejada
    assert "padding:8.33%" in _html()


def test_brandbook_da_familia_ativa_nao_cita_alternativa():
    minimos = {k: v for k, v in MINIMOS.items() if k != "assinatura-mae"}
    nomes = [n for n in NOMES if not n.startswith("assinatura-mae")]
    h = html(P, tema(P), {n: SVG for n in nomes}, {"Cinzel": "AAAA", "Jost": "BBBB"}, minimos, 0.1, FAMILIAS["americas"])
    assert "alternativa" not in h.lower()
    assert "Cidade das Américas" in h
