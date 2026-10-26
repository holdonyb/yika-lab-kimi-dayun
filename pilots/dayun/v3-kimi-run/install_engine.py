from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import json
from mathutils import Vector
from geo import (group, register, registry, box, cylinder, mesh, clone_tree,
                 capture_rest, export_registry)
from studio import studio

ROOT = Path(__file__).resolve().parent
scene = bpy.context.scene
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets'/'dayun_base_frozen.blend'))
scene = bpy.context.scene
from wheel_end import create_hub, create_wheel


def remove_tree(obj):
    for child in list(obj.children_recursive):
        bpy.data.objects.remove(child, do_unlink=True)
    bpy.data.objects.remove(obj, do_unlink=True)


base = bpy.data.objects['Dayun_N8E_6x4']
for obj in list(base.children):
    if obj.name == 'Engine' or obj.get('partType') == 'wheel':
        remove_tree(obj)
for obj in list(bpy.data.objects):
    if obj.type == 'LIGHT' or obj.type == 'CAMERA' or obj.name == 'Studio ground':
        bpy.data.objects.remove(obj, do_unlink=True)
for obj in list(base.children_recursive):
    if obj.location.y < -2 and obj.name.startswith(('Axle housing','Differential casing')):
        bpy.data.objects.remove(obj, do_unlink=True)
    elif obj.name.startswith('Propeller shaft'):
        bpy.data.objects.remove(obj, do_unlink=True)

assembly = group('TruckAssembly')
base.parent = assembly
base['source'] = 'v1-frozen-bb6929a1'
control = group('PowertrainControl',base)
control['engine_angle'] = 0.0
control['clutch_angle'] = 0.0
control['wheel_angle'] = 0.0
control['clutch_engaged'] = 1.0
control['source'] = 'v3-kinematic-control'


def drive(obj, path, index, property_name, expression):
    curve = obj.driver_add(path) if index is None else obj.driver_add(path,index)
    driver = curve.driver
    variable = driver.variables.new()
    variable.name = 'v'
    variable.type = 'SINGLE_PROP'
    variable.targets[0].id = control
    variable.targets[0].data_path = '["'+property_name+'"]'
    driver.expression = expression


engine_system = group('EngineSystem',base,(0,-1.85,1.02))
engine_system.rotation_euler.z = 1.57079632679
engine_system['source'] = 'v2-frozen-dbae2ea6'
with bpy.data.libraries.load(str(ROOT/'assets'/'engine_core_frozen.blend'),link=False) as (source,target):
    target.objects = source.objects
imported = target.objects
core = next(obj for obj in imported if obj.name == 'InlineSixCore')
controller = next(obj for obj in imported if obj.name == 'CrankAngleController')
keep = {core,controller,*core.children_recursive}
for obj in imported:
    if obj not in keep:
        bpy.data.objects.remove(obj,do_unlink=True)
for obj in list(keep):
    if 'PhotoSection' in obj.name or obj.name.startswith(('Display support foot','Support pad')):
        keep.discard(obj)
        bpy.data.objects.remove(obj,do_unlink=True)
for obj in keep:
    if obj.name not in bpy.context.collection.objects:
        bpy.context.collection.objects.link(obj)
    if obj.type == 'MESH':
        obj.animation_data_clear()
    elif obj != controller and not (obj.animation_data and obj.animation_data.drivers):
        obj.animation_data_clear()
    obj.hide_render = False
    obj.hide_viewport = False
    if obj.get('part_family'):
        obj['source'] = 'v2-frozen-dbae2ea6'
        obj['semantic_id'] = obj.name
        registry.append({'id':obj.name,'family':obj['part_family'],
                         'shape':obj.get('structure','Imported fine mechanical part'),
                         'note':'Frozen v2 core with installed liners and no photographic support'})
core.parent = engine_system
core.location = (0,0,0)
core.rotation_euler = (0,0,0)
controller.parent = engine_system
controller.location = (0,0,0)
controller.animation_data_clear()
controller['angle'] = 0.0
for name in ['ring1_open','ring2_open','oil_open']:
    controller[name] = 0.0
drive(controller,'["angle"]',None,'engine_angle','v')
bpy.data.objects['CylinderLinerBank_PhotographyLift'].animation_data_clear()
bpy.data.objects['CylinderLinerBank_PhotographyLift'].location.z = 0
bpy.data.objects['FirstCylinderAssemblyLift'].animation_data_clear()
bpy.data.objects['FirstCylinderAssemblyLift'].location = (0,0,0)
for i,x in enumerate([(j-2.5)*.165 for j in range(6)],start=1):
    liner = bpy.data.objects[f'CylinderLiner_{i:02d}']
    liner.animation_data_clear()
    liner.location = (x,0,0)

