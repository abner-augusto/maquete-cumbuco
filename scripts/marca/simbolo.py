"""Símbolo de arco e pilar (estudo E5), redesenhado por parâmetros.

Unidades: largura 1000, y para cima a partir da base. Ajuste um número em Parametros e rode de novo;
a sobreposição com o E5 sai em cache/marca/comparacao-simbolo.png.
Uso: uv run python -m scripts.marca.simbolo
"""

import math
import sys
from dataclasses import dataclass

from PIL import Image, ImageDraw

from scripts.comum.ambiente import RAIZ, terreno_dir

Ponto = tuple[float, float]
LARGURA = 1000.0
CAIXA_E5 = (352, 144, 1154, 452)  # x0, y0, x1, y1 em px da imagem do E5
COMPARACAO = RAIZ / "cache" / "marca" / "comparacao-simbolo.png"


@dataclass(frozen=True)
class Parametros:
    crista: Ponto = (384.0, 237.0)
    ctrl_subida: tuple[Ponto, Ponto] = ((150.0, 140.0), (260.0, 237.0))
    ctrl_descida: tuple[Ponto, Ponto] = ((560.0, 237.0), (720.0, 40.0))
    espessura_pe: float = 3.0
    espessura_pico: float = 70.0  # a face larga da fita na descida, no E5
    pico_u: float = 0.75  # posição do pico ao longo da fita (0 = pé esquerdo, 0,5 = crista, 1 = pé direito)
    expoente_subida: float = 8.0  # quanto maior, mais fina a fita antes do pico
    expoente_descida: float = 1.5
    perna_topo: Ponto = (495.0, 205.0)  # dentro da fita
    perna_largura_topo: float = 12.0
    perna_pe: float = 424.0  # x onde a perna toca a base
    perna_aba: float = 279.0  # x onde a aba da perna termina na base
    pilar_x: tuple[float, float] = (638.0, 808.0)
    pilar_topo: float = 384.0
    pilar_ombro: float = 300.0  # altura do lado direito do pilar; o topo desce em quarto de elipse
    vao: float = 9.0  # recorte entre a fita e o pilar

    def espessura(self, u: float) -> float:
        """Espessura da fita no parâmetro u ∈ [0, 1]: fina na subida e na crista, larga na descida."""
        if u <= self.pico_u:
            w, expoente = u / (2 * self.pico_u), self.expoente_subida
        else:
            w, expoente = 0.5 + (u - self.pico_u) / (2 * (1 - self.pico_u)), self.expoente_descida
        return self.espessura_pe + (self.espessura_pico - self.espessura_pe) * math.sin(math.pi * w) ** expoente

    def espessura_maxima(self, x: float) -> float:
        """Espessura da fita perto da abscissa x (para o teste do vão)."""
        topo = _curva_topo(self)
        i = min(range(len(topo)), key=lambda k: abs(topo[k][0] - x))
        return self.espessura(i / (len(topo) - 1))


def _bezier(p0: Ponto, p1: Ponto, p2: Ponto, p3: Ponto, n: int) -> list[Ponto]:
    pts = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t**2, t**3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return pts


def _curva_topo(p: Parametros, n: int = 120) -> list[Ponto]:
    subida = _bezier((0.0, 0.0), *p.ctrl_subida, p.crista, n)
    descida = _bezier(p.crista, *p.ctrl_descida, (LARGURA, 0.0), n)
    return subida + descida[1:]


def _fita(p: Parametros) -> list[Ponto]:
    topo = _curva_topo(p)
    baixo = []
    for i, (x, y) in enumerate(topo):
        (xa, ya), (xb, yb) = topo[max(i - 1, 0)], topo[min(i + 1, len(topo) - 1)]
        tx, ty = xb - xa, yb - ya
        norma = math.hypot(tx, ty) or 1.0
        nx, ny = ty / norma, -tx / norma  # normal para baixo de uma curva que anda para a direita
        e = p.espessura(i / (len(topo) - 1))
        baixo.append((min(max(x + nx * e, 0.0), LARGURA), max(y + ny * e, 0.0)))
    return topo + baixo[::-1]


