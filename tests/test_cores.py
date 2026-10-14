import pytest

from scripts.marca.cores import ajustar_contraste, contraste, hex_para_rgb, luminancia, misturar, rgb_para_hex


def test_hex_ida_e_volta():
    assert hex_para_rgb("#c9a45c") == (201, 164, 92)
    assert rgb_para_hex((201, 164, 92)) == "#C9A45C"


def test_misturar():
    assert misturar((0, 0, 0), (255, 255, 255), 0.5) == (128, 128, 128)
    assert misturar((10, 20, 30), (200, 200, 200), 0.0) == (10, 20, 30)


def test_contraste_wcag():
    assert luminancia((255, 255, 255)) == pytest.approx(1.0)
    assert contraste((0, 0, 0), (255, 255, 255)) == pytest.approx(21.0)
    assert contraste((119, 119, 119), (255, 255, 255)) == pytest.approx(4.48, abs=0.01)


def test_ajustar_escurece_sobre_fundo_claro():
    ouro, creme = (201, 164, 92), (243, 235, 221)
    assert contraste(ouro, creme) < 4.5
    novo = ajustar_contraste(ouro, creme, 4.5)
    assert contraste(novo, creme) >= 4.5
    assert luminancia(novo) < luminancia(ouro)


def test_ajustar_clareia_sobre_fundo_escuro():
    bronze, preto = (120, 90, 40), (17, 15, 12)
    novo = ajustar_contraste(bronze, preto, 4.5)
    assert contraste(novo, preto) >= 4.5
    assert luminancia(novo) > luminancia(bronze)


def test_ajustar_nao_mexe_quando_ja_passa():
    assert ajustar_contraste((0, 0, 0), (255, 255, 255), 4.5) == (0, 0, 0)
