from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import json
from studio import render_frame

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'p2_balls.blend'))
scene = bpy.context.scene
obj = bpy.data.objects['Shallow tray end']
scene.frame_set(1)
bpy.context.view_layer.update()
evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
origin = evaluated.matrix_world.translation.copy()
rotation = evaluated.matrix_world.to_quaternion().copy()
max_xy = 0
max_z = 0
max_angle = 0
rows = []
for frame in range(1,49):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    position = evaluated.matrix_world.translation.copy()
    xy = (position-origin).xy.length
    dz = abs(position.z-origin.z)
    angle = evaluated.matrix_world.to_quaternion().rotation_difference(rotation).angle*180/3.141592653589793
    max_xy,max_z,max_angle = max(max_xy,xy),max(max_z,dz),max(max_angle,angle)
    if frame in [1,4,13,48]:
        rows.append({'frame':frame,'position':list(position),'tiltDegrees':angle})
report = {'scope':'Active front tray beam before vehicle contact, cached frames 1-48',
          'cacheBaked':scene.rigidbody_world.point_cache.is_baked,
          'maxHorizontalDisplacement':max_xy,'maxVerticalSettlement':max_z,'maxTiltDegrees':max_angle,
          'samples':rows,'endBeamLength':4.32,'sideBeamInnerFaceX':2.18,'cornerClearancePerSide':.02,
          'note':'Only the two tray end-beam lengths changed; balls, materials, vehicle animation and other physics settings retained'}
report['stableBeforeContact'] = max_xy < .003 and max_angle < .10 and max_z < .006
(ROOT/'p2_balls_support_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
if not report['stableBeforeContact']:
    raise RuntimeError('Tray end beam is not stable before contact')
if '--stills' in sys.argv:
    for frame in [1,4,13,48]:
        render_frame(scene,frame,f'p2_balls_support_f{frame:04d}.png',960,540,16,False)
