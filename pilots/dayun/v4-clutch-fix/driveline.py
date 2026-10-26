import math
from mathutils import Vector
from geo import PI, group, register, mesh, box, cylinder, revolve, sector, boolean, bevel, frustum
from studio import palette

MATS = palette()


def drive_property(obj, control, property_name, expression, index=0, path='rotation_euler'):
    curve = obj.driver_add(path,index)
    driver = curve.driver
    variable = driver.variables.new()
    variable.name = 'v'
    variable.type = 'SINGLE_PROP'
    variable.targets[0].id = control
    variable.targets[0].data_path = '["'+property_name+'"]'
    driver.expression = expression


def gear(name,parent,loc,radius,teeth,width,material=None,axis='Y',helix=.18,bore=None):
    material = material or MATS['machined']
    bore_radius = radius*.23 if bore is None else bore
    verts = []
    steps = teeth*4
    for i in range(steps):
        angle = 2*PI*i/steps
        outer = radius if i%4 in [1,2] else radius*.84
        for r,axial in [(bore_radius,-width/2),(outer,-width/2),(outer,width/2),(bore_radius,width/2)]:
            twist = helix*axial/width
            a = angle+twist
            if axis == 'Y':
                verts.append((r*math.cos(a),axial,r*math.sin(a)))
            else:
                verts.append((axial,r*math.cos(a),r*math.sin(a)))
    faces = []
    for i in range(steps):
        for j in range(4):
            faces.append((i*4+j,i*4+(j+1)%4,((i+1)%steps)*4+(j+1)%4,((i+1)%steps)*4+j))
    obj = mesh(name,verts,faces,material,parent,.0006,False,'gear',
               'Open-center gear with individual helical trapezoid teeth and a real shaft bore')
    obj.location = loc
    return obj


def beam(name,parent,a,b,radius,material=None):
    material = material or MATS['machined']
    a,b = Vector(a),Vector(b)
    return cylinder(name,radius,(b-a).length,(a+b)/2,material,parent,b-a,40)


def universal_joint(name,parent,loc):
    root = group(name,parent,loc)
    register(root,'universal_joint','Two yokes, cross trunnion and four capped needle-bearing interfaces')
    for sign in [-1,1]:
        box(name+'_Yoke',(0,sign*.040,0),(.072,.038,.066),MATS['steel'],root,.006)
        for side in [-1,1]:
            box(name+'_Fork',(side*.027,sign*.040,0),(.016,.045,.067),MATS['steel'],root,.005)
    cylinder(name+'_CrossX',.010,.082,(0,0,0),MATS['machined'],root,(1,0,0),32)
    cylinder(name+'_CrossZ',.010,.082,(0,0,0),MATS['machined'],root,(0,0,1),32)
    for axis in [(1,0,0),(0,0,1)]:
        for sign in [-1,1]:
            loc = tuple(sign*.041 if value else 0 for value in axis)
            cap = revolve(name+'_BearingCap',[(.0105,-.007),(.015,-.007),(.015,.007),(.0105,.007)],
                          MATS['machined'],root,'X',loc,32)
            cap.rotation_euler.y = 0 if axis[0] else PI/2
    return root


def clutch(name,parent,loc,control):
    root = group(name,parent,loc)
    register(root,'clutch_assembly','Flywheel, friction disc, pressure plate, diaphragm spring and release bearing')
    revolve(name+'_Flywheel',[(.036,-.022),(.143,-.022),(.143,.022),(.036,.022)],
            MATS['steel'],root,'Y',segments=96)
    disc = revolve(name+'_FrictionDisc',[(.041,-.007),(.123,-.007),(.123,.007),(.041,.007)],
                   MATS['friction'],root,'Y',segments=96,family='clutch_friction_disc',
                   shape='Driven friction disc with a separate splined hub and two friction faces')
    gear(name+'_SplineHub',root,(0,0,0),.047,18,.020,MATS['machined'],'Y',0,.0205)
    pressure = revolve(name+'_PressurePlate',[(.039,-.009),(.137,-.009),(.137,.009),(.039,.009)],
                       MATS['machined'],root,'Y',(0,.021,0),96,'clutch_pressure_plate',
                       'Pressure plate with an open center and diaphragm-spring contact surface',edge=.0007)
    for i in range(18):
        a = 2*PI*i/18
        sector(name+'_DiaphragmFinger',[(.053,-.0015),(.127,-.0015),(.127,.0015),(.053,.0015)],
               a+.025,a+.24,MATS['steel'],root,'Y',(0,.034,0),5)
    release = revolve(name+'_ReleaseBearing',[(.021,-.010),(.047,-.010),(.047,.010),(.021,.010)],
                      MATS['machined'],root,'Y',(0,.060,0),64,'clutch_release_bearing',
                      'Axially sliding clutch release bearing, not part of the friction disc',edge=.0005)
    drive_property(disc,control,'clutch_angle','v',1,'rotation_euler')
    drive_property(pressure,control,'clutch_angle','v',1,'rotation_euler')
    drive_property(release,control,'clutch_release','v*.035',1,'location')
    return {'root':root,'disc':disc,'pressure':pressure,'release':release}


