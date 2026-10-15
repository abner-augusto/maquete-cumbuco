"""Placa do loteamento: o platô partido em peças sem sobreposição e levantado em volume.

Cada metro quadrado do platô pertence a uma peça só, por prioridade; por isso nada briga na vista.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.strtree import STRtree

from .geometria import Ponto
from .malha import aninhar, simplificar, triangular

PRECISAO = 0.001  # m: a partição é arredondada a 1 mm, sem lascas numéricas
ORDEM = ["Calcadas", "APP", "Verdes", "Institucional", "Fundo"]  # depois da lagoa e dos lotes, antes da pista; APP antes do verde que a envolve
MATERIAL = {"Pista": "vias", "ChaoPlato": "terreno", "Calcadas": "calcadas", "Verdes": "verdes",
            "Institucional": "institucional", "Fundo": "fundo", "APP": "app", "Juntas": "juntas", "Lagoa": "agua"}


@dataclass(frozen=True)
class PlacaCfg:
    alturas: dict[str, float]  # topo relativo à cota do platô, por peça; "lote" vale para todos os lotes
    recuo_lote: float = 0.15
    fundo: float = -1.0  # base das paredes (meio-fio, margem e saia)
    fresta_max: float = 2.0  # m²: fresta encostada na via vira pista

    @classmethod
    def carregar(cls, caminho: Path) -> "PlacaCfg":
        return cls(**tomllib.loads(caminho.read_text(encoding="utf-8"))["placa"])


def partes(g: BaseGeometry) -> list[Polygon]:
    """Só os polígonos com área (diferenças do shapely deixam linhas e pontos soltos)."""
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g] if g.area > 1e-6 else []
    return [p for q in getattr(g, "geoms", []) for p in partes(q)]


def _limpa(g: BaseGeometry) -> BaseGeometry:
    return unary_union(partes(shapely.set_precision(g, PRECISAO)))


def poligonos(aneis: list[list[Ponto]], tol: float = 0.0) -> BaseGeometry:
    """Anéis de uma layer → polígonos com furos (o anel de dentro é furo do de fora)."""
    aneis = [simplificar(a, tol) if tol else list(a) for a in aneis if len(a) >= 3]
    return unary_union([Polygon(e, furos).buffer(0) for e, furos in aninhar(aneis)])


def particionar(plato: BaseGeometry, papeis: dict[str, BaseGeometry], lotes: dict[str, BaseGeometry],
                lagoa: BaseGeometry | None, cfg: PlacaCfg) -> dict[str, BaseGeometry]:
    pecas: dict[str, BaseGeometry] = {}
    ocupado: list[BaseGeometry] = []

    def tomar(nome: str, g: BaseGeometry) -> BaseGeometry:
        g = g.intersection(plato)
        if ocupado:
            g = g.difference(unary_union(ocupado))
        g = _limpa(g)
        if not g.is_empty:
            pecas[nome] = g
            ocupado.append(g)
        return g

    if lagoa is not None:
        tomar("Lagoa", lagoa)
    for id_, g in lotes.items():
        if tomar(id_, g).is_empty:
            raise ValueError(f"lote {id_} sem área na placa (coberto pela lagoa ou fora do platô)")
    for papel in ORDEM:
        if papel in papeis:
            tomar(papel, papeis[papel])
    resto = _limpa(plato.difference(unary_union(ocupado))) if ocupado else plato
    pista = resto.intersection(papeis.get("Vias", Polygon()))
    frestas = [p for p in partes(resto.difference(pista))
               if p.area < cfg.fresta_max and p.buffer(0.01).intersects(pista)]
    tomar("Pista", unary_union([pista, *frestas]))
    tomar("ChaoPlato", plato)
    juntas = []
    for id_ in lotes:
        lote = pecas[id_]
        recuado = _limpa(lote.buffer(-cfg.recuo_lote, join_style="mitre"))
        if recuado.is_empty:
            continue  # estreito demais para o recuo: fica inteiro
        juntas.append(lote.difference(recuado))
        pecas[id_] = recuado
    if juntas:
        pecas["Juntas"] = _limpa(unary_union(juntas))
    return pecas


def aneis_orientados(p: Polygon) -> tuple[list[Ponto], list[list[Ponto]]]:
    p = orient(p, 1.0)  # externo anti-horário, furos horários: a peça fica sempre à esquerda
    return list(p.exterior.coords)[:-1], [list(i.coords)[:-1] for i in p.interiors]


def ccw(a: Ponto, b: Ponto, c: Ponto) -> bool:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 0


def topo(g: BaseGeometry, z: float) -> tuple[list[list[float]], list[list[int]]]:
    """Topo plano da peça, triangulado com os furos; normais para cima."""
    vs: list[list[float]] = []
    fs: list[list[int]] = []
    for p in partes(g):
        ext, furos = aneis_orientados(p)
        v, t = triangular(ext, furos)
        base = len(vs)
        vs += [[round(x, 3), round(y, 3), round(z, 3)] for x, y in v]
        fs += [[base + a, base + b, base + c] if ccw(v[a], v[b], v[c]) else [base + a, base + c, base + b]
               for a, b, c in t]
    return vs, fs


def _linhas(g: BaseGeometry) -> list[LineString]:
    if g.is_empty:
        return []
    if isinstance(g, LineString):
        return [g]
    return [l for q in getattr(g, "geoms", []) for l in _linhas(q)]


def paredes(g: BaseGeometry, z_topo: float, z_base: float,
            cobertura: BaseGeometry) -> tuple[list[list[float]], list[list[int]]]:
    """Parede vertical do topo à base no trecho do contorno que `cobertura` (as peças de topo igual
    ou mais alto) não encosta. A normal aponta para fora da peça."""
    cob = None if cobertura.is_empty else cobertura.buffer(0.005)
    vs: list[list[float]] = []
    fs: list[list[int]] = []
    for p in partes(g):
        for anel in [p.exterior, *p.interiors]:
            linha = LineString(anel.coords)
            for seg in _linhas(linha if cob is None else linha.difference(cob)):
                cs = list(seg.coords)
                for a, b in zip(cs, cs[1:]):
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    n = (dx * dx + dy * dy) ** 0.5
                    if n < 1e-6:
                        continue
                    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                    if p.contains(Point(mx + dy / n * 0.01, my - dx / n * 0.01)):
                        a, b = b, a  # a direita de a→b tem de ser o lado de fora
                    k = len(vs)
                    vs += [[round(a[0], 3), round(a[1], 3), z_topo], [round(a[0], 3), round(a[1], 3), z_base],
                           [round(b[0], 3), round(b[1], 3), z_base], [round(b[0], 3), round(b[1], 3), z_topo]]
                    fs += [[k, k + 1, k + 2], [k, k + 2, k + 3]]
    return vs, fs


def altura(nome: str, cfg: PlacaCfg) -> float:
    return cfg.alturas["lote"] if nome.startswith("Q") else cfg.alturas[nome]


def montar_placa(pecas: dict[str, BaseGeometry], cfg: PlacaCfg, cota: float,
                 materiais_lote: dict[str, str]) -> list[dict]:
    """Objetos de cena das peças: topo + paredes. Lote com `origem` no centro da caixa do topo (o pivô)."""
    nomes = list(pecas)
    arvore = STRtree([pecas[n] for n in nomes])
    objetos = []
    for nome in nomes:
        g, h = pecas[nome], altura(nome, cfg)
        vizinhos = [nomes[i] for i in arvore.query(g.buffer(0.01))
                    if nomes[i] != nome and altura(nomes[i], cfg) >= h]
        cobertura = unary_union([pecas[n] for n in vizinhos]) if vizinhos else Polygon()
        vt, ft = topo(g, cota + h)
        vp, fp = paredes(g, round(cota + h, 3), round(cota + cfg.fundo, 3), cobertura)
        obj = {"nome": nome, "material": materiais_lote.get(nome) or MATERIAL[nome],
               "vertices": vt + vp, "faces": ft + [[a + len(vt), b + len(vt), c + len(vt)] for a, b, c in fp],
               "suave": False}
        if nome.startswith("Q"):
            x0, y0, x1, y1 = g.bounds
            obj["origem"] = [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3), round(cota + h, 3)]
        objetos.append(obj)
    return objetos
