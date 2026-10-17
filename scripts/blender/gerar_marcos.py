"""Põe os marcos no lugar e exporta. Roda dentro do Blender:

    blender -b --factory-startup --python-exit-code 1 -P gerar_marcos.py -- marcos.json saida.glb [previa.png]

Para cada marco: importa a fonte, fica com os objetos do prefixo, desfaz o giro (clube), aplica a
transformação rígida e a cota, apaga as faces com algum vértice fora da pegada (a mesma regra do furo da
placa em encaixe.py) e junta tudo num objeto.

Cores: se `marcos.json` traz `cores` (o .npz de scripts/marcos/cores.py), cada face recebe a cor do material
do SketchUp no triângulo do DAE mais perto, no lugar das cores de categoria. Normais: as que vêm no GLB são
descartadas; os vértices soltos se soldam e o sombreamento é refeito, liso até ANGULO_SUAVE.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import closest_point_on_tri
from mathutils.kdtree import KDTree

args = sys.argv[sys.argv.index("--") + 1:]
MARCOS, GLB = Path(args[0]), Path(args[1])
PREVIA = Path(args[2]) if len(args) > 2 else None
DIST_COR = 0.10        # m: face mais longe que isto de um triângulo do DAE fica com a cor da categoria
SOLDA = 0.0001         # m, merge by distance
ANGULO_SUAVE = 30.0    # graus; acima disso a aresta fica viva
SOBREPOSTA = 0.03      # m: face horizontal com outra a menos disto acima ou abaixo disputa o mesmo plano
MARCACAO = 0.2         # razão de áreas: face menor que isto da de baixo é desenho sobre o plano (linha de quadra)
MESMO_LADO = 0.7       # cosseno mínimo entre a normal da face e a do triângulo do DAE
VIZINHOS = 32          # triângulos do DAE (pelo centro) testados por face, pela distância exata
# Face sem triângulo do DAE perto fica com a cor da categoria: as dos renders do clube, não as de diagnóstico.
CATEGORIAS = {"LAJE": "#3d3f41", "PISO": "#dcd8d0", "PAREDE": "#ece9e2", "PILAR": "#2b2b2b",
              "VIGA": "#2b2b2b", "ESQUADRIA": "#222222", "GRADIL": "#222222", "EQUIPAMENTO": "#777777",
              "OUTROS": "#c8c2b8"}


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


class Planta:
    """Vista de topo do SketchUp (scripts/marcos/planta.py) como textura projetada de cima: o chão do clube."""

    def __init__(self, arq: Path):
        d = json.loads(arq.read_text(encoding="utf-8"))
        self.afim = np.array(d["afim"])
        self.tam = (d["largura"], d["altura"])
        self.mat = bpy.data.materials.new("PLANTA")
        self.mat.use_nodes = True
        nos = self.mat.node_tree.nodes
        bsdf = next(n for n in nos if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Roughness"].default_value = 0.85
        tex = nos.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(d["imagem"])
        self.mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

    def uv(self, x: float, y: float) -> tuple[float, float]:
        u, v = self.afim @ (x, y, 1.0)
        return u / self.tam[0], 1.0 - v / self.tam[1]


def material_solido(nome: str, rgba) -> bpy.types.Material:
    r, g, b, a = (float(x) for x in rgba)
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.8
    if a < 0.99:
        bsdf.inputs["Alpha"].default_value = a
        mat.surface_render_method = "BLENDED"
    mat.diffuse_color = (r, g, b, a)
    return mat


class Cores:
    """Triângulos do DAE numa KD-tree e um material por cor da paleta, criado sob demanda."""

    def __init__(self, npz: Path):
        d = np.load(npz)
        self.cor, self.paleta, self.tris = d["cor"], d["paleta"], d["tris"]
        self.arvore = KDTree(len(d["centros"]))
        for i, c in enumerate(d["centros"]):
            self.arvore.insert(c, i)
        self.arvore.balance()
        self.mats: dict[int, bpy.types.Material] = {}

    def material(self, k: int) -> bpy.types.Material:
        if k not in self.mats:
            self.mats[k] = material_solido(f"SKP_{k:02d}", self.paleta[k])
        return self.mats[k]

    def pintar(self, o: bpy.types.Object, planta: "Planta | None" = None) -> tuple[int, int]:
        """Troca o material de cada face pelo da cor mais perto; com `planta`, as faces horizontais levam a vista
        de topo como textura, projetada de cima. Devolve (pintadas, total)."""
        me = o.data
        centros = np.empty(len(me.polygons) * 3)
        me.polygons.foreach_get("center", centros)
        idx = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get("material_index", idx)
        slots = {}
        pintadas = 0
        da_planta = []
        normais_f = np.empty(len(me.polygons) * 3)
        me.polygons.foreach_get("normal", normais_f)
        for i, (c, n) in enumerate(zip(centros.reshape(-1, 3), normais_f.reshape(-1, 3))):
            c, n = Vector(c), Vector(n)
            if abs(n.z) > 0.7:  # horizontal: a cor é a do lado de cima, o que se vê na maquete, qualquer que seja a
                n = Vector((0, 0, 1))  # orientação da face no GLB (o DAE traz frente e verso como triângulos à parte)
            perto = []
            for _, j, _ in self.arvore.find_n(c, VIZINHOS):
                a, b, t = (Vector(p) for p in self.tris[j])
                nt = (b - a).cross(t - a)
                if nt.length < 1e-12 or nt.normalized().dot(n) < MESMO_LADO:
                    continue  # o outro lado da laje ou o chão sob o piso: mesmo lugar, outra face
                perto.append((j, (closest_point_on_tri(c, a, b, t) - c).length))
            j, d = min(perto, key=lambda x: x[1], default=(None, math.inf))
            achou = j is not None and d <= DIST_COR
            if planta and n.z == 1:
                if "PLANTA" not in slots:
                    me.materials.append(planta.mat)
                    slots["PLANTA"] = len(me.materials) - 1
                idx[i] = slots["PLANTA"]
                da_planta.append(i)
                pintadas += 1
                continue
            if not achou:
                continue
            mat = self.material(int(self.cor[j]))
            if mat.name not in slots:
                me.materials.append(mat)
                slots[mat.name] = len(me.materials) - 1
            idx[i] = slots[mat.name]
            pintadas += 1
        me.polygons.foreach_set("material_index", idx)
        if planta:
            camada = me.uv_layers["UVMap"]
            for i in da_planta:
                for li in me.polygons[i].loop_indices:
                    camada.data[li].uv = planta.uv(*me.vertices[me.loops[li].vertex_index].co[:2])
        return pintadas, len(idx)


def cor_de_categoria() -> None:
    """Os materiais de categoria do GLB fonte passam a ter cor de acabamento (só valem onde não há cor do DAE)."""
    for mat in bpy.data.materials:
        hexa = CATEGORIAS.get(mat.name.split(".")[0])
        if not hexa or not mat.use_nodes:
            continue
        srgb = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b = (x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in srgb)
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
        mat.diffuse_color = (r, g, b, 1.0)


def planos_simples(o: bpy.types.Object) -> int:
    """Uma superfície por plano: apaga a face horizontal coberta por outra até SOBREPOSTA acima dela (o chão
    sob o piso) e a pequena que fica sobre uma grande (o desenho da quadra na grama). Devolve quantas."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    arvore = BVHTree.FromBMesh(bm)
    sobe, desce = Vector((0, 0, 1)), Vector((0, 0, -1))
    apagar = set()
    for f in bm.faces:
        if abs(f.normal.z) < 0.95:
            continue
        c, area = f.calc_center_median(), f.calc_area()
        _, _, g, d = arvore.ray_cast(c + sobe * 1e-4, sobe, SOBREPOSTA)
        if g is not None and g != f.index and bm.faces[g].calc_area() >= MARCACAO * area:
            apagar.add(f.index)
            continue
        _, _, h, d = arvore.ray_cast(c + desce * 1e-4, desce, SOBREPOSTA)
        if h is not None and h != f.index and area < MARCACAO * bm.faces[h].calc_area():
            apagar.add(f.index)
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in apagar], context="FACES")
    bm.to_mesh(o.data)
    bm.free()
    return len(apagar)


