from pathlib import Path
import bpy
import bmesh
import json
import math
import sys
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PI = math.pi
RADIUS = 0.54
AXLES = [-2.48, 1.27, 2.60]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in list(bpy.data.materials):
    bpy.data.materials.remove(block)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0


def material(name, color, metallic=0.0, roughness=0.4, coat=0.0, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1.0)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Coat Weight'].default_value = coat
    shader.inputs['Coat Roughness'].default_value = 0.18
    if emission:
        shader.inputs['Emission Color'].default_value = (*color, 1.0)
        shader.inputs['Emission Strength'].default_value = emission
    return mat


red = material('Dayun red | enamel', (0.43, 0.006, 0.012), 0.27, 0.27, 0.4)
red_dark = material('Red | shadow trim', (0.22, 0.005, 0.009), 0.2, 0.31, 0.3)
red_light = material('Red | highlight', (0.62, 0.012, 0.018), 0.25, 0.25, 0.4)
black = material('Graphite | trim', (0.012, 0.017, 0.023), 0.15, 0.40)
rubber = material('Tires | rubber', (0.015, 0.019, 0.022), 0.0, 0.72)
tread_mat = material('Tires | tread', (0.024, 0.028, 0.031), 0.0, 0.83)
glass = material('Glazing | smoked blue', (0.008, 0.021, 0.032), 0.14, 0.18, 0.3)
glass.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .28
glass_soft = material('Glazing | reflection', (0.035, 0.078, 0.10), 0.25, 0.22, 0.3)
chrome = material('Chrome | grille', (0.67, 0.74, 0.80), 0.88, 0.19)
alloy = material('Alloy | wheels', (0.54, 0.60, 0.66), 0.84, 0.24)
steel = material('Steel | chassis', (0.053, 0.067, 0.079), 0.7, 0.39)
engine_blue = material('Engine | enamel', (0.058, 0.15, 0.18), 0.52, 0.34)
silver_dark = material('Steel | satin', (0.25, 0.31, 0.35), 0.78, 0.31)
gold = material('Warm gold | lettering', (0.98, 0.66, 0.17), 0.65, 0.23)
white = material('Ivory | lettering', (0.88, 0.93, 0.94), 0.25, 0.31)
lamp = material('LED | cool white', (0.69, 0.89, 1.0), 0.3, 0.17, 0.3, 1.8)
amber = material('Amber | indicators', (1.0, 0.26, 0.018), 0.2, 0.23, 0.3, 0.45)
tail_red = material('Ruby | tail lamps', (0.68, 0.006, 0.012), 0.25, 0.2, 0.4, 0.4)
seat_mat = material('Interior | fabric', (0.048, 0.058, 0.068), 0.0, 0.88)


