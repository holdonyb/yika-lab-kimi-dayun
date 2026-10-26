from pathlib import Path
import bpy
import json
import time
from mathutils import Vector
from geo import metal

ROOT = Path(__file__).resolve().parent


def palette():
    return {
        'aluminum': metal('V3 cast aluminum',(.48,.54,.60),.39,.82,.16,True),
        'steel': metal('V3 forged steel',(.22,.27,.32),.36,.94,.18,True),
        'machined': metal('V3 machined steel',(.45,.52,.59),.27,.98,.25),
        'bronze': metal('V3 plain bearing bronze',(.56,.30,.115),.30,.86,.18),
        'frame': metal('V3 dark frame',(.028,.039,.052),.43,.74),
        'rubber': metal('V3 tire rubber',(.014,.018,.022),.78,.02),
        'tread': metal('V3 tread rubber',(.022,.027,.031),.81,.01),
        'friction': metal('V3 friction lining',(.085,.072,.058),.72,.05),
        'glass': metal('V3 smoked glazing',(.018,.045,.060),.16,.24,.22),
        'red': metal('V3 red accessories',(.38,.012,.018),.31,.36,.3),
        'amber': metal('V3 amber',(.85,.32,.025),.30,.35),
        'ivory': metal('V3 ivory',(.70,.73,.72),.38,.25),
        'floor': metal('V3 studio charcoal',(.020,.027,.036),.48,.22),
    }


def area(name, location, energy, color, size, target, shape='DISK', size_y=None):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.specular_factor = .35
    data.color = color
    data.shape = shape
    data.size = size
    if shape == 'RECTANGLE' and size_y is not None:
        data.size_y = size_y
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    return obj


def studio(scene, target=(0,0,1), scale=6, floor_z=-.03):
    world = bpy.data.worlds.new('V3 dark studio')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.065,.085,.12,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .22
    scene.world = world
    from geo import box
    mats = palette()
    box('Studio floor', (0,0,floor_z-.015), (200,200,.025), mats['floor'])
    x,y,z = target
    area('V3 key', (x-scale*.35,y-scale*.70,z+scale*1.05), 32*scale*scale,
         (.84,.91,1.0),scale*.72,target)
    area('V3 strip', (x+scale*.15,y+scale*.35,z+scale*.95), 28*scale*scale,
         (.91,.96,1.0),scale*.85,target,'RECTANGLE',scale*.07)
    area('V3 warm rim', (x+scale*.75,y+scale*.40,z+scale*.45), 20*scale*scale,
         (1.0,.64,.34),scale*.50,target,'RECTANGLE',scale*.12)
    area('V3 fill', (x-scale*.75,y-scale*.15,z+scale*.40), 10*scale*scale,
         (.64,.79,1.0),scale*.45,target)
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 48
    scene.eevee.use_raytracing = True
    scene.eevee.ray_tracing_options.resolution_scale = '2'
    scene.eevee.ray_tracing_options.screen_trace_quality = .75
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.45
    scene.render.fps = 24
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 18
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    return mats


def camera(scene, position, target, lens=50, fstop=11):
    if scene.camera is None:
        data = bpy.data.cameras.new('V3 cinema camera')
        obj = bpy.data.objects.new('V3 cinema camera', data)
        bpy.context.collection.objects.link(obj)
        scene.camera = obj
    camera = scene.camera
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.lens = lens
    camera.data.sensor_width = 36
    camera.data.clip_start = .003
    camera.data.clip_end = 200
    focus = bpy.data.objects.get('V3 camera focus')
    if focus is None:
        focus = bpy.data.objects.new('V3 camera focus', None)
        bpy.context.collection.objects.link(focus)
    focus.location = target
    camera.data.dof.focus_object = focus
    camera.data.dof.aperture_fstop = fstop
    camera.data.dof.aperture_blades = 7
    return camera


def render_frame(scene, frame, filename, width=960, height=540, samples=32, blur=False):
    path = ROOT / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.frame_set(frame)
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.eevee.taa_render_samples = samples
    scene.render.use_motion_blur = blur
    scene.render.motion_blur_shutter = .20
    scene.render.filepath = str(path)
    started = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    elapsed = time.perf_counter() - started
    print(f'RENDERED frame={frame} seconds={elapsed:.3f} file={filename}', flush=True)
    return {'frame': frame, 'file': filename, 'seconds': elapsed, 'width': width, 'height': height}


def render_sequence(scene, directory, start, end, width=960, height=540, samples=24, step=1, blur=False):
    records = []
    for index, frame in enumerate(range(start, end+1, step), start=1):
        records.append(render_frame(scene, frame, f'{directory}/frame_{index:04d}.png', width, height, samples, blur))
    (ROOT / f'{directory}_status.json').write_text(json.dumps({
        'asset': Path(bpy.data.filepath).name,
        'frames': records,
    }, indent=2), encoding='utf-8')
    return records
