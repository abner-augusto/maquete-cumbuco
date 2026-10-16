"""Põe os marcos no lugar e exporta. Roda dentro do Blender:

    blender -b --factory-startup --python-exit-code 1 -P gerar_marcos.py -- marcos.json saida.glb [previa.png]

Para cada marco: importa a fonte, fica com os objetos do prefixo, desfaz o giro (clube), aplica a
transformação rígida e a cota, apaga as faces com algum vértice fora da pegada (a mesma regra do furo da
placa em encaixe.py) e junta tudo num objeto.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
MARCOS, GLB = Path(args[0]), Path(args[1])
PREVIA = Path(args[2]) if len(args) > 2 else None


def dentro(px: np.ndarray, py: np.ndarray, anel: list) -> np.ndarray:
    """Par/ímpar vetorizado: pontos (px, py) dentro do anel."""
    r = np.zeros(px.shape, dtype=bool)
    xs, ys = np.array([p[0] for p in anel]), np.array([p[1] for p in anel])
    for i in range(len(anel)):
        x0, y0, x1, y1 = xs[i - 1], ys[i - 1], xs[i], ys[i]
        cruza = (y0 > py) != (y1 > py)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = (x1 - x0) * (py - y0) / (y1 - y0) + x0
        r ^= cruza & (px < xi)
    return r


def girar(x, y, cx, cy, graus):
    a = math.radians(graus)
    dx, dy = x - cx, y - cy
    return cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)


def falhar(msg: str) -> None:
    print("RESUMO " + json.dumps({"erro": msg}))
    sys.exit(0)


def marco(nome: str, m: dict) -> bpy.types.Object:
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=m["fonte"])
    novos = [o for o in bpy.data.objects if o not in antes]
    for o in novos:
        if o.type != "MESH" or not o.name.startswith(m["prefixo"]):
            bpy.data.objects.remove(o)
    obs = [o for o in bpy.data.objects if o not in antes]
    if not obs:
        falhar(f"nenhum objeto com prefixo {m['prefixo']} em {Path(m['fonte']).name} ({nome})")
    t = m["transf"]
    c, s = math.cos(t["theta"]), math.sin(t["theta"])
    for o in obs:
        o.data.transform(o.matrix_world)  # aplica a matriz do import (y-up → z-up) na malha
        o.matrix_world.identity()
        co = np.empty(len(o.data.vertices) * 3)
        o.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        x, y = co[:, 0], co[:, 1]
        if m["giro"]:
            x, y = girar(x, y, *m["giro"])
        co[:, 0], co[:, 1] = c * x - s * y + t["tx"], s * x + c * y + t["ty"]
        co[:, 2] += m["z"]
        o.data.vertices.foreach_set("co", co.ravel())
        o.data.update()
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.verts.index_update()
        xy = np.array([v.co[:2] for v in bm.verts]) if bm.verts else np.zeros((0, 2))
        fora_v = ~dentro(xy[:, 0], xy[:, 1], m["pegada"]) if len(xy) else np.zeros(0, dtype=bool)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if any(fora_v[v.index] for v in f.verts)], context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.to_mesh(o.data)
        bm.free()
    obs = [o for o in obs if len(o.data.polygons)]
    if not obs:
        falhar(f"{nome}: nenhuma face de {Path(m['fonte']).name} dentro da pegada")
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = nome
    return ob


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dados = json.loads(MARCOS.read_text(encoding="utf-8"))
    obs = [marco(n, m) for n, m in dados["marcos"].items()]
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    GLB.parent.mkdir(parents=True, exist_ok=True)
    # Draco: o SketchUp deixa ~800 mil triângulos de detalhe real (a dissolução planar tira só 4%); sem
    # compressão são 28 MB, com ela ~2,5 MB. O front carrega com o DRACOLoader.
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=6)
    if PREVIA:
        cena = bpy.context.scene
        try:
            cena.render.engine = "BLENDER_WORKBENCH"
        except TypeError:
            pass
        xs = [v.co.x for o in obs for v in o.data.vertices]
        ys = [v.co.y for o in obs for v in o.data.vertices]
        cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
        cena.collection.objects.link(cam)
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.1
        cam.location = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 500.0)
        cam.data.clip_end = 2000.0
        cena.camera = cam
        cena.render.resolution_x = cena.render.resolution_y = 1400
        cena.render.filepath = str(PREVIA)
        bpy.ops.render.render(write_still=True)
    resumo = {}
    for o in obs:
        vs = [v.co for v in o.data.vertices]
        resumo[o.name] = {"x": [round(min(v.x for v in vs), 3), round(max(v.x for v in vs), 3)],
                          "z": [round(min(v.z for v in vs), 3), round(max(v.z for v in vs), 3)],
                          "triangulos": sum(len(p.vertices) - 2 for p in o.data.polygons)}
    resumo["glb_mb"] = round(GLB.stat().st_size / 1e6, 2)
    print("RESUMO " + json.dumps(resumo))


main()
