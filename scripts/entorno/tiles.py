"""Corte do recorte do chão em 2×2 tiles. As linhas caem em nós da grade, então nenhuma célula
(e nenhum triângulo) é partida. Chave "ij": i = 0 oeste / 1 leste, j = 0 sul / 1 norte."""

Ext = tuple[float, float, float, float]


def linhas_de_corte(ext: Ext, passo: float) -> tuple[float, float]:
    x0, y0, x1, y1 = ext
    return (x0 + round((x1 - x0) / 2 / passo) * passo, y0 + round((y1 - y0) / 2 / passo) * passo)


def janelas(ext: Ext, passo: float) -> dict[str, Ext]:
    x0, y0, x1, y1 = ext
    xc, yc = linhas_de_corte(ext, passo)
    xs, ys = ((x0, xc), (xc, x1)), ((y0, yc), (yc, y1))
    return {f"{i}{j}": (xs[i][0], ys[j][0], xs[i][1], ys[j][1]) for i in range(2) for j in range(2)}


def da_janela(janela: Ext, x: float, y: float) -> bool:
    """Borda oeste e sul incluídas, leste e norte não: cada ponto cai numa janela só."""
    x0, y0, x1, y1 = janela
    return x0 <= x < x1 and y0 <= y < y1


def ext_da_grade(g) -> Ext:
    return (g.x0, g.y0, g.x0 + g.passo * (g.nx - 1), g.y0 + g.passo * (g.ny - 1))


def com_margem(janela: Ext, px: int, margem_px: int) -> Ext:
    """Janela aumentada em `margem_px` pixels de cada lado, para a imagem de `px` no lado maior.
    O UV usa esta extensão: o texel da borda já tem o conteúdo do vizinho e o filtro não abre costura."""
    x0, y0, x1, y1 = janela
    m = max(x1 - x0, y1 - y0) / (px - 2 * margem_px) * margem_px
    return (x0 - m, y0 - m, x1 + m, y1 + m)
