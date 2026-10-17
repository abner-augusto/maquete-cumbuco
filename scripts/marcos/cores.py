"""Cores dos marcos: a cor de cada material do SketchUp (média da textura ou a cor do difuso), por triângulo do DAE.

Os GLBs fonte (`clube - sem mobiliario.glb`, `portaria e rotatoria.glb`) só têm materiais por categoria
(PAREDE, LAJE…), em cores de diagnóstico. O DAE do mesmo SKP guarda os materiais originais. Grava, para
cada triângulo do DAE, os vértices e o centro no referencial dos GLBs fonte e o índice da cor; o `gerar_marcos.py` pinta
cada face com a cor do triângulo mais perto da face.

O referencial é o do `prep_np.py` que gerou os GLBs (04-CLUBE/DWG Abner/_scripts 3D para 2D): metros,
menos ORIGEM, e o clube girado GIRO graus em torno de PIVO.

Uso: uv run --with pycollada python -m scripts.marcos.cores
"""

import json
import math
import sys

import numpy as np
from PIL import Image

from scripts.comum.ambiente import RAIZ, terreno_dir

DAE = "6-PROJETOS/04-CLUBE/DWG Abner/clube3d 4(limpo).dae"
DESTINO = RAIZ / "cache" / "cena" / "marcos-cores.npz"
POL_M = 0.0254  # o DAE do SketchUp está em polegadas
ORIGEM = np.array([515.2508, 979.5262, 0.0])
PIVO = np.array([40.56, 45.98])
GIRO = math.radians(28)
Y_CLUBE = 1150.0  # y (m, antes da origem) abaixo do qual é o clube; acima, portaria e rotatória


def linear(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def cor_do_efeito(efeito, pasta, cache: dict) -> tuple[float, ...]:
    """RGBA linear 0–1 do difuso: a média da textura (sRGB → linear) ou a cor; a transparência do efeito."""
    d = efeito.diffuse
    if isinstance(d, tuple):
        rgb = linear(np.array(d[:3], dtype=float))
    else:  # collada.material.Map
        arq = d.sampler.surface.image.path
        if arq not in cache:
            try:
                img = Image.open(pasta / arq).convert("RGB").resize((64, 64))
                cache[arq] = linear(np.asarray(img, dtype=float) / 255.0).reshape(-1, 3).mean(0)
            except OSError:
                cache[arq] = np.ones(3)
        rgb = cache[arq]
    t = efeito.transparency
    alfa = 1.0 if t is None or isinstance(efeito.transparent, type(None)) else float(t)
    if efeito.opaque_mode == "A_ONE" and isinstance(efeito.transparent, tuple):
        alfa = float(efeito.transparent[3]) * (1.0 if t is None else float(t))
    return tuple(round(float(x), 4) for x in (*rgb, min(max(alfa, 0.0), 1.0)))


def referencial(p: np.ndarray) -> np.ndarray:
    """Polegadas do DAE (z para cima) → referencial dos GLBs fonte."""
    q = p * POL_M
    clube = q[:, 1] < Y_CLUBE
    q = q - ORIGEM
    c, s = math.cos(GIRO), math.sin(GIRO)
    x, y = q[clube, 0] - PIVO[0], q[clube, 1] - PIVO[1]
    q[clube, 0], q[clube, 1] = c * x - s * y + PIVO[0], s * x + c * y + PIVO[1]
    return q


def main() -> int:
    import collada

    sys.stdout.reconfigure(encoding="utf-8")
    dae = terreno_dir() / DAE
    doc = collada.Collada(str(dae), ignore=[collada.common.DaeUnsupportedError, collada.common.DaeBrokenRefError])
    paleta: dict[tuple, int] = {}
    imagens: dict = {}
    tris, indices = [], []
    for geo in doc.scene.objects("geometry"):
        for prim in geo.primitives():
            if isinstance(prim, collada.polylist.BoundPolylist):
                prim = prim.triangleset()  # o SketchUp exporta polylist
            if not isinstance(prim, collada.triangleset.BoundTriangleSet) or not len(prim):
                continue
            cor = cor_do_efeito(prim.material.effect, dae.parent, imagens) if prim.material else (1.0, 1.0, 1.0, 1.0)
            k = paleta.setdefault(cor, len(paleta))
            tris.append(prim.vertex[prim.vertex_index])
            indices.append(np.full(len(prim.vertex_index), k, np.int32))
    t = referencial(np.vstack(tris).reshape(-1, 3)).reshape(-1, 3, 3).astype(np.float32)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(DESTINO, centros=t.mean(1), tris=t, cor=np.concatenate(indices),
                        paleta=np.array(list(paleta), np.float32))
    print(json.dumps({"triangulos": len(t), "cores": len(paleta), "texturas": len(imagens), "destino": str(DESTINO)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
