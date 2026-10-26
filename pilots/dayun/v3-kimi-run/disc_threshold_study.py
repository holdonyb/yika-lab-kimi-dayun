from pathlib import Path
import sys
import bpy
import json
import math
import hashlib
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
BASE = ROOT/'p2_disc_physics_base.blend'
FPS = 24
END = 192


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def link(a,b,threshold):
    obj = bpy.data.objects.new('Study breakable fixed joint',None)
    bpy.context.collection.objects.link(obj)
    obj.location = (a.location+b.location)/2
    activate(obj)
    bpy.ops.rigidbody.constraint_add()
    constraint = obj.rigid_body_constraint
    constraint.type = 'FIXED'
    constraint.object1 = a
    constraint.object2 = b
    constraint.disable_collisions = True
    constraint.use_breaking = True
    constraint.breaking_threshold = threshold


def cluster_sizes(cells,pairs,depsgraph):
    parent = {obj.name:obj.name for obj in cells}
    def find(name):
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name
    for a,b,initial in pairs:
        distance = (a.evaluated_get(depsgraph).matrix_world.translation-b.evaluated_get(depsgraph).matrix_world.translation).length
        if abs(distance-initial) < .06:
            ra,rb = find(a.name),find(b.name)
            parent[ra] = rb
    sizes = {}
    for obj in cells:
        root = find(obj.name)
        sizes[root] = sizes.get(root,0)+1
    return sorted(sizes.values(),reverse=True)


reports = []
for threshold in ([float(value) for value in sys.argv[sys.argv.index('--')+1:]] if '--' in sys.argv else [.3,1.0,2.0]):
    label = str(threshold).replace('.','_')
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene = bpy.context.scene
    scene.frame_set(1)
    world = scene.rigidbody_world
    cache = world.point_cache
    with bpy.context.temp_override(scene=scene,point_cache=cache):
        bpy.ops.ptcache.free_bake()
    original_links = [(obj.rigid_body_constraint.object1,obj.rigid_body_constraint.object2) for obj in scene.objects if obj.rigid_body_constraint]
    for obj in list(scene.objects):
        if obj.rigid_body_constraint:
            bpy.data.objects.remove(obj,do_unlink=True)
    cells = [obj for obj in scene.objects if obj.name.startswith('Gypsum pre-cut cell')]
    for a,b in original_links:
        link(a,b,threshold)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    centers = {obj.name:obj.evaluated_get(depsgraph).matrix_world.translation.copy() for obj in cells}
    normals = {obj.name:(obj.evaluated_get(depsgraph).matrix_world.to_3x3() @ Vector((0,1,0))).normalized() for obj in cells}
    pairs = [(a,b,(centers[a.name]-centers[b.name]).length) for a,b in original_links]
    samples = []
    pre_max_delta = 0
    pre_max_tilt = 0
    contact = None
    first_fragment = None
    for frame in range(1,END+1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        delta = max(abs((a.evaluated_get(depsgraph).matrix_world.translation-b.evaluated_get(depsgraph).matrix_world.translation).length-initial)
                    for a,b,initial in pairs)
        tilt = max(math.degrees(((obj.evaluated_get(depsgraph).matrix_world.to_3x3() @ Vector((0,1,0))).normalized()).angle(normals[obj.name])) for obj in cells)
        front = (bpy.data.objects['TruckAssembly'].matrix_world @ Vector((0,-3.76,1.5))).y
        if contact is None and front <= -6.38+.003:
            contact = frame
        if first_fragment is None and delta > .04:
            first_fragment = frame
        if contact is None:
            pre_max_delta = max(pre_max_delta,delta)
            pre_max_tilt = max(pre_max_tilt,tilt)
        if frame in [1,24,48,56,64,72,96,144,192]:
            sizes = cluster_sizes(cells,pairs,depsgraph)
            minimum = 100
            for obj in cells:
                evaluated = obj.evaluated_get(depsgraph)
                data = evaluated.to_mesh()
                minimum = min(minimum,min((evaluated.matrix_world @ vertex.co).z for vertex in data.vertices))
                evaluated.to_mesh_clear()
            samples.append({'frame':frame,'maxLinkDistanceChange':delta,'maxTiltDegrees':tilt,
                            'approximateClusterSizes':sizes,'minimumMeshVertexZ':minimum,
                            'objects':{obj.name:list(obj.evaluated_get(depsgraph).matrix_world.translation) for obj in cells}})
    with bpy.context.temp_override(scene=scene,point_cache=cache):
        bpy.ops.ptcache.bake_from_cache()
    asset = ROOT/f'p2_disc_study_t{label}.blend'
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(asset))
    final = samples[-1]
    stable = pre_max_delta < .04 and pre_max_tilt < 12 and (first_fragment is None or contact is None or first_fragment >= contact-2)
    majority = final['approximateClusterSizes'][0] <= 9
    report = {'threshold':threshold,'asset':asset.name,'sourceSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
              'cacheBaked':cache.is_baked,'proxyContactEstimate':contact,'firstFragmentationFrame':first_fragment,
              'preContactMaxDistanceChange':pre_max_delta,'preContactMaxTiltDegrees':pre_max_tilt,
              'stableBeforeContact':stable,'majoritySeparatedAtEnd':majority,
              'clusterMethod':'Approximate connectivity from linked center spacing, not a direct Bullet broken-flag count',
              'samples':samples}
    (ROOT/f'p2_disc_study_t{label}_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    reports.append(report)
    print('STUDY_RESULT',threshold,'stable',stable,'majority',majority,'firstFragment',first_fragment,'clusters',final['approximateClusterSizes'],flush=True)
(ROOT/'p2_disc_threshold_study.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print('THRESHOLD_STUDY_COMPLETE',flush=True)
