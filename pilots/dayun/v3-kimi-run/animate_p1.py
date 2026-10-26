from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import json
import math
from mathutils import Vector, Matrix
from studio import studio, camera, render_sequence, render_frame, area, palette
from geo import box, group

ROOT = Path(__file__).resolve().parent
ARGS = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
MODE = ARGS[0] if ARGS else 'explosion'
DRAFT = '--draft' in ARGS
FPS = 24


def load_scene():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'truck_systems.blend'))
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT' or obj.name == 'Studio floor':
            bpy.data.objects.remove(obj,do_unlink=True)
    scene.frame_set(1)
    return scene


def smooth(t,a,b):
    if t <= a: return 0.0
    if t >= b: return 1.0
    x = (t-a)/(b-a)
    return x*x*(3-2*x)


def object_side(obj):
    current = obj
    while current:
        if 'side' in current:
            return current['side']
        current = current.parent
    return 1


def cylinder_index(obj):
    current = obj
    while current:
        for prefix in ['PistonMotion_', 'RodMotion_', 'CylinderLiner_']:
            if current.name.startswith(prefix):
                return int(current.name[len(prefix):].split('.')[0].split('_')[0])
        if '_C' in current.name and current.name.rsplit('_C',1)[1][:2].isdigit():
            return int(current.name.rsplit('_C',1)[1][:2])
        if current.name.startswith('FirstDetachedRodParts') or current.name.endswith('_01'):
            return 1
        current = current.parent
    return 0


