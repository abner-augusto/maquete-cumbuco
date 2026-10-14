import xml.etree.ElementTree as ET

from PIL import Image

from scripts.loteamento.geometria import contem
from scripts.marca.simbolo import LARGURA, Parametros, _curva_topo, formas, raster, sobrepor, svg_simbolo

P = Parametros()


def test_caixa_do_simbolo():
    pts = [pt for f in formas(P).values() for pt in f]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    assert min(xs) >= 0 and max(xs) <= LARGURA + 1e-6
    assert min(ys) >= 0 and max(ys) == P.pilar_topo


def test_topo_da_perna_fica_dentro_da_fita():
    assert contem(formas(P)["fita"], P.perna_topo)


def test_pilar_nasce_atras_da_fita_com_vao():
    # No E5 o pilar não desce até a base: some atrás da fita, separado dela por um vão.
    img = raster(P, int(LARGURA))
    x = P.pilar_x[1] - P.pilar_face / 2  # na face larga (o meio do pilar é vazado)
    topo = min(_curva_topo(P), key=lambda pt: abs(pt[0] - x))  # borda de cima da fita nesse x
    linha = lambda y: int(P.pilar_topo - y)  # noqa: E731 — raster tem y para baixo
    assert img.getpixel((int(x), linha(topo[1] - 3))) == 255  # fita
    assert img.getpixel((int(x), linha(topo[1] + P.vao / 2))) == 0  # vão
    assert img.getpixel((int(x), linha(topo[1] + 3 * P.vao))) == 255  # pilar
    abaixo = topo[1] - P.espessura_maxima(x) - 3 * P.vao
    if abaixo >= 2:  # onde a fita ainda não chegou ao chão
        assert img.getpixel((int(x), linha(abaixo))) == 0  # nada do pilar abaixo da fita


def test_svg_valido_com_mascara_e_sem_texto():
    frag = svg_simbolo(P, "#B38F59")
    doc = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {P.pilar_topo:g}">{frag}</svg>'
    raiz = ET.fromstring(doc)
    tags = {e.tag.split("}")[1] for e in raiz.iter()}
    assert "mask" in tags and "text" not in tags
    assert "#B38F59" in frag


def test_sobrepor_tinge_a_mascara():
    ref = Image.new("RGB", (10, 10), (255, 255, 255))
    m = Image.new("L", (10, 10), 0)
    m.putpixel((2, 2), 255)
    out = sobrepor(ref, m)
    r, g, b = out.getpixel((2, 2))[:3]
    assert r > g and r > b
    assert out.getpixel((5, 5))[:3] != (r, g, b)


# Revisão visual do Abner (14/10): mais leve — pilar vazado (lâmina curvada do E5).


def _px(img, x, y):
    return img.getpixel((int(x), int(P.pilar_topo - y)))


def test_pilar_vazado_com_parede_fina_e_face_larga():
    img = raster(P, int(LARGURA))
    x0, x1 = P.pilar_x
    y = P.pilar_ombro - 20
    assert _px(img, x0 + P.pilar_parede / 2, y) == 255  # parede esquerda
    assert _px(img, x0 + P.pilar_parede + 10, y) == 0  # vazio
    assert _px(img, x1 - P.pilar_face / 2, y) == 255  # face direita
    assert _px(img, x0 + 20, P.pilar_topo - P.pilar_topo_espessura / 2) == 255  # faixa do topo


def test_arco_da_esquerda_fica_aberto():
    # Revisão do Abner (14/10): o traço do pé e a linha de base pesaram; o canto esquerdo é só a fita.
    img = raster(P, int(LARGURA))
    for x in (60, 100, 200, 300):
        assert _px(img, x, 1.5) == 0, x
    assert "base" not in formas(P) and "traco" not in formas(P)
