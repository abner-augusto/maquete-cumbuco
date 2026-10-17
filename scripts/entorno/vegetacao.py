"""Vegetação: posições das três espécies para o front instanciar (vegetacao.glb), já com a cota
do relevo. Zonas do OSM no raio da vegetação e coqueiros nos canteiros estreitos da Fase 1.

Uso: uv run python -m scripts.entorno.vegetacao
"""

import json
import math
import random
import sys

import ezdxf
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

from scripts.comum.ambiente import RAIZ
from scripts.loteamento.cena import CFG_TOML, DXF, CenaCfg, aneis_da_layer
from scripts.loteamento.placa import PlacaCfg
from scripts.loteamento.terreno import DESTINO_ENTORNO, Relevo, TerrenoCfg, aneis_do_plato

from .extrair import BASE, CACHE, EntornoCfg
from .preparar import faixas

DESTINO = CACHE / "vegetacao.json"
ESPECIES = ("coqueiro", "cajueiro", "arbusto")
ESCALA = {"coqueiro": (0.8, 1.2), "cajueiro": (0.75, 1.25), "arbusto": (0.7, 1.3)}
# Zona OSM -> (m² por árvore, mistura). Em sobreposição vale a primeira. Densidades para ler
# como mata a 1 km de câmera, não para contar árvores.
ZONAS = [
    ("mata", lambda t: t.get("landuse") == "forest" or t.get("natural") == "wood", 120,
     {"cajueiro": 0.7, "coqueiro": 0.3}),
    ("restinga", lambda t: t.get("natural") in ("scrub", "heath", "grassland"), 80,
     {"arbusto": 0.8, "cajueiro": 0.2}),
    ("varzea", lambda t: t.get("natural") == "wetland", 70, {"coqueiro": 0.5, "arbusto": 0.5}),
    ("parque", lambda t: t.get("leisure") in ("park", "garden")
     or t.get("landuse") in ("recreation_ground", "village_green"), 250, {"cajueiro": 0.6, "coqueiro": 0.4}),
    ("quintais", lambda t: t.get("landuse") == "residential", 500, {"coqueiro": 0.5, "cajueiro": 0.5}),
    ("campo", lambda t: t.get("landuse") in ("grass", "meadow", "farmland", "orchard"), 900, {"cajueiro": 1.0}),
]
OFFSET_CANTEIRO = PlacaCfg.carregar(CFG_TOML).alturas["Verdes"]  # coqueiro no topo do verde da placa


def pontos_zona(zona, m2: float, mistura: dict[str, float], sorte: random.Random) -> list[tuple[float, float, str]]:
    """Grade com sorteio dentro de cada célula: uma árvore a cada `m2`."""
    if zona.is_empty:
        return []
    dentro = prep(zona)
    passo = math.sqrt(m2)
    x0, y0, x1, y1 = zona.bounds
    nomes, pesos = zip(*mistura.items())
    pts = []
    for i in range(int((x1 - x0) / passo) + 1):
        for j in range(int((y1 - y0) / passo) + 1):
            x, y = x0 + (i + sorte.random()) * passo, y0 + (j + sorte.random()) * passo
            if dentro.contains(Point(x, y)):
                pts.append((x, y, sorte.choices(nomes, pesos)[0]))
    return pts


def canteiros(aneis: list[list[tuple[float, float]]], largura_max: float = 8.0, passo: float = 12.0) -> list[tuple[float, float]]:
    """Coqueiros no eixo dos canteiros: anel estreito (2·área/perímetro < largura_max) e comprido.
    Pontos na borda a cada `passo`, levados meia largura para dentro; vizinhos a < passo/2 viram um."""
    pts: list[tuple[float, float]] = []
    for anel in aneis:
        p = Polygon(anel).buffer(0)
        if p.is_empty or p.length == 0:
            continue
        largura = 2 * p.area / p.length
        if largura >= largura_max or p.length < 4 * passo:
            continue
        borda = p.exterior
        for k in range(int(borda.length / passo)):
            a, b = borda.interpolate(k * passo), borda.interpolate(k * passo + 0.5)
            dx, dy = b.x - a.x, b.y - a.y
            n = math.hypot(dx, dy) or 1.0
            for s in (1, -1):
                c = (a.x - s * dy / n * largura / 2, a.y + s * dx / n * largura / 2)
                if p.contains(Point(c)) and all(math.dist(c, q) >= passo / 2 for q in pts):
                    pts.append(c)
    return pts


def instancias(pontos: list[tuple[float, float, str]], relevo, nivel_mar: float, sorte: random.Random,
               offset: float = 0.0) -> dict[str, list[int]]:
    """Planos [x_dm, y_dm, z_cm, escala_pct, rotacao_graus] por espécie, embaralhados (as N
    primeiras são uma amostra uniforme: o app escolhe N pelo aparelho). Ponto no mar sai."""
    saida = {e: [] for e in ESPECIES}
    for x, y, esp in pontos:
        z = relevo.cota(x, y)
        if z <= nivel_mar + 0.5:
            continue
        lo, hi = ESCALA[esp]
        saida[esp].append([round(x * 10), round(y * 10), round((z + offset) * 100),
                           round(sorte.uniform(lo, hi) * 100), sorte.randrange(360)])
    for lista in saida.values():
        sorte.shuffle(lista)
    return {e: [c for inst in v for c in inst] for e, v in saida.items()}