def entity_offset(entity,obj):
    family = entity['family']
    side = object_side(obj)
    name = obj.name
    index = cylinder_index(obj)
    spread = (index-3.5)*.16 if index else 0
    if name.startswith('PistonMotion_'):
        return Vector((spread,0,.24))
    if name.startswith('RodMotion_'):
        return Vector((spread,0,.08))
    if name.startswith('High roof'):
        return Vector((0,.18,.60))
    if name.startswith('Cab rear wall'):
        return Vector((0,.55,.12))
    if name.startswith('Cab floor'):
        return Vector((0,0,-.15))
    if name.startswith('Cab front shell'):
        return Vector((0,-.55,.18))
    if name.startswith('Side rear cab wall'):
        return Vector((side*.60,.20,.25))
    if name.startswith('Sleeper'):
        return Vector((side*.42,.30,.30))
    if name.startswith('Front corner'):
        return Vector((side*.55,-.30,.18))
    if name.startswith('Panoramic sun visor'):
        return Vector((0,-.50,.65))
    if name.startswith('Front graphite mask'):
        return Vector((0,-.75,.10))
    if name.startswith('Front red wheel arch'):
        return Vector((side*.60,-.10,-.10))
    if name.startswith('Roof brand'):
        return Vector((0,.18,.63))
    wheel = {
        'tire':(.80,0,0),'rim':(1.16,0,0),'wheel_nut':(1.55,0,0),'wheel_hub_stud':(.20,0,0),
        'rotating_hub':(.22,0,0),'brake_drum':(.62,0,0),'brake_backing':(-.24,0,0),
        'tapered_hub_bearing':(0,0,0),'tapered_bearing_inner_race':(.35,0,0),
        'tapered_bearing_outer_race':(-.14,0,0),'tapered_bearing_cage':(.39,0,0),
        'tapered_bearing_roller':(.42,0,0),'brake_wheel_cylinder':(0,0,.17),
        's_cam':(0,0,-.16),'s_cam_shaft':(0,0,-.20),'brake_air_chamber':(0,-.15,-.09),
        'slack_adjuster':(0,-.13,-.04),'brake_return_spring':(0,0,.12),
        'wheel_cylinder_piston':(0,0,.17),'wheel_cylinder_dust_seal':(0,0,.17),
    }
    if family in ['brake_shoe','brake_friction_lining']:
        sign = 1 if obj.data.vertices and obj.data.vertices[0].co.y >= 0 else -1
        z = .10 if family == 'brake_friction_lining' else 0
        return Vector((0,sign*.14,sign*.10+z))
    if family in wheel:
        x,y,z = wheel[family]
        return Vector((x*side,y,z))
    values = {
        'piston':(0,0,.03),'piston_pin':(.18,0,0),'compression_ring_top':(0,0,.54),
        'compression_ring_second':(0,0,.45),'oil_control_ring':(0,0,.36),'oil_scraper_rail':(0,0,.36),
        'connecting_rod_body':(0,0,0),'small_end_bush':(.17,0,0),
        'rod_bearing_upper':(0,0,.11),'rod_bearing_lower':(0,0,-.10),
        'connecting_rod_cap':(0,0,-.19),'rod_cap_bolt':(0,0,-.27),
        'cylinder_liner':(spread,.38,.16),'crankshaft':(0,-.43,0),'flywheel':(.16,-.43,0),
        'flywheel_ring_gear':(.29,-.43,0),'main_bearing_cap':(0,0,-.14),
        'main_bearing_upper':(0,0,.14),'main_bearing_lower':(0,0,-.07),'main_bearing_bolt':(0,0,-.23),
        'gear':(0,.08,0),'clutch_friction_disc':(0,.20,0),'clutch_pressure_plate':(0,.40,0),
        'clutch_release_bearing':(0,.58,0),'gearbox_service_cover':(-.58,0,.15),
        'drive_shaft_assembly':(0,.18,0),'universal_joint':(0,.10,0),
        'gearbox_shaft':(0,0,.12),'gearbox_bearing':(0,0,.15),'synchronizer_ring':(0,.16,0),
        'shift_fork':(0,0,.20),'gearbox_housing':(0,0,-.13),
        'differential_cover':(-.46,0,.08),'differential_carrier':(.30,0,.05),
        'crown_bolt':(.44,0,.06),'half_shaft':(side*.46,0,0),'side_bearing':(side*.28,0,0),
        'differential_planet_gear':(0,0,.16),'differential_housing':(-.16,0,-.10),
        'cab_body_panel':(side*.32,0,.18),'door_outer_panel':(side*.48,-.12,.18),
        'cab_glazing':(side*.62,-.10,.32),'mirror_assembly':(side*.80,0,.30),
        'door_frame':(side*.52,0,.18),'door_handle':(side*.65,-.12,0),
        'headlamp_assembly':(side*.35,-.60,.15),'front_grille_assembly':(0,-.88,.12),
        'cab_entry_step':(side*.48,0,-.10),'frame_crossmember':(0,0,-.08),
        'fuel_tank':(.60,0,0),'fuel_tank_strap':(.78,0,0),'fuel_filler':(.86,0,.08),
        'fuel_tank_step':(.74,0,-.08),'battery_modules':(-.60,0,.10),
        'air_reservoirs':(0,.50,0),'radiator_and_fan':(0,-.70,.08),
        'cooling_fan':(0,-.30,0),'camshaft':(0,.15,.67),
        'cylinder_head_cover':(0,.25,.92),'cylinder_head_and_valvetrain':(0,0,0),
        'poppet_valve':(0,0,.43),'valvetrain_component':(0,0,.43),
        'camshaft_component':(0,0,0),'leaf_spring_pack':(side*.40,0,-.15),
        'leaf_spring':(0,0,-.04),'leaf_spring_eye':(0,0,-.04),
        'steering_knuckle':(side*.28,0,0),'front_steer_axle':(0,-.30,0),
        'fifth_wheel':(0,.30,.32),'rear_mudguard':(side*.40,0,.14),
        'suspension_link':(side*.32,0,-.12),'radiator_component':(0,-.10,0),
        'cooling_fan_blade':(0,-.18,.05),'air_tank_component':(0,.16,0),
        'battery_component':(-.20,0,.10),'exhaust_component':(-.45,0,0),
        'clutch_diaphragm':(0,.24,0),'inter_axle_tube':(0,.14,0),
        'universal_joint_cross':(0,.08,.04),'universal_joint_bearing_cap':(0,.06,.04),
        'universal_joint_yoke':(0,.06,.04),'seat_suspension':(side*.50,.20,.32),
        'seat_component':(side*.60,.18,.65),'dashboard_component':(0,-.65,.52),
        'steering_control':(-.55,-.70,.62),'head_cover_fastener':(0,.25,.99),
        'vehicle_badge':(0,-.94,.17),'rear_lamp':(0,.24,.08),
    }
    if family == 'piston_circlip':
        return Vector((.15 if obj.location.x >= 0 else -.15,0,0))
    if name.startswith('Cylinder head deck'):
        return Vector((0,.12,.28))
    if family in values:
        return Vector(values[family])
    return Vector((0,0,0))


