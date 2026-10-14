"""Famílias de nome da marca. O desenho (símbolo, cores, fontes) é o mesmo; muda só o que se escreve.

A família ativa é a que o site e o material atual usam. As outras ficam guardadas para validação:
"alternativa" espera o registro do nome (decisão da empresa de 14/10/2026).
"""

from dataclasses import dataclass

# (texto, peso, largura alvo, espaçamento): peso "leve" = Jost 300, "normal" = Jost 400
Linha = tuple[str, str, float, float]


@dataclass(frozen=True)
class Familia:
    chave: str
    nome: str  # letreiro principal, em Cinzel
    sobre_nome: str | None  # linha pequena acima do nome, em Jost
    produto: tuple[Linha, ...]  # sub-linhas do produto vertical, abaixo do filete
    produto_linha: str  # sub-linha do produto horizontal
    mae: str | None  # sub-linha da assinatura da marca-mãe; None = sem marca-mãe
    titulo: str  # nome por extenso
    titulo_mae: str | None
    confidencial: bool


FAMILIAS = {
    "americas": Familia(
        chave="americas",
        nome="AMÉRICAS",
        sobre_nome="CIDADE DAS",
        produto=(("RESIDENCIAL · CUMBUCO", "leve", 700.0, 0.35),),
        produto_linha="RESIDENCIAL · CUMBUCO",
        mae=None,
        titulo="Cidade das Américas — Residencial Cumbuco",
        titulo_mae=None,
        confidencial=False,
    ),
    "alternativa": Familia(
        chave="alternativa",
        nome="ALTERNATIVA",
        sobre_nome=None,
        produto=(("RESIDENCIAL", "leve", 560.0, 0.5), ("CUMBUCO", "normal", 480.0, 0.55)),
        produto_linha="RESIDENCIAL · CUMBUCO",
        mae="DESENVOLVIMENTO URBANO",
        titulo="Alternativa Residencial Cumbuco",
        titulo_mae="Alternativa Desenvolvimento Urbano",
        confidencial=True,
    ),
}
ATIVA = "americas"


def textos(f: Familia) -> list[str]:
    """Tudo o que a família escreve nas assinaturas."""
    saida = [f.nome, f.produto_linha, *(l[0] for l in f.produto)]
    if f.sobre_nome:
        saida.append(f.sobre_nome)
    if f.mae:
        saida.append(f.mae)
    return saida
