from pathlib import Path
import sys, json, math, random, time, hashlib
import bpy
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parent
SRC=ROOT.parents[2]/'dayun'/'v3-kimi-run'
# ROOT is reboot_20261026/edit_show_v5/collisions
SRC=ROOT.parents[2]/'dayun'/'v3-kimi-run' if (ROOT.parents[2]/'dayun').exists() else ROOT.parents[3]/'dayun'/'v3-kimi-run'
ARGS=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
MODE=ARGS[0] if ARGS else 'freeze'
KIND=ARGS[1] if len(ARGS)>1 else 'buttons'
FPS=24; END=228
TARGETS=[]
FONT=None
COLORS=[(.98,.20,.12),(.02,.62,.78),(.98,.63,.06),(.28,.85,.48),(.56,.28,.91),(.98,.36,.65)]
TITLES={'buttons':'下次一定，今天就撞','folders':'最终版的最终版','loading':'这个99%，我忍很久了','deadline':'明天一定开始','errors':'报错？一起下班','vram':'显存不够，物理扩容','crates':'禁止套娃','danmaku':'弹幕护体','revision':'甲方：再改亿版','banana':'香蕉皮也能排队？','triple':'这次真的三连了','coins':'画的饼，都落地了'}
DELIVERY_FRAMES={'buttons':144,'folders':144,'loading':144,'deadline':168,'errors':144,'vram':144,'crates':168,'danmaku':144,'revision':168,'banana':192,'triple':168,'coins':168}

