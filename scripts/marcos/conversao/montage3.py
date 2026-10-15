import sys,json
from PIL import Image, ImageDraw
S=sys.argv[1]; res={r['cluster']:r for r in json.load(open(S+'/eq_clusters.json'))}
ks=(0,2,7,4,6,30,11,1,12,13,14,15,21,18)
w,h=500,350;cols=7; M=Image.new('RGB',(w*cols,h*2)); d=ImageDraw.Draw(M)
for i,k in enumerate(ks):
    im=Image.open(f'{S}/cl/c{k:02d}.png').convert('RGB'); x,y=(i%cols)*w,(i//cols)*h; M.paste(im,(x,y)); d.text((x+5,y+5),f"c{k} {res[k]['tris']} {res[k]['size']} z{res[k]['zmin']}",fill=(255,255,0))
M.save(S+'/cl_montage_b.png')
