import bpy, collections
sc=bpy.context.scene
print('NOBJ',len(sc.objects), collections.Counter(o.type for o in sc.objects))
print('COLLS',[ (c.name,len(c.all_objects)) for c in bpy.data.collections][:40])
names=collections.Counter()
import re
for o in sc.objects:
    names[re.sub(r'[\._]\d+$','',o.name)]+=1
for k,v in names.most_common(150): print('N',v,k)
print('MATS',len(bpy.data.materials),'IMGS',len(bpy.data.images))
