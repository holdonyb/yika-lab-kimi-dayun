import math
from geo import group, register, revolve, sector, cylinder, mesh
from driveline import gear, drive_property
from studio import metal


def materials():
    return {
        'active':metal('V4 active flywheel and pressure steel',(.23,.34,.44),.40,.82,.08),
        'friction':metal('V4 driven friction composite',(.22,.075,.022),.77,.04),
        'input':metal('V4 splined input steel',(.43,.56,.66),.34,.90,.12),
        'spring':metal('V4 diaphragm spring steel',(.16,.21,.28),.32,.92),
        'cover':metal('V4 clutch cover',(.055,.080,.11),.42,.84),
        'release':metal('V4 release bearing silver',(.62,.67,.72),.25,.95),
    }


def annulus(name,profile,mat,parent,sectioned):
    obj = sector(name,profile,math.radians(45),math.radians(320),mat,parent,'Y',steps=72) if sectioned else revolve(name,profile,mat,parent,'Y',segments=96)
    register(obj,'clutch_annular_component','Annular clutch component with a teaching cutaway' if sectioned else 'Complete annular clutch component')
    obj['sectionedForTeaching'] = bool(sectioned)
    return obj


def spring_finger(index,parent,control,mat):
    vertices = []
    radial_steps = 7
    inner,outer = .055,.155
    gap = .015
    a0 = index*2*math.pi/18+gap
    a1 = (index+1)*2*math.pi/18-gap
    for side in [-1,1]:
        for j in range(radial_steps):
            u = j/(radial_steps-1)
            radius = inner+(outer-inner)*u
            y = .0687+(.036-.0687)*min(u/.82,1)
            for angle in [a0,a1]:
                vertices.append((radius*math.cos(angle),y+side*.0013,radius*math.sin(angle)))
    faces = []
    band = radial_steps*2
    for j in range(radial_steps-1):
        a,b = j*2,(j+1)*2
        faces.extend([(a,b,b+1,a+1),(band+a,band+a+1,band+b+1,band+b),
                      (a,band+a,band+b,b),(a+1,b+1,band+b+1,band+a+1)])
    faces.extend([(0,1,band+1,band),(band-2,2*band-2,2*band-1,band-1)])
    obj = mesh(f'DiaphragmFinger_{index+1:02d}',vertices,faces,mat,parent)
    register(obj,'diaphragm_spring_finger','Conical spring finger with driven inner-tip deflection and fixed outer support')
    obj.shape_key_add(name='Basis')
    released = obj.shape_key_add(name='ReleaseDeflection')
    for j,vertex in enumerate(vertices):
        radius = math.hypot(vertex[0],vertex[2])
        u = (radius-inner)/(outer-inner)
        released.data[j].co.y -= .007*max(0,1-u/.82)
    curve = released.driver_add('value')
    driver = curve.driver
    variable = driver.variables.new()
    variable.name = 'v'
    variable.type = 'SINGLE_PROP'
    variable.targets[0].id = control
    variable.targets[0].data_path = '["clutch_release"]'
    driver.expression = 'v'
    return obj


