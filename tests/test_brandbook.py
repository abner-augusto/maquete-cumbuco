import re

from scripts.marca.brandbook import EQUIVALENTES, STATUS, html, ids_unicos
from scripts.marca.paleta import Paleta
from scripts.marca.tokens import tema

P = Paleta(ouro_claro="#E3C89C", ouro="#B38F59", bronze="#735222", creme="#EAE3D8", preto="#08090A")
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0 L10 10 Z"/></svg>'
NOMES = [f"{c}-{v}" for c in ("simbolo", "produto-vertical", "produto-horizontal", "assinatura-mae")
         for v in ("positivo", "negativo", "mono-escuro", "mono-claro")]


def _html():
    return html(P, tema(P), {n: SVG for n in NOMES}, {"Cinzel": "AAAA", "Jost": "BBBB"})


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


def test_ids_de_mascara_unicos_no_html():
    svg = '<svg><mask id="vao"/><path mask="url(#vao)"/></svg>'
    h = "".join(ids_unicos({"a": svg, "b": svg}).values())
    ids = re.findall(r'id="([^"]+)"', h)
    assert len(ids) == len(set(ids)) == 2
    assert 'url(#vao-a)' in h and 'url(#vao-b)' in h


def test_assinatura_repetida_no_html_nao_repete_id():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><mask id="vao"/><path mask="url(#vao)"/></svg>'
    h = html(P, tema(P), ids_unicos({n: svg for n in NOMES}), {"Cinzel": "AAAA", "Jost": "BBBB"})
    ids = re.findall(r'id="([^"]+)"', h)
    assert len(ids) == len(set(ids))
    assert set(re.findall(r"url\(#([^)]+)\)", h)) == set(ids)  # toda máscara referida existe
