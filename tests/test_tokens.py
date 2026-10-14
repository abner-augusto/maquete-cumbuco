import re
from pathlib import Path

import pytest

from scripts.marca.cores import contraste, hex_para_rgb
from scripts.marca.paleta import Paleta
from scripts.marca.tokens import CHAVES, FONTES_PADRAO, css, tema

# Paleta próxima da real, com ouro claro demais para texto sobre o creme.
P = Paleta(ouro_claro="#E8C77A", ouro="#C9A45C", bronze="#8A6A2E", creme="#F3EBDD", preto="#0E0C0A")
MANOA = Path.home() / "_repos/cv_espelho_vendas/frontend/src/estilos/temas/manoa.css"


def _c(t, modo, a, b):
    return contraste(hex_para_rgb(t[modo][a]), hex_para_rgb(t[modo][b]))


def test_os_dois_modos_tem_todas_as_chaves():
    t = tema(P)
    assert set(t["claro"]) == set(CHAVES) == set(t["escuro"])


@pytest.mark.parametrize("modo", ["claro", "escuro"])
def test_contrastes_de_texto(modo):
    t = tema(P)
    assert _c(t, modo, "tinta", "papel") >= 7
    for chave in ("tinta-2", "tinta-3", "acento", "sol-texto"):
        assert _c(t, modo, chave, "papel") >= 4.5, chave
    assert _c(t, modo, "acento-contraste", "acento") >= 4.5


def test_ouro_cru_nao_vira_texto():
    t = tema(P)
    assert t["claro"]["acento"] != P.ouro and t["claro"]["sol-texto"] != P.ouro


def test_css_tem_os_dois_blocos_e_as_fontes():
    texto = css(tema(P), FONTES_PADRAO)
    assert '[data-tema="alternativa"] {' in texto
    assert '[data-tema="alternativa"][data-cor="escuro"] {' in texto
    assert '--tema-fonte-display: "Cinzel"' in texto
    assert texto.count("--tema-papel:") == 2


@pytest.mark.skipif(not MANOA.exists(), reason="repo do espelho ausente")
def test_chaves_iguais_as_do_tema_manoa():
    bloco_claro = MANOA.read_text(encoding="utf-8").split("[data-cor=")[0]
    chaves_manoa = set(re.findall(r"--tema-([a-z0-9-]+):\s*#", bloco_claro))
    assert chaves_manoa == set(CHAVES)