def driver_save(obj):
    saved = []
    if not obj.animation_data:
        return saved
    for curve in obj.animation_data.drivers:
        if curve.data_path != 'location':
            continue
        variables = []
        for variable in curve.driver.variables:
            target = variable.targets[0]
            variables.append((variable.name,target.id,target.data_path))
        saved.append((obj,curve.array_index,curve.driver.expression,variables))
    return saved


def prepare_explosion():
    entities = json.loads((ROOT/'vehicle_entities.json').read_text(encoding='utf-8'))['entities']
    prepared = []
    detached = []
    for entity in entities:
        obj = bpy.data.objects.get(entity['id'])
        if obj is None:
            continue
        saved = driver_save(obj)
        for item in saved:
            obj.driver_remove('location',item[1])
        detached.extend(saved)
        base = obj.matrix_local.copy()
        offset = entity_offset(entity,obj)
        prepared.append({'object':obj,'entity':entity,'base':base,'offset':offset})
        obj['explodeMatrix'] = [list(row) for row in (Matrix.Translation(offset) @ base)]
    groups = []
    def add(name,offset):
        obj = bpy.data.objects.get(name)
        if obj:
            groups.append({'object':obj,'base':obj.matrix_local.copy(),'offset':Vector(offset)})
    add('Cab',(-1.70,.70,1.25))
    add('Door_L',(-1.65,-.05,.75)); add('Door_R',(.10,-.35,.65))
    add('EngineSystem',(4.20,-3.35,1.00)); add('Gearbox',(2.65,.25,1.05))
    add('RadiatorAndFan',(-1.20,-1.55,.25)); add('AirReservoirs',(-1.20,1.10,.20))
    add('BatteryModules',(-1.20,-.40,.45)); add('ExhaustComponents',(-1.80,1.80,.40))
    add('Clutch',(2.40,-2.15,1.30)); add('PropellerShaft',(2.00,.10,.80))
    add('InterAxleDrive',(2.10,.80,.90))
    add('FinalDrive_Mid',(2.10,1.60,1.05)); add('FinalDrive_Rear',(-2.20,2.00,1.05))
    add('FrontSteeringAxle',(-1.10,-.50,.05))
    add('WheelEnd_R',(2.0,-.65,.20)); add('Front_R',(2.0,-.65,.20))
    add('FirstDetachedRodParts',(-.40,-.05,.15))
    for obj in bpy.data.objects:
        if obj.name.startswith(('WheelEnd_','Front_L','Mid_','Rear_')) and obj.type == 'EMPTY' and obj.parent and obj.parent.name == 'Dayun_N8E_6x4' and obj not in [g['object'] for g in groups]:
            side = obj.get('side',-1 if obj.location.x < 0 else 1)
            y = -.10 if obj.location.y < 0 else (.30 if obj.location.y < 2 else .75)
            add(obj.name,(side*1.60,y,.40))
    grouped = {item['object']:item for item in groups}
    for item in prepared:
        if item['object'] in grouped:
            item['groupOffset'] = grouped[item['object']]['offset'].copy()
            combined = item['offset'] + item['groupOffset']
            item['object']['explodeMatrix'] = [list(row) for row in (Matrix.Translation(combined) @ item['base'])]
    return prepared,groups,detached


