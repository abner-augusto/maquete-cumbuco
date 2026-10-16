"""Encaixe dos marcos na planta de venda: dois pares de pontos (ilha↔círculo, clube↔quadra) dão a
transformação rígida; ICP com o chão da portaria a refina. Python puro: o Blender só extrai e aplica.

Uso: uv run python -m scripts.marcos.encaixe
"""

import math
import tomllib
from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree

from scripts.comum.ambiente import RAIZ
from scripts.entorno.masterplan import Semelhanca, umeyama

CFG_TOML = RAIZ / "scripts" / "marcos" / "marcos.toml"


@dataclass(frozen=True)
class MarcosCfg:
    pasta: str
    clube: str
    portaria: str
    pivo_clube: list[float]
    giro_clube: float
    edificacao: list[str]
    margem_portaria: float
    raio_icp: float
    corte_icp: float
    residuo_max: float
    tol_raio: float
    tol_dist: float
    cobertura_min: float
    kmz_estande: str

    @classmethod
    def carregar(cls) -> "MarcosCfg":
        return cls(**tomllib.loads(CFG_TOML.read_text(encoding="utf-8")))


def girar(pts, pivo: tuple[float, float], graus: float) -> np.ndarray:
    a = math.radians(graus)
    r = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    p = np.asarray(pts, dtype=float) - pivo
    return p @ r.T + pivo


def escolher_circulo(circulos: list[tuple[float, float, float]], raio: float, dist_clube: float,
                     quadra: tuple[float, float], tol_raio: float = 3.0, tol_dist: float = 10.0
                     ) -> tuple[float, float, float]:
    """O círculo do DWG com o raio da ilha do GLB e à distância ilha–clube da quadra central."""
    bons = [c for c in circulos if abs(c[2] - raio) <= tol_raio
            and abs(math.hypot(c[0] - quadra[0], c[1] - quadra[1]) - dist_clube) <= tol_dist]
    if len(bons) != 1:
        raise SystemExit(f"círculo da rotatória: {len(bons)} candidatos (raio {raio:.1f} m, "
                         f"distância ao clube {dist_clube:.1f} m) entre {circulos}")
    return bons[0]


def ancora(ilha, clube, circulo, quadra) -> Semelhanca:
    """Transformação rígida que leva ilha→círculo e o rumo ilha→clube ao rumo círculo→quadra."""
    ilha, clube, circulo, quadra = (np.asarray(p, dtype=float) for p in (ilha, clube, circulo, quadra))
    de, para = clube - ilha, quadra - circulo
    theta = math.atan2(para[1], para[0]) - math.atan2(de[1], de[0])
    c, s = math.cos(theta), math.sin(theta)
    t = circulo - np.array([[c, -s], [s, c]]) @ ilha
    return Semelhanca(1.0, theta, float(t[0]), float(t[1]))


def _normais(pts: np.ndarray, arvore: cKDTree, k: int = 6) -> np.ndarray:
    """Normal de cada ponto do destino: o eixo de menor variância dos k vizinhos."""
    _, viz = arvore.query(pts, k=min(k, len(pts)))
    d = pts[viz] - pts[viz].mean(1, keepdims=True)
    _, vetores = np.linalg.eigh(np.einsum("nki,nkj->nij", d, d))
    return vetores[:, :, 0]


def icp_rigido(origem: np.ndarray, destino: np.ndarray, inicial: Semelhanca, iteracoes: int = 30,
               corte: float = 5.0) -> tuple[Semelhanca, float]:
    """ICP rígido ponto-a-reta a partir de `inicial`; par mais longe que `corte` não entra (sobra de um
    dos lados). Ponto-a-ponto empaca na distância entre amostras; ponto-a-reta desliza ao longo da borda.
    Devolve também o resíduo mediano ponto-a-ponto."""
    arvore = cKDTree(destino)
    normais = _normais(destino, arvore)
    t = inicial
    for _ in range(iteracoes):
        p = t.aplicar(origem)
        d, i = arvore.query(p)
        ok = d <= corte
        if ok.sum() < 3:
            break
        p, q, n = p[ok], destino[i[ok]], normais[i[ok]]
        jac = np.c_[n[:, 1] * p[:, 0] - n[:, 0] * p[:, 1], n]  # d/dθ, d/dtx, d/dty
        dth, dx, dy = np.linalg.lstsq(jac, -((p - q) * n).sum(1), rcond=None)[0]
        c, s = math.cos(dth), math.sin(dth)
        t = Semelhanca(1.0, t.theta + dth, c * t.tx - s * t.ty + dx, s * t.tx + c * t.ty + dy)
        if abs(dth) < 1e-9 and math.hypot(dx, dy) < 1e-6:
            break
    d, _ = arvore.query(t.aplicar(origem))
    return t, float(np.median(d[d <= corte])) if (d <= corte).any() else math.inf
