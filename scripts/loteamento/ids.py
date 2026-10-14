"""Id canônico de lote: Q<quadra>L<lote> (Q07L04, QHL01)."""

import re

_PREFIXO_QUADRA = re.compile(r"^(QUADRA|QD\.?|Q)\s*-?\s*")
_PREFIXO_LOTE = re.compile(r"^(LOTE|LT\.?|L)\s*-?\s*")
_INTEIRO = re.compile(r"\d+(\.0+)?")


def normalizar_quadra(q) -> str:
    if q is None:
        raise ValueError("quadra vazia")
    s = _PREFIXO_QUADRA.sub("", str(q).strip().upper())
    if _INTEIRO.fullmatch(s):
        return f"{int(float(s)):02d}"
    if re.fullmatch(r"[A-Z]", s):
        return s
    raise ValueError(f"quadra inválida: {q!r}")


def normalizar_lote(l) -> str:
    if l is None:
        raise ValueError("lote vazio")
    s = _PREFIXO_LOTE.sub("", str(l).strip().upper())
    if _INTEIRO.fullmatch(s):
        return f"{int(float(s)):02d}"
    raise ValueError(f"lote inválido: {l!r}")


def id_lote(q, l) -> str:
    return f"Q{normalizar_quadra(q)}L{normalizar_lote(l)}"


def tipo_por_quadra(q) -> str:
    return "uso_misto" if normalizar_quadra(q).isalpha() else "residencial"
