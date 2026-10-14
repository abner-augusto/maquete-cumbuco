"""Constrói o loteamento a partir de cache/cena/loteamento.json. Roda dentro do Blender:

    blender -b --factory-startup --python-exit-code 1 -P gerar_loteamento.py -- cena.json saida.blend saida.glb [previa.png]

Não calcula geometria: só cria malhas, materiais e exporta. Ajuste é no Python de fora.
"""

import json
import math
import sys
from pathlib import Path

import bpy

args = sys.argv[sys.argv.index("--") + 1 :]
CENA, BLEND, GLB = (Path(a) for a in args[:3])
PREVIA = Path(args[3]) if len(args) > 3 else None

# Cores de cena (ambiente, não marca): sRGB 0–1 e rugosidade.
MATERIAIS = {
    "terreno": ((0.86, 0.80, 0.68), 0.95),
    "vias": ((0.42, 0.42, 0.44), 0.9),
    "calcadas": ((0.82, 0.80, 0.76), 0.9),
    "verdes": ((0.52, 0.62, 0.40), 0.95),
    "institucional": ((0.66, 0.70, 0.56), 0.95),
    "fundo": ((0.60, 0.66, 0.48), 0.95),
    "app": ((0.44, 0.56, 0.38), 0.95),
    "agua": ((0.30, 0.55, 0.62), 0.15),
    "lote_residencial": ((0.93, 0.89, 0.80), 0.8),
    "lote_uso_misto": ((0.85, 0.76, 0.62), 0.8),
}


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material(nome: str) -> bpy.types.Material:
    if nome in bpy.data.materials:
        return bpy.data.materials[nome]
    cor, rug = MATERIAIS.get(nome, ((1.0, 0.0, 1.0), 0.5))
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*(_linear(c) for c in cor), 1.0)
    bsdf.inputs["Roughness"].default_value = rug
    m.diffuse_color = (*(_linear(c) for c in cor), 1.0)
    return m


def construir(dados: dict) -> bpy.types.Collection:
    col = bpy.data.collections.new("Loteamento")
    bpy.context.scene.collection.children.link(col)
    for o in dados["objetos"]:
        me = bpy.data.meshes.new(o["nome"])
        me.from_pydata(o["vertices"], [], o["faces"])
        me.validate()
        me.update()
        me.materials.append(material(o["material"]))
        # Normais suaves: o glTF compartilha o vértice entre triângulos (facetado duplica tudo).
        me.shade_smooth()
        ob = bpy.data.objects.new(o["nome"], me)
        col.objects.link(ob)
    return col


def _vista(cena, alvo_xyz, distancia: float, destino: Path) -> None:
    """Câmera a sudoeste, 40° acima do horizonte, olhando para o alvo."""
    alvo = bpy.data.objects.new("Alvo", None)
    cena.collection.objects.link(alvo)
    alvo.location = alvo_xyz
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cena.collection.objects.link(cam)
    az, el = math.radians(225), math.radians(40)
    cam.location = (
        alvo_xyz[0] + distancia * math.cos(el) * math.sin(az),
        alvo_xyz[1] + distancia * math.cos(el) * math.cos(az),
        alvo_xyz[2] + distancia * math.sin(el),
    )
    trava = cam.constraints.new("TRACK_TO")
    trava.target, trava.track_axis, trava.up_axis = alvo, "TRACK_NEGATIVE_Z", "UP_Y"
    cam.data.lens = 35
    cam.data.clip_start, cam.data.clip_end = 1.0, distancia * 10
    cena.camera = cam
    cena.render.filepath = str(destino)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    bpy.data.objects.remove(alvo)


def previa(destino: Path, col: bpy.types.Collection) -> None:
    cena = bpy.context.scene
    try:
        cena.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    cena.display.shading.color_type = "MATERIAL"
    cena.display.shading.light = "STUDIO"
    cena.render.resolution_x, cena.render.resolution_y = 1600, 1000
    lotes = [v.co for ob in col.objects if ob.name.startswith("Q") for v in ob.data.vertices]
    xs, ys, zs = [c.x for c in lotes], [c.y for c in lotes], [c.z for c in lotes]
    centro = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, sum(zs) / len(zs))
    raio = max(max(xs) - min(xs), max(ys) - min(ys))
    _vista(cena, centro, raio * 1.1, destino)
    _vista(cena, centro, 160.0, destino.with_name(destino.stem + "-perto" + destino.suffix))
    if "Lagoa" in col.objects:
        vs = [v.co for v in col.objects["Lagoa"].data.vertices]
        meio = (sum(c.x for c in vs) / len(vs), sum(c.y for c in vs) / len(vs), vs[0].z)
        _vista(cena, meio, 140.0, destino.with_name(destino.stem + "-lagoa" + destino.suffix))


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dados = json.loads(CENA.read_text(encoding="utf-8"))
    col = construir(dados)
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0  # sem .blend1: a pasta vai para o Drive do cliente
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    bpy.ops.object.select_all(action="DESELECT")
    for ob in col.objects:
        ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(GLB), export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True, export_texcoords=False)
    if PREVIA:
        previa(PREVIA, col)
    tris = sum(len(p.vertices) - 2 for ob in col.objects for p in ob.data.polygons)
    print("RESUMO " + json.dumps({"objetos": len(col.objects), "triangulos": tris,
                                   "glb_mb": round(GLB.stat().st_size / 1e6, 2)}))


main()
