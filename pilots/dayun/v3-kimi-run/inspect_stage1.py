from pathlib import Path
import bpy
import json

ROOT = Path(__file__).resolve().parent
scene = bpy.context.scene
names = ['Cab','Door_L','Door_R','EngineSystem','InlineSixCore']
report = {}
for name in names:
    obj = bpy.data.objects[name]
    action = obj.animation_data.action if obj.animation_data else None
    report[name] = {'location':list(obj.location),'parent':obj.parent.name if obj.parent else None,
                    'action':action.name if action else None,
                    'drivers':[curve.data_path for curve in obj.animation_data.drivers] if obj.animation_data else []}
scene.frame_set(1)
cab = bpy.data.objects['Cab']
cab.location.z = 1.05
report['beforePhotoFrameSet'] = list(cab.location)
scene.frame_set(1)
report['afterPhotoFrameSet'] = list(cab.location)
for name in ['Cab','Door_L','Door_R']:
    obj = bpy.data.objects[name]
    obj.animation_data_clear()
    obj.location.z = 1.05
report['afterClearingPhotoOverrides'] = {name:list(bpy.data.objects[name].location) for name in ['Cab','Door_L','Door_R']}
(ROOT/'stage1_inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
