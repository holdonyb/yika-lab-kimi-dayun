from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from studio import render_sequence

ROOT = Path(__file__).resolve().parent
asset = sys.argv[sys.argv.index('--')+1]
draft = '--draft' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(ROOT/(asset+'.blend')))
scene = bpy.context.scene
frames = {'p1_explosion':336,'p1_wheel':144,'p1_power':192,
          'mv_cruise':168,'mv_turn':168,'mv_detail':168,
          'p2_bricks':192,'p2_balls':192,'p2_disc':192}[asset]
prefix = ('draft_' if draft else '')+asset+'_frames'
render_sequence(scene,prefix,1,frames,960 if draft else 1920,540 if draft else 1080,
                16 if draft else 48,3 if draft else 1,not draft)
print('SAVED_SHOT_RENDER_COMPLETE',asset,'draft',draft,flush=True)
