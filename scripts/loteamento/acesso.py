"""Acesso da CE ao loteamento: a faixa do DWG entre a rotatória e a CE vira avenida em rampa.

O platô fica a ~21 m e a CE no chão natural, ~17 m abaixo. O eixo sai do centro da rotatória pela
faixa do DWG; a seção é a da avenida (calçada, pista, canteiro, pista, calçada); o perfil é plano na
rotatória, rampa constante e um patamar antes da CE, com curvas verticais nas quebras. Na CE, as bordas
abrem em curva (raio `raio_boca`) e o canteiro termina numa ilha triangular.

Python puro: terreno.py calcula o acesso (precisa do chão natural na CE) e grava cache/cena/acesso.json;
cena.py monta as peças em rampa; preparar.py tira a faixa do platô.
"""

import json
import math
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from scripts.comum.ambiente import RAIZ

from .malha import triangular
from .placa import aneis_orientados, ccw, paredes, partes

DESTINO = RAIZ / "cache" / "cena" / "acesso.json"
ALTURAS = {"AcessoPista": 0.0, "AcessoCalcadas": 0.25, "AcessoCanteiro": 0.25}  # como Pista, Calcadas e Verdes
MATERIAIS = {"AcessoPista": "vias", "AcessoCalcadas": "calcadas", "AcessoCanteiro": "verdes"}


@dataclass(frozen=True)
class AcessoCfg:
    camada_via: str          # layer do DWG com a faixa de acesso
    recuo_inicio: float      # m antes do começo da faixa: o braço da rotatória termina num corte inclinado
    secao: list[float]       # larguras: calçada, pista, canteiro, pista, calçada
    raio_boca: float         # m, curva das bordas na CE
    patamar: float           # m quase planos antes da CE, onde a conversão acontece
    patamar_inclinacao: float
    curva_vertical: float    # m de cada curva vertical (parábola) nas quebras do perfil
    rampa_max: float
    passo: float             # m: aresta máxima das peças em rampa
    folga_ce: float          # m além da meia largura da CE que ficam no chão natural
    ilha_base: float
    ilha_comprimento: float
    ilha_recuo: float        # m entre a base da ilha e a borda da CE

    @classmethod
    def carregar(cls, caminho: Path) -> "AcessoCfg":
        return cls(**tomllib.loads(caminho.read_text(encoding="utf-8"))["acesso"])


@dataclass(frozen=True)
class Acesso:
    c0: tuple[float, float]  # centro da rotatória
    d: tuple[float, float]   # direção do eixo, para a CE
    s_ini: float             # começo da faixa (borda da rotatória)
    s_fim: float             # borda da CE no eixo
    pvis: list[tuple[float, float]]  # perfil (s, z)
    ce: list | None = None   # anéis da faixa da CE perto da boca (para a curva das bordas)

    def local(self, xy) -> tuple[np.ndarray, np.ndarray]:
        p = np.asarray(xy, dtype=float) - self.c0
        d = np.asarray(self.d)
        return p @ d, p @ np.array([-d[1], d[0]])

    def salvar(self, caminho: Path = DESTINO) -> None:
        caminho.write_text(json.dumps(asdict(self)), encoding="utf-8")

    @classmethod
    def carregar(cls, caminho: Path = DESTINO) -> "Acesso | None":
        if not caminho.exists():
            return None
        d = json.loads(caminho.read_text(encoding="utf-8"))
        return cls(tuple(d["c0"]), tuple(d["d"]), d["s_ini"], d["s_fim"], [tuple(p) for p in d["pvis"]], d.get("ce"))


def perfil_vertical(pvis: list[tuple[float, float]], curva: float):
    """z(s) pelos pontos de inflexão, com parábola de comprimento `curva` em cada inflexão interna
    (encurtada se o trecho não couber). Antes do primeiro e depois do último ponto, segue a rampa da ponta."""
    s = np.array([p[0] for p in pvis], dtype=float)
    z = np.array([p[1] for p in pvis], dtype=float)
    g = np.diff(z) / np.diff(s)
    meias = [min(curva / 2, (s[i] - s[i - 1]) / 2, (s[i + 1] - s[i]) / 2) for i in range(1, len(s) - 1)]

    def zs(x: float) -> float:
        x = float(x)
        if x <= s[0]:
            return float(z[0] + g[0] * (x - s[0]))
        i = min(int(np.searchsorted(s, x, side="right")) - 1, len(g) - 1)
        for k, m in enumerate(meias, start=1):  # parábola perto de cada inflexão
            if abs(x - s[k]) < m:
                u = x - (s[k] - m)
                return float(z[k] - g[k - 1] * m + g[k - 1] * u + (g[k] - g[k - 1]) / (4 * m) * u * u)
        return float(z[i] + g[i] * (x - s[i]))

    return zs


