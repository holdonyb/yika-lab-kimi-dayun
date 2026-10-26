from pathlib import Path
import json, hashlib, subprocess, math, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
PROD=ROOT.parents[1]
PILOTS=ROOT.parents[2]
DAYUN=PILOTS/'dayun'
W,H,FPS=1920,1080,24
OUT=ROOT/'clips'; OUT.mkdir(exist_ok=True)
REVIEW=ROOT/'review'; REVIEW.mkdir(exist_ok=True)
FONT='C:/Windows/Fonts/msyh.ttc'
BOLD='C:/Windows/Fonts/msyhbd.ttc'
MONO='C:/Windows/Fonts/consola.ttf'
fonts={}
def font(size,bold=False,mono=False):
    key=(size,bold,mono)
    if key not in fonts:fonts[key]=ImageFont.truetype(MONO if mono else BOLD if bold else FONT,size)
    return fonts[key]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(cmd):return subprocess.run(cmd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
def load(path):return Image.open(path).convert('RGBA')
def write_clip(name,duration,framefunc):
    path=OUT/f'{name}.mp4'
    if '--only' in sys.argv and name not in sys.argv[sys.argv.index('--only')+1:]:
        old=json.loads((ROOT/'source_manifest.json').read_text(encoding='utf8'))
        return next(c for c in old['clips'] if c['id']==name)
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','24','-i','-',
         '-an','-c:v','libx264','-preset','fast','-crf','18','-threads','3','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
         '-movflags','+faststart',str(path)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    samples=[]
    for n in range(round(duration*FPS)):
        t=n/FPS; frame=framefunc(t,n).convert('RGB')
        if n in (12,round(duration*FPS/2),round(duration*FPS)-12):
            fp=REVIEW/f'{name}_{n:04d}.jpg';frame.save(fp,quality=94);samples.append(str(fp))
        p.stdin.write(frame.tobytes())
    p.stdin.close();err=p.stderr.read().decode('utf8','replace');rc=p.wait()
    if rc:raise RuntimeError(err)
    print('CLIP_DONE',name,duration,flush=True)
    return {'id':name,'path':str(path),'seconds':duration,'frames':round(duration*FPS),'sha256':sha(path),'samples':samples}

y,x=np.mgrid[0:H,0:W]
dist=np.sqrt(((x-1200)/1500)**2+((y-450)/1000)**2)
base=np.zeros((H,W,3),dtype=np.uint8)
for k,(c,a) in enumerate([(10,8),(20,12),(30,17)]):base[:,:,k]=np.clip(c+a*(1-dist),0,255)
BG=Image.fromarray(base)
grid=ImageDraw.Draw(BG)
for xx in range(420,1920,64):grid.line((xx,150,xx,940),fill=(22,34,44),width=1)
for yy in range(170,950,64):grid.line((400,yy,1890,yy),fill=(22,34,44),width=1)

def text(draw,xy,s,size=32,fill='#eaf1f5',bold=False):draw.text(xy,s,font=font(size,bold),fill=fill)
def shell(chapter,title,small='生成回放',footer='从整车，到每个细件。'):
    im=BG.copy();d=ImageDraw.Draw(im)
    text(d,(56,40),'KIMI CODE',22,'#78d7dd',True)
    text(d,(56,87),title,42,'#f5f4ee',True)
    d.rounded_rectangle((1712,46,1864,91),22,fill='#243a47')
    text(d,(1735,53),small,23,'#b7dce1')
    d.line((56,147,1864,147),fill='#30424d',width=2)
    items=['说需求','看它生成','细化零件','拆开检查','修正交卷']
    for i,label in enumerate(items):
        yy=199+i*76;active=i==chapter
        d.rounded_rectangle((58,yy,100,yy+42),12,fill='#61cbd4' if active else '#1c2b36')
        text(d,(69,yy+6),str(i+1),22,'#06141c' if active else '#728b9b',True)
        text(d,(119,yy+4),label,28,'#eaf6f7' if active else '#6b8595',active)
    d.line((365,186,365,938),fill='#30424d',width=2)
    text(d,(58,1003),'一卡实验室',24,'#97a7af')
    text(d,(404,1003),footer,24,'#86a7b5')
    return im

def place(im,source,box,zoom=1):
    l,t,r,b=box;ww,hh=r-l,b-t
    factor=min(ww/source.width,hh/source.height)*zoom
    res=source.resize((round(source.width*factor),round(source.height*factor)),Image.Resampling.LANCZOS)
    layer=Image.new('RGBA',(ww,hh),(0,0,0,0))
    layer.alpha_composite(res,(round((ww-res.width)/2),round((hh-res.height)/2)))
    im.paste(layer,(l,t),layer)

def read_video(path,start,duration,size=(1460,821),crop=None):
    filters=[]
    if crop:filters.append('crop='+':'.join(map(str,crop)))
    filters+=['fps=24',f'scale={size[0]}:{size[1]}:flags=lanczos']
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-ss',str(start),'-i',str(path),'-t',str(duration),'-an','-vf',','.join(filters),'-f','rawvideo','-pix_fmt','rgb24','-']
    data=run(cmd).stdout
    a=np.frombuffer(data,dtype=np.uint8).reshape(-1,size[1],size[0],3)
    return [Image.fromarray(frame) for frame in a]

prompt=DAYUN/'kimi-run/prompt_01.txt'
feedback=DAYUN/'submitted_prompt_05.txt'
truck_original=DAYUN/'kimi-run/preview_front_side.png'
first=load(truck_original)
truck_obs=json.loads((ROOT/'observed/truck/observations.json').read_text(encoding='utf8'))
engine_obs=json.loads((ROOT/'observed/engine/observations.json').read_text(encoding='utf8'))
truck_images=[load(s['file']) for s in truck_obs]
engine_images=[load(s['file']) for s in engine_obs]
old_fail=PROD/'failure_evidence/ring_original/ring_failure_replay.mp4'
fixed=DAYUN/'v2-kimi-run/engine_core_15s.mp4'
whole=DAYUN/'v3-kimi-run/p1_explosion_14s.mp4'
fail_frames=read_video(old_fail,0,3,crop=(640,360,350,120))
fixed_frames=read_video(fixed,3,7)
six_frames=read_video(fixed,10,2)
whole_frames=read_video(whole,2,2)

def prompt_frame(t,n):
    im=shell(0,'一辆能跑、能拆的大运。','原始要求');d=ImageDraw.Draw(im)
    place(im,first,(395,160,1885,930),1+0.015*t/4)
    # Source quote, shown as editorial typesetting instead of imitating the original UI.
    d.rounded_rectangle((421,731,1819,913),24,fill='#0b1721',outline='#3e626c',width=2)
    text(d,(455,755),'我要一辆能跑、能拆开的“大运”重卡',42,'#faf7e9',True)
    text(d,(456,823),'造车  →  能跑  →  能拆',32,'#6bd6dc',True)
    text(d,(58,669),'第一条任务',27,'#d2e5ea',True)
    text(d,(58,715),'原文节选',23,'#8eabb8')
    return im

def build_frame(mode,t,n):
    is_truck=mode=='truck'; obs=truck_obs if is_truck else engine_obs; ims=truck_images if is_truck else engine_images
    count=len(obs)
    idx=min(count-1,int(t/(8/count)))
    s=obs[idx]
    im=shell(1 if is_truck else 2,'先把整车搭出来。' if is_truck else '再往里拆，拆到活塞环。',footer='原建模脚本重跑' if is_truck else '从整车，到每个细件。')
    place(im,ims[idx],(393,170,1888,928))
    d=ImageDraw.Draw(im)
    text(d,(426,174),s['label'],35,'#d9eef2',True)
    text(d,(1690,181),f'{idx+1:02d} / {count:02d}',27,'#78cbd3')
    # One actual executable statement is readable, while the model dominates the screen.
    file='build_truck.py' if is_truck else 'build_engine.py'
    text(d,(58,645),'Kimi 生成的脚本',24,'#9dbcc6')
    text(d,(58,689),file,22,'#dbebe9')
    text(d,(58,733),f'执行至第 {s["line_next"]-1} 行',23,'#7195a7')
    code=(ROOT/'frozen_sources'/mode/file).read_text(encoding='utf8').splitlines()
    excerpt=next((line.strip() for line in reversed(code[max(0,s['line_next']-12):s['line_next']-1]) if '(' in line and ')' in line and len(line.strip())<110),'')
    if len(excerpt)>25:excerpt=excerpt[:23]+'…'
    d.text((58,788),excerpt,font=font(18,mono=True),fill='#70ced2')
    d.rounded_rectangle((426,929,1840,937),4,fill='#203643')
    d.rounded_rectangle((426,929,426+round(1414*(idx+1)/count),937),4,fill='#62cdd5')
    return im

def failure_frame(t,n):
    im=shell(3,'一拆，问题就出来了。','失败回放')
    # The preserved failure plays at source speed, then holds for inspection.
    f=fail_frames[min(len(fail_frames)-1,int(min(t,2.5)*24))]
    place(im,f.convert('RGBA'),(400,160,1880,993))
    d=ImageDraw.Draw(im)
    if t<3.5:
        text(d,(59,644),'环没张开',29,'#ffb06d',True)
        text(d,(59,690),'直接向上穿了',26,'#e0c5b0')
        # The top piston/ring zone is selected from the actual source frame crop.
        d.rounded_rectangle((800,313,1262,604),25,outline='#ff9c61',width=4)
        d.line((1262,358,1510,258),fill='#ff9c61',width=4)
        text(d,(1433,209),'这里穿过去了',31,'#ffc498',True)
    else:
        d.rounded_rectangle((440,660,1820,929),24,fill='#101d27',outline='#73cad1',width=3)
        text(d,(477,685),'发回 Kimi 的修改意见',28,'#76d7df',True)
        text(d,(477,742),'“请缸套先让位，',37,'#f3f4ea',True)
        text(d,(477,800),'开口环以合理张开路径退出并能归位。”',37,'#f3f4ea',True)
        text(d,(59,644),'发回修改',29,'#ffb06d',True)
        text(d,(59,690),'先让开，再拆',26,'#d1e1e8')
    return im

def fixed_frame(t,n):
    im=shell(4,'让位、拆开，再装回去。','修正结果')
    place(im,fixed_frames[min(round(n*1.4),len(fixed_frames)-1)].convert('RGBA'),(400,160,1880,993))
    d=ImageDraw.Draw(im)
    if t<0.7:lab='缸套先让位'
    elif t<1.5:lab='连杆与活塞抬离'
    elif t<2.2:lab='开口环扩径退出'
    elif t<2.9:lab='每个零件独立可见'
    else:lab='逆序装回'
    d.rounded_rectangle((436,180,1010,250),18,fill='#17333f')
    text(d,(461,193),lab,34,'#bcebed',True)
    text(d,(59,644),'再拆一遍',29,'#78d8d9',True)
    text(d,(59,690),'这次按顺序来',26,'#d1e1e8')
    return im

def result_frame(t,n):
    im=shell(4,'最后，把细件装回整车。','生成结果')
    f=six_frames[n] if n<48 else whole_frames[min(n-48,len(whole_frames)-1)]
    place(im,f.convert('RGBA'),(400,160,1880,993))
    d=ImageDraw.Draw(im)
    text(d,(59,644),'六缸一起动' if n<48 else '整车继续拆',29,'#78d8d9',True)
    text(d,(59,690),'实际保存结果',26,'#d1e1e8')
    return im

clips=[]
clips.append(write_clip('01_prompt',4,prompt_frame))
clips.append(write_clip('02_truck_generation',8,lambda t,n:build_frame('truck',t,n)))
clips.append(write_clip('03_engine_generation',8,lambda t,n:build_frame('engine',t,n)))
clips.append(write_clip('04_failure_and_feedback',7,failure_frame))
clips.append(write_clip('05_fixed_disassembly',5,fixed_frame))
clips.append(write_clip('06_results',4,result_frame))
concat=ROOT/'concat.txt'
concat.write_text('\n'.join("file '"+Path(c['path']).as_posix()+"'" for c in clips),encoding='utf8')
final=ROOT/'process_generation_36s.mp4'
run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(final)])
timeline=0
for c in clips:c['start_seconds']=timeline;timeline+=c['seconds']
source_map=[
 {'clip':'01_prompt','kind':'original_saved_prompt_and_original_render','sources':[str(prompt),str(truck_original)],'treatment':'Exact short quote typeset editorially; original saved preview reframed.'},
 {'clip':'02_truck_generation','kind':'new_verbatim_source_rerun_observation','sources':[str(ROOT/'observed/truck/receipt.json')],'treatment':'11 real intermediate states photographed while original copied source executed; source order retained. Fixed observation camera; stages cut directly without white flash or fly-in animation. Progress indicator is editorial.'},
 {'clip':'03_engine_generation','kind':'new_verbatim_source_rerun_observation','sources':[str(ROOT/'observed/engine/receipt.json')],'treatment':'10 real intermediate states photographed while original copied source executed; source order retained. Small-component framing follows the current assembly bounds, then a fixed six-cylinder camera. Stages cut directly without white flash or fly-in animation.'},
 {'clip':'04_failure_and_feedback','kind':'preserved_failure_replay_and_original_saved_feedback','sources':[str(old_fail),str(PROD/'failure_evidence/ring_original/source_manifest.json'),str(feedback)],'treatment':'Failure source crop x350 y120 w640 h360; source-speed playback then inspection hold. Original feedback excerpt typeset.'},
 {'clip':'05_fixed_disassembly','kind':'original_saved_final_render','sources':[str(fixed)],'source_seconds':[3,10],'speed':1.4,'treatment':'Original motion and geometry, 1.4x playback; picture reframed with stage labels.'},
 {'clip':'06_results','kind':'original_saved_final_renders','sources':[str(fixed),str(whole)],'source_seconds':[[10,12],[2,4]],'treatment':'Two original clips reframed, joined by a cut.'}
]
manifest={'title':'Kimi生成记录回放','seconds':36,'fps':24,'resolution':[1920,1080],'audio':'none; editor adds narration and music',
 'final':str(final),'final_sha256':sha(final),'clips':clips,'segments':source_map,
 'source_hashes':{str(p):sha(p) for p in (prompt,feedback,truck_original,old_fail,fixed,whole)},
 'new_kimi_calls':0,'original_session_usage_unchanged':True,'original_source_files_modified':False,
 'presentation':'External source-execution photography and editorial assembly; no simulated Kimi typing or fabricated original realtime screen recording.',
 'validation':{'pending':True}}
(ROOT/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
sheet=Image.new('RGB',(1280,6*240),'#0b141e')
for i,c in enumerate(clips):
    for j,sp in enumerate(c['samples'][:2]):sheet.paste(Image.open(sp).resize((640,360)).crop((0,0,640,240)),(j*640,i*240))
sheet.save(REVIEW/'contact.jpg',quality=92)
print('COMPLETE',final,sha(final),flush=True)
