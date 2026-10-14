import json

import numpy as np
from PIL import Image

from scripts.marca.cores import hex_para_rgb, luminancia
from scripts.marca.paleta import FONTES_LOGO, FONTES_OURO, FONTES_PRETO, Paleta, medir

CREME, PRETO = (243, 235, 221), (14, 12, 10)
OURO_ESCURO, OURO_CLARO = (138, 106, 46), (232, 199, 122)


def _imagem(fundo, com_ouro=True, realce=False):
    a = np.zeros((200, 200, 3), dtype=np.uint8)
    a[:, :] = fundo
    if com_ouro:
        for i in range(100):  # gradiente de ouro escuro a ouro claro
            t = i / 99
            a[100:, i * 2 : i * 2 + 2] = [round(x + (y - x) * t) for x, y in zip(OURO_ESCURO, OURO_CLARO)]
    if realce:
        a[100:110, :] = (255, 252, 240)  # brilho especular quase branco
    return Image.fromarray(a)


def _perto(hex_cor, rgb, tol=4):
    return max(abs(a - b) for a, b in zip(hex_para_rgb(hex_cor), rgb)) <= tol


def test_mede_creme_preto_e_ouros_em_ordem():
    p = medir([_imagem(CREME)], [_imagem(PRETO, com_ouro=False)])
    assert _perto(p.creme, CREME)
    assert _perto(p.preto, PRETO)
    l = [luminancia(hex_para_rgb(c)) for c in (p.bronze, p.ouro, p.ouro_claro)]
    assert l[0] < l[1] < l[2]


def test_realce_quase_branco_nao_vira_ouro_claro():
    p = medir([_imagem(CREME, realce=True)], [_imagem(PRETO, com_ouro=False)])
    assert luminancia(hex_para_rgb(p.ouro_claro)) <= luminancia(OURO_CLARO) + 0.01


def test_sem_imagem_escura_explica():
    import pytest

    with pytest.raises(ValueError, match="preto"):
        medir([_imagem(CREME)], [])


def test_paleta_ida_e_volta(tmp_path):
    p = Paleta("#E8C77A", "#C9A45C", "#8A6A2E", "#F3EBDD", "#0E0C0A")
    destino = tmp_path / "paleta.json"
    destino.write_text(json.dumps(p.para_json()), encoding="utf-8")
    assert Paleta.carregar(destino) == p


def test_fontes_tem_o_produto_e_os_seis_estudos():
    assert set(FONTES_LOGO) == {"P0", "E1", "E2", "E3", "E4", "E5", "E6"}
    assert FONTES_LOGO["P0"].endswith("LOGO Preliminar.jpeg")


def test_cena_de_fundo_nao_entra_no_ouro():
    # Os estudos E1–E4 têm parede de pedra e céu de pôr do sol: o ouro sai só do P0.
    assert FONTES_OURO == ("P0",)
    assert set(FONTES_PRETO) == {"E5", "E6"}
    parede = _imagem((186, 149, 116), com_ouro=False)
    p = medir([_imagem(CREME)], [_imagem(PRETO, com_ouro=False), parede])
    assert _perto(p.preto, PRETO)
