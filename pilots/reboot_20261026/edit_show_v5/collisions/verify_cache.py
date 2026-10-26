from pathlib import Path
import json,sys,math
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
ARGS=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
rows=[]
for kind in ARGS:
    folder=ROOT/kind;report=json.loads((folder/'physics.json').read_text(encoding='utf8'));bpy.ops.wm.open_mainfile(filepath=str(folder/'scene.blend'));sc=bpy.context.scene;err=0
    for f in [1,36,52,80,100,160,228]:
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get();sample=report['poses'][f-1]['targets']
        for name,pose in sample.items():
            loc=bpy.data.objects[name].evaluated_get(dg).matrix_world.translation;err=max(err,(loc-Vector(pose['p'])).length)
    first=report['poses'][0]['targets'];first_moved=None;moving_count=0
    for p in report['poses']:
        movers=sum((Vector(v['p'])-Vector(first[n]['p'])).length>.12 for n,v in p['targets'].items())
        if movers and first_moved is None:first_moved=p['frame']
        moving_count=max(moving_count,movers)
    r={'kind':kind,'cache_reopen_max_position_error_m':err,'cache_baked':sc.rigidbody_world.point_cache.is_baked,'pre_1_5s_displacement_m':report['maximum_target_displacement_before_1_5s'],'target_count':report['target_count'],'targets_moved_over_25cm':report['targets_moved_over_25cm'],'first_target_moves_over_12cm_frame':first_moved,'first_target_moves_over_12cm_seconds':None if first_moved is None else (first_moved-1)/24,'target_animation_channels':report['target_animation_channels'],'pass':err<1e-5 and report['maximum_target_displacement_before_1_5s']<.05 and report['target_animation_channels']==0 and report['targets_moved_over_25cm']>0}
    (folder/'cache_reopen.json').write_text(json.dumps(r,indent=2),encoding='utf8');rows.append(r);print('VERIFY',r,flush=True)
(ROOT/'physics_validation.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
