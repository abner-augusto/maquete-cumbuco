from shapely.geometry import LineString, Polygon

from scripts.entorno.mapa import CORES, rasterizar

EXT = (0.0, 0.0, 100.0, 100.0)


def test_area_com_furo_e_via_por_cima():
    verde = Polygon([(10, 10), (90, 10), (90, 90), (10, 90)], [[(40, 40), (60, 40), (60, 60), (40, 60)]])
    via = LineString([(0, 80), (100, 80)]).buffer(3)
    img = rasterizar([("verde", verde), ("via_local", via)], EXT, 100)
    px = lambda x, y: img.getpixel((int(x), int(100 - y)))  # noqa: E731 — linha 0 é o norte
    assert px(20, 20) == CORES["verde"]
    assert px(50, 50) == CORES["solo"]  # furo
    assert px(5, 5) == CORES["solo"]
    assert px(50, 80) == CORES["via_local"]  # via por cima do verde
    assert img.size == (100, 100)
