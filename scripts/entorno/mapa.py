"""Mapa do chão: vias e áreas do OSM pintadas numa imagem aplicada por UV ao relevo."""

from PIL import Image, ImageDraw

# Cores de cena (ambiente, não marca), sRGB. O solo é a cor do terreno do Blender (0.86, 0.80, 0.68).
CORES = {
    "solo": (219, 204, 173),
    "urbano": (206, 196, 178),  # bairros na orla regional (landuse residencial, comercial, industrial)
    "verde": (171, 180, 138),
    "lazer": (178, 190, 142),
    "areia": (234, 223, 195),
    "agua": (122, 160, 168),
    "estacionamento": (200, 195, 184),
    "via_local": (160, 156, 150),
    "via_principal": (118, 116, 118),
}


def _partes(geom):
    return [p for p in getattr(geom, "geoms", [geom]) if p.geom_type == "Polygon" and not p.is_empty]


def rasterizar(camadas: list[tuple[str, object]], ext: tuple[float, float, float, float], px: int) -> Image.Image:
    """Camadas de baixo para cima; cada uma com a cor de CORES[nome]. `px` é o lado maior."""
    x0, y0, x1, y1 = ext
    escala = px / max(x1 - x0, y1 - y0)
    tam = (round((x1 - x0) * escala), round((y1 - y0) * escala))
    img = Image.new("RGB", tam, CORES["solo"])
    para_px = lambda coords: [((x - x0) * escala, (y1 - y) * escala) for x, y in coords]  # noqa: E731
    for nome, geom in camadas:
        mascara = Image.new("1", tam, 0)
        dr = ImageDraw.Draw(mascara)
        for p in _partes(geom):
            dr.polygon(para_px(p.exterior.coords), fill=1)
            for furo in p.interiors:
                dr.polygon(para_px(furo.coords), fill=0)
        img.paste(CORES[nome], (0, 0, *tam), mascara)
    return img
