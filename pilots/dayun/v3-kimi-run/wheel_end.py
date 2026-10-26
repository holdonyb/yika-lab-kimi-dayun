import math
from geo import (PI, group, register, mesh, box, cylinder, revolve, sector, tube_curve,
                 boolean, bevel, frustum, mirror_assembly)
from studio import palette

MATS = palette()


def tire(parent, rear, name):
    width = .302 if rear else .335
    root = group(name, parent)
    register(root, 'tire', 'Radial tire carcass with shoulder, sidewalls and merged chevron tread')
    profile = [(.292,-width/2),(.424,-width/2),(.483,-width*.47),(.519,-width*.32),
               (.529,0),(.519,width*.32),(.483,width*.47),(.424,width/2),(.292,width/2),
               (.279,width*.34),(.279,-width*.34)]
    revolve(name+'_Carcass', profile, MATS['rubber'], root, 'X', segments=80)
    for face in [-1,1]:
        revolve(name+'_Bead', [(.302,-.004),(.312,-.004),(.312,.004),(.302,.004)],
                MATS['rubber'],root,'X',(face*width/2,0,0),64)
        revolve(name+'_SidewallRidge',[(.436,-.003),(.444,-.003),(.444,.003),(.436,.003)],
                MATS['tread'],root,'X',(face*(width/2+.001),0,0),64)
    verts, faces = [], []
    cube_faces = [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    for j in range(48):
        for band in [-1,0,1]:
            a = 2*PI*j/48 + (band*.012)
            dims = (.082,.026,.006)
            base = [(-dims[0]/2,-dims[1]/2,-dims[2]/2),(-dims[0]/2,-dims[1]/2,dims[2]/2),
                    (-dims[0]/2,dims[1]/2,-dims[2]/2),(-dims[0]/2,dims[1]/2,dims[2]/2),
                    (dims[0]/2,-dims[1]/2,-dims[2]/2),(dims[0]/2,-dims[1]/2,dims[2]/2),
                    (dims[0]/2,dims[1]/2,-dims[2]/2),(dims[0]/2,dims[1]/2,dims[2]/2)]
            offset = len(verts)
            for vx,vy,vz in base:
                vy,vz = vy,.533+vz
                verts.append((band*.102+vx,vy*math.cos(a)-vz*math.sin(a),vy*math.sin(a)+vz*math.cos(a)))
            faces.extend(tuple(offset+i for i in face) for face in cube_faces)
    mesh(name+'_Tread',verts,faces,MATS['tread'],root)
    return root


def rim(parent, mount_offset, name):
    profile = [(.105,-.020),(.160,-.020),(.240,-.048),(.280,-.048),(.295,-.036),
               (.295,.036),(.280,.048),(.240,.048),(.160,.020),(.105,.020)]
    profile = [(r,u+mount_offset) for r,u in profile]
    obj = revolve(name,profile,MATS['machined'],parent,'X',segments=96,
                  family='rim',shape='Dished wheel rim with rolled lips and ten true through ventilation holes')
    barrel = revolve('Rim barrel',[(.265,min(0,mount_offset)),(.280,min(0,mount_offset)),
                    (.280,max(0,mount_offset)),(.265,max(0,mount_offset))],MATS['machined'],parent,'X',segments=80)
    boolean(obj,barrel,'UNION')
    for i in range(10):
        angle = 2*PI*i/10
        cutter = cylinder('Rim through-hole cutter',.0255,.36,
                          (mount_offset,.196*math.cos(angle),.196*math.sin(angle)),MATS['machined'],parent,(1,0,0),32)
        boolean(obj,cutter)
    bevel(obj,.0010)
    return obj


def bearing(parent, rotating, x, name):
    root = group(name,parent)
    register(root,'tapered_hub_bearing','Two independent races, cage and tapered rolling elements')
    outer = revolve(name+'_OuterRace',[(.052,-.008),(.068,-.008),(.068,.008),(.052,.008)],
            MATS['machined'],parent,'X',(x,0,0),64)
    register(outer,'tapered_bearing_outer_race','Fixed outer race of the tapered hub bearing')
    inner = revolve(name+'_InnerRace',[(.035,-.008),(.047,-.008),(.047,.008),(.035,.008)],
            MATS['steel'],rotating,'X',(x,0,0),64)
    register(inner,'tapered_bearing_inner_race','Rotating inner race of the tapered hub bearing')
    cage = revolve(name+'_Cage',[(.056,-.003),(.061,-.003),(.061,.003),(.056,.003)],
            MATS['bronze'],rotating,'X',(x,0,0),48)
    register(cage,'tapered_bearing_cage','Open annular roller cage')
    for i in range(12):
        a = 2*PI*i/12
        roller = frustum(name+f'_Roller_{i+1:02d}',(x,.058*math.cos(a),.058*math.sin(a)),
                .0042,.0060,.022,MATS['machined'],rotating,
                (math.cos(.18),math.sin(.18)*math.cos(a),math.sin(.18)*math.sin(a)),20)
        register(roller,'tapered_bearing_roller','Truncated-cone rolling element in the bearing cage')
    return root


def create_hub(name,parent,location,side=1):
    root = group(name,parent)
    register(root,'wheel_hub_assembly','Fixed brake support, rotating hub, bearings, brake drum and hub flange')
    root['side'] = side
    rotating = group(name+'_RotatingHub',root)
    register(rotating,'rotating_hub','Hub flange and drum rotate around the X axle')
    revolve(name+'_Spindle',[(0,-.14),(.034,-.14),(.034,.14),(0,.14)],MATS['steel'],root,'X',segments=64)
    revolve(name+'_HubShell',[(.034,-.065),(.067,-.065),(.067,.045),(.126,.045),
            (.126,.065),(.034,.065)],MATS['machined'],rotating,'X',segments=80)
    revolve(name+'_HubFlange',[(.034,-.013),(.130,-.013),(.130,.013),(.034,.013)],
            MATS['steel'],rotating,'X',segments=80)
    bearing(root,rotating,-.055,name+'_InnerBearing')
    bearing(root,rotating,.055,name+'_OuterBearing')
    drum = revolve(name+'_BrakeDrum',[(.215,-.070),(.235,-.070),(.235,.070),(.065,.070),(.065,.058),(.215,.058)],
                   MATS['steel'],rotating,'X',(.040,0,0),96,'brake_drum',
                   'Hollow brake drum with a real inner friction cylinder and open service side',edge=.0008)
    backing = revolve(name+'_BackingPlate',[(.070,-.007),(.210,-.007),(.210,.007),(.070,.007)],
                      MATS['frame'],root,'X',(-.055,0,0),72,'brake_backing',
                      'Fixed annular backing plate with a center opening',edge=.0006)
    for index,(start,end) in enumerate([(math.radians(20),math.radians(160)),(math.radians(200),math.radians(340))]):
        sector(name+f'_Shoe_{index+1}',[(.174,-.025),(.194,-.025),(.194,.025),(.174,.025)],
               start,end,MATS['steel'],root,'X',(-.010,0,0),48,'brake_shoe',
               'Curved steel brake shoe supporting an independent friction lining',edge=.0007)
        sector(name+f'_Lining_{index+1}',[(.194,-.026),(.207,-.026),(.207,.026),(.194,.026)],
               start,end,MATS['friction'],root,'X',(-.010,0,0),48,'brake_friction_lining',
               'Replaceable curved friction lining on the brake shoe',edge=.0005)
    wheel_cylinder = cylinder(name+'_WheelCylinder',.022,.115,(0,0,.171),MATS['machined'],root,(0,1,0),40)
    register(wheel_cylinder,'brake_wheel_cylinder','Hydraulic or air-over-hydraulic wheel cylinder body with opposed pistons')
    for sign in [-1,1]:
        piston = cylinder(name+'_CylinderPiston',.010,.025,(0,sign*.064,.171),MATS['machined'],root,(0,1,0),32)
        register(piston,'wheel_cylinder_piston','Opposed wheel-cylinder piston acting on a brake shoe')
        seal = cylinder(name+'_DustSeal',.024,.012,(0,sign*.048,.171),MATS['rubber'],root,(0,1,0),32)
        register(seal,'wheel_cylinder_dust_seal','Flexible wheel-cylinder dust seal')
        points = []
        for j in range(161):
            t = j/160
            a = 2*PI*16*t
            points.append((.004*math.cos(a),-.072+.144*t,sign*.137+.004*math.sin(a)))
        spring = tube_curve(name+f'_ReturnSpring_{sign}',points,.0013,MATS['machined'],root,8,
                            'brake_return_spring','Helical return spring between the two brake shoes')
    camshaft = cylinder(name+'_SCamShaft',.012,.175,(0,0,-.142),MATS['machined'],root,(1,0,0),40)
    register(camshaft,'s_cam_shaft','Brake camshaft passing through the backing plate')
    cam = revolve(name+'_SCamLobe',[(0,-.008),(.031,-.008),(.031,.008),(0,.008)],
                  MATS['machined'],root,'X',(.070,.008,-.142),48,'s_cam',
                  'Offset cam lobe spreading the brake shoes, not a decorative disk')
    slack = box(name+'_SlackAdjuster',(.104,-.065,-.142),(.018,.125,.020),MATS['steel'],root,.003)
    register(slack,'slack_adjuster','Slack adjuster arm linking the air chamber to the camshaft')
    chamber = cylinder(name+'_AirChamber',.042,.080,(.118,-.140,-.142),MATS['frame'],root,(0,1,0),48)
    register(chamber,'brake_air_chamber','Air brake chamber driving the slack adjuster')
    for i in range(10):
        angle = 2*PI*i/10
        stud = cylinder(name+f'_HubStud_{i+1:02d}',.0075,.073,(0,.108*math.cos(angle),.108*math.sin(angle)),
                 MATS['machined'],rotating,(1,0,0),24)
        register(stud,'wheel_hub_stud','Hub flange stud aligned to the wheel nut')
    root.location = location
    if side < 0:
        mirror_assembly(root)
    return root


def create_wheel(name,parent,location,side=1,rear=False,dual='front'):
    root = group(name,parent)
    register(root,'wheel_rotation_assembly','Tire and dished rim rotate together around their true wheel center')
    root['side'] = side
    root['dualPosition'] = dual
    tire(root,rear,name+'_Tire')
    wheel_abs = abs(location[0])
    hub_abs = 1.10 if not rear else .97
    offset = hub_abs-wheel_abs
    rim(root,offset,name+'_Rim')
    for i in range(10):
        a = 2*PI*i/10
        nut = cylinder(name+f'_Nut_{i+1:02d}',.012,.012,(offset+side*.048,.108*math.cos(a),.108*math.sin(a)),
                       MATS['machined'],root,(1,0,0),6)
        register(nut,'wheel_nut','Hexagonal wheel nut with a real shank aligned to a hub stud')
        bevel(nut,.0006)
    root.location = location
    if side < 0:
        mirror_assembly(root)
    return root
