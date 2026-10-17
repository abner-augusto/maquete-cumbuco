"""Cor do chão do clube a partir da vista de topo do SketchUp (`maqueteclubeplanta.jpg`).

Os pisos externos do clube (grama, deque, areia das quadras, borda da piscina) estão com o material padrão
do SketchUp no DAE: brancos. A vista de topo exportada do SketchUp completo tem essas cores. Grava a planta
recortada no clube (JPEG) e a afinidade metro → pixel do recorte, no referencial do GLB fonte do clube; o
`gerar_marcos.py` a aplica como textura, por projeção de cima, nas faces horizontais do clube.

A afinidade foi achada uma vez (2026-10-17) casando as arestas de uma vista de topo ortogonal do
`marcos.glb` com as da planta (busca de giro e escala por correlação, `cv2.matchTemplate`), e levada ao
referencial do GLB fonte pelo encaixe do clube. Vale enquanto a planta e o GLB fonte forem os mesmos.

Uso: uv run python -m scripts.marcos.planta
"""

import json
import sys

import numpy as np
from PIL import Image

from scripts.comum.ambiente import RAIZ, terreno_dir

from .encaixe import MarcosCfg

PLANTA = "maqueteclubeplanta.jpg"
DESTINO = RAIZ / "cache" / "cena" / "marcos-planta.json"
IMAGEM = DESTINO.with_suffix(".jpg")
AFIM = np.array([[4.9569, 2.7114, 6239.9106], [2.7114, -4.9569, 3466.0928]])  # m (GLB fonte) → px da planta
CAIXA_M = (-5.0, 10.0, 95.0, 102.0)  # x0, y0, x1, y1 do clube no GLB fonte, com folga
LADO_MAX = 1024  # px do lado maior da textura


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    Image.MAX_IMAGE_PIXELS = None
    img = Image.open(terreno_dir() / MarcosCfg.carregar().pasta / PLANTA).convert("RGB")
    x0, y0, x1, y1 = CAIXA_M
    cantos = np.array([[x, y, 1.0] for x in (x0, x1) for y in (y0, y1)]) @ AFIM.T
    (u0, v0), (u1, v1) = np.floor(cantos.min(0)).astype(int), np.ceil(cantos.max(0)).astype(int)
    recorte = img.crop((u0, v0, u1, v1))
    k = min(1.0, LADO_MAX / max(recorte.size))
    recorte = recorte.resize((round(recorte.width * k), round(recorte.height * k)), Image.LANCZOS)
    afim = (AFIM - np.array([[0, 0, u0], [0, 0, v0]])) * k
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    recorte.save(IMAGEM, quality=88)
    DESTINO.write_text(json.dumps({"imagem": str(IMAGEM), "largura": recorte.width, "altura": recorte.height,
                                   "afim": afim.tolist()}), encoding="utf-8")
    print(json.dumps({"textura_px": list(recorte.size), "destino": str(DESTINO)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