def perfil_acesso(s_ini: float, s_fim: float, z0: float, z_fim: float, cfg: AcessoCfg
                  ) -> tuple[list[tuple[float, float]], float]:
    """Plano até a primeira curva (que começa em s_ini), rampa, patamar de `cfg.patamar` m até a CE."""
    s_rampa = s_ini + cfg.curva_vertical / 2
    s_pat = s_fim - cfg.patamar
    z_pat = z_fim + cfg.patamar * cfg.patamar_inclinacao
    if s_pat - s_rampa < cfg.curva_vertical:
        raise SystemExit(f"acesso: sem espaço para a rampa ({s_pat - s_rampa:.1f} m entre as curvas)")
    rampa = (z_pat - z0) / (s_pat - s_rampa)
    if abs(rampa) > cfg.rampa_max:
        raise SystemExit(f"acesso: rampa de {abs(rampa):.1%} acima de {cfg.rampa_max:.0%}")
    return [(s_ini, z0), (s_rampa, z0), (s_pat, round(z_pat, 3)), (s_fim, z_fim)], rampa


def eixo_da_faixa(faixa: Polygon, circulos: list[tuple[float, float, float]], recuo: float = 0.0
                  ) -> tuple[tuple[float, float], tuple[float, float], float, float]:
    """Centro da rotatória (o círculo mais perto da faixa), direção do lado comprido da faixa, para longe
    dele, e o começo (`recuo` m antes do ponto mais recuado da faixa) e o fim da faixa no eixo."""
    cx, cy, _ = min(circulos, key=lambda c: faixa.distance(Point(c[0], c[1])))
    r = np.array(faixa.minimum_rotated_rectangle.exterior.coords)[:4]
    lados = [r[1] - r[0], r[2] - r[1]]
    d = max(lados, key=lambda v: np.hypot(*v))
    d = d / np.hypot(*d)
    if np.dot(np.array(faixa.centroid.coords[0]) - (cx, cy), d) < 0:
        d = -d
    s = (np.array(faixa.exterior.coords) - (cx, cy)) @ d
    return (cx, cy), (float(d[0]), float(d[1])), float(s.min()) - recuo, float(s.max())


def _mundo(a: Acesso, g: BaseGeometry) -> BaseGeometry:
    dx, dy = a.d
    return affinity.affine_transform(g, [dx, -dy, dy, dx, a.c0[0], a.c0[1]])


def _local(a: Acesso, g: BaseGeometry) -> BaseGeometry:
    dx, dy = a.d
    p = affinity.translate(g, -a.c0[0], -a.c0[1])
    return affinity.affine_transform(p, [dx, dy, -dy, dx, 0.0, 0.0])


def _borda_ce(ce_l: BaseGeometry, s_fim: float) -> tuple[np.ndarray, np.ndarray]:
    """Um ponto e a direção da borda da CE onde o eixo chega (perto da boca a CE é reta)."""
    anel = min((q.exterior for q in partes(ce_l)), key=lambda r: r.distance(Point(s_fim, 0.0)))
    k = anel.project(Point(s_fim, 0.0))
    p1, p2 = (np.array(anel.interpolate(k + dk).coords[0]) for dk in (-5.0, 5.0))
    e = (p2 - p1) / np.hypot(*(p2 - p1))
    q = np.array(anel.interpolate(k).coords[0])
    return q + e * (-q[1] / e[1]), e  # o ponto em t = 0


