from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BLENDER = 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
shots = [arg for arg in sys.argv[1:] if not arg.startswith('--')] or ['wheel','power','cruise','turn','detail']
flags = [arg for arg in sys.argv[1:] if arg.startswith('--')]
environment = dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
for shot in shots:
    log_name = f'preview_{shot}.log'
    print('PREVIEW_START',shot,flush=True)
    with (ROOT/log_name).open('w',encoding='utf-8') as log:
        subprocess.run([BLENDER,'--background','--python-exit-code','1','--python','animate_p1.py','--',shot,'--draft',*flags],
                       cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True)
    print('PREVIEW_COMPLETE',shot,flush=True)
