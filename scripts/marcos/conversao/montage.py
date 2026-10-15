import sys,glob,json
from PIL import Image, ImageDraw
S=sys.argv[1]; res=json.load(open(S+'/eq_clusters.json'))
ims=[];labs=[]
for r in res[:24]:
    ims.append(Image.open(S+'/cl/c%02d.png'%r['cluster']).convert('RGB')); labs.append('c%d %dk %s'%(r['cluster'],r['tris']//1000,r['size']))
w,h=ims[0].size; cols=6; rows=(len(ims)+cols-1)//cols
M=Image.new('RGB',(w*cols,h*rows),'white'); d=ImageDraw.Draw(M)
for i,(im,l) in enumerate(zip(ims,labs)):
    x,y=(i%cols)*w,(i//cols)*h; M.paste(im,(x,y)); d.text((x+5,y+5),l,fill=(255,255,0))
M.save(S+'/cl_montage.png')
