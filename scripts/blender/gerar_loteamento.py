"""Constrói o loteamento a partir de cache/cena/loteamento.json. Roda dentro do Blender:

    blender -b --factory-startup --python-exit-code 1 -P gerar_loteamento.py -- cena.json saida.blend saida.glb [previa.png] [contexto.json]

O contexto (o entorno) entra só nas prévias: não vai ao .blend nem ao GLB.

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
CONTEXTO = Path(args[4]) if len(args) > 4 else None

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
    "predio": ((0.90, 0.88, 0.84), 0.85),
    "via_principal_osm": ((0.47, 0.46, 0.47), 0.9),
    "entorno": ((0.86, 0.80, 0.68), 0.95),  # igual ao terreno: a costura não aparece
    "mar": ((0.18, 0.42, 0.55), 0.2),  # provisório: o front troca por shader
    "juntas": ((0.72, 0.70, 0.66), 0.9),
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


def material_textura(arquivo: str) -> bpy.types.Material:
    """Chão pintado: a imagem do tile na cor base (o glTF leva a imagem embutida). Um material por tile."""
    nome = "chao_" + Path(arquivo).stem
    if nome in bpy.data.materials:
        return bpy.data.materials[nome]
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(arquivo, check_existing=True)
    img.extension = "EXTEND"  # CLAMP_TO_EDGE no glTF: o mipmap não mistura a borda oposta do tile
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    return m


def construir(dados: dict, nome: str = "Loteamento") -> bpy.types.Collection:
    col = bpy.data.collections.new(nome)
    bpy.context.scene.collection.children.link(col)
    for o in dados["objetos"]:
        me = bpy.data.meshes.new(o["nome"])
        ox, oy, oz = o.get("origem", (0.0, 0.0, 0.0))  # pivô do objeto (centro do lote); malha relativa a ele
        me.from_pydata([(x - ox, y - oy, z - oz) for x, y, z in o["vertices"]], [], o["faces"])
        me.validate()
        me.update()
        if "textura" in o:
            x0, y0, x1, y1 = o["textura"]["ext"]
            uv = me.uv_layers.new(name="UVMap")
            for loop in me.loops:
                x, y = o["vertices"][loop.vertex_index][:2]  # coordenada absoluta: o tile é do mundo
                uv.data[loop.index].uv = ((x - x0) / (x1 - x0), (y - y0) / (y1 - y0))
            me.materials.append(material_textura(o["textura"]["arquivo"]))
        else:
            me.materials.append(material(o["material"]))
        if o.get("suave", True):
            # Normais suaves: o glTF compartilha o vértice entre triângulos (facetado duplica tudo).
            me.shade_smooth()
        ob = bpy.data.objects.new(o["nome"], me)
        ob.location = (ox, oy, oz)
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
    cam.data.clip_start, cam.data.clip_end = max(1.0, distancia / 200), distancia * 10  # precisão de profundidade de longe
    cena.camera = cam
    cena.render.filepath = str(destino)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    bpy.data.objects.remove(alvo)


def _caixa(cos) -> tuple[tuple[float, float, float], float]:
    xs, ys, zs = [c.x for c in cos], [c.y for c in cos], [c.z for c in cos]
    centro = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, sum(zs) / len(zs))
    return centro, max(max(xs) - min(xs), max(ys) - min(ys))


def _mundo(objetos) -> list:
    """Vértices em coordenadas de mundo: com o pivô no lote, v.co é local."""
    bpy.context.view_layer.update()  # em -b, matrix_world só reflete location depois do update
    return [ob.matrix_world @ v.co for ob in objetos for v in ob.data.vertices]


def previa(destino: Path, col: bpy.types.Collection, ctx: bpy.types.Collection | None = None) -> None:
    cena = bpy.context.scene
    try:
        cena.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    cena.display.shading.color_type = "TEXTURE"  # o chão pintado aparece; sem imagem, vale a cor do material
    cena.display.shading.light = "STUDIO"
    cena.render.resolution_x, cena.render.resolution_y = 1600, 1000
    sufixo = lambda s: destino.with_name(destino.stem + s + destino.suffix)  # noqa: E731
    if ctx is not None:
        centro, raio = _caixa(_mundo(ctx.objects))
        _vista(cena, centro, raio * 1.1, sufixo("-entorno"))
    lotes = _mundo([ob for ob in col.objects if ob.name.startswith("Q")])
    if not lotes:
        centro, raio = _caixa(_mundo(col.objects))
        _vista(cena, centro, raio * 1.1, destino)
        return
    centro, raio = _caixa(lotes)
    _vista(cena, centro, raio * 1.1, destino)
    _vista(cena, centro, 160.0, sufixo("-perto"))
    if "Lagoa" in col.objects:
        vs = _mundo([col.objects["Lagoa"]])
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
                              export_apply=True, export_yup=True, export_texcoords=True)
    ctx = construir(json.loads(CONTEXTO.read_text(encoding="utf-8")), "Contexto") if CONTEXTO else None
    if PREVIA:
        previa(PREVIA, col, ctx)
    tris = sum(len(p.vertices) - 2 for ob in col.objects for p in ob.data.polygons)
    print("RESUMO " + json.dumps({"objetos": len(col.objects), "triangulos": tris,
                                   "glb_mb": round(GLB.stat().st_size / 1e6, 2)}))


main()
