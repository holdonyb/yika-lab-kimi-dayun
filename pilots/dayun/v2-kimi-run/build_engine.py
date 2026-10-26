from pathlib import Path
import bpy
import bmesh
import json
import math
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PI = math.pi
BORE = 0.126
STROKE = 0.166
CRANK_R = STROKE / 2
ROD_L = 0.235
PITCH = 0.165
CYLINDERS = [(i - 2.5) * PITCH for i in range(6)]
PHASES = [0, 4 * PI / 3, 2 * PI / 3, 2 * PI / 3, 4 * PI / 3, 0]
MAINS = [(i - 3) * PITCH for i in range(7)]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for material in list(bpy.data.materials):
    bpy.data.materials.remove(material)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 360
registry = []
explosions = {}
prototypes = {}


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


aluminum = metal('Aluminum | cast and machined piston', (0.48, 0.54, 0.60), .39, .82, .16, True)
bowl_mat = metal('Aluminum | combustion bowl', (.15, .18, .21), .49, .80, .08, True)
steel = metal('Steel | forged', (.22, .27, .32), .36, .94, .18, True)
machined = metal('Steel | machined journals', (.45, .52, .59), .27, .98, .25)
pin_steel = metal('Steel | polished pin', (.55, .63, .71), .20, 1, .32)
ring_steel = metal('Steel | compression rings', (.15, .19, .23), .28, .96, .25)
dark_steel = metal('Steel | crank webs', (.12, .155, .19), .39, .94, .16, True)
bronze = metal('Bronze | sliding bearing', (.56, .30, .115), .30, .86, .18)
bush_bronze = metal('Bronze | small-end bush', (.50, .275, .095), .33, .86, .22)
shell_back = metal('Steel | bearing backing', (.29, .33, .38), .34, .92, .18)
black = metal('Frame | dark oxide', (.028, .039, .052), .43, .74)
floor_mat = metal('Studio | charcoal', (.020, .027, .036), .48, .22)


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
    obj['reference_scope'] = 'Generic heavy-duty inline-six structure; not OEM CAD'
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
            point = (0, 0, axial) if axis == 'Z' else (axial, 0, 0)
            verts.append(point)
        else:
            ring = []
            for j in range(segments):
                angle = 2 * PI * j / segments
                point = (radius * math.cos(angle), radius * math.sin(angle), axial) if axis == 'Z' else (axial, radius * math.cos(angle), radius * math.sin(angle))
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


def add_elastic_opening(root, property_name):
    controller[property_name] = 0.0
    objects = [root] if root.type == 'MESH' else list(root.children_recursive)
    for obj in objects:
        if obj.type != 'MESH':
            continue
        obj.data = obj.data.copy()
        obj.shape_key_add(name='Basis')
        opened = obj.shape_key_add(name='ElasticOpening')
        for vertex in opened.data:
            radius = math.hypot(vertex.co.x, vertex.co.y)
            if radius > 0.00001:
                factor = (radius + .0048) / radius
                vertex.co.x *= factor
                vertex.co.y *= factor
        curve = opened.driver_add('value')
        drive = curve.driver
        variable = drive.variables.new()
        variable.name = 'opening'
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id = controller
        variable.targets[0].data_path = '["' + property_name + '"]'
        drive.expression = 'opening'
        obj['disassembly_path'] = 'Liner clears first; open ring expands radially beyond the piston land, lifts, then returns and closes'


def split_ring(name, profile, gap_angle, mat, parent, family, shape):
    obj = sector(name, profile, gap_angle/2, 2*PI-gap_angle/2, mat, parent, 'Z',
                 steps=160, family=family, shape=shape, edge=.00010)
    obj.rotation_euler.z = gap_angle * 2.7
    return obj


def make_piston():
    outer = .06265
    groove = .0596
    profile = [(.052,-.055),(.0605,-.055),(outer,-.049),(outer,.020),
               (outer,.022),(groove,.022),(groove,.030),(outer,.030),
               (outer,.037),(groove,.037),(groove,.044),(outer,.044),
               (outer,.050),(groove,.050),(groove,.056),(outer,.056),
               (outer,.063),(.0618,.067),(.0485,.067),(.0455,.063),
               (.0400,.055),(.0320,.049),(.0230,.047),(.0130,.049),(0,.052),
               (0,.025),(.043,.025),(.052,.013)]
    piston = revolve('Piston_01', profile, aluminum, edge=0, segments=128,
                     family='piston', shape='Hollow skirt; recessed omega bowl; three machined ring grooves; two pin bosses; transverse bore')
    piston.data.materials.append(bowl_mat)
    for polygon in piston.data.polygons:
        if polygon.center.z > .044 and math.hypot(polygon.center.x, polygon.center.y) < .049:
            polygon.material_index = 1
    for side in [-1, 1]:
        boss = revolve('Pin boss', [(.0223,-.013),(.030,-.013),(.030,.013),(.0223,.013)],
                       aluminum, piston, 'X', (side*.035,0,0), 72)
        boolean(piston, boss, 'UNION')
        web = box('Boss crown web', (side*.035,0,.019), (.026,.035,.037), aluminum, piston)
        boolean(piston, web, 'UNION')
    bore = cylinder('Through piston-pin bore cutter', .0223, .155, (0,0,0), aluminum, piston, (1,0,0), 96)
    boolean(piston, bore)
    for side in [-1,1]:
        groove_cut = revolve('Circlip groove cutter', [(.0220,-.0008),(.0258,-.0008),(.0258,.0008),(.0220,.0008)],
                             aluminum, piston, 'X', (side*.058,0,0), 96)
        boolean(piston, groove_cut)
    bevel(piston, .00055)
    prototypes['piston'] = piston
    return piston