def _perna(p: Parametros) -> list[Ponto]:
    tx, ty = p.perna_topo
    w = p.perna_largura_topo
    direita = _bezier((tx + w / 2, ty), (tx - 10, ty - 70), (p.perna_pe + 5, 40.0), (p.perna_pe, 0.0), 40)
    esquerda = _bezier((p.perna_aba, 0.0), (p.perna_pe - 60, 2.0), (tx - 60, ty - 90), (tx - w / 2, ty), 40)
    return direita + esquerda


def _altura_topo_fita(p: Parametros, x: float) -> float:
    topo = _curva_topo(p)
    for (xa, ya), (xb, yb) in zip(topo, topo[1:]):
        if xa <= x <= xb:
            return ya + (yb - ya) * (x - xa) / ((xb - xa) or 1.0)
    return 0.0


def _pilar(p: Parametros) -> list[Ponto]:
    """Pilar atrás da fita: a base dele segue a borda de cima da fita (no E5 ele não desce até o chão)."""
    x0, x1 = p.pilar_x
    rx, ry = x1 - x0, p.pilar_topo - p.pilar_ombro
    topo = [(x0 + rx * math.cos(a), p.pilar_ombro + ry * math.sin(a)) for a in (math.pi / 2 * (1 - i / 40) for i in range(41))]
    base = [(x, _altura_topo_fita(p, x)) for x in (x1 - (x1 - x0) * i / 40 for i in range(41))]
    return [*topo, *base]


def formas(p: Parametros) -> dict[str, list[Ponto]]:
    return {"fita": _fita(p), "perna": _perna(p), "pilar": _pilar(p)}


def _d(pts: list[Ponto], altura: float) -> str:
    return "M" + " L".join(f"{x:.1f} {altura - y:.1f}" for x, y in pts) + " Z"


def svg_simbolo(p: Parametros, cor: str, id_mascara: str = "vao") -> str:
    f = formas(p)
    h = p.pilar_topo
    fita = _d(f["fita"], h)
    return (
        f'<g fill="{cor}">'
        f'<defs><mask id="{id_mascara}" maskUnits="userSpaceOnUse" x="-50" y="-50" width="{LARGURA + 100:g}" height="{h + 100:g}">'
        f'<rect x="-50" y="-50" width="{LARGURA + 100:g}" height="{h + 100:g}" fill="white"/>'
        f'<path d="{fita}" fill="black" stroke="black" stroke-width="{2 * p.vao:g}" stroke-linejoin="round"/>'
        f"</mask></defs>"
        f'<path d="{_d(f["pilar"], h)}" mask="url(#{id_mascara})"/>'
        f'<path d="{_d(f["perna"], h)}"/>'
        f'<path d="{fita}"/>'
        f"</g>"
    )


def raster(p: Parametros, largura_px: int) -> Image.Image:
    k = largura_px / LARGURA
    h = p.pilar_topo
    img = Image.new("L", (largura_px, math.ceil(h * k) + 1), 0)
    dr = ImageDraw.Draw(img)
    px = lambda pts: [(x * k, (h - y) * k) for x, y in pts]  # noqa: E731
    f = formas(p)
    dr.polygon(px(f["pilar"]), fill=255)
    fita = px(f["fita"])
    dr.line(fita + fita[:1], fill=0, width=max(1, round(2 * p.vao * k)), joint="curve")
    dr.polygon(fita, fill=0)
    dr.polygon(px(f["perna"]), fill=255)
    dr.polygon(fita, fill=255)
    return img


def sobrepor(referencia: Image.Image, mascara: Image.Image) -> Image.Image:
    base = referencia.convert("L").convert("RGB")
    vermelho = Image.new("RGB", base.size, (230, 40, 40))
    alfa = mascara.resize(base.size).point(lambda v: int(v * 0.55))
    return Image.composite(vermelho, base, alfa)


def main() -> int:
    from .paleta import FONTES_LOGO

    e5 = Image.open(terreno_dir() / FONTES_LOGO["E5"]).crop(CAIXA_E5)
    largura = 1000
    ref = e5.resize((largura, round(e5.height * largura / e5.width)))
    COMPARACAO.parent.mkdir(parents=True, exist_ok=True)
    sobrepor(ref, raster(Parametros(), largura)).save(COMPARACAO)
    print(COMPARACAO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