def normais(o: bpy.types.Object) -> None:
    """Fora as normais do GLB; solda, orienta as faces de forma coerente e alisa até ANGULO_SUAVE."""
    me = o.data
    if me.has_custom_normals:
        bpy.context.view_layer.objects.active = o
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=SOLDA)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    limite = math.radians(ANGULO_SUAVE)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(math.pi) < limite
    bm.to_mesh(me)
    bm.free()
    if "custom_normal" in me.attributes:
        me.attributes.remove(me.attributes["custom_normal"])
    me.update()


def marco(nome: str, m: dict, cores: Cores | None, planta: Planta | None) -> bpy.types.Object:
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
        if planta and m.get("planta") and "UVMap" not in o.data.uv_layers:
            o.data.uv_layers.new(name="UVMap")  # o join junta camadas pelo nome: todas iguais
        if cores:  # no referencial do GLB fonte, o mesmo do npz: antes do giro e do encaixe
            m.setdefault("pintadas", [0, 0])
            m["pintadas"] = [a + b for a, b in zip(m["pintadas"], cores.pintar(o, planta if m.get("planta") else None))]
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
    m["planos_apagados"] = planos_simples(ob)
    normais(ob)
    return ob


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dados = json.loads(MARCOS.read_text(encoding="utf-8"))
    cores = Cores(Path(dados["cores"])) if dados.get("cores") else None
    planta = Planta(Path(dados["planta"])) if dados.get("planta") and dados.get("cores") else None
    obs = [marco(n, m, cores, planta) for n, m in dados["marcos"].items()]
    cor_de_categoria()
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
    if cores:
        resumo["cores"] = {n: m["pintadas"] for n, m in dados["marcos"].items()}
    resumo["planos_apagados"] = {n: m["planos_apagados"] for n, m in dados["marcos"].items()}
    resumo["glb_mb"] = round(GLB.stat().st_size / 1e6, 2)
    print("RESUMO " + json.dumps(resumo))


main()
