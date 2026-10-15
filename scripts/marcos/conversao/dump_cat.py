import bpy, numpy as np, sys
a=sys.argv[sys.argv.index('--')+1:]; S=a[0]
for name in a[1:]:
    me=bpy.data.objects[name].data
    V=np.empty(len(me.vertices)*3,np.float32); me.vertices.foreach_get('co',V)
    T=np.empty(len(me.polygons)*3,np.int32); me.polygons.foreach_get('vertices',T)
    np.save(f'{S}/{name}_V.npy',V.reshape(-1,3)); np.save(f'{S}/{name}_T.npy',T.reshape(-1,3)); print('DUMP',name)
