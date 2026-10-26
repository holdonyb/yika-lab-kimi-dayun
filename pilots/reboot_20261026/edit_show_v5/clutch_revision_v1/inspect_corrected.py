"""Read author-delivered BLEND, inspect actual evaluated geometry and motion. No source edits."""
from pathlib import Path
import bpy,json,hashlib,sys,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
ARGS=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
SOURCE=Path(ARGS[0]);OUTPUT=ROOT/'evidence'/f'{SOURCE.stem}_evaluated.json'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));scene=bpy.context.scene
control=bpy.data.objects['PowertrainControl'];root=bpy.data.objects['Clutch']
names=['Clutch_Flywheel','Clutch_FlywheelFrictionFace','Clutch_FrictionDisc','Clutch_PressurePlate',
       'Clutch_ReleaseContactRace','Clutch_ReleaseCarrier','Clutch_InputShaft']
rows=[]
for frame in range(1,193):
    scene.frame_set(frame);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();inv=root.evaluated_get(dg).matrix_world.inverted()
    parts={}
    for name in names:
        o=bpy.data.objects[name];e=o.evaluated_get(dg);mat=inv@e.matrix_world
        mesh=e.to_mesh();coordinates=[mat@v.co for v in mesh.vertices];e.to_mesh_clear()
        parts[name]={'yBounds':[min(p.y for p in coordinates),max(p.y for p in coordinates)],
            'location':list(e.location),'worldPosition':list(e.matrix_world.translation),'worldQuaternion':list(e.matrix_world.to_quaternion())}
    active=bpy.data.objects['Clutch_ActiveRotation'].evaluated_get(dg)
    driven=bpy.data.objects['Clutch_InputRotation'].evaluated_get(dg)
    fly=parts['Clutch_FlywheelFrictionFace']['yBounds'];disc=parts['Clutch_FrictionDisc']['yBounds'];press=parts['Clutch_PressurePlate']['yBounds']
    rows.append({'frame':frame,'time':(frame-1)/24,'release':float(control['clutch_release']),
        'engineAngle':float(control['engine_angle']),'clutchAngle':float(control['clutch_angle']),
        'activeAngle':active.rotation_euler.y,'drivenAngle':driven.rotation_euler.y,
        'flywheelGap':disc[0]-fly[1],'pressureGap':press[0]-disc[1],'parts':parts})
tol=5e-6;issues=[]
for r in rows:
    if min(r['flywheelGap'],r['pressureGap']) < -tol:issues.append({'frame':r['frame'],'issue':'Friction faces overlap','gaps':[r['flywheelGap'],r['pressureGap']]})
    if abs(r['activeAngle']-r['engineAngle'])>.0001:issues.append({'frame':r['frame'],'issue':'Active rotation differs from engine'})
    if abs(r['drivenAngle']-r['clutchAngle'])>.0001:issues.append({'frame':r['frame'],'issue':'Driven rotation differs from input'})
open_frames=[r['frame'] for r in rows if min(r['flywheelGap'],r['pressureGap'])>tol]
recontact=next((r['frame'] for r in rows if r['time']>=4 and max(r['flywheelGap'],r['pressureGap'])<=tol),None)
restart=next((r['frame'] for a,r in zip(rows,rows[1:]) if r['time']>=4 and abs(r['drivenAngle']-a['drivenAngle'])>1e-5),None)
if restart is not None and recontact is not None and restart<recontact:
    issues.append({'issue':'Stopped driven side restarts before geometric contact','restartFrame':restart,'recontactFrame':recontact})
if not open_frames:issues.append({'issue':'No real dual-face clearance'})
summary={'firstClearanceFrame':min(open_frames) if open_frames else None,'lastClearanceFrame':max(open_frames) if open_frames else None,
    'recontactFrame':recontact,'drivenRestartFrame':restart,
    'fullOpenGaps':max(([r['flywheelGap'],r['pressureGap']] for r in rows),key=sum),
    'carrierYAtFrame1':rows[0]['parts']['Clutch_ReleaseCarrier']['location'][1],
    'carrierYAtFrame85':rows[84]['parts']['Clutch_ReleaseCarrier']['location'][1]}
report={'source':str(SOURCE),'sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'coordinateSystem':'Clutch-root local Y; actual evaluated vertices including modifiers and parenting',
    'passed':not issues,'issues':issues,'summary':summary,'rows':rows}
OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'source':str(SOURCE),'output':str(OUTPUT),'passed':not issues,'summary':summary,'issues':issues[:10]},ensure_ascii=False,indent=2),flush=True)
