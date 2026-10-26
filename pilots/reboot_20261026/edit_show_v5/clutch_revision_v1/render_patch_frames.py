from pathlib import Path
import bpy,json,math,sys,hashlib
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parent;SRC=ROOT/'author_candidate_1953';OUT=ROOT/'patch_frames';OUT.mkdir(exist_ok=True)
ARGS=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ALL='all' in ARGS
TRACK_ONLY='track' in ARGS
PAUSED_DRIVEN=json.loads((SRC/'clutch_phase.json').read_text(encoding='utf8'))['frames'][84]['clutch_angle']
FRAMES=list(range(348)) if ALL else [24,60,84,108,130,140,156,180,240]
if 'first' in ARGS:FRAMES=list(range(192))
KEYS=[(0,0),(2.65,2),(3.10,2.25),(3.50,3),(5.15,101/24),(5.775,112/24),(6.65,5),(14.5,191/24)]
def source_time(t):
    for (a,x),(b,y) in zip(KEYS,KEYS[1:]):
        if a<=t<=b:return x+(y-x)*(t-a)/(b-a)
    return KEYS[-1][1]
def smooth(x):
    x=min(1,max(0,x));return x*x*(3-2*x)
def load_scene(kind):
    path=SRC/('clutch_mechanism.blend' if kind=='close' else 'clutch_powertrain.blend')
    bpy.ops.wm.open_mainfile(filepath=str(path));scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=48
    scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.film_transparent=False
    if kind=='close':
        cam=bpy.data.objects.new('EditorMacroSideCamera',bpy.data.cameras.new('EditorMacroSideCamera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
    return scene
def project(scene,p):
    q=world_to_camera_view(scene,scene.camera,p);return [q.x*1920,(1-q.y)*1080]
def mesh_y(o,dg,inv):
    e=o.evaluated_get(dg);m=e.to_mesh();mat=inv@e.matrix_world;v=[(mat@p.co).y for p in m.vertices];e.to_mesh_clear();return min(v),max(v)
def marker(scene,dg,name,desired_angle):
    o=bpy.data.objects[name];e=o.evaluated_get(dg);m=e.to_mesh()
    # Choose a persistent actual mesh vertex; no independently animated indicator.
    radii=[math.hypot(v.co.x,v.co.z) for v in m.vertices];r=max(radii)
    eligible=[v for v,rr in zip(m.vertices,radii) if abs(rr-r)<1e-5]
    def score(v):
        angle=math.atan2(v.co.z,v.co.x)
        return abs(math.atan2(math.sin(angle-desired_angle),math.cos(angle-desired_angle)))+abs(v.co.y-min(q.co.y for q in eligible))
    v=min(eligible,key=score);local=v.co.copy();point=e.matrix_world@local;e.to_mesh_clear()
    direction=scene.camera.matrix_world.to_quaternion()@Vector((0,0,-1));origin=point-direction*4
    hit,loc,normal,index,obj,matrix=scene.ray_cast(dg,origin,direction,distance=4.01)
    visible=hit and obj.original.name==name and (loc-point).length<.002
    return {'pixel':project(scene,point),'visible':visible,'world':list(point),'localVertex':list(local),'object':name}
current=None;scene=None;report=[]
for i in FRAMES:
    t=i/24;kind='close' if 48<=i<192 else 'wide'
    if kind!=current:scene=load_scene(kind);current=kind
    st=source_time(t);f=1+st*24;scene.frame_set(int(math.floor(f)),subframe=f-math.floor(f))
    if kind=='close':
        push=smooth((t-2)/.65);pull=smooth((t-7.25)/.60);weight=push*(1-pull)
        target=Vector((0,.10+(.012-.10)*weight,.055*weight));cam=scene.camera;cam.location=target+Vector((.8,0,.025));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.80+(.36-.80)*weight
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();root=bpy.data.objects['Clutch'].evaluated_get(dg);inv=root.matrix_world.inverted()
    disc=mesh_y(bpy.data.objects['Clutch_FrictionDisc'],dg,inv);pressure=mesh_y(bpy.data.objects['Clutch_PressurePlate'],dg,inv);fly=mesh_y(bpy.data.objects['Clutch_FlywheelFrictionFace'],dg,inv)
    def point(y,z=.08,r=.13):return root.matrix_world@Vector((math.sqrt(r*r-z*z),y,z))
    record={'frame':i,'time':t,'sourceFrame':f,'sourceSeconds':st,'kind':kind,'gap':pressure[0]-disc[1],
        'gapA':project(scene,point(disc[1])),'gapB':project(scene,point(pressure[0])),
        'anchors':{'flywheel':project(scene,point(-.029,.085,.156)),
                   'disc':project(scene,point((disc[0]+disc[1])/2,.09,.13)),
                   'pressure':project(scene,point((pressure[0]+pressure[1])/2,.085,.142))},
        'activeAngle':float(bpy.data.objects['PowertrainControl']['engine_angle']),
        'drivenAngle':float(bpy.data.objects['PowertrainControl']['clutch_angle'])}
    if kind=='close':
        record['activeMarker']=marker(scene,dg,'Clutch_Flywheel',28.35)
        record['drivenMarker']=marker(scene,dg,'Clutch_FrictionDisc',PAUSED_DRIVEN+.35)
    if not TRACK_ONLY:
        scene.render.filepath=str(OUT/f'{i:04d}.png');bpy.ops.render.render(write_still=True)
    (OUT/f'{i:04d}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');report.append(record)
    print('PATCH_FRAME',i,kind,'source',round(f,3),flush=True)
(ROOT/('tracking_first.json' if 'first' in ARGS else 'tracking.json' if ALL else 'tracking_preflight.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'render_source_receipt.json').write_text(json.dumps({'files':[{ 'path':str(SRC/n),'sha256':hashlib.sha256((SRC/n).read_bytes()).hexdigest()} for n in ['clutch_mechanism.blend','clutch_powertrain.blend']], 'changes':'camera and render settings only; geometry, materials, controllers and source keyframes untouched','retimeKeys':KEYS,'frames':348,'fps':24},ensure_ascii=False,indent=2),encoding='utf8')
