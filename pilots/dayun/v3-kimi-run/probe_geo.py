from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from driveline import beam, MATS
import geo
original_mesh = geo.mesh
def logging_mesh(name, verts, faces, mat, parent=None, **kwargs):
    print('MESH_INPUT',name,type(verts),type(faces),verts[:2],faces[:2],type(mat),type(parent))
    return original_mesh(name,verts,faces,mat,parent,**kwargs)
geo.mesh = logging_mesh
print('START_BEAM_PROBE')
obj = beam('ProbeRocker',None,(0,0,.505),(0,.034,.491),.006,MATS['steel'])
print('BEAM_OK',obj.name,len(obj.data.vertices),len(obj.data.polygons))