def build_clutch(parent,control,name='Clutch',origin=(0,0,0),sectioned=True):
    mats = materials()
    root = group(name,parent,origin)
    register(root,'clutch_assembly','Single dry clutch with independent active and driveline rotations, real pressure lift and release spring deflection')
    root['source'] = 'v4-clutch-fix'
    root['sectionedForTeaching'] = bool(sectioned)
    active = group('Clutch_ActiveRotation',root)
    register(active,'engine_active_side','Flywheel, cover, pressure plate and diaphragm rotate with the engine even while released')
    drive_property(active,control,'engine_angle','v',1,'rotation_euler')
    driven = group('Clutch_InputRotation',root)
    register(driven,'splined_driven_side','Friction disc and gearbox input shaft share the driven angle; axial float is allowed on the splines')
    drive_property(driven,control,'clutch_angle','v',1,'rotation_euler')
    annulus('Clutch_Flywheel',[(.036,-.034),(.156,-.034),(.156,-.002),(.036,-.002)],mats['active'],active,sectioned)
    annulus('Clutch_FlywheelFrictionFace',[(.036,-.002),(.142,-.002),(.142,0),(.036,0)],mats['active'],active,sectioned)
    gear('Clutch_FlywheelRingGear',active,(0,-.015,0),.174,64,.014,mats['active'],'Y',0,.156)
    cylinder('Clutch_CrankStub',.0115,.06,(0,-.020,0),mats['active'],active,(0,1,0),64)
    cover = annulus('Clutch_Cover',[(.145,.036),(.174,.036),(.174,.058),(.145,.058)],mats['cover'],active,sectioned)
    lift = group('Clutch_PressurePlateLift',active)
    register(lift,'pressure_plate_lift','Actual axial release of the pressure plate while it continues rotating with the flywheel')
    annulus('Clutch_PressurePlate',[(.038,.010),(.142,.010),(.142,.026),(.038,.026)],mats['active'],lift,sectioned)
    for angle in [math.pi/2,math.pi,3*math.pi/2]:
        x,z = .142*math.cos(angle),.142*math.sin(angle)
        cutter = cylinder('Cover guide bore cutter',.0045,.12,(x,.047,z),mats['release'],cover,(0,1,0),32)
        from geo import boolean
        boolean(cover,cutter)
        pin = cylinder('Clutch_PressureDrivePin',.0038,.036,(x,.031,z),mats['release'],lift,(0,1,0),32)
        register(pin,'pressure_drive_pin','Sliding drive pin keeps pressure plate rotating with cover while allowing axial lift')
    revolve('Clutch_DiaphragmFulcrum',[(.138,.026),(.142,.026),(.142,.030),(.138,.030)],mats['spring'],active,'Y',segments=80)
    diaphragm = group('Clutch_DiaphragmRotation',active)
    register(diaphragm,'diaphragm_spring','Inner fingers deflect toward the flywheel as the pressure plate lifts away')
    for index in range(18):
        spring_finger(index,diaphragm,control,mats['spring'])
    disc_lift = group('Clutch_DiscSplineFloat',driven)
    register(disc_lift,'disc_spline_float','Small axial float of the splined friction disc clears both friction faces after clamp release')
    disc = revolve('Clutch_FrictionDisc',[(.036,0),(.130,0),(.130,.010),(.036,.010)],mats['friction'],disc_lift,'Y',segments=112)
    register(disc,'clutch_friction_disc','Full annular friction disc clamped between flywheel and pressure plate only while engaged')
    hub = gear('Clutch_SplineHub',disc_lift,(0,.012,0),.033,18,.046,mats['input'],'Y',0,.0125)
    register(hub,'splined_disc_hub','Toothed hub with a real center bore and axial travel on the input shaft splines')
    shaft = cylinder('Clutch_InputShaft',.012,.36,(0,.20,0),mats['input'],driven,(0,1,0),64)
    register(shaft,'gearbox_input_shaft','Input shaft rotates with the splined disc and stops while the active side continues')
    revolve('Clutch_InputGuide',[(.014,.11),(.022,.11),(.022,.26),(.014,.26)],mats['cover'],root,'Y',segments=64)
    contact = revolve('Clutch_ReleaseContactRace',[(.046,-.006),(.066,-.006),(.066,.006),(.046,.006)],mats['release'],active,'Y',(0,.085,0),80)
    register(contact,'release_contact_race','Annular release contact face covers the .055m spring-tip radius and retains its assembled offset')
    inner_race = revolve('Clutch_ReleaseInnerRace',[(.022,-.006),(.037,-.006),(.037,.006),(.022,.006)],mats['release'],root,'Y',(0,.085,0),80)
    register(inner_race,'release_inner_race','Guided inner race concentric with the input guide and the enlarged spring contact ring')
    carrier = revolve('Clutch_ReleaseCarrier',[(.067,-.006),(.079,-.006),(.079,.006),(.067,.006)],mats['release'],root,'Y',(0,.085,0),80)
    register(carrier,'release_bearing_carrier','Non-rotating carrier surrounds the release contact race without intersecting it')
    root['pressureLiftMeters'] = .010
    root['discFloatMeters'] = .002
    root['bearingTravelMeters'] = .016
    root['fingerDeflectionMeters'] = .007
    root['displayAxialScale'] = 4.0
    return {'root':root,'active':active,'driven':driven,'pressureLift':lift,'discLift':disc_lift,
            'disc':disc,'cover':cover,'releaseContact':contact,'releaseCarrier':carrier,'releaseInnerRace':inner_race}
