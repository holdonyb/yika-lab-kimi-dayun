from pathlib import Path
import bpy
import json
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
scene = bpy.context.scene
scene.frame_set(73)
bpy.context.view_layer.update()


def tree(name, depsgraph):
    obj = bpy.data.objects[name].evaluated_get(depsgraph)
    data = obj.to_mesh()
    data.calc_loop_triangles()
    vertices = [obj.matrix_world @ vertex.co for vertex in data.vertices]
    faces = [tuple(triangle.vertices) for triangle in data.loop_triangles]
    result = BVHTree.FromPolygons(vertices, faces, all_triangles=True, epsilon=0.0000001)
    obj.to_mesh_clear()
    return result


def counts():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return {
        'upperBearingVsRod': len(tree('RodBearingUpper_01', depsgraph).overlap(tree('Rod big upper half', depsgraph))),
        'capVsCrank': len(tree('Rod cap lower half', depsgraph).overlap(tree('Crankshaft_Forging', depsgraph))),
    }


report = {'withBevel': counts()}
for name in ['RodBearingUpper_01', 'Rod big upper half', 'Rod cap lower half']:
    obj = bpy.data.objects[name]
    for modifier in list(obj.modifiers):
        if modifier.type == 'BEVEL':
            obj.modifiers.remove(modifier)
bpy.context.view_layer.update()
report['withoutBevel'] = counts()
(ROOT / 'bearing_fit_probe.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
