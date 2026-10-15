import sys, numpy as np, json
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
S=sys.argv[1]
V=np.load(S+'/eq_V.npy'); T=np.load(S+'/eq_T.npy'); fl=np.load(S+'/eq_facelab.npy')
nc=fl.max()+1
vl=np.full(len(V),-1); vl[T.ravel()]=np.repeat(fl,3)
ok=vl>=0
mn=np.full((nc,3),1e9); mx=np.full((nc,3),-1e9)
np.minimum.at(mn,vl[ok],V[ok]); np.maximum.at(mx,vl[ok],V[ok])
cnt=np.bincount(fl,minlength=nc)
tol=0.15
a=mn-tol; b=mx+tol
ov=(a[:,None,:]<=b[None,:,:]).all(2)&(a[None,:,:]<=b[:,None,:]).all(2)
nk,cl=connected_components(coo_matrix(ov),directed=False)
res=[]
for k in range(nk):
    idx=np.where(cl==k)[0]
    m0=mn[idx].min(0); m1=mx[idx].max(0)
    res.append(dict(cluster=int(k),islands=len(idx),tris=int(cnt[idx].sum()),center=((m0+m1)/2).round(2).tolist(),size=(m1-m0).round(2).tolist(),zmin=round(float(m0[2]),2),zmax=round(float(m1[2]),2)))
res.sort(key=lambda r:-r['tris'])
json.dump(res,open(S+'/eq_clusters.json','w'),indent=0)
np.save(S+'/eq_island_cluster.npy',cl)
print('clusters',nk)
for r in res: print(r['cluster'],r['islands'],r['tris'],r['center'],r['size'],r['zmin'],r['zmax'])
