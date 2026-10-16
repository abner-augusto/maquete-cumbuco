"""Driver dos scripts de Blender dos marcos. Uso: uv run python -m scripts.marcos.blender (Task 5)."""

import json
from pathlib import Path

from scripts.comum.ambiente import RAIZ
from scripts.loteamento.blender import rodar_blender

EXTRAIR = RAIZ / "scripts" / "blender" / "extrair_marcos.py"
FONTE_JSON = RAIZ / "cache" / "cena" / "marcos-fonte.json"


def rodar_extracao(blender: Path, glbs: list[Path], destino: Path, prefixos: list[str]) -> dict:
    resumo = rodar_blender(blender, EXTRAIR, str(destino), ",".join(prefixos), *[str(g) for g in glbs])
    if "erro" in resumo:
        raise RuntimeError(resumo["erro"])
    return json.loads(destino.read_text(encoding="utf-8"))


def extrair() -> int:
    """`uv run python -m scripts.marcos.blender --extrair`: caixas e chão dos GLBs fonte."""
    from scripts.comum.ambiente import ler_env, terreno_dir
    from scripts.loteamento.blender import BLENDER_PADRAO

    from .encaixe import MarcosCfg

    c = MarcosCfg.carregar()
    pasta = terreno_dir() / c.pasta
    blender = Path(ler_env(RAIZ / ".env").get("BLENDER", BLENDER_PADRAO))
    d = rodar_extracao(blender, [pasta / c.clube, pasta / c.portaria], FONTE_JSON, ["CLUBE_", "PORTARIA_", "ROTATORIA_"])
    print({k: (len(v["objetos"]), sum(len(t) for t in v["chao"].values())) for k, v in d.items()})
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(extrair())
