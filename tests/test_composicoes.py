import re
import xml.etree.ElementTree as ET

from scripts.marca.composicoes import COMPOSICOES, VARIANTES, Tipos, composicoes_da, cores_da_variante, gerar
from scripts.marca.familias import FAMILIAS
from scripts.marca.letreiro import fonte
from scripts.marca.paleta import Paleta

NIE, AME = FAMILIAS["alternativa"], FAMILIAS["americas"]
P = Paleta(ouro_claro="#E3C89C", ouro="#B38F59", bronze="#735222", creme="#EAE3D8", preto="#08090A")


def _tipos(caminho):
    tt = fonte(str(caminho), 400)
    return Tipos(serifada=tt, sans_leve=tt, sans=tt)


def _caixa(raiz):
    return [float(v) for v in raiz.get("viewBox").split()]


def test_gera_toda_composicao_em_toda_variante_mais_favicon(tmp_path, fonte_teste):
    arquivos = gerar(P, _tipos(fonte_teste), tmp_path, NIE)
    nomes = {a.name for a in arquivos}
    assert {f"{c}-{v}.svg" for c in COMPOSICOES for v in VARIANTES} | {"favicon.svg"} == nomes


def test_svgs_validos_sem_texto_e_so_com_cores_da_paleta(tmp_path, fonte_teste):
    permitidas = {P.ouro, P.ouro_claro, P.bronze, P.preto, "#FFFFFF", "white", "black"}
    for a in gerar(P, _tipos(fonte_teste), tmp_path, NIE):
        texto = a.read_text(encoding="utf-8")
        raiz = ET.fromstring(texto)
        assert not [e for e in raiz.iter() if e.tag.endswith("}text")], a.name
        cores = set(re.findall(r'(?:fill|stroke)="([^"]+)"', texto)) - {"none"}
        assert cores <= permitidas, (a.name, cores - permitidas)
        x, y, w, h = _caixa(raiz)
        assert w > 0 and h > 0


def test_proporcoes(tmp_path, fonte_teste):
    gerar(P, _tipos(fonte_teste), tmp_path, NIE)
    caixa = lambda n: _caixa(ET.parse(tmp_path / f"{n}-positivo.svg").getroot())  # noqa: E731
    _, _, w, h = caixa("produto-horizontal")
    assert w > 2 * h
    _, _, w, h = caixa("produto-vertical")
    assert h > 0.6 * w


def test_cores_da_variante():
    assert cores_da_variante(P, "positivo") == (P.ouro, P.bronze)
    assert cores_da_variante(P, "negativo") == (P.ouro_claro, P.ouro_claro)


def test_cada_svg_tem_id_de_mascara_proprio(tmp_path, fonte_teste):
    # Duas assinaturas na mesma página do site não podem repetir id (a segunda perde o vão).
    ids = []
    for a in gerar(P, _tipos(fonte_teste), tmp_path, NIE):
        ids += re.findall(r'id="([^"]+)"', a.read_text(encoding="utf-8"))
    assert len(ids) == len(set(ids))


def test_minimos_garantem_vao_visivel(fonte_teste):
    from scripts.marca.composicoes import minimos

    m = minimos(_tipos(fonte_teste), NIE)
    assert set(m) == set(COMPOSICOES)
    assert 50 <= m["simbolo"][0] <= 80  # o vão do símbolo some abaixo de ~60 px
    for nome in ("produto-horizontal", "assinatura-mae"):
        assert m[nome][0] > m["simbolo"][0]  # símbolo menor dentro da assinatura


def test_fracao_de_protecao_e_a_largura_do_pilar(fonte_teste):
    from scripts.marca.composicoes import fracao_protecao

    f = fracao_protecao(_tipos(fonte_teste), NIE)
    assert 0.01 < f < 0.2


def test_familia_americas_sem_marca_mae(tmp_path, fonte_teste):
    nomes = {a.name for a in gerar(P, _tipos(fonte_teste), tmp_path, AME)}
    assert not any(n.startswith("assinatura-mae") for n in nomes)
    assert {f"{c}-{v}.svg" for c in composicoes_da(AME) for v in VARIANTES} | {"favicon.svg"} == nomes
    assert set(COMPOSICOES) - set(composicoes_da(AME)) == {"assinatura-mae"}


def test_americas_tem_cidade_das_acima_do_nome(tmp_path, fonte_teste):
    import xml.etree.ElementTree as ET

    gerar(P, _tipos(fonte_teste), tmp_path, AME)
    gerar(P, _tipos(fonte_teste), tmp_path / "n", NIE)
    _, _, _, h_ame = _caixa(ET.parse(tmp_path / "produto-vertical-positivo.svg").getroot())
    _, _, _, h_nie = _caixa(ET.parse(tmp_path / "n" / "produto-vertical-positivo.svg").getroot())
    assert h_ame > h_nie * 0.9  # uma linha a mais (CIDADE DAS) compensa o RESIDENCIAL · CUMBUCO numa linha só
