from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import json
import hashlib
from clutch_geometry import build_clutch
from clutch_phases import timeline, phase_report
from geo import group
from studio import studio, camera, area, render_frame, render_sequence

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'v3-kimi-run'/'p1_power.blend'
ARGS = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
MODE = ARGS[0] if ARGS else 'stills'
DRAFT = MODE != 'final'
(ROOT/'clutch_phase.json').write_text(json.dumps(phase_report(),indent=2),encoding='utf-8')


def animate(control,clutch):
    control['source'] = 'v4-clutch-fix'
    for row in timeline():
        frame = row['frame']
        for name in ['engine_angle','clutch_angle','wheel_angle','clutch_release']:
            control[name] = row[name]
            control.keyframe_insert(data_path='["'+name+'"]',frame=frame)
        control['clutch_engaged'] = 1-row['clutch_release']
        control.keyframe_insert(data_path='["clutch_engaged"]',frame=frame)
        clutch['pressureLift'].location.y = row['pressureLift']
        clutch['pressureLift'].keyframe_insert('location',index=1,frame=frame)
        clutch['discLift'].location.y = row['discFloat']
        clutch['discLift'].keyframe_insert('location',index=1,frame=frame)
        for name in ['releaseContact','releaseCarrier','releaseInnerRace']:
            clutch[name].location.y = .085-row['bearingTravel']
            clutch[name].keyframe_insert('location',index=1,frame=frame)


def configure(scene):
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 192
    scene['phaseFile'] = 'clutch_phase.json'
    scene['mechanismScope'] = 'Generic single dry clutch; not OEM dimensions or a torque/contact dynamics simulation'
    scene['teachingSection'] = 'Cover, flywheel and pressure plate have a geometric inspection cutaway; the friction disc is complete'
    scene['axialDisplayScale'] = 4.0
    scene.frame_set(1)


def object_table(scene,root):
    inverse = root.matrix_world.inverted()
    objects = []
    for obj in [root,*root.children_recursive]:
        objects.append({'id':obj.name,'type':obj.type,'parent':obj.parent.name if obj.parent else None,
                        'family':obj.get('part_family',''),'source':obj.get('source','v4-clutch-fix'),
                        'localMatrix':[list(row) for row in obj.matrix_local],
                        'worldMatrix':[list(row) for row in obj.matrix_world]})
    return objects


def teaching():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    configure(scene)
    control = group('PowertrainControl')
    clutch = build_clutch(None,control,'Clutch',(0,0,0),True)
    animate(control,clutch)
    studio(scene,(0,.02,0),.60,-.21)
    camera(scene,(.76,-.22,.16),(0,.012,0),44,16)
    scene.camera.data.dof.use_dof = False
    area('Clutch face fill',(.25,-.35,.38),7,(.84,.92,1.0),.30,(0,.02,0))
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .28
    scene.view_settings.exposure = -.25
    scene.frame_set(1)
    bpy.context.view_layer.update()
    (ROOT/'clutch_objects.json').write_text(json.dumps(object_table(scene,clutch['root']),indent=2),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'clutch_mechanism.blend'))
    if MODE == 'build':
        return
    if MODE == 'stills':
        for frame,name in [(25,'clutch_engaged'),(85,'clutch_disengaged'),(145,'clutch_reengaged')]:
            render_frame(scene,frame,name+'.png',960,540,40)
    else:
        render_sequence(scene,'draft_clutch_close_frames' if DRAFT else 'clutch_close_frames',1,192,
                        960 if DRAFT else 1920,540 if DRAFT else 1080,24 if DRAFT else 64,3 if DRAFT else 1,not DRAFT)


def powertrain():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    configure(scene)
    old = bpy.data.objects['Clutch']
    for obj in list(old.children_recursive):
        bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.objects.remove(old,do_unlink=True)
    base = bpy.data.objects['Dayun_N8E_6x4']
    control = bpy.data.objects['PowertrainControl']
    control.animation_data_clear()
    clutch = build_clutch(base,control,'Clutch',(0,-1.15,1.02),True)
    animate(control,clutch)
    camera(scene,(4.2,-4.5,3.2),(0,-.65,1.05),53,16)
    scene['sourceAsset'] = 'Read-only v3 p1_power.blend; only the clutch and its drive timing replaced'
    scene['sourceSha256'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    scene.frame_set(1)
    bpy.context.view_layer.update()
    (ROOT/'clutch_power_objects.json').write_text(json.dumps(object_table(scene,clutch['root']),indent=2),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'clutch_powertrain.blend'))
    if MODE == 'build':
        return
    if MODE == 'stills':
        for frame,name in [(25,'clutch_power_engaged'),(85,'clutch_power_disengaged'),(145,'clutch_power_reengaged')]:
            render_frame(scene,frame,name+'.png',960,540,32)
    else:
        render_sequence(scene,'draft_clutch_power_frames' if DRAFT else 'clutch_power_frames',1,192,
                        960 if DRAFT else 1920,540 if DRAFT else 1080,24 if DRAFT else 64,3 if DRAFT else 1,not DRAFT)


teaching()
powertrain()
print('CLUTCH_BUILD_COMPLETE',MODE,flush=True)
