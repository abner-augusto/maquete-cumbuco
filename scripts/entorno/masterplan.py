"""Masterplan das fases 2–10 pintado no chão, em segundo plano.

Fonte: página 5 ("MASTERPLAN") do MASTER URBANO.pdf (plano b), em vetor. O registro é a semelhança
que leva a poligonal desenhada no PDF à poligonal do DWG R05. O PDF tem y para baixo: o contorno
entra como (x, −y), senão a semelhança teria de ser um espelho.

Uso: uv run python -m scripts.entorno.masterplan
"""

import json
import math
import sys
from dataclasses import asdict, dataclass

import ezdxf
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from scipy.spatial import cKDTree
from shapely.geometry import Polygon

from scripts.comum.ambiente import RAIZ, terreno_dir
from scripts.loteamento.cena import DXF as DXF_VENDA
from scripts.loteamento.cena import aneis_da_layer
from scripts.loteamento.geometria import Ponto, centroide
from scripts.loteamento.placa import partes

from .extrair import CACHE

PDF = "2-LEVANTAMENTOS/PLANTAS_BASE/MASTER URBANO.pdf"
PAGINA = 4  # a 5ª, "MASTERPLAN"
DXF_R05 = RAIZ / "cache" / "dxf" / "masterplan-r05.dxf"
PNG = CACHE / "masterplan.png"
META = CACHE / "masterplan.json"
PX_POR_M = 2.0  # resolução do raster: 0,5 m/px, o dobro dos tiles
RESIDUO_MAX = 2.0  # m, mediana


@dataclass(frozen=True)
class Semelhanca:
    s: float
    theta: float
    tx: float
    ty: float

    def _r(self) -> np.ndarray:
        c, s = math.cos(self.theta), math.sin(self.theta)
        return np.array([[c, -s], [s, c]])

    def aplicar(self, pts: np.ndarray) -> np.ndarray:
        return self.s * np.asarray(pts, dtype=float) @ self._r().T + [self.tx, self.ty]

    def inversa(self, pts: np.ndarray) -> np.ndarray:
        return (np.asarray(pts, dtype=float) - [self.tx, self.ty]) @ self._r() / self.s


def amostrar(contorno: np.ndarray, passo: float) -> np.ndarray:
    """Pontos a cada `passo` ao longo do contorno fechado."""
    fechado = np.vstack([contorno, contorno[:1]])
    seg = np.diff(fechado, axis=0)
    comp = np.hypot(seg[:, 0], seg[:, 1])
    acum = np.concatenate([[0.0], np.cumsum(comp)])
    t = np.arange(0.0, acum[-1], passo)
    i = np.clip(np.searchsorted(acum, t, side="right") - 1, 0, len(seg) - 1)
    f = ((t - acum[i]) / np.where(comp[i] > 0, comp[i], 1.0))[:, None]
    return fechado[i] + seg[i] * f


def umeyama(a: np.ndarray, b: np.ndarray) -> Semelhanca:
    """Semelhança de mínimos quadrados a → b, sem espelho."""
    ma, mb = a.mean(0), b.mean(0)
    da, db = a - ma, b - mb
    u, d, vt = np.linalg.svd(db.T @ da / len(a))
    sinal = np.diag([1.0, np.sign(np.linalg.det(u @ vt))])
    r = u @ sinal @ vt
    s = float(np.trace(np.diag(d) @ sinal) / (da ** 2).sum(1).mean())
    t = mb - s * r @ ma
    return Semelhanca(s, math.atan2(r[1, 0], r[0, 0]), float(t[0]), float(t[1]))


