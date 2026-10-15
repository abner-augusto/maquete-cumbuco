import bpy, sys
S=sys.argv[sys.argv.index('--')+1]; sys.path.insert(0,S)
from render_util import render
obs=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.endswith('LINHAS')]
eq=[o for o in obs if o.name.endswith('EQUIPAMENTO')]
rest=[o for o in obs if o not in eq]
render(S+'/prev_clube_EQUIP_so.png',eq)
render(S+'/prev_clube_sem_EQUIP.png',rest)
render(S+'/prev_clube_EQUIP_so_b.png',eq,az=135,el=30)
render(S+'/prev_clube_sem_EQUIP_b.png',rest,az=135,el=30)
