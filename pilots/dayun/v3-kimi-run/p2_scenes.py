from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import json
import math
import random
from mathutils import Vector
from geo import box, cylinder, mesh, group
from studio import studio, camera, render_frame, render_sequence, metal

ROOT = Path(__file__).resolve().parent
ARGS = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
KIND = ARGS[0] if ARGS else 'bricks'
DRAFT = '--draft' in ARGS
GREY = '--grey' in ARGS
END = 192
FPS = 24
RADIUS = .536
MATS = {}


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def body(obj, mass=1, shape='BOX', moving=False, passive=False):
    print('P2_BODY',obj.name,shape,flush=True)
    activate(obj)
    bpy.ops.rigidbody.object_add()
    print('P2_BODY_ADDED',obj.name,flush=True)
    rb = obj.rigid_body
    rb.type = 'PASSIVE' if passive else 'ACTIVE'
    rb.collision_shape = shape
    rb.mass = mass
    rb.kinematic = moving
    rb.use_margin = True
    rb.collision_margin = .0015 if shape != 'MESH' else .003
    rb.friction = .52
    rb.restitution = .035
    rb.linear_damping = .13
    rb.angular_damping = .18
    rb.use_deactivation = False
    return rb


def fixed_link(a,b,threshold):
    obj = group('Gypsum breakable fixed joint',loc=(a.location+b.location)/2)
    activate(obj)
    bpy.ops.rigidbody.constraint_add()
    constraint = obj.rigid_body_constraint
    constraint.type = 'FIXED'
    constraint.object1 = a
    constraint.object2 = b
    constraint.disable_collisions = True
    constraint.use_breaking = True
    constraint.breaking_threshold = threshold
    return obj


def materials():
    colors = [(0.65,.045,.025),(.035,.27,.48),(.90,.46,.035),(.05,.43,.31),(.45,.14,.47),(.83,.71,.14)]
    return [metal('P2 toy color '+str(i),color,.32,.10) for i,color in enumerate(colors)]


def truck():
    truck = bpy.data.objects['TruckAssembly']
    control = bpy.data.objects['PowertrainControl']
    for name in ['EngineSystem','Gearbox','Clutch','PropellerShaft','InterAxleDrive','FinalDrive_Mid','FinalDrive_Rear']:
        root = bpy.data.objects.get(name)
        if root:
            for obj in root.children_recursive:
                if obj.type == 'MESH':
                    obj.hide_render = True
    verts = [(-1.235,-3.76,.82),(1.235,-3.76,.82),(-1.235,-3.76,2.02),(1.235,-3.76,2.02),
             (-1.10,-3.34,3.84),(1.10,-3.34,3.84),(-1.19,-.48,3.84),(1.19,-.48,3.84),
             (-1.235,-.48,.82),(1.235,-.48,.82)]
    faces = [(0,1,3,2),(0,2,4,6,8),(1,9,7,5,3),(2,3,5,4),(0,8,9,1),
             (4,5,7,6),(8,6,7,9)]
    hull = mesh('P2 animated cab contact hull',verts,faces,None,truck,smooth=False)
    hull.hide_render = True
    hull.display_type = 'WIRE'
    body(hull,shape='CONVEX_HULL',moving=True)
    for side in [-1,1]:
        for axle,y in [('Front',-2.48),('Mid',1.27),('Rear',2.60)]:
            obj = cylinder(f'P2 tire contact {axle} {side}',.536,.36,(side*1.10,y,.536),None,truck,(1,0,0),32)
            obj.hide_render = True
            obj.display_type = 'WIRE'
            body(obj,shape='CYLINDER',moving=True)
    travel = 0.0
    speed_rows = []
    for frame in range(1,END+1):
        t = (frame-1)/FPS
        if KIND == 'disc':
            if t < 2.2:
                speed = 1.53
            elif t < 2.45:
                speed = 1.53+(5.5-1.53)*(t-2.2)/.25
            elif t < 2.65:
                speed = 5.5
            elif t < 4.1:
                q = (t-2.65)/1.45
                speed = 5.5*(1-q*q*(3-2*q))
            else:
                speed = 0.0
            travel += speed/FPS
            speed_rows.append({'frame':frame,'speedMetersPerSecond':speed,'travelMeters':travel})
        else:
            travel = min(t*1.53,9.0)
        truck.location = (0,1.2-travel,0)
        truck.keyframe_insert('location',frame=frame)
        control['wheel_angle'] = travel/RADIUS
        control['engine_angle'] = t*6
        control['clutch_angle'] = t*3
        control['clutch_release'] = 0.0
        for name in ['wheel_angle','engine_angle','clutch_angle','clutch_release']:
            control.keyframe_insert(data_path='["'+name+'"]',frame=frame)
    if KIND == 'disc':
        bpy.context.scene['discImpactProfile'] = 'disc only: 1.53m/s approach, accelerate to 5.5m/s near contact, smooth stop at 4.1s'
        (ROOT/'p2_disc_speed_profile.json').write_text(json.dumps(speed_rows,indent=2),encoding='utf-8')
    return truck


