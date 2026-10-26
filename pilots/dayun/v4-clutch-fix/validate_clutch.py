from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import json
from clutch_phases import timeline

ROOT = Path(__file__).resolve().parent


def evaluated(scene,name):
    return bpy.data.objects[name].evaluated_get(bpy.context.evaluated_depsgraph_get())


def bounds(root,name):
    obj = evaluated(scene,name)
    data = obj.to_mesh()
    inverse = root.matrix_world.inverted()
    ys = [(inverse @ obj.matrix_world @ vertex.co).y for vertex in data.vertices]
    obj.to_mesh_clear()
    return [min(ys),max(ys)]


def tip_y(root,index):
    obj = evaluated(scene,f'DiaphragmFinger_{index:02d}')
    data = obj.to_mesh()
    inverse = root.matrix_world.inverted()
    y = sum((inverse @ obj.matrix_world @ data.vertices[i].co).y for i in [0,1,14,15])/4
    obj.to_mesh_clear()
    return y


def tip_radius(root,index):
    obj = evaluated(scene,f'DiaphragmFinger_{index:02d}')
    data = obj.to_mesh()
    inverse = root.matrix_world.inverted()
    radius = sum(math_hypot(inverse @ obj.matrix_world @ data.vertices[i].co) for i in [0,1,14,15])/4
    obj.to_mesh_clear()
    return radius


def math_hypot(point):
    return (point.x**2+point.z**2)**.5


def bearing_radii(root):
    obj = evaluated(scene,'Clutch_ReleaseContactRace')
    data = obj.to_mesh()
    inverse = root.matrix_world.inverted()
    radii = [math_hypot(inverse @ obj.matrix_world @ vertex.co) for vertex in data.vertices]
    obj.to_mesh_clear()
    return [min(radii),max(radii)]


def inspect(scene,root_name,full):
    root = bpy.data.objects[root_name]
    control = bpy.data.objects['PowertrainControl']
    rows = []
    errors = []
    previous_driven = None
    for expected in timeline():
        frame = expected['frame']
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        disc = bounds(root,'Clutch_FrictionDisc')
        pressure = bounds(root,'Clutch_PressurePlate')
        flywheel = bounds(root,'Clutch_FlywheelFrictionFace')
        front_gap = pressure[0]-disc[1]
        back_gap = disc[0]-flywheel[1]
        lift = evaluated(scene,'Clutch_PressurePlateLift').location.y
        disc_float = evaluated(scene,'Clutch_DiscSplineFloat').location.y
        bearing_range = bounds(root,'Clutch_ReleaseContactRace')
        bearing_front = bearing_range[0]
        bearing_center = sum(bearing_range)/2
        race_radii = bearing_radii(root)
        finger_tip = tip_y(root,1)
        finger_top = finger_tip+.0013
        finger_radius = tip_radius(root,1)
        active_angle = evaluated(scene,'Clutch_ActiveRotation').rotation_euler.y
        driven_angle = evaluated(scene,'Clutch_InputRotation').rotation_euler.y
        checks = {
            'pressureGapMatchesMesh':abs(front_gap-expected['pressureGap']) < .000002,
            'flywheelGapMatchesMesh':abs(back_gap-expected['flywheelGap']) < .000002,
            'noFrictionFacePenetration':front_gap >= -.000002 and back_gap >= -.000002,
            'pressureLiftMatchesMesh':abs(lift-expected['pressureLift']) < .000002,
            'discFloatMatchesMesh':abs(disc_float-expected['discFloat']) < .000002,
            'activeFollowsEngine':abs(active_angle-expected['engine_angle']) < .00001,
            'drivenFollowsInput':abs(driven_angle-expected['clutch_angle']) < .00001,
            'fingerDeflectionMatchesMesh':abs(finger_tip-(.0687-expected['fingerDeflection'])) < .000002,
            'bearingRetainsAssemblyOffset':abs(bearing_center-(.085-expected['bearingTravel'])) < .000002,
            'bearingCoversSpringTipRadius':race_radii[0] <= finger_radius <= race_radii[1],
            'bearingDoesNotPassFingertips':bearing_front-finger_top >= -.000002,
            'bearingGapMatchesContactSequence':abs((bearing_front-finger_top)-expected['bearingFingerGap']) < .000002,
            'noAccelerationBeforeContact':expected['phase'] != 'reengaging' or (expected['drivenSpeed'] == 0 and previous_driven is not None and abs(driven_angle-previous_driven) < .00001),
        }
        if full:
            checks.update({
                'gearboxInputFollowsDisc':abs(evaluated(scene,'Gearbox_InputShaft').rotation_euler.y-expected['clutch_angle']) < .00001,
                'propellerFollowsInput':abs(evaluated(scene,'PropellerShaft_Spinner').rotation_euler.y-expected['clutch_angle']) < .00001,
                'wheelFollowsFinalDrive':abs(evaluated(scene,'Front_R').rotation_euler.x-expected['wheel_angle']) < .00001,
                'crankContinuesWithEngine':abs(evaluated(scene,'CrankshaftRotation').rotation_euler.x-expected['engine_angle']) < .00001,
            })
        for name,value in checks.items():
            if not value:
                errors.append({'frame':frame,'check':name})
        rows.append({'frame':frame,'phase':expected['phase'],'controls':{name:control[name] for name in ['engine_angle','clutch_angle','clutch_release']},
                     'mesh':{'pressureFrontGap':front_gap,'flywheelBackGap':back_gap,'pressureLift':lift,
                             'discSplineFloat':disc_float,'releaseBearingFrontY':bearing_front,
                             'releaseBearingCenterY':bearing_center,'releaseRaceRadii':race_radii,
                             'diaphragmInnerTipY':finger_tip,'fingerContactSurfaceY':finger_top,
                             'fingerTipRadius':finger_radius,'bearingFingerClearance':bearing_front-finger_top},
                     'actualAngles':{'activeY':active_angle,'drivenY':driven_angle},
                     'checks':checks})
        previous_driven = driven_angle
    return rows,errors


reports = {}
for filename,root_name,full in [('clutch_mechanism.blend','Clutch',False),('clutch_powertrain.blend','Clutch',True)]:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/filename))
    scene = bpy.context.scene
    rows,errors = inspect(scene,root_name,full)
    reports[filename] = {'source':filename,'evaluatedFrames':len(rows),'errors':errors,'passed':not errors,'frames':rows}
    print('CLUTCH_VALIDATION',filename,'passed',not errors,'errors',errors[:10],flush=True)
(ROOT/'clutch_validation.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
if any(not report['passed'] for report in reports.values()):
    raise RuntimeError('Clutch geometry or driver validation failed; see clutch_validation.json')