def bake_explosion(scene,prepared,groups,detached):
    control = bpy.data.objects['PowertrainControl']
    truck = bpy.data.objects['TruckAssembly']
    control['clutch_release'] = 0.0
    errors = []
    phases = [0,4*math.pi/3,2*math.pi/3,2*math.pi/3,4*math.pi/3,0]

    def crank_position(obj):
        index = int(obj.name.rsplit('_',1)[1])-1
        angle = control['engine_angle']+phases[index]
        if obj.name.startswith('PistonMotion_'):
            obj.location.z = .083*math.cos(angle)+math.sqrt(.235**2-(.083*math.sin(angle))**2)
        elif obj.name.startswith('RodMotion_'):
            obj.location.y = -.083*math.sin(angle)
            obj.location.z = .083*math.cos(angle)

    for frame in range(1,337):
        t = (frame-1)/24
        travel = 2.8*(1-smooth(t,0,2)) if t < 2 else (-3.0*smooth(t,11,14) if t >= 11 else 0)
        truck.location.y = travel
        truck.keyframe_insert('location',frame=frame)
        system = 0 if t >= 11 else smooth(t,2,5)
        detailed = 0 if t >= 11 else smooth(t,5,9)
        control['engine_angle'] = t*6 if t < 2 else (0 if t < 11 else (t-11)*6)
        control['clutch_angle'] = 0 if t < 11 else (t-11)*3
        control['wheel_angle'] = (2.8-travel)/.54 if t < 2 else (0 if t < 11 else -travel/.54)
        control['clutch_release'] = 0.0
        for item in groups:
            obj = item['object']
            obj.matrix_local = item['base'].copy()
            obj.location += item['offset']*system
            obj.keyframe_insert('location',frame=frame)
            if obj.name == 'EngineSystem':
                obj.rotation_euler.z = (1-system)*math.pi/2
                obj.keyframe_insert('rotation_euler',frame=frame)
        for item in prepared:
            obj = item['object']
            obj.matrix_local = item['base'].copy()
            if obj.name.startswith(('PistonMotion_','RodMotion_')):
                crank_position(obj)
            obj.location += item['offset']*detailed
            if 'groupOffset' in item:
                obj.location += item['groupOffset']*system
            obj.keyframe_insert('location',frame=frame)
        for name in ['engine_angle','clutch_angle','wheel_angle','clutch_release']:
            control.keyframe_insert(data_path='["'+name+'"]',frame=frame)
        if frame in [264,265]:
            bpy.context.view_layer.update()
            if frame == 265:
                for item in prepared:
                    difference = max(abs(item['object'].matrix_local[row][col]-item['base'][row][col])
                                     for row in range(4) for col in range(4))
                    if difference > .00002:
                        errors.append({'id':item['entity']['id'],'error':difference})
                for item in groups:
                    difference = max(abs(item['object'].matrix_local[row][col]-item['base'][row][col])
                                     for row in range(4) for col in range(4))
                    if difference > .00002:
                        errors.append({'id':item['object'].name,'error':difference})
    report = {'instantRestoreFrame':265,'restoreErrors':errors,
              'physicalEntities':len(prepared),'camera':'Single continuous camera, no cut or flash',
              'disabledLocationDrivers':[saved[0].name for saved in detached],
              'bakeMode':'Location channels are explicitly baked; no location driver is reactivated after assembly',
              'note':'System groups and detailed entities are checked independently at the instant of assembly'}
    (ROOT/'p1_motion_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'p1_explosion_map.json').write_text(json.dumps([{
        'id':item['entity']['id'],'family':item['entity']['family'],'source':item['entity']['source'],
        'assemblyMatrix':item['entity']['assemblyMatrix'],
        'explodeMatrix':[[float(value) for value in row] for row in item['object']['explodeMatrix']]}
        for item in prepared],ensure_ascii=False,indent=2),encoding='utf-8')


def shot_explosion(scene):
    prepared,groups,detached = prepare_explosion()
    camera(scene,(9.5,-14.5,8.0),(0,-.65,2.40),40,16)
    area('Engine foreground softbox',(4.0,-7.0,6.0),1500,(.86,.93,1.0),4.0,(4.2,-5.1,2.4))
    area('Chassis fill softbox',(1.0,-.8,6.0),1100,(1.0,.91,.79),4.5,(0,0,.8))
    area('Wheel layers softbox',(6.0,-1.0,3.6),1000,(.82,.90,1.0),3.0,(3.0,-1.5,.8))
    for light in bpy.data.lights:
        light.use_shadow = light.name == 'V3 key'
    scene.view_settings.exposure = -.20
    bake_explosion(scene,prepared,groups,detached)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'p1_explosion.blend'))
    if MODE == 'hero':
        render_frame(scene,264,'p1_exploded.png',1920,1080,64)
        render_frame(scene,265,'p1_reassembled.png',1920,1080,64)
    else:
        render_sequence(scene,('draft_' if DRAFT else '')+'p1_explosion_frames',1,336,
                        960 if DRAFT else 1920,540 if DRAFT else 1080,16 if DRAFT else 48,3 if DRAFT else 1,not DRAFT)


