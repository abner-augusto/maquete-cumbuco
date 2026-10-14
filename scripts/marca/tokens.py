"""Tema do front (formato do temas/manoa.css do espelho) derivado da paleta. Uso: uv run python -m scripts.marca.tokens"""

import sys

from scripts.comum.ambiente import RAIZ

from .cores import Cor, ajustar_contraste, contraste, hex_para_rgb, misturar, rgb_para_hex
from .paleta import DESTINO as PALETA_JSON
from .paleta import Paleta

CHAVES = (
    "papel", "papel-2", "areia", "filete", "filete-forte", "tinta", "tinta-2", "tinta-3",
    "acento", "acento-contraste", "acento-hover", "caramelo", "sol", "sol-texto", "sol-fundo",
    "sol-sobre-tinta", "ceu", "campo",
)
FONTES_PADRAO = {"display": "Cinzel", "texto": "Jost", "rotulo": "Jost"}
DESTINO = RAIZ / "marca" / "tokens.css"
_BRANCO: Cor = (255, 255, 255)
_PRETO: Cor = (0, 0, 0)


def _texto_sobre(fundo: Cor, *candidatas: Cor) -> Cor:
    return next((c for c in candidatas if contraste(c, fundo) >= 4.5), ajustar_contraste(candidatas[0], fundo, 4.5))


def _legivel(cor: Cor, fundos: list[Cor], minimo: float = 4.5) -> Cor:
    """Ajusta a cor contra o pior dos fundos em que o front a usa, até passar em todos."""
    for _ in range(len(fundos)):
        pior = min(fundos, key=lambda f: contraste(cor, f))
        if contraste(cor, pior) >= minimo:
            break
        cor = ajustar_contraste(cor, pior, minimo)
    return cor


def _claro(c: Cor, k: Cor, o: Cor, oc: Cor, b: Cor) -> dict[str, Cor]:
    papel = c
    fundos = [papel, misturar(c, b, 0.06), misturar(c, o, 0.22), misturar(c, b, 0.10), _BRANCO]
    sol_fundo = misturar(c, oc, 0.25)
    acento = _legivel(b, fundos[:2])
    return {
        "papel": papel,
        "papel-2": fundos[1],
        "areia": fundos[2],
        "filete": misturar(c, b, 0.18),
        "filete-forte": misturar(c, b, 0.35),
        "tinta": _legivel(misturar(k, b, 0.12), fundos, 7),
        "tinta-2": _legivel(misturar(k, b, 0.45), fundos),
        "tinta-3": _legivel(misturar(k, b, 0.60), fundos),
        "acento": acento,
        "acento-contraste": _texto_sobre(acento, c, _BRANCO),
        "acento-hover": misturar(acento, k, 0.15),
        "caramelo": o,
        "sol": oc,
        "sol-texto": _legivel(o, [papel, sol_fundo]),
        "sol-fundo": sol_fundo,
        "sol-sobre-tinta": oc,
        "ceu": fundos[3],
        "campo": _BRANCO,
    }


def _escuro(c: Cor, k: Cor, o: Cor, oc: Cor, b: Cor) -> dict[str, Cor]:
    papel = misturar(k, b, 0.06)
    fundos = [papel, misturar(k, b, 0.12), misturar(k, o, 0.18), misturar(k, b, 0.10), misturar(k, _PRETO, 0.30)]
    sol_fundo = misturar(k, o, 0.25)
    acento = _legivel(oc, fundos[:2])
    return {
        "papel": papel,
        "papel-2": fundos[1],
        "areia": fundos[2],
        "filete": misturar(k, b, 0.22),
        "filete-forte": misturar(k, b, 0.40),
        "tinta": _legivel(c, fundos, 7),
        "tinta-2": _legivel(misturar(c, b, 0.30), fundos),
        "tinta-3": _legivel(misturar(c, b, 0.45), fundos),
        "acento": acento,
        "acento-contraste": _texto_sobre(acento, k, _PRETO),
        "acento-hover": misturar(acento, c, 0.20),
        "caramelo": o,
        "sol": oc,
        "sol-texto": _legivel(oc, [papel, sol_fundo]),
        "sol-fundo": sol_fundo,
        "sol-sobre-tinta": ajustar_contraste(b, c, 3),
        "ceu": fundos[3],
        "campo": fundos[4],
    }


def tema(p: Paleta) -> dict[str, dict[str, str]]:
    cores = [hex_para_rgb(x) for x in (p.creme, p.preto, p.ouro, p.ouro_claro, p.bronze)]
    return {
        modo: {k: rgb_para_hex(v) for k, v in f(*cores).items()}
        for modo, f in (("claro", _claro), ("escuro", _escuro))
    }


def _sombras(rgb: str, a: tuple[float, float, float, float, float, float]) -> list[str]:
    return [
        f"  --tema-sombra-1: 0 1px 2px rgba({rgb}, {a[0]}), 0 4px 12px rgba({rgb}, {a[1]});",
        f"  --tema-sombra-2: 0 -1px 0 rgba({rgb}, {a[2]}), 0 -8px 28px rgba({rgb}, {a[3]});",
        f"  --tema-sombra-3: 0 2px 4px rgba({rgb}, {a[4]}), 0 10px 22px rgba({rgb}, {a[5]});",
    ]


def css(t: dict[str, dict[str, str]], fontes: dict[str, str], nome: str = "americas") -> str:
    tinta = ", ".join(str(x) for x in hex_para_rgb(t["claro"]["tinta"]))
    linhas = [
        f"/* temas/{nome} — gerado por scripts/marca/tokens.py a partir de marca/paleta.json. Não editar à mão. */",
        f'[data-tema="{nome}"] {{',
        *[f"  --tema-{k}: {t['claro'][k]};" for k in CHAVES],
        "",
        f'  --tema-fonte-display: "{fontes["display"]}", Georgia, serif;',
        f'  --tema-fonte-texto: "{fontes["texto"]}", system-ui, sans-serif;',
        f'  --tema-fonte-rotulo: "{fontes["rotulo"]}", system-ui, sans-serif;',
        "",
        *_sombras(tinta, (0.10, 0.08, 0.06, 0.14, 0.10, 0.14)),
        "}",
        "",
        f'[data-tema="{nome}"][data-cor="escuro"] {{',
        *[f"  --tema-{k}: {t['escuro'][k]};" for k in CHAVES],
        "",
        *_sombras("0, 0, 0", (0.35, 0.28, 0.3, 0.45, 0.35, 0.45)),
        "}",
    ]
    return "\n".join(linhas) + "\n"


def main() -> int:
    t = tema(Paleta.carregar(PALETA_JSON))
    DESTINO.write_text(css(t, FONTES_PADRAO), encoding="utf-8")
    print(f"{DESTINO} ({len(CHAVES)} cores × 2 modos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
