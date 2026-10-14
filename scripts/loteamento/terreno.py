"""Terreno da cena: platô do loteamento, morro pelo levantamento suavizado e entorno pelo Copernicus.

Uso: uv run python -m scripts.loteamento.terreno
"""

import json
import math
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import ezdxf
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, label, map_coordinates

from scripts.comum.ambiente import RAIZ
from scripts.entorno import dem

from .cena import CFG_TOML, DXF, CenaCfg, aneis_da_layer
from .geometria import Ponto, centroide
from .relevo import DESTINO as RELEVO_JSON
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
    plato_folga: float = 0.0  # m de platô além das áreas, antes do talude

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
    """Metros de cada nó até a área dos anéis (0 dentro). A distância ao nó de dentro mais perto
    passa da distância à borda em até uma célula: desconta-se uma célula (erra para o lado do platô)."""
    return np.maximum(distance_transform_edt(~mascara(g, aneis)) * g.passo - g.passo, 0.0)


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
    t = np.clip((dist - cfg.plato_folga) / cfg.talude, 0.0, 1.0)
    final = (1.0 - t) * cota + t * base
    return Grade(lev.x0, lev.y0, lev.passo, lev.nx, lev.ny, np.round(final, 2).tolist())


def malha_entorno(dem: Grade, buraco: tuple[float, float, float, float], centro: tuple[float, float],
                  raio: float) -> tuple[list[list[float]], list[list[int]]]:
    """Grade do Copernicus em triângulos: células com os 4 cantos no raio e fora do `buraco`
    (o terreno perto). O buraco cai em linhas da grade, então cada célula está toda dentro ou fora."""
    bx0, by0, bx1, by1 = buraco
    z = dem.z
    indice: dict[tuple[int, int], int] = {}
    vertices: list[list[float]] = []
    faces: list[list[int]] = []

    def no(i: int, j: int) -> int:
        if (i, j) not in indice:
            indice[(i, j)] = len(vertices)
            vertices.append([round(dem.x0 + i * dem.passo, 2), round(dem.y0 + j * dem.passo, 2), z[j][i]])
        return indice[(i, j)]

    for j in range(dem.ny - 1):
        for i in range(dem.nx - 1):
            xa, ya = dem.x0 + i * dem.passo, dem.y0 + j * dem.passo
            xb, yb = xa + dem.passo, ya + dem.passo
            if bx0 <= xa and xb <= bx1 and by0 <= ya and yb <= by1:
                continue
            if any(math.hypot(x - centro[0], y - centro[1]) > raio for x in (xa, xb) for y in (ya, yb)):
                continue
            a, b, c, d = no(i, j), no(i + 1, j), no(i + 1, j + 1), no(i, j + 1)
            faces += [[a, b, c], [a, c, d]]
    return vertices, faces


def disco_mar(centro: tuple[float, float], raio: float, nivel: float, n: int = 96) -> tuple[list[list[float]], list[list[int]]]:
    """Plano da água: disco no raio do entorno; a terra acima do nível o esconde."""
    cx, cy = centro
    v = [[round(cx, 2), round(cy, 2), nivel]] + [
        [round(cx + raio * math.cos(2 * math.pi * k / n), 2), round(cy + raio * math.sin(2 * math.pi * k / n), 2), nivel]
        for k in range(n)]
    return v, [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)]


DESTINO_PERTO = RAIZ / "cache" / "cena" / "terreno.json"
DESTINO_ENTORNO = RAIZ / "cache" / "cena" / "entorno.json"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = TerrenoCfg.carregar(CFG_TOML)
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    lev = Grade.de_json(json.loads(RELEVO_JSON.read_text(encoding="utf-8")))
    bruto = Grade.de_json(json.loads(dem.DESTINO.read_text(encoding="utf-8")))
    msp = ezdxf.readfile(DXF).modelspace()
    poligonal = aneis_da_layer(msp, cfg.poligonal, e0, n0)
    # O platô cobre tudo o que está desenhado (vias de acesso, verdes e lotes fora da poligonal
    # também): nada da planta fica no talude, onde a grade de 10 m o cortaria.
    camadas = [l for ls in CenaCfg.carregar(CFG_TOML).camadas.values() for l in ls]
    plato = poligonal + aneis_da_layer(msp, camadas, e0, n0) + [[tuple(p) for p in l["poligono"]] for l in lotes]
    xs = [x for a in poligonal for x, _ in a]
    ys = [y for a in poligonal for _, y in a]
    folga = cfg.alcance + cfg.transicao + bruto.passo  # a borda do perto já é Copernicus puro
    ext = encaixar((min(xs) - folga, min(ys) - folga, max(xs) + folga, max(ys) + folga), bruto.passo)
    perto_lev = reamostrar(lev, ext, cfg.passo_perto)
    fora = _distancia_fora(perto_lev, plato) > cfg.plato_folga + cfg.talude
    com_mar = separar_mar(bruto, 0.0, cfg.mar_rebaixo)
    delta = ajustar_datum(perto_lev, com_mar, fora)
    longe = Grade(bruto.x0, bruto.y0, bruto.passo, bruto.nx, bruto.ny,
                  (np.array(com_mar.z, dtype=float) + delta).round(2).tolist())
    cota = cfg.plato_cota if cfg.plato_cota is not None else cota_plato(lev, lotes)
    perto = compor_perto(perto_lev, longe, plato, cota, cfg)
    centro = dem.centro_dos_lotes()
    v, f = malha_entorno(longe, ext, centro, cfg.raio)
    vm, fm = disco_mar(centro, cfg.raio, round(delta, 2))
    DESTINO_PERTO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO_PERTO.write_text(json.dumps(perto.para_json()), encoding="utf-8")
    DESTINO_ENTORNO.write_text(json.dumps({"objetos": [
        {"nome": "Entorno", "material": "entorno", "vertices": v, "faces": f},
        {"nome": "Mar", "material": "mar", "vertices": vm, "faces": fm},
    ]}), encoding="utf-8")
    print(f"platô {cota:.1f} m · levantamento − Copernicus = {delta:+.2f} m (mar nessa cota) · "
          f"perto {perto.nx}×{perto.ny} de {perto.passo:.0f} m · entorno {len(f)} triângulos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
