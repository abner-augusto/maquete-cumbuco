import pytest

from scripts.entorno.osm import Projecao
from scripts.pontos.pontos import (distancia_m, escolher_osm, faixa, galeria, grafo_carro, licenca_livre, minutos,
                                   slug)

P = Projecao(534600.0, 9595100.0)


def test_escolher_osm_pega_o_mais_perto_e_recusa_homonimo_longe():
    rs = [{"lat": "-3.60", "lon": "-38.80", "osm_type": "way", "osm_id": 1},
          {"lat": "-3.6601", "lon": "-38.6901", "osm_type": "node", "osm_id": 2}]
    assert escolher_osm(rs, -3.66, -38.69)["osm_id"] == 2
    assert escolher_osm(rs[:1], -3.66, -38.69) is None  # a 15 km: outro lugar com o mesmo nome


@pytest.mark.parametrize("nome,livre", [
    ("CC BY-SA 4.0", True), ("CC BY 2.0", True), ("CC0", True), ("Public domain", True),
    ("CC BY-NC-SA 4.0", False), ("CC BY-ND 3.0", False), ("Copyrighted", False), ("", False)])
def test_licenca_livre(nome, livre):
    assert licenca_livre(nome) is livre


def test_faixa_e_distancia():
    assert faixa(2999) == "proximo" and faixa(3001) == "distante"
    assert distancia_m(-3.66, -38.69, -3.66, -38.68) == pytest.approx(1110, rel=0.01)


def _way(i, nos, pts, highway="primary", **tags):
    return {"type": "way", "id": i, "nodes": nos, "tags": {"highway": highway, **tags},
            "geometry": [{"lon": lon, "lat": lat} for lon, lat in (P.lonlat(x, y) for x, y in pts)]}


def test_minutos_de_carro_pelo_grafo_com_mao_unica():
    elementos = [_way(1, [1, 2], [(0, 0), (5000, 0)]),  # 5 km a 50 km/h = 6 min
                 _way(2, [2, 3], [(5000, 0), (5000, 1000)], oneway="yes")]  # 1 km só para o norte
    xy, g = grafo_carro(elementos, P)
    assert minutos(g, xy, (0, 0), (5000, 0)) == 6 + 1  # + 1 min de manobra
    assert minutos(g, xy, (0, 0), (5000, 1000)) == 9  # 6 + 1,2 + 1 = 8,2, arredondado para cima
    assert minutos(g, xy, (5000, 1000), (0, 0)) is None  # contramão, sem rota


def test_galeria_mostra_credito_e_licenca():
    html = galeria({"Praia do Cumbuco": [{"titulo": "File:A.jpg", "miniatura": "https://x/a.jpg",
                                          "autor": "Fulano", "licenca": "CC BY-SA 4.0", "pagina": "https://c/A"}]})
    assert "Praia do Cumbuco" in html and "File:A.jpg" in html and "CC BY-SA 4.0" in html and "Fulano" in html


def test_slug():
    assert slug("Lagoa do Cauípe") == "lagoa-do-cauipe"


def test_ponto_pendente_fica_fora_e_e_listado():
    from scripts.pontos.pontos import separar_pendentes

    prontos, pendentes = separar_pendentes([{"nome": "A"}, {"nome": "B", "pendente": "sem elemento no OSM"}])
    assert [p["nome"] for p in prontos] == ["A"] and pendentes == ["B: sem elemento no OSM"]


def test_minutos_usa_o_no_alcancavel_mais_perto_e_ponta_de_carro():
    # o nó mais perto do Vila Galé ficava num trecho solto da malha: "sem rota"
    elementos = [_way(1, [1, 2], [(0, 0), (5000, 0)]),
                 _way(2, [3, 4], [(5000, 1000), (5000, 1100)], highway="residential")]  # solto
    xy, g = grafo_carro(elementos, P)
    # 6 min no grafo + 900 m de ponta a 25 km/h (2,16 min) + 1 de manobra = 9,16 → 10
    assert minutos(g, xy, (0, 0), (5000, 900)) == 10


def test_ponto_do_elemento_fica_dentro_da_area_nao_no_centro_da_caixa():
    # revisão final: o "out center" da praia do Icaraí caía no mar (centro da caixa de uma faixa curva)
    from shapely.geometry import Point, Polygon

    from scripts.pontos.pontos import ponto_do_elemento

    ele = [(0, 0), (1000, 0), (1000, 50), (50, 50), (50, 1000), (0, 1000), (0, 0)]  # faixa em L
    el = {"type": "way", "geometry": [{"lon": lon, "lat": lat} for lon, lat in (P.lonlat(x, y) for x, y in ele)]}
    lon, lat = ponto_do_elemento(P, el)
    assert Polygon(ele).contains(Point(P.xy(lon, lat)))
    assert ponto_do_elemento(P, {"type": "node", "lon": -38.7, "lat": -3.66}) == (-38.7, -3.66)