def pecas_acesso(a: Acesso, ce: BaseGeometry, cfg: AcessoCfg) -> dict[str, BaseGeometry]:
    """Pista, calçadas e canteiro (com a ilha) do acesso, no referencial do mundo. `ce`: a faixa da CE.

    Em cada lado, a borda da avenida concorda com a borda da CE por um arco tangente às duas. A CE cruza
    na diagonal: o lado do ângulo agudo (a conversão mais fechada) leva `raio_boca`; o outro, o raio que
    dá a mesma tangente, e a boca abre o mesmo tanto ao longo da CE. A calçada é a faixa de `w` m ao longo
    da borda e do arco; o arco de dentro (raio + w) corta a borda da CE antes, e a calçada termina afinando."""
    h = sum(cfg.secao) / 2
    w, c = cfg.secao[0], cfg.secao[2] / 2
    ce_l = _local(a, ce).intersection(box(a.s_ini, -h - 200, a.s_fim + 200, h + 200))
    P, e = _borda_ce(ce_l, a.s_fim)
    nn = np.array([-e[1], e[0]])
    nn = nn if nn[0] < 0 else -nn  # normal da borda da CE para o lado da avenida
    grande = 1e4
    lado_avenida = lambda recuo: Polygon([P + nn * recuo + e * grande, P + nn * recuo - e * grande,  # noqa: E731
                                          P + nn * grande - e * grande, P + nn * grande + e * grande])
    cantos = {}
    for sig in (1.0, -1.0):
        C = P + e * ((sig * h - P[1]) / e[1])
        u1, u2 = np.array([-1.0, 0.0]), (e if e[1] * sig > 0 else -e)
        cantos[sig] = (C, u1, u2, math.pi - math.acos(float(np.clip(u1 @ u2, -1, 1))))
    tang = cfg.raio_boca * math.tan(max(d for *_, d in cantos.values()) / 2)
    curvas, bordas = [], []
    for sig, (C, u1, u2, defl) in cantos.items():
        R = tang / math.tan(defl / 2)
        T1, T2 = C + u1 * tang, C + u2 * tang
        O = T1 + np.array([0.0, sig]) * R
        a1, a2 = (math.atan2(*(T - O)[::-1]) for T in (T1, T2))
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        arco = [O + R * np.array([math.cos(a1 + da * k / 64), math.sin(a1 + da * k / 64)]) for k in range(65)]
        curvas.append(Polygon([T1, C, T2]).difference(Point(O).buffer(R, quad_segs=64)))
        borda = LineString([(a.s_ini, sig * h), *[tuple(q) for q in arco], tuple(T2 + u2 * 2 * w)])
        bordas.append(borda.buffer(-sig * w, single_sided=True))  # para o lado da avenida
    s_longe = max(C[0] for C, *_ in cantos.values()) + 1.0
    # a boca vai até a borda real da CE (que faz curva), não só até a reta tangente: sem fresta entre as duas
    t2 = [C + u2 * tang for C, _, u2, _ in cantos.values()]
    soleira = Polygon([t2[0], t2[1], t2[1] - nn * 3.0, t2[0] - nn * 3.0])  # da reta tangente até 3 m CE adentro
    total = unary_union([box(a.s_ini, -h, s_longe, h), *curvas, soleira])
    total = max(partes(total.difference(ce_l)), key=lambda q: q.area)
    inicio = box(a.s_ini, -grande, grande, grande)
    calcadas = unary_union(bordas).intersection(total).intersection(inicio)
    s_ponta = a.s_fim - cfg.ilha_recuo - cfg.ilha_comprimento
    b = cfg.ilha_base / 2
    s_x = a.s_fim + 20.0  # a ilha abre de c a b na base (a `ilha_recuo` m da CE) e segue até ser cortada
    m = c + (b - c) * (s_x - s_ponta) / cfg.ilha_comprimento
    canteiro = Polygon([(a.s_ini, -c), (s_ponta, -c), (s_x, -m), (s_x, m), (s_ponta, c),
                        (a.s_ini, c)]).intersection(lado_avenida(cfg.ilha_recuo))  # base paralela à CE
    pista = total.difference(calcadas).difference(canteiro)
    pecas = {"AcessoPista": pista, "AcessoCalcadas": calcadas.difference(canteiro), "AcessoCanteiro": canteiro}
    return {k: _mundo(a, shapely.set_precision(g, 0.001)) for k, g in pecas.items() if not g.is_empty}


def dz(a: Acesso, cfg: AcessoCfg, xy, cota: float) -> np.ndarray:
    """Quanto cada ponto do acesso desce em relação à cota do platô (zero até o começo da rampa)."""
    zs = perfil_vertical(a.pvis, cfg.curva_vertical)
    s, _ = a.local(np.atleast_2d(xy))
    return np.array([zs(min(max(x, a.s_ini), a.s_fim)) for x in s]) - cota


def _topo_em_faixas(a: Acesso, g: BaseGeometry, passo: float) -> tuple[list[list[float]], list[list[int]]]:
    """Topo cortado em faixas de `passo` m perpendiculares ao eixo, cada uma triangulada à parte: como a
    cota só varia ao longo do eixo, o triângulo curto nessa direção já segue o perfil (refinar as arestas
    dos triângulos compridos do earcut multiplicava a malha)."""
    loc = _local(a, g)
    s0, t0, s1, t1 = loc.bounds
    vs, fs = [], []
    for k in range(int(math.floor(s0 / passo)), int(math.ceil(s1 / passo))):
        faixa = loc.intersection(box(k * passo, t0 - 1, (k + 1) * passo, t1 + 1))
        for p in partes(_mundo(a, faixa)):
            ext, furos = aneis_orientados(p)
            v, t = triangular(ext, furos)
            base = len(vs)
            vs += [[x, y] for x, y in v]
            fs += [[base + i, base + j, base + k_] if ccw(v[i], v[j], v[k_]) else [base + i, base + k_, base + j]
                   for i, j, k_ in t]
    return vs, fs