def group(name, parent=None, part=None, explode=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.empty_display_size = 0.18
    if parent:
        obj.parent = parent
    if part:
        obj['partType'] = part
    if explode:
        obj['explode'] = [explode[0], explode[2], -explode[1]]
    return obj


truck = group('Dayun_N8E_6x4')
truck['model'] = 'Original stylized N8E 3.0-inspired 6x4 tractor'
truck['units'] = 'meters'
truck['authoringAxes'] = 'Blender Z up, front -Y, axle X; glTF Y up, front +Z'
truck['wheelRadius'] = RADIUS
truck['structure'] = 'Display geometry; simplified non-manufacturing internals'
cab = group('Cab', truck, 'cab', (0, 0.65, 2.05))
doors = {}
for side, label in [(-1, 'L'), (1, 'R')]:
    doors[side] = group(f'Door_{label}', truck, 'door', (side * 1.6, -0.28, 0.38))
engine = group('Engine', truck, 'engine', (0, -1.5, 0.5))
chassis = group('Chassis', truck, 'chassis', (0, 0, 0))


def mesh_obj(name, verts, faces, mat, parent=None, bevel=0.0, smooth=False):
    mesh = bpy.data.meshes.new(name + '_mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    if faces:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if mat:
        mesh.materials.append(mat)
    if parent:
        obj.parent = parent
    for poly in mesh.polygons:
        poly.use_smooth = smooth
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = 'ANGLE'
        mod.harden_normals = True
        normal = obj.modifiers.new('Face weighted normals', 'WEIGHTED_NORMAL')
        normal.keep_sharp = True
        normal.weight = 40
    return obj


def box(name, loc, dims, mat, parent=None, bevel=0.02, rot=None):
    x, y, z = (v / 2 for v in dims)
    verts = [(-x,-y,-z), (-x,-y,z), (-x,y,-z), (-x,y,z),
             (x,-y,-z), (x,-y,z), (x,y,-z), (x,y,z)]
    faces = [(0,4,6,2), (1,3,7,5), (0,1,5,4), (2,6,7,3), (0,2,3,1), (4,5,7,6)]
    obj = mesh_obj(name, verts, faces, mat, parent, bevel, bool(bevel))
    obj.location = loc
    if rot:
        obj.rotation_euler = rot
    return obj


def prism(name, outline, vector, mat, parent=None, bevel=0.01):
    n = len(outline)
    verts = [tuple(p) for p in outline] + [tuple(Vector(p) + Vector(vector)) for p in outline]
    faces = [tuple(range(n-1, -1, -1)), tuple(range(n, n*2))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    return mesh_obj(name, verts, faces, mat, parent, bevel)


def front_y(z):
    return -3.535 + max(0.0, z - 2.26) * 0.34


def front_panel(name, points, mat, parent=cab, offset=-0.012, thickness=0.055, bevel=0.012):
    outline = [(x, front_y(z) + offset, z) for x, z in points]
    return prism(name, outline, (0, thickness, 0), mat, parent, bevel)


def cylinder(name, loc, radius, depth, mat, parent=None, axis=(0,0,1), vertices=32, bevel=0.005):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = loc
    obj.rotation_euler = Vector(axis).to_track_quat('Z', 'Y').to_euler()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    if bevel:
        mod = obj.modifiers.new('Machined edge', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.harden_normals = True
        obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj


def rod(name, start, end, radius, mat, parent=None, vertices=12):
    a, b = Vector(start), Vector(end)
    return cylinder(name, (a+b)/2, radius, (b-a).length, mat, parent, b-a, vertices, 0.0)


def torus(name, loc, major, minor, mat, parent=None, axis=(0,0,1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=48, minor_segments=8)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = loc
    obj.rotation_euler = Vector(axis).to_track_quat('Z', 'Y').to_euler()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def pipe(name, points, radius, mat, parent=None):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 12
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for point, co in zip(spline.bezier_points, points):
        point.co = co
        point.handle_left_type = 'AUTO'
        point.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    return bpy.context.object


font_cn = bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')
font_latin = bpy.data.fonts.load('C:/Windows/Fonts/arialbd.ttf')


def text(name, body, loc, size, mat, parent=None, rotation=(PI/2,0,0), latin=False):
    curve = bpy.data.curves.new(name, 'FONT')
    curve.body = body
    curve.font = font_latin if latin else font_cn
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    curve.size = size
    curve.extrude = 0.0015
    curve.bevel_depth = 0.0006
    curve.bevel_resolution = 2
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.location = loc
    obj.rotation_euler = rotation
    obj.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    return bpy.context.object


def lathe_x(name, profile, mat, parent, segments=64):
    verts = []
    for u, r in profile:
        for j in range(segments):
            angle = 2*PI*j/segments
            verts.append((u, r*math.sin(angle), r*math.cos(angle)))
    faces = []
    for k in range(len(profile)):
        k2 = (k+1) % len(profile)
        for j in range(segments):
            j2 = (j+1) % segments
            faces.append((k*segments+j, k*segments+j2, k2*segments+j2, k2*segments+j))
    return mesh_obj(name, verts, faces, mat, parent, 0.0, True)


def arch(name, side, y, z, inner, outer, width, mat, parent, start=-0.18, end=PI+0.18):
    verts = []
    steps = 40
    for i in range(steps+1):
        a = start + (end-start)*i/steps
        for x, r in [(-width/2, inner), (-width/2, outer), (width/2, inner), (width/2, outer)]:
            verts.append((side*1.12+x, y+r*math.cos(a), z+r*math.sin(a)))
    faces = []
    for i in range(steps):
        n, m = i*4, (i+1)*4
        faces += [(n,m,m+1,n+1), (n+2,n+3,m+3,m+2),
                  (n,n+2,m+2,m), (n+1,m+1,m+3,n+3)]
    faces += [(0,1,3,2), (steps*4,steps*4+2,steps*4+3,steps*4+1)]
    return mesh_obj(name, verts, faces, mat, parent, 0.012, True)


front_panel('Cab front shell', [(-1.10,.84),(1.10,.84),(1.24,1.20),(1.23,2.31),
            (1.15,2.47),(-1.15,2.47),(-1.23,2.31),(-1.24,1.20)], red, bevel=.065)
box('Cab rear wall', (0,-.43,2.28), (2.40,.13,2.24), red, cab, .065)
box('Cab rear upper', (0,-.48,3.45), (2.32,.19,.42), red, cab, .09)
box('Cab floor', (0,-1.89,1.17), (2.33,2.71,.15), black, cab, .045)
roof_outline = [(-1.15,-3.29,3.39),(1.15,-3.29,3.39),(1.15,-3.29,3.56),(-1.15,-3.29,3.56),
                (-1.04,-3.02,3.94),(1.04,-3.02,3.94),(1.15,-.43,3.96),(-1.15,-.43,3.96),
                (-1.22,-.43,3.38),(1.22,-.43,3.38)]
roof_faces = [(0,1,2,3),(3,2,5,4),(4,5,6,7),(7,6,9,8),(8,9,2,0,3),
              (1,9,6,5,2),(0,4,7,8)]
mesh_obj('High roof | aero shell', roof_outline, roof_faces, red, cab, .075, True)
prism('Front roof badge panel', [(-.91,-3.208,3.60),(.91,-3.208,3.60),
      (.86,-3.097,3.79),(-.86,-3.097,3.79)], (0,.024,.015), black, cab, .035)
text('Roof brand | 大运', '大运', (0,-3.254,3.695), .53, gold, cab, (math.atan2(1,.49),0,0))
text('Roof small type', 'N 8 E   ·   6 × 4', (0,-3.106,3.84), .065, white, cab, (math.atan2(1,.49),0,0), True)
prism('Panoramic sun visor', [(-1.19,-3.32,3.47),(1.19,-3.32,3.47),
      (1.20,-3.50,3.34),(-1.20,-3.50,3.34)], (0,.085,.035), black, cab, .035)
for x in [-.90,-.45,0,.45,.90]:
    box('Roof marker', (x,-3.31,3.48), (.115,.085,.035), lamp, cab, .013)

windshield = [(-1.095,-3.46,2.51),(1.095,-3.46,2.51),(1.075,-3.26,3.34),(-1.075,-3.26,3.34)]
prism('Front windshield', windshield, (0,.012,.004), glass, cab, .026)
prism('Windshield soft reflection', [(-1.02,-3.452,2.56),(-.84,-3.452,2.56),
      (-.72,-3.284,3.28),(-.88,-3.284,3.28)], (0,.003,.001), glass_soft, cab, .004)
for side in [-1,1]:
    rod('A pillar', (side*1.17,-3.45,2.39), (side*1.125,-3.23,3.39), .050, red, cab)
    rod('Windshield wiper arm', (side*.70,-3.483,2.53),(side*.40,-3.397,2.79),.013,black,cab)
    rod('Windshield wiper blade', (side*.78,-3.397,2.78),(side*.15,-3.362,2.86),.018,black,cab)
    prism('Front corner sculpted panel', [(side*1.20,-3.49,1.02),(side*1.20,-3.54,2.30),
          (side*1.20,-3.20,2.34),(side*1.20,-3.15,1.28),(side*1.20,-3.04,1.12)],
          (side*.075,0,0), red, cab, .040)
    prism('Front corner upper frame', [(side*1.20,-3.48,2.34),(side*1.20,-3.245,3.39),
          (side*1.20,-3.15,3.36),(side*1.20,-3.205,2.34)], (side*.075,0,0), red, cab, .025)
    box('Side rear cab wall', (side*1.205,-.88,2.11), (.115,.87,1.98), red, cab, .055)
    box('Sleeper upper side', (side*1.19,-.84,3.03), (.12,.83,.70), red, cab, .06)
    box('Sleeper rear fairing', (side*1.235,-.42,2.68), (.12,.22,1.36), red, cab, .045)
    box('Sleeper window gasket', (side*1.258,-.83,2.96), (.025,.57,.49), black, cab, .07)
    box('Sleeper window glass', (side*1.276,-.83,2.96), (.014,.49,.40), glass, cab, .06)
    pipe('Sleeper accent', [(side*1.27,-1.18,2.64),(side*1.28,-.86,2.53),(side*1.27,-.53,2.66)], .013, gold, cab)
    box('Rear cab lower panel', (side*1.19,-.73,1.13), (.15,.59,.20), red, cab, .035)
    arch('Front red wheel arch', side, AXLES[0], RADIUS, .575, .665, .36, red, cab).location.x = side * .06
    for idx in range(3):
        box(f'Entry step {idx+1}', (side*1.13,-1.22,.38+idx*.245), (.39,.59,.09), silver_dark, cab, .018)
        for n in range(6):
            box('Step grip', (side*1.13,-1.45+n*.087,.426+idx*.245), (.33,.023,.012), black, cab, .003)
    box('Step side skirt', (side*1.11,-1.17,.91), (.18,.73,.13), red, cab, .025)

front_panel('Front graphite mask', [(-1.095,1.16),(1.095,1.16),(1.13,2.27),(.99,2.39),(-.99,2.39),(-1.13,2.27)],
            black, offset=-.050, thickness=.046, bevel=.035)
front_panel('Brand red brow', [(-.92,2.31),(.92,2.31),(.85,2.47),(-.85,2.47)], red_dark, offset=-.088, bevel=.017)
text('Front brand | 大运', '大运', (0,-3.640,2.384), .29, chrome, cab)
text('Front DAYUN', 'D A Y U N', (0,-3.622,2.239), .065, chrome, cab, latin=True)
for i, (low, high, half) in enumerate([(1.21,1.45,.86),(1.51,1.75,.97),(1.81,2.05,1.045),(2.10,2.18,1.055)]):
    front_panel(f'Grille recessed opening {i+1}', [(-half,low),(half,low),(half+.035,high),(-half-.035,high)],
                rubber, offset=-.102-i*.002, thickness=.022, bevel=.012)
    for row in range(3):
        z = low+.035+row*(high-low-.06)/2
        rod('Grille fine horizontal', (-half+.035,front_y(z)-.119,z),(half-.035,front_y(z)-.119,z),.0045, black,cab,6)
    for j in range(-int(half/.075),int(half/.075)+1):
        x = j*.075
        rod('Grille fine vertical', (x,front_y(low)-.116,low+.01),(x,front_y(high)-.116,high-.01),.0045,black,cab,6)
    verts, faces = [], []
    for j in range(25):
        x = -half + 2*half*j/24
        z = high+.012+.065*(abs(x)/half)**1.8
        y = front_y(z)-.143
        k = len(verts)
        verts += [(x-half/24,y,z+.015),(x+half/24,y,z+.015),
                  (x+half/24,y-.028,z-.025),(x-half/24,y-.028,z-.025)]
        faces.append((k,k+1,k+2,k+3))
    mesh_obj(f'Chrome sweeping grille rail {i+1}', verts, faces, chrome, cab)
front_panel('Shield lower chrome lip', [(-.86,1.19),(.86,1.19),(.76,1.115),(-.76,1.115)], chrome, offset=-.142, thickness=.025, bevel=.014)
front_panel('Lower bumper', [(-1.12,.74),(1.12,.74),(1.25,.93),(1.17,1.095),(-1.17,1.095),(-1.25,.93)], red, offset=-.035, thickness=.22, bevel=.045)
front_panel('Bumper center intake', [(-.58,.82),(.58,.82),(.61,.97),(-.61,.97)], black, offset=-.074, thickness=.028, bevel=.018)
front_panel('Front plate', [(-.255,.80),(.255,.80),(.255,.90),(-.255,.90)], red_dark, offset=-.111, thickness=.012, bevel=.006)
text('Plate lettering', '大运 · N8E', (0,-3.666,.85), .063, white, cab)
for side in [-1,1]:
    pts = [(side*.90,1.245),(side*1.19,1.27),(side*1.205,1.58),(side*1.08,1.67),(side*.92,1.59)]
    front_panel('Headlamp black surround', pts, black, offset=-.065, thickness=.07, bevel=.027)
    pts = [(side*.935,1.30),(side*1.155,1.31),(side*1.166,1.535),(side*1.075,1.60),(side*.95,1.545)]
    front_panel('Headlamp silver lens', pts, alloy, offset=-.103, thickness=.025, bevel=.018)
    for x, z, r in [(side*1.015,1.435,.064),(side*1.125,1.448,.041)]:
        cylinder('Projector chrome cup', (x,-3.642,z),r,.032,chrome,cab,(0,-1,0),32,.003)
        cylinder('Projector optical lens', (x,-3.665,z),r*.74,.012,lamp,cab,(0,-1,0),32,.003)
    box('Amber turn signal', (side*1.145,-3.626,1.566), (.09,.045,.060), amber, cab,.012)
    pipe('LED daytime running light', [(side*.965,-3.641,1.58),(side*1.067,-3.641,1.615),(side*1.163,-3.627,1.558)], .013, lamp, cab)
    box('Fog light recess', (side*1.01,-3.588,1.017), (.35,.12,.155), black,cab,.029)
    box('Fog light strip', (side*1.01,-3.660,1.028), (.25,.025,.048), lamp,cab,.012)
    box('Corner red cheek', (side*1.226,-3.44,1.43), (.072,.25,.62), red,cab,.042)
    cylinder('Tow pin cap', (side*.77,-3.615,.865), .035,.022,black,cab,(0,-1,0),20,.004)

for side, door in doors.items():
    label = 'L' if side < 0 else 'R'
    lower = [(side*1.257,-3.19,1.27),(side*1.273,-2.93,1.185),(side*1.275,-1.30,1.185),
             (side*1.258,-1.075,1.44),(side*1.24,-1.075,2.34),(side*1.232,-3.21,2.34)]
    prism(f'Door {label} outer panel', lower, (side*.052,0,0),red,door,.035)
    win = [(side*1.274,-3.125,2.405),(side*1.241,-2.935,3.255),
           (side*1.254,-1.205,3.255),(side*1.267,-1.135,2.405)]
    prism(f'Door {label} glass',win,(side*.014,0,0),glass,door,.024)
    frame = [(-3.19,2.34),(-3.015,3.325),(-1.13,3.325),(-1.005,2.34)]
    for i in range(len(frame)):
        y1,z1 = frame[i]
        y2,z2 = frame[(i+1)%len(frame)]
        rod(f'Door {label} window frame', (side*1.275,y1,z1),(side*1.275,y2,z2),.048,red,door,8)
    rod('Door quarter divider',(side*1.299,-2.81,2.42),(side*1.286,-2.77,3.23),.023,black,door,8)
    pipe('Door lower bright swoosh', [(side*1.321,-2.97,1.92),(side*1.329,-2.39,1.79),(side*1.323,-1.40,1.92)],.011,chrome,door)
    pipe('Door gold feather', [(side*1.323,-2.78,1.95),(side*1.331,-2.33,1.86),(side*1.325,-1.65,1.93)],.009,gold,door)
    box('Door handle recess',(side*1.319,-1.38,2.21),(.029,.255,.103),red_dark,door,.018)
    box('Door handle',(side*1.340,-1.40,2.225),(.035,.18,.043),black,door,.012)
    box('Door key insert',(side*1.362,-1.32,2.224),(.009,.025,.015),chrome,door,.003)
    box('Side indicator',(side*1.325,-1.18,1.37),(.024,.105,.047),amber,door,.009)
    text(f'Door {label} N8E', 'N8E 3.0', (side*1.326,-2.43,1.53), .098,white,door,(PI/2,0,side*PI/2),True)
    rod('Mirror upper bracket',(side*1.245,-3.04,3.19),(side*1.54,-3.14,3.18),.025,black,door)
    rod('Mirror lower bracket',(side*1.275,-3.06,2.64),(side*1.54,-3.14,2.72),.025,black,door)
    box('Mirror main housing',(side*1.555,-3.13,2.99),(.17,.18,.43),black,door,.055)
    box('Mirror main reflective glass',(side*1.555,-3.031,2.99),(.135,.015,.36),chrome,door,.035)
    box('Mirror lower housing',(side*1.53,-3.105,2.665),(.16,.16,.18),black,door,.035)
    box('Mirror lower glass',(side*1.53,-3.018,2.665),(.125,.012,.13),chrome,door,.026)

for side in [-1,1]:
    box('Seat cushion',(side*.57,-1.63,1.58),(.63,.66,.18),seat_mat,cab,.08)
    box('Seat back',(side*.57,-1.32,1.98),(.62,.18,.76),seat_mat,cab,.09,(-.12,0,0))
    box('Seat headrest',(side*.57,-1.29,2.42),(.38,.18,.22),black,cab,.05)
    box('Seat red center',(side*.57,-1.417,2.04),(.32,.022,.46),red_dark,cab,.025)
box('Dashboard',(0,-2.99,2.28),(2.10,.43,.24),black,cab,.085)
box('Dash display',(-.05,-2.737,2.35),(.29,.035,.16),glass_soft,cab,.016)
rod('Steering column',(-.57,-2.78,2.20),(-.57,-2.55,2.39),.038,black,cab)
torus('Steering wheel',(-.57,-2.54,2.40),.19,.019,black,cab,(0,-.8,.6))
rod('Steering spoke',(-.74,-2.54,2.40),(-.40,-2.54,2.40),.014,silver_dark,cab)

for side in [-1,1]:
    box('Main chassis rail',(side*.76,.0,1.005),(.17,6.61,.245),steel,chassis,.022)
    box('Chassis rail upper flange',(side*.76,.0,1.142),(.23,6.60,.035),silver_dark,chassis,.007)
for y in [-3.10,-2.0,-.90,.1,1.0,1.93,2.90,3.23]:
    box('Frame crossmember',(0,y,1.005),(1.49,.095,.16),steel,chassis,.014)
box('Rear deck',(0,1.86,1.205),(1.76,2.96,.095),black,chassis,.025)
for y in [.54+i*.17 for i in range(16)]:
    box('Deck grip',(0,y,1.259),(1.49,.025,.013),silver_dark,chassis,.003)
box('Rear catwalk',(0,-.04,1.19),(1.74,.63,.09),silver_dark,chassis,.025)
for x in [-.66,-.44,-.22,0,.22,.44,.66]:
    box('Catwalk grip',(x,-.04,1.245),(.04,.52,.016),black,chassis,.005)
for side in [-1,1]:
    box('Fifth wheel support',(side*.38,1.48,1.31),(.17,.79,.19),steel,chassis,.025)
coupler = [(-.62,-.44),(.62,-.44),(.62,.32),(.25,.60),(.11,.60),(.09,.20),(-.09,.20),(-.11,.60),(-.25,.60),(-.62,.32)]
prism('Fifth wheel | slotted coupling',[(x,y+1.47,1.45) for x,y in coupler],(0,0,.11),black,chassis,.032)
cylinder('Coupler pivot',(0,1.40,1.515),.095,.09,silver_dark,chassis,(0,0,1),32,.01)
box('Rear light bar',(0,3.35,.99),(2.16,.12,.18),black,chassis,.025)
for side in [-1,1]:
    box('Rear lamp',(side*.90,3.421,1.00),(.33,.035,.115),tail_red,chassis,.012)
    box('Rear white lamp',(side*.63,3.422,1.00),(.13,.035,.105),lamp,chassis,.009)
    box('Rear underrun upright',(side*.88,3.31,.65),(.065,.085,.58),steel,chassis,.01)
box('Rear underrun protection',(0,3.36,.39),(2.20,.10,.13),silver_dark,chassis,.017)
box('Front under bumper beam',(0,-3.32,.60),(1.79,.16,.14),steel,chassis,.02)

box('Fuel tank | 800L visual approximation',(1.045,.20,.77),(.54,1.43,.67),alloy,chassis,.095)
for y in [-.31,.69]:
    box('Fuel tank retaining strap',(1.050,y,.77),(.565,.065,.69),steel,chassis,.025)
cylinder('Fuel filler cap',(1.09,-.10,1.123),.083,.040,black,chassis,(0,0,1),32,.008)
box('Fuel step',(1.085,.20,.393),(.55,1.27,.06),silver_dark,chassis,.017)
box('Battery box',(-1.045,.16,.80),(.51,1.08,.55),silver_dark,chassis,.055)
for z in [.64,.72,.80,.88,.96]:
    box('Battery ventilation',(-1.307,.16,z),(.016,.77,.021),black,chassis,.003)
box('Battery latch',(-1.327,-.18,.85),(.025,.085,.12),chrome,chassis,.008)
box('Rear equipment box',(-1.01,1.06,.83),(.36,.51,.40),black,chassis,.03)

for y in AXLES:
    cylinder('Axle housing',(0,y,.55),.092,2.16,steel,chassis,(1,0,0),24,.008)
    cylinder('Differential casing',(0,y,.55),.22,.42,steel,chassis,(1,0,0),32,.025)
    for side in [-1,1]:
        for layer in range(3):
            box('Leaf spring',(side*.70,y,.79+layer*.029),(.105,.96-layer*.14,.025),silver_dark,chassis,.008)
        cylinder('Suspension damper',(side*.72,y-.31,.86),.041,.43,black,chassis,(0,0,1),20,.007)
        rod('Suspension link',(side*.65,y-.40,.91),(side*.65,y+.37,.63),.024,steel,chassis)
for y1,y2 in [(-1.18,.98),(1.27,2.60)]:
    rod('Propeller shaft',(0,y1,.75),(0,y2,.60),.060,silver_dark,chassis,24)
for side in [-1,1]:
    for y in AXLES[1:]:
        arch('Rear tandem mudguard',side,y,RADIUS,.581,.638,.49,black,chassis,-.05,PI+.05)
        box('Rear mudflap',(side*1.12,y+.57,.49),(.49,.045,.64),rubber,chassis,.012)
        box('Mudflap reflective strip',(side*1.12,y+.596,.30),(.39,.012,.042),white,chassis,.003)

box('Engine block',(0,-1.91,1.42),(1.00,1.43,.70),engine_blue,engine,.065)
box('Engine sump',(0,-1.88,.986),(.72,1.03,.22),black,engine,.05)
box('Cylinder head',(0,-1.94,1.835),(.94,1.35,.19),silver_dark,engine,.035)
for i in range(6):
    y=-2.48+i*.207
    box('Six cylinder head cover',(0,y,1.973),(.59,.16,.105),alloy,engine,.028)
    pipe('Injector line',[(.15,y,1.96),(.40,y,1.87),(.49,y,1.62)],.014,chrome,engine)
    box('Engine side rib',(-.512,y,1.42),(.032,.045,.44),silver_dark,engine,.005)
box('Engine front cover',(0,-2.67,1.42),(.80,.10,.58),alloy,engine,.045)
cylinder('Engine front pulley',(0,-2.754,1.33),.185,.075,black,engine,(0,-1,0),32,.007)
cylinder('Turbo charger',(.56,-1.31,1.54),.204,.22,alloy,engine,(1,0,0),40,.018)
pipe('Turbo intake pipe',[(.61,-1.29,1.56),(.79,-.99,1.65),(.67,-.72,1.90)],.088,black,engine)
box('Transmission',(0,-.78,1.05),(.65,.90,.51),silver_dark,engine,.10)
for y in [-1.1,-.96,-.82,-.68,-.54]:
    box('Gearbox cooling rib',(0,y,1.07),(.71,.027,.40),alloy,engine,.008)
rod('Engine exhaust',(.49,-1.19,1.20),(.58,-.35,1.20),.061,silver_dark,engine)

wheel_records = []
for axle_index, y in enumerate(AXLES):
    placements = [-1.10,1.10] if axle_index == 0 else [-1.175,-.825,.825,1.175]
    for x in placements:
        side = -1 if x < 0 else 1
        label = ('F' if axle_index == 0 else ('M' if axle_index == 1 else 'R'))
        label += ('L' if side < 0 else 'R') + ('' if axle_index == 0 else ('O' if abs(x)>1 else 'I'))
        pivot = group('Wheel_'+label, truck, 'wheel', (side*(.92 if axle_index==0 else (1.10 if abs(x)>1 else .59)),0,.055))
        pivot.location = (x,y,RADIUS)
        pivot['spinAxis'] = [1,0,0]
        pivot['radius'] = RADIUS
        pivot['axleIndex'] = axle_index
        pivot['side'] = side
        pivot['nominalCenterBlender'] = [x,y,RADIUS]
        width = .335 if axle_index==0 else .302
        profile = [(-width/2,.292),(-width/2,.424),(-width*.47,.483),(-width*.32,.519),
                   (0,.529),(width*.32,.519),(width*.47,.483),(width/2,.424),(width/2,.292),
                   (width*.34,.279),(-width*.34,.279)]
        lathe_x('Tire carcass '+label,profile,rubber,pivot)
        for face in [-1,1]:
            torus('Sidewall bead', (face*width/2,0,0),.307,.009,rubber,pivot,(1,0,0))
            torus('Sidewall molded ridge', (face*(width/2+.001),0,0),.439,.006,tread_mat,pivot,(1,0,0))
        verts, faces = [], []
        for j in range(48):
            a = 2*PI*j/48
            for band in [-1,0,1]:
                cx = band*.102
                cy, cz = 0, .532
                if band:
                    a2 = a + (.016 if band<0 else -.016)
                else:
                    a2 = a
                dims = (.091,.040,.016)
                base = [(-dims[0]/2,-dims[1]/2,-dims[2]/2),(-dims[0]/2,-dims[1]/2,dims[2]/2),
                        (-dims[0]/2,dims[1]/2,-dims[2]/2),(-dims[0]/2,dims[1]/2,dims[2]/2),
                        (dims[0]/2,-dims[1]/2,-dims[2]/2),(dims[0]/2,-dims[1]/2,dims[2]/2),
                        (dims[0]/2,dims[1]/2,-dims[2]/2),(dims[0]/2,dims[1]/2,dims[2]/2)]
                k=len(verts)
                for vx,vy,vz in base:
                    vy,vz=vy,vz+cz
                    yy=vy*math.cos(a2)-vz*math.sin(a2)
                    zz=vy*math.sin(a2)+vz*math.cos(a2)
                    verts.append((cx+vx,yy,zz))
                faces += [tuple(k+i for i in f) for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]]
        mesh_obj('Chevron tread blocks '+label,verts,faces,tread_mat,pivot)
        out = side*(width/2+.008)
        rim_profile = [(out-.018*side,.306),(out,.291),(out+.008*side,.268),
                       (out+.013*side,.237),(out-.038*side,.221),(out-.060*side,.159),
                       (out-.028*side,.110),(out-.105*side,.105),(out-.099*side,.285)]
        lathe_x('Pressed alloy rim '+label,rim_profile,alloy,pivot)
        cylinder('Dark rim ventilation well',(out-.030*side,0,0),.228,.014,black,pivot,(1,0,0),48,.002)
        torus('Polished rim lip',(out+.006*side,0,0),.276,.014,chrome,pivot,(1,0,0))
        for j in range(10):
            a=2*PI*j/10
            yy,zz=.194*math.sin(a),.194*math.cos(a)
            cylinder('Wheel ventilation recess',(out-.016*side,yy,zz),.025,.010,rubber,pivot,(1,0,0),16,.001)
            torus('Ventilation hole edge',(out-.008*side,yy,zz),.025,.004,alloy,pivot,(1,0,0))
        cylinder('Wheel hub',(out+.003*side,0,0),.110,.073,silver_dark,pivot,(1,0,0),32,.008)
        cylinder('Hub cap',(out+.046*side,0,0),.077,.025,chrome,pivot,(1,0,0),32,.008)
        for j in range(8):
            a=2*PI*j/8
            cylinder('Wheel lug nut',(out+.029*side,.126*math.sin(a),.126*math.cos(a)),.018,.027,chrome,pivot,(1,0,0),6,.003)
        wheel_records.append({'name':pivot.name,'center':[x,y,RADIUS],'radius':RADIUS,'axleIndex':axle_index})

bpy.context.view_layer.update()
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1500
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
world = bpy.data.worlds.new('Studio world')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.32,.38,.47,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .32
floor_mat = material('Studio floor',(.22,.26,.30),.08,.54)
box('Studio ground',(0,0,-.075),(200,200,.10),floor_mat,None,.0)


def area(name, loc, energy, color, size, target):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=energy
    data.color=color
    data.shape='DISK'
    data.size=size
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.location=loc
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


area('Key softbox',(1,-6,10),1700,(1.0,.90,.82),7,(0,-.6,1.4))
area('Fill softbox',(7,-1,5),850,(.75,.85,1.0),6,(0,-.8,1.6))
area('Rim softbox',(-5,4,8),1700,(.90,.95,1.0),5,(0,0,1.7))
area('Front softbox',(-2,-8,4),550,(1,1,1),5,(0,-2,2))
cam_data=bpy.data.cameras.new('Camera')
cam=bpy.data.objects.new('Camera',cam_data)
bpy.context.collection.objects.link(cam)
scene.camera=cam
cam.data.lens=53


def aim(location,target,lens=53):
    cam.location=location
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=lens


def render(filename, location, target, lens=53):
    aim(location,target,lens)
    scene.render.filepath=str(ROOT/filename)
    bpy.ops.render.render(write_still=True)


aim((10,-13,7.0),(0,-.05,1.77))
bpy.ops.object.select_all(action='DESELECT')
truck.select_set(True)
bpy.context.view_layer.objects.active=truck
for screen in bpy.data.screens:
    for space_area in screen.areas:
        if space_area.type=='VIEW_3D':
            space_area.spaces.active.region_3d.view_perspective='CAMERA'
            space_area.spaces.active.clip_end=300
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'dayun_n8e.blend'))
for obj in truck.children_recursive:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'dayun_n8e.glb'),export_format='GLB',
    use_selection=True,export_apply=True,export_extras=True,export_animations=False,
    export_cameras=False,export_lights=False,export_yup=True)
