"""Etapa 2 do entorno: mapa do chão (vias e áreas pintadas), vias principais perto do loteamento
em faixa 3D e prédios extrudados, tudo assentado no relevo da cena.

Uso: uv run python -m scripts.entorno.preparar
"""

import json
import math
import sys
from pathlib import Path

import ezdxf
import numpy as np
from PIL import Image
from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import unary_union

from scripts.comum.ambiente import RAIZ
from scripts.loteamento.cena import CFG_TOML, DXF
from scripts.loteamento.malha import drapear, triangular
from scripts.loteamento.placa import ccw, aneis_orientados
from scripts.loteamento.acesso import Acesso, AcessoCfg, corredor, sem_faixa
from scripts.loteamento.terreno import (DESTINO_ENTORNO, DESTINO_LONGE, ZONA_LAGOA, Relevo, TerrenoCfg, aneis_do_plato,
                                        lagoa_do_masterplan)

from .extrair import BASE, CACHE, EntornoCfg
from .mapa import CORES, rasterizar
from .tiles import Ext, com_margem, janelas

MAPA_JSON = CACHE / "mapa.json"
DETALHE = RAIZ / "cache" / "cena" / "entorno-detalhe.json"
AREA_MINIMA_PREDIO_M2 = 8.0  # abaixo disso, ruído das pegadas por ML
AREA_MINIMA_PREDIO_LONGE_M2 = 30.0  # na faixa da orla, além do raio_predios: some de longe
OFFSET_FAIXA = 0.5  # m acima do relevo (0,3 deixava 0,9% da faixa sob o terreno)
BORDA_GLEBA = 5.0  # m: via do OSM com 80% do traçado até essa distância da divisa da gleba sai
MAX_ARESTA_FAIXA = 2.5  # m entre seções: segue o relevo de perto
ALTURA_QUEBRA_MAR = 1.5  # m acima do plano da água

# classe OSM -> (grupo, largura padrão em metros)
VIAS_CLASSES = {
    "motorway": ("via_principal", 14), "trunk": ("via_principal", 12), "primary": ("via_principal", 10),
    "secondary": ("via_principal", 9), "tertiary": ("via_principal", 8), "motorway_link": ("via_principal", 7),
    "trunk_link": ("via_principal", 7), "primary_link": ("via_principal", 7),
    "secondary_link": ("via_principal", 7), "tertiary_link": ("via_principal", 7),
    "unclassified": ("via_local", 6), "residential": ("via_local", 6), "living_street": ("via_local", 5),
    "service": ("via_local", 4), "track": ("via_local", 3), "pedestrian": ("via_local", 4),
    "footway": ("via_local", 2), "cycleway": ("via_local", 2), "path": ("via_local", 1.5),
}
ORDEM_AREAS = ["verde", "lazer", "areia", "estacionamento", "agua"]  # de baixo para cima


def _poligono(aneis):
    return Polygon(aneis[0], aneis[1:])


def _largura(via, padrao):
    try:
        return float(str(via["largura"]).replace(",", ".").split()[0])
    except (KeyError, TypeError, ValueError, IndexError):
        return padrao


def altura_predio(p: dict, area: float) -> float:
    if p.get("altura"):
        return round(float(p["altura"]), 2)
    if p.get("niveis"):
        return round(float(p["niveis"]) * 3.0 + 0.5, 2)
    if area < 60:
        return 3.2
    if area < 250:
        return 4.0
    if area < 1000:
        return 6.0
    return 8.0  # galpões, atacado, shopping


def pegada_longe(g: Polygon, tolerancia: float = 1.0) -> Polygon:
    """Pegada de prédio distante (faixa da orla, a 2–4 km da câmera): o retângulo mínimo quando a
    forma já é quase isso; senão, a forma simplificada a `tolerancia` m. Corta os triângulos do GLB."""
    r = g.minimum_rotated_rectangle
    return r if r.area and g.area / r.area > 0.85 else g.simplify(tolerancia)


