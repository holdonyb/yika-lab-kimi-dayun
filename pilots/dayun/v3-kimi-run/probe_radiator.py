from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import faulthandler
faulthandler.dump_traceback_later(15,repeat=True)

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'truck_stage1.blend'))
import accessories

for name in ['group','register','revolve','cylinder','mesh','pipe']:
    original = getattr(accessories,name)
    def wrapped(*args,__original=original,__name=name,**kwargs):
        print('CALL',__name,args[0] if args else '',flush=True)
        if args and args[0] == 'Swept fan blade':
            print('FAN_VERTS',args[1],flush=True)
            print('FAN_FACES',args[2],flush=True)
        result = __original(*args,**kwargs)
        print('DONE',__name,args[0] if args else '',flush=True)
        return result
    setattr(accessories,name,wrapped)
print('RADIATOR_START',flush=True)
accessories.radiator(bpy.data.objects['Dayun_N8E_6x4'],bpy.data.objects['CrankAngleController'])
print('RADIATOR_COMPLETE',flush=True)
