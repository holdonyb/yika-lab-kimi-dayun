from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import json
from geo import group, register, registry, clone_tree, capture_rest, export_registry, cylinder, revolve

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'truck_stage1.blend'))
scene = bpy.context.scene
from accessories import (MATS, cylinder_head, radiator, air_tanks, battery_modules,
                         exhaust, refine_seats_and_dash, c_channel_frames)
from driveline import clutch, gearbox, drive_shaft, differential, universal_joint, beam, gear

base = bpy.data.objects['Dayun_N8E_6x4']
control = bpy.data.objects['PowertrainControl']
controller = bpy.data.objects['CrankAngleController']
control['clutch_release'] = 0.0
cab = bpy.data.objects['Cab']
engine = bpy.data.objects['EngineSystem']


def remove_named(prefixes):
    for obj in list(base.children_recursive):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj,do_unlink=True)


def restore_registry():
    seen = {item['id'] for item in registry}
    source = json.loads((ROOT/'stage1_entities.json').read_text(encoding='utf-8'))
    for entity in source['entities']:
        identifier = entity['id']
        obj = bpy.data.objects.get(identifier)
        if identifier in seen or obj is None or not obj.get('part_family'):
            continue
        obj['semantic_id'] = obj.name
        obj['source'] = entity.get('source',obj.get('source','v2-frozen-dbae2ea6'))
        registry.append({'id':identifier,'family':obj['part_family'],
                         'shape':obj.get('structure',entity['shape']),
                         'note':'Recovered from stage1 semantic data; source and physical meaning retained'})
        seen.add(identifier)
    print('RESTORED_STAGE1_ENTITIES',len(seen),flush=True)


restore_registry()
print('STEP remove old parts',flush=True)
remove_named(('Main chassis rail','Chassis rail upper flange','Leaf spring',
              'Axle housing','Differential casing','Seat cushion','Seat back','Seat headrest',
              'Seat red center','Dashboard','Dash display','Steering wheel','Steering column','Steering spoke',
              'Battery box','Battery ventilation','Battery latch'))
print('STEP frame channels',flush=True)
c_channel_frames(base,MATS['frame'])
print('STEP cylinder head',flush=True)
head = cylinder_head(engine,controller)
print('STEP clutch',flush=True)
clutch_parts = clutch('Clutch',base,(0,-1.15,1.02),control)
print('STEP gearbox',flush=True)
gearbox_parts = gearbox('Gearbox',base,(0,-.40,1.00),control)
print('STEP propeller shaft',flush=True)
shaft = drive_shaft('PropellerShaft',base,control)
print('STEP differentials',flush=True)
diff_mid = differential('FinalDrive_Mid',base,(0,1.27,.55),control)
diff_rear = differential('FinalDrive_Rear',base,(0,2.60,.55),control)
print('STEP inter axle',flush=True)
inter = group('InterAxleDrive',base,(0,1.935,.695))
register(inter,'inter_axle_drive','Inter-axle shaft and universal joints linking the two driven axles')
revolve('Inter axle tube',[(.023,-.665),(.028,-.665),(.028,.665),(.023,.665)],
        MATS['machined'],inter,'Y',segments=64)
for y in [-.665,.665]:
    universal_joint('InterAxle_UJoint',inter,(0,y,0))
from driveline import drive_property
drive_property(inter,control,'clutch_angle','v*3',1,'rotation_euler')
print('STEP radiator',flush=True)
radiator_parts = radiator(base,controller)
print('STEP air tanks',flush=True)
air_tanks(base)
print('STEP batteries',flush=True)
battery_modules(base)
print('STEP exhaust',flush=True)
exhaust(base)
print('STEP cab interior',flush=True)
refine_seats_and_dash(cab)