def test_ponto_do_elemento_em_terra():
    # a faixa de praia do OSM é estreita e o Copernicus põe parte dela no mar: o pino precisa de terra
    from shapely.geometry import Point, Polygon

    from scripts.pontos.pontos import ponto_do_elemento

    ele = [(0, 0), (1000, 0), (1000, 50), (50, 50), (50, 1000), (0, 1000), (0, 0)]
    el = {"type": "way", "geometry": [{"lon": lon, "lat": lat} for lon, lat in (P.lonlat(x, y) for x, y in ele)]}
    lon, lat = ponto_do_elemento(P, el, em_terra=lambda x, y: y > 500)  # só o braço vertical é terra
    x, y = P.xy(lon, lat)
    assert Polygon(ele).contains(Point(x, y)) and y > 500


def test_coordenada_lida_no_satelite_dispensa_o_osm():
    from scripts.pontos.pontos import coordenada_osm

    p = {"nome": "Parque", "ref_lat": -3.6340, "ref_lon": -38.7117,
         "satelite": {"lat": -3.633971, "lon": -38.711931, "imagem": "Esri World Imagery z18", "data": "2026-10-15"}}
    c = coordenada_osm(p, P)
    assert (c["lat"], c["lon"], c["osm_type"], c["fonte"]) == (-3.633971, -38.711931, None, "satelite")


def test_coordenada_do_satelite_longe_da_referencia_e_recusada():
    from scripts.pontos.pontos import coordenada_osm

    p = {"nome": "Parque", "ref_lat": -3.6340, "ref_lon": -38.7117,
         "satelite": {"lat": -3.6640, "lon": -38.7117, "imagem": "Esri World Imagery z18", "data": "2026-10-15"}}
    with pytest.raises(SystemExit, match="satelite"):
        coordenada_osm(p, P)  # 3,3 km: digitação errada, não o lugar


def test_ponto_do_elemento_perto_da_referencia():
    # a praia do Cumbuco é uma faixa de 8 km: o pino vai ao trecho que a curadoria aponta (referência do
    # Google), em terra, e não a um ponto qualquer da faixa (o representative_point caía 7 km a oeste)
    from shapely.geometry import Point, Polygon

    from scripts.pontos.pontos import ponto_do_elemento

    ele = [(0, 0), (1000, 0), (1000, 50), (50, 50), (50, 1000), (0, 1000), (0, 0)]
    el = {"type": "way", "geometry": [{"lon": lon, "lat": lat} for lon, lat in (P.lonlat(x, y) for x, y in ele)]}
    x, y = P.xy(*ponto_do_elemento(P, el, ref=(25, 950)))
    assert Polygon(ele).contains(Point(x, y)) and abs(x - 25) < 10 and abs(y - 950) < 10
    # referência no braço horizontal, que está no mar: o pino fica no ponto de terra mais perto dela
    x, y = P.xy(*ponto_do_elemento(P, el, em_terra=lambda x, y: y > 500, ref=(900, 25)))
    assert Polygon(ele).contains(Point(x, y)) and 500 <= y < 520


def test_credito_sem_prefixo_user():
    # o Commons devolve "User:Fulano" para quem não preencheu o campo autor: na legenda sai só o nome
    from scripts.pontos.pontos import credito

    assert credito("User:Eduardo P") == "Eduardo P"
    assert credito("Boris Karpuk") == "Boris Karpuk"
    assert credito("") == ""


def test_foto_externa_baixa_reduz_e_leva_o_credito(tmp_path, monkeypatch):
    from io import BytesIO

    from PIL import Image

    from scripts.pontos import pontos

    buf = BytesIO()
    Image.new("RGB", (3200, 1600), (10, 20, 30)).save(buf, "JPEG")

    class Resposta(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(pontos, "FOTOS", tmp_path)
    monkeypatch.setattr(pontos.urllib.request, "urlopen", lambda req, timeout: Resposta(buf.getvalue()))
    p = {"nome": "Hotel Teste", "foto_externa": {"url": "https://x/a.jpg", "credito": "Hotel Teste (divulgação)",
                                                  "pagina": "https://x/"}}
    r = pontos.baixar_externa(p)
    assert Image.open(tmp_path / "hotel-teste.jpg").size == (1600, 800)
    assert r == {"foto": "pontos/fotos/hotel-teste.jpg", "credito": "Hotel Teste (divulgação)", "licenca": None,
                 "licenca_url": None, "fonte_foto": "https://x/"}
