import bpy, sys, numpy as np
a=sys.argv[sys.argv.index('--')+1:]; S, glb, png = a
sys.path.insert(0,S); from render_util import render, bbox
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
ms=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.context.view_layer.update()
tri=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in ms)
mn,mx=bbox(ms)
print('VERIFY',glb.split('/')[-1],'objs',len(bpy.context.scene.objects),'meshes',len(ms),'tris',tri,'bbmin',mn.round(2),'bbmax',mx.round(2),'dims',(mx-mn).round(2),'images',len(bpy.data.images),'mats',sorted(m.name for m in bpy.data.materials))
for o in ms: print('  OBJ',o.name,len(o.data.polygons))
render(png,ms,az=-45,el=45,res=1600,color='MATERIAL')
