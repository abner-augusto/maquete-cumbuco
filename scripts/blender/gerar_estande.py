"""Exporta as malhas do CAD em GLB e gera prévias locais do estande."""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--")+1:]
FONTE, DESTINO, PREVIAS = map(Path, args[:3])
# Cor sRGB, rugosidade, metal, alfa. Acabamentos interpretados das referências.
PALETA = {
    "parede": ("e7e1d5", .8, 0, 1), "piso": ("cfc8b9", .7, 0, 1),
    "pedra": ("b6aa90", .95, 0, 1), "madeira": ("a57547", .65, 0, 1),
    "pedra_relevo": ("c5b99f", .95, 0, 1),
    "madeira_escura": ("61452e", .7, 0, 1), "cobertura": ("77726b", .85, 0, 1),
    "metal": ("302e28", .4, .55, 1), "vidro": ("a2c6c2", .12, .08, .23),
    "agua": ("477f85", .2, .15, .85), "gramado": ("829064", 1, 0, 1),
    "asfalto": ("73736e", 1, 0, 1), "tronco": ("83715a", 1, 0, 1),
    "folhagem": ("4a7042", 1, 0, 1), "tecido": ("d7ccb4", .95, 0, 1),
    "luz": ("ffcc85", .4, .1, 1),
}


def material(nome):
    hexa, rough, metal, alfa = PALETA[nome]
    srgb = [int(hexa[i:i+2],16)/255 for i in (0,2,4)]
    cor = tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in srgb)
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*cor, alfa)
    shader.inputs["Roughness"].default_value = rough
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Alpha"].default_value = alfa
    if nome == "luz":
        shader.inputs["Emission Color"].default_value = (*cor,1)
        shader.inputs["Emission Strength"].default_value = 2
    if alfa < 1:
        mat.surface_render_method = "BLENDED"
    mat.use_backface_culling = nome not in {"vidro", "folhagem", "agua"}
    mat.diffuse_color = (*cor, alfa)
    return mat


def renderizar(raiz):
    cena = bpy.context.scene
    cena.render.engine = "CYCLES"
    cena.cycles.samples = 24
    cena.world = bpy.data.worlds.new("Ambiente")
    cena.world.use_nodes = True
    cena.world.node_tree.nodes["Background"].inputs[0].default_value = (.65,.73,.83,1)
    cena.world.node_tree.nodes["Background"].inputs[1].default_value = .7
    bpy.ops.object.camera_add(location=(72,-40,34))
    cam = bpy.context.object
    cam.rotation_euler = (Vector((32,17,2.3))-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.type, cam.data.ortho_scale = "ORTHO", 65
    cena.camera = cam
    bpy.ops.object.light_add(type="SUN", location=(-10,-10,30))
    bpy.context.object.data.energy = 2.5
    bpy.context.object.rotation_euler = (math.radians(30),math.radians(-20),math.radians(-40))
    bpy.ops.mesh.primitive_plane_add(size=240, location=(30,17,-.11))
    fundo = bpy.context.object
    fundo.name = "Fundo da prévia"
    fundo.data.materials.append(bpy.data.materials["piso"])
    cena.render.resolution_x, cena.render.resolution_y, cena.render.resolution_percentage = 1600,1000,100
    cena.render.filepath = str(PREVIAS/"previa-estande.png")
    bpy.ops.render.render(write_still=True)
    cam.location = (2,54,27)
    cam.rotation_euler = (Vector((25,21,2))-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.ortho_scale = 44
    cena.render.filepath = str(PREVIAS/"previa-estande-deck.png")
    bpy.ops.render.render(write_still=True)
    # Corte de apresentação para conferir a organização interna da planta.
    for o in raiz.children:
        if o.name.startswith("Cobertura"):
            o.hide_render = True
    cam.location = (63,-29,58)
    cam.rotation_euler = (Vector((32,18,1))-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.ortho_scale = 54
    cena.render.filepath = str(PREVIAS/"previa-estande-sem-cobertura.png")
    bpy.ops.render.render(write_still=True)
    for o in raiz.children:
        o.hide_render = False
    for o in list(cena.objects):
        if o != raiz and o.parent != raiz:
            bpy.data.objects.remove(o, do_unlink=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dados = json.loads(FONTE.read_text(encoding="utf-8"))
    mats = {nome: material(nome) for nome in PALETA}
    raiz = bpy.data.objects.new("Estande", None)
    bpy.context.scene.collection.objects.link(raiz)
    for item in dados["objetos"]:
        mesh = bpy.data.meshes.new(item["nome"])
        mesh.from_pydata(item["vertices"], [], item["faces"])
        mesh.validate()
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(item["nome"], mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = raiz
        mesh.materials.append(mats[item["material"]])
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(DESTINO.with_name("estande-local.glb")), export_format="GLB")
    renderizar(raiz)
    meta = dados["implantacao"]
    co, _, si, _, tx, ty = meta["transformacao"]
    raiz.rotation_euler.z = math.atan2(si,co)
    raiz.location = (tx,ty,meta["z"])
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(DESTINO.with_suffix(".blend")))
    bpy.ops.export_scene.gltf(filepath=str(DESTINO), export_format="GLB", export_apply=True)
    print("RESUMO "+json.dumps({"glb_mb": round(DESTINO.stat().st_size/1e6,3),
                               "triangulos": sum(len(p.vertices)-2 for o in raiz.children for p in o.data.polygons),
                               "componentes": len(raiz.children),
                               "residuo_implantacao_m": meta["residuo_implantacao_m"]}))


main()
