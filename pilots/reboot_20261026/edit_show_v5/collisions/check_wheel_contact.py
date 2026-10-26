from pathlib import Path
import bpy,json,math
ROOT=Path(__file__).resolve().parent
rows=[]
for kind in ['buttons','deadline']:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/kind/'scene.blend'));sc=bpy.context.scene;root=bpy.data.objects['KimiTruck_animated_proxy_root'];wheels=[o for o in root.children if o.name.startswith('KimiFrozen_') and o.name!='KimiFrozen_body'];radii={o.name:max(math.hypot(v.co.y,v.co.z) for v in o.data.vertices) for o in wheels};checks=[]
    for f in [18,36,44,49,54,65,76,83]:
        sc.frame_set(f);y0=root.location.y;a0={o.name:o.rotation_euler.x for o in wheels};sc.frame_set(f+1);vy=(root.location.y-y0)*24
        checks.append({'frame':f,'truck_velocity_y':vy,'wheel_ground_velocity_y':{o.name:vy+(o.rotation_euler.x-a0[o.name])*24*radii[o.name] for o in wheels}})
    max_slip=max(abs(v) for c in checks for v in c['wheel_ground_velocity_y'].values());row={'scene':kind,'wheel_count':len(wheels),'geometry_radii':radii,'maximum_residual_contact_speed_m_s':max_slip,'pass':len(wheels)==10 and max_slip<.02,'samples':checks};rows.append(row);print('CONTACT_CHECK',kind,len(wheels),max_slip,flush=True)
(ROOT/'wheel_contact_check.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
