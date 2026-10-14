"""Roda o Blender sobre a cena do loteamento e confere o GLB. Uso: uv run python -m scripts.loteamento.blender"""

import json
import struct
import subprocess
import sys
from pathlib import Path

from scripts.comum.ambiente import RAIZ, ler_env, terreno_dir

from .cena import DESTINO as CENA_JSON
from .terreno import DESTINO_ENTORNO as ENTORNO_JSON

BLENDER_PADRAO = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
SCRIPT = RAIZ / "scripts" / "blender" / "gerar_loteamento.py"
PASTA_MAQUETE = "6-PROJETOS/10-MAQUETE INTERATIVA"
PREVIA = RAIZ / "cache" / "cena" / "previa.png"
LIMITE_MB = 8.0
LIMITE_ENTORNO_MB = 3.0


def nos_do_glb(caminho: Path) -> list[str]:
    dados = caminho.read_bytes()
    tamanho, tipo = struct.unpack_from("<II", dados, 12)
    if tipo != 0x4E4F534A:
        raise ValueError(f"{caminho}: primeiro bloco do GLB não é JSON")
    gltf = json.loads(dados[20 : 20 + tamanho])
    return [n.get("name", "") for n in gltf.get("nodes", [])]


def conferir_glb(nomes: list[str], ids: list[str]) -> list[str]:
    lotes_glb = {n for n in nomes if n.startswith("Q")}
    erros = [f"lote sem objeto no GLB: {i}" for i in sorted(set(ids) - lotes_glb)]
    erros += [f"objeto de lote sem linha no lotes.json: {n}" for n in sorted(lotes_glb - set(ids))]
    return erros


def conferir_entorno(nomes: list[str], mb: float) -> list[str]:
    erros = [f"objeto do entorno faltando no GLB: {n}" for n in ("Entorno", "Mar") if n not in nomes]
    if mb > LIMITE_ENTORNO_MB:
        erros.append(f"entorno.glb com {mb} MB (alvo {LIMITE_ENTORNO_MB} MB)")
    return erros


def rodar_blender(blender: Path, script: Path, *args: str) -> dict:
    r = subprocess.run(
        [str(blender), "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(script), "--", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
    )
    linha = next((l for l in r.stdout.splitlines() if l.startswith("RESUMO ")), None)
    if r.returncode != 0 or linha is None:
        raise RuntimeError(f"Blender falhou (código {r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return json.loads(linha[len("RESUMO "):])


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    blender = Path(ler_env(RAIZ / ".env").get("BLENDER", BLENDER_PADRAO))
    destino = terreno_dir() / PASTA_MAQUETE
    ent_glb = destino / "entorno.glb"
    ent = rodar_blender(blender, SCRIPT, str(ENTORNO_JSON), str(destino / "entorno.blend"), str(ent_glb))
    erros_ent = conferir_entorno(nos_do_glb(ent_glb), ent["glb_mb"])
    glb, blend = destino / "loteamento.glb", destino / "loteamento.blend"
    resumo = rodar_blender(blender, SCRIPT, str(CENA_JSON), str(blend), str(glb), str(PREVIA), str(ENTORNO_JSON))
    ids = [l["id"] for l in json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]]
    erros = conferir_glb(nos_do_glb(glb), ids)
    if resumo["glb_mb"] > LIMITE_MB:
        erros.append(f"loteamento.glb com {resumo['glb_mb']} MB (alvo {LIMITE_MB} MB)")
    erros = erros_ent + erros
    print("entorno " + json.dumps(ent, ensure_ascii=False), "loteamento " + json.dumps(resumo, ensure_ascii=False),
          *erros, sep="\n")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
