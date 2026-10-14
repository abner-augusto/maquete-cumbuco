"""Texto → contorno SVG com fontTools (letreiros da marca sem depender de fonte instalada)."""

from dataclasses import dataclass
from functools import lru_cache

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


@lru_cache(maxsize=None)
def fonte(caminho: str, peso: int) -> TTFont:
    tt = TTFont(caminho)
    if "fvar" in tt:
        tt = instantiateVariableFont(tt, {"wght": peso})
    return tt


@dataclass(frozen=True)
class Letreiro:
    d: str
    largura: float
    altura_maiuscula: float
    topo: float  # altura da tinta mais alta acima da linha de base (acentos passam da maiúscula)


def _num(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def contorno(tt: TTFont, texto: str, tamanho: float, espacamento: float = 0.0) -> Letreiro:
    glifos = tt.getGlyphSet()
    cmap = tt.getBestCmap()
    k = tamanho / tt["head"].unitsPerEm
    caneta = SVGPathPen(glifos, ntos=_num)
    caixa = BoundsPen(glifos)
    x = 0.0
    for i, letra in enumerate(texto):
        if ord(letra) not in cmap:
            raise ValueError(f"glifo ausente: {letra!r}")
        g = glifos[cmap[ord(letra)]]
        g.draw(TransformPen(caneta, (k, 0, 0, -k, x, 0)))
        g.draw(TransformPen(caixa, (k, 0, 0, k, x, 0)))
        x += g.width * k
        if i < len(texto) - 1:
            x += espacamento * tamanho
    cap = tt["OS/2"].sCapHeight * k
    return Letreiro(caneta.getCommands(), x, cap, max(cap, caixa.bounds[3]) if caixa.bounds else cap)