for y in [-2.48,1.27,2.60]:
    for side in [-1,1]:
        spring = group(f'LeafPack_{y}_{side}',base,(side*.70,y,.79))
        register(spring,'leaf_spring_pack','Four tapered curved leaves with end eyes and a shared center seat')
        for layer in range(4):
            length = .96-layer*.12
            verts = []
            for j in range(25):
                t = j/24
                yy = -length/2 + length*t
                z = layer*.024 + .045*(2*t-1)**2
                for x,dz in [(-.047,0),(.047,0),(-.047,.007),(.047,.007)]:
                    verts.append((x,yy,z+dz))
            faces = []
            for j in range(24):
                a,b = j*4,(j+1)*4
                faces.extend([(a,b,b+1,a+1),(a+2,b+2,b+3,a+3),(a,a+2,b+2,b),
                              (a+1,b+1,b+3,a+3),(a,b,b+2,a+2),(a+3,b+3,b+1,a+1)])
            from geo import mesh
            mesh('Curved leaf',verts,faces,MATS['steel'],spring,.001)
            for end in [-1,1]:
                revolve('Leaf eye',[(.010,-.006),(.021,-.006),(.021,.006),(.010,.006)],
                        MATS['steel'],spring,'X',(0,end*length/2,layer*.024+.045),32)

