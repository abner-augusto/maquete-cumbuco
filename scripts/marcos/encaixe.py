"""Encaixe dos marcos na planta de venda: dois pares de pontos (ilha↔círculo, clube↔quadra) dão a
transformação rígida; ICP com o chão da portaria a refina. Python puro: o Blender só extrai e aplica.

Uso: uv run python -m scripts.marcos.encaixe
"""

import json
import math
import sys
import tomllib
from dataclasses import dataclass

import ezdxf
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import unary_union

from scripts.comum.ambiente import RAIZ
from scripts.entorno.masterplan import Semelhanca, umeyama
from scripts.loteamento.placa import partes

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


def quadra_do_clube(chao_plato, plato) -> Polygon:
    """A maior parte do ChaoPlato que não toca a borda do platô: a quadra sem lote do meio."""
    borda = plato.exterior if isinstance(plato, Polygon) else unary_union([p.exterior for p in partes(plato)])
    interiores = [p for p in partes(chao_plato) if not p.buffer(0.01).intersects(borda)]
    if not interiores:
        raise SystemExit(f"quadra do clube: nenhuma parte interior do ChaoPlato (partes: "
                         f"{[round(p.area) for p in partes(chao_plato)][:10]} m²)")
    return max(interiores, key=lambda p: p.area)


def pegada_de_triangulos(tris) -> object:
    """União dos triângulos; o milímetro a mais fecha as frestas de arredondamento e depois sai."""
    return unary_union([Polygon([(t[0], t[1]), (t[2], t[3]), (t[4], t[5])]).buffer(0.001, join_style="mitre")
                        for t in tris]).buffer(-0.001, join_style="mitre")


def pegada_portaria(tris, margem: float) -> Polygon:
    """Envoltória dos triângulos de topo da edificação + margem. Caixa não serve: parede solta sem topo
    estica a caixa do objeto por centenas de metros."""
    pts = [(t[i], t[i + 1]) for t in tris for i in (0, 2, 4)]
    return MultiPoint(pts).convex_hull.buffer(margem, join_style="mitre")


def cobertura(chao, quadra) -> float:
    return chao.intersection(quadra).area / quadra.area


def _centro(caixas) -> np.ndarray:
    x0 = min(c[0] for c in caixas); y0 = min(c[1] for c in caixas)
    x1 = max(c[3] for c in caixas); y1 = max(c[4] for c in caixas)
    return np.array([(x0 + x1) / 2, (y0 + y1) / 2])


def _borda(g, passo: float = 1.0) -> np.ndarray:
    from scripts.entorno.masterplan import amostrar

    return np.vstack([amostrar(np.array(anel.coords[:-1]), passo) for p in partes(g)
                      for anel in [p.exterior, *p.interiors] if len(anel.coords) > 3])


def _chao_clube(tris, pivo, giro, t: Semelhanca) -> object:
    """Triângulos de chão do clube no referencial local: desfaz o giro e aplica a transformação."""
    pts = np.asarray(tris, dtype=float).reshape(-1, 2)
    pts = t.aplicar(girar(pts, pivo, -giro))
    return pegada_de_triangulos(pts.reshape(-1, 6).tolist())