def registrar(origem: np.ndarray, destino: np.ndarray, passo: float = 2.0,
              iteracoes: int = 50) -> tuple[Semelhanca, float]:
    """Semelhança origem → destino: escala pela razão de áreas, varredura de rotação de 1 em 1° e ICP.
    Devolve também o resíduo mediano (na unidade do destino)."""
    s0 = math.sqrt(Polygon(destino).buffer(0).area / Polygon(origem).buffer(0).area)  # contorno do PDF é inválido
    dest = amostrar(destino, passo)
    orig = amostrar(origem, passo / s0)
    arvore = cKDTree(dest)
    co, cd = orig.mean(0), dest.mean(0)
    melhor, erro = None, math.inf
    for graus in range(360):
        r = math.radians(graus)
        c, s = math.cos(r), math.sin(r)
        t = cd - s0 * np.array([[c, -s], [s, c]]) @ co
        cand = Semelhanca(s0, r, float(t[0]), float(t[1]))
        e = float(np.median(arvore.query(cand.aplicar(orig))[0]))
        if e < erro:
            melhor, erro = cand, e
    for _ in range(iteracoes):
        _, i = arvore.query(melhor.aplicar(orig))
        melhor = umeyama(orig, dest[i])
    return melhor, float(np.median(arvore.query(melhor.aplicar(orig))[0]))


def _compacidade(c: np.ndarray) -> float:
    g = Polygon(c).buffer(0)
    return 4 * math.pi * g.area / g.length ** 2


def escolher_contorno(caminhos: list[np.ndarray], alvo: np.ndarray) -> np.ndarray:
    """O caminho cuja forma (compacidade, invariante à semelhança) mais se parece com a da gleba,
    entre os 10 de maior área."""
    grandes = sorted(caminhos, key=lambda c: Polygon(c).buffer(0).area, reverse=True)[:10]
    ka = _compacidade(alvo)
    return min(grandes, key=lambda c: abs(_compacidade(c) - ka))


def caminhos_fechados(pagina, min_pontos: int = 50) -> list[np.ndarray]:
    saida = []
    for d in pagina.get_drawings():
        pts = []
        for it in d["items"]:
            if it[0] == "l":
                pts += [it[1], it[2]]
            elif it[0] == "c":
                pts += [it[1], it[4]]
        if len(pts) < min_pontos:
            continue
        a = np.array([(q.x, q.y) for q in pts])
        if d.get("closePath") or math.hypot(*(a[0] - a[-1])) < 0.5:
            saida.append(a)
    return saida


def rasterizar_contorno(pagina, px_por_pt: float, contorno: np.ndarray | None = None) -> tuple[Image.Image, list[float]]:
    """Raster da caixa do contorno (+5 pt). Zera o /Rotate da página antes: get_drawings dá o vetor sem o
    giro e get_pixmap desenha com ele; sem giro, os dois ficam no mesmo espaço (o registro absorve o giro)."""
    import pymupdf

    pagina.set_rotation(0)
    if contorno is None:
        contorno = max(caminhos_fechados(pagina), key=lambda c: Polygon(c).buffer(0).area)
    xs, ys = contorno[:, 0], contorno[:, 1]
    clip = pymupdf.Rect(xs.min() - 5, ys.min() - 5, xs.max() + 5, ys.max() + 5)
    pix = pagina.get_pixmap(matrix=pymupdf.Matrix(px_por_pt, px_por_pt), clip=clip, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples), [clip.x0, clip.y0, clip.x1, clip.y1]


def poligonal_gleba(msp, e0: float, n0: float, ref: Ponto) -> list[Ponto]:
    """A cópia da poligonal da gleba (o R05 a repete em vários deslocamentos) que contém `ref`."""
    copias = [a for a in aneis_da_layer(msp, ["POLIGONAL"], e0, n0) if len(a) >= 600]
    marca = Polygon([ref, (ref[0] + 0.1, ref[1]), (ref[0], ref[1] + 0.1)])
    dentro = {tuple((round(x, 2), round(y, 2)) for x, y in a): a  # cópia idêntica repetida conta uma vez
              for a in copias if Polygon(a).buffer(0).contains(marca)}
    dentro = list(dentro.values())
    if len(dentro) != 1:
        raise SystemExit(f"poligonal da gleba: {len(dentro)} cópias contêm a Fase 1 (esperado 1)")
    return dentro[0]


