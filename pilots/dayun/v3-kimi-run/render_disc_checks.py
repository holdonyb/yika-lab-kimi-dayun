from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import hashlib
import json
from studio import render_frame

ROOT = Path(__file__).resolve().parent
source = ROOT/'p2_disc.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
thresholds = sorted({obj.rigid_body_constraint.breaking_threshold for obj in scene.objects if obj.rigid_body_constraint})
tag = f'{thresholds[0]:g}' if len(thresholds) == 1 else f'{thresholds[0]:g}-{thresholds[-1]:g}_graded'
if scene.get('discImpactProfile'):
    tag += '_impact5_5'
records = [render_frame(scene,frame,f'p2_disc_t{tag}_f{frame:04d}.png',960,540,16,False)
           for frame in [1,48,64,96,192]]
(ROOT/f'p2_disc_t{tag}_checks.json').write_text(json.dumps({
    'asset':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'cacheBaked':scene.rigidbody_world.point_cache.is_baked,
    'frames':records,'scope':'Requested physics review stills and end state, no P2 video render'
},indent=2),encoding='utf-8')
