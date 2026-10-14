"""Inventário de layers de um DXF, para decidir o layers.toml. Uso: uv run python -m scripts.loteamento.inventario"""

import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import ezdxf
from ezdxf import bbox

from scripts.comum.ambiente import RAIZ

from .geometria import poligono_fechado

_AMOSTRAS = 8


@dataclass
class LayerResumo:
    nome: str
    por_tipo: dict[str, int]
    fechadas: int
    blocos: dict[str, int]
    textos: list[str]
    extensao: tuple[float, float, float, float] | None


def _textos(e) -> list[str]:
    t = e.dxftype()
    if t == "TEXT":
        return [e.dxf.text.strip()]
    if t == "MTEXT":
        return [e.plain_text().strip()]
    if t == "INSERT":
        return [a.dxf.text.strip() for a in e.attribs]
    return []


def inventariar(doc) -> list[LayerResumo]:
    grupos = defaultdict(list)
    for e in doc.modelspace():
        grupos[e.dxf.layer].append(e)
    resumos = []
    for nome in sorted(grupos):
        ents = grupos[nome]
        textos = [t for e in ents for t in _textos(e) if t]
        caixa = bbox.extents(ents, fast=True)
        resumos.append(
            LayerResumo(
                nome=nome,
                por_tipo=dict(Counter(e.dxftype() for e in ents)),
                fechadas=sum(1 for e in ents if poligono_fechado(e)),
                blocos=dict(Counter(e.dxf.name for e in ents if e.dxftype() == "INSERT")),
                textos=list(dict.fromkeys(textos))[:_AMOSTRAS],
                extensao=(caixa.extmin.x, caixa.extmin.y, caixa.extmax.x, caixa.extmax.y) if caixa.has_data else None,
            )
        )
    return resumos


def escrever_md(resumos: list[LayerResumo], destino: Path, titulo: str) -> None:
    linhas = [
        f"# Inventário de layers — {titulo}",
        "",
        "Gerado por `scripts/loteamento/inventario.py`. Serve para preencher `scripts/loteamento/layers.toml`.",
        "",
        "| Layer | Entidades | Polilinhas fechadas | Blocos | Amostra de textos | Extensão (xmin, ymin, xmax, ymax) |",
        "|---|---|---:|---|---|---|",
    ]
    for r in resumos:
        tipos = ", ".join(f"{k}: {v}" for k, v in sorted(r.por_tipo.items()))
        blocos = ", ".join(f"{k}: {v}" for k, v in sorted(r.blocos.items()))
        textos = " · ".join(t.replace("|", "/") for t in r.textos)
        ext = "" if r.extensao is None else ", ".join(f"{v:.1f}" for v in r.extensao)
        linhas.append(f"| {r.nome} | {tipos} | {r.fechadas} | {blocos} | {textos} | {ext} |")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main() -> int:
    for nome, sufixo in (("planta-venda", ""), ("masterplan-r05", "-masterplan")):
        doc = ezdxf.readfile(RAIZ / "cache" / "dxf" / f"{nome}.dxf")
        escrever_md(inventariar(doc), RAIZ / "dados" / f"inventario-layers{sufixo}.md", nome)
    return 0


if __name__ == "__main__":
    sys.exit(main())
