import bpy, numpy as np, sys, math
S=sys.argv[sys.argv.index('--')+1]
from mathutils import Vector
for o in bpy.context.scene.objects:
    me=o.data
    V=np.empty(len(me.vertices)*3,np.float32); me.vertices.foreach_get('co',V); V=V.reshape(-1,3)
    if len(V)==0: print('BB',o.name,'empty'); continue
    q=np.percentile(V,[0,1,50,99,100],axis=0)
    print('BB',o.name,len(V),len(me.polygons),len(me.edges),'min',q[0].round(1),'p1',q[1].round(1),'p99',q[3].round(1),'max',q[4].round(1), 'mat', [m.name for m in me.materials], 'uv',len(me.uv_layers), 'mw_ident', o.matrix_world.is_identity if hasattr(o.matrix_world,'is_identity') else None)
    if o.name.endswith('EQUIPAMENTO') and 'CLUBE' in o.name:
        T=np.empty(sum(len(p.vertices) for p in me.polygons),np.int32); me.polygons.foreach_get('vertices',T) if all(len(p.vertices)==3 for p in me.polygons[:10]) else None
        np.save(S+'/eq_V.npy',V); np.save(S+'/eq_T.npy',T.reshape(-1,3))
for m in bpy.data.materials: print('MAT',m.name,tuple(round(x,3) for x in m.diffuse_color),m.use_nodes)
