"""Terreno da cena: platô do loteamento, morro pelo levantamento suavizado e entorno pelo Copernicus.

Uso: uv run python -m scripts.loteamento.terreno
"""

import json
import math
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, label, map_coordinates

from .geometria import Ponto, centroide
from .relevo import Grade, mascara


@dataclass(frozen=True)
class TerrenoCfg:
    poligonal: list[str]
    talude: float
    sigma: float
    alcance: float
    transicao: float
    raio: float
    mar_rebaixo: float
    passo_perto: float
    plato_cota: float | None = None

    @classmethod
    def carregar(cls, caminho: Path) -> "TerrenoCfg":
        return cls(**tomllib.loads(caminho.read_text(encoding="utf-8"))["terreno"])


def encaixar(ext: tuple[float, float, float, float], passo: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = ext
    return (math.floor(x0 / passo) * passo, math.floor(y0 / passo) * passo,
            math.ceil(x1 / passo) * passo, math.ceil(y1 / passo) * passo)


def _nos(g: Grade) -> tuple[np.ndarray, np.ndarray]:
    return np.meshgrid(g.x0 + g.passo * np.arange(g.nx), g.y0 + g.passo * np.arange(g.ny))


def amostrar_grade(g: Grade, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Bilinear presa na borda (como Grade.cota), vetorizada; NaN da grade se propaga."""
    fx = np.clip((np.asarray(xs) - g.x0) / g.passo, 0, g.nx - 1)
    fy = np.clip((np.asarray(ys) - g.y0) / g.passo, 0, g.ny - 1)
    return map_coordinates(np.array(g.z, dtype=float), [fy, fx], order=1, mode="nearest")


def reamostrar(g: Grade, ext: tuple[float, float, float, float], passo: float) -> Grade:
    """`g` numa grade nova; fora de `g` (ou onde ela é NaN) fica NaN."""
    x0, y0, x1, y1 = ext
    nx, ny = int(round((x1 - x0) / passo)) + 1, int(round((y1 - y0) / passo)) + 1
    gx, gy = np.meshgrid(x0 + passo * np.arange(nx), y0 + passo * np.arange(ny))
    z = amostrar_grade(g, gx, gy)
    fora = (gx < g.x0) | (gx > g.x0 + g.passo * (g.nx - 1)) | (gy < g.y0) | (gy > g.y0 + g.passo * (g.ny - 1))
    z[fora] = np.nan
    return Grade(float(x0), float(y0), float(passo), nx, ny, z.tolist())


def cota_plato(lev: Grade, lotes: list[dict], passo: float = 0.5) -> float:
    """Mediana do levantamento nos centróides dos lotes, arredondada a `passo`."""
    zs = [lev.cota(*centroide([tuple(p) for p in l["poligono"]])) for l in lotes]
    zs = [z for z in zs if not math.isnan(z)]
    return float(round(float(np.median(zs)) / passo) * passo)


def ajustar_datum(lev: Grade, dem: Grade, onde: np.ndarray) -> float:
    """Mediana de (levantamento − Copernicus) nos nós de `lev` marcados em `onde` que têm levantamento."""
    z = np.array(lev.z, dtype=float)
    gx, gy = _nos(lev)
    d = amostrar_grade(dem, gx, gy)
    ok = onde & ~np.isnan(z)
    return float(np.median(z[ok] - d[ok]))


def separar_mar(dem: Grade, nivel: float = 0.0, rebaixo: float = 1.0) -> Grade:
    """Água ligada à borda com cota ≤ `nivel` é mar: desce a `nivel − rebaixo`. Baixio isolado
    no continente sobe a `nivel + 0,2`, para o plano do mar não aparecer nele."""
    z = np.array(dem.z, dtype=float)
    rotulo, _ = label(z <= nivel)
    borda = set(np.unique(np.concatenate([rotulo[0], rotulo[-1], rotulo[:, 0], rotulo[:, -1]]))) - {0}
    mar = np.isin(rotulo, list(borda))
    z = np.where(mar, nivel - rebaixo, np.where(rotulo > 0, nivel + 0.2, z))
    return Grade(dem.x0, dem.y0, dem.passo, dem.nx, dem.ny, np.round(z, 2).tolist())


def _distancia_fora(g: Grade, aneis: list[list[Ponto]]) -> np.ndarray:
    """Metros de cada nó até a área dos anéis (0 dentro)."""
    return distance_transform_edt(~mascara(g, aneis)) * g.passo


def compor_perto(lev: Grade, dem: Grade, poligonal: list[list[Ponto]], cota: float, cfg: TerrenoCfg) -> Grade:
    """Platô na cota dentro da poligonal; talude de `cfg.talude` m; depois o levantamento suavizado
    (σ = `cfg.sigma`) até `cfg.alcance` m, passando ao Copernicus em `cfg.transicao` m. Onde o
    levantamento acaba, a troca também é gradual (peso pela cobertura suavizada)."""
    z = np.array(lev.z, dtype=float)
    tem = ~np.isnan(z)
    s = cfg.sigma / lev.passo
    soma = gaussian_filter(np.where(tem, z, 0.0), s, mode="nearest")
    cobertura = gaussian_filter(tem.astype(float), s, mode="nearest")
    suave = np.divide(soma, cobertura, out=np.zeros_like(soma), where=cobertura > 1e-6)
    gx, gy = _nos(lev)
    longe = amostrar_grade(dem, gx, gy)
    dist = _distancia_fora(lev, poligonal)
    peso = np.clip((cfg.alcance + cfg.transicao - dist) / cfg.transicao, 0.0, 1.0) * np.clip(cobertura, 0.0, 1.0)
    base = peso * suave + (1.0 - peso) * longe
    t = np.clip(dist / cfg.talude, 0.0, 1.0)
    final = (1.0 - t) * cota + t * base
    return Grade(lev.x0, lev.y0, lev.passo, lev.nx, lev.ny, np.round(final, 2).tolist())
