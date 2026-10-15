import bpy, sys
a=sys.argv[sys.argv.index('--')+1:]; S, glb, png = a
sys.path.insert(0,S); from render_util import render
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
ms=[o for o in bpy.context.scene.objects if o.type=='MESH']
me=bpy.data.meshes.new('frame'); me.from_pydata([(38,305,-3),(95,432,8)],[],[])
fr=bpy.data.objects.new('frame',me); bpy.context.scene.collection.objects.link(fr)
from render_util import bbox
import render_util
orig=render_util.bbox
render_util.bbox=lambda objs: orig([fr])
render(png,ms+[fr],az=-45,el=45,res=1600,color='MATERIAL')