def mat(name,c,metal=0,rough=.35,emission=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
    s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=(*c,1);s.inputs['Metallic'].default_value=metal;s.inputs['Roughness'].default_value=rough
    if emission:s.inputs['Emission Color'].default_value=(*c,1);s.inputs['Emission Strength'].default_value=emission
    return m
def activate(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def mesh(name,verts,faces,m,loc=(0,0,0)):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update();o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc
    if m:d.materials.append(m)
    return o
def cube(name,loc,dims,m,edge=.035):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;activate(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if m:o.data.materials.append(m)
    if edge:
        b=o.modifiers.new('Soft prop edges','BEVEL');b.width=edge;b.segments=3
        n=o.modifiers.new('Face normals','WEIGHTED_NORMAL')
    return o
def cyl(name,loc,r,depth,m,rot=(math.pi/2,0,0),vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=loc,rotation=rot);o=bpy.context.object;o.name=name
    activate(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
    b=o.modifiers.new('Edge','BEVEL');b.width=.035;b.segments=2
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    return o
def rb(o,mass=1,shape='BOX',passive=False,moving=False):
    activate(o);bpy.ops.rigidbody.object_add();r=o.rigid_body;r.type='PASSIVE' if passive else 'ACTIVE';r.kinematic=moving;r.mass=mass;r.collision_shape=shape;r.friction=.64;r.restitution=.13;r.use_margin=True;r.collision_margin=.002;r.linear_damping=.08;r.angular_damping=.13;r.use_deactivation=False
    if not passive and not moving:TARGETS.append(o)
    return o
def text(body,loc,size=.45,parent=None,color=(.98,.98,.93),rot=(math.pi/2,0,0)):
    d=bpy.data.curves.new('Label '+body,'FONT');d.body=body;d.align_x='CENTER';d.align_y='CENTER';d.size=size;d.extrude=.004;d.resolution_u=3
    if FONT:d.font=FONT
    o=bpy.data.objects.new('Label '+body,d);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=rot;d.materials.append(mat('Ink '+body,color,rough=.7))
    if parent:
        w=o.matrix_world.copy();bpy.context.view_layer.update();w=o.matrix_world.copy();o.parent=parent;o.matrix_world=w
    return o
def parent_keep(o,p):
    bpy.context.view_layer.update();w=o.matrix_world.copy();o.parent=p;o.matrix_world=w
def polygon_prop(name,pts,depth,loc,m):
    n=len(pts);v=[(x,y,z) for y in [-depth/2,depth/2] for x,z in pts];f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    o=mesh(name,v,f,m,loc);b=o.modifiers.new('Rounded rim','BEVEL');b.width=.025;b.segments=2;return o
def empty(name):
    o=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(o);return o

def freeze():
    src=SRC/'p2_bricks.blend';bpy.ops.wm.open_mainfile(filepath=str(src));sc=bpy.context.scene;sc.frame_set(1);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    old=list(bpy.data.objects);wheel_names=['Front_R','Front_R_L','Mid_R_Inner','Mid_R_Inner_L','Mid_R_Outer','Mid_R_Outer_L','Rear_R_Inner','Rear_R_Inner_L','Rear_R_Outer','Rear_R_Outer_L'];groups={'body':[]};pivots={}
    tr=bpy.data.objects.get('TruckAssembly');members=set(tr.children_recursive) if tr else set(old);baseinv=tr.matrix_world.inverted() if tr else Matrix.Identity(4)
    for o in old:
        if o.type not in ['MESH','FONT','CURVE'] or o not in members or o.hide_render or not o.visible_get():continue
        k='body';p=o
        while p:
            if p.name in wheel_names:k=p.name;pivots[k]=baseinv@p.matrix_world.translation;break
            p=p.parent
        groups.setdefault(k,[]).append(o)
    result=[];counts={}
    for k,objs in groups.items():
        verts=[];faces=[];indices=[];smooth=[];mats=[];lookup={};pivot=pivots.get(k,Vector((0,0,0)))
        for o in objs:
            ev=o.evaluated_get(dg);me=ev.to_mesh();base=len(verts);verts.extend([tuple(baseinv@ev.matrix_world@v.co-pivot) for v in me.vertices])
            mp={}
            for i,slot in enumerate(o.material_slots):
                m=slot.material
                if m and m.name not in lookup:lookup[m.name]=len(mats);mats.append(m)
                mp[i]=lookup.get(m.name if m else '',0)
            for p in me.polygons:faces.append(tuple(base+i for i in p.vertices));indices.append(mp.get(p.material_index,0));smooth.append(p.use_smooth)
            ev.to_mesh_clear()
        o=mesh('KimiFrozen_'+k,verts,faces,None,pivot)
        for m in mats:o.data.materials.append(m)
        for p,i,s in zip(o.data.polygons,indices,smooth):p.material_index=i;p.use_smooth=s
        o['source']='Kimi K3.1 Pro p2_bricks.blend, evaluated assembled frame 1, merged without geometry edits';result.append(o);counts[k]={'source_objects':len(objs),'vertices':len(verts),'polygons':len(faces),'pivot':list(pivot)}
    frozen_scene=bpy.data.scenes.new('Frozen Kimi assembled truck')
    for o in result:
        frozen_scene.collection.objects.link(o)
        for c in list(o.users_collection):
            if c!=frozen_scene.collection:c.objects.unlink(o)
    for m in {m for o in result for m in o.data.materials if m}:
        if m.use_nodes:
            s=m.node_tree.nodes.get('Principled BSDF')
            if s and s.inputs['Normal'].is_linked:
                for link in list(s.inputs['Normal'].links):m.node_tree.links.remove(link)
    bpy.data.libraries.write(str(ROOT/'kimi_truck_frozen.blend'),{frozen_scene},fake_user=True,compress=True)
    (ROOT/'source_manifest.json').write_text(json.dumps({'source':str(src),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'authorship':'Kimi original vehicle geometry; Codex froze evaluated frame 1, merged draw meshes and removed subpixel bump inputs for rendering; all targets/cameras/simulations by Codex','groups':counts},ensure_ascii=False,indent=2),encoding='utf8')
    print('FROZEN',counts,flush=True)

def targets(kind):
    p=[mat('Prop '+str(i),c,.08,.28) for i,c in enumerate(COLORS)];dark=mat('Charcoal',(.018,.025,.045),.15,.28);gold=mat('Coin gold',(1,.52,.07),.68,.24)
    if kind=='buttons':
        for i,label in enumerate(['下次','一定','这次！']):
            x=[-.65,.65,-.85][i];o=rb(cyl('Huge button '+str(i),(x,-6-i*2.7,1.25),1.24,.38,p[i]),7,'CONVEX_HULL');text(label,(x,-6-i*2.7-.21,1.25),.74,o)
    elif kind=='folders':
        for i in range(7):
            w=4.2-i*.34;h=2.8-i*.19;y=-6-i*.85
            pts=[(-w/2,-h/2),(w/2,-h/2),(w/2,h/2-.35),(.15*w,h/2-.35),(.06*w,h/2),(-w/2,h/2)]
            o=rb(polygon_prop('Folder '+str(i),pts,.22,(0,y,h/2+.01),p[2 if i%2==0 else 3]),2,'CONVEX_HULL');text('最终版' if i==0 else ('FINAL_'+str(i)),(0,y-.13,h*.52),.50 if i==0 else .35,o,color=(.10,.11,.08));o.rotation_euler.z=.08*(-1 if i%2 else 1)
    elif kind=='loading':
        for i in range(20):
            x=(i-9.5)*.255;o=rb(cube('Progress segment '+str(i),(x,-6,.96),(.24,.8,1.9),p[3 if i<19 else 0],.015),1.4)
        text('99%',(0,-6.43,2.65),1.0)
        # the last stubborn percent is a separate heavy red pedestal; impact scatters the entire bar
    elif kind=='deadline':
        for i in range(8):
            y=-5.8-i*.85;o=rb(cube('Calendar domino '+str(i),(0,y,1.62),(2.2,.32,3.22),p[0] if i==7 else mat('Calendar ivory '+str(i),(.84,.84,.76))),4)
            bar=cube('Calendar red header',(0,y-.18,2.97),(2.14,.025,.43),p[0],.01);parent_keep(bar,o);text('DDL' if i==7 else str(24+i),(0,y-.19,1.65),1.02,o,color=(.12,.13,.16));text('明天再说',(0,y-.19,.63),.32,o,color=(.2,.2,.2))
            rb(cube('Calendar floor trip '+str(i),(0,y-.23,.045),(2.25,.08,.09),dark,.01),passive=True)
    elif kind=='errors':
        for row in range(4):
            for col in range(3):
                x=(col-1)*1.46;z=.422+row*.844;y=-6-row*.01;o=rb(cube('Error dialog '+str(row*3+col),(x,y,z),(1.42,.72,.84),p[0],.04),1.8);text('ERROR',(x,y-.38,z),.24,o)
                for a in [-.14,.14]:
                    line=cube('Close x',(x+.53,y-.389,z+.22),(.20,.025,.035),p[2],.006);line.rotation_euler.y=a*5.5;parent_keep(line,o)
    elif kind=='vram':
        for i in range(8):
            x=(i-3.5)*.64;o=rb(cube('VRAM module '+str(i),(x,-6,1.43),(.57,.42,2.84),p[3],.018),1.4)
            for z in [.65,1.25,1.85,2.45]:
                chip=cube('Black memory chip',(x,-6.24,z),(.40,.08,.40),dark,.01);parent_keep(chip,o)
            text('8G',(x,-6.30,.18),.21,o,color=(1,.80,.24))
    elif kind=='crates':
        wood=mat('Warm wood',(.49,.21,.065),.05,.6)
        for row in range(3):
            for col in range(3-row):
                x=(col-(2-row)/2)*1.53;z=.742+row*1.485;o=rb(cube('Nested crate '+str(row)+str(col),(x,-6,z),(1.48,1.10,1.48),wood,.025),3.5)
                for a in [-.75,.75]:
                    beam=cube('Crate diagonal',(x,-6.58,z),(1.65,.05,.12),p[2],.01);beam.rotation_euler.y=a;parent_keep(beam,o)
                text('套娃' if row else '禁止',(x,-6.62,z),.32,o)
    elif kind=='danmaku':
        labels=['前方高能','？？？','这合理吗','好活','弹幕护体','来了来了','绷不住了','再来一遍']
        for row in range(4):
            for col in range(2):
                i=row*2+col;x=(col-.5)*2.44;z=.387+row*.774;o=rb(cube('Danmaku shield '+str(i),(x,-6,z),(2.40,.65,.77),p[i%6],.15),2.1);text(labels[i],(x,-6.36,z),.37,o)
    elif kind=='revision':
        for i in range(9):
            y=-5.7-i*1.0;x=.55*(-1 if i%2 else 1);o=rb(cube('Revision paper '+str(i),(x,y,1.16),(1.9,.18,2.30),mat('Paper '+str(i),(.83-i*.025,.86-i*.02,.87))),.6);o.rigid_body.restitution=.3
            text('再改一版' if i==0 else '第 '+str(i+1)+' 版',(x,y-.11,1.85),.35,o,color=(.80,.06,.06));text('FINAL.psd',(x,y-.11,1.25),.29,o,color=(.13,.16,.19))
            for z in [.45,.65,.85]:
                line=cube('Paper line',(x,y-.14,z),(1.5,.015,.025),dark,0);parent_keep(line,o)
            o.rotation_euler.z=.4*(-1 if i%2 else 1)
    elif kind=='banana':
        for i in range(14):
            x=math.sin(i*.6)*1.55;y=-5.8-i*.65;pts=[(-.48,-.03),(-.30,.19),(-.17,.56),(-.02,1.55),(.13,1.1),(.20,.42),(.54,.03),(.37,-.02),(.03,.15),(-.18,-.02)]
            o=rb(polygon_prop('Banana peel domino '+str(i),pts,.38,(x,y,.05),p[2]),.8,'CONVEX_HULL');o.rigid_body.restitution=.25
    elif kind=='triple':
        shapes=[('LIKE',[(-.75,-1),(.5,-1),(.85,-.25),(.7,.25),(.2,.25),(.2,1),(-.15,1.15),(-.4,.25),(-.75,.25)]),('COIN',[(1.1*math.cos(a*math.pi/24),1.1*math.sin(a*math.pi/24)) for a in range(48)]),('FAVORITE',[((1.2 if i%2==0 else .54)*math.sin(i*math.pi/5),(1.2 if i%2==0 else .54)*math.cos(i*math.pi/5)) for i in range(10)])]
        for i,(label,pts) in enumerate(shapes):
            z=-min(p[1] for p in pts)+.004;o=rb(polygon_prop(label,pts,.65,(0,-6-i*2.2,z),p[[5,2,1][i]]),4,'CONVEX_HULL');text(['赞','币','藏'][i],(0,-6-i*2.2-.35,z),.65,o,color=(.09,.12,.16))
    elif kind=='coins':
        for j in range(3):
            for i in range(7):
                o=rb(cyl('Pancake stack '+str(j)+str(i),((j-1)*1.43,-6,.134+i*.264),.68,.26,gold,rot=(0,0,0)),1.5,'CYLINDER')
                text('饼',((j-1)*1.43,-6,.274+i*.264),.6,o,color=(.39,.15,.015),rot=(0,0,0))
    return TARGETS

def area(name,pos,power,color,size,target):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
def look(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def setup_scene():
    global FONT,TARGETS
    TARGETS=[];bpy.ops.wm.open_mainfile(filepath=str(ROOT/'kimi_truck_frozen.blend'));sc=bpy.context.scene
    for o in bpy.data.objects:
        if o.name.startswith('KimiFrozen_') and o.name not in sc.objects:sc.collection.objects.link(o)
    FONT=bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')
    sc.frame_start=1;sc.frame_end=END;sc.render.fps=FPS
    sc.world=bpy.data.worlds.new('Show black-blue');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.12,.17,.25,1);sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.3
    sc.render.engine='BLENDER_EEVEE';sc.eevee.taa_render_samples=16;sc.eevee.use_raytracing=False;sc.render.resolution_x=1920;sc.render.resolution_y=1080;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.render.image_settings.compression=15
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.3
    bpy.ops.rigidbody.world_add();w=sc.rigidbody_world;w.substeps_per_frame=16;w.solver_iterations=50;w.use_split_impulse=True;w.point_cache.frame_start=1;w.point_cache.frame_end=END
    floor=rb(cube('Arena floor',(0,-7,-.18),(70,85,.36),mat('Floor',(.045,.07,.105),.05,.58),0),passive=True)
    line=mat('Runway lines',(.06,.65,.8),rough=.3,emission=.4)
    for x in [-3.1,3.1]:cube('Runway edge',(x,-10,.005),(.055,45,.009),line,0)
    for y in range(-25,16,3):cube('Lane dash',(0,y,.006),(.06,.80,.01),line,0)
    area('Key',(1,-9,14),4500,(.86,.92,1),10,(0,-6,0));area('Warm rim',(-9,-2,7),2600,(1,.47,.17),8,(0,-7,1));area('Front fill',(8,-18,8),3200,(.42,.72,1),10,(0,-7,1))
    vehicle=empty('KimiTruck_animated_proxy_root')
    for o in list(bpy.data.objects):
        if o.name.startswith('KimiFrozen_'):parent_keep(o,vehicle)
    hull=rb(cube('Cab collision proxy',(0,-2.14,2.18),(2.47,3.24,3.32),None,0),moving=True,shape='BOX');hull.hide_render=True;hull.parent=vehicle
    lip=rb(cube('Upper grille contact',(0,-3.76,2.20),(2.30,.14,.24),None,0),moving=True);lip.hide_render=True;lip.parent=vehicle
    for x in [-1.1,1.1]:
        for y in [-2.48,1.27,2.60]:
            o=cyl('Tire collision proxy',(x,y,.536),.536,.38,mat('Hidden rubber',(.01,.01,.01)),rot=(0,math.pi/2,0),vertices=24);rb(o,moving=True,shape='CONVEX_HULL');o.hide_render=True;o.parent=vehicle
    for f in range(1,END+1):
        t=(f-1)/24
        if t<1.5:travel=3*t
        elif t<2.1:
            q=t-1.5;travel=4.5+3*q+5*q*q
        elif t<2.8:travel=8.1+9*(t-2.1)
        elif t<3.6:
            q=t-2.8;travel=14.4+9*q-5.625*q*q
        else:travel=18
        if KIND=='deadline':
            if t<1.5:travel=3*t
            elif t<2.0:
                q=t-1.5;travel=4.5+3*q+2*q*q
            elif t<2.4:
                q=t-2;travel=6.5+5*q-6.25*q*q
            else:travel=7.5
        vehicle.location=(0,4-travel,0);vehicle.keyframe_insert('location',frame=f)
        for o in vehicle.children:
            if o.name.startswith('KimiFrozen_') and o.name!='KimiFrozen_body':o.rotation_euler.x=travel/.536;o.keyframe_insert('rotation_euler',frame=f)
    cd=bpy.data.cameras.new('Show camera');cam=bpy.data.objects.new('Show camera',cd);bpy.context.collection.objects.link(cam);sc.camera=cam;cd.lens=35;cd.clip_end=200
    views={'buttons':(15,-12,8.5),'folders':(12,-17,9),'loading':(10,-15,11),'deadline':(13,-15,8),'errors':(10,-15,7.5),'vram':(14,-13,7),'crates':(13,-14,10),'danmaku':(9,-16,6.5),'revision':(12,-16,8),'banana':(12,-16,12),'triple':(11,-17,7.5),'coins':(12,-14,9)}
    offset=Vector(views.get(KIND,(14,-13,8)))
    for f in range(1,END+1):
        t=(f-1)/24;q=max(0,min(1,(t-1.4)/3.2));q=q*q*(3-2*q);target=Vector((0,-4.0-(5 if KIND=='deadline' else 14.5)*q,1.2));angle=max(0,t-4.6)*.025;off=Matrix.Rotation(angle,4,'Z')@offset;cam.location=target+off;look(cam,target);cam.keyframe_insert('location',frame=f);cam.keyframe_insert('rotation_euler',frame=f);cam.data.lens=35-3*q;cam.data.keyframe_insert('lens',frame=f)
    return sc,vehicle

def build():
    sc,vehicle=setup_scene();targets(KIND);folder=ROOT/KIND;folder.mkdir(exist_ok=True);sc.frame_set(1);bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'scene.blend'),compress=True)
    poses=[];initial={};maxpre=0;changed=0
    for f in range(1,END+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get();row={}
        for o in TARGETS:
            mx=o.evaluated_get(dg).matrix_world;loc=mx.translation;row[o.name]={'p':list(loc),'q':list(mx.to_quaternion())}
            if f==1:initial[o.name]=loc.copy()
            if f<=36:maxpre=max(maxpre,(loc-initial[o.name]).length)
        poses.append({'frame':f,'targets':row})
    changed=sum((Vector(poses[-1]['targets'][n]['p'])-p).length>.25 for n,p in initial.items());cache=sc.rigidbody_world.point_cache
    with bpy.context.temp_override(scene=sc,point_cache=cache):bpy.ops.ptcache.bake_from_cache()
    sc.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(folder/'scene.blend'),compress=True)
    report={'kind':KIND,'title':TITLES[KIND],'fps':FPS,'frames':END,'duration':END/FPS,'target_count':len(TARGETS),'cache_baked':cache.is_baked,'maximum_target_displacement_before_1_5s':maxpre,'targets_moved_over_25cm':changed,'target_animation_channels':sum(bool(o.animation_data) for o in TARGETS),'simulation':'Blender Bullet target rigid bodies; animated Kimi vehicle contact proxies. Artistic prop masses, gravity 9.81.','authorship':'Kimi vehicle mesh frozen; Codex props, physics scene, camera and rendering','poses':poses}
    (folder/'physics.json').write_text(json.dumps(report,ensure_ascii=False),encoding='utf8');print('BUILT',KIND,len(TARGETS),'pre',maxpre,'moved',changed,'baked',cache.is_baked,flush=True)

def render():
    folder=ROOT/KIND;bpy.ops.wm.open_mainfile(filepath=str(folder/'scene.blend'));sc=bpy.context.scene;draft='--draft' in ARGS;stills='--stills' in ARGS
    sc.render.resolution_x=768 if draft else 1920;sc.render.resolution_y=432 if draft else 1080;sc.eevee.taa_render_samples=8 if draft else 16
    out=folder/('draft_v5' if draft else 'frames_final');out.mkdir(exist_ok=True)
    frames=[1,36,52,64,80,100,128,160,192] if stills else range(1,DELIVERY_FRAMES[KIND]+1,2 if draft else 1)
    for f in frames:
        target=out/f'{f:04d}.png'
        if target.exists() and '--overwrite' not in ARGS:continue
        sc.frame_set(f);sc.render.filepath=str(target);t=time.time();bpy.ops.render.render(write_still=True);print('FRAME',KIND,f,round(time.time()-t,2),flush=True)
    print('RENDER_DONE',KIND,draft,stills,flush=True)

def breakout():
    sc,vehicle=setup_scene();sc.frame_end=216;sc.rigidbody_world.point_cache.frame_end=216;vehicle.animation_data_clear()
    for o in vehicle.children:
        if o.animation_data:o.animation_data_clear()
    cam=sc.camera;cam.animation_data_clear();cam.location=(.60,-21,2.80);look(cam,(0,-6,2.20));cam.data.lens=45
    for f in range(1,217):
        t=(f-1)/24;q=min(1,t/8.35);s=q*q*(3-2*q);travel=21.0*s;vehicle.location=(0,7-travel,0);vehicle.keyframe_insert('location',frame=f)
        for o in vehicle.children:
            if o.name.startswith('KimiFrozen_') and o.name!='KimiFrozen_body':o.rotation_euler.x=travel/.536;o.keyframe_insert('rotation_euler',frame=f)
    # Four real black planes form a virtual screen. The truck physically passes their plane;
    # foreground visibility is produced by depth, so the road remains occluded by the frame.
    m=bpy.data.materials.new('Absolute black screen mask');m.use_nodes=True;n=m.node_tree.nodes;n.clear();e=n.new('ShaderNodeEmission');e.inputs['Color'].default_value=(0,0,0,1);e.inputs['Strength'].default_value=0;out=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(e.outputs[0],out.inputs['Surface'])
    depth=10;half_w=4.0;half_h=2.25;inner_w=2.85;inner_h=1.72
    bpy.context.view_layer.update();mx=cam.matrix_world
    # Keep the runway entirely behind the virtual screen. Otherwise nearby floor
    # would itself cross the screen plane and leak below the bottom black border.
    import bmesh
    forward=mx.to_quaternion()@Vector((0,0,-1));clip_point=cam.location+forward*(depth+.04)
    for o in list(bpy.data.objects):
        if o.type!='MESH' or not o.name.startswith(('Arena floor','Runway edge','Lane dash')):continue
        bm=bmesh.new();bm.from_mesh(o.data)
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=o.matrix_world.inverted()@clip_point,plane_no=o.matrix_world.to_3x3().transposed()@forward,clear_inner=True,clear_outer=False)
        bm.to_mesh(o.data);bm.free();o.data.update()
    for name,rect in [('left',(-100,-inner_w,-100,100)),('right',(inner_w,100,-100,100)),('top',(-inner_w,inner_w,inner_h,100)),('bottom',(-inner_w,inner_w,-100,-inner_h))]:
        x0,x1,y0,y1=rect;verts=[tuple(mx@Vector((x,y,-depth))) for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]];mesh('Screen black '+name,verts,[(0,1,2,3)],m)
    # Thin luminous edging makes the before/after depth ordering easy to read.
    edge=mat('Screen inner edge',(.06,.40,.50),rough=.5,emission=.7)
    for name,rect in [('top',(-inner_w,inner_w,inner_h,inner_h+.018)),('left',(-inner_w-.018,-inner_w,-inner_h,inner_h)),('right',(inner_w,inner_w+.018,-inner_h,inner_h)),('bottom',(-inner_w,inner_w,-inner_h-.018,-inner_h))]:
        x0,x1,y0,y1=rect;verts=[tuple(mx@Vector((x,y,-depth-.005))) for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]];mesh('Screen rim '+name,verts,[(0,1,2,3)],edge)
    folder=ROOT/'breakout';folder.mkdir(exist_ok=True);sc.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(folder/'scene.blend'),compress=True)
    (folder/'physics.json').write_text(json.dumps({'kind':'breakout','duration':9,'frames':216,'fps':24,'authorship':'Kimi frozen truck geometry, Codex camera, screen frame and vehicle animation','effect':'Actual geometry depth ordering, four black screen planes; truck moves through screen plane and in front of its edges. End frame holds from 8.35s.','screen_plane_depth_from_camera':depth,'camera':list(cam.location),'final_truck_root':[0,-14,0]},ensure_ascii=False,indent=2),encoding='utf8')
    draft='--draft' in ARGS;stills='--stills' in ARGS;sc.render.resolution_x=768 if draft else 1920;sc.render.resolution_y=432 if draft else 1080;sc.eevee.taa_render_samples=12 if draft else 24
    path=folder/('draft_v2' if draft else 'frames_v2');path.mkdir(exist_ok=True)
    for f in ([1,72,120,150,180,201,216] if stills else range(1,217,2 if draft else 1)):
        p=path/f'{f:04d}.png'
        if p.exists():continue
        sc.frame_set(f);sc.render.filepath=str(p);bpy.ops.render.render(write_still=True);print('BREAKOUT',f,flush=True)

