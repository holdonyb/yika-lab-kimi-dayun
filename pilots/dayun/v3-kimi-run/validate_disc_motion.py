from pathlib import Path
import bpy
import math
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'p2_disc.blend'))
scene = bpy.context.scene
cells = [obj for obj in scene.objects if obj.name.startswith('Gypsum pre-cut cell')]
hull = bpy.data.objects['P2 animated cab contact hull']
links = [obj.rigid_body_constraint for obj in scene.objects if obj.rigid_body_constraint]
initial = {}


def mesh_bvh(obj,depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    data = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ vertex.co for vertex in data.vertices]
    data.calc_loop_triangles()
    faces = [tuple(face.vertices) for face in data.loop_triangles]
    tree = BVHTree.FromPolygons(vertices,faces,all_triangles=True,epsilon=.0001)
    minimum = min(point.z for point in vertices)
    evaluated.to_mesh_clear()
    return tree,minimum


def overlaps(a,b,depsgraph):
    tree_a,_ = mesh_bvh(a,depsgraph)
    tree_b,_ = mesh_bvh(b,depsgraph)
    return bool(tree_a.overlap(tree_b))


scene.frame_set(1)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
for obj in cells:
    initial[obj.name] = {'center':obj.evaluated_get(depsgraph).matrix_world.translation.copy(),
                         'normal':(obj.evaluated_get(depsgraph).matrix_world.to_3x3() @ Vector((0,1,0))).normalized()}
pairs = []
for link in links:
    a,b = link.object1,link.object2
    pairs.append((a,b,(initial[a.name]['center']-initial[b.name]['center']).length))
contact = None
fragmentation = None
pre_max_delta = 0
pre_max_tilt = 0
post_max_delta = 0
ground_min = 100
samples = []
for frame in range(1,193):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    deltas = []
    for a,b,distance in pairs:
        delta = abs((a.evaluated_get(depsgraph).matrix_world.translation-b.evaluated_get(depsgraph).matrix_world.translation).length-distance)
        deltas.append(delta)
    max_delta = max(deltas,default=0)
    tilts = []
    for obj in cells:
        normal = (obj.evaluated_get(depsgraph).matrix_world.to_3x3() @ Vector((0,1,0))).normalized()
        tilts.append(math.degrees(normal.angle(initial[obj.name]['normal'])))
    max_tilt = max(tilts,default=0)
    if contact is None:
        for obj in cells:
            if overlaps(hull,obj,depsgraph):
                contact = frame
                break
    if contact is None:
        pre_max_delta = max(pre_max_delta,max_delta)
        pre_max_tilt = max(pre_max_tilt,max_tilt)
    else:
        post_max_delta = max(post_max_delta,max_delta)
        if fragmentation is None and max_delta > .04:
            fragmentation = frame
    if frame % 4 == 0 or frame in [1,contact,fragmentation,192]:
        minimum = min(mesh_bvh(obj,depsgraph)[1] for obj in cells)
        ground_min = min(ground_min,minimum)
        samples.append({'frame':frame,'contact':contact,'maxLinkCenterDistanceChange':max_delta,
                        'maxCellTiltDegrees':max_tilt,'minimumMeshVertexZ':minimum})
report = {'source':'Evaluated cached geometry in p2_disc.blend, no rendering',
          'cacheBaked':scene.rigidbody_world.point_cache.is_baked,
          'embeddedCache':not scene.rigidbody_world.point_cache.use_disk_cache,
          'geometricContactFrame':contact,'geometricContactSeconds':(contact-1)/24 if contact else None,
          'preContactMaxLinkedCenterDistanceChange':pre_max_delta,
          'preContactMaxCellTiltDegrees':pre_max_tilt,
          'firstFragmentationFrame':fragmentation,
          'postContactMaxLinkedCenterDistanceChange':post_max_delta,
          'minimumEvaluatedMeshVertexZ':ground_min,
          'method':'BVH surface overlap between the actual animated cab collision hull and each cell; linked cell center spacing and normals evaluated every frame',
          'massModel':'Art-directed lightweight prop mass, not measured gypsum density or material strength',
          'samples':samples}
report['preContactStable'] = pre_max_delta < .04 and pre_max_tilt < 12
report['fracturesAfterContact'] = fragmentation is not None and contact is not None and fragmentation >= contact
report['passed'] = bool(report['cacheBaked'] and report['preContactStable'] and report['fracturesAfterContact'])
(ROOT/'p2_disc_physics_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in report.items() if key != 'samples'},indent=2),flush=True)