manifest={'title':'大运 N8E 风格 6×4 高顶牵引车','kind':'Original procedural display model',
    'units':'meters','blenderAxes':{'up':'Z','front':'-Y','wheelSpin':'X'},
    'gltfAxes':{'up':'Y','front':'+Z','wheelSpin':'X'},'wheelRadius':RADIUS,
    'axlesBlenderY':AXLES,'wheels':wheel_records,
    'parts':[{'name':o.name,'type':o.get('partType'),'explodeGltf':list(o.get('explode',[]))}
             for o in [cab,*doors.values(),engine,chassis]],
    'objects':len(bpy.data.objects),'meshObjects':sum(o.type=='MESH' for o in bpy.data.objects),
    'simplifications':['Exterior proportions are artistic, not OEM CAD','Engine and cabin interior are simplified',
    'No trailer or physics simulation','Single 800L-style tank plus battery box'],
    'source':'build_truck.py','reference':'https://www.dayungroup.com/product-productdetail-27-229'}
(ROOT/'asset_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
if '--no-render' not in sys.argv:
    render('preview_front_side.png',(10,-13,7.0),(0,-.05,1.77))
    if '--extras' in sys.argv:
        for obj in [cab,*doors.values(),engine]:
            x,y,z=obj['explode']
            obj.location=(x,-z,y)
        for obj in bpy.data.objects:
            if obj.get('partType')=='wheel':
                x,y,z=obj['explode']
                obj.location += Vector((x,-z,y))
        scene.cycles.samples=24
        render('preview_exploded.png',(11,-15,10),(0,-.05,2.75),52)
        for obj in [cab,*doors.values(),engine]:
            obj.location=(0,0,0)
        for obj in bpy.data.objects:
            if obj.get('partType')=='wheel':
                obj.location=obj['nominalCenterBlender']
        render('preview_rear.png',(-10,13,6.4),(0,.10,1.62))
print('BUILD_COMPLETE', json.dumps({'wheels':len(wheel_records),'meshes':manifest['meshObjects'],'root':str(ROOT)},ensure_ascii=False))
