from pathlib import Path
import bpy
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parent
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def option(name, default=None):
    if name not in args:
        return default
    index = args.index(name)
    return args[index + 1] if index + 1 < len(args) else True


mode = option('--mode', 'stills')
asset = option('--asset')
if asset:
    bpy.ops.wm.open_mainfile(filepath=str((ROOT / asset).resolve()))
scene = bpy.context.scene
scene.render.engine = option('--engine', 'BLENDER_EEVEE')
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.compression = 15
scene.render.resolution_percentage = 100
scene.render.use_file_extension = True
scene.render.fps = 24
if option('--specular') is not None:
    for light in bpy.data.lights:
        light.specular_factor = float(option('--specular'))
if option('--exposure') is not None:
    scene.view_settings.exposure = float(option('--exposure'))
if hasattr(scene.render, 'use_motion_blur'):
    scene.render.use_motion_blur = mode == 'final'
    scene.render.motion_blur_shutter = .20
source_hash = hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
records = []


def render(frame, filename, width, height, samples):
    path = ROOT / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.frame_set(frame)
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.eevee.taa_render_samples = samples
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = .025
    scene.render.filepath = str(path)
    started = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    elapsed = time.perf_counter() - started
    records.append({'frame': frame, 'file': filename, 'seconds': elapsed,
                    'width': width, 'height': height, 'samples': samples})
    (ROOT / f'{path.parent.name}_render_status.json').write_text(json.dumps({
        'asset': Path(bpy.data.filepath).name,
        'assetSha256': source_hash,
        'mode': mode,
        'frames': records,
    }, indent=2), encoding='utf-8')
    print(f'RENDERED frame={frame} seconds={elapsed:.3f} file={filename}', flush=True)


if mode == 'single':
    frame = int(option('--frame', 1))
    name = option('--name', f'check_frame_{frame:04d}.png')
    render(frame, name, int(option('--width', 960)), int(option('--height', 540)), int(option('--samples', 24)))
elif mode == 'stills':
    width = int(option('--width', 1920))
    height = int(option('--height', 1080))
    samples = int(option('--samples', 64))
    prefix = option('--prefix', '')
    for frame, name in [(1, '01_assembled.png'), (174, '02_first_cylinder_exploded.png'), (290, '03_six_cylinder_working.png')]:
        render(frame, prefix + name, width, height, samples)
elif mode in ['preview', 'final']:
    preview = mode == 'preview'
    width = int(option('--width', 960 if preview else 1920))
    height = int(option('--height', 540 if preview else 1080))
    samples = int(option('--samples', 16 if preview else 64))
    step = 3 if preview else 1
    directory = option('--directory', 'preview_frames' if preview else 'frames')
    start = int(option('--start', 1))
    end = int(option('--end', 360))
    resume = '--resume' in args
    for index, frame in enumerate(range(start, end + 1, step), start=1):
        filename = f'{directory}/frame_{index:04d}.png'
        if resume and (ROOT / filename).is_file() and (ROOT / filename).stat().st_size > 1000:
            print(f'RESUME_SKIP frame={frame} file={filename}', flush=True)
            continue
        render(frame, filename, width, height, samples)
else:
    raise ValueError(f'Unknown render mode: {mode}')
print('RENDER_BATCH_COMPLETE', mode, len(records), flush=True)
