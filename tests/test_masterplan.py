import math

import numpy as np
import pytest
from PIL import Image
from shapely.geometry import Polygon, box

from scripts.entorno.masterplan import Semelhanca, escolher_contorno, pintar, poligonal_gleba, registrar


def _estrela(n=120):
    """Contorno radial sem simetria de rotação nem autointerseção."""
    ts = [2 * math.pi * k / n for k in range(n)]
    return np.array([((1000 + 300 * math.sin(3 * t) + 150 * math.cos(5 * t + 0.7)) * math.cos(t),
                      (1000 + 300 * math.sin(3 * t) + 150 * math.cos(5 * t + 0.7)) * math.sin(t)) for t in ts])


def test_registro_devolve_a_semelhanca_conhecida():
    destino = _estrela()
    t = Semelhanca(s=6.75, theta=math.radians(5), tx=100.0, ty=-50.0)
    origem = t.inversa(destino)  # o contorno "no PDF"
    achada, residuo = registrar(origem, destino)
    assert achada.s == pytest.approx(6.75, rel=1e-3)
    assert math.degrees(achada.theta) == pytest.approx(5.0, abs=0.05)
    assert (achada.tx, achada.ty) == pytest.approx((100.0, -50.0), abs=1.0)
    assert residuo < 0.5


def test_inversa_desfaz_aplicar():
    t = Semelhanca(2.0, 0.7, 10.0, -3.0)
    p = np.array([[1.0, 2.0], [-5.0, 4.0]])
    assert t.inversa(t.aplicar(p)) == pytest.approx(p)


def test_escolhe_o_contorno_com_a_forma_da_gleba():
    alvo = _estrela()
    quadrado = np.array([[0, 0], [3000, 0], [3000, 3000], [0, 3000]], dtype=float)
    parecido = Semelhanca(0.1, 1.0, 5.0, 5.0).aplicar(alvo)
    assert escolher_contorno([quadrado, parecido], alvo) is parecido


def test_poligonal_e_a_copia_que_contem_a_referencia():
    import ezdxf

    doc = ezdxf.new()
    m = doc.modelspace()
    anel = [(100 * math.cos(2 * math.pi * k / 674), 100 * math.sin(2 * math.pi * k / 674)) for k in range(674)]
    for dx in (0.0, 5000.0):
        m.add_lwpolyline([(x + dx + 1000, y + 1000) for x, y in anel], close=True, dxfattribs={"layer": "POLIGONAL"})
    g = poligonal_gleba(m, 1000.0, 1000.0, (0.0, 0.0))
    assert len(g) == 674 and Polygon(g).contains(Polygon([(-1, -1), (1, -1), (1, 1)]))


def test_pintar_so_dentro_da_mascara_e_apagado():
    tile = Image.new("RGB", (100, 100), (219, 204, 173))
    mp = Image.new("RGB", (100, 100), (255, 0, 0))
    meta = {"clip": [0, 0, 100, 100], "px_por_pt": 1.0, "transf": {"s": 1.0, "theta": 0.0, "tx": 0.0, "ty": 0.0}}
    # PDF com y para baixo: o ponto do mundo (x, y) é (x, -y) no PDF; a imagem cobre y de 0 a -100
    ext = (0.0, -100.0, 100.0, 0.0)
    out = pintar(tile, ext, mp, meta, box(0, -100, 50, 0), saturacao=0.35, opacidade=0.55)
    esq, dir_ = out.getpixel((25, 50)), out.getpixel((75, 50))
    assert dir_ == (219, 204, 173)
    assert esq != (219, 204, 173) and esq[0] < 255  # misturado, não vermelho puro


def test_copia_repetida_no_mesmo_lugar_conta_uma_vez():
    # revisão: o R05 tem a poligonal duas vezes, idêntica, no referencial da topografia
    import ezdxf

    doc = ezdxf.new()
    m = doc.modelspace()
    anel = [(100 * math.cos(2 * math.pi * k / 674), 100 * math.sin(2 * math.pi * k / 674)) for k in range(674)]
    for _ in range(2):
        m.add_lwpolyline([(x + 1000, y + 1000) for x, y in anel], close=True, dxfattribs={"layer": "POLIGONAL"})
    assert len(poligonal_gleba(m, 1000.0, 1000.0, (0.0, 0.0))) == 674


def test_registro_aguenta_contorno_percorrido_duas_vezes():
    # revisão: no PDF real o caminho da gleba repete pontos e se autointercepta; a área bruta dobrava
    destino = _estrela()
    t = Semelhanca(s=4.8, theta=math.radians(90), tx=10.0, ty=20.0)
    origem = t.inversa(destino)
    achada, residuo = registrar(np.vstack([origem, origem]), destino)
    assert achada.s == pytest.approx(4.8, rel=1e-3) and residuo < 0.5


def test_raster_e_vetor_no_mesmo_espaco_em_pagina_girada():
    # revisão: a página do MASTER URBANO.pdf tem /Rotate 270; o vetor vinha sem giro e o raster girado
    import pymupdf

    from scripts.entorno.masterplan import caminhos_fechados, rasterizar_contorno

    doc = pymupdf.open()
    pagina = doc.new_page(width=400, height=300)
    pts = [pymupdf.Point(50 + 40 * math.cos(2 * math.pi * k / 60), 200 + 40 * math.sin(2 * math.pi * k / 60))
           for k in range(60)]
    pagina.draw_polyline(pts + [pts[0]], color=(0, 0, 0), fill=(1, 0, 0), closePath=True)
    pagina.set_rotation(270)
    img, clip = rasterizar_contorno(pagina, 2.0)
    (contorno,) = caminhos_fechados(pagina)
    cx, cy = contorno.mean(0)
    u, v = int((cx - clip[0]) * 2.0), int((cy - clip[1]) * 2.0)
    r, g, b = img.getpixel((u, v))
    assert r > 200 and g < 60 and b < 60  # o centro do contorno é o vermelho do desenho
