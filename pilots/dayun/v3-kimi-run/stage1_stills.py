from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from studio import camera, render_frame

ROOT = Path(__file__).resolve().parent
scene = bpy.context.scene
scene.frame_set(1)
cab = bpy.data.objects['Cab']
for obj in [cab,bpy.data.objects['Door_L'],bpy.data.objects['Door_R']]:
    obj.animation_data_clear()
    obj.location.z = 1.25
camera(scene,(3.20,-1.70,2.00),(0,-1.85,1.18),58,11)
render_frame(scene,1,'p1_engine_installed.png',1920,1080,64)
cab.location.z = 0
bpy.data.objects['Door_L'].location.z = 0
bpy.data.objects['Door_R'].location.z = 0

hub = bpy.data.objects['WheelEnd_R']
wheel = bpy.data.objects['Front_R']
base = bpy.data.objects['Dayun_N8E_6x4']
visible = {hub,wheel,*hub.children_recursive,*wheel.children_recursive}
for obj in base.children_recursive:
    if obj.type == 'MESH' and obj not in visible:
        obj.hide_render = True
wheel.location.x += .32
wheel.location.y += .40
bpy.data.objects['WheelEnd_R_BrakeDrum'].location.x += .22
bpy.data.objects['WheelEnd_R_BrakeDrum'].location.y -= .22
bpy.data.objects['WheelEnd_R_BackingPlate'].location.x -= .14
bpy.data.objects['WheelEnd_R_BackingPlate'].location.y += .35
bpy.data.objects['WheelEnd_R_OuterBearing'].location.x += .10
from studio import area
area('Wheel detail fill',(0.0,-3.1,1.50),8,(.82,.9,1.0),.55,(1.1,-2.48,.60),'RECTANGLE',.12)
camera(scene,(-.35,-3.60,1.45),(1.05,-2.48,.58),60,11)
render_frame(scene,1,'p1_wheel_end.png',1920,1080,64)
print('STAGE1_STILLS_RENDERED')
