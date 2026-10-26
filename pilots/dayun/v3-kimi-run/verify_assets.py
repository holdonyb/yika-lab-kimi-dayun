from pathlib import Path
import bpy
import json
import math
from mathutils import Vector

ROOT = Path(__file__).resolve().parent


def matrix_error(a,b):
    return max(abs(a[r][c]-b[r][c]) for r in range(4) for c in range(4))


def explosion():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'truck_systems.blend'))
    bpy.context.scene.frame_set(1)
    base = bpy.data.objects['Dayun_N8E_6x4']
    original = {obj.name:obj.matrix_local.copy() for obj in base.children_recursive}
    parents = {obj.name:obj.parent.name if obj.parent else None for obj in base.children_recursive}
    original['TruckAssembly'] = bpy.data.objects['TruckAssembly'].matrix_local.copy()
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'p1_explosion.blend'))
    scene = bpy.context.scene
    scene.frame_set(265)
    bpy.context.view_layer.update()
    errors = []
    parent_errors = []
    for name,matrix in original.items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            errors.append({'id':name,'error':'missing'})
            continue
        error = matrix_error(obj.matrix_local,matrix)
        if error > .00002:
            errors.append({'id':name,'error':error})
        if name in parents and (obj.parent.name if obj.parent else None) != parents[name]:
            parent_errors.append(name)
    registry = json.loads((ROOT/'vehicle_entities.json').read_text(encoding='utf-8'))['entities']
    missing = [item['id'] for item in registry if item['id'] not in bpy.data.objects]
    report = {'source':'Independent reopen of truck_systems.blend and p1_explosion.blend',
              'frame':265,'checkedOriginalTransforms':len(original),'restoreErrors':errors,
              'parentErrors':parent_errors,'missingEntityIds':missing,
              'engineRotationZ':bpy.data.objects['EngineSystem'].rotation_euler.z}
    wheel = bpy.data.objects['Front_R']
    tread = bpy.data.objects['Front_R_Tire_Tread']
    scene.frame_set(12)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = tread.evaluated_get(depsgraph)
    vertices = [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]
    lowest = min(vertices,key=lambda point:point.z)
    center = wheel.matrix_world.translation
    axle = (wheel.matrix_world.to_3x3() @ Vector((1,0,0))).normalized()
    radius = center.z-lowest.z
    scene.frame_set(11)
    center_before = wheel.matrix_world.translation.copy()
    angle_before = bpy.data.objects['PowertrainControl']['wheel_angle']
    scene.frame_set(13)
    center_after = wheel.matrix_world.translation.copy()
    angle_after = bpy.data.objects['PowertrainControl']['wheel_angle']
    velocity = (center_after-center_before)/(2/24)
    angular_velocity = axle*(angle_after-angle_before)/(2/24)
    contact_actual = velocity+angular_velocity.cross(Vector((0,0,-radius)))
    contact_nominal = velocity+angular_velocity.cross(Vector((0,0,-.54)))
    report['rolling'] = {'note':'Independent v = v_center + omega cross r, using the actual wheel axle and evaluated tread',
                        'frame':12,'actualLowestTreadRadius':radius,'centerVelocity':list(velocity),
                        'axle':list(axle),'angularVelocity':list(angular_velocity),
                        'contactVelocityActualTread':list(contact_actual),
                        'contactVelocityNominalRadius':list(contact_nominal),
                        'nominalRadius':.54}
    (ROOT/'p1_reopen_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('P1_REOPEN',len(errors),'parent',len(parent_errors),'missing',len(missing),flush=True)


def power():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'p1_power.blend'))
    scene = bpy.context.scene
    names = ['Clutch_FrictionDisc','Gearbox_InputShaft','Gearbox_CounterShaft','PropellerShaft_Spinner',
             'FinalDrive_Mid_Carrier','FinalDrive_Rear_Carrier','Front_R','Mid_R_Outer','Rear_R_Outer']
    rows = []
    for frame in [1,48,72,96,120,144,192]:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        control = bpy.data.objects['PowertrainControl']
        rows.append({'frame':frame,'time':(frame-1)/24,'release':control['clutch_release'],
                     'engineAngle':control['engine_angle'],'clutchAngle':control['clutch_angle'],
                     'objects':{name:list(bpy.data.objects[name].rotation_euler) for name in names},
                     'piston01Z':bpy.data.objects['PistonMotion_01'].location.z})
    off_start = rows[2]
    off_end = rows[3]
    stopped = {}
    for name in names:
        a,b = off_start['objects'][name],off_end['objects'][name]
        stopped[name] = max(abs(x-y) for x,y in zip(a,b)) < .00001
    report = {'source':'Reopened p1_power.blend evaluated animation',
              'frames':rows,'downstreamStoppedFrom72To96':stopped,
              'engineContinuesWhileClutchOpen':off_end['engineAngle'] > off_start['engineAngle'],
              'pistonContinuesWhileClutchOpen':abs(off_end['piston01Z']-off_start['piston01Z']) > .00001,
              'kinematicOnly':True,'combustionOrVehicleDynamicsValidated':False}
    (ROOT/'p1_power_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('P1_POWER',stopped,'engine_continues',report['engineContinuesWhileClutchOpen'],flush=True)


explosion()
power()
