"""Gera dados/lotes.json, georref.json e relatorio-conferencia.md. Uso: uv run python -m scripts.loteamento.gerar_dados"""

import json
import sys
from pathlib import Path

import ezdxf

from scripts.comum.ambiente import RAIZ, terreno_dir

from .conferir import Relatorio, conferir, escrever_relatorio
from .extrair import ExtracaoErro, MapaLayers, extrair_lotes
from .fontes import ler_iptu, ler_tabela_set26
from .geometria import extensao
from .georref import georref_json, origem, parece_utm_24s
from .saida import Config, carregar_config, montar_lotes_json

IPTU_CSV = "4-PREFEITURA/IPTU_2025/00-INDICE IPTU 2025 - LOTES CANCUN.csv"


def _gravar_json(destino: Path, dados: dict) -> None:
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def gerar(doc, mapa: MapaLayers, tabela, iptu, config: Config, saida_dir: Path) -> Relatorio:
    saida_dir.mkdir(parents=True, exist_ok=True)
    (saida_dir / "lotes.json").unlink(missing_ok=True)
    try:
        lotes = extrair_lotes(doc, mapa)
    except ExtracaoErro as erro:
        rel = Relatorio(erros=erro.erros)
        escrever_relatorio(rel, saida_dir / "relatorio-conferencia.md")
        return rel

    ext = extensao([p for l in lotes.values() for p in l.pontos])
    rel = conferir(lotes, tabela, iptu, config.mostrar_precos, config.tolerancia_area)
    if not parece_utm_24s(ext):
        rel.erros.insert(0, f"desenho fora de UTM 24S: extensão {ext}")
    escrever_relatorio(rel, saida_dir / "relatorio-conferencia.md")
    if rel.erros:
        return rel

    e0, n0 = origem(ext)
    _gravar_json(saida_dir / "georref.json", georref_json(e0, n0))
    _gravar_json(saida_dir / "lotes.json", montar_lotes_json(lotes, tabela, iptu, config, e0, n0))
    return rel


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # console do Windows é cp1252
    dxf = RAIZ / "cache" / "dxf" / "planta-venda.dxf"
    if not dxf.exists():
        print("Falta o DXF. Rode antes: uv run python -m scripts.loteamento.converter_dwg")
        return 2
    terreno = terreno_dir()
    config = carregar_config(RAIZ / "dados" / "config.json")
    rel = gerar(
        ezdxf.readfile(dxf),
        MapaLayers.carregar(RAIZ / "scripts" / "loteamento" / "layers.toml"),
        ler_tabela_set26(terreno / config.tabela_arquivo),
        ler_iptu(terreno / IPTU_CSV),
        config,
        RAIZ / "dados",
    )
    print(f"{rel.contagens} · {len(rel.erros)} erro(s) · {len(rel.avisos)} aviso(s) → dados/relatorio-conferencia.md")
    return 1 if rel.erros else 0


if __name__ == "__main__":
    sys.exit(main())
