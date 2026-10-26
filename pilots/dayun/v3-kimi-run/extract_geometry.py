from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
source = (ROOT / 'assets' / 'build_engine_frozen.py').read_text(encoding='utf-8')
tree = ast.parse(source)
functions = {
    'group', 'register', 'mesh', 'activate', 'delete', 'boolean', 'bevel', 'box',
    'revolve', 'sector', 'cylinder', 'tube_curve', 'clone_tree', 'metal',
}
header = '''from pathlib import Path
import bpy
import bmesh
import json
import math
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
PI = math.pi
registry = []

'''
parts = [header]
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in functions:
        text = ast.get_source_segment(source, node)
        if node.name == 'revolve':
            text = text.replace("point = (0, 0, axial) if axis == 'Z' else (axial, 0, 0)",
                "point = (0, 0, axial) if axis == 'Z' else ((axial, 0, 0) if axis == 'X' else (0, axial, 0))")
            text = text.replace("point = (radius * math.cos(angle), radius * math.sin(angle), axial) if axis == 'Z' else (axial, radius * math.cos(angle), radius * math.sin(angle))",
                "point = (radius * math.cos(angle), radius * math.sin(angle), axial) if axis == 'Z' else ((axial, radius * math.cos(angle), radius * math.sin(angle)) if axis == 'X' else (radius * math.cos(angle), axial, radius * math.sin(angle)))")
        elif node.name == 'sector':
            text = text.replace("            else:\n                verts.append((radius * math.cos(angle), radius * math.sin(angle), axial))",
                "            elif axis == 'Y':\n                verts.append((radius * math.cos(angle), axial, radius * math.sin(angle)))\n            else:\n                verts.append((radius * math.cos(angle), radius * math.sin(angle), axial))")
        parts.append(text.replace('Generic heavy-duty inline-six structure; not OEM CAD',
                                  'Generic mechanical display structure; not OEM CAD'))
parts.append('''

_original_register = register


def register(obj, family, shape, note='', source='v3-procedural'):
    result = _original_register(obj, family, shape, note)
    obj['source'] = source
    return result


def matrix_values(matrix):
    return [[float(value) for value in row] for row in matrix]


def capture_rest(root):
    bpy.context.view_layer.update()
    for obj in [root, *root.children_recursive]:
        obj['assemblyMatrix'] = matrix_values(obj.matrix_local)
        if 'explodeMatrix' not in obj:
            obj['explodeMatrix'] = matrix_values(obj.matrix_local)


def export_registry(path, root):
    entities = []
    for item in registry:
        obj = bpy.data.objects.get(item['id'])
        if obj is None:
            continue
        entities.append({
            'id': item['id'],
            'family': item['family'],
            'shape': item['shape'],
            'parent': obj.parent.name if obj.parent else None,
            'type': obj.type,
            'source': obj.get('source', 'v3-derived'),
            'assemblyMatrix': matrix_values(obj.get('assemblyMatrix', obj.matrix_local)),
            'explodeMatrix': matrix_values(obj.get('explodeMatrix', obj.get('assemblyMatrix', obj.matrix_local))),
            'note': item['note'],
        })
    report = {
        'scope': 'Physical semantic parts, not decorative mesh fragments; generic internals, no OEM BOM',
        'physicalInstances': len(entities),
        'physicalFamilies': len({entity['family'] for entity in entities}),
        'meshObjects': sum(obj.type == 'MESH' for obj in root.children_recursive),
        'entities': entities,
    }
    Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def mirror_assembly(root):
    mirror = Matrix.Diagonal((-1,1,1))
    root.scale.x = 1
    for obj in root.children_recursive:
        obj.location.x *= -1
        obj.rotation_euler = (mirror @ obj.rotation_euler.to_matrix() @ mirror).to_euler()
        obj.scale.x = 1
        if obj.type == 'MESH':
            obj.data = obj.data.copy()
            for vertex in obj.data.vertices:
                vertex.co.x *= -1
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
            bm.to_mesh(obj.data)
            bm.free()


def frustum(name, loc, radius1, radius2, depth, mat, parent=None, axis=(0,0,1), vertices=24):
    verts = []
    for radius, z in [(radius1, -depth/2), (radius2, depth/2)]:
        for i in range(vertices):
            angle = 2*PI*i/vertices
            verts.append((radius*math.cos(angle), radius*math.sin(angle), z))
    faces = []
    for i in range(vertices):
        j = (i+1) % vertices
        faces.append((i, j, j+vertices, i+vertices))
    faces += [tuple(range(vertices-1, -1, -1)), tuple(range(vertices, 2*vertices))]
    obj = mesh(name, verts, faces, mat, parent)
    obj.location = loc
    obj.rotation_euler = Vector(axis).to_track_quat('Z', 'Y').to_euler()
    return obj
''')
(ROOT / 'geo.py').write_text('\n\n'.join(parts), encoding='utf-8')
print('geo.py generated from the frozen Kimi geometry functions')
