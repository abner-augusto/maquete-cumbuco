import pytest
from shapely.geometry import Polygon

from scripts.entorno.osm import Projecao, aneis, poligono_osm, tipo_area

E0, N0 = 534600.0, 9595100.0


def test_projecao_volta_a_origem_e_ida_e_volta():
    p = Projecao(E0, N0)
    lon, lat = p.lonlat(0.0, 0.0)
    assert p.xy(lon, lat) == pytest.approx((0.0, 0.0), abs=1e-6)
    assert p.xy(*p.lonlat(1234.5, -987.0)) == pytest.approx((1234.5, -987.0), abs=1e-6)
    assert -38.70 < lon < -38.68 and -3.67 < lat < -3.65


def _geo(p, pts):
    return [{"lon": lon, "lat": lat} for lon, lat in (p.lonlat(x, y) for x, y in pts)]


def test_poligono_osm_way_fechado_e_relacao_com_furo():
    p = Projecao(E0, N0)
    quad = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    furo = [(40, 40), (60, 40), (60, 60), (40, 60), (40, 40)]
    w = poligono_osm(p, {"type": "way", "geometry": _geo(p, quad)})
    assert w.area == pytest.approx(10000, rel=1e-6)
    r = poligono_osm(p, {"type": "relation", "members": [
        {"type": "way", "role": "outer", "geometry": _geo(p, quad[:3])},
        {"type": "way", "role": "", "geometry": _geo(p, quad[2:])},
        {"type": "way", "role": "inner", "geometry": _geo(p, furo)}]})
    assert r.area == pytest.approx(10000 - 400, rel=1e-6)
    assert poligono_osm(p, {"type": "way", "geometry": _geo(p, quad[:3])}) is None  # aberto


def test_aneis_externo_e_furos():
    g = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], [[(4, 4), (6, 4), (6, 6), (4, 6)]])
    (p,) = aneis(g)
    assert len(p) == 2 and p[0][0] == [0.0, 0.0]


@pytest.mark.parametrize("tags,tipo", [
    ({"natural": "water"}, "agua"), ({"natural": "beach"}, "areia"), ({"natural": "sand"}, "areia"),
    ({"natural": "scrub"}, "verde"), ({"leisure": "park"}, "lazer"), ({"amenity": "parking"}, "estacionamento"),
    ({"landuse": "residential"}, "uso:residential"), ({"building": "yes"}, None)])
def test_tipo_area(tags, tipo):
    assert tipo_area(tags) == tipo


def test_overpass_nao_guarda_erro_de_execucao_como_resposta(tmp_path, monkeypatch):
    # o Overpass devolve 200 com "remark": "runtime error: Query timed out" e lista vazia
    import io
    import json
    import urllib.request

    from scripts.entorno import osm

    respostas = iter([{"elements": [], "remark": "runtime error: Query timed out in \"query\""},
                      {"elements": [{"type": "node", "id": 1}]}])

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: Resp(json.dumps(next(respostas)).encode()))
    monkeypatch.setattr(osm.time, "sleep", lambda s: None)
    dados = osm.overpass("[out:json];node(1);out;", tmp_path / "c.json")
    assert dados["elements"] == [{"type": "node", "id": 1}]
    assert json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))["elements"]
