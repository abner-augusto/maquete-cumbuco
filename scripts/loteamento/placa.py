"""Placa do loteamento: o platô partido em peças sem sobreposição e levantado em volume.

Cada metro quadrado do platô pertence a uma peça só, por prioridade; por isso nada briga na vista.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

import shapely
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .geometria import Ponto
from .malha import aninhar, simplificar

PRECISAO = 0.001  # m: a partição é arredondada a 1 mm, sem lascas numéricas
ORDEM = ["Calcadas", "Verdes", "Institucional", "Fundo", "APP"]  # depois da lagoa e dos lotes, antes da pista


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