def make_oil_ring(parent):
    root = group('OilRing_01', parent)
    register(root, 'oil_control_ring', 'Two split scraper rails, slotted spacer band and open toroidal coil expander',
             'Generic interpretation of the referenced coil-spring-loaded oil-control ring')
    for z, label in [(-.0025,'Lower'),(.0025,'Upper')]:
        split_ring('Oil'+label+'Rail_01', [(.0598,.026+z-.00045),(.0629,.026+z-.00045),
                   (.0629,.026+z+.00045),(.0598,.026+z+.00045)], math.radians(.8), ring_steel,
                   root, 'oil_scraper_rail', 'Open rectangular-section oil scraper rail')
    for i in range(28):
        a0 = math.radians(.4) + 2*PI*i/28 + math.radians(1.4)
        a1 = 2*PI*(i+1)/28 - math.radians(1.4)
        sector('Oil spacer window segment', [(.0601,.0252),(.0621,.0252),(.0621,.0268),(.0601,.0268)],
               a0,a1,steel,root,'Z',steps=4,edge=.00006)
    points = []
    turns = 44
    for i in range(turns*14+1):
        a = math.radians(.7) + (2*PI-math.radians(1.4))*i/(turns*14)
        phase = turns*a
        radius = .0612 + .00115*math.cos(phase)
        points.append((radius*math.cos(a),radius*math.sin(a),.026+.00115*math.sin(phase)))
    tube_curve('Oil expander coil_01',points,.00043,pin_steel,root,8)
    prototypes['oil_ring'] = root
    return root


def make_pin_and_clips(parent):
    pin = revolve('PistonPin_01', [(.0135,-.0565),(.0208,-.0565),(.0220,-.0548),
                  (.0220,.0548),(.0208,.0565),(.0135,.0565)], pin_steel, parent, 'X',
                  segments=112, family='piston_pin', shape='Through-hollow floating pin with chamfered ends')
    prototypes['pin'] = pin
    for side, label in [(-1,'L'),(1,'R')]:
        clip = sector('PistonCirclip'+label+'_01', [(.0220,-.0006),(.0255,-.0006),(.0255,.0006),(.0220,.0006)],
                      math.radians(16),math.radians(344),pin_steel,parent,'X',(side*.058,0,0),96,
                      'piston_circlip','Open spring-steel retaining ring with plier lugs')
        for sign in [-1,1]:
            a = math.radians(16 if sign<0 else 344)
            y,z = .0247*math.cos(a),.0247*math.sin(a)
            lug = revolve('Circlip plier lug', [(.0008,-.0009),(.0025,-.0009),(.0025,.0009),(.0008,.0009)],
                          pin_steel,clip,'X',(0,y,z),32)
            boolean(clip,lug,'UNION')
        bevel(clip,.00010)
        prototypes['clip'+label] = clip


def make_rod_bolt(parent):
    root = group('RodCapBolt_01_A',parent)
    register(root,'rod_cap_bolt','Hex-head cap bolt with washer, shank and actual helical thread crest')
    cylinder('Cap bolt shank',.0042,.069,(0,0,.001),machined,root,vertices=40)
    cylinder('Cap bolt hex head',.0080,.0065,(0,0,-.036),steel,root,vertices=6)
    revolve('Cap bolt washer',[(.0044,-.0310),(.0090,-.0310),(.0090,-.0295),(.0044,-.0295)],
            machined,root,'Z',segments=48)
    points = []
    turns = 12
    for i in range(turns*20+1):
        t = i/(turns*20)
        a = 2*PI*turns*t
        points.append((.00425*math.cos(a),.00425*math.sin(a),.016+.017*t))
    tube_curve('Cap bolt thread',points,.00043,machined,root,7)
    bevel(root.children[0],.00018)
    prototypes['rod_bolt'] = root
    return root


def make_rod_body():
    big = sector('Rod big upper half',[(.0358,-.019),(.0495,-.019),(.0495,.019),(.0358,.019)],
                 0,PI,steel,steps=72)
    small = revolve('Rod small ring',[(.0242,-.0145),(.0305,-.0145),(.0305,.0145),(.0242,.0145)],
                    steel,axis='X',center=(0,0,ROD_L),segments=80)
    boolean(big,small,'UNION')
    cross = [(-.014,-.021),(.014,-.021),(.014,-.016),(.005,-.016),(.005,.016),(.014,.016),
             (.014,.021),(-.014,.021),(-.014,.016),(-.005,.016),(-.005,-.016),(-.014,-.016)]
    verts = []
    sections = [(.040,1.20),(.073,1.04),(ROD_L-.060,.72),(ROD_L-.024,.63)]
    for z,scale in sections:
        for x,y in cross:
            verts.append((x*scale,y*scale,z))
    faces = [tuple(range(11,-1,-1))]
    n = len(cross)
    for k in range(len(sections)-1):
        for j in range(n):
            faces.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
    faces.append(tuple((len(sections)-1)*n+j for j in range(n)))
    web = mesh('Tapered forged I-beam',verts,faces,steel)
    boolean(big,web,'UNION')
    for side in [-1,1]:
        boss = box('Rod threaded boss',(0,side*.042,.018),(.034,.012,.034),steel)
        boolean(big,boss,'UNION')
        hole = cylinder('Rod bolt bore',.0048,.09,(0,side*.042,.012),steel,axis=(0,0,1),vertices=32)
        boolean(big,hole)
    bevel(big,.00035)
    register(big,'connecting_rod_body','Upper big-end half bore, full small-end bore and tapered forged I-section')
    prototypes['rod_body'] = big
    return big


