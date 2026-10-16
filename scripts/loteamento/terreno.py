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
import shapely
from scipy.ndimage import distance_transform_edt, gaussian_filter, label, map_coordinates
from shapely.geometry.base import BaseGeometry

from scripts.comum.ambiente import RAIZ
from scripts.entorno import dem
from scripts.entorno.tiles import da_janela, ext_da_grade, janelas

from .acesso import Acesso, AcessoCfg, com_perfil, corredor, eixo_do_acesso, perfil_vertical, sem_faixa
from .cena import CFG_TOML, DXF, CenaCfg, aneis_da_layer
from .costa import agua_do_osm, costa_suave, linhas_de_costa, malha_mar, mar_da_costa
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
    praia_inclinacao: float = 0.05
    fundo_inclinacao: float = 0.1
    mar_alcance: float = 16000.0

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


def compor_perto(lev: Grade, dem: Grade, poligonal: list[list[Ponto]], cota: float, cfg: TerrenoCfg,
                 livre: BaseGeometry | None = None) -> Grade:
    """Platô na cota dentro da poligonal; talude de `cfg.talude` m; depois o levantamento suavizado
    (σ = `cfg.sigma`) até `cfg.alcance` m, passando ao Copernicus em `cfg.transicao` m. Onde o
    levantamento acaba, a troca também é gradual (peso pela cobertura suavizada). Em `livre` (a faixa
    da CE), o chão natural: o talude do platô não sobe nela."""
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
    if livre is not None:
        t = np.where(shapely.contains_xy(livre, gx, gy), 1.0, t)
    final = (1.0 - t) * cota + t * base
    return Grade(lev.x0, lev.y0, lev.passo, lev.nx, lev.ny, np.round(final, 2).tolist())


def aplicar_acesso(g: Grade, a: Acesso, acfg: AcessoCfg, area: BaseGeometry, talude: float) -> Grade:
    """Chão do corredor do acesso: 0,5 m abaixo do perfil até uma célula e meia da área (a célula que a
    borda corta fica toda no perfil), depois talude de `talude` m até o chão que já estava."""
    gx, gy = _nos(g)
    dist = shapely.distance(area, shapely.points(gx, gy))
    perto = dist <= 1.5 * g.passo + talude
    zs = perfil_vertical(a.pvis, acfg.curva_vertical)
    s, _ = a.local(np.c_[gx[perto], gy[perto]])
    zc = np.array([zs(min(max(x, a.s_ini), a.s_fim)) for x in s]) - 0.5
    w = np.clip((dist[perto] - 1.5 * g.passo) / talude, 0.0, 1.0)
    z = np.array(g.z, dtype=float)
    z[perto] = (1.0 - w) * zc + w * z[perto]
    return Grade(g.x0, g.y0, g.passo, g.nx, g.ny, np.round(z, 2).tolist())


def malha_entorno(dem: Grade, buraco: tuple[float, float, float, float], centro: tuple[float, float],
                  raio: float, janela: tuple[float, float, float, float] | None = None
                  ) -> tuple[list[list[float]], list[list[int]]]:
    """Grade do Copernicus em triângulos: células com os 4 cantos no raio e fora do `buraco`
    (o terreno perto). O buraco cai em linhas da grade, então cada célula está toda dentro ou fora.
    Com `janela`, só as células cujo centro cai nela (tiles.da_janela)."""
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
            if janela is not None and not da_janela(janela, (xa + xb) / 2, (ya + yb) / 2):
                continue
            if bx0 <= xa and xb <= bx1 and by0 <= ya and yb <= by1:
                continue
            if any(math.hypot(x - centro[0], y - centro[1]) > raio for x in (xa, xb) for y in (ya, yb)):
                continue
            a, b, c, d = no(i, j), no(i + 1, j), no(i + 1, j + 1), no(i, j + 1)
            faces += [[a, b, c], [a, c, d]]
    return vertices, faces


def raio_do_mar(raio: float, passo: float) -> float:
    """O entorno só guarda células com os 4 cantos no raio: a terra acaba em escada até uma
    diagonal de célula para dentro. O disco do mar para ali, para não sobrar água além da terra."""
    return raio - passo * math.sqrt(2)


def disco_mar(centro: tuple[float, float], raio: float, nivel: float, n: int = 96) -> tuple[list[list[float]], list[list[int]]]:
    """Plano da água: disco no raio do entorno; a terra acima do nível o esconde."""
    cx, cy = centro
    v = [[round(cx, 2), round(cy, 2), nivel]] + [
        [round(cx + raio * math.cos(2 * math.pi * k / n), 2), round(cy + raio * math.sin(2 * math.pi * k / n), 2), nivel]
        for k in range(n)]
    return v, [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)]


DESTINO_LONGE = RAIZ / "cache" / "cena" / "longe.json"


