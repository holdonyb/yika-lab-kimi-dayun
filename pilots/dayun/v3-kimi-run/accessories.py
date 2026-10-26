import math
from geo import PI, group, register, mesh, box, cylinder, revolve, sector, tube_curve, boolean, bevel
from driveline import gear, beam
from studio import palette

MATS = palette()


def pipe(name,parent,points,radius,wall,material=None):
    from mathutils import Vector
    material = material or MATS['steel']
    if wall <= 0 or wall >= radius:
        raise ValueError('Pipe wall must be positive and smaller than the radius')
    coords = [Vector(point) for point in points]
    verts = []
    sides = 16
    for i,point in enumerate(coords):
        tangent = (coords[min(i+1,len(coords)-1)]-coords[max(0,i-1)]).normalized()
        reference = Vector((0,0,1)) if abs(tangent.z) < .9 else Vector((0,1,0))
        normal = tangent.cross(reference).normalized()
        binormal = tangent.cross(normal).normalized()
        for r in [radius,radius-wall]:
            for j in range(sides):
                angle = 2*PI*j/sides
                verts.append(tuple(point + r*(normal*math.cos(angle)+binormal*math.sin(angle))))
    faces = []
    for i in range(len(coords)-1):
        for j in range(sides):
            k = (j+1)%sides
            a,b = i*2*sides,(i+1)*2*sides
            faces.append((a+j,a+k,b+k,b+j))
            faces.append((a+sides+k,a+sides+j,b+sides+j,b+sides+k))
    for j in range(sides):
        k = (j+1)%sides
        faces.append((j,k,sides+k,sides+j))
        last = (len(coords)-1)*2*sides
        faces.append((last+j,last+sides+j,last+sides+k,last+k))
    return mesh(name,verts,faces,material,parent)


def cylinder_head(parent,controller):
    root = group('GenericCylinderHead',parent)
    register(root,'cylinder_head_and_valvetrain','Generic four-valve-per-cylinder head, guides, springs, rockers and camshaft; not OEM layout')
    deck = box('Cylinder head deck',(0,0,.435),(1.045,.188,.065),MATS['aluminum'],root)
    for x in [(i-2.5)*.165 for i in range(6)]:
        cutter = cylinder('Head fire bore',.064,.10,(x,0,.435),MATS['aluminum'],root,vertices=64)
        boolean(deck,cutter)
    bevel(deck,.002)
    for i in range(6):
        x = (i-2.5)*.165
        for dx in [-.026,.026]:
            for side in [-1,1]:
                y = side*.034
                valve = group(f'Valve_{i+1}_{dx}_{side}',root,(x+dx,y,0))
                register(valve,'poppet_valve','Independent valve head, stem, guide, spring and retainer')
                cylinder('Valve stem',.0045,.087,(0,0,.446),MATS['machined'],valve,vertices=32)
                cylinder('Valve head',.016,.005,(0,0,.403),MATS['machined'],valve,vertices=48)
                revolve('Valve guide',[(.0046,-.018),(.009,-.018),(.009,.018),(.0046,.018)],
                        MATS['bronze'],valve,'Z',(0,0,.446),48)
                points = []
                for j in range(121):
                    t = j/120
                    a = 2*PI*6*t
                    points.append((.0105*math.cos(a),.0105*math.sin(a),.456+.037*t))
                tube_curve('Valve spring',points,.0014,MATS['steel'],valve,8)
                revolve('Spring retainer',[(.0045,-.002),(.013,-.002),(.013,.002),(.0045,.002)],
                        MATS['machined'],valve,'Z',(0,0,.494),40)
                beam('Rocker arm',root,(x+dx,-.020,.505),(x+dx,y,.491),.006,MATS['steel'])
    cam = group('Camshaft',root,(0,.060,.520))
    register(cam,'camshaft','Camshaft with eccentric lobes and a 1:2 kinematic drive relationship')
    cylinder('Camshaft tube',.013,1.055,(0,0,0),MATS['machined'],cam,(1,0,0),64)
    for i in range(6):
        x = (i-2.5)*.165
        for dx in [-.026,.026]:
            for side in [-1,1]:
                revolve('Eccentric cam lobe',[(.010,-.005),(.024,-.005),(.024,.005),(.010,.005)],
                        MATS['machined'],cam,'X',(x+dx,.007,0),48)
    gear('Cam timing gear',cam,(-.54,0,0),.073,32,.024,MATS['steel'],'X',0)
    curve = cam.driver_add('rotation_euler',0)
    variable = curve.driver.variables.new()
    variable.name = 'a'
    variable.type = 'SINGLE_PROP'
    variable.targets[0].id = controller
    variable.targets[0].data_path = '["angle"]'
    curve.driver.expression = 'a*.5'
    cover = box('Cylinder head cover',(0,0,.565),(1.035,.204,.034),MATS['steel'],root,.012)
    register(cover,'cylinder_head_cover','Removable cylinder head cover exposing the valvetrain')
    for x in [-.47,0,.47]:
        for y in [-.072,.072]:
            cylinder('Head cover fastener',.0055,.038,(x,y,.565),MATS['machined'],root,vertices=6)
    return {'root':root,'cam':cam,'cover':cover}