def bricks():
    targets = []
    palette = materials()
    for side in [-1,1]:
        for depth in range(2):
            for layer in range(9):
                loc = (side*1.30,-6.20-depth*.51,.142+layer*.286)
                obj = box(f'Gate tower {side} {depth} {layer}',loc,(.54,.49,.282),palette[(layer+depth*2)%len(palette)],edge=.010)
                body(obj,3.8)
                targets.append(obj)
    central_step = (2.575-.002)/6
    central_height = central_step-.002
    for index in range(6):
        obj = box('Gate central supported stack '+str(index),(0,-6.43,.002+central_height/2+index*central_step),(.66,.60,central_height),palette[(index+2)%len(palette)],edge=.008)
        body(obj,4.5)
        targets.append(obj)
    obj = box('Gate continuous supported lintel',(0,-6.455,2.72),(3.14,1.06,.29),palette[3],edge=.010)
    body(obj,22)
    targets.append(obj)
    return targets,'bumper'


def balls():
    targets = []
    palette = materials()
    rng = random.Random(9217)
    wall_mat = metal('P2 shallow tray blue',(.035,.11,.18),.40,.45)
    for x in [-2.26,2.26]:
        obj = box('Shallow tray side', (x,-7.25,.13),(.16,2.95,.26),wall_mat,edge=.022)
        body(obj,passive=True)
    for y in [-5.815,-8.685]:
        obj = box('Shallow tray end', (0,y,.13),(4.32,.16,.26),wall_mat,edge=.022)
        if y > -7:
            body(obj,3.0)
            targets.append(obj)
        else:
            body(obj,passive=True)
    for row in range(4):
        for col in range(6):
            radius = rng.uniform(.265,.32)
            x = (col-2.5)*.685+rng.uniform(-.016,.016)
            y = -6.24-row*.675+rng.uniform(-.016,.016)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,radius=radius,location=(x,y,radius+.004))
            obj = bpy.context.object
            obj.name = f'P2 ball {row:02d} {col:02d}'
            obj.data.materials.append(palette[(row+col*2)%len(palette)])
            for face in obj.data.polygons:
                face.use_smooth = True
            rb = body(obj,.16,'SPHERE')
            rb.restitution = .64
            rb.friction = .35
            rb.linear_damping = .055
            rb.angular_damping = .065
            targets.append(obj)
    return targets,'wheels'


def clip_polygon(poly,normal,limit):
    result = []
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da = a[0]*normal[0]+a[1]*normal[1]-limit
        db = b[0]*normal[0]+b[1]*normal[1]-limit
        if da <= 0:
            result.append(a)
        if (da < 0) != (db < 0):
            factor = da/(da-db)
            result.append((a[0]+factor*(b[0]-a[0]),a[1]+factor*(b[1]-a[1])))
    return result


