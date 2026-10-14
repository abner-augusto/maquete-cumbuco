"""Relevo macro do entorno: Copernicus GLO-30 (DSM, 30 m) reamostrado na grade local.

Uso: uv run python -m scripts.entorno.dem
"""

import json
import math
import shutil
import sys
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window
from scipy.ndimage import map_coordinates

from scripts.comum.ambiente import RAIZ
from scripts.loteamento.relevo import Grade

TILE = "Copernicus_DSM_COG_10_S04_00_W039_00_DEM"
URL = f"https://copernicus-dem-30m.s3.amazonaws.com/{TILE}/{TILE}.tif"
CACHE = RAIZ / "cache" / "dem" / f"{TILE}.tif"
DESTINO = RAIZ / "cache" / "cena" / "dem.json"
CRS_LOCAL = "EPSG:31984"
RAIO = 4000.0  # m a partir do centro dos lotes
PASSO = 30.0  # m, a resolução do Copernicus


def baixar(url: str = URL, destino: Path = CACHE) -> Path:
    """Baixa uma vez; grava em .part e renomeia, para um download cortado não virar cache."""
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    parte = destino.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=600) as r, open(parte, "wb") as f:
        shutil.copyfileobj(r, f)
    parte.replace(destino)
    return destino


def amostrar(tif: Path, e: np.ndarray, n: np.ndarray, crs: str = CRS_LOCAL) -> np.ndarray:
    """Cota bilinear do raster nos pontos (E, N) de `crs`; nodata vira 0 (mar)."""
    with rasterio.open(tif) as src:
        lon, lat = Transformer.from_crs(crs, src.crs, always_xy=True).transform(np.asarray(e), np.asarray(n))
        col, lin = ~src.transform @ (np.asarray(lon), np.asarray(lat))
        c0 = max(int(math.floor(np.min(col))) - 2, 0)
        r0 = max(int(math.floor(np.min(lin))) - 2, 0)
        c1 = min(int(math.ceil(np.max(col))) + 2, src.width)
        r1 = min(int(math.ceil(np.max(lin))) + 2, src.height)
        a = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0)).astype(float)
        if src.nodata is not None:
            a[a == src.nodata] = 0.0
    return map_coordinates(a, [np.asarray(lin) - r0 - 0.5, np.asarray(col) - c0 - 0.5], order=1, mode="nearest")


def grade_dem(tif: Path, e0: float, n0: float, centro: tuple[float, float],
              raio: float = RAIO, passo: float = PASSO) -> Grade:
    """Grade local (x = E − E0, y = N − N0) de `passo` m, nós em múltiplos de `passo`, cobrindo o raio."""
    x0 = math.floor((centro[0] - raio) / passo) * passo
    y0 = math.floor((centro[1] - raio) / passo) * passo
    nx = int(math.ceil((centro[0] + raio - x0) / passo)) + 1
    ny = int(math.ceil((centro[1] + raio - y0) / passo)) + 1
    gx, gy = np.meshgrid(x0 + passo * np.arange(nx), y0 + passo * np.arange(ny))
    z = amostrar(tif, (gx + e0).ravel(), (gy + n0).ravel()).reshape(gx.shape)
    return Grade(float(x0), float(y0), float(passo), nx, ny, np.round(z, 2).tolist())


def centro_dos_lotes() -> tuple[float, float]:
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    xs = [x for l in lotes for x, _ in l["poligono"]]
    ys = [y for l in lotes for _, y in l["poligono"]]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    tif = baixar()
    g = grade_dem(tif, georref["origem"]["E"], georref["origem"]["N"], centro_dos_lotes())
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(g.para_json()), encoding="utf-8")
    zs = [v for linha in g.z for v in linha]
    print(f"Copernicus {tif.name} · grade {g.nx}×{g.ny} de {g.passo:.0f} m · cota {min(zs):.1f}–{max(zs):.1f} m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