def radiator(parent,controller):
    root = group('RadiatorAndFan',parent,(0,-3.10,1.05))
    register(root,'radiator_and_fan','Open fin-and-tube radiator, shroud, curved fan and coolant connections')
    for z in [-.31,.31]:
        box('Radiator header tank',(0,0,z),(1.12,.13,.075),MATS['frame'],root,.018)
    for x in [-.52,.52]:
        box('Radiator side rail',(x,0,0),(.028,.095,.60),MATS['frame'],root,.004)
    for i in range(22):
        x = -.49+i*.0465
        cylinder('Cooling tube',.006,.56,(x,0,0),MATS['aluminum'],root,vertices=20)
    for i in range(23):
        z = -.27+i*.024
        box('Radiator fin',(0,0,z),(1.02,.045,.0022),MATS['aluminum'],root,.0005)
    revolve('Fan shroud',[(.235,-.028),(.280,-.028),(.280,.028),(.235,.028)],
            MATS['frame'],root,'Y',(0,.09,0),72)
    fan = group('CoolingFan',root,(0,.075,0))
    register(fan,'cooling_fan','Six swept curved blades and a driven fan hub')
    cylinder('Fan hub',.054,.048,(0,0,0),MATS['machined'],fan,(0,1,0),48)
    for i in range(6):
        a = 2*PI*i/6
        points = [(.052,-.016),(.105,-.028),(.222,-.020),(.255,.007),(.238,.031),(.118,.031)]
        verts = []
        for r,y in points:
            for angle in [a,a+.17]:
                verts.append((r*math.cos(angle),y,r*math.sin(angle)))
        faces = [(j,j+1,(j+2)%len(verts)) for j in range(0,len(verts)-1,2)]
        blade = mesh('Swept fan blade',verts,faces,MATS['steel'],fan)
        solid = blade.modifiers.new('Blade thickness','SOLIDIFY')
        solid.thickness = .003
    curve = fan.driver_add('rotation_euler',1)
    variable = curve.driver.variables.new()
    variable.name = 'a'
    variable.type = 'SINGLE_PROP'
    variable.targets[0].id = controller
    variable.targets[0].data_path = '["angle"]'
    curve.driver.expression = 'a*1.2'
    pipe('Upper coolant hose',root,[(.36,0,.30),(.42,.12,.36),(.33,.35,.36),(.20,.50,.24)],.024,.004,MATS['rubber'])
    return {'root':root,'fan':fan}


def air_tanks(parent):
    root = group('AirReservoirs',parent,(.40,.55,.65))
    register(root,'air_reservoirs','Two strapped pressure vessels with drain valves, fittings and mounting feet')
    for y in [-.22,.22]:
        revolve('Air tank pressure vessel',[(0,-.31),(.095,-.29),(.14,-.24),(.14,.24),(.095,.29),(0,.31)],
                MATS['steel'],root,'Y',(0,y,0),72)
        for dy in [-.16,.16]:
            sector('Tank retaining strap',[(.143,-.012),(.154,-.012),(.154,.012),(.143,.012)],
                   0,2*PI,MATS['frame'],root,'Y',(0,y+dy,0),64)
        cylinder('Tank drain valve',.009,.035,(0,y,-.156),MATS['machined'],root,vertices=24)
        cylinder('Tank outlet fitting',.011,.030,(0,y+.31,0),MATS['machined'],root,(0,1,0),32)
    return root