def make_rod_cap():
    cap = sector('Rod cap lower half',[(.0358,-.019),(.0495,-.019),(.0495,.019),(.0358,.019)],
                 PI,2*PI,steel,steps=72)
    for side in [-1,1]:
        boss = box('Cap bolt boss',(0,side*.042,-.015),(.036,.012,.028),steel)
        boolean(cap,boss,'UNION')
        hole = cylinder('Cap bolt clearance bore',.0048,.08,(0,side*.042,-.015),steel,vertices=32)
        boolean(cap,hole)
    bevel(cap,.00035)
    register(cap,'connecting_rod_cap','Independent lower half cap with two real bolt bores')
    prototypes['rod_cap'] = cap
    return cap


def animate_offset(obj, offset, start, end):
    explosions[obj.name] = {'object': obj, 'base': obj.location.copy(), 'offset': Vector(offset),
                            'start': start, 'end': end}


def ease_between(time, start, end):
    if time <= start:
        return 0.0
    if time >= end:
        return 1.0
    t = (time - start) / (end - start)
    return t * t * (3 - 2 * t)


def explosion_amount(time, start, end):
    restore_start = 13 - end
    restore_end = 13 - start
    if time < start or time >= restore_end:
        return 0.0
    if time < end:
        return ease_between(time, start, end)
    if time <= restore_start:
        return 1.0
    return 1.0 - ease_between(time, restore_start, restore_end)


def sample_liner(time):
    for (start_time,start_point),(end_time,end_point) in zip(liner_path,liner_path[1:]):
        if time <= end_time:
            amount = ease_between(time,start_time,end_time)
            return Vector(start_point).lerp(Vector(end_point),amount)
    return Vector(liner_path[-1][1])


controller = group('CrankAngleController')
controller['angle'] = 0.0
controller['crank_radius'] = CRANK_R
controller['rod_length'] = ROD_L
controller['phase_layout_degrees'] = [math.degrees(value) for value in PHASES]
controller['kinematics'] = 'One crank angle; exact slider-crank geometry; no independent piston sine animations'
for frame, angle in [(1,0),(240,0),(241,0),(360,4*PI)]:
    controller['angle'] = angle
    controller.keyframe_insert(data_path='["angle"]',frame=frame)


def driver(obj, path, index, expression, phase=None):
    curve = obj.driver_add(path,index) if index is not None else obj.driver_add(path)
    drive = curve.driver
    drive.type = 'SCRIPTED'
    for name, prop in [('a','angle'),('r','crank_radius'),('l','rod_length')]:
        variable = drive.variables.new()
        variable.name = name
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id = controller
        variable.targets[0].data_path = '["' + prop + '"]'
    if phase is not None:
        expression = expression.replace('PHASE', f'{phase:.12f}')
    drive.expression = expression