def extrudar(aneis: list, relevo, altura: float,
             cotas: tuple[float, float] | None = None) -> tuple[list[list[float]], list[list[int]]]:
    """Caixa de teto plano: base na menor cota sob a pegada − 0,3 m (não flutua na encosta),
    teto na cota média + altura. Com `cotas` (base, teto), o relevo não entra (quebra-mar)."""
    # externo anti-horário e furos horários: a direita de cada lado é fora, a parede olha para fora
    externo, furos = aneis_orientados(Polygon(aneis[0], aneis[1:]))
    if cotas is not None:
        base, topo = cotas
    else:
        zs = [relevo.cota(x, y) for x, y in externo]
        base, topo = min(zs) - 0.3, sum(zs) / len(zs) + altura
    vt, tt = triangular(externo, furos)
    vertices = [[round(x, 2), round(y, 2), round(topo, 2)] for x, y in vt]
    faces = [[a, b, c] if ccw(vt[a], vt[b], vt[c]) else [a, c, b] for a, b, c in tt]  # teto para cima
    for anel in [externo, *furos]:
        for a, b in zip(anel, anel[1:] + anel[:1]):
            i = len(vertices)
            vertices += [[round(a[0], 2), round(a[1], 2), round(base, 2)], [round(b[0], 2), round(b[1], 2), round(base, 2)],
                         [round(b[0], 2), round(b[1], 2), round(topo, 2)], [round(a[0], 2), round(a[1], 2), round(topo, 2)]]
            faces += [[i, i + 1, i + 2], [i, i + 2, i + 3]]
    return vertices, faces


def sem_vias_na_divisa(vias: list[dict], gleba: Polygon) -> list[dict]:
    """Tira as vias do OSM que correm pela divisa da gleba: o masterplan desenha o acesso real ali, e a
    metade de fora da faixa pintada aparecia como uma segunda estrada ao lado da CE."""
    borda = gleba.exterior.buffer(BORDA_GLEBA)
    return [v for v in vias if (l := LineString(v["pontos"])).length == 0
            or l.intersection(borda).length < 0.8 * l.length]


def faixas(vias: list[dict], grupo: str) -> object:
    return unary_union([LineString(v["pontos"]).buffer(_largura(v, VIAS_CLASSES[v["classe"]][1]) / 2, quad_segs=3)
                        for v in vias if VIAS_CLASSES.get(v["classe"], ("", 0))[0] == grupo])