def _afim(f) -> tuple[float, ...]:
    """Coeficientes do Image.AFFINE a partir de f(u, v) → (x, y) no raster de entrada."""
    o = np.array(f(0.0, 0.0))
    a, b = np.array(f(1.0, 0.0)) - o, np.array(f(0.0, 1.0)) - o
    return (a[0], b[0], o[0], a[1], b[1], o[1])


def _mascara(geom, ext_m, tam) -> Image.Image:
    x0, y0, x1, y1 = ext_m
    w, h = tam
    m = Image.new("L", tam, 0)
    dr = ImageDraw.Draw(m)
    px = lambda cs: [((x - x0) / (x1 - x0) * w, (y1 - y) / (y1 - y0) * h) for x, y in cs]  # noqa: E731
    for p in partes(geom):
        dr.polygon(px(p.exterior.coords), fill=255)
        for furo in p.interiors:
            dr.polygon(px(furo.coords), fill=0)
    return m


def pintar(tile: Image.Image, ext_m, mp_img: Image.Image, meta: dict, mascara,
           saturacao: float, opacidade: float) -> Image.Image:
    """O masterplan registrado sobre o tile, dessaturado e meio transparente, só dentro da máscara."""
    w, h = tile.size
    x0, y0, x1, y1 = ext_m
    T = Semelhanca(**meta["transf"])
    k = meta["px_por_pt"]
    cx0, cy0 = meta["clip"][:2]

    def f(u: float, v: float) -> tuple[float, float]:
        X, Y = x0 + u * (x1 - x0) / w, y1 - v * (y1 - y0) / h
        xp, ym = T.inversa(np.array([[X, Y]]))[0]
        return ((xp - cx0) * k, (-ym - cy0) * k)

    mp = mp_img.convert("RGB").transform((w, h), Image.AFFINE, _afim(f), resample=Image.BILINEAR,
                                         fillcolor=(255, 255, 255))
    mp = ImageEnhance.Color(mp).enhance(saturacao).filter(ImageFilter.GaussianBlur(0.8))
    alfa = _mascara(mascara, ext_m, (w, h)).point(lambda a: round(a * opacidade))
    return Image.composite(mp, tile, alfa)


def main() -> int:
    import pymupdf

    sys.stdout.reconfigure(encoding="utf-8")
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    pol_venda = aneis_da_layer(ezdxf.readfile(DXF_VENDA).modelspace(), ["AR-CNT-POL"], e0, n0)
    gleba = poligonal_gleba(ezdxf.readfile(DXF_R05).modelspace(), e0, n0, centroide(pol_venda[0]))
    alvo = np.array(gleba)
    pagina = pymupdf.open(terreno_dir() / PDF)[PAGINA]
    pagina.set_rotation(0)  # a página tem /Rotate 270: vetor e raster no espaço sem giro
    contorno = escolher_contorno(caminhos_fechados(pagina), alvo)
    T, residuo = registrar(contorno * [1.0, -1.0], alvo)
    print(f"masterplan: {T.s:.3f} m/pt · rotação {math.degrees(T.theta):+.2f}° · resíduo mediano {residuo:.2f} m")
    if residuo > RESIDUO_MAX:
        raise SystemExit(f"resíduo {residuo:.2f} m acima de {RESIDUO_MAX} m: contorno errado no PDF?")
    k = PX_POR_M * T.s
    img, clip = rasterizar_contorno(pagina, k, contorno)
    img.save(PNG)
    META.write_text(json.dumps({"arquivo": str(PNG), "clip": clip, "px_por_pt": k,
                                "transf": asdict(T), "residuo_m": residuo, "gleba": [list(p) for p in gleba]}),
                    encoding="utf-8")
    print(f"raster {img.width}×{img.height} px ({1 / PX_POR_M:.1f} m/px) → {PNG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
