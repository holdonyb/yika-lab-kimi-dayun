from pathlib import Path
import bpy,json,hashlib,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'frozen_original/p1_power.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;control=bpy.data.objects['PowertrainControl'];clutch=bpy.data.objects['Clutch']
names=['Clutch_Flywheel','Clutch_FrictionDisc','Clutch_PressurePlate','Clutch_ReleaseBearing','Clutch_SplineHub','Gearbox_InputShaft','PropellerShaft_Spinner']
names += [o.name for o in bpy.data.objects if o.name.startswith(('Flywheel_01','Crankshaft'))]
names=list(dict.fromkeys(n for n in names if n in bpy.data.objects))
def drivers(o):
 return [{'path':c.data_path,'index':c.array_index,'expression':c.driver.expression,'variables':[{'name':v.name,'target':v.targets[0].id.name,'path':v.targets[0].data_path} for v in c.driver.variables]} for c in o.animation_data.drivers] if o.animation_data else []
rows=[]
for f in [1,25,48,49,55,61,73,96,97,103,113,121,145,192]:
 scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
 root_inverse=clutch.evaluated_get(dg).matrix_world.inverted();parts={}
 for name in names:
  o=bpy.data.objects[name];ev=o.evaluated_get(dg);mat=root_inverse@ev.matrix_world
  p={'parent':o.parent.name if o.parent else None,'localLocation':list(ev.location),'localRotationEuler':list(ev.rotation_euler),'worldPosition':list(ev.matrix_world.translation),'worldMatrix':[list(row) for row in ev.matrix_world],'drivers':drivers(o)}
  if o.type=='MESH':
   mesh=ev.to_mesh();co=[mat@v.co for v in mesh.vertices]
   p['clutchRootBounds']={axis:[min(v[i] for v in co),max(v[i] for v in co)] for i,axis in enumerate('XYZ')}
   p['vertexCount']=len(mesh.vertices);ev.to_mesh_clear()
  parts[name]=p
 row={'frame':f,'sourceTime':(f-1)/24,'controls':{k:float(control[k]) for k in ['engine_angle','clutch_angle','wheel_angle','clutch_release']},'parts':parts}
 fly=parts['Clutch_Flywheel']['clutchRootBounds']['Y'];disc=parts['Clutch_FrictionDisc']['clutchRootBounds']['Y'];press=parts['Clutch_PressurePlate']['clutchRootBounds']['Y']
 row['interfaces']={'flywheelY':fly,'frictionDiscY':disc,'pressurePlateY':press,'discPressureAxialGap':press[0]-disc[1],'flywheelDiscAxialOverlap':max(0,min(fly[1],disc[1])-max(fly[0],disc[0]))}
 rows.append(row)
report={'source':str(SOURCE),'sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'coordinateFrame':'Clutch root local Y, evaluated vertices incl modifiers and all parent transforms','names':names,'frames':rows}
(ROOT/'evidence/evaluated_original_clutch.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'source':str(SOURCE),'names':names,'summary':[{'frame':r['frame'],'t':r['sourceTime'],'release':r['controls']['clutch_release'],'interfaces':r['interfaces'],'flywheelRot':r['parts']['Clutch_Flywheel']['localRotationEuler'],'pressureLoc':r['parts']['Clutch_PressurePlate']['localLocation'],'releaseLoc':r['parts']['Clutch_ReleaseBearing']['localLocation']} for r in rows]},ensure_ascii=False,indent=2))
# Freeze a camera-only isolated inspection view. Geometry, drivers, keyframes untouched.
visible={clutch,*clutch.children_recursive}
for o in bpy.data.objects:
 if o.type=='MESH':o.hide_render=o not in visible
 if o.type=='LIGHT':o.hide_render=True
scene.frame_set(1);bpy.context.view_layer.update();center=clutch.matrix_world.translation.copy()
cam=bpy.data.objects.new('ClutchInspectionCamera',bpy.data.cameras.new('ClutchInspectionCamera'));scene.collection.objects.link(cam)
cam.data.type='ORTHO';cam.data.ortho_scale=.64
cam.location=center+Vector((.8,.17,.11));cam.rotation_euler=(center+Vector((0,.025,0))-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
for i,(offset,power,size) in enumerate([((.35,-.20,.40),7,.45),((-.25,.15,.20),5,.4),((.10,.45,.05),6,.3)]):
 light=bpy.data.objects.new('ClutchInspectionLight'+str(i),bpy.data.lights.new('ClutchInspectionLight'+str(i),'AREA'));scene.collection.objects.link(light);light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.location=center+Vector(offset);light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32;scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'evidence/original_clutch_inspection.blend'))
for f in [25,73,145]:
 scene.frame_set(f);scene.render.filepath=str(ROOT/f'evidence/original_clutch_f{f:03d}.png');bpy.ops.render.render(write_still=True)
print('CLUTCH_EVIDENCE_DONE',flush=True)
