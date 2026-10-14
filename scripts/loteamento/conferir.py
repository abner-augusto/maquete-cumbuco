"""Conferência desenho × tabela × IPTU (spec §6). Erro bloqueia o lotes.json; aviso só informa."""

from dataclasses import dataclass, field
from pathlib import Path

from .extrair import LoteBruto
from .fontes import LinhaPreco
from .geometria import area

FRENTE_MIN_AVISO = 5.0


@dataclass
class Relatorio:
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    contagens: dict[str, int] = field(default_factory=dict)


def conferir(
    lotes: dict[str, LoteBruto],
    tabela: dict[str, LinhaPreco],
    iptu: dict[str, str],
    mostrar_precos: bool,
    tolerancia: float,
) -> Relatorio:
    rel = Relatorio(contagens={"desenho": len(lotes), "tabela": len(tabela), "iptu": len(iptu)})
    desenho, cadastro = set(lotes), set(tabela)
    rel.erros += [f"{i}: no desenho e não na tabela" for i in sorted(desenho - cadastro)]
    rel.erros += [f"{i}: na tabela e não no desenho" for i in sorted(cadastro - desenho)]
    for i in sorted(desenho & cadastro):
        a, t = area(lotes[i].pontos), tabela[i].area_m2
        if abs(a - t) / t > tolerancia:
            rel.erros.append(f"{i}: área do desenho {a:.2f} m² × tabela {t:.2f} m² ({(a - t) / t:+.2%})")
        if mostrar_precos and tabela[i].preco_total <= 0:
            rel.erros.append(f"{i}: sem preço na tabela")
    for i in sorted(desenho):
        cad = lotes[i].area_cad
        if cad:
            a = area(lotes[i].pontos)
            if abs(a - cad) / cad > tolerancia:
                rel.avisos.append(
                    f"{i}: área escrita no desenho {cad:.2f} m² × polígono {a:.2f} m² ({(a - cad) / cad:+.2%})"
                )
    for i in sorted(desenho):
        f = lotes[i].frente_m
        if f is not None and f < FRENTE_MIN_AVISO:
            rel.avisos.append(f"{i}: frente de {f:.2f} m (menos de {FRENTE_MIN_AVISO:g} m), conferir no desenho")
    rel.avisos += [f"{i}: sem inscrição de IPTU" for i in sorted(desenho - set(iptu))]
    rel.avisos += [f"{i}: inscrição de IPTU de lote fora do desenho" for i in sorted(set(iptu) - desenho)]
    return rel


def escrever_relatorio(rel: Relatorio, destino: Path) -> None:
    linhas = [
        "# Relatório de conferência — lotes da Fase 1",
        "",
        "Gerado por `scripts/loteamento/gerar_dados.py`. Erro bloqueia o `lotes.json`; aviso só informa.",
        "",
        "| Fonte | Lotes |",
        "|---|---:|",
        *[f"| {k} | {v} |" for k, v in rel.contagens.items()],
        "",
        f"## Erros ({len(rel.erros)})",
        "",
        *[f"- {e}" for e in rel.erros],
        "",
        f"## Avisos ({len(rel.avisos)})",
        "",
        *[f"- {a}" for a in rel.avisos],
    ]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