def gearbox(name,parent,loc,control):
    root = group(name,parent,loc)
    register(root,'gearbox_assembly','Openable three-shaft gearbox with helical pairs, bearings and synchronizer rings')
    input_shaft = group(name+'_InputShaft',root)
    counter_shaft = group(name+'_CounterShaft',root,(.135,0,-.085))
    output_shaft = group(name+'_OutputShaft',root)
    for shaft,z,x,length,y in [(input_shaft,0,0,.35,-.17),(counter_shaft,0,0,.46,.04),(output_shaft,0,0,.38,.19)]:
        cylinder(name+'_Shaft',.020,length,(x,y,z),MATS['machined'],shaft,(0,1,0),48)
        for end in [-1,1]:
            revolve(name+'_ShaftBearing',[(.015,-.012),(.033,-.012),(.033,.012),(.015,.012)],
                    MATS['steel'],shaft,'Y',(x,y+end*length*.46,z),48)
    for y,r1,r2 in [(-.09,.095,.064),(.15,.064,.095)]:
        gear(name+'_InputGear',input_shaft,(0,y,0),r1,24,.028,bore=.021)
        gear(name+'_CounterGear',counter_shaft,(0,y,0),r2,20,.028,bore=.021)
    revolve(name+'_Synchronizer',[(.019,-.014),(.043,-.014),(.043,.014),(.019,.014)],
            MATS['bronze'],output_shaft,'Y',(0,.08,0),64)
    box(name+'_ShiftFork',(.005,.08,.042),(.065,.022,.012),MATS['steel'],output_shaft,.002)
    for side in [-1,1]:
        box(name+'_HousingRail',(side*.135,0,-.115),(.026,.64,.025),MATS['frame'],root,.004)
        box(name+'_EndPlate',(side*.10,-.315,0),(.16,.018,.23),MATS['steel'],root,.006)
    cover = box(name+'_ServiceCover',(-.165,0,0),(.022,.61,.235),MATS['steel'],root,.007)
    register(cover,'gearbox_service_cover','Removable side service cover exposing the gear pairs')
    drive_property(input_shaft,control,'clutch_angle','v',1,'rotation_euler')
    drive_property(counter_shaft,control,'clutch_angle','-v*1.48',1,'rotation_euler')
    drive_property(output_shaft,control,'clutch_angle','v',1,'rotation_euler')
    return {'root':root,'input':input_shaft,'counter':counter_shaft,'output':output_shaft,'cover':cover}


def drive_shaft(name,parent,control):
    root = group(name,parent,(0,.59,.775))
    register(root,'drive_shaft_assembly','Hollow propeller shaft, slip yoke and two universal joints')
    root.rotation_mode = 'QUATERNION'
    root.rotation_quaternion = Vector((0,1.36,-.45)).to_track_quat('Y','Z')
    spinner = group(name+'_Spinner',root)
    revolve(name+'_Tube',[(.031,-.68),(.035,-.68),(.035,.68),(.031,.68)],
            MATS['machined'],spinner,'Y',segments=64)
    gear(name+'_SlipYoke',spinner,(0,-.02,0),.049,18,.055,MATS['steel'],'Y',0)
    front = universal_joint(name+'_FrontUJoint',spinner,(0,-.68,0))
    rear = universal_joint(name+'_RearUJoint',spinner,(0,.68,0))
    drive_property(spinner,control,'clutch_angle','v',1,'rotation_euler')
    return {'root':root,'front':front,'rear':rear,'spinner':spinner}


def differential(name,parent,loc,control):
    root = group(name,parent,loc)
    register(root,'differential_assembly','Openable final drive with pinion, crown gear, carrier, bevel gears and half shafts')
    pinion = gear(name+'_Pinion',root,(0,-.18,.145),.054,14,.034,MATS['machined'],'Y',.12,.022)
    carrier = group(name+'_Carrier',root)
    register(carrier,'differential_carrier','Carrier and crown wheel rotate around the X axle')
    gear(name+'_CrownWheel',carrier,(0,0,0),.148,36,.027,MATS['machined'],'X',.15)
    for i in range(8):
        a = 2*PI*i/8
        cylinder(name+'_CrownBolt',.005,.035,(0,.112*math.cos(a),.112*math.sin(a)),
                 MATS['machined'],carrier,(1,0,0),6)
    for side in [-1,1]:
        gear(name+'_SideGear',carrier,(side*.055,0,0),.040,14,.024,MATS['steel'],'X',.12,.025)
        cylinder(name+'_HalfShaft',.024,.83,(side*.48,0,0),MATS['machined'],carrier,(1,0,0),48)
        revolve(name+'_SideBearing',[(.019,-.012),(.039,-.012),(.039,.012),(.019,.012)],
                MATS['steel'],root,'X',(side*.16,0,0),48)
    for axis in ['Y','Z']:
        for sign in [-1,1]:
            loc = (0,sign*.034,0) if axis == 'Y' else (0,0,sign*.034)
            frustum(name+'_PlanetBevel',loc,.014,.027,.027,MATS['machined'],carrier,
                    (0,1,0) if axis == 'Y' else (0,0,1),32)
    for side in [-1,1]:
        box(name+'_HousingCheek',(side*.11,0,-.08),(.023,.23,.065),MATS['frame'],root,.008)
    cover = revolve(name+'_RearCover',[(.048,-.010),(.174,-.010),(.174,.010),(.048,.010)],
                    MATS['steel'],root,'X',(-.14,0,0),72,'differential_cover',
                    'Removable rear cover exposing the differential carrier and bevel gears',edge=.001)
    drive_property(carrier,control,'wheel_angle','v',0,'rotation_euler')
    drive_property(pinion,control,'clutch_angle','v*3',1,'rotation_euler')
    return {'root':root,'carrier':carrier,'pinion':pinion,'cover':cover}