def shot_wheel(scene):
    base = bpy.data.objects['Dayun_N8E_6x4']
    hub = bpy.data.objects['WheelEnd_R']
    wheel = bpy.data.objects['Front_R']
    visible = {hub,wheel,*hub.children_recursive,*wheel.children_recursive}
    for obj in base.children_recursive:
        if obj.type == 'MESH' and obj not in visible:
            obj.hide_render = True
    layers = {
        'Front_R_Tire':((.70,.90,0),'wheel'),
        'Front_R_Rim':((1.05,-.10,0),'wheel'),
        'WheelEnd_R_BrakeDrum':((.42,-1.15,.04),'drum'),
        'WheelEnd_R_BackingPlate':((-.20,.10,0),'service'),
        'WheelEnd_R_OuterBearing_OuterRace':((.50,-1.50,.04),'service'),
    }
    for obj in base.children_recursive:
        if obj.get('part_family') == 'wheel_nut' and obj.name.startswith('Front_R_'):
            layers[obj.name] = ((1.35,-.10,0),'wheel')
        elif obj.name.startswith('WheelEnd_R_OuterBearing_') and obj.get('part_family') in ['tapered_bearing_inner_race','tapered_bearing_cage','tapered_bearing_roller']:
            x = {'tapered_bearing_inner_race':.54,'tapered_bearing_cage':.59,'tapered_bearing_roller':.64}[obj['part_family']]
            layers[obj.name] = ((x,-1.50,.04),'service')
        elif obj.name.startswith(('WheelEnd_R_Shoe_','WheelEnd_R_Lining_')):
            sign = 1 if obj.data.vertices[0].co.y >= 0 else -1
            layers[obj.name] = ((0,sign*.10,sign*.07),'service')
    bases = {name:bpy.data.objects[name].matrix_local.copy() for name in layers}
    for frame in range(1,145):
        t = (frame-1)/24
        factors = {'wheel':smooth(t,.8,2.3),'drum':smooth(t,2.0,3.3),'service':smooth(t,3.1,4.6)}
        restore = smooth(t,4.9,6)
        for name,(offset,stage) in layers.items():
            obj = bpy.data.objects[name]
            obj.matrix_local = bases[name].copy()
            obj.location += Vector(offset)*factors[stage]*(1-restore)
            obj.keyframe_insert('location',frame=frame)
        drum = bpy.data.objects['WheelEnd_R_BrakeDrum']
        drum.rotation_euler.y = math.pi*factors['drum']*(1-restore)
        drum.keyframe_insert('rotation_euler',frame=frame)
    camera(scene,(5.4,-5.7,3.0),(1.28,-2.60,.62),56,16)
    area('Wheel inspection key',(3.0,-4.2,3.5),500,(.88,.94,1.0),2.5,(1.4,-2.5,.6))
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'p1_wheel.blend'))
    if '--stills' in ARGS:
        for frame in [1,60,96,112,144]:
            render_frame(scene,frame,f'wheel_check_{frame:04d}.png',960,540,24)
    else:
        render_sequence(scene,('draft_' if DRAFT else '')+'p1_wheel_frames',1,144,
                        960 if DRAFT else 1920,540 if DRAFT else 1080,16 if DRAFT else 48,3 if DRAFT else 1,not DRAFT)


