"""Rotatória procedural: calçada circular e escultura de curvas, sem inscrições."""

import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


def material(nome, cor, metal=0.0, brilho=0.55, emissao=0.0):
    mat = bpy.data.materials.new(nome)
    mat.diffuse_color = (*cor, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*cor, 1)
    shader.inputs['Metallic'].default_value = metal
    shader.inputs['Roughness'].default_value = brilho
    shader.inputs['Emission Color'].default_value = (*cor, 1)
    shader.inputs['Emission Strength'].default_value = emissao
    return mat


def malha(nome, vertices, faces, mat):
    mesh = bpy.data.meshes.new(nome)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(nome, mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(mat)
    return obj


def anel(nome, interno, externo, baixo, topo, mat, passos=192):
    vertices = [(r * math.cos(a), r * math.sin(a), z)
                for r, z in ((interno, baixo), (externo, baixo), (externo, topo), (interno, topo))
                for a in [2 * math.pi * i / passos for i in range(passos)]]
    faces = []
    for j in range(4):
        for i in range(passos):
            k = (i + 1) % passos
            faces.append((j * passos + i, j * passos + k,
                          ((j + 1) % 4) * passos + k, ((j + 1) % 4) * passos + i))
    return malha(nome, vertices, faces, mat)


def bloco(nome, tamanho, z, mat):
    x, y, h = tamanho
    vertices = [(sx * x / 2, sy * y / 2, z + dz * h)
                for dz in (0, 1) for sy in (-1, 1) for sx in (-1, 1)]
    return malha(nome, vertices, [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4),
                                (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)], mat)


def curva(inicio, trechos, passos=20):
    pontos = [inicio]
    for c1, c2, fim in trechos:
        p0 = pontos[-1]
        for i in range(1, passos + 1):
            t = i / passos
            pontos.append(tuple((1-t)**3*p0[k] + 3*(1-t)**2*t*c1[k]
                                + 3*(1-t)*t*t*c2[k] + t**3*fim[k] for k in (0, 1)))
    return pontos


def casca(nome, contorno, profundidade, espessura, pedra, ouro):
    """Silhueta extrudada com leve torção: frente e verso claros, borda dourada."""
    n = len(contorno)
    perfil = [Vector((x, z, 0)) for x, z in contorno]
    indices = {tuple(v): i for i, v in enumerate(perfil)}
    triangulos = tessellate_polygon([perfil])
    vertices = [(x, profundidade + 0.035 * z + 0.09 * x * z / 14 + lado * espessura / 2, z + 0.34)
                for lado in (-1, 1) for x, z in contorno]
    faces = []
    for tri in triangulos:
        ids = tuple(v if isinstance(v, int) else indices[tuple(v)] for v in tri)
        faces.extend([tuple(reversed(ids)), tuple(i + n for i in ids)])
    borda = len(faces)
    faces.extend((i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n))
    obj = malha(nome, vertices, faces, pedra)
    obj.data.materials.append(ouro)
    for p in obj.data.polygons:
        if p.index >= borda:
            p.material_index = 1
            p.use_smooth = True
    bevel = obj.modifiers.new('Arestas arredondadas', 'BEVEL')
    bevel.width = 0.055
    bevel.segments = 3
    bevel.affect = 'EDGES'
    bevel.angle_limit = math.radians(25)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    return obj


