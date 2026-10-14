"""Aritmética de cor em sRGB 8 bits e contraste WCAG 2.x."""

Cor = tuple[int, int, int]


def hex_para_rgb(h: str) -> Cor:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_para_hex(c: Cor) -> str:
    return "#{:02X}{:02X}{:02X}".format(*c)


def misturar(a: Cor, b: Cor, t: float) -> Cor:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


def _linear(canal: int) -> float:
    c = canal / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminancia(c: Cor) -> float:
    r, g, b = (_linear(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: Cor, b: Cor) -> float:
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def ajustar_contraste(cor: Cor, fundo: Cor, minimo: float) -> Cor:
    """Escurece (fundo claro) ou clareia (fundo escuro) a cor, mantendo o matiz, até o contraste mínimo."""
    alvo: Cor = (0, 0, 0) if luminancia(fundo) > 0.18 else (255, 255, 255)
    for passo in range(101):
        nova = misturar(cor, alvo, passo / 100)
        if contraste(nova, fundo) >= minimo:
            return nova
    raise ValueError(f"contraste {minimo} impossível sobre {rgb_para_hex(fundo)}")
