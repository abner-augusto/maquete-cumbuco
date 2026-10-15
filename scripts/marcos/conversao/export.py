import bpy, sys, numpy as np, bmesh, json, struct, time
a=sys.argv[sys.argv.index('--')+1:]; S, mode, out = a[0], a[1], a[2]
sc=bpy.context.scene
# 1) drop line-only objects (LINHAS: 0 tris, outlier vertex at y=-1130)
for o in list(sc.objects):
    if o.name.endswith('_LINHAS'): bpy.data.objects.remove(o)
# 2) materials: Principled base colour from the viewport colour (bl_build only set diffuse_color)
ALPHA={'VIDRO':0.35,'AGUA':0.8}
for m in bpy.data.materials:
    if not m.use_nodes: m.use_nodes=True
    p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if p is None: continue
    c=m.diffuse_color
    p.inputs['Base Color'].default_value=(c[0],c[1],c[2],1)
    p.inputs['Roughness'].default_value=0.6
    if m.name in ALPHA:
        p.inputs['Alpha'].default_value=ALPHA[m.name]
        for attr,val in (('blend_method','BLEND'),('surface_render_method','BLENDED')):
            try: setattr(m,attr,val)
            except Exception as e: print('warn',attr,e)
        print('ALPHA',m.name,getattr(m,'blend_method',None),getattr(m,'surface_render_method',None))
# 3) furniture removal by precomputed face masks
if mode=='sem':
    for o in list(sc.objects):
        f=f'{S}/{o.name}_rmmask.npy'
        try: mk=np.load(f)
        except FileNotFoundError: continue
        me=o.data; assert len(me.polygons)==len(mk), (o.name,len(me.polygons),len(mk))
        bm=bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[bm.faces[i] for i in np.where(mk)[0]],context='FACES')
        bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
        bm.to_mesh(me); bm.free(); me.update()
        print('MASKED',o.name,int(mk.sum()),'->',len(me.polygons))
tri=sum(len(o.data.polygons) for o in sc.objects if o.type=='MESH')
print('TRIS_EXPORT',tri, 'OBJS',len(sc.objects))
t=time.time()
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_apply=True, export_yup=True, use_selection=False, export_image_format='AUTO')
print('EXPORTED',out,round(time.time()-t,1),'s')
with open(out,'rb') as f:
    f.read(12); cl,_=struct.unpack('<II',f.read(8)); g=json.loads(f.read(cl))
for m in g.get('materials',[]):
    print('GMAT',m['name'],m.get('alphaMode','OPAQUE'),[round(x,3) for x in m.get('pbrMetallicRoughness',{}).get('baseColorFactor',[1,1,1,1])])
print('GIMAGES',len(g.get('images',[])),'NODES',len(g['nodes']),'EXT',g.get('extensionsUsed'))