def gerar_rotatoria(m, destino):
    pontos = m['pegada']
    cx = (min(p[0] for p in pontos) + max(p[0] for p in pontos)) / 2
    cy = (min(p[1] for p in pontos) + max(p[1] for p in pontos)) / 2
    # A pegada do encaixe inclui 1 cm de tolerância além do círculo original do DWG.
    raio = (max(p[0] for p in pontos) - min(p[0] for p in pontos)) / 2 - 0.01
    escala = raio / 17.5
    raio = 17.5  # Toda a composição é escalada uma vez, depois da união.
    pedra = material('Monumento - pedra clara', (0.78, 0.71, 0.59))
    ouro = material('Monumento - bronze dourado', (0.66, 0.34, 0.085), 0.72, 0.3)
    calcada = material('Rotatória - concreto claro', (0.59, 0.56, 0.49))
    piso = material('Rotatória - piso quadrado', (0.39, 0.35, 0.29))
    grama = material('Rotatória - gramado', (0.17, 0.27, 0.10))
    junta = material('Rotatória - juntas do piso', (0.23, 0.21, 0.17))
    luz = material('Monumento - filete âmbar', (1.0, 0.42, 0.08), 0.3, 0.4, 1.8)
    obs = [anel('Meio-fio', raio - .25, raio, 0, .22, calcada),
           anel('Calçada circular', raio - 2.6, raio - .25, .04, .19, calcada),
           anel('Gramado', 0, raio - 2.6, .02, .13, grama),
           bloco('Praça quadrada', (14, 14, .19), .13, piso),
           anel('Arremate interno', raio - 2.65, raio - 2.6, .13, .20, piso)]
    # Paginação quadrada e juntas radiais da calçada, como geometria exportável.
    for i in range(-6, 7, 2):
        for eixo in (0, 1):
            o = bloco('Junta da praça', (.025, 14, .004), .32, junta)
            if eixo:
                o.rotation_euler.z = math.pi / 2
            o.location[eixo] = i
            obs.append(o)
    for i in range(48):
        a = 2 * math.pi * i / 48
        o = bloco('Junta da calçada', (2.32, .025, .004), .19, junta)
        o.location.x = (raio - 1.43) * math.cos(a)
        o.location.y = (raio - 1.43) * math.sin(a)
        o.rotation_euler.z = a
        obs.append(o)
    # Vela principal: abertura em arco na base e curva ascendente na lateral.
    corpo = curva((-3.5, 0), [
        ((-4.1, 4.3), (-2.6, 7.8), (.9, 10.4)),
        ((2.3, 11.5), (2.9, 13.1), (1.3, 14.1)),
        ((3.0, 13.6), (3.0, 11.5), (2.9, 9.5)),
        ((2.7, 6.6), (2.8, 2.0), (3.0, 0)),
        ((2.9, 2.5), (0.0, 3.5), (-.7, 1.3)),
        ((-.9, .9), (-1.0, .4), (-.9, 0)),
    ])
    obs.append(casca('Vela de pedra', corpo, 0, .55, pedra, ouro))
    coroa = curva((-2.6, 12.3), [
        ((-.1, 16.4), (5.3, 14.5), (2.6, 10.1)),
        ((4.0, 13.2), (1.4, 15.1), (-2.6, 12.3)),
    ])[:-1]
    obs.append(casca('Coroa curva', coroa, .48, .35, ouro, ouro))
    fita = curva((-3.45, .25), [
        ((-4.4, 6.0), (.8, 9.6), (1.25, 12.9)),
        ((1.8, 9.1), (-2.9, 5.5), (-3.45, .25)),
    ])[:-1]
    obs.append(casca('Fita ascendente', fita, -.48, .22, ouro, ouro))
    # Filete na curva externa, sem letras nem texturas da referência.
    caminho = curva((-3.5, .3), [((-4.1, 4.3), (-2.6, 7.8), (.9, 10.4))])
    c = bpy.data.curves.new('Filete de luz', 'CURVE')
    c.dimensions = '3D'
    c.bevel_depth = .035
    c.bevel_resolution = 2
    s = c.splines.new('POLY')
    s.points.add(len(caminho) - 1)
    for p, (x, z) in zip(s.points, caminho):
        p.co = (x, -.30 + .035*z + .09*x*z/14, z + .34, 1)
    o = bpy.data.objects.new('Filete de luz', c)
    bpy.context.scene.collection.objects.link(o)
    c.materials.append(luz)
    obs.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.join()
    ob = bpy.context.object
    # O objeto ativo tem origem zero; toda a ilha acompanha a escala do raio do DWG.
    ob.name = ob.data.name = 'Rotatoria'
    for v in ob.data.vertices:
        v.co *= escala
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(destino), export_format='GLB', use_selection=True,
                              export_yup=True, export_apply=True)
    for v in ob.data.vertices:
        v.co += Vector((cx, cy, m['z']))
    m['planos_apagados'] = 0
    m['pintadas'] = [0, 0]
    return ob