def encaixar(fonte: dict, cfg: MarcosCfg, circulos, pecas: dict, plato, cota: float, alturas: dict,
             vias_dwg) -> dict:
    clube_d, port_d = fonte[cfg.clube], fonte[cfg.portaria]
    cx = [c for n, c in clube_d["objetos"].items() if n.startswith("CLUBE_")]
    ilha_cx = [c for n, c in port_d["objetos"].items() if n.startswith("ROTATORIA_")]
    port_topo = [tr for n, ts in port_d["topo"].items()
                 if n.startswith("PORTARIA_") and n.split("_", 1)[1].split(".")[0] in cfg.edificacao for tr in ts]
    pivo = tuple(cfg.pivo_clube)
    clube_c = girar(_centro(cx)[None], pivo, -cfg.giro_clube)[0]
    ilha_c = _centro(ilha_cx)
    raio_ilha = max(max(c[3] for c in ilha_cx) - min(c[0] for c in ilha_cx),
                    max(c[4] for c in ilha_cx) - min(c[1] for c in ilha_cx)) / 2
    quadra = quadra_do_clube(pecas["ChaoPlato"], plato)
    qc = (quadra.centroid.x, quadra.centroid.y)
    circ = escolher_circulo(circulos, raio_ilha, float(np.hypot(*(ilha_c - clube_c))), qc, cfg.tol_raio, cfg.tol_dist)
    inicial = ancora(ilha_c, clube_c, circ[:2], qc)
    chao_port = pegada_de_triangulos([t for n, ts in port_d["chao"].items() if n.startswith("PORTARIA_PISO") for t in ts])
    destino = _borda(vias_dwg.intersection(Point(circ[:2]).buffer(cfg.raio_icp)))
    t, residuo = icp_rigido(_borda(chao_port), destino, inicial, corte=cfg.corte_icp)
    print(f"encaixe: âncora {math.degrees(inicial.theta):+.2f}° → ICP {math.degrees(t.theta):+.2f}°, "
          f"({t.tx:.2f}; {t.ty:.2f}) m, resíduo mediano {residuo:.2f} m, círculo r={circ[2]} em {circ[:2]}")
    if residuo > cfg.residuo_max:
        raise SystemExit(f"encaixe: resíduo {residuo:.2f} m acima de {cfg.residuo_max} m")
    clube_final = t.aplicar(clube_c[None])[0]
    if not quadra.contains(Point(clube_final)):
        raise SystemExit(f"encaixe: o clube caiu fora da quadra central ({clube_final.round(1)})")
    # projeção de tudo que olha para cima, em qualquer altura: prédio, piscina e deck também cobrem a quadra
    cob = cobertura(_chao_clube([tr for ts in clube_d["topo"].values() for tr in ts], pivo, cfg.giro_clube, t), quadra)
    print(f"encaixe: projeção do clube cobre {cob:.0%} da quadra ({quadra.area:.0f} m²)")
    if cob < cfg.cobertura_min:
        raise SystemExit(f"encaixe: projeção do clube cobre {cob:.0%} da quadra (mínimo {cfg.cobertura_min:.0%})")
    port_peg = pegada_portaria(t.aplicar(np.asarray(port_topo, dtype=float).reshape(-1, 2)).reshape(-1, 6).tolist(),
                               cfg.margem_portaria)
    ilha_peg = Point(circ[:2]).buffer(circ[2], 128)
    tj = {"s": 1.0, "theta": t.theta, "tx": t.tx, "ty": t.ty}
    anel = lambda g: [[round(x, 3), round(y, 3)] for x, y in g.exterior.coords[:-1]]  # noqa: E731
    return {"cota": cota, "marcos": {
        "Clube": {"fonte": cfg.clube, "prefixo": "CLUBE_", "giro": [*pivo, -cfg.giro_clube], "transf": tj,
                  "z": round(cota + alturas["ChaoPlato"], 3), "pegada": anel(quadra)},
        "Portaria": {"fonte": cfg.portaria, "prefixo": "PORTARIA_", "giro": None, "transf": tj,
                     "z": round(cota, 3), "pegada": anel(port_peg)},
        "Rotatoria": {"fonte": cfg.portaria, "prefixo": "ROTATORIA_", "giro": None, "transf": tj,
                      "z": round(cota, 3), "pegada": anel(ilha_peg)},
    }}


DESTINO = RAIZ / "cache" / "cena" / "marcos.json"


def main() -> int:
    from scripts.loteamento.cena import CFG_TOML as CENA_TOML
    from scripts.loteamento.cena import DXF, TERRENO_JSON, CenaCfg, aneis_da_layer, pecas_da_placa
    from scripts.loteamento.placa import PlacaCfg
    from scripts.loteamento.relevo import Grade
    from scripts.loteamento.terreno import TerrenoCfg, aneis_do_plato

    from .blender import FONTE_JSON

    sys.stdout.reconfigure(encoding="utf-8")
    cfg = MarcosCfg.carregar()
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    msp = ezdxf.readfile(DXF).modelspace()
    ccfg, pcfg = CenaCfg.carregar(CENA_TOML), PlacaCfg.carregar(CENA_TOML)
    pecas, plato = pecas_da_placa(msp, lotes, ccfg, pcfg, aneis_do_plato(msp, TerrenoCfg.carregar(CENA_TOML), lotes, e0, n0),
                                  e0, n0)
    grade = Grade.de_json(json.loads(TERRENO_JSON.read_text(encoding="utf-8")))
    cota = grade.cota_malha(*plato.representative_point().coords[0])
    layers = [l for ls in ccfg.camadas.values() for l in ls]
    circulos = [(round(e.dxf.center.x - e0, 3), round(e.dxf.center.y - n0, 3), round(e.dxf.radius, 3))
                for e in msp.query("CIRCLE") if e.dxf.layer in layers]
    vias = unary_union([pecas[k] for k in ("Pista", "Calcadas") if k in pecas])
    fonte = json.loads(FONTE_JSON.read_text(encoding="utf-8"))
    DESTINO.write_text(json.dumps(encaixar(fonte, cfg, circulos, pecas, plato, cota, pcfg.alturas, vias)),
                       encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
