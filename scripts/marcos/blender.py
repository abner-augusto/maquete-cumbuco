"""Driver dos scripts de Blender dos marcos.

Uso: uv run python -m scripts.marcos.blender [--extrair]
"""

import json
import sys
from pathlib import Path

from PIL import Image

from scripts.comum.ambiente import RAIZ, ler_env, terreno_dir
from scripts.loteamento.blender import BLENDER_PADRAO, PASTA_MAQUETE, nos_do_glb, rodar_blender

from .cores import DESTINO as CORES
from .planta import DESTINO as PLANTA
from .encaixe import DESTINO as MARCOS_JSON
from .encaixe import MarcosCfg

EXTRAIR = RAIZ / "scripts" / "blender" / "extrair_marcos.py"
FONTE_JSON = RAIZ / "cache" / "cena" / "marcos-fonte.json"
GERAR = RAIZ / "scripts" / "blender" / "gerar_marcos.py"
PREVIA = RAIZ / "cache" / "cena" / "previa-marcos.png"
LIMITE_MB = 6.0
OBJETOS = ("Clube", "Portaria", "Rotatoria")


def rodar_extracao(blender: Path, fontes: dict[Path, list[str]], destino: Path) -> dict:
    """`fontes`: cada GLB com os prefixos que ele tem de ter."""
    resumo = rodar_blender(blender, EXTRAIR, str(destino), *[f"{g}::{','.join(ps)}" for g, ps in fontes.items()])
    if "erro" in resumo:
        raise RuntimeError(resumo["erro"])
    return json.loads(destino.read_text(encoding="utf-8"))


def extrair() -> int:
    """`uv run python -m scripts.marcos.blender --extrair`: caixas e chão dos GLBs fonte."""
    c = MarcosCfg.carregar()
    pasta = terreno_dir() / c.pasta
    blender = Path(ler_env(RAIZ / ".env").get("BLENDER", BLENDER_PADRAO))
    d = rodar_extracao(blender, {pasta / c.clube: ["CLUBE_"], pasta / c.portaria: ["PORTARIA_", "ROTATORIA_"]},
                       FONTE_JSON)
    print({k: (len(v["objetos"]), sum(len(t) for t in v["chao"].values())) for k, v in d.items()})
    return 0


def rodar_geracao(blender: Path, marcos: Path, glb: Path, previa: Path | None = None) -> dict:
    resumo = rodar_blender(blender, GERAR, str(marcos), str(glb), *([str(previa)] if previa else []))
    if "erro" in resumo:
        raise RuntimeError(resumo["erro"])
    return resumo


def conferir_marcos(nomes: list[str], mb: float) -> list[str]:
    erros = [f"objeto faltando no marcos.glb: {n}" for n in OBJETOS if n not in nomes]
    if mb > LIMITE_MB:
        erros.append(f"marcos.glb com {mb} MB (alvo {LIMITE_MB} MB)")
    return erros


def lado_a_lado(previa: Path, referencia: Path, destino: Path, altura: int = 900) -> None:
    Image.MAX_IMAGE_PIXELS = None
    a, b = Image.open(previa).convert("RGB"), Image.open(referencia).convert("RGB")
    a = a.resize((round(a.width * altura / a.height), altura))
    b = b.resize((round(b.width * altura / b.height), altura))
    m = Image.new("RGB", (a.width + b.width, altura), "white")
    m.paste(a, (0, 0))
    m.paste(b, (a.width, 0))
    m.save(destino, quality=85)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = MarcosCfg.carregar()
    blender = Path(ler_env(RAIZ / ".env").get("BLENDER", BLENDER_PADRAO))
    pasta = terreno_dir() / cfg.pasta
    dados = json.loads(MARCOS_JSON.read_text(encoding="utf-8"))
    for m in dados["marcos"].values():
        m["fonte"] = str(pasta / m["fonte"])
    if CORES.exists():
        dados["cores"] = str(CORES)
        if PLANTA.exists():  # a vista de topo só cobre o clube
            dados["planta"] = str(PLANTA)
            dados["marcos"]["Clube"]["planta"] = True
    else:
        print(f"sem {CORES.name}: cores de categoria (rode scripts.marcos.cores)")
    temp = RAIZ / "cache" / "cena" / "marcos-abs.json"
    temp.write_text(json.dumps(dados), encoding="utf-8")
    glb = terreno_dir() / PASTA_MAQUETE / "marcos.glb"
    resumo = rodar_geracao(blender, temp, glb, PREVIA)
    lado_a_lado(PREVIA, pasta / "maqueteclubeplanta.jpg", PREVIA.with_name("previa-marcos-lado-a-lado.jpg"))
    erros = conferir_marcos(nos_do_glb(glb), resumo["glb_mb"])
    print("marcos " + json.dumps(resumo, ensure_ascii=False), *erros, sep="\n")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(extrair() if "--extrair" in sys.argv else main())