def montar_acesso(a: Acesso, pecas: dict[str, BaseGeometry], vizinhos: dict[str, tuple[BaseGeometry, float]],
                  cota: float, fundo: float, cfg: AcessoCfg) -> list[dict]:
    """Objetos de cena das peças do acesso: topo refinado a `cfg.passo` e paredes, tudo descido pelo perfil.
    `vizinhos`: as peças planas da placa (geometria, altura), para a parede só onde ninguém encosta."""
    todos = {**{k: (g, ALTURAS[k]) for k, g in pecas.items()}, **vizinhos}
    objetos = []
    for nome, g in pecas.items():
        h = ALTURAS[nome]
        g = shapely.segmentize(g, cfg.passo)
        cob = unary_union([q for k, (q, hq) in todos.items() if k != nome and hq >= h and q.intersects(g.buffer(0.01))])
        v2, ft = _topo_em_faixas(a, g, cfg.passo)
        vp, fp = paredes(g, 0.0, fundo - h, cob)  # alturas relativas ao topo; o perfil soma depois
        xy = np.array([p[:2] for p in v2] + [p[:2] for p in vp], dtype=float).reshape(-1, 2)
        z0 = np.array([0.0] * len(v2) + [p[2] for p in vp]) + cota + h + dz(a, cfg, xy, cota)
        vertices = [[round(x, 3), round(y, 3), round(z, 3)] for (x, y), z in zip(xy, z0)]
        objetos.append({"nome": nome, "material": MATERIAIS[nome], "vertices": vertices,
                        "faces": ft + [[i + len(v2), j + len(v2), k + len(v2)] for i, j, k in fp], "suave": False})
    return objetos


def corredor(a: Acesso, cfg: AcessoCfg) -> BaseGeometry:
    """A área toda do acesso (para tirar do platô e furar o terreno)."""
    ce = unary_union([Polygon(r[0], r[1:]) for r in a.ce]) if a.ce else Polygon()
    return unary_union(list(pecas_acesso(a, ce, cfg).values()))


def faixa_ce(vias: list[dict], a_c0, a_d, s_max: float, larguras: dict[str, float], folga: float = 0.0
             ) -> tuple[BaseGeometry, float]:
    """A rodovia que o eixo cruza primeiro: todas as vias com o mesmo nome e classe, com meia largura
    + `folga`. Devolve a faixa e o s do primeiro cruzamento do eixo com a borda dela."""
    raio = LineString([a_c0, (a_c0[0] + a_d[0] * s_max, a_c0[1] + a_d[1] * s_max)])
    cruzam = [v for v in vias if v["classe"] in larguras and LineString(v["pontos"]).intersects(raio)]
    if not cruzam:
        raise SystemExit(f"acesso: nenhuma via principal cruza o eixo em {s_max:.0f} m")
    primeira = min(cruzam, key=lambda v: Point(a_c0).distance(LineString(v["pontos"]).intersection(raio)))
    mesmas = [v for v in vias if v["classe"] == primeira["classe"] and v["nome"] == primeira["nome"]]
    meia = larguras[primeira["classe"]] / 2
    faixa = unary_union([LineString(v["pontos"]).buffer(meia + folga, cap_style="flat") for v in mesmas])
    borda = faixa if folga == 0 else unary_union([LineString(v["pontos"]).buffer(meia, cap_style="flat") for v in mesmas])
    x = raio.intersection(borda)
    s = min(Point(a_c0).distance(Point(c)) for g in getattr(x, "geoms", [x]) for c in g.coords)
    return faixa, s


def faixa_comprida(aneis: list[list]) -> Polygon:
    """A faixa de acesso entre os anéis da camada: o único comprido (lado maior ≥ 5× o menor)."""
    def alongamento(p: Polygon) -> float:
        r = np.array(p.minimum_rotated_rectangle.exterior.coords)[:3]
        a, b = np.hypot(*(r[1] - r[0])), np.hypot(*(r[2] - r[1]))
        return max(a, b) / max(min(a, b), 1e-9)

    compridos = [p for p in (Polygon(a).buffer(0) for a in aneis if len(a) >= 3) if alongamento(p) >= 5]
    if len(compridos) != 1:
        raise SystemExit(f"acesso: {len(compridos)} faixas compridas na camada (esperava 1)")
    return compridos[0]


