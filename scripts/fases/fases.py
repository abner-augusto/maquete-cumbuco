"""Fases do loteamento: onde cada uma fica, para a etiqueta "Fase N · Em breve" na maquete.

Fonte: `masterplan-fases.png`, um recorte da página do MASTERPLAN (MASTER URBANO.pdf) em que o autor marcou o
número de cada fase. Os pontos estão em `curadoria.json`, em pixels desse recorte. O recorte é achado na página do
PDF por correlação cruzada normalizada (escala e posição); dali, o ponto vai ao referencial da maquete pela
mesma semelhança que pinta o masterplan no chão (scripts/entorno/masterplan.py, cache/entorno/masterplan.json).

A Fase 1 é a própria maquete e não ganha etiqueta: não entra no arquivo.

Uso: uv run python -m scripts.fases.fases   (depois de scripts.entorno.masterplan)

Escreve dados/fases.json.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from scipy import ndimage, signal

from scripts.comum.ambiente import RAIZ, terreno_dir
from scripts.entorno.masterplan import META, PAGINA, PDF, Semelhanca

PASTA = Path(__file__).resolve().parent
IMAGEM = PASTA / "masterplan-fases.png"
CURADORIA = PASTA / "curadoria.json"
DESTINO = RAIZ / "dados" / "fases.json"

PX_POR_PT = 1.5          # resolução da página para a busca
GROSSO = 2               # a busca grossa roda em metade dessa resolução
ESCALAS = np.arange(0.6, 1.5, 0.02)   # tamanho do recorte na página, em relação ao seu tamanho em pixels
SCORE_MIN = 0.8          # correlação mínima aceita


@dataclass(frozen=True)
class Registro:
    """Onde o recorte está no raster da página: pixel da página = (x, y) + escala · pixel do recorte."""
    escala: float
    x: float
    y: float
    correlacao: float


def correlacao(pagina: np.ndarray, molde: np.ndarray) -> np.ndarray:
    """Correlação cruzada normalizada do molde em cada posição da página (só onde ele cabe inteiro)."""
    h, w = molde.shape
    t = molde - molde.mean()
    soma = signal.fftconvolve(pagina, t[::-1, ::-1], mode="valid")
    lin, col = soma.shape
    cortar = lambda a: a[h // 2: h // 2 + lin, w // 2: w // 2 + col]  # noqa: E731
    media = cortar(ndimage.uniform_filter(pagina, (h, w), mode="constant"))
    media2 = cortar(ndimage.uniform_filter(pagina ** 2, (h, w), mode="constant"))
    variancia = np.maximum(media2 - media ** 2, 1e-6) * h * w
    return soma / np.sqrt(variancia * (t ** 2).sum())


def _cinza(img: Image.Image, escala: float) -> np.ndarray:
    tam = (max(int(round(img.width * escala)), 1), max(int(round(img.height * escala)), 1))
    return np.asarray(img.resize(tam, Image.LANCZOS).convert("L")).astype(float)


def achar_recorte(pagina: np.ndarray, recorte: Image.Image) -> Registro:
    """Escala e posição do recorte na página: busca grossa em metade da resolução e refino na cheia."""
    pagina_grossa = pagina[::GROSSO, ::GROSSO]
    melhor = (-1.0, 1.0, 0, 0)
    for f in ESCALAS:
        molde = _cinza(recorte, f / GROSSO)
        if molde.shape[0] >= pagina_grossa.shape[0] or molde.shape[1] >= pagina_grossa.shape[1]:
            continue
        m = correlacao(pagina_grossa, molde)
        i, j = np.unravel_index(np.argmax(m), m.shape)
        if m[i, j] > melhor[0]:
            melhor = (float(m[i, j]), float(f), int(j) * GROSSO, int(i) * GROSSO)
    _, f0, x0, y0 = melhor
    fino = (-1.0, f0, x0, y0)
    for f in np.arange(f0 - 0.03, f0 + 0.031, 0.002):
        molde = _cinza(recorte, f)
        h, w = molde.shape
        a, b = max(x0 - 12, 0), max(y0 - 12, 0)
        janela = pagina[b: b + h + 36, a: a + w + 36]
        if janela.shape[0] < h or janela.shape[1] < w:
            continue
        m = correlacao(janela, molde)
        i, j = np.unravel_index(np.argmax(m), m.shape)
        if m[i, j] > fino[0]:
            fino = (float(m[i, j]), float(f), a + int(j), b + int(i))
    c, f, x, y = fino
    return Registro(f, x, y, c)


def para_a_cena(u: float, v: float, reg: Registro, pagina: pymupdf.Page, T: Semelhanca) -> tuple[float, float]:
    """Pixel (u, v) do recorte → metros (leste, norte) da maquete. A página tem /Rotate: o ponto sai do espaço
    girado do raster e volta ao do vetor, que é o em que o masterplan foi registrado (y para baixo, daí o −y)."""
    ponto = pymupdf.Point((reg.x + u * reg.escala) / PX_POR_PT, (reg.y + v * reg.escala) / PX_POR_PT) * pagina.derotation_matrix
    leste, norte = T.aplicar(np.array([[ponto.x, -ponto.y]]))[0]
    return float(leste), float(norte)


def gerar(pagina: pymupdf.Page, recorte: Image.Image, fases: list[dict], T: Semelhanca) -> dict:
    pix = pagina.get_pixmap(matrix=pymupdf.Matrix(PX_POR_PT, PX_POR_PT), alpha=False)
    cinza = np.asarray(Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")).astype(float)
    if recorte.mode == "RGBA":  # o recorte tem fundo transparente: sobre branco, como o papel
        fundo = Image.new("RGB", recorte.size, (255, 255, 255))
        fundo.paste(recorte, mask=recorte.split()[3])
        recorte = fundo
    reg = achar_recorte(cinza, recorte)
    if reg.correlacao < SCORE_MIN:
        raise SystemExit(f"o recorte não casa com a página do masterplan (correlação {reg.correlacao:.2f} < {SCORE_MIN})")
    saida = []
    for f in fases:
        x, y = para_a_cena(f["x"], f["y"], reg, pagina, T)
        saida.append({"id": f["id"], "nome": f"Fase {f['id']}", "x": round(x, 1), "y": round(y, 1)})
    return {"versao": 2, "fonte": "scripts/fases/masterplan-fases.png", "correlacao": round(reg.correlacao, 3), "fases": saida}


def main() -> None:
    curadoria = json.loads(CURADORIA.read_text(encoding="utf-8"))
    meta = json.loads(META.read_text(encoding="utf-8"))
    pagina = pymupdf.open(terreno_dir() / PDF)[PAGINA]  # com o /Rotate da página: o raster sai girado, como a imagem do autor
    dados = gerar(pagina, Image.open(IMAGEM), curadoria["fases"], Semelhanca(**meta["transf"]))
    DESTINO.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"correlação {dados['correlacao']}")
    for f in dados["fases"]:
        print(f"{f['nome']}: x {f['x']} y {f['y']}")


if __name__ == "__main__":
    main()
