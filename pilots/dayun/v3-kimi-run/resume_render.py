from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import hashlib
import json
import struct
import zlib
from datetime import datetime
from studio import render_frame

ROOT = Path(__file__).resolve().parent
ARGS = sys.argv[sys.argv.index('--')+1:]
asset = ARGS[0]
draft = '--draft' in ARGS
prefix = ('draft_' if draft else '')+asset+'_frames'
directory = ROOT/prefix
counts = {'p1_explosion':336,'p1_wheel':144,'p1_power':192,
          'mv_cruise':168,'mv_turn':168,'mv_detail':168,
          'p2_bricks':192,'p2_balls':192,'p2_disc':192}
step = 3 if draft else 1
expected = (counts[asset]+step-1)//step


def verify_png(path):
    data = path.read_bytes()
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError(f'Not a PNG: {path.name}')
    position = 8
    compressed = []
    width = height = None
    color = depth = None
    ended = False
    while position < len(data):
        length = struct.unpack('>I',data[position:position+4])[0]
        kind = data[position+4:position+8]
        start = position+8
        end = start+length
        if end+4 > len(data):
            raise ValueError(f'Truncated PNG chunk: {path.name}')
        payload = data[start:end]
        crc = struct.unpack('>I',data[end:end+4])[0]
        if zlib.crc32(kind+payload) & 0xffffffff != crc:
            raise ValueError(f'PNG CRC mismatch: {path.name}')
        if kind == b'IHDR':
            width,height,depth,color = struct.unpack('>IIBB',payload[:10])
        elif kind == b'IDAT':
            compressed.append(payload)
        elif kind == b'IEND':
            if length != 0:
                raise ValueError(f'Invalid IEND: {path.name}')
            ended = True
            position = end+4
            break
        position = end+4
    if not ended or position != len(data):
        raise ValueError(f'Missing PNG IEND or trailing data: {path.name}')
    raw = zlib.decompress(b''.join(compressed))
    if depth == 8 and color in [2,6]:
        channels = 3 if color == 2 else 4
        if len(raw) != height*(1+width*channels):
            raise ValueError(f'Incomplete PNG pixel data: {path.name}')
    return [width,height]


indices = sorted(int(path.stem.split('_')[-1]) for path in directory.glob('frame_*.png'))
if indices and indices != list(range(1,indices[-1]+1)):
    raise RuntimeError(f'Frame index gap in {prefix}; existing frames are preserved')
for index in indices:
    verify_png(directory/f'frame_{index:04d}.png')
print('EXISTING_FRAMES_VALID',asset,len(indices),'last',indices[-1] if indices else 0,flush=True)
if len(indices) > expected:
    raise RuntimeError(f'Unexpected extra frames in {prefix}')
first = (indices[-1]+1) if indices else 1
source = ROOT/(asset+'.blend')
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
records = []
for index in range(first,expected+1):
    frame = 1+(index-1)*step
    records.append(render_frame(scene,frame,f'{prefix}/frame_{index:04d}.png',
                                960 if draft else 1920,540 if draft else 1080,
                                16 if draft else 48,not draft))
    verify_png(directory/f'frame_{index:04d}.png')
report = {'asset':asset,'draft':draft,'resumedFromIndex':first,
          'existingFramesVerified':len(indices),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'startedAt':datetime.now().astimezone().isoformat(),'renderedFrames':records,
          'note':'Existing PNG chunks, CRC and pixel payload verified before rendering; no original frame overwritten'}
status = ROOT/f'{prefix}_resume_{first:04d}_status.json'
status.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RESUME_RENDER_COMPLETE',asset,'from',first,'to',expected,'draft',draft,flush=True)
