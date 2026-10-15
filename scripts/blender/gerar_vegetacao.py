"""Vegetação do entorno (Plano 4): gera as três espécies estilizadas (coqueiro, cajueiro, arbusto
de restinga) que o front instancia nas posições de vegetacao.json.

    blender -b --factory-startup --python-exit-code 1 -P gerar_vegetacao.py -- saida.glb

Uma malha por espécie (VEG_coqueiro, VEG_cajueiro, VEG_arbusto), base em z = 0 e altura real em
metros; a escala de cada instância vem do vegetacao.json. Cor chapada por vértice (COLOR_0) e um
único material, para cada espécie ser um InstancedMesh de uma chamada de desenho. Adaptado do
Manoa (cv_espelho_vendas/scripts/entorno/gerar_vegetacao.py).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

GLB = Path(sys.argv[sys.argv.index("--") + 1])

# Verdes acinzentados, mais escuros que o chão, para a copa destacar.
COPA_CAJUEIRO, COPA_CAJUEIRO_2 = "#7F8D66", "#8E9B72"
FRONDE = "#8A9A63"
ARBUSTO = "#97A27A"
TRONCO = "#8C7D68"


def linear(hexa):
    s = hexa.lstrip("#")
    c = [int(s[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]


class Especie:
    def __init__(self, nome):
        self.nome, self.bm, self.cores = nome, bmesh.new(), {}

    def pintar(self, faces, hexa):
        for f in faces:
            self.cores[f] = hexa

    def prisma(self, raio, altura, lados=5, base=(0, 0, 0)):
        bx, by, bz = base
        anel = [(bx + raio * math.cos(2 * math.pi * k / lados), by + raio * math.sin(2 * math.pi * k / lados))
                for k in range(lados)]
        baixo = [self.bm.verts.new((x, y, bz)) for x, y in anel]
        cima = [self.bm.verts.new((x, y, bz + altura)) for x, y in anel]
        faces = [self.bm.faces.new((baixo[k], baixo[(k + 1) % lados], cima[(k + 1) % lados], cima[k]))
                 for k in range(lados)]
        self.pintar(faces, TRONCO)

    def copa(self, centro, raio, achatamento, hexa):
        m = Matrix.Translation(centro) @ Matrix.Diagonal((raio, raio, raio * achatamento, 1))
        geo = bmesh.ops.create_icosphere(self.bm, subdivisions=1, radius=1, matrix=m)
        faces = {f for v in geo["verts"] for f in v.link_faces}
        self.pintar(faces, hexa)

    def lamina(self, angulo, topo, comprimento, queda, largura, hexa):
        """Folha de palmeira dobrada, com as duas faces (o app usa FrontSide)."""
        d = Vector((math.cos(angulo), math.sin(angulo), 0))
        lado = Vector((-d.y, d.x, 0)) * largura / 2
        meio = topo + d * comprimento * 0.5 + Vector((0, 0, queda * 0.15))
        ponta = topo + d * comprimento + Vector((0, 0, -queda))
        vs = [self.bm.verts.new(v) for v in (topo, meio + lado, ponta, meio - lado)]
        frente = [self.bm.faces.new((vs[0], vs[1], vs[3])), self.bm.faces.new((vs[1], vs[2], vs[3]))]
        vs2 = [self.bm.verts.new(v.co) for v in vs]
        verso = [self.bm.faces.new((vs2[0], vs2[3], vs2[1])), self.bm.faces.new((vs2[1], vs2[3], vs2[2]))]
        self.pintar(frente + verso, hexa)

    def objeto(self, material, colecao):
        me = bpy.data.meshes.new("VEG_" + self.nome)
        bm = self.bm
        bm.normal_update()
        cores = {}
        for f in bm.faces:
            base = linear(self.cores[f])
            luz = 0.82 + 0.18 * max(-1.0, min(1.0, f.normal.z))  # de cima mais claro
            cores[f.index] = (*[c * luz for c in base], 1.0)
        bm.to_mesh(me)
        bm.free()
        attr = me.color_attributes.new("Cor", "FLOAT_COLOR", "CORNER")
        for pol in me.polygons:
            pol.use_smooth = False
            for li in pol.loop_indices:
                attr.data[li].color = cores[pol.index]
        me.color_attributes.active_color = attr
        me.materials.append(material)
        ob = bpy.data.objects.new("VEG_" + self.nome, me)
        colecao.objects.link(ob)
        return ob


def material_vegetacao():
    mat = bpy.data.materials.new("VEGETACAO")
    mat.use_nodes = True
    nt = mat.node_tree
    sh = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    cor = nt.nodes.new("ShaderNodeVertexColor")
    cor.layer_name = "Cor"
    nt.links.new(cor.outputs["Color"], sh.inputs["Base Color"])
    sh.inputs["Roughness"].default_value = 0.95
    return mat


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cena = bpy.context.scene
    col = bpy.data.collections.new("VEGETACAO_MODELOS")
    cena.collection.children.link(col)
    mat = material_vegetacao()

    # Coqueiro: estipe fino de ~12 m, nove folhas compridas e caídas.
    e = Especie("coqueiro")
    e.prisma(0.2, 12.0, lados=4)
    topo = Vector((0, 0, 12.0))
    e.copa(topo, 0.7, 0.8, FRONDE)
    for k in range(9):
        e.lamina(2 * math.pi * k / 9 + 0.2, topo, 4.5, 2.4, 1.0, FRONDE)
    coqueiro = e.objeto(mat, col)

    # Cajueiro: tronco curto e copa larga e baixa em dois volumes, ~6 m.
    e = Especie("cajueiro")
    e.prisma(0.3, 1.8)
    e.copa((0, 0, 3.4), 3.6, 0.55, COPA_CAJUEIRO)
    e.copa((1.6, 0.9, 4.2), 2.4, 0.6, COPA_CAJUEIRO_2)
    cajueiro = e.objeto(mat, col)

    # Arbusto de restinga: volume baixo e largo, ~1,5 m.
    e = Especie("arbusto")
    e.copa((0, 0, 0.7), 1.6, 0.55, ARBUSTO)
    arbusto = e.objeto(mat, col)

    obs = [coqueiro, cajueiro, arbusto]
    bpy.ops.object.select_all(action="DESELECT")
    for ob in obs:
        ob.select_set(True)
    GLB.parent.mkdir(parents=True, exist_ok=True)
    opcoes = dict(filepath=str(GLB), export_format="GLB", use_selection=True, export_texcoords=False,
                  export_yup=True)
    try:
        bpy.ops.export_scene.gltf(**opcoes, export_vertex_color="ACTIVE")
    except TypeError:
        bpy.ops.export_scene.gltf(**opcoes)
    print("RESUMO " + json.dumps({"objetos": len(obs), "glb_mb": round(GLB.stat().st_size / 1e6, 3),
                                   "altura_m": {ob.name: round(ob.dimensions.z, 1) for ob in obs}}))


main()
