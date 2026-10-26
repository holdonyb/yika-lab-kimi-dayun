from pathlib import Path
import bpy
import json
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'truck_systems.blend'))
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
report = {}
for name in ['Cab', 'EngineSystem', 'Gearbox', 'WheelEnd_R', 'Front_R', 'Mid_R_Outer', 'FinalDrive_Mid']:
    root = bpy.data.objects[name]
    children = []
    for obj in root.children:
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        children.append({
            'id': obj.name, 'type': obj.type, 'family': obj.get('part_family',''),
            'location': list(obj.location), 'rotation': list(obj.rotation_euler),
            'scale': list(obj.scale), 'dimensions': list(obj.dimensions),
            'worldCenter': list(sum(points,Vector())/8) if points else list(obj.matrix_world.translation),
            'children': len(obj.children),
        })
    report[name] = {'matrix': [list(row) for row in root.matrix_local], 'children': children}
(ROOT/'spread_geometry_inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for root,data in report.items():
    print('\nROOT',root)
    for obj in data['children']:
        print(obj['id'],obj['family'],'loc',[round(x,3) for x in obj['location']], 'dim',[round(x,3) for x in obj['dimensions']], 'children',obj['children'])
