import bpy, json, sys, os
from mathutils import Vector
out = sys.argv[sys.argv.index('--')+1]
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene
def tris(o):
    if o.type != 'MESH': return 0
    e = o.evaluated_get(dg)
    try:
        m = e.to_mesh()
    except Exception: return 0
    n = sum(len(p.vertices)-2 for p in m.polygons)
    e.to_mesh_clear(); return n
otri = {}
bbmin=[1e18]*3; bbmax=[-1e18]*3
for o in sc.objects:
    otri[o.name]=tris(o)
    if o.type=='MESH':
        for c in o.bound_box:
            w=o.matrix_world@Vector(c)
            for i in range(3): bbmin[i]=min(bbmin[i],w[i]); bbmax[i]=max(bbmax[i],w[i])
def coll(c):
    objs=list(c.objects)
    d={'name':c.name,'n_obj':len(objs),'n_mesh':sum(o.type=='MESH' for o in objs),
       'tris':sum(otri.get(o.name,0) for o in objs),'hide_render':c.hide_render,
       'children':[coll(ch) for ch in c.children]}
    d['tris_total']=d['tris']+sum(ch['tris_total'] for ch in d['children'])
    d['n_obj_total']=d['n_obj']+sum(ch['n_obj_total'] for ch in d['children'])
    return d
mats=[]
for m in bpy.data.materials:
    imgs=[]
    if m.use_nodes and m.node_tree:
        imgs=[n.image.name for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
    mats.append({'name':m.name,'users':m.users,'images':imgs,'blend_method':m.blend_method})
types={}
for o in sc.objects: types[o.type]=types.get(o.type,0)+1
mods={}
for o in sc.objects:
    for md in o.modifiers: mods[md.type]=mods.get(md.type,0)+1
r={'file':bpy.data.filepath,'units':{'system':sc.unit_settings.system,'scale_length':sc.unit_settings.scale_length,'length_unit':sc.unit_settings.length_unit},
 'n_objects':len(sc.objects),'types':types,'modifiers':mods,'tris_total':sum(otri.values()),
 'bbox_min':bbmin,'bbox_max':bbmax,'dims_m':[bbmax[i]-bbmin[i] for i in range(3)],
 'collections':coll(sc.collection),
 'materials':mats,'images':[{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file),'filepath':i.filepath} for i in bpy.data.images],
 'root_scales':sorted({tuple(round(x,4) for x in o.scale) for o in sc.objects if o.parent is None}),
 'top_objects_by_tris':sorted(otri.items(),key=lambda x:-x[1])[:60],
 'object_names':{o.name:[o.type,otri[o.name],[c.name for c in o.users_collection], o.parent.name if o.parent else None] for o in sc.objects}}
json.dump(r,open(out,'w',encoding='utf-8'),ensure_ascii=False,indent=1,default=str)
print('OK',r['n_objects'],r['tris_total'],r['dims_m'])