class Relevo:
    """Cota do chão da cena: a grade perto onde ela existe (borda incluída), o Copernicus ajustado fora.
    A borda do perto coincide com o longe (costura do 3c), então a troca não tem degrau."""

    def __init__(self, perto: Grade, longe: Grade):
        self.perto, self.longe = perto, longe
        self._x1 = perto.x0 + perto.passo * (perto.nx - 1)
        self._y1 = perto.y0 + perto.passo * (perto.ny - 1)

    def cota(self, x: float, y: float) -> float:
        p = self.perto
        if p.x0 <= x <= self._x1 and p.y0 <= y <= self._y1:
            return p.cota_malha(x, y)
        return self.longe.cota_malha(x, y)  # a superfície desenhada, não o bilinear: nada afunda nem flutua

    @classmethod
    def carregar(cls) -> "Relevo":
        ler = lambda c: Grade.de_json(json.loads(c.read_text(encoding="utf-8")))  # noqa: E731
        return cls(ler(DESTINO_PERTO), ler(DESTINO_LONGE))


def aneis_do_plato(msp, cfg: TerrenoCfg, lotes: list[dict], e0: float, n0: float) -> list[list[Ponto]]:
    """Poligonal + todas as áreas da cena + lotes: o que fica plano (e fora do entorno)."""
    camadas = [l for ls in CenaCfg.carregar(CFG_TOML).camadas.values() for l in ls]
    return (aneis_da_layer(msp, cfg.poligonal, e0, n0) + aneis_da_layer(msp, camadas, e0, n0)
            + [[tuple(p) for p in l["poligono"]] for l in lotes])


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
    plato = aneis_do_plato(msp, cfg, lotes, e0, n0)
    acfg = AcessoCfg.carregar(CFG_TOML)
    acesso, livre = eixo_do_acesso(msp, acfg, e0, n0)
    plato = sem_faixa(plato, acesso, acfg)
    xs = [x for a in poligonal for x, _ in a]
    ys = [y for a in poligonal for _, y in a]
    folga = cfg.alcance + cfg.transicao + bruto.passo  # a borda do perto já é Copernicus puro
    ext = encaixar((min(xs) - folga, min(ys) - folga, max(xs) + folga, max(ys) + folga), bruto.passo)
    perto_lev = reamostrar(lev, ext, cfg.passo_perto)
    fora = _distancia_fora(perto_lev, plato) > cfg.plato_folga + cfg.talude
    com_mar = separar_mar(bruto, 0.0, cfg.mar_rebaixo)
    centro = dem.centro_dos_lotes()
    costa = linhas_de_costa(e0, n0)
    # o arco do disco fica bem fora do entorno; o plano da água vai até lá do lado do mar
    mar = mar_da_costa(costa, centro, cfg.mar_alcance) if costa else None
    agua = agua_do_osm(e0, n0)
    if mar is not None:
        com_mar = costa_suave(com_mar, mar, 0.0, cfg.praia_inclinacao, cfg.fundo_inclinacao, cfg.mar_rebaixo, agua=agua)
    else:
        print("sem cache/entorno/osm-areas.json: costa em escada do Copernicus (rode scripts.entorno.extrair)")
    delta = ajustar_datum(perto_lev, com_mar, fora)
    longe = Grade(bruto.x0, bruto.y0, bruto.passo, bruto.nx, bruto.ny,
                  (np.array(com_mar.z, dtype=float) + delta).round(2).tolist())
    cota = cfg.plato_cota if cfg.plato_cota is not None else cota_plato(lev, lotes)
    perto = compor_perto(perto_lev, longe, plato, cota, cfg, livre=livre)
    if mar is not None:  # o levantamento chega à boca da barra: a costa dele também segue a linha
        perto = costa_suave(perto, mar, delta, cfg.praia_inclinacao, cfg.fundo_inclinacao, cfg.mar_rebaixo,
                            celula=longe.passo, agua=agua)
    acesso = com_perfil(acesso, perto, cota, acfg)
    perto = aplicar_acesso(perto, acesso, acfg, corredor(acesso, acfg), cfg.talude)
    acesso.salvar()
    entorno = [{"nome": f"Entorno_{k}", "material": "entorno", "vertices": v, "faces": f}
               for k, jan in janelas(ext_da_grade(longe), longe.passo).items()
               for v, f in [malha_entorno(longe, ext, centro, cfg.raio, jan)]]
    if mar is not None:
        vm, fm = malha_mar(centro, raio_do_mar(cfg.raio, longe.passo), mar, cfg.mar_alcance, round(delta, 2))
    else:
        vm, fm = disco_mar(centro, raio_do_mar(cfg.raio, longe.passo), round(delta, 2))
    DESTINO_PERTO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO_PERTO.write_text(json.dumps(perto.para_json()), encoding="utf-8")
    DESTINO_LONGE.write_text(json.dumps(longe.para_json()), encoding="utf-8")
    DESTINO_ENTORNO.write_text(json.dumps({"objetos": [
        *entorno,
        {"nome": "Mar", "material": "mar", "vertices": vm, "faces": fm},
    ]}), encoding="utf-8")
    print(f"platô {cota:.1f} m · levantamento − Copernicus = {delta:+.2f} m (mar nessa cota) · "
          f"perto {perto.nx}×{perto.ny} de {perto.passo:.0f} m · entorno {sum(len(o["faces"]) for o in entorno)} triângulos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
