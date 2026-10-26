from pathlib import Path
import bpy
import json
import math
import hashlib
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
source = ROOT/'p2_disc.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
cells = [obj for obj in scene.objects if obj.name.startswith('Gypsum pre-cut cell')]
links = [obj.rigid_body_constraint for obj in scene.objects if obj.rigid_body_constraint]
scene.frame_set(1)
depsgraph = bpy.context.evaluated_depsgraph_get()
centers = {obj.name:obj.evaluated_get(depsgraph).matrix_world.translation.copy() for obj in cells}
normals = {obj.name:(obj.evaluated_get(depsgraph).matrix_world.to_3x3() @ Vector((0,1,0))).normalized() for obj in cells}
pairs = [(link.object1,link.object2,(centers[link.object1.name]-centers[link.object2.name]).length) for link in links]
rows = []
first_fragmentation = None
for frame in range(1,193):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    delta = max(abs((a.evaluated_get(depsgraph).matrix_world.translation-b.evaluated_get(depsgraph).matrix_world.translation).length-distance)
                for a,b,distance in pairs)
    tilt = max(math.degrees(((obj.evaluated_get(depsgraph).matrix_world.to_3x3() @ Vector((0,1,0))).normalized()).angle(normals[obj.name])) for obj in cells)
    if first_fragmentation is None and delta > .04:
        first_fragmentation = frame
    if frame in [1,48,64,96,144,192]:
        minimum = 100
        for obj in cells:
            evaluated = obj.evaluated_get(depsgraph)
            data = evaluated.to_mesh()
            minimum = min(minimum,min((evaluated.matrix_world @ vertex.co).z for vertex in data.vertices))
            evaluated.to_mesh_clear()
        rows.append({'frame':frame,'maxLinkedCenterDistanceChange':delta,'maxCellTiltDegrees':tilt,'minimumActualMeshVertexZ':minimum})
thresholds = sorted({link.breaking_threshold for link in links})
report = {'asset':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'cacheBaked':scene.rigidbody_world.point_cache.is_baked,'embeddedCache':not scene.rigidbody_world.point_cache.use_disk_cache,
          'constraintThresholds':thresholds,'firstFragmentationFrame':first_fragmentation,'frames':rows,
          'impactProfile':scene.get('discImpactProfile','standard 1.53m/s approach'),
          'stableAt48':rows[1]['maxLinkedCenterDistanceChange'] < .04 and rows[1]['maxCellTiltDegrees'] < 12,
          'fragmentedBy96':next(row for row in rows if row['frame'] == 96)['maxLinkedCenterDistanceChange'] > .08,
          'fragmentedByEnd':rows[-1]['maxLinkedCenterDistanceChange'] > .08,
          'method':'Actual cached mesh vertices and linked cell centers, evaluated without rendering; Bullet margin means surface overlap is not used as a contact-time oracle',
          'massModel':'Art-directed lightweight prop mass, not real gypsum material density or strength',
          'visualReviewRequired':'Inspect the four key frames and final rendered frame before freezing'}
(ROOT/'p2_disc_frame_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
