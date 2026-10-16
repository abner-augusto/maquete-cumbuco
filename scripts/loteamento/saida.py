"""config.json → Config, e a montagem do lotes.json (contrato do Plano 1, Task 8)."""

import json
from dataclasses import dataclass
from pathlib import Path

from .extrair import LoteBruto
from .fontes import LinhaPreco
from .georref import CRS, para_local
from .ids import tipo_por_quadra


@dataclass(frozen=True)
class Config:
    mostrar_precos: bool
    tabela_arquivo: str
    tabela_nome: str
    tabela_referencia: str
    tolerancia_area: float


def carregar_config(caminho: Path) -> Config:
    c = json.loads(caminho.read_text(encoding="utf-8"))
    t = c["tabelaPrecos"]
    return Config(bool(c["mostrarPrecos"]), t["arquivo"], t["nome"], t["referencia"], float(c["toleranciaArea"]))


def montar_lotes_json(
    lotes: dict[str, LoteBruto],
    tabela: dict[str, LinhaPreco],
    iptu: dict[str, str],
    config: Config,
    e0: float,
    n0: float,
) -> dict:
    saida = []
    for i in sorted(lotes):
        l, t = lotes[i], tabela[i]
        item = {
            "id": i,
            "quadra": l.quadra,
            "lote": l.lote,
            "tipo": tipo_por_quadra(l.quadra),
            "area_m2": round(t.area_m2, 2),
            "lados_m": l.lados_m,
            "frente_m": l.frente_m,
            "frente_rumo": l.frente_rumo,
            "poligono": para_local(l.pontos, e0, n0),
        }
        if i in iptu:
            item["inscricao_iptu"] = iptu[i]
        if config.mostrar_precos:
            item["preco"] = {"total": round(t.preco_total, 2), "m2": round(t.preco_m2, 2), "classificacao": t.classificacao}
        saida.append(item)
    return {
        "versao": 1,
        "crs": CRS,
        "origem": {"E": e0, "N": n0},
        "precos": {"tabela": config.tabela_nome, "referencia": config.tabela_referencia} if config.mostrar_precos else None,
        "lotes": saida,
    }