def disc():
    rng = random.Random(4061)
    seeds = [(0,0)]
    for radius,count,phase in [(.62,6,.18),(1.23,11,0)]:
        for j in range(count):
            angle = 2*math.pi*j/count+phase
            seeds.append((radius*math.cos(angle)+rng.uniform(-.07,.07),radius*math.sin(angle)+rng.uniform(-.07,.07)))
    circle = [(1.72*math.cos(2*math.pi*j/72),1.72*math.sin(2*math.pi*j/72)) for j in range(72)]
    gypsum = metal('P2 chalk gypsum',(.78,.77,.72),.87,.0)
    targets = []
    cells = []
    center_y = -6.50
    center_z = 1.735
    for index,seed in enumerate(seeds):
        poly = circle
        for other in seeds:
            if seed == other:
                continue
            normal = (other[0]-seed[0],other[1]-seed[1])
            limit = (other[0]**2+other[1]**2-seed[0]**2-seed[1]**2)/2
            poly = clip_polygon(poly,normal,limit)
        area = abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2
        signed = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))
        cx = sum((a[0]+b[0])*(a[0]*b[1]-b[0]*a[1]) for a,b in zip(poly,poly[1:]+poly[:1]))/(3*signed)
        cz = sum((a[1]+b[1])*(a[0]*b[1]-b[0]*a[1]) for a,b in zip(poly,poly[1:]+poly[:1]))/(3*signed)
        poly = [(cx+(x-cx)*.992,cz+(z-cz)*.992) for x,z in poly]
        n = len(poly)
        verts = [(x-cx,side*.12,z-cz) for side in [-1,1] for x,z in poly]
        faces = [tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        faces += [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        obj = mesh(f'Gypsum pre-cut cell {index:02d}',verts,faces,gypsum,bevel=.006,smooth=False)
        obj.location = (cx,center_y,center_z+cz)
        rb = body(obj,max(.2,area*.24*35),'CONVEX_HULL')
        obj['mass_basis'] = 'Art-directed lightweight prop mass, not measured gypsum density or material strength'
        rb.friction = .67
        rb.linear_damping = .10
        rb.angular_damping = .18
        targets.append(obj)
        cells.append((index,seed,poly,obj))
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lowest = 100.0
    for obj in targets:
        evaluated = obj.evaluated_get(depsgraph)
        data = evaluated.to_mesh()
        lowest = min(lowest,min((evaluated.matrix_world @ vertex.co).z for vertex in data.vertices))
        evaluated.to_mesh_clear()
    correction = .0015-lowest
    for obj in targets:
        obj.location.z += correction
    bpy.context.view_layer.update()
    bpy.context.scene['discImpactProfile'] = 'disc only: 1.53m/s approach, accelerate to 5.5m/s near contact, smooth stop at 4.1s'
    (ROOT/'p2_disc_initial_state.json').write_text(json.dumps({
        'minimumMeshZBeforeCorrection':lowest,'translationZ':correction,'targetMinimumMeshZ':.0015,
        'note':'All cells are placed before creating breakable constraints; no gravity drop is used to fracture the disc'
    },indent=2),encoding='utf-8')
    print('DISC_BOTTOM_PLACEMENT',lowest,correction,flush=True)
    links = 0
    for i,(index,seed,poly,obj) in enumerate(cells):
        for other_index,other_seed,other_poly,other in cells[i+1:]:
            near = False
            for a,b in zip(poly,poly[1:]+poly[:1]):
                for c,d in zip(other_poly,other_poly[1:]+other_poly[:1]):
                    if (Vector(a)-Vector(c)).length < .032 or (Vector(a)-Vector(d)).length < .032 or (Vector(b)-Vector(c)).length < .032:
                        near = True
            if near:
                supporting = max(obj.location.z,other.location.z) < 1.40
                fixed_link(obj,other,12 if supporting else 6)
                links += 1
    print('GYPSUM_PRECUT',len(targets),'CONSTRAINTS',links,flush=True)
    return targets,'bumper'


def bounds(obj):
    return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]


def build_scene():
    print('P2_STEP load',flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'truck_systems.blend'))
    scene = bpy.context.scene
    print('P2_STEP frame',flush=True)
    scene.frame_set(1)
    print('P2_STEP clean',flush=True)
    for obj in list(bpy.data.objects):
        if obj.type in ['LIGHT','CAMERA'] or obj.name == 'Studio floor':
            bpy.data.objects.remove(obj,do_unlink=True)
    scene.camera = None
    print('P2_STEP world',flush=True)
    bpy.ops.rigidbody.world_add()
    print('P2_STEP world_ready',flush=True)
    world = scene.rigidbody_world
    world.substeps_per_frame = 20 if KIND == 'disc' else 12
    print('P2_STEP substeps',flush=True)
    world.solver_iterations = 60 if KIND == 'disc' else 50
    print('P2_STEP solver',flush=True)
    world.time_scale = 1
    world.use_split_impulse = True
    print('P2_STEP impulse',flush=True)
    world.point_cache.frame_start = 1
    world.point_cache.frame_end = END
    print('P2_STEP cache_range',flush=True)
    print('P2_STEP cache_disk_deferred_until_saved',flush=True)
    floor_mat = metal('P2 concrete stage',(.10,.12,.145),.65,.06)
    print('P2_STEP floor_mat',flush=True)
    floor = box('P2 ground',(0,0,-.16),(100,100,.32),floor_mat)
    print('P2_STEP floor_mesh',flush=True)
    body(floor,passive=True)
    vehicle = truck()
    targets,contact_source = {'bricks':bricks,'balls':balls,'disc':disc}[KIND]()
    scene.frame_set(1)
    bpy.context.view_layer.update()
    initial = {obj.name:{'location':list(obj.location),'rotation':list(obj.rotation_euler),
                         'bounds':[list(p) for p in bounds(obj)]} for obj in targets}
    (ROOT/f'p2_{KIND}_initial.json').write_text(json.dumps(initial,indent=2),encoding='utf-8')
    studio(scene,(0,-4.4,1.1),8,-.22)
    camera_obj = camera(scene,(12.5,-12.0,6.6),(0,-3.0,1.10),37,16)
    focus = bpy.data.objects['V3 camera focus']
    for frame in range(1,END+1):
        t = (frame-1)/FPS
        q = min(1,max(0,(t-1.5)/6.0))
        q = q*q*(3-2*q)
        target = Vector((0,-3.0-4.0*q,1.10))
        camera_obj.location = target+Vector((12.5,-9.0,5.5))
        camera_obj.rotation_euler = (target-camera_obj.location).to_track_quat('-Z','Y').to_euler()
        camera_obj.data.lens = 37-4*q
        camera_obj.keyframe_insert('location',frame=frame)
        camera_obj.keyframe_insert('rotation_euler',frame=frame)
        camera_obj.data.keyframe_insert('lens',frame=frame)
        focus.location = target
        focus.keyframe_insert('location',frame=frame)
    scene.view_settings.exposure = -.65
    scene.render.fps = FPS
    scene.frame_end = END
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/f'p2_{KIND}.blend'))
    print('P2_STEP embedded_cache_after_native_disk_toggle_failure',flush=True)
    frames = []
    contact_frame = None
    max_speed = 0
    min_z = 100
    for frame in range(1,END+1):
        scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        if frame == 1 or frame % 4 == 0 or frame in [END]:
            for obj in targets:
                evaluated = obj.evaluated_get(depsgraph)
                points = [evaluated.matrix_world @ Vector(p) for p in evaluated.bound_box]
                min_z = min(min_z,min(p.z for p in points))
                if frame > 1:
                    previous = frames[-1]['objects'][obj.name]
                    elapsed = (frame-frames[-1]['frame'])/FPS
                    max_speed = max(max_speed,(evaluated.matrix_world.translation-Vector(previous)).length/elapsed)
            frames.append({'frame':frame,'objects':{obj.name:list(obj.evaluated_get(depsgraph).matrix_world.translation) for obj in targets}})
        bumper_front = vehicle.matrix_world @ Vector((0,-3.76,1.5))
        wheel_front = vehicle.matrix_world @ Vector((0,-3.016,.536))
        probe = wheel_front if contact_source == 'wheels' else bumper_front
        for obj in targets:
            points = bounds(obj)
            front = max(p.y for p in points)
            if probe.y <= front+.004 and probe.y >= min(p.y for p in points)-.1:
                if min(p.x for p in points) <= probe.x+1.3 <= max(p.x for p in points)+1.3:
                    contact_frame = contact_frame or frame
    cache = world.point_cache
    with bpy.context.temp_override(scene=scene,point_cache=cache):
        bpy.ops.ptcache.bake_from_cache()
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/f'p2_{KIND}.blend'))
    report = {'scene':KIND,'frames':END,'fps':FPS,'seed':'fixed per scene','cacheBaked':cache.is_baked,
        'cacheDisk':cache.use_disk_cache,'vehicle':'Animated parent with convex cab and tire contact shapes',
        'targets':'Blender rigid-body solver; no per-target transform animation',
        'gypsum':'Pre-cut convex cells with breakable fixed constraints, not material fracture simulation' if KIND == 'disc' else None,
        'contactProbe':contact_source,'approximateContactFrame':contact_frame,
        'approximateContactSeconds':round((contact_frame-1)/FPS,3) if contact_frame else None,
        'sampledMinimumTargetZ':min_z,'sampledMaximumTargetSpeed':max_speed,
        'note':'Contact timing uses visible-proxy planar bounds; inspect adjacent rendered frames for actual first contact',
        'samples':frames}
    (ROOT/f'p2_{KIND}_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('P2_PHYSICS_COMPLETE',KIND,'contact',contact_frame,'cache',cache.is_baked,'minZ',min_z,flush=True)
    return scene


if '--render' in ARGS:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'p2_{KIND}.blend'))
    scene = bpy.context.scene
else:
    scene = build_scene()
if GREY:
    clay = metal('P2 neutral physics review',(.43,.46,.50),.68,0)
    scene.view_layers[0].material_override = clay
if '--build' not in ARGS:
    prefix = ('draft_' if DRAFT else '')+f'p2_{KIND}'+('_grey' if GREY else '')
    if '--stills' in ARGS:
        for frame in [1,48,64,72,80,96,128,END]:
            render_frame(scene,frame,f'{prefix}_check_{frame:04d}.png',960,540,16,False)
    else:
        render_sequence(scene,prefix+'_frames',1,END,960 if DRAFT else 1920,540 if DRAFT else 1080,
                        16 if DRAFT else 48,3 if DRAFT else 1,not DRAFT)
print('P2_SCENE_COMPLETE',KIND,'draft',DRAFT,'grey',GREY,flush=True)