def battery_modules(parent):
    root = group('BatteryModules',parent,(-1.045,.16,.77))
    register(root,'battery_modules','Two battery cases with cell caps, terminal posts and hold-down structure')
    for y in [-.235,.235]:
        box('Battery case',(0,y,0),(.36,.36,.26),MATS['frame'],root,.014)
        box('Battery lid',(0,y,.141),(.36,.36,.023),MATS['steel'],root,.005)
        for i in range(6):
            x = -.12+(i%3)*.12
            yy = y-.08+(i//3)*.16
            cylinder('Battery cell cap',.018,.009,(x,yy,.159),MATS['frame'],root,vertices=32)
        for side in [-1,1]:
            cylinder('Battery terminal',.010,.022,(side*.12,y-.12,.167),MATS['machined'],root,vertices=32)
    box('Battery hold down',(0,0,.187),(.06,.89,.020),MATS['steel'],root,.003)
    box('Battery tray bottom',(0,0,-.15),(.43,.90,.022),MATS['steel'],root,.004)
    for side in [-1,1]:
        box('Battery tray side',(side*.20,0,0),(.020,.88,.26),MATS['steel'],root,.004)
        box('Battery tray end',(0,side*.44,0),(.40,.020,.26),MATS['steel'],root,.004)
    return root


def exhaust(parent):
    root = group('ExhaustComponents',parent,(-.72,.38,.68))
    register(root,'exhaust_components','Hollow inlet/outlet pipes, muffler shell, baffles and retaining bands')
    revolve('Muffler shell',[(.088,-.31),(.109,-.31),(.109,.31),(.088,.31)],
            MATS['steel'],root,'Y',segments=80)
    for y in [-.30,.30]:
        revolve('Muffler baffle',[(.022,-.004),(.090,-.004),(.090,.004),(.022,.004)],
                MATS['steel'],root,'Y',(0,y,0),64)
        sector('Muffler band',[(.110,-.011),(.119,-.011),(.119,.011),(.110,.011)],
               0,2*PI,MATS['frame'],root,'Y',(0,y*.75,0),64)
    pipe('Exhaust inlet',root,[(0,0,-.34),(.03,-.43,-.04),(.16,-.52,-.04),(.19,-.60,.02)],.031,.003,MATS['steel'])
    pipe('Exhaust outlet',root,[(0,0,.34),(-.02,.42,.04),(-.05,.58,.10),(-.04,.68,.19)],.031,.003,MATS['steel'])
    return root


def refine_seats_and_dash(cab):
    for side in [-1,1]:
        x,y = side*.57,-1.63
        box('Seat suspension pedestal',(x,y,1.36),(.43,.45,.30),MATS['frame'],cab,.035)
        box('Seat cushion',(x,y,1.60),(.62,.65,.17),MATS['frame'],cab,.065)
        seat_back = box('Seat back',(x,y+.30,1.99),(.61,.17,.74),MATS['frame'],cab,.065)
        seat_back.rotation_euler.x = -.12
        box('Seat headrest',(x,y+.32,2.42),(.36,.17,.20),MATS['frame'],cab,.048)
        for dx in [-.28,.28]:
            box('Seat side bolster',(x+dx,y,1.66),(.09,.59,.14),MATS['frame'],cab,.04)
            box('Seat armrest',(x+dx,y+.02,1.88),(.07,.34,.06),MATS['frame'],cab,.022)
        points = [(x-.25,y-.26,1.69),(x+.25,y-.26,1.69),(x+.25,y+.25,1.69),(x-.25,y+.25,1.69),(x-.25,y-.26,1.69)]
        tube_curve('Seat sewn edge',points,.0025,MATS['steel'],cab,8)
    box('Dashboard main',(0,-2.99,2.28),(2.10,.43,.24),MATS['frame'],cab,.070)
    for i in range(5):
        x = -.75+(i%3)*.13
        z = 2.34+(i//3)*.07
        cylinder('Instrument bezel',.038,.014,(x,-2.752,z),MATS['machined'],cab,(0,1,0),48)
        cylinder('Instrument glass',.032,.016,(x,-2.744,z),MATS['glass'],cab,(0,1,0),48)
        needle = box('Instrument needle',(x,-2.733,z),(.003,.004,.022),MATS['ivory'],cab,.001)
        needle.rotation_euler.y = .4
    box('Dashboard display',(-.03,-2.745,2.35),(.28,.028,.155),MATS['glass'],cab,.013)
    wheel = revolve('Steering wheel rim',[(.181,-.009),(.193,-.009),(.193,.009),(.181,.009)],
                    MATS['frame'],cab,'Y',(-.57,-2.54,2.40),80)
    wheel.rotation_euler.x = .55
    for a in [0,2*PI/3,4*PI/3]:
        beam('Steering spoke',cab,(-.57,-2.54,2.40),(-.57+.18*math.cos(a),-2.54,2.40+.18*math.sin(a)),.009,MATS['steel'])
    cylinder('Steering hub',.048,.045,(-.57,-2.54,2.40),MATS['frame'],cab,(0,1,0),48)
    beam('Steering column',cab,(-.57,-2.78,2.20),(-.57,-2.54,2.40),.025,MATS['frame'])


def c_channel_frames(parent,material):
    for side in [-1,1]:
        root = group('CChannelRail_'+str(side),parent)
        register(root,'c_channel_frame_rail','Open C-section longitudinal frame rail, not a solid rectangular block')
        box('Rail web',(side*.76,0,1.005),(.026,6.61,.245),material,root,.004)
        for z in [.883,1.127]:
            box('Rail flange',(side*.76,0,z),(.215,6.61,.029),material,root,.004)
