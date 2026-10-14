"""Paleta medida nos logos raster. Uso: uv run python -m scripts.marca.paleta"""

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.comum.ambiente import RAIZ, terreno_dir

from .cores import rgb_para_hex

_MIDIA = "6-PROJETOS/09-MIDIA"
_ESTUDOS = f"{_MIDIA}/Estudo Logo Joao Carlos"
FONTES_LOGO = {
    "P0": f"{_MIDIA}/LOGO Preliminar.jpeg",
    "E1": f"{_ESTUDOS}/WhatsApp Image 2026-10-14 at 11.05.31 (1).jpeg",
    "E2": f"{_ESTUDOS}/WhatsApp Image 2026-10-14 at 11.05.31.jpeg",
    "E3": f"{_ESTUDOS}/WhatsApp Image 2026-10-14 at 11.05.32 (1).jpeg",
    "E4": f"{_ESTUDOS}/WhatsApp Image 2026-10-14 at 11.05.32 (2).jpeg",
    "E5": f"{_ESTUDOS}/WhatsApp Image 2026-10-14 at 11.05.32 (3).jpeg",
    "E6": f"{_ESTUDOS}/WhatsApp Image 2026-10-14 at 11.05.32.jpeg",
}
# Os estudos E1–E4 são cenas (parede de pedra, céu de pôr do sol, noite azul) que
# contaminam a medição. O ouro e o creme saem do P0 (logo sobre creme liso); o preto,
# do fundo de estúdio do E5 e do E6.
FONTES_OURO = ("P0",)
FONTES_PRETO = ("E5", "E6")
DESTINO = RAIZ / "marca" / "paleta.json"


@dataclass(frozen=True)
class Paleta:
    ouro_claro: str
    ouro: str
    bronze: str
    creme: str
    preto: str

    def para_json(self) -> dict:
        return asdict(self)

    @classmethod
    def carregar(cls, caminho: Path) -> "Paleta":
        return cls(**json.loads(caminho.read_text(encoding="utf-8")))


def pixels(img: Image.Image, lado: int = 256) -> np.ndarray:
    img = img.convert("RGB")
    img.thumbnail((lado, lado))
    return np.asarray(img, dtype=np.float64).reshape(-1, 3)


def _hsv(px: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    r, g, b = (px[:, i] / 255 for i in range(3))
    mx, mn = np.max(px / 255, axis=1), np.min(px / 255, axis=1)
    delta = mx - mn
    h = np.zeros_like(mx)
    m = delta > 0
    rm, gm, bm = m & (mx == r), m & (mx == g) & (mx != r), m & (mx == b) & (mx != r) & (mx != g)
    h[rm] = (60 * ((g[rm] - b[rm]) / delta[rm])) % 360
    h[gm] = 60 * ((b[gm] - r[gm]) / delta[gm]) + 120
    h[bm] = 60 * ((r[bm] - g[bm]) / delta[bm]) + 240
    s = np.where(mx > 0, delta / np.where(mx > 0, mx, 1), 0)
    return h, s, mx


def _mediana(px: np.ndarray, nome: str) -> str:
    if len(px) == 0:
        raise ValueError(f"nenhum pixel de {nome} nas imagens")
    return rgb_para_hex(tuple(int(round(v)) for v in np.median(px, axis=0)))


def medir(imagens_ouro: list[Image.Image], imagens_preto: list[Image.Image]) -> Paleta:
    """Ouros e creme das imagens de logo sobre fundo claro; preto das imagens de fundo escuro."""
    px = np.concatenate([pixels(i) for i in imagens_ouro])
    h, s, v = _hsv(px)
    dourado = px[(h >= 20) & (h <= 55) & (s >= 0.25) & (v >= 0.25)]
    if len(dourado) == 0:
        raise ValueError("nenhum pixel de ouro nas imagens")
    ordem = dourado[np.argsort(dourado @ np.array([0.2126, 0.7152, 0.0722]))]
    n = len(ordem)
    faixa = lambda a, b: ordem[int(n * a) : max(int(n * b), int(n * a) + 1)]  # noqa: E731

    creme = px[(s < 0.15) & (v > 0.85)]
    preto = np.concatenate([pixels(i) for i in imagens_preto]) if imagens_preto else np.empty((0, 3))
    if len(preto):
        preto = preto[_hsv(preto)[2] < 0.12]

    return Paleta(
        ouro_claro=_mediana(faixa(0.80, 0.95), "ouro claro"),
        ouro=_mediana(faixa(0.40, 0.60), "ouro"),
        bronze=_mediana(faixa(0.05, 0.20), "bronze"),
        creme=_mediana(creme, "creme"),
        preto=_mediana(preto, "preto"),
    )


def main() -> int:
    terreno = terreno_dir()
    abrir = lambda ids: [Image.open(terreno / FONTES_LOGO[i]) for i in ids]  # noqa: E731
    p = medir(abrir(FONTES_OURO), abrir(FONTES_PRETO))
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(p.para_json(), indent=1) + "\n", encoding="utf-8")
    print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