def action_curves(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return []
    action = obj.animation_data.action
    if hasattr(action,'fcurves'):
        return list(action.fcurves)
    curves = []
    for layer in action.layers:
        for strip in layer.strips:
            if hasattr(strip,'channelbags'):
                for bag in strip.channelbags:
                    curves.extend(bag.fcurves)
    return curves


for curve in action_curves(controller):
    for point in curve.keyframe_points:
        point.interpolation = 'LINEAR'

engine_root = group('InlineSixCore')
engine_root['scope'] = 'Original generic heavy-truck inline-six cranktrain core; not a Dayun or Weichai OEM model'
engine_root['units'] = 'meters; cylinder axes Z; crankshaft axis X'
engine_root['bore'] = BORE
engine_root['stroke'] = STROKE
engine_root['rod_center_distance'] = ROD_L
engine_root['cylinder_pitch'] = PITCH
piston_motions = []
rod_motions = []
pin_anchors = []
small_anchors = []
crankpin_anchors = []
liner_groups = []
first_lift = group('FirstCylinderAssemblyLift',engine_root)
first_detached = group('FirstDetachedRodParts',engine_root,(CYLINDERS[0],0,CRANK_R))
first_detached['role'] = 'Removed cap, lower bearing and bolts follow the crankpin, not the service lift of the piston and rod'
for path,index,expression in [('location',1,'-r*sin(a+PHASE)'),('location',2,'r*cos(a+PHASE)'),
                              ('rotation_euler',0,'atan2(-r*sin(a+PHASE),sqrt(l*l-r*r*sin(a+PHASE)**2))')]:
    driver(first_detached,path,index,expression,0.0)
liner_bank = group('CylinderLinerBank_PhotographyLift',engine_root)

for i, x in enumerate(CYLINDERS):
    number = i + 1
    suffix = '' if i == 0 else f'_C{number:02d}'
    piston_motion = group(f'PistonMotion_{number:02d}',first_lift if i == 0 else engine_root,(x,0,0))
    piston_motions.append(piston_motion)
    driver(piston_motion,'location',2,'r*cos(a+PHASE)+sqrt(l*l-r*r*sin(a+PHASE)**2)',PHASES[i])
    body_carrier = group(f'PistonBodyCarrier_{number:02d}',piston_motion)
    if i == 0:
        piston = make_piston()
        piston.parent = body_carrier
        ring1 = split_ring('CompressionRing1_01',[(.0598,.0514),(.06272,.0514),(.0629,.0530),(.06272,.0546),(.0598,.0543)],
                           math.radians(.65),machined,body_carrier,'compression_ring_top','Open keystone barrel-faced top compression ring')
        ring2 = split_ring('CompressionRing2_01',[(.0598,.0389),(.0629,.0390),(.06265,.0421),(.0598,.0418)],
                           math.radians(.65),ring_steel,body_carrier,'compression_ring_second','Open twist taper-faced second compression ring')
        ring2.rotation_euler.z = 2.7
        make_oil_ring(body_carrier)
        make_pin_and_clips(piston_motion)
    else:
        clone_tree(prototypes['piston'],body_carrier,suffix)
        clone_tree(bpy.data.objects['CompressionRing1_01'],body_carrier,suffix)
        clone_tree(bpy.data.objects['CompressionRing2_01'],body_carrier,suffix)
        clone_tree(prototypes['oil_ring'],body_carrier,suffix)
        clone_tree(prototypes['pin'],piston_motion,suffix)
        clone_tree(prototypes['clipL'],piston_motion,suffix)
        clone_tree(prototypes['clipR'],piston_motion,suffix)
    pin_anchor = group(f'PistonPinAnchor_{number:02d}',piston_motion)
    pin_anchors.append(pin_anchor)
    rod_motion = group(f'RodMotion_{number:02d}',first_lift if i == 0 else engine_root,(x,0,CRANK_R*math.cos(PHASES[i])))
    rod_motions.append(rod_motion)
    driver(rod_motion,'location',1,'-r*sin(a+PHASE)',PHASES[i])
    driver(rod_motion,'location',2,'r*cos(a+PHASE)',PHASES[i])
    driver(rod_motion,'rotation_euler',0,'atan2(-r*sin(a+PHASE),sqrt(l*l-r*r*sin(a+PHASE)**2))',PHASES[i])
    if i == 0:
        rod = make_rod_body()
        rod.parent = rod_motion
        bush = revolve('SmallEndBush_01',[(.0221,-.0143),(.0240,-.0143),(.0240,.0143),(.0221,.0143)],
                       bush_bronze,rod_motion,'X',(0,0,ROD_L),96,
                       'small_end_bush','Independent full-thickness plain sliding bush, aligned to piston pin',edge=.00020)
        prototypes['bush'] = bush
        upper = sector('RodBearingUpper_01',[(.0330,-.016),(.0355,-.016),(.0355,.016),(.0330,.016)],
                       0,PI,shell_back,rod_motion,'X',steps=80,family='rod_bearing_upper',
                       shape='Upper half-shell plain bearing with steel back and bronze running surface',inner_mat=bronze,edge=.00012)
        lower = sector('RodBearingLower_01',[(.0330,-.016),(.0355,-.016),(.0355,.016),(.0330,.016)],
                       PI,2*PI,shell_back,first_detached,'X',steps=80,family='rod_bearing_lower',
                       shape='Lower half-shell plain bearing with steel back and bronze running surface',inner_mat=bronze,edge=.00012)
        cap_carrier = group('RodCapCarrier_01',first_detached)
        cap = make_rod_cap()
        cap.parent = cap_carrier
        bolt_a = make_rod_bolt(first_detached)
        bolt_a.location.y = -.042
        bolt_b = clone_tree(bolt_a,first_detached,'_B')
        bolt_b.name = 'RodCapBolt_01_B'
        bolt_b['semantic_id'] = bolt_b.name
        bolt_b.location.y = .042
        registry[-1]['id'] = bolt_b.name
        prototypes['cap_carrier'] = cap_carrier
        prototypes['upper_bearing'] = upper
        prototypes['lower_bearing'] = lower
        prototypes['bolt_a'] = bolt_a
        prototypes['bolt_b'] = bolt_b
    else:
        clone_tree(prototypes['rod_body'],rod_motion,suffix)
        clone_tree(prototypes['bush'],rod_motion,suffix)
        clone_tree(prototypes['upper_bearing'],rod_motion,suffix)
        clone_tree(prototypes['lower_bearing'],rod_motion,suffix)
        clone_tree(prototypes['cap_carrier'],rod_motion,suffix)
        clone_tree(prototypes['bolt_a'],rod_motion,suffix)
        clone_tree(prototypes['bolt_b'],rod_motion,suffix)
    small_anchor = group(f'RodSmallEndAnchor_{number:02d}',rod_motion,(0,0,ROD_L))
    small_anchors.append(small_anchor)
    if i == 0:
        for name in ['RodCapBolt_01_A','RodCapBolt_01_B']:
            animate_offset(bpy.data.objects[name],(0,0,-.145),3.20,3.50)
        animate_offset(cap_carrier,(0,0,-.100),3.45,3.75)
        animate_offset(lower,(0,0,-.060),3.70,4.00)
        animate_offset(first_lift,(0,0,.150),3.95,4.30)
        animate_offset(upper,(0,0,-.070),4.30,4.60)
        animate_offset(prototypes['clipL'],(-.055,0,0),4.45,4.70)
        animate_offset(prototypes['clipR'],(.040,0,0),4.45,4.70)
        animate_offset(prototypes['pin'],(-.170,0,0),4.70,5.00)
        animate_offset(body_carrier,(0,0,.055),4.95,5.25)
        animate_offset(bush,(-.055,0,0),5.10,5.40)
        animate_offset(bpy.data.objects['CompressionRing1_01'],(0,0,.055),5.35,5.60)
        animate_offset(bpy.data.objects['CompressionRing2_01'],(0,0,.085),5.60,5.80)
        animate_offset(prototypes['oil_ring'],(0,0,.115),5.85,6.00)

full_liner = None
for i,x in enumerate(CYLINDERS):
    number = i+1
    liner_root = group(f'CylinderLiner_{number:02d}',liner_bank,(x,0,0))
    liner_groups.append(liner_root)
    profile = [(.063,.140),(.0695,.140),(.0700,.148),(.0700,.391),(.074,.391),(.074,.405),(.063,.405)]
    if full_liner is None:
        full_liner = revolve('CylinderLiner_01_Closed',profile,machined,liner_root,segments=128,
            family='cylinder_liner',shape='Hollow wet liner with through bore, wall thickness and upper flange',edge=.00045)
        full_liner['photography_state'] = 'Closed source liner; hidden only for photographic section view'
        cutter = box('Photographic half-section cutter',(0,-.080,.270),(.30,.160,.40),machined,liner_root)
        section = full_liner.copy()
        section.data = full_liner.data.copy()
        bpy.context.collection.objects.link(section)
        section.name = 'CylinderLiner_01_PhotoSection'
        section.parent = liner_root
        section['semantic_id'] = section.name
        section['photography_state'] = 'Open photographic half section of CylinderLiner_01; not a closed liner'
        section.modifiers.clear()
        boolean(section,cutter)
        bevel(section,.00045)
        full_liner.hide_render = True
        full_liner.hide_viewport = True
        liner_path = [(0,(0,0,0)),(3.00,(0,0,0)),(3.35,(0,0,.300)),
                      (3.65,(0,.360,.300)),(9.65,(0,.360,.300)),
                      (9.75,(0,0,.300)),(10.0,(0,0,0)),(15.0,(0,0,0))]
    else:
        liner = full_liner.copy()
        liner.data = full_liner.data
        bpy.context.collection.objects.link(liner)
        liner.name = f'CylinderLiner_{number:02d}'
        liner.parent = liner_root
        liner.location = (0,0,0)
        liner.hide_render = False
        liner.hide_viewport = False
        liner['semantic_id'] = liner.name
        registry.append({'id':liner.name,'family':'cylinder_liner','shape':full_liner['structure'],
                         'note':'Linked closed hollow liner instance'})
for frame,lift in [(1,0),(240,0),(241,.220),(360,.220)]:
    liner_bank.location.z = lift
    liner_bank.keyframe_insert(data_path='location',index=2,frame=frame)
for curve in action_curves(liner_bank):
    for point in curve.keyframe_points:
        point.interpolation = 'CONSTANT'

crank_root = group('CrankshaftRotation',engine_root)
driver(crank_root,'rotation_euler',0,'a')
crank_parts = []
for x in MAINS:
    crank_parts.append(cylinder('Main journal',.037,.034,(x,0,0),machined,crank_root,(1,0,0),80))
for i,x in enumerate(CYLINDERS):
    for side in [-1,1]:
        web_x = x + side*.041
        main_x = x + side*PITCH/2
        crank_parts.append(cylinder('Journal to web shoulder',.024,abs(main_x-web_x)+.004,
            ((main_x+web_x)/2,0,0),dark_steel,crank_root,(1,0,0),56))
        outline = [(-.026,-.066),(-.051,-.061),(-.063,-.034),(-.061,-.009),(-.040,.018),
                   (-.030,.048),(-.030,.071),(-.024,.096),(-.015,.114),(.015,.114),(.024,.096),
                   (.030,.071),(.030,.048),(.040,.018),(.061,-.009),(.063,-.034),(.051,-.061),(.026,-.066)]
        verts = []
        for xx in [web_x-.006,web_x+.006]:
            for y,z in outline:
                a = PHASES[i]
                verts.append((xx,y*math.cos(a)-z*math.sin(a),y*math.sin(a)+z*math.cos(a)))
        n = len(outline)
        faces = [tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]
        for j in range(n):
            faces.append((j,(j+1)%n,(j+1)%n+n,j+n))
        crank_parts.append(mesh('Forged crank web and counterweight',verts,faces,dark_steel,crank_root))
    y = -CRANK_R*math.sin(PHASES[i])
    z = CRANK_R*math.cos(PHASES[i])
    crank_parts.append(cylinder('Offset connecting-rod journal',.0325,.076,(x,y,z),machined,crank_root,(1,0,0),80))
    crankpin_anchors.append(group(f'CrankpinAnchor_{i+1:02d}',crank_root,(x,y,z)))
crank_parts.append(cylinder('Front crank nose',.029,.105,(-.558,0,0),machined,crank_root,(1,0,0),80))
crank_parts.append(cylinder('Rear crank flange',.064,.034,(.543,0,0),dark_steel,crank_root,(1,0,0),80))
crank = crank_parts[0]
crank.name = 'Crankshaft_Forging'
for part in crank_parts[1:]:
    boolean(crank,part,'UNION')
for i in range(8):
    angle = 2*PI*i/8
    cutter = cylinder('Flywheel flange mounting hole',.0052,.12,(.548,.060*math.cos(angle),.060*math.sin(angle)),
                      machined,crank_root,(1,0,0),32)
    boolean(crank,cutter)
bevel(crank,.00085)
register(crank,'crankshaft','Continuous forged shaft, seven main journals, six offset crankpins, crank webs and counterweights')
prototypes['crank'] = crank

flywheel = revolve('Flywheel_01',[(.028,-.015),(.054,-.015),(.054,-.022),(.075,-.022),(.075,-.013),
    (.132,-.013),(.132,.013),(.075,.013),(.075,.022),(.054,.022),(.054,.015),(.028,.015)],
    steel,crank_root,'X',(.552,0,0),128,'flywheel','Stepped flywheel with center spigot interface and eight through mounting holes')
for i in range(8):
    angle = 2*PI*i/8
    cutter = cylinder('Flywheel through hole',.0052,.075,(.552,.060*math.cos(angle),.060*math.sin(angle)),
                      steel,crank_root,(1,0,0),32)
    boolean(flywheel,cutter)
bevel(flywheel,.00055)
verts = []
teeth = 96
for i in range(teeth*4):
    angle = 2*PI*i/(teeth*4)
    outer = .149 if i%4 in [1,2] else .142
    for radius,axial in [(.128,-.010),(outer,-.010),(outer,.010),(.128,.010)]:
        verts.append((.556+axial,radius*math.cos(angle),radius*math.sin(angle)))
faces = []
for i in range(teeth*4):
    for j in range(4):
        faces.append((i*4+j,i*4+(j+1)%4,((i+1)%(teeth*4))*4+(j+1)%4,((i+1)%(teeth*4))*4+j))
gear = mesh('Flywheel_RingGear',verts,faces,machined,crank_root,.00020,False,
            'flywheel_ring_gear','Continuous ring gear with trapezoid teeth and open center')

frame_root = group('OpenCrankcaseAndMainBearings',engine_root)
for i,x in enumerate(MAINS):
    number = i+1
    main = group(f'MainBearing_{number:02d}',frame_root,(x,0,0))
    upper = sector(f'MainBearingUpper_{number:02d}',[(.0374,-.014),(.0405,-.014),(.0405,.014),(.0374,.014)],
                   0,PI,shell_back,main,steps=64,family='main_bearing_upper',
                   shape='Fixed upper half-shell plain main bearing',inner_mat=bronze,edge=.00012)
    lower = sector(f'MainBearingLower_{number:02d}',[(.0374,-.014),(.0405,-.014),(.0405,.014),(.0374,.014)],
                   PI,2*PI,shell_back,main,steps=64,family='main_bearing_lower',
                   shape='Lower half-shell plain main bearing in independent cap',inner_mat=bronze,edge=.00012)
    saddle = sector('Fixed upper main saddle',[(.0408,-.017),(.058,-.017),(.058,.017),(.0408,.017)],
                    0,PI,steel,main,steps=64,edge=.00065)
    cap = sector(f'MainBearingCap_{number:02d}',[(.0408,-.017),(.058,-.017),(.058,.017),(.0408,.017)],
                 PI,2*PI,steel,main,steps=64,family='main_bearing_cap',
                 shape='Independent fixed lower main bearing cap with two fastener bosses',edge=0)
    for side in [-1,1]:
        boss = box('Main cap fastener boss',(0,side*.052,-.018),(.033,.021,.030),steel,main)
        boolean(cap,boss,'UNION')
        bolt = clone_tree(prototypes['rod_bolt'],main,f'_Main_{number:02d}_{side}')
        bolt.name = f'MainBearingBolt_{number:02d}_{"A" if side<0 else "B"}'
        bolt['part_family'] = 'main_bearing_bolt'
        bolt['structure'] = 'Fixed main-cap bolt with shank, washer and helical thread'
        bolt['semantic_id'] = bolt.name
        bolt.location = (0,side*.052,-.005)
        bolt.scale = (1.25,1.25,1.25)
        registry[-1].update({'id':bolt.name,'family':'main_bearing_bolt','shape':bolt['structure'],
                             'note':'Main bearing fasteners remain fixed while crank rotates'})
    bevel(cap,.00065)
    box('Main upper bridge',(0,0,.069),(.034,.183,.028),steel,main,.0015)

for side in [-1,1]:
    box('Lower ladder rail',(0,side*.106,-.092),(1.09,.025,.027),black,frame_root,.003)
    box('Upper side rail',(0,side*.106,.083),(1.06,.022,.023),black,frame_root,.003)
    for x in MAINS:
        box('Open crankcase rib',(x,side*.106,-.005),(.025,.021,.162),black,frame_root,.0025)
        box('Main cap side connection',(x,side*.079,-.040),(.030,.060,.020),steel,frame_root,.002)
    for x in [-.36,.36]:
        box('Display support foot',(x,side*.106,-.138),(.12,.055,.070),black,frame_root,.005)
        box('Support pad',(x,side*.106,-.175),(.14,.065,.009),floor_mat,frame_root,.002)

add_elastic_opening(bpy.data.objects['CompressionRing1_01'],'ring1_open')
add_elastic_opening(bpy.data.objects['CompressionRing2_01'],'ring2_open')
add_elastic_opening(prototypes['oil_ring'],'oil_open')
open_tracks = {'ring1_open':(5.15,5.35),'ring2_open':(5.40,5.60),'oil_open':(5.65,5.85)}
shot_isolated = []
for root in piston_motions[1:] + rod_motions[1:] + liner_groups[1:]:
    shot_isolated.extend(root.children_recursive)
shot_isolated.extend(frame_root.children_recursive)
for obj in set(shot_isolated):
    if obj.type != 'MESH':
        continue
    for frame, hidden in [(1,False),(72,False),(73,True),(240,True),(241,False),(360,False)]:
        obj.hide_render = hidden
        obj.keyframe_insert(data_path='hide_render',frame=frame)

first_liner = liner_groups[0]
first_liner_base = first_liner.location.copy()
for frame in range(1,361):
    time = (frame-1)/24
    for item in explosions.values():
        amount = explosion_amount(time,item['start'],item['end'])
        item['object'].location = item['base'] + item['offset']*amount
        item['object'].keyframe_insert(data_path='location',frame=frame)
    first_liner.location = first_liner_base + sample_liner(time)
    first_liner.keyframe_insert(data_path='location',frame=frame)
    for property_name,(start,end) in open_tracks.items():
        controller[property_name] = explosion_amount(time,start,end)
        controller.keyframe_insert(data_path='["'+property_name+'"]',frame=frame)
for obj in explosions.values():
    for curve in action_curves(obj['object']):
        for point in curve.keyframe_points:
            point.interpolation = 'LINEAR'
for curve in action_curves(controller):
    for point in curve.keyframe_points:
        point.interpolation = 'LINEAR'

floor = box('Photography floor',(0,0,-.191),(200,200,.02),floor_mat)
world = bpy.data.worlds.new('Dark mechanical studio')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.065,.085,.12,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .20
scene.world = world


def area(name,loc,energy,color,size,target,shape='DISK',size_y=None):
    data = bpy.data.lights.new(name,'AREA')
    data.energy = energy
    data.specular_factor = .35
    data.color = color
    data.shape = shape
    data.size = size
    if size_y is not None and shape == 'RECTANGLE':
        data.size_y = size_y
    obj = bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj


area('Key | large softbox',(-.40,-.72,1.12),32,(.83,.91,1.0),.75,(0,0,.20))
area('Machined edge | narrow strip',(.10,.35,1.05),28,(.91,.96,1.0),.95,(0,0,.23),'RECTANGLE',.075)
area('Warm rim',(.76,.45,.50),20,(1.0,.64,.34),.55,(0,0,.22),'RECTANGLE',.12)
area('Front pin fill',(-.85,-.15,.48),10,(.64,.79,1.0),.42,(-.30,0,.29))
area('Low bore fill',(.15,-.50,.12),6,(.79,.87,1.0),.55,(0,0,.08),'RECTANGLE',.08)

focus = group('CameraFocus')
camera_data = bpy.data.cameras.new('CinemaCamera')
camera = bpy.data.objects.new('CinemaCamera',camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera
camera.data.sensor_width = 36
camera.data.clip_start = .005
camera.data.clip_end = 100
camera.data.dof.focus_object = focus
camera.data.dof.aperture_blades = 7


def camera_key(frame,position,target,lens,fstop):
    camera.location = position
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.lens = lens
    camera.data.dof.aperture_fstop = fstop
    focus.location = target
    camera.keyframe_insert(data_path='location',frame=frame)
    camera.keyframe_insert(data_path='rotation_euler',frame=frame)
    camera.data.keyframe_insert(data_path='lens',frame=frame)
    camera.data.dof.keyframe_insert(data_path='aperture_fstop',frame=frame)
    focus.keyframe_insert(data_path='location',frame=frame)


camera_key(1,(-.650,-.280,.610),(-.4125,0,.350),58,14.0)
camera_key(40,(-.620,-.285,.535),(-.4125,0,.344),60,14.0)
camera_key(72,(-.600,-.290,.490),(-.4125,0,.333),62,14.0)
camera_key(73,(-1.16,-1.15,.76),(-.425,0,.30),33,11)
camera_key(169,(-1.23,-1.23,.80),(-.425,0,.31),33,11)
camera_key(217,(-1.21,-1.21,.79),(-.425,0,.31),33,11)
camera_key(240,(-1.20,-1.20,.79),(-.425,0,.31),33,11)
camera_key(241,(-.72,-1.90,.97),(0,0,.29),45,11)
camera_key(360,(-.58,-2.02,1.00),(0,0,.285),45,11)
for frame,name in [(1,'01 Macro / bowl and rings'),(73,'02 First cylinder disassembly'),(169,'03 Reverse assembly'),(241,'04 Six-cylinder working core')]:
    scene.timeline_markers.new(name,frame=frame)

scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 64
if hasattr(scene.eevee,'use_raytracing'):
    scene.eevee.use_raytracing = True
    if hasattr(scene.eevee,'ray_tracing_options'):
        options = scene.eevee.ray_tracing_options
        options.resolution_scale = '2'
        options.screen_trace_quality = .75
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.compression = 20
scene.render.filepath = '//frames/frame_'
scene.render.film_transparent = False
if hasattr(scene.render,'use_motion_blur'):
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = .20
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = -.50
scene.frame_set(1)
for screen in bpy.data.screens:
    for area_space in screen.areas:
        if area_space.type == 'VIEW_3D':
            area_space.spaces.active.region_3d.view_perspective = 'CAMERA'
            area_space.spaces.active.clip_start = .002
            area_space.spaces.active.clip_end = 100
activate(engine_root)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'engine_core.blend'))

