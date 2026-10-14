import re
import xml.etree.ElementTree as ET

from scripts.marca.composicoes import COMPOSICOES, VARIANTES, Tipos, cores_da_variante, gerar
from scripts.marca.letreiro import fonte
from scripts.marca.paleta import Paleta

P = Paleta(ouro_claro="#E3C89C", ouro="#B38F59", bronze="#735222", creme="#EAE3D8", preto="#08090A")


def _tipos(caminho):
    tt = fonte(str(caminho), 400)
    return Tipos(serifada=tt, sans_leve=tt, sans=tt)


def _caixa(raiz):
    return [float(v) for v in raiz.get("viewBox").split()]


def test_gera_toda_composicao_em_toda_variante_mais_favicon(tmp_path, fonte_teste):
    arquivos = gerar(P, _tipos(fonte_teste), tmp_path)
    nomes = {a.name for a in arquivos}
    assert {f"{c}-{v}.svg" for c in COMPOSICOES for v in VARIANTES} | {"favicon.svg"} == nomes


def test_svgs_validos_sem_texto_e_so_com_cores_da_paleta(tmp_path, fonte_teste):
    permitidas = {P.ouro, P.ouro_claro, P.bronze, P.preto, "#FFFFFF", "white", "black"}
    for a in gerar(P, _tipos(fonte_teste), tmp_path):
        texto = a.read_text(encoding="utf-8")
        raiz = ET.fromstring(texto)
        assert not [e for e in raiz.iter() if e.tag.endswith("}text")], a.name
        cores = set(re.findall(r'(?:fill|stroke)="([^"]+)"', texto)) - {"none"}
        assert cores <= permitidas, (a.name, cores - permitidas)
        x, y, w, h = _caixa(raiz)
        assert w > 0 and h > 0


def test_proporcoes(tmp_path, fonte_teste):
    gerar(P, _tipos(fonte_teste), tmp_path)
    caixa = lambda n: _caixa(ET.parse(tmp_path / f"{n}-positivo.svg").getroot())  # noqa: E731
    _, _, w, h = caixa("produto-horizontal")
    assert w > 2 * h
    _, _, w, h = caixa("produto-vertical")
    assert h > 0.6 * w


def test_cores_da_variante():
    assert cores_da_variante(P, "positivo") == (P.ouro, P.bronze)
    assert cores_da_variante(P, "negativo") == (P.ouro_claro, P.ouro_claro)
