import pytest
from PIL import Image

from scripts.marcos.dados import estande_do_kmz, faltantes, reduzir

KML = """<kml><Document><Placemark><name>Lote</name><Polygon><outerBoundaryIs><LinearRing>
<coordinates>-38.1,-3.1,0 -38.2,-3.1,0 -38.2,-3.2,0 -38.1,-3.1,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
<Placemark><name>Estande (edificacao)</name><Polygon><outerBoundaryIs><LinearRing>
<coordinates>-38.68711576,-3.66149433,0 -38.68725579,-3.66135343,0 -38.68716805,-3.66124869,0 -38.68711576,-3.66149433,0</coordinates>
</LinearRing></outerBoundaryIs></Polygon></Placemark></Document></kml>"""


def test_estande_e_o_poligono_da_edificacao():
    pts = estande_do_kmz(KML)
    assert pts[0] == pytest.approx((-38.68711576, -3.66149433)) and len(pts) == 3  # sem repetir o 1º


def test_reduzir_ate_1600_no_lado_maior(tmp_path):
    Image.new("RGB", (4000, 2000), (10, 20, 30)).save(tmp_path / "a.jpg")
    reduzir(tmp_path / "a.jpg", tmp_path / "b.jpg")
    assert Image.open(tmp_path / "b.jpg").size == (1600, 800)


def test_faltantes_lista_todos(tmp_path):
    (tmp_path / "ok.jpg").write_bytes(b"x")
    cur = {"clube": {"fotos": [{"arquivo": "ok.jpg"}, {"arquivo": "nao1.jpg"}]},
           "portaria": {"fotos": [{"arquivo": "nao2.jpg"}]}}
    assert faltantes(cur, tmp_path) == ["nao1.jpg", "nao2.jpg"]
