import pytest

from scripts.entorno.tiles import com_margem, da_janela, janelas, linhas_de_corte

EXT = (-4050.0, -3960.0, 3990.0, 4050.0)  # recorte real (mapa.json do Plano 4)


def test_linhas_caem_em_nos_da_grade_perto_do_meio():
    xc, yc = linhas_de_corte(EXT, 30.0)
    assert (xc, yc) == (-30.0, 60.0)
    assert (xc - EXT[0]) % 30 == 0 and (yc - EXT[1]) % 30 == 0
    assert xc % 10 == 0 and yc % 10 == 0  # também nó da grade perto (10 m, múltiplos absolutos de 30)


def test_quatro_janelas_cobrem_o_recorte_sem_fresta():
    js = janelas(EXT, 30.0)
    assert sorted(js) == ["00", "01", "10", "11"]
    area = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in js.values())
    assert area == pytest.approx((EXT[2] - EXT[0]) * (EXT[3] - EXT[1]))
    assert js["00"][2] == js["10"][0] and js["00"][3] == js["01"][1]


def test_ponto_na_linha_pertence_a_uma_janela_so():
    js = janelas(EXT, 30.0)
    assert sum(da_janela(j, -30.0, 60.0) for j in js.values()) == 1


def test_margem_e_de_k_pixels_exatos():
    j = (0.0, 0.0, 4092.0, 2000.0)
    x0, y0, x1, y1 = com_margem(j, 4096, 2)
    mpp = (x1 - x0) / 4096  # rasterizar usa o lado maior
    assert (0.0 - x0) / mpp == pytest.approx(2.0)
