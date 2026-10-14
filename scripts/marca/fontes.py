"""Fontes OFL (Cinzel, Jost) de um commit fixo do google/fonts. Uso: uv run python -m scripts.marca.fontes"""

import hashlib
import sys
import urllib.request
from pathlib import Path

from scripts.comum.ambiente import RAIZ

COMMIT = "4a943f60f1e99b2e5a2778aa34ba82adf77e4615"
_BASE = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}/ofl"
FONTES = {
    "Cinzel[wght].ttf": (f"{_BASE}/cinzel/Cinzel%5Bwght%5D.ttf", "f4d83d34d1f6c741193e4acf4b3dff9531e5a67b6aa65228d00a7db72a4e0f34"),
    "Jost[wght].ttf": (f"{_BASE}/jost/Jost%5Bwght%5D.ttf", "6343b70971000b04c5d401c96ae08ce371086135e999d5e1e1413039c0213076"),
    "Cinzel-OFL.txt": (f"{_BASE}/cinzel/OFL.txt", "f2b3029aba64c378bf0963b62945eee15e564fe4330b934c8f2eb058282b5e83"),
    "Jost-OFL.txt": (f"{_BASE}/jost/OFL.txt", "1af3438a4d5f0ed2bdbc5751a5a67ebf6d537334161184b7fbb68503ef0ea0c5"),
}
PASTA = RAIZ / "cache" / "fontes"


def _sha(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def baixar(url: str, destino: Path, sha256: str) -> Path:
    if destino.exists() and _sha(destino.read_bytes()) == sha256:
        return destino
    with urllib.request.urlopen(url, timeout=60) as r:
        dados = r.read()
    if _sha(dados) != sha256:
        raise ValueError(f"SHA-256 diferente do esperado para {url}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(dados)
    return destino


def garantir(nome: str, pasta: Path = PASTA) -> Path:
    url, sha = FONTES[nome]
    return baixar(url, pasta / nome, sha)


def main() -> int:
    for nome in FONTES:
        print(garantir(nome))
    return 0


if __name__ == "__main__":
    sys.exit(main())
