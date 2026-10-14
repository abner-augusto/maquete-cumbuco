"""Leitura das fontes tabulares: índice de IPTU (CSV) e tabela SET26 (XLS).

O calamine lê o .xls regravado pelo Excel 2016, que o xlrd rejeita (tabela de strings)."""

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .ids import id_lote

ABA_SET26 = "12, 24 e 36meses"
COL_QUADRA, COL_LOTE, COL_AREA, COL_CLASSIF, COL_PRECO_M2, COL_TOTAL = 0, 1, 2, 3, 4, 14


def _ler_texto(caminho: Path) -> str:
    dados = caminho.read_bytes()
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            return dados.decode(codificacao)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"codificação desconhecida: {caminho}")


def ler_iptu(caminho: Path) -> dict[str, str]:
    inscricoes: dict[str, str] = {}
    for linha in csv.DictReader(_ler_texto(caminho).splitlines(), delimiter=";"):
        # Boletos sem quadra/lote (uso misto, multifamiliar) não se ligam a um lote.
        if not linha["quadra"].strip() and not linha["lote"].strip():
            continue
        i = id_lote(linha["quadra"], linha["lote"])
        inscricao = linha["inscricao"].strip()
        if i in inscricoes and inscricoes[i] != inscricao:
            raise ValueError(f"{i}: duas inscrições ({inscricoes[i]}, {inscricao})")
        inscricoes[i] = inscricao
    return inscricoes


@dataclass(frozen=True)
class LinhaPreco:
    area_m2: float
    classificacao: str
    preco_m2: float
    preco_total: float


def _numero(v) -> bool:
    return isinstance(v, (int, float)) and not pd.isna(v)


def linhas_tabela(df: pd.DataFrame) -> dict[str, LinhaPreco]:
    cabecalho = next(
        i for i, v in enumerate(df[COL_QUADRA]) if str(v).strip().upper() == "QUADRA"
    )
    linhas: dict[str, LinhaPreco] = {}
    for _, r in df.iloc[cabecalho + 1 :].iterrows():
        q, l = r[COL_QUADRA], r[COL_LOTE]
        if pd.isna(q) or pd.isna(l) or not _numero(r[COL_AREA]):
            continue
        i = id_lote(q, l)
        if i in linhas:
            raise ValueError(f"{i} duplicado na tabela")
        linhas[i] = LinhaPreco(
            area_m2=float(r[COL_AREA]),
            classificacao=str(r[COL_CLASSIF]).strip(),
            preco_m2=float(r[COL_PRECO_M2]),
            preco_total=float(r[COL_TOTAL]),
        )
    return linhas


def ler_tabela_set26(caminho: Path) -> dict[str, LinhaPreco]:
    return linhas_tabela(pd.read_excel(caminho, sheet_name=ABA_SET26, header=None, engine="calamine"))
