from pathlib import Path
import bpy
import json
import math
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
scene = bpy.context.scene
pairs = [
    ('CompressionRing1_01','CylinderLiner_01_PhotoSection'),
    ('CompressionRing2_01','CylinderLiner_01_PhotoSection'),
    ('OilRing_01','CylinderLiner_01_PhotoSection'),
    ('CompressionRing1_01','Piston_01'),
    ('CompressionRing2_01','Piston_01'),
    ('OilRing_01','Piston_01'),
    ('RodBearingLower_01','Crankshaft_Forging'),
    ('RodBearingUpper_01','Crankshaft_Forging'),
    ('RodBearingUpper_01','Rod big upper half'),
    ('Rod big upper half','Crankshaft_Forging'),
    ('Rod cap lower half','Crankshaft_Forging'),
]
frames = sorted(set(range(73,241,3)) | set(range(95,143)) | {90,94,100,101,102,121,123,126,128,174,212,213,214})
critical_frames = {90,94,100,101,102,121,123,126,128,174,212,213,214}
issues = []
critical = []


def geometry(root, depsgraph):
    objects = [root] if root.type == 'MESH' else [obj for obj in root.children_recursive if obj.type == 'MESH']
    vertices = []
    polygons = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        data = evaluated.to_mesh()
        data.calc_loop_triangles()
        offset = len(vertices)
        vertices.extend(evaluated.matrix_world @ vertex.co for vertex in data.vertices)
        polygons.extend(tuple(offset + index for index in triangle.vertices) for triangle in data.loop_triangles)
        evaluated.to_mesh_clear()
    centers = [[sum(vertices[index][axis] for index in polygon)/len(polygon) for axis in range(3)] for polygon in polygons]
    return BVHTree.FromPolygons(vertices,polygons,all_triangles=True,epsilon=0.0000001),centers


def min_radius(name,depsgraph):
    root = bpy.data.objects[name]
    objects = [root] if root.type == 'MESH' else [obj for obj in root.children_recursive if obj.type == 'MESH']
    radius = float('inf')
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        data = evaluated.to_mesh()
        if data.vertices:
            radius = min(radius,min(math.hypot(vertex.co.x,vertex.co.y) for vertex in data.vertices))
        evaluated.to_mesh_clear()
    return radius


for frame in frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cache = {}
    def tree(name):
        if name not in cache:
            cache[name] = geometry(bpy.data.objects[name],depsgraph)
        return cache[name]
    for first,second in pairs:
        a,ca = tree(first)
        b,cb = tree(second)
        overlaps = a.overlap(b)
        if overlaps:
            item = {'frame':frame,'timeSeconds':(frame-1)/24,'pair':[first,second],
                    'triangleOverlaps':len(overlaps),
                    'examples':[{'firstCenterM':ca[i],'secondCenterM':cb[j]} for i,j in overlaps[:4]]}
            issues.append(item)
            if frame in critical_frames:
                critical.append(item)

ring_opening = []
for frame in [130,136,142,174]:
    scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for name in ['CompressionRing1_01','CompressionRing2_01','OilRing_01']:
        radius = min_radius(name,depsgraph)
        ring_opening.append({'frame':frame,'part':name,'evaluatedMinimumInnerRadiusM':radius,
                             'pistonLandRadiusM':.06265,'clearanceM':radius-.06265})
        expected_open = ((name == 'CompressionRing1_01' and frame in [130,174]) or
                         (name == 'CompressionRing2_01' and frame in [136,174]) or
                         (name == 'OilRing_01' and frame in [142,174]))
        if expected_open and radius <= .06265:
            issues.append({'frame':frame,'part':name,'problem':'Expanded ring still crosses the piston land radial envelope'})

liner_positions = []
for frame in [1,73,82,90,94,174,241]:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    first = bpy.data.objects['CylinderLiner_01']
    liner_positions.append({'frame':frame,'firstLinerLocalM':list(first.location),
        'otherLinerLocalM':{f'CylinderLiner_{i:02d}':list(bpy.data.objects[f'CylinderLiner_{i:02d}'].location) for i in range(2,7)}})
    for i in range(2,7):
        actual = bpy.data.objects[f'CylinderLiner_{i:02d}'].location
        error = (actual - __import__('mathutils').Vector(((i-3.5)*.165,0,0))).length
        if error > .000001:
            issues.append({'frame':frame,'part':f'CylinderLiner_{i:02d}','problem':'Another liner was moved by the first-liner path','errorM':error})
for frame in [90,94,174]:
    scene.frame_set(frame)
    actual = bpy.data.objects['CylinderLiner_01'].location
    if (actual - __import__('mathutils').Vector((-.4125,.360,.300))).length > .000001:
        issues.append({'frame':frame,'part':'CylinderLiner_01','problem':'First liner did not complete its lift and side clearance','actual':list(actual)})

scene.frame_set(241)
bpy.context.view_layer.update()
baseline = {
    'CompressionRing1_01':[0,0,0], 'CompressionRing2_01':[0,0,0], 'OilRing_01':[0,0,0],
    'PistonBodyCarrier_01':[0,0,0], 'PistonPin_01':[0,0,0],
    'PistonCirclipL_01':[-.058,0,0], 'PistonCirclipR_01':[.058,0,0],
    'RodCapBolt_01_A':[0,-.042,0], 'RodCapBolt_01_B':[0,.042,0],
    'RodCapCarrier_01':[0,0,0], 'RodBearingUpper_01':[0,0,0], 'RodBearingLower_01':[0,0,0],
    'SmallEndBush_01':[0,0,.235], 'FirstCylinderAssemblyLift':[0,0,0],
    'FirstDetachedRodParts':[-.4125,0,.083], 'CylinderLiner_01':[-.4125,0,0],
}
reset_errors = []
for name,expected in baseline.items():
    obj = bpy.data.objects[name]
    error = (obj.location - __import__('mathutils').Vector(expected)).length
    if error > 0.000001:
        reset_errors.append({'part':name,'errorM':error,'actual':list(obj.location),'expected':expected})
shape_reset = {}
for name in ['CompressionRing1_01','CompressionRing2_01','OilLowerRail_01']:
    obj = bpy.data.objects[name]
    shape_reset[name] = obj.data.shape_keys.key_blocks['ElasticOpening'].value if obj.data.shape_keys else None
    if shape_reset[name] is None or abs(shape_reset[name]) > 0.000001:
        reset_errors.append({'part':name,'problem':'Ring shape did not return to its assembled profile','value':shape_reset[name]})
report = {
    'scope':'Evaluated-mesh inspection of the actual disassembly paths. Render visibility is ignored; the full crankshaft remains in collision checks.',
    'inspectedPairs':pairs,
    'inspectedFrameRange':[73,240],
    'explicitFrames':sorted(critical_frames),
    'criticalIssues':critical,
    'issues':issues,
    'ringRadialClearance':ring_opening,
    'linerPositions':liner_positions,
    'resetErrors':reset_errors,
    'shapeReset':shape_reset,
    'result':'clear' if not issues and not reset_errors else 'issues_found',
    'photographyNote':'At frame 241 the separate liner-bank lift of 0.220 m is a declared photographic state, not an assembly offset.',
    'limitations':'Discrete sampled-frame inspection, not manufacturing tolerances, material deformation, dynamics, or a continuous collision proof.',
}
(ROOT/'verification_paths.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'result':report['result'],'issueCount':len(issues),'resetErrors':reset_errors,
                  'criticalIssues':critical,'ringRadialClearance':ring_opening},ensure_ascii=False,indent=2))
if issues or reset_errors:
    raise SystemExit(1)
