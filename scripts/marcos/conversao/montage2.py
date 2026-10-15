import sys
from PIL import Image
S=sys.argv[1]
ims=[Image.open(f'{S}/rm_{t}.png').convert('RGB').resize((700,490)) for t in ['play','mesa','pend','bar']]
M=Image.new('RGB',(1400,980)); [M.paste(im,((i%2)*700,(i//2)*490)) for i,im in enumerate(ims)]; M.save(S+'/rm_zones.png')
