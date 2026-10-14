"""Raiz do repo e leitura do .env (sem dependência externa)."""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def ler_env(caminho: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    if not caminho.exists():
        return valores
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip().strip('"')
    return valores


def terreno_dir(env_path: Path = RAIZ / ".env") -> Path:
    valor = os.environ.get("TERRENO_DIR") or ler_env(env_path).get("TERRENO_DIR")
    if not valor:
        raise RuntimeError("TERRENO_DIR ausente: defina no .env (modelo em .env.example)")
    pasta = Path(valor)
    if not pasta.is_dir():
        raise RuntimeError(f"TERRENO_DIR não existe: {pasta}")
    return pasta
