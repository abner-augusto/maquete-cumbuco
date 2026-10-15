import bpy, numpy as np
for o in bpy.context.scene.objects:
    me=o.data
    if not len(me.polygons): continue
    V=np.empty(len(me.vertices)*3,np.float32); me.vertices.foreach_get('co',V); V=V.reshape(-1,3)
    T=np.empty(len(me.polygons)*3,np.int32); me.polygons.foreach_get('vertices',T); C=V[T.reshape(-1,3)].mean(1)
    for lab,k in (('far(y<150)',C[:,1]<150),('portaria(150-350)',(C[:,1]>=150)&(C[:,1]<350)),('rot(>=350)',C[:,1]>=350)):
        if k.sum(): print('P',o.name,lab,int(k.sum()),C[k].min(0).round(1),C[k].max(0).round(1))
