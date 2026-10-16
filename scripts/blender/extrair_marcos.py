"""Extrai dos GLBs fonte dos marcos só o que o encaixe precisa. Roda dentro do Blender:

    blender -b --factory-startup --python-exit-code 1 -P extrair_marcos.py -- destino.json PREFIXO[,PREFIXO] a.glb [b.glb ...]

Caixa de cada objeto e triângulos de chão (normal para cima, perto de z = 0), em coordenadas do Blender.
"""

import json
import sys
from pathlib import Path

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
DESTINO, PREFIXOS, GLBS = Path(args[0]), args[1].split(","), [Path(a) for a in args[2:]]

saida = {}
for glb in GLBS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    objetos, chao = {}, {}
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        mw = ob.matrix_world
        vs = [mw @ v.co for v in ob.data.vertices]
        if not vs:
            continue
        objetos[ob.name] = [round(min(v.x for v in vs), 3), round(min(v.y for v in vs), 3), round(min(v.z for v in vs), 3),
                            round(max(v.x for v in vs), 3), round(max(v.y for v in vs), 3), round(max(v.z for v in vs), 3)]
        nrm = mw.to_3x3()
        tris = []
        for p in ob.data.polygons:
            n = (nrm @ p.normal).normalized()
            pts = [vs[i] for i in p.vertices]
            zm = sum(q.z for q in pts) / len(pts)
            if n.z > 0.9 and -0.3 <= zm <= 0.6:
                for k in range(1, len(pts) - 1):  # leque: o polígono vira triângulos
                    a, b, c = pts[0], pts[k], pts[k + 1]
                    tris.append([round(a.x, 3), round(a.y, 3), round(b.x, 3), round(b.y, 3), round(c.x, 3), round(c.y, 3)])
        if tris:
            chao[ob.name] = tris
    saida[glb.name] = {"objetos": objetos, "chao": chao}

faltam = [p for p in PREFIXOS if not any(n.startswith(p) for d in saida.values() for n in d["objetos"])]
if faltam:
    print("RESUMO " + json.dumps({"erro": f"nenhum objeto com prefixo {', '.join(faltam)} em {[g.name for g in GLBS]}"}))
    sys.exit(0)
DESTINO.parent.mkdir(parents=True, exist_ok=True)
DESTINO.write_text(json.dumps(saida), encoding="utf-8")
print("RESUMO " + json.dumps({k: {"objetos": len(v["objetos"]), "chao": sum(len(t) for t in v["chao"].values())}
                               for k, v in saida.items()}))
