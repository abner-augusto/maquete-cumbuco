import sys, numpy as np, json
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
S=sys.argv[1]
cl=json.load(open(S+'/eq_clusters.json'))
KEEP={0,2,7,4,6}
boxes=[]
cl=[r for r in cl if r['cluster'] not in KEEP]
for r in cl:
    c=np.array(r['center']); h=np.array(r['size'])/2
    boxes.append((c-h-0.10, c+h+0.10, c[2]-h[2]))
rep={}
for name in ['CLUBE_OUTROS','CLUBE_PISO','CLUBE_ESQUADRIA','CLUBE_PAREDE','CLUBE_LAJE','CLUBE_VIGA','CLUBE_PILAR','CLUBE_GRADIL','CLUBE_VIDRO','CLUBE_AGUA']:
    V=np.load(f'{S}/{name}_V.npy'); T=np.load(f'{S}/{name}_T.npy'); n=len(V)
    A=coo_matrix((np.ones(len(T)*2),(np.r_[T[:,0],T[:,0]],np.r_[T[:,1],T[:,2]])),shape=(n,n))
    nc,lab=connected_components(A,directed=False); fl=lab[T[:,0]]
    mn=np.full((nc,3),1e9); mx=np.full((nc,3),-1e9)
    np.minimum.at(mn,lab,V); np.maximum.at(mx,lab,V)
    small=(mx-mn).max(1)<3.0
    rm=np.zeros(nc,bool); which=np.full(nc,-1)
    for bi,(b0,b1,zfloor) in enumerate(boxes):
        inside=(mn>=b0).all(1)&(mx<=b1).all(1)
        notfloor=mx[:,2]>zfloor+0.10+0.03   # island rises above the cluster floor (flat floor tiles stay)
        hit=inside&small&notfloor&~rm
        rm|=hit; which[hit]=cl[bi]['cluster']
    fmask=rm[fl]
    np.save(f'{S}/{name}_rmmask.npy',fmask)
    per={}
    for c,t in zip(*np.unique(which[fl][fmask],return_counts=True)): per[int(c)]=int(t)
    rep[name]=dict(tris=int(len(T)),removed=int(fmask.sum()),by_cluster=per)
    print(name,len(T),'remove',int(fmask.sum()),per)
fl=np.load(S+'/eq_facelab.npy'); ic=np.load(S+'/eq_island_cluster.npy'); fc=ic[fl]
em=~np.isin(fc,list(KEEP)); np.save(S+'/CLUBE_EQUIPAMENTO_rmmask.npy',em)
rep['CLUBE_EQUIPAMENTO']=dict(tris=int(len(fl)),removed=int(em.sum()),kept_clusters=sorted(KEEP))
print('EQUIP remove',int(em.sum()),'of',len(fl))
json.dump(rep,open(S+'/rm_report.json','w'),indent=1)
