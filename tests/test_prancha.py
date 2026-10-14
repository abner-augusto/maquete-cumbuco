import numpy as np
from PIL import Image

from scripts.comum.ambiente import RAIZ
from scripts.marca.paleta import FONTES_LOGO, Paleta
from scripts.marca.prancha import DESTINO, html_prancha, miniatura
from scripts.marca.tokens import tema

P = Paleta(ouro_claro="#E8C77A", ouro="#C9A45C", bronze="#8A6A2E", creme="#F3EBDD", preto="#0E0C0A")


def test_miniatura_abre_nome_com_espaco_parenteses_e_acento(tmp_path):
    pasta = tmp_path / "Estudo Logo João Carlos"
    pasta.mkdir()
    arq = pasta / "WhatsApp Image 2026-10-14 at 11.05.31 (1).jpeg"
    Image.fromarray(np.full((50, 80, 3), 200, dtype=np.uint8)).save(arq)
    assert miniatura(arq).startswith("data:image/jpeg;base64,")


def test_html_tem_todos_os_insumos_cores_e_fontes():
    imagens = {i: "data:image/jpeg;base64,AAAA" for i in FONTES_LOGO}
    html = html_prancha(imagens, P, tema(P))
    for i in FONTES_LOGO:
        assert f">{i}<" in html
    for cor in (P.ouro_claro, P.ouro, P.bronze, P.creme, P.preto):
        assert cor in html
    for fonte in ("Cinzel", "Marcellus", "Jost", "Montserrat"):
        assert fonte in html
    assert "Combinação A" in html and "Combinação C" in html


def test_prancha_nao_vaza():
    html = html_prancha({i: "data:," for i in FONTES_LOGO}, P, tema(P))
    assert '<meta name="robots" content="noindex, nofollow">' in html
    DESTINO.relative_to(RAIZ / "cache")  # levanta ValueError se sair de cache/
    assert "cache/" in (RAIZ / ".gitignore").read_text(encoding="utf-8")