hub = create_hub('WheelEnd_R',base,(1.10,-2.48,.54),1)
front_wheel = create_wheel('Front_R',base,(1.10,-2.48,.54),1,False,'front')
hub_roots = [hub]
wheel_roots = [front_wheel]
for axle,y in [('Mid',1.27),('Rear',2.60)]:
    for dual,x in [('Outer',1.175),('Inner',.825)]:
        wheel = create_wheel(f'{axle}_R_{dual}',base,(x,y,.54),1,True,dual.lower())
        wheel_roots.append(wheel)
for side,label in [(-1,'L'),(1,'R')]:
    for axle,y in [('Mid',1.27),('Rear',2.60)]:
        hub_clone = clone_tree(hub,base,f'_{axle}_{label}')
        hub_clone.location = (side*.97,y,.54)
        hub_clone['side'] = side
        hub_roots.append(hub_clone)
        if side < 0:
            from geo import mirror_assembly
            mirror_assembly(hub_clone)
front_left = clone_tree(hub,base,'_Front_L')
front_left.location = (-1.10,-2.48,.54)
front_left['side'] = -1
from geo import mirror_assembly
mirror_assembly(front_left)
hub_roots.append(front_left)
for side,label in [(-1,'L')]:
    for axle,y in [('Mid',1.27),('Rear',2.60)]:
        for dual,x in [('Outer',1.175),('Inner',.825)]:
            prototype = next(w for w in wheel_roots if w.name == f'{axle}_R_{dual}')
            wheel = clone_tree(prototype,base,f'_{label}')
            wheel.location = (side*x,y,.54)
            wheel['side'] = side
            wheel['dualPosition'] = dual.lower()
            wheel_roots.append(wheel)
            if side < 0:
                mirror_assembly(wheel)
front_left_wheel = clone_tree(front_wheel,base,'_L')
front_left_wheel.location = (-1.10,-2.48,.54)
front_left_wheel['side'] = -1
mirror_assembly(front_left_wheel)
wheel_roots.append(front_left_wheel)
for root in hub_roots:
    rotating = next(obj for obj in root.children if obj.get('part_family') == 'rotating_hub')
    drive(rotating,'rotation_euler',0,'wheel_angle','v')
for root in wheel_roots:
    drive(root,'rotation_euler',0,'wheel_angle','v')

steering = group('FrontSteeringAxle',base,(0,-2.48,.54))
register(steering,'front_steer_axle','Non-driven forged front axle with kingpins and steering linkage')
box('Front forged axle beam',(0,0,-.065),(1.62,.105,.095),bpy.data.materials['Steel | chassis'],steering,.016)
for side in [-1,1]:
    knuckle = group('SteeringKnuckle_'+str(side),steering,(side*1.02,0,0))
    register(knuckle,'steering_knuckle','Steering knuckle pivoting about a vertical kingpin, not a differential')
    cylinder('Kingpin',.022,.18,(0,0,0),bpy.data.materials['Steel | satin'],knuckle,(0,0,1),48)
    cylinder('Knuckle spindle',.034,.18,(side*.07,0,0),bpy.data.materials['Steel | satin'],knuckle,(1,0,0),48)
    box('Steering arm',(0,.075,.035),(.055,.18,.035),bpy.data.materials['Steel | chassis'],knuckle,.008)
    cylinder('Tie rod end',.022,.055,(0,.155,.035),bpy.data.materials['Steel | satin'],knuckle,(0,0,1),32)
cylinder('Steering tie rod',.014,2.08,(0,.155,.035),bpy.data.materials['Steel | satin'],steering,(1,0,0),48)
cylinder('Tie rod adjustment sleeve',.022,.20,(0,.155,.035),bpy.data.materials['Steel | chassis'],steering,(1,0,0),48)

studio(scene,(0,-1.5,1.25),4,-.03)
scene.frame_set(1)
capture_rest(base)
report = export_registry(ROOT/'stage1_entities.json',base)
report['stage'] = 'Fine engine and representative wheel ends installed; remaining vehicle systems are not yet claimed complete'
report['pending'] = ['Engine head and valvetrain','Clutch and gearbox internals','Rear differential internals',
                     'Cab interior refinement','Radiator and accessory details','Full-vehicle explosion and P2']
(ROOT/'stage1_entities.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'stage1_state.json').write_text(json.dumps({'stage':report['stage'],'pending':report['pending'],
    'physicalInstances':report['physicalInstances'],'physicalFamilies':report['physicalFamilies'],
    'wheelHubAssemblies':len(hub_roots),'wheelAssemblies':len(wheel_roots),
    'note':'Six hub assemblies and ten tire/rim assemblies; rear dual tires share one hub per side'},ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'truck_stage1.blend'))
print('STAGE1_COMPLETE',json.dumps({'hubs':len(hub_roots),'wheels':len(wheel_roots),
      'families':report['physicalFamilies'],'instances':report['physicalInstances']},ensure_ascii=False))
