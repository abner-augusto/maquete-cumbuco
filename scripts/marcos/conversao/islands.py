import sys, numpy as np, json
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
S=sys.argv[1]
V=np.load(S+'/eq_V.npy'); T=np.load(S+'/eq_T.npy')
n=len(V)
A=coo_matrix((np.ones(len(T)*2),(np.r_[T[:,0],T[:,0]],np.r_[T[:,1],T[:,2]])),shape=(n,n))
nc,lab=connected_components(A,directed=False)
fl=lab[T[:,0]]
cnt=np.bincount(fl,minlength=nc)
order=np.argsort(-cnt)
# per-island bbox
mn=np.full((nc,3),1e9); mx=np.full((nc,3),-1e9)
np.minimum.at(mn,lab,V); np.maximum.at(mx,lab,V)
print('islands',nc,'tris',len(T))
# cluster islands spatially into objects: merge islands whose bboxes overlap (expanded 5cm)
rows=[]
for i in order[:80]:
    d=mx[i]-mn[i]; c=(mx[i]+mn[i])/2
    rows.append((int(i),int(cnt[i]),c.round(1).tolist(),d.round(2).tolist(),round(float(mn[i][2]),2),round(float(mx[i][2]),2)))
for r in rows: print(r)
np.save(S+'/eq_facelab.npy',fl)
# cumulative
cs=np.cumsum(cnt[order]); 
for k in [1,5,10,20,50,100,500]: print('top',k,int(cs[min(k,nc)-1]))
