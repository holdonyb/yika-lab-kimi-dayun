"""Execute frozen Kimi sources; photograph actual intermediate scene states."""
from pathlib import Path
import bpy, sys, hashlib, json, shutil, time, math
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
PILOTS=ROOT.parents[2]
SOURCES=PILOTS/'dayun'
MODE=sys.argv[sys.argv.index('--')+1]
SOURCE=SOURCES/('kimi-run/build_truck.py' if MODE=='truck' else 'v2-kimi-run/build_engine.py')
FROZEN=ROOT/'frozen_sources'/MODE/SOURCE.name
FROZEN.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(SOURCE,FROZEN)
OUT=ROOT/'observed'/MODE
OUT.mkdir(parents=True,exist_ok=True)
before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
start=time.monotonic()
entries=[]
stages=(
 {269:'驾驶室骨架',278:'驾驶室外壳',285:'风挡与车顶',312:'车侧结构',337:'格栅细节',357:'车灯与保险杠',385:'车门与后视镜',396:'驾驶室内饰',421:'底盘与鞍座',431:'油箱与电池箱',448:'车桥与悬挂',465:'初版发动机',528:'轮组生成完毕'}
 if MODE=='truck' else
 {568:'活塞：销孔与环槽',574:'压缩环与组合油环',583:'活塞销与卡簧',593:'连杆本体',597:'小头衬套',621:'轴瓦、连杆盖与螺栓',645:'扩展为六缸',689:'六缸缸套',729:'连续曲轴',755:'飞轮与齿圈',794:'主轴瓦与曲轴箱框架'}
)
seen=set()
STOP=529 if MODE=='truck' else 795

def photo(line, label, namespace):
    scene=bpy.context.scene
    bpy.context.view_layer.update()
    original=[o for o in scene.objects if o.type in ('MESH','CURVE','FONT')]
    meshes=[o for o in original if o.type=='MESH']
    camera_data=bpy.data.cameras.new('ObserverCamera')
    camera=bpy.data.objects.new('ObserverCamera',camera_data)
    scene.collection.objects.link(camera)
    if MODE=='truck':
        camera.location=(10,-13,8.3)
        target=Vector((0,0,1.7));camera_data.ortho_scale=10.1
    elif line<645:
        points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
        lo=Vector(tuple(min(p[k] for p in points) for k in range(3)))
        hi=Vector(tuple(max(p[k] for p in points) for k in range(3)))
        target=(lo+hi)/2
        camera.location=target+Vector((-.40,-.65,.36))
        camera_data.ortho_scale=max(.45,(hi.z-lo.z)*2.35,(hi.x-lo.x)*2.5)
    else:
        camera.location=(-.94,-1.75,.95)
        target=Vector((0,0,.17));camera_data.ortho_scale=1.55
    camera_data.type='ORTHO'
    camera_data.clip_start=.001
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    old_camera=scene.camera;scene.camera=camera
    scene.render.engine='BLENDER_WORKBENCH'
    scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGBA'
    scene.render.film_transparent=True
    sh=scene.display.shading
    sh.light='STUDIO';sh.studiolight_rotate_z=.4
    sh.color_type='SINGLE';sh.single_color=(.58,.64,.72)
    sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH'
    sh.curvature_ridge_factor=1.15;sh.curvature_valley_factor=.8
    sh.cavity_ridge_factor=1.2;sh.cavity_valley_factor=1.2
    sh.show_specular_highlight=True
    scene.display.render_aa='16'
    scene.view_settings.view_transform='Standard'
    scene.render.filepath=str(OUT/f'{len(entries):02d}_{line}.png')
    bpy.ops.render.render(write_still=True)
    record={'index':len(entries),'line_next':line,'label':label,'file':scene.render.filepath,
            'mesh_objects':len(meshes),'vertices':sum(len(o.data.vertices) for o in meshes),
            'faces':sum(len(o.data.polygons) for o in meshes),
            'objects':[o.name for o in meshes], 'elapsed_with_observer_seconds':time.monotonic()-start,
            'camera':{'position':list(camera.location),'target':list(target),'ortho_scale':camera_data.ortho_scale},
            'mode':'actual source execution observed before listed line; presentation camera and solid shading only'}
    entries.append(record)
    (OUT/'observations.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf8')
    scene.camera=old_camera
    bpy.data.objects.remove(camera,do_unlink=True)
    bpy.data.cameras.remove(camera_data)
    print('OBSERVED',MODE,line,label,len(meshes),flush=True)

class ObservationComplete(Exception):pass
def trace(frame,event,arg):
    if event=='line' and frame.f_code.co_filename==str(FROZEN) and frame.f_code.co_name=='<module>':
        line=frame.f_lineno
        if line in stages and line not in seen:
            seen.add(line);photo(line,stages[line],frame.f_globals)
        if line>=STOP:raise ObservationComplete()
    return trace

namespace={'__file__':str(FROZEN),'__name__':'__main__'}
sys.settrace(trace)
try:
    exec(compile(FROZEN.read_text(encoding='utf8'),str(FROZEN),'exec'),namespace)
except ObservationComplete:pass
finally:sys.settrace(None)
after=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
receipt={'source':str(SOURCE),'source_sha256_before':before,'source_sha256_after':after,
         'frozen_copy':str(FROZEN),'frozen_sha256':hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
         'mode':MODE,'captured_stages':len(entries),'stop_before_line':STOP,
         'source_unchanged':before==after,'geometry_edited_by_observer':False,
         'observer':'external sys.settrace photographer; source copied verbatim; scene observed at actual execution checkpoints',
         'elapsed_seconds_including_photography':time.monotonic()-start}
(OUT/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(receipt,ensure_ascii=False),flush=True)