def sem_faixa(aneis: list[list], a: Acesso, cfg: AcessoCfg) -> list[list]:
    """Os anéis do platô menos o corredor reto do acesso: somem a faixa do DWG e as calçadas dela, e a
    língua da poligonal que vai até a CE perde o trecho do acesso. O acesso sai do platô e desce com o perfil.
    Anel que o corredor não toca fica como está. O corredor sobra 1 m para os lados, mas começa em s_ini:
    recuar dali abria uma fresta entre o braço da rotatória e o acesso."""
    h = sum(cfg.secao) / 2 + 1.0
    reto = _mundo(a, box(a.s_ini, -h, a.s_fim + h, h))
    fica = []
    for anel in aneis:
        p = Polygon(anel).buffer(0) if len(anel) >= 3 else Polygon()
        if p.is_empty or not p.intersects(reto):
            fica.append(anel)
            continue
        fica += [list(q.exterior.coords)[:-1] for q in partes(p.difference(reto)) if q.area > 1.0]
    return fica


BASE_OSM = RAIZ / "cache" / "entorno" / "base.json"  # vias do OSM (scripts/entorno/extrair.py)
OFFSET_CE = 0.5  # m: a faixa da CE fica esse tanto acima do relevo (OFFSET_FAIXA de preparar.py)
ALCANCE_CE = 600.0  # m do centro da rotatória em que o eixo procura a rodovia
RAIO_BOCA_CE = 150.0  # m: só a CE perto da boca entra na curva das bordas


def eixo_do_acesso(msp, cfg: AcessoCfg, e0: float, n0: float) -> tuple[Acesso, BaseGeometry]:
    """Eixo pela faixa do DWG, da rotatória à borda da CE do OSM (sem perfil ainda) e a faixa da CE com
    folga, que fica no chão natural."""
    from scripts.entorno.preparar import VIAS_CLASSES

    from .cena import CFG_TOML, CenaCfg, aneis_da_layer

    faixa = faixa_comprida(aneis_da_layer(msp, [cfg.camada_via], e0, n0))
    camadas = [l for ls in CenaCfg.carregar(CFG_TOML).camadas.values() for l in ls]
    circulos = [(e.dxf.center.x - e0, e.dxf.center.y - n0, e.dxf.radius)
                for e in msp.query("CIRCLE") if e.dxf.layer in camadas]
    c0, d, s_ini, _ = eixo_da_faixa(faixa, circulos, cfg.recuo_inicio)
    vias = json.loads(BASE_OSM.read_text(encoding="utf-8"))["vias"]
    larguras = {k: float(w) for k, (grupo, w) in VIAS_CLASSES.items() if grupo == "via_principal"}
    ce, s_fim = faixa_ce(vias, c0, d, ALCANCE_CE, larguras)
    livre, _ = faixa_ce(vias, c0, d, ALCANCE_CE, larguras, folga=cfg.folga_ce)
    boca = Point(c0[0] + d[0] * s_fim, c0[1] + d[1] * s_fim).buffer(RAIO_BOCA_CE)
    aneis = [[[list(c) for c in p.exterior.coords[:-1]], *[[list(c) for c in i.coords[:-1]] for i in p.interiors]]
             for p in partes(ce.intersection(boca))]
    return Acesso(c0, d, s_ini, s_fim, [], aneis), livre


def com_perfil(a: Acesso, perto, cota: float, cfg: AcessoCfg) -> Acesso:
    """O perfil: do platô (`cota`) ao chão natural na borda da CE (+ a altura da faixa dela)."""
    x, y = a.c0[0] + a.d[0] * a.s_fim, a.c0[1] + a.d[1] * a.s_fim
    z_fim = round(perto.cota_malha(x, y) + OFFSET_CE, 3)
    pvis, rampa = perfil_acesso(a.s_ini, a.s_fim, cota, z_fim, cfg)
    print(f"acesso: {a.s_fim - a.s_ini:.0f} m da rotatória à CE · desce {cota - z_fim:.1f} m · "
          f"rampa {abs(rampa):.1%} · patamar de {cfg.patamar:.0f} m a {cfg.patamar_inclinacao:.0%}")
    return Acesso(a.c0, a.d, a.s_ini, a.s_fim, pvis, a.ce)
