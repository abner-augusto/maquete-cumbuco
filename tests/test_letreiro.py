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


def test_glifo_ausente_explica(fonte_teste):
    with pytest.raises(ValueError, match="glifo ausente: 'é'"):
        contorno(fonte(str(fonte_teste), 400), "Aé", 100)
