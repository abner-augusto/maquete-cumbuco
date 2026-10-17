import json

import numpy as np
import pytest
from PIL import Image
from scipy import ndimage

from scripts.fases.fases import CURADORIA, IMAGEM, achar_recorte, correlacao


def _pagina(semente=3, forma=(400, 600)) -> np.ndarray:
    """Uma 'página' de manchas suaves e traços, sem repetição, para a correlação ter um só pico."""
    r = np.random.default_rng(semente)
    return ndimage.gaussian_filter(r.random(forma), 4) * 255 + ndimage.gaussian_filter(r.random(forma), 1) * 60


def test_correlacao_acha_o_molde_onde_ele_foi_cortado():
    pagina = _pagina()
    molde = pagina[120:220, 250:370]
    m = correlacao(pagina, molde)
    i, j = np.unravel_index(np.argmax(m), m.shape)
    assert (j, i) == (250, 120) and m[i, j] == pytest.approx(1.0, abs=1e-3)


def test_achar_recorte_recupera_escala_e_posicao():
    pagina = _pagina(forma=(500, 800))
    # o recorte vive em pixels próprios: a página o vê 1,2 vez maior (escala 1,2) a partir de (210, 90)
    caixa = pagina[90:90 + 180, 210:210 + 240]
    recorte = Image.fromarray(caixa.clip(0, 255).astype("uint8")).resize((200, 150), Image.LANCZOS)
    reg = achar_recorte(pagina, recorte)
    assert reg.escala == pytest.approx(1.2, abs=0.03)
    assert (reg.x, reg.y) == pytest.approx((210, 90), abs=4)
    assert reg.correlacao > 0.9


def test_curadoria_nao_traz_a_fase_1_e_cada_ponto_cai_dentro_da_imagem():
    fases = json.loads(CURADORIA.read_text(encoding="utf-8"))["fases"]
    ids = [f["id"] for f in fases]
    assert 1 not in ids and len(set(ids)) == len(ids) and ids == sorted(ids)
    largura, altura = Image.open(IMAGEM).size
    assert all(0 <= f["x"] < largura and 0 <= f["y"] < altura for f in fases)
