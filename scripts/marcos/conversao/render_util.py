import bpy, math, numpy as np
from mathutils import Vector
def bbox(objs):
    mn=np.full(3,1e18); mx=np.full(3,-1e18)
    for o in objs:
        if o.type!='MESH' or len(o.data.vertices)==0: continue
        V=np.empty(len(o.data.vertices)*3,np.float32); o.data.vertices.foreach_get('co',V); V=V.reshape(-1,3)
        M=np.array(o.matrix_world); W=V@M[:3,:3].T+M[:3,3]
        mn=np.minimum(mn,W.min(0)); mx=np.maximum(mx,W.max(0))
    return mn,mx
def render(path, objs, az=-45, el=45, res=1600, color='MATERIAL', zoom=1.0):
    sc=bpy.context.scene
    try: sc.render.engine='BLENDER_WORKBENCH'
    except TypeError as e: print(e)
    sh=sc.display.shading
    sh.light='STUDIO'; sh.color_type=color
    sh.show_shadows=True; sh.show_cavity=True
    try: sh.cavity_type='WORLD'
    except: pass
    sc.render.resolution_x=res; sc.render.resolution_y=int(res*0.7); sc.render.film_transparent=False
    sc.render.image_settings.file_format='PNG'
    mn,mx=bbox(objs); c=(mn+mx)/2; r=np.linalg.norm(mx-mn)/2
    cam=bpy.data.objects.get('_PREV_CAM')
    if cam is None:
        cd=bpy.data.cameras.new('_PREV_CAM'); cam=bpy.data.objects.new('_PREV_CAM',cd); sc.collection.objects.link(cam)
    cam.data.type='ORTHO'; cam.data.ortho_scale=2*r*zoom*1.05
    a=math.radians(az); e=math.radians(el)
    d=Vector((math.cos(e)*math.sin(a), -math.cos(e)*math.cos(a), math.sin(e)))
    cam.location=Vector(c)+d*(r*3); cam.data.clip_end=r*10
    cam.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler()
    sc.camera=cam
    keep=set(o.name for o in objs)
    for o in sc.objects:
        if o.type=='MESH': o.hide_render = o.name not in keep
    sc.render.filepath=path
    bpy.ops.render.render(write_still=True)
    print('RENDER',path,'center',c.round(1),'size',(mx-mn).round(1))
