import sys, numpy as np, json
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
S,name=sys.argv[1],sys.argv[2]
V=np.load(f'{S}/{name}_V.npy'); T=np.load(f'{S}/{name}_T.npy'); n=len(V)
A=coo_matrix((np.ones(len(T)*2),(np.r_[T[:,0],T[:,0]],np.r_[T[:,1],T[:,2]])),shape=(n,n))
nc,lab=connected_components(A,directed=False); fl=lab[T[:,0]]
cnt=np.bincount(fl,minlength=nc)
mn=np.full((nc,3),1e9); mx=np.full((nc,3),-1e9)
np.minimum.at(mn,lab,V); np.maximum.at(mx,lab,V)
used=cnt>0
tol=0.05; a=mn-tol; b=mx+tol
# merge only small islands (<3m max dim) to avoid huge slabs bridging everything
small=((mx-mn).max(1)<3)&used
idx=np.where(small)[0]
ov=(a[idx][:,None,:]<=b[idx][None,:,:]).all(2)&(a[idx][None,:,:]<=b[idx][:,None,:]).all(2)
nk,c2=connected_components(coo_matrix(ov),directed=False)
cl=np.full(nc,-1); cl[idx]=c2
big=np.where(used&~small)[0]; cl[big]=nk+np.arange(len(big)); nk+=len(big)
cl[~used]=-1
fc=cl[fl]
res=[]
for k in range(nk):
    ii=np.where(cl==k)[0]
    m0=mn[ii].min(0); m1=mx[ii].max(0)
    res.append(dict(cluster=int(k),islands=len(ii),tris=int(cnt[ii].sum()),center=((m0+m1)/2).round(2).tolist(),size=(m1-m0).round(2).tolist()))
res.sort(key=lambda r:-r['tris'])
np.save(f'{S}/{name}_fc.npy',fc); json.dump(res,open(f'{S}/{name}_clusters.json','w'))
print(name,'islands',nc,'clusters',nk,'tris',len(T))
for r in res[:25]: print(r)
