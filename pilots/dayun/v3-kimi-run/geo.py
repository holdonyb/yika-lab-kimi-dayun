from pathlib import Path
import bpy
import bmesh
import json
import math
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
PI = math.pi
registry = []



def metal(name, color, roughness, metallic=1.0, anisotropy=0.0, micro=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    shader = nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    if 'Anisotropic IOR Level' in shader.inputs:
        shader.inputs['Anisotropic IOR Level'].default_value = anisotropy
    if micro:
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 1150
        noise.inputs['Detail'].default_value = 2
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.10
        bump.inputs['Distance'].default_value = 0.000025
        mat.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
        mat.node_tree.links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return mat

def group(name, parent=None, loc=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.empty_display_size = .012
    obj.parent = parent
    obj.location = loc
    return obj

def register(obj, family, shape, note=''):
    obj['part_family'] = family
    obj['semantic_id'] = obj.name
    obj['structure'] = shape
    obj['reference_scope'] = 'Generic mechanical display structure; not OEM CAD'
    registry.append({'id': obj.name, 'family': family, 'shape': shape, 'note': note})
    return obj

def mesh(name, verts, faces, mat, parent=None, bevel=0, smooth=True, family=None, shape='', note=''):
    data = bpy.data.meshes.new(name + '_mesh')
    data.from_pydata(verts, [], faces)
    data.update()
    if faces:
        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(data)
        bm.free()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    if mat:
        data.materials.append(mat)
    for polygon in data.polygons:
        polygon.use_smooth = smooth
    if bevel:
        mod = obj.modifiers.new('Machined edge radii', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        mod.harden_normals = True
        normal = obj.modifiers.new('Weighted face normals', 'WEIGHTED_NORMAL')
        normal.keep_sharp = True
        normal.weight = 40
    if family:
        register(obj, family, shape, note)
    return obj

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def delete(obj):
    bpy.data.objects.remove(obj, do_unlink=True)

def boolean(target, cutter, operation='DIFFERENCE'):
    activate(target)
    bpy.context.view_layer.update()
    modifier = target.modifiers.new('Actual solid ' + operation.lower(), 'BOOLEAN')
    modifier.operation = operation
    modifier.solver = 'EXACT'
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    delete(cutter)

def bevel(obj, width, segments=3):
    mod = obj.modifiers.new('Finished edges', 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.harden_normals = True
    normal = obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    normal.keep_sharp = True
    return obj

def box(name, loc, dims, mat, parent=None, edge=0):
    x, y, z = (value / 2 for value in dims)
    verts = [(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)]
    faces = [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    obj = mesh(name, verts, faces, mat, parent, edge)
    obj.location = loc
    return obj

def revolve(name, profile, mat, parent=None, axis='Z', center=(0,0,0), segments=96,
            family=None, shape='', note='', edge=0):
    rings = []
    verts = []
    for radius, axial in profile:
        if abs(radius) < 1e-10:
            rings.append([len(verts)])
            point = (0, 0, axial) if axis == 'Z' else ((axial, 0, 0) if axis == 'X' else (0, axial, 0))
            verts.append(point)
        else:
            ring = []
            for j in range(segments):
                angle = 2 * PI * j / segments
                point = (radius * math.cos(angle), radius * math.sin(angle), axial) if axis == 'Z' else ((axial, radius * math.cos(angle), radius * math.sin(angle)) if axis == 'X' else (radius * math.cos(angle), axial, radius * math.sin(angle)))
                ring.append(len(verts))
                verts.append(point)
            rings.append(ring)
    faces = []
    face_bands = []
    for k in range(len(rings)):
        next_k = (k + 1) % len(rings)
        a, b = rings[k], rings[next_k]
        for j in range(segments):
            j2 = (j + 1) % segments
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                faces.append((a[0], b[j2], b[j]))
            elif len(b) == 1:
                faces.append((a[j], a[j2], b[0]))
            else:
                faces.append((a[j], a[j2], b[j2], b[j]))
            face_bands.append(k)
    obj = mesh(name, verts, faces, mat, parent, edge, True, family, shape, note)
    obj.location = center
    obj['profile_bands'] = face_bands
    return obj

def sector(name, profile, start, end, mat, parent=None, axis='X', center=(0,0,0), steps=48,
           family=None, shape='', note='', inner_mat=None, edge=0):
    verts = []
    for i in range(steps + 1):
        angle = start + (end - start) * i / steps
        for radius, axial in profile:
            if axis == 'X':
                verts.append((axial, radius * math.cos(angle), radius * math.sin(angle)))
            elif axis == 'Y':
                verts.append((radius * math.cos(angle), axial, radius * math.sin(angle)))
            else:
                verts.append((radius * math.cos(angle), radius * math.sin(angle), axial))
    n = len(profile)
    faces = []
    indices = []
    for i in range(steps):
        for j in range(n):
            j2 = (j + 1) % n
            faces.append((i*n+j, i*n+j2, (i+1)*n+j2, (i+1)*n+j))
            indices.append(j)
    faces.append(tuple(range(n-1, -1, -1)))
    indices.append(-1)
    faces.append(tuple(steps*n+j for j in range(n)))
    indices.append(-1)
    obj = mesh(name, verts, faces, mat, parent, edge, True, family, shape, note)
    obj.location = center
    if inner_mat:
        obj.data.materials.append(inner_mat)
        for poly, index in zip(obj.data.polygons, indices):
            if index == n - 1:
                poly.material_index = 1
    return obj

def cylinder(name, radius, depth, loc, mat, parent=None, axis=(0,0,1), vertices=64):
    verts = []
    for z in [-depth/2, depth/2]:
        for i in range(vertices):
            angle = 2 * PI * i / vertices
            verts.append((radius * math.cos(angle), radius * math.sin(angle), z))
    faces = []
    for i in range(vertices):
        j = (i + 1) % vertices
        faces.append((i, j, j + vertices, i + vertices))
    faces.extend([tuple(range(vertices-1, -1, -1)), tuple(range(vertices, vertices*2))])
    obj = mesh(name, verts, faces, mat, parent)
    obj.location = loc
    obj.rotation_euler = Vector(axis).to_track_quat('Z', 'Y').to_euler()
    return obj

def tube_curve(name, points, radius, mat, parent=None, sides=8, family=None, shape='', note=''):
    coords = [Vector(point) for point in points]
    verts = []
    for i, point in enumerate(coords):
        tangent = (coords[min(i+1, len(coords)-1)] - coords[max(i-1, 0)]).normalized()
        reference = Vector((0,0,1)) if abs(tangent.z) < .90 else Vector((0,1,0))
        normal = tangent.cross(reference).normalized()
        binormal = tangent.cross(normal).normalized()
        for j in range(sides):
            a = 2 * PI * j / sides
            verts.append(tuple(point + radius * (normal * math.cos(a) + binormal * math.sin(a))))
    faces = []
    for i in range(len(coords)-1):
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((i*sides+j, i*sides+j2, (i+1)*sides+j2, (i+1)*sides+j))
    faces += [tuple(range(sides-1,-1,-1)), tuple((len(coords)-1)*sides+j for j in range(sides))]
    return mesh(name, verts, faces, mat, parent, 0, True, family, shape, note)

def clone_tree(source, parent, suffix):
    obj = source.copy()
    obj.name = source.name + suffix
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.animation_data_clear()
    if 'semantic_id' in obj:
        obj['semantic_id'] = obj.name
        registry.append({'id': obj.name, 'family': obj['part_family'], 'shape': obj['structure'],
                         'note': 'Linked geometry instance of ' + source.name})
    for child in source.children:
        clone_tree(child, obj, suffix)
    return obj



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