def faixa_3d(pontos: list, largura: float, relevo, offset: float, passo: float = MAX_ARESTA_FAIXA,
             fora=None) -> tuple[list[list[float]], list[list[int]]]:
    """Faixa pelo eixo da via: uma seção transversal a cada `passo` m, assentada no relevo. Trecho
    com o meio dentro de `fora` (o platô) sai. Triangular o polígono unido dava diagonais de centenas
    de metros, que cortavam o relevo ou explodiam no refino."""
    eixo = []
    for a, b in zip(pontos, pontos[1:]):
        n = max(1, math.ceil(math.dist(a, b) / passo))
        eixo += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    eixo.append(tuple(pontos[-1]))
    vertices, faces = [], []
    secao = []
    for i, (x, y) in enumerate(eixo):
        a, b = eixo[max(i - 1, 0)], eixo[min(i + 1, len(eixo) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / n * largura / 2, dx / n * largura / 2
        secao.append([(x + nx, y + ny), (x, y), (x - nx, y - ny)])  # o eixo também: o relevo dobra no meio
    prepara = fora.contains if fora is not None else (lambda p: False)
    for i in range(len(eixo) - 1):
        meio = Point((eixo[i][0] + eixo[i + 1][0]) / 2, (eixo[i][1] + eixo[i + 1][1]) / 2)
        if prepara(meio):
            continue
        base = len(vertices)
        vertices += drapear(secao[i] + secao[i + 1], relevo, offset)
        for k in range(2):
            a0, a1, c0, c1 = base + k, base + k + 1, base + 3 + k, base + 4 + k
            faces += [[a0, a1, c1], [a0, c1, c0]]
    return vertices, faces


def gerar_tiles(camadas, ext: Ext, passo: float, px: int, margem_px: int, pasta: Path, pos=None) -> dict[str, dict]:
    """Um JPEG por janela, com `margem_px` de borda; `pos(img, ext_m)` pinta por cima (o masterplan)."""
    tiles = {}
    for k, jan in janelas(ext, passo).items():
        ext_m = com_margem(jan, px, margem_px)
        img = rasterizar(camadas, ext_m, px)
        if pos is not None:
            img = pos(img, ext_m)
        arquivo = pasta / f"mapa_{k}.jpg"
        img.save(arquivo, quality=85)
        tiles[k] = {"arquivo": str(arquivo), "ext": list(ext_m), "janela": list(jan), "px": list(img.size)}
    return tiles


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = EntornoCfg.carregar()
    base = json.loads(BASE.read_text(encoding="utf-8"))
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    aneis = aneis_do_plato(ezdxf.readfile(DXF).modelspace(), TerrenoCfg.carregar(CFG_TOML), lotes,
                           georref["origem"]["E"], georref["origem"]["N"])
    acesso, acfg = Acesso.carregar(), AcessoCfg.carregar(CFG_TOML)
    if acesso is None:
        raise SystemExit("sem cache/cena/acesso.json: rode uv run python -m scripts.loteamento.terreno")
    # o platô sem a faixa do acesso, que desce até a CE; a avenida em rampa entra à parte
    plano = unary_union([Polygon(a).buffer(0) for a in sem_faixa(aneis, acesso, acfg) if len(a) >= 3])
    area_acesso = corredor(acesso, acfg)
    plato = plano.union(area_acesso)
    relevo = Relevo.carregar()
    centro = tuple(base["centro"])
    longe = json.loads(DESTINO_LONGE.read_text(encoding="utf-8"))
    ext = (longe["x0"], longe["y0"], longe["x0"] + longe["passo"] * (longe["nx"] - 1),
           longe["y0"] + longe["passo"] * (longe["ny"] - 1))

    if cfg.masterplan:
        from .masterplan import META

        if not META.exists():
            raise SystemExit("masterplan = true sem cache: rode uv run python -m scripts.entorno.masterplan")
        n = len(base["vias"])
        base["vias"] = sem_vias_na_divisa(base["vias"],
                                          Polygon(json.loads(META.read_text(encoding="utf-8"))["gleba"]).buffer(0))
        print(f"vias na divisa da gleba removidas: {n - len(base['vias'])}")
    lagoa = lagoa_do_masterplan() if cfg.masterplan else None
    camadas = []
    for tipo in ORDEM_AREAS:
        g = unary_union([_poligono(p).buffer(0) for a in base["areas"] if a["tipo"] == tipo for p in a["poligonos"]])
        if tipo == "agua" and lagoa is not None:  # perto do masterplan, a água é a lagoa do R05 (pintada por cima)
            g = g.difference(lagoa[0].buffer(ZONA_LAGOA))
        if not g.is_empty:
            camadas.append((tipo, g))
    camadas += [("via_local", faixas(base["vias"], "via_local")), ("via_principal", faixas(base["vias"], "via_principal")),
                ("solo", plato)]  # o platô fica liso: o loteamento é desenhado por cima
    pos = None
    if cfg.masterplan:
        from .masterplan import META, pintar, pintar_por_cima

        if not META.exists():
            raise SystemExit("masterplan = true sem cache: rode uv run python -m scripts.entorno.masterplan")
        meta = json.loads(META.read_text(encoding="utf-8"))
        mp_img = Image.open(meta["arquivo"])
        tcfg = TerrenoCfg.carregar(CFG_TOML)
        mascara = Polygon(meta["gleba"]).buffer(0).difference(plato.buffer(tcfg.plato_folga + tcfg.talude))
        rio = shape(meta["rio"])
        # a avenida só fora do platô: dentro dele a Fase 1 já tem as suas, e as duas se encontram na borda
        vias_fases = shape(meta["vias"]).intersection(Polygon(meta["gleba"]).buffer(0)).difference(plato)
        por_cima = [(CORES["agua"], rio), (CORES["via_principal"], vias_fases)]
        pos = lambda img, ext_m: pintar_por_cima(  # noqa: E731
            pintar(img, ext_m, mp_img, meta, mascara, cfg.masterplan_saturacao, cfg.masterplan_opacidade),
            ext_m, por_cima)
    tiles = gerar_tiles(camadas, ext, longe["passo"], cfg.tile_px, cfg.tile_margem_px, CACHE, pos)
    MAPA_JSON.write_text(json.dumps({"tiles": tiles}), encoding="utf-8")

    fora = plano.buffer(10).union(area_acesso)  # a CE encosta na boca do acesso: sem folga ali
    if cfg.masterplan:
        fora = fora.union(mascara).union(rio)  # sobre o masterplan e a lagoa, nem faixa nem prédio do OSM
    circulo = Point(centro).buffer(cfg.raio_faixas, 128)
    vf, ff = [], []
    for via in base["vias"]:
        grupo, padrao = VIAS_CLASSES.get(via["classe"], ("", 0))
        if grupo != "via_principal":
            continue
        cortada = LineString(via["pontos"]).intersection(circulo)
        for t in getattr(cortada, "geoms", [cortada]):
            if t.is_empty or t.geom_type != "LineString":
                continue
            v, f = faixa_3d([list(c) for c in t.coords], _largura(via, padrao), relevo, OFFSET_FAIXA, fora=fora)
            ff += [[a + len(vf), b + len(vf), c + len(vf)] for a, b, c in f]
            vf += v
    vp, fp, n = [], [], 0
    perto_predios = Point(centro).buffer(cfg.raio_predios, 128)
    for p in base["predios"]:
        g = unary_union([_poligono(q) for q in p["poligonos"]]).buffer(0).simplify(0.2)
        if not perto_predios.contains(g.centroid):
            if g.area < AREA_MINIMA_PREDIO_LONGE_M2:
                continue
            g = unary_union([pegada_longe(q) for q in getattr(g, "geoms", [g])])
        if g.area < AREA_MINIMA_PREDIO_M2 or g.intersects(fora):
            continue
        for parte in getattr(g, "geoms", [g]):
            aneis = [list(parte.exterior.coords)] + [list(i.coords) for i in parte.interiors]
            v, f = extrudar(aneis, relevo, altura_predio(p, parte.area))
            fp += [[a + len(vp), b + len(vp), c + len(vp)] for a, b, c in f]
            vp += v
        n += 1
    # Quebra-mares: do fundo do mar a 1,5 m acima da água, em pedra.
    nivel = next(o for o in json.loads(DESTINO_ENTORNO.read_text(encoding="utf-8"))["objetos"]
                 if o["nome"] == "Mar")["vertices"][0][2]
    vq, fq = [], []
    for aneis_q in base.get("quebra_mares", []):
        v, f = extrudar([[tuple(p) for p in a] for a in aneis_q], None, 0.0,
                        cotas=(round(nivel - TerrenoCfg.carregar(CFG_TOML).mar_rebaixo, 2), round(nivel + ALTURA_QUEBRA_MAR, 2)))
        fq += [[a + len(vq), b + len(vq), c + len(vq)] for a, b, c in f]
        vq += v
    objetos = [
        {"nome": "ViasPrincipais", "material": "via_principal_osm", "vertices": vf, "faces": ff},
        {"nome": "Predios", "material": "predio", "vertices": vp, "faces": fp, "suave": False},
    ]
    if fq:
        objetos.append({"nome": "QuebraMares", "material": "pedra", "vertices": vq, "faces": fq, "suave": False})
    DETALHE.write_text(json.dumps({"objetos": objetos}), encoding="utf-8")
    print(f"tiles {len(tiles)} × {cfg.tile_px} px ({(ext[2] - ext[0]) / 2 / cfg.tile_px:.2f} m/px) · "
          f"faixas {len(ff)} tri · prédios {n} ({len(fp)} tri) · quebra-mares {len(fq)} tri · cota média do relevo nos prédios "
          f"{np.mean([z for _, _, z in vp]) if vp else 0:.1f} m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
