from pathlib import Path
import json,sys,subprocess,hashlib
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
KINDS=['buttons','folders','loading','deadline','errors','vram','crates','danmaku','revision','banana','triple','coins']
ARGS=sys.argv[1:];draft='--draft' in ARGS
kinds=[a for a in ARGS if not a.startswith('--')] or KINDS
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
out=ROOT/('previews' if draft else 'final');out.mkdir(exist_ok=True)
for kind in kinds:
    folder=ROOT/kind;frames=folder/('draft_v5' if draft else 'frames_final');imgs=sorted(frames.glob('*.png'))
    if not imgs:continue
    if draft:
        lst=folder/'preview_concat.txt';lst.write_text('\n'.join("file '"+p.as_posix()+"'\nduration 0.0833333333333" for p in imgs)+"\nfile '"+imgs[-1].as_posix()+"'\n",encoding='utf8')
        cmd=['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-t','9.5','-r','12','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',str(out/(kind+'_preview.mp4'))]
    else:
        cmd=['ffmpeg','-y','-v','error','-framerate','24','-i',str(frames/'%04d.png'),'-frames:v',str(len(imgs)),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart',str(out/(kind+'.mp4'))]
    subprocess.run(cmd,check=True)
    pick=[1,25,49,61,73,97,min(121,len(imgs)),len(imgs)]
    sheet=Image.new('RGB',(1280,4*385),(9,17,27));d=ImageDraw.Draw(sheet)
    for i,f in enumerate(pick):
        p=frames/f'{f:04d}.png'
        if not p.exists():continue
        im=Image.open(p).convert('RGB');im.thumbnail((640,360));x=(i%2)*640;y=(i//2)*385;sheet.paste(im,(x,y));d.text((x+8,y+361),f'{kind}  {(f-1)/24:.2f}s  f{f}',font=font,fill='white')
    sheet.save(out/(kind+'_contact.jpg'),quality=90)
    print('ENCODED',kind,draft,flush=True)
