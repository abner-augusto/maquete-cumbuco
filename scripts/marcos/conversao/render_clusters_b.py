import bpy, sys, json, numpy as np
S=sys.argv[sys.argv.index('--')+1]; sys.path.insert(0,S)
from render_util import render
bpy.ops.wm.read_factory_settings(use_empty=True)
V=np.load(S+'/eq_V.npy'); T=np.load(S+'/eq_T.npy'); fl=np.load(S+'/eq_facelab.npy'); cl=np.load(S+'/eq_island_cluster.npy')
fc=cl[fl]
res=json.load(open(S+'/eq_clusters.json'))
import os; os.makedirs(S+'/cl',exist_ok=True)
for r in [x for x in res if x["cluster"] in (0,2,7,4,6,30,11,1,12,13,14,15,21,18)]:
    k=r['cluster']; TT=T[fc==k]; u,inv=np.unique(TT.ravel(),return_inverse=True)
    me=bpy.data.meshes.new('c%d'%k); me.from_pydata(V[u].tolist(),[],inv.reshape(-1,3).tolist())
    o=bpy.data.objects.new('c%d'%k,me); bpy.context.scene.collection.objects.link(o)
    render(S+'/cl/c%02d.png'%k,[o],res=500,color='OBJECT',az=-30,el=30)
    bpy.data.objects.remove(o)