def shot_power(scene):
    control = bpy.data.objects['PowertrainControl']
    base = bpy.data.objects['Dayun_N8E_6x4']
    power_roots = [bpy.data.objects[name] for name in ['EngineSystem','Clutch','Gearbox','PropellerShaft','InterAxleDrive','FinalDrive_Mid','FinalDrive_Rear']]
    visible = {obj for root in power_roots for obj in root.children_recursive}
    for obj in base.children_recursive:
        if obj.parent == base and obj.name.startswith(('Front_','Mid_','Rear_')):
            visible.update(obj.children_recursive)
        if obj.type == 'MESH':
            obj.hide_render = obj not in visible
    bpy.data.objects['Gearbox_ServiceCover'].location.x = -.25
    bpy.data.objects['FinalDrive_Mid_RearCover'].location.x = -.22
    bpy.data.objects['FinalDrive_Rear_RearCover'].location.x = -.22
    for obj in bpy.data.objects['CylinderLinerBank_PhotographyLift'].children_recursive:
        obj.hide_render = True
    for name in ['Cylinder head deck','Cylinder head cover']:
        bpy.data.objects[name].hide_render = True
    for frame in range(1,193):
        t = (frame-1)/24
        control['engine_angle'] = t*5
        if t < 2:
            control['clutch_angle'] = t*5
            control['wheel_angle'] = t*5/3
            control['clutch_release'] = 0
        elif t < 4:
            control['clutch_angle'] = 10.0
            control['wheel_angle'] = 10/3
            control['clutch_release'] = smooth(t,2,2.5)
        elif t < 6:
            control['clutch_angle'] = 10+(t-4)*5
            control['wheel_angle'] = (10+(t-4)*5)/3
            control['clutch_release'] = 1-smooth(t,4,4.7)
        else:
            control['clutch_angle'] = 20+(t-6)*5
            control['wheel_angle'] = (20+(t-6)*5)/3
            control['clutch_release'] = 0
        for name in ['engine_angle','clutch_angle','wheel_angle','clutch_release']:
            control.keyframe_insert(data_path='["'+name+'"]',frame=frame)
    camera(scene,(5.8,-4.2,3.9),(0,-.10,1.10),52,16)
    area('Powertrain inspection key',(1.8,-3.5,4.8),900,(.89,.94,1.0),3.0,(0,-.6,1.1))
    scene['powerView'] = 'Cutaway: cab, liner bank and head deck are removed for this explanatory shot; shared clutch controller drives downstream shafts and wheels'
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'p1_power.blend'))
    if '--stills' in ARGS:
        for frame in [1,48,80,144,192]:
            render_frame(scene,frame,f'power_check_{frame:04d}.png',960,540,24)
    else:
        render_sequence(scene,('draft_' if DRAFT else '')+'p1_power_frames',1,192,
                        960 if DRAFT else 1920,540 if DRAFT else 1080,16 if DRAFT else 48,3 if DRAFT else 1,not DRAFT)


def make_night_road(radius):
    from geo import revolve, cylinder
    mats = palette()
    box('MV asphalt',(0,0,-.025),(120,120,.025),mats['frame'])
    for side in [-1,1]:
        revolve('MV continuous lane edge',[(radius+side*1.43-.035,.003),(radius+side*1.43+.035,.003)],mats['ivory'],segments=256)
    for i in range(96):
        a = 2*math.pi*i/96
        marker = box('MV lane marker',(radius*math.cos(a),radius*math.sin(a),.004),(.65,.065,.004),mats['ivory'])
        marker.rotation_euler.z = a+math.pi/2
    truck = bpy.data.objects['TruckAssembly']
    for x in [-.85,.85]:
        data = bpy.data.lights.new('MV headlight','SPOT')
        data.energy = 180
        data.color = (1,.86,.65)
        data.spot_size = .78
        data.spot_blend = .65
        data.shadow_soft_size = .16
        data.use_shadow = False
        obj = bpy.data.objects.new('MV headlight',data)
        bpy.context.collection.objects.link(obj)
        obj.parent = truck
        obj.location = (x,-3.60,1.13)
        obj.rotation_euler = Vector((0,-1,-.24)).to_track_quat('-Z','Y').to_euler()
    for i in range(8):
        a = 2*math.pi*i/8
        r = radius+3.6
        x,y = r*math.cos(a),r*math.sin(a)
        cylinder('MV road light pole',.04,5.6,(x,y,2.8),mats['steel'],vertices=16)
        box('MV road light head',(x,y,5.58),(.25,.25,.075),mats['ivory'])
        lamp = area('MV road pool',(x,y,5.5),190,(.55,.68,1.0),3.5,(radius*math.cos(a),radius*math.sin(a),0))
        lamp.data.use_shadow = False


