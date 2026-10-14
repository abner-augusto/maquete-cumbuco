"""SIRGAS 2000 / UTM 24S e a origem local da cena (x = leste, y = norte, em metros)."""

CRS = "EPSG:31984"


class GeorrefErro(Exception):
    pass


def parece_utm_24s(ext: tuple[float, float, float, float]) -> bool:
    xmin, ymin, xmax, ymax = ext
    return 166_000 <= xmin <= xmax <= 834_000 and 9_400_000 <= ymin <= ymax <= 9_800_000


def origem(ext: tuple[float, float, float, float]) -> tuple[float, float]:
    xmin, ymin, xmax, ymax = ext
    return (round((xmin + xmax) / 2, -2), round((ymin + ymax) / 2, -2))


def para_local(pts, e0: float, n0: float) -> list[list[float]]:
    return [[round(x - e0, 2), round(y - n0, 2)] for x, y in pts]


def georref_json(e0: float, n0: float) -> dict:
    return {"crs": CRS, "origem": {"E": e0, "N": n0}}