def result_camera():
    folder=ROOT/KIND;bpy.ops.wm.open_mainfile(filepath=str(folder/'scene.blend'));sc=bpy.context.scene;cam=sc.camera;cam.animation_data_clear();cam.data.animation_data_clear();sc.frame_set(169);dg=bpy.context.evaluated_depsgraph_get()
    props=[o for o in bpy.data.objects if o.rigid_body and o.rigid_body.type=='ACTIVE' and not o.rigid_body.kinematic]
    points=[o.evaluated_get(dg).matrix_world.translation.copy() for o in props]
    mid=Vector((sum(p.x for p in points)/len(points),sum(p.y for p in points)/len(points),.6))
    base=Vector((8.5,-10,7));cam.data.lens=43
    for i in range(30):
        f=169+i;q=i/29;angle=-.14+.28*q;cam.location=mid+(Matrix.Rotation(angle,4,'Z')@base)*(1-.12*q);look(cam,mid);cam.keyframe_insert('location',frame=f);cam.keyframe_insert('rotation_euler',frame=f)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'result_camera.blend'),compress=True)
    draft='--draft' in ARGS;sc.render.resolution_x=768 if draft else 1920;sc.render.resolution_y=432 if draft else 1080;sc.eevee.taa_render_samples=12 if draft else 20;out=folder/('result_draft' if draft else 'result_frames');out.mkdir(exist_ok=True)
    for i in ([0,14,29] if draft else range(30)):
        f=169+i;target=out/f'{i+1:04d}.png'
        if target.exists():continue
        sc.frame_set(f);sc.render.filepath=str(target);bpy.ops.render.render(write_still=True);print('RESULT_FRAME',KIND,i+1,flush=True)

def fix_wheels():
    for kind in TITLES:
        folder=ROOT/kind;bpy.ops.wm.open_mainfile(filepath=str(folder/'scene.blend'));sc=bpy.context.scene;root=bpy.data.objects['KimiTruck_animated_proxy_root'];wheel=[o for o in root.children if o.name.startswith('KimiFrozen_') and o.name!='KimiFrozen_body']
        for f in range(1,END+1):
            sc.frame_set(f);travel=4-root.location.y
            for o in wheel:o.rotation_euler.x=travel/.536;o.keyframe_insert('rotation_euler',frame=f)
        sc['wheel_direction']='Positive X rotation cancels negative-Y forward translation at tire contact; ten frozen wheel groups rotate about source centers.';sc.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(folder/'scene.blend'),compress=True);print('WHEELS_FIXED',kind,len(wheel),flush=True)

if MODE=='freeze':freeze()
elif MODE=='build':build()
elif MODE=='render':render()
elif MODE=='breakout':breakout()
elif MODE=='result':result_camera()
elif MODE=='fix_wheels':fix_wheels()