def night_lighting(scene):
    truck = bpy.data.objects['TruckAssembly']
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT' and obj.name.startswith('V3'):
            bpy.data.objects.remove(obj,do_unlink=True)
    settings = [
        ('MV soft key',(3.5,-4.5,6.0),1200,(.84,.91,1.0),4.5,(0,-.8,1.5)),
        ('MV side fill',(-3.0,-.5,3.6),650,(.53,.70,1.0),4.0,(0,0,1.4)),
        ('MV warm rim',(2.5,4.0,4.8),1500,(1.0,.72,.45),4.0,(0,.7,1.8)),
        ('MV front fill',(-.5,-5.0,3.5),450,(.76,.86,1.0),3.5,(0,-2.0,1.5)),
    ]
    for name,loc,power,color,size,target in settings:
        obj = area(name,loc,power,color,size,target)
        obj.parent = truck
        obj.data.use_shadow = name == 'MV soft key'
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.025,.045,.085,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .16
    scene.view_settings.exposure = -.10


def shot_mv(scene):
    truck = bpy.data.objects['TruckAssembly']
    control = bpy.data.objects['PowertrainControl']
    radius = 18 if MODE == 'cruise' else 9
    make_night_road(radius)
    night_lighting(scene)
    camera_obj = camera(scene,(9,-11,5.2),(0,0,1.5),45,16)
    for frame in range(1,169):
        t = (frame-1)/24
        a = 2*math.pi*t/7
        truck.location = (radius*math.cos(a),radius*math.sin(a),0)
        truck.rotation_euler.z = a+math.pi
        control['wheel_angle'] = radius*a/.54
        control['engine_angle'] = a*2
        control['clutch_angle'] = a*2
        for name in ['wheel_angle','engine_angle','clutch_angle']:
            control.keyframe_insert(data_path='["'+name+'"]',frame=frame)
        truck.keyframe_insert('location',frame=frame)
        truck.keyframe_insert('rotation_euler',frame=frame)
        bpy.context.view_layer.update()
        if MODE == 'detail':
            target = truck.matrix_world @ Vector((1.10,-2.48,.56))
            offset = Vector((2.2,1.3,.22))
        else:
            target = truck.matrix_world @ Vector((0,-.4 if MODE == 'cruise' else .4,1.5))
            offset = Vector((8,-10,4.5) if MODE == 'cruise' else (-8,8,3.6))
        rotation = truck.rotation_euler.to_matrix()
        camera_obj.location = target + rotation @ offset
        camera_obj.rotation_euler = (target-camera_obj.location).to_track_quat('-Z','Y').to_euler()
        camera_obj.data.lens = 58 if MODE == 'detail' else (45 if MODE == 'cruise' else 39)
        camera_obj.keyframe_insert('location',frame=frame)
        camera_obj.keyframe_insert('rotation_euler',frame=frame)
        camera_obj.data.keyframe_insert('lens',frame=frame)
        camera_obj.data.dof.focus_object.location = target
        camera_obj.data.dof.focus_object.keyframe_insert('location',frame=frame)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/f'mv_{MODE}.blend'))
    if '--stills' in ARGS:
        for frame in [1,56,112,168]:
            render_frame(scene,frame,f'mv_{MODE}_check_{frame:04d}.png',960,540,24)
    else:
        render_sequence(scene,('draft_' if DRAFT else '')+f'mv_{MODE}_frames',1,168,
                        960 if DRAFT else 1920,540 if DRAFT else 1080,16 if DRAFT else 48,3 if DRAFT else 1,not DRAFT)


scene = load_scene()
studio(scene,(0,-.6,1.4),6,-.03)
if MODE in ['explosion','hero']:
    shot_explosion(scene)
elif MODE == 'wheel':
    shot_wheel(scene)
elif MODE == 'power':
    shot_power(scene)
else:
    shot_mv(scene)
print('P1_SHOT_COMPLETE',MODE,'draft',DRAFT)
