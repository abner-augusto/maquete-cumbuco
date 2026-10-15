import bpy, sys, numpy as np, json
S=sys.argv[sys.argv.index('--')+1]; sys.path.insert(0,S)
from render_util import render
bpy.ops.wm.read_factory_settings(use_empty=True)
cols={'OUTROS':(.9,.9,.2,1),'PISO':(.2,.8,.2,1),'ESQUADRIA':(1,.5,0,1),'LAJE':(.2,.3,1,1),'VIGA':(0,.9,.9,1),'VIDRO':(.6,.8,1,1),'GRADIL':(1,0,1,1),'PAREDE':(1,0,0,1)}
objs=[]
for cat,c in cols.items():
    name='CLUBE_'+cat
    V=np.load(f'{S}/{name}_V.npy'); T=np.load(f'{S}/{name}_T.npy'); m=np.load(f'{S}/{name}_rmmask.npy')
    TT=T[m]
    if len(TT)==0: continue
    u,inv=np.unique(TT.ravel(),return_inverse=True)
    me=bpy.data.meshes.new(cat); me.from_pydata(V[u].tolist(),[],inv.reshape(-1,3).tolist())
    o=bpy.data.objects.new(cat,me); o.color=c; bpy.context.scene.collection.objects.link(o); objs.append(o)
render(S+'/rm_all.png',objs,res=1200,color='OBJECT',az=-30,el=35)
# zone close-ups via temporary clip: create zone sub-objects
def zone(tag,b0,b1):
    sub=[]
    for o in objs:
        V=np.array([v.co[:] for v in o.data.vertices])
        P=np.array([p.vertices[:] for p in o.data.polygons])
        c=V[P].mean(1); k=((c>=b0)&(c<=b1)).all(1)
        if k.sum()==0: continue
        u,inv=np.unique(P[k].ravel(),return_inverse=True)
        me=bpy.data.meshes.new(tag+o.name); me.from_pydata(V[u].tolist(),[],inv.reshape(-1,3).tolist())
        z=bpy.data.objects.new(tag+o.name,me); z.color=o.color; bpy.context.scene.collection.objects.link(z); sub.append(z)
    render(S+f'/rm_{tag}.png',sub,res=700,color='OBJECT',az=-30,el=35)
zone('play',np.array([21,27,-1]),np.array([29,35,3]))
zone('mesa',np.array([47,66.5,-5]),np.array([51,70,-2]))
zone('pend',np.array([59,75,2]),np.array([64,80,10]))
zone('bar',np.array([11,57,-1]),np.array([19,64,4]))
