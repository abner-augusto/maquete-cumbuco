import pytest

from scripts.marca.letreiro import contorno, fonte


def test_largura_altura_e_eixo_y_do_svg(fonte_teste):
    l = contorno(fonte(str(fonte_teste), 400), "AB", 100)
    assert l.largura == pytest.approx(120)
    assert l.altura_maiuscula == pytest.approx(70)
    assert l.d.startswith("M") and "-70" in l.d  # topo da letra acima da linha de base


def test_espacamento_entre_letras_nao_depois_da_ultima(fonte_teste):
    tt = fonte(str(fonte_teste), 400)
    assert contorno(tt, "AB", 100, 0.5).largura == pytest.approx(120 + 50)
    assert contorno(tt, "A B", 100, 0.5).largura == pytest.approx(60 + 30 + 60 + 2 * 50)


def test_topo_e_a_tinta_mais_alta(fonte_teste):
    assert contorno(fonte(str(fonte_teste), 400), "AB", 100).topo == pytest.approx(70)


def test_acento_passa_da_altura_das_maiusculas():
    from scripts.marca.fontes import PASTA

    cinzel = PASTA / "Cinzel[wght].ttf"
    if not cinzel.exists():
        pytest.skip("fontes reais não baixadas")
    l = contorno(fonte(str(cinzel), 400), "AMÉRICAS", 100)
    assert l.topo > l.altura_maiuscula + 5


def test_glifo_ausente_explica(fonte_teste):
    with pytest.raises(ValueError, match="glifo ausente: 'é'"):
        contorno(fonte(str(fonte_teste), 400), "Aé", 100)