def _poligono(a):
    return Polygon(a[0], a[1:]).buffer(0)


def area_livre(base: dict, raio: float, plato, gleba=None):
    """Onde pode haver árvore: o raio menos o platô, vias, prédios, água, areia e o masterplan
    (as fases 2–10 são pintadas no chão; árvore por cima esconde o desenho)."""
    tirar = [
        plato.buffer(5), faixas(base["vias"], "via_principal").buffer(2), faixas(base["vias"], "via_local").buffer(1),
        *[_poligono(p).buffer(1.5) for pr in base["predios"] for p in pr["poligonos"]],
        *[_poligono(p) for a in base["areas"] if a["tipo"] in ("agua", "estacionamento", "areia") for p in a["poligonos"]],
    ]
    if gleba is not None:
        tirar.append(gleba)
    return Point(base["centro"]).buffer(raio, 128).difference(unary_union(tirar))


def plantar(base: dict, livre, sorte: random.Random) -> tuple[list[tuple[float, float, str]], dict[str, int]]:
    """As árvores de cada zona do OSM dentro de `livre`; onde duas zonas se sobrepõem vale a primeira."""
    pts, ja, por_zona = [], Polygon(), {}
    for nome, regra, m2, mistura in ZONAS:
        g = unary_union([_poligono(p) for a in base["areas"] if regra(a["tags"]) for p in a["poligonos"]])
        zona = g.difference(ja).intersection(livre)
        ja = ja.union(g)
        novos = pontos_zona(zona, m2, mistura, sorte)
        por_zona[nome] = len(novos)
        pts += novos
    return pts, por_zona


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = EntornoCfg.carregar()
    base = json.loads(BASE.read_text(encoding="utf-8"))
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    msp = ezdxf.readfile(DXF).modelspace()
    plato = unary_union([Polygon(a).buffer(0) for a in aneis_do_plato(msp, TerrenoCfg.carregar(CFG_TOML), lotes, e0, n0)
                         if len(a) >= 3])
    relevo = Relevo.carregar()
    nivel = next(o for o in json.loads(DESTINO_ENTORNO.read_text(encoding="utf-8"))["objetos"]
                 if o["nome"] == "Mar")["vertices"][0][2]
    gleba = None
    if cfg.masterplan:
        from .masterplan import META

        if META.exists():
            gleba = Polygon(json.loads(META.read_text(encoding="utf-8"))["gleba"]).buffer(0)
    livre = area_livre(base, cfg.raio_vegetacao, plato, gleba)
    sorte = random.Random(4)
    pts, por_zona = plantar(base, livre, sorte)
    if not pts:
        raise SystemExit("Nenhuma árvore nas zonas do OSM: áreas vazias no base.json? Rode o extrair com --refazer.")
    verdes = aneis_da_layer(msp, CenaCfg.carregar(CFG_TOML).camadas["Verdes"], e0, n0)
    inst = instancias(pts, relevo, nivel, sorte)
    cant = instancias([(x, y, "coqueiro") for x, y in canteiros(verdes)], relevo, nivel, sorte, offset=OFFSET_CANTEIRO)
    inst["coqueiro"] = cant["coqueiro"] + inst["coqueiro"]  # os da Fase 1 primeiro: sempre aparecem
    # A mata do OSM sob o masterplan: o front só a mostra com a projeção desligada (o chão volta a ser o OSM).
    sob_masterplan = {}
    if gleba is not None:
        sob = area_livre(base, cfg.raio_vegetacao, plato).intersection(gleba)
        extra, _ = plantar(base, sob, random.Random(5))
        sob_masterplan = instancias(extra, relevo, nivel, random.Random(6))
    DESTINO.write_text(json.dumps({
        "versao": 1,
        "referencial": "x = leste, y = norte em dm; z = cota em cm (sem exagero); no glTF, (x, z, -y)",
        "modelos": "vegetacao.glb (malhas VEG_<especie>, base em z = 0, em metros)",
        "campos": ["x_dm", "y_dm", "z_cm", "escala_pct", "rotacao_graus"],
        "canteiros_fase1": len(cant["coqueiro"]) // 5,
        "especies": {e: {"n": len(v) // 5, "instancias": v} for e, v in inst.items()},
        "sem_masterplan": {"especies": {e: {"n": len(v) // 5, "instancias": v} for e, v in sob_masterplan.items()}},
    }, separators=(",", ":")), encoding="utf-8")
    print(f"vegetação por zona {por_zona} · canteiros da Fase 1 {len(cant['coqueiro']) // 5} coqueiros · "
          f"por espécie { {e: len(v) // 5 for e, v in inst.items()} } · sob o masterplan { {e: len(v) // 5 for e, v in sob_masterplan.items()} } · {DESTINO.stat().st_size / 1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
