"""O repositório não carrega nada da máquina de quem o escreveu: caminhos, pastas de sincronização e IPs
da rede local vêm do `.env` (modelo em `.env.example`)."""
import re
import subprocess

import pytest

from scripts.comum.ambiente import RAIZ

# Montados em pedaços para este arquivo não casar com o próprio padrão.
PROIBIDO = re.compile(
    "|".join([
        r"[A-Za-z]:[\\/]+Users[\\/]+\w",  # pasta de usuário do Windows
        r"/c/Users/\w",
        r"App" + r"Data",
        r"Next" + r"cloud",
        r"D:[\\/]+obs" + r"idian",
        r"\b192\.168\.\d+\.\d+",
        r"\b10\.\d+\.\d+\.\d+\b",
    ])
)
BINARIOS = (".png", ".jpg", ".jpeg", ".webp", ".glb", ".woff", ".woff2", ".ico", ".wasm", ".pdf", ".dxf", ".dwg", ".kmz")
IGNORADOS = ("package-lock.json", "uv.lock")


def _versionados() -> list[str]:
    try:
        saida = subprocess.run(["git", "ls-files", "-z"], cwd=RAIZ, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("sem git")
    return [f for f in saida.decode("utf-8").split("\0") if f and not f.endswith(BINARIOS) and not f.endswith(IGNORADOS)]


def test_nenhum_arquivo_versionado_cita_a_maquina_local():
    achados = []
    for f in _versionados():
        try:
            texto = (RAIZ / f).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for n, linha in enumerate(texto.splitlines(), 1):
            if PROIBIDO.search(linha):
                achados.append(f"{f}:{n}: {linha.strip()[:120]}")
    assert not achados, "caminho ou rede da máquina local no repositório:\n" + "\n".join(achados)