families = {}
for item in registry:
    families.setdefault(item['family'],{'shape':item['shape'],'instances':[],'notes':[]})
    families[item['family']]['instances'].append(item['id'])
    if item['note']:
        families[item['family']]['notes'].append(item['note'])
manifest = {
    'title':'通用重卡直列六缸曲柄连杆核心',
    'scope':'Original generic structure. Not a Dayun OEM engine, not a Weichai OEM replica, not manufacturing CAD.',
    'reference':{'file':'../../reboot_20261026/references/weichai_wp13_parts.pdf',
                 'viewed':['PDF p25 main bearing half shells','p31 piston and rod exploded view','p33 rod body, cap, small-end bush and bolts','p35 piston ring set','following parts tables in extracted text']},
    'units':'meters',
    'authorDimensions':{'bore':BORE,'stroke':STROKE,'rodCenterDistance':ROD_L,'cylinderPitch':PITCH,
                        'pistonPinOuterRadius':.022,'pistonPinInnerRadius':.0135,'crankpinRadius':.0325,
                        'mainJournalRadius':.037,'pistonNominalOuterRadius':.06265,'linerInnerRadius':.063},
    'axes':{'crankshaft':'X','cylinderAndPiston':'Z','pistonPin':'X'},
    'phaseDegrees':[math.degrees(value) for value in PHASES],
    'phaseReason':'Inline-six 120-degree crank spacing with paired throws 1/6, 2/5 and 3/4; kinematic demonstration only',
    'families':families,
    'photography':{'firstLiner':'Closed source mesh retained but hidden; separate open section is explicitly a photographic variant',
                   'workingCore':'All six closed liners lift 0.220 m at the 10-second shot cut to expose the mechanism',
                   'notBuilt':['Cylinder head and head gasket','Valves, springs, camshaft and rocker mechanism','Fuel injectors and high-pressure fuel system',
                               'Water jackets, coolant and oil circuits','Intake and exhaust manifolds','Turbocharger','Complete crankcase and oil sump',
                               'Timing gears and front cover','Clutch and gearbox','Manufacturing tolerances, loads, combustion and fluid simulation']},
    'animation':{'fps':24,'frames':[1,360],'durationSeconds':15,
                 'shots':['0-3 s macro piston bowl, grooves, pin and retaining rings',
                          '3-7 s ordered first-cylinder disassembly','7-10 s reverse-order exact reassembly',
                          '10-15 s raised-liner photographic view of the working six-cylinder core'],
                 'motion':'Single animated crank angle drives every piston and rod using the slider-crank equation',
                 'disassembly':'Offsets are in parent-local assembly directions and return to stored local transforms',
                 'workingRevolutions':2},
}
(ROOT/'semantic_parts.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

from mathutils.bvhtree import BVHTree


def world_bvh(obj,depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    data = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ vertex.co for vertex in data.vertices]
    polygons = [tuple(polygon.vertices) for polygon in data.polygons]
    tree = BVHTree.FromPolygons(vertices,polygons,epsilon=0.000001)
    evaluated.to_mesh_clear()
    return tree


kinematic_samples = []
scene.frame_set(241)
for degrees in [0,90,180,270]:
    controller['angle'] = math.radians(degrees)
    controller.update_tag()
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for i in range(6):
        expected_big = Vector((CYLINDERS[i],-CRANK_R*math.sin(math.radians(degrees)+PHASES[i]),
                              CRANK_R*math.cos(math.radians(degrees)+PHASES[i])))
        actual_big = rod_motions[i].matrix_world.translation
        small = small_anchors[i].matrix_world.translation
        pin = pin_anchors[i].matrix_world.translation
        crankpin = crankpin_anchors[i].matrix_world.translation
        kinematic_samples.append({'angleDegrees':degrees,'cylinder':i+1,
            'bigEndToCrankpinErrorM':(actual_big-crankpin).length,
            'bigEndToAnalyticErrorM':(actual_big-expected_big).length,
            'smallEndToPistonPinErrorM':(small-pin).length,
            'smallEndY':small.y,'pinY':pin.y})
collision_samples = []
for degrees in [0,90,180,270]:
    controller['angle'] = math.radians(degrees)
    controller.update_tag()
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    crank_tree = world_bvh(crank,depsgraph)
    for obj in [bpy.data.objects['Rod big upper half'],bpy.data.objects['Rod cap lower half']]:
        if obj.name not in bpy.data.objects:
            continue
        overlaps = crank_tree.overlap(world_bvh(obj,depsgraph))
        collision_samples.append({'angleDegrees':degrees,'object':obj.name,'triangleOverlapCandidates':len(overlaps)})
scene.frame_set(1)
controller.update_tag()
bpy.context.view_layer.update()
max_error = max(max(item['bigEndToCrankpinErrorM'],item['bigEndToAnalyticErrorM'],item['smallEndToPistonPinErrorM']) for item in kinematic_samples)
verification = {'scope':'Kinematic and assembly checks, not manufacturing or dynamic simulation',
    'samples':kinematic_samples,'maxInterfaceErrorM':max_error,
    'collisionScreening':collision_samples,
    'note':'Exact 0/90/180/270 degree checks evaluate actual Blender driver transforms. Surface overlap checks are a screening aid, not a continuous collision proof.',
    'clearances':{'pistonToBoreRadialM':.063-.06265,'ringToBoreRadialM':.063-.0629,
                  'pinToSmallBushRadialM':.0221-.022,'crankpinToBearingRadialM':.0330-.0325,
                  'mainJournalToBearingRadialM':.0374-.037,
                  'rodBigEndAxialHalfWidthM':.019,'nearestCrankWebInnerFaceM':.035},
    'renderedFramesReviewed':[]}
(ROOT/'verification_working.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
print('ENGINE_BUILD_COMPLETE',json.dumps({'families':len(families),'semanticInstances':len(registry),
      'maxInterfaceErrorM':max_error,'collisionScreening':collision_samples},ensure_ascii=False))