for obj in base.children_recursive:
    if obj.get('part_family') or obj.type != 'MESH':
        continue
    name = obj.name
    family = None
    if name.startswith(('Cab front','High roof','Cab rear','Cab floor','Side rear cab','Sleeper upper',
                        'Sleeper rear fairing','Rear cab lower','Front corner','Panoramic sun visor',
                        'Front roof badge','Front graphite','Brand red brow','Lower bumper','Front plate','Corner red cheek')):
        family = 'cab_body_panel'
    elif name.startswith(('Door_L outer','Door_R outer')):
        family = 'door_outer_panel'
    elif name.startswith(('Door_L glass','Door_R glass','Front windshield','Sleeper window glass')):
        family = 'cab_glazing'
    elif name.startswith(('Door_L window frame','Door_R window frame','A pillar')):
        family = 'door_frame'
    elif name.startswith(('Door handle','Door key')):
        family = 'door_handle'
    elif name.startswith('Mirror'):
        family = 'mirror_assembly'
    elif name.startswith(('Entry step','Step grip','Step side')):
        family = 'cab_entry_step'
    elif name.startswith('Front red wheel arch'):
        family = 'cab_fender'
    elif name.startswith(('Headlamp','Projector','Amber turn','LED daytime','Fog light')):
        family = 'headlamp_assembly'
    elif name.startswith(('Grille','Chrome sweeping')):
        family = 'front_grille_assembly'
    elif name.startswith(('Frame crossmember','Rear deck','Rear catwalk','Deck grip','Catwalk grip')):
        family = 'frame_crossmember'
    elif name.startswith(('Fifth wheel','Coupler')):
        family = 'fifth_wheel'
    elif name.startswith(('Rear lamp','Rear white','Rear light bar')):
        family = 'rear_lamp'
    elif name.startswith(('Rear underrun','Front under')):
        family = 'underrun_protection'
    elif name.startswith('Fuel tank retaining'):
        family = 'fuel_tank_strap'
    elif name.startswith('Fuel tank'):
        family = 'fuel_tank'
    elif name.startswith('Fuel filler'):
        family = 'fuel_filler'
    elif name.startswith('Fuel step'):
        family = 'fuel_tank_step'
    elif name.startswith(('Rear tandem','Rear mudflap','Mudflap')):
        family = 'rear_mudguard'
    elif name.startswith(('Suspension damper','Suspension link')):
        family = 'suspension_link'
    elif name.startswith(('Roof brand','Front brand','Front DAYUN','Roof small','Plate lettering','Door_L N8E','Door_R N8E')):
        family = 'vehicle_badge'
    if family is None:
        if name.startswith('Seat suspension'):
            family = 'seat_suspension'
        elif name.startswith(('Seat cushion','Seat sewn','Seat back','Seat headrest','Seat side bolster','Seat armrest')):
            family = 'seat_component'
        elif name.startswith(('Dashboard main','Dashboard display','Instrument bezel','Instrument glass','Instrument needle')):
            family = 'dashboard_component'
        elif name.startswith(('Steering wheel','Steering spoke','Steering hub','Steering column')):
            family = 'steering_control'
        elif name.startswith(('Valve stem','Valve head','Valve guide','Valve spring','Spring retainer','Rocker arm')):
            family = 'valvetrain_component'
        elif name.startswith(('Camshaft tube','Eccentric cam lobe')):
            family = 'camshaft_component'
        elif name.startswith('Head cover fastener'):
            family = 'head_cover_fastener'
        elif name.startswith(('Cooling tube','Radiator fin','Radiator header','Radiator side','Fan shroud','Fan hub','Upper coolant hose')):
            family = 'radiator_component'
        elif name.startswith('Swept fan blade'):
            family = 'cooling_fan_blade'
        elif name.startswith(('Air tank pressure','Tank retaining','Tank drain','Tank outlet')):
            family = 'air_tank_component'
        elif name.startswith(('Battery case','Battery lid','Battery cell','Battery terminal','Battery hold','Battery tray')):
            family = 'battery_component'
        elif name.startswith(('Muffler shell','Muffler baffle','Muffler band','Exhaust inlet','Exhaust outlet')):
            family = 'exhaust_component'
        elif name.startswith('Gearbox_ShaftBearing'):
            family = 'gearbox_bearing'
        elif name.startswith('Gearbox_Shaft'):
            family = 'gearbox_shaft'
        elif name.startswith('Gearbox_Synchronizer'):
            family = 'synchronizer_ring'
        elif name.startswith('Gearbox_ShiftFork'):
            family = 'shift_fork'
        elif name.startswith(('Gearbox_HousingRail','Gearbox_EndPlate')):
            family = 'gearbox_housing'
        elif name.startswith('Clutch_DiaphragmFinger'):
            family = 'clutch_diaphragm'
        elif name.startswith('Inter axle tube'):
            family = 'inter_axle_tube'
        elif name.startswith(('FinalDrive_Mid_CrownBolt','FinalDrive_Rear_CrownBolt')):
            family = 'crown_bolt'
        elif name.startswith(('FinalDrive_Mid_HalfShaft','FinalDrive_Rear_HalfShaft')):
            family = 'half_shaft'
        elif name.startswith(('FinalDrive_Mid_SideBearing','FinalDrive_Rear_SideBearing')):
            family = 'side_bearing'
        elif name.startswith(('FinalDrive_Mid_PlanetBevel','FinalDrive_Rear_PlanetBevel')):
            family = 'differential_planet_gear'
        elif name.startswith(('FinalDrive_Mid_HousingCheek','FinalDrive_Rear_HousingCheek')):
            family = 'differential_housing'
        elif 'CrossX' in name or 'CrossZ' in name:
            family = 'universal_joint_cross'
        elif 'BearingCap' in name:
            family = 'universal_joint_bearing_cap'
        elif 'Yoke' in name or 'Fork' in name:
            family = 'universal_joint_yoke'
        elif name.startswith('Curved leaf'):
            family = 'leaf_spring'
        elif name.startswith('Leaf eye'):
            family = 'leaf_spring_eye'
    if family:
        obj['part_family'] = family
        obj['semantic_id'] = obj.name
        obj['source'] = 'v1-frozen-bb6929a1'
        obj['structure'] = 'Retained physical mesh from the frozen exterior asset'
        registry.append({'id':obj.name,'family':family,'shape':obj['structure'],
                         'note':'Retained exterior component; multiple decorative faces stay with one physical part'})
for material in bpy.data.materials:
    if material.name.startswith('Glazing'):
        shader = material.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Transmission Weight'].default_value = .28
        shader.inputs['Roughness'].default_value = .14

print('STEP capture matrices',flush=True)
scene.frame_set(1)
capture_rest(base)
print('STEP export registry',flush=True)
report = export_registry(ROOT/'vehicle_entities.json',base)
report['stage'] = 'Integrated procedural vehicle with generic internal systems; not a complete OEM bill of materials'
report['pending'] = ['OEM-specific valve timing, gear ratios and manufacturing dimensions',
                     'Complete coolant, lubrication, fuel, air and electrical circuits',
                     'Combustion, torque, material strength and vehicle dynamics validation',
                     'P1 continuous shot verification and P2 rigid-body caches']
(ROOT/'vehicle_entities.json').write_text(__import__('json').dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('STEP save blend',flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'truck_systems.blend'))
print('SYSTEMS_COMPLETE',report['physicalFamilies'],report['physicalInstances'])
