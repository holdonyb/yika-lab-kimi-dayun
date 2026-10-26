from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,math,subprocess,sys
ROOT=Path(__file__).resolve().parent;FR=ROOT/'patch_frames';PRE=ROOT/'label_preflight';PRE.mkdir(exist_ok=True)
S=2;BLUE='#a4cfe8';ORANGE='#ecad72';WHITE='#f4f5f7';INK='#0b141b'
FONTS={}
def font(n):
    if n not in FONTS:FONTS[n]=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n*S)
    return FONTS[n]
def draw_frame(i):
    r=json.loads((FR/f'{i:04d}.json').read_text(encoding='utf8'));base=Image.open(FR/f'{i:04d}.png').convert('RGBA')
    overlay=Image.new('RGBA',(1920*S,1080*S));d=ImageDraw.Draw(overlay);t=i/24
    def line(points,fill,width=2):d.line([(round(x*S),round(y*S)) for x,y in points],fill=fill,width=width*S,joint='curve')
    def text(p,s,n=38,fill=WHITE,anchor='la'):
        d.text((p[0]*S,p[1]*S),s,font=font(n),fill=fill,anchor=anchor,stroke_width=1*S,stroke_fill='#071018')
    def dot(p,c,radius=7):
        x,y=p;d.ellipse(((x-radius)*S,(y-radius)*S,(x+radius)*S,(y+radius)*S),fill=c,outline=WHITE,width=2*S)
    if r['kind']=='close':
        text((75,55),'轴向间隙 ×4',26,'#b7c7d3')
        labels=[('flywheel',(180,250),'飞轮 · 主动端',BLUE,(480,305)),
                ('disc',(150,500),'摩擦片 · 从动端',ORANGE,(500,555)),
                ('pressure',(1410,250),'压盘 · 主动端',BLUE,(1380,305))]
        for key,pos,label,color,knee in labels:
            point=r['anchors'][key]
            text(pos,label,38,color)
            line([knee,(point[0]-24 if key!='pressure' else point[0]+24,point[1]),point],color,2)
            dot(point,color,3)
        if r['sourceSeconds']>=112/24:stage='重新夹紧 → 恢复传动'
        elif r['sourceSeconds']>=101/24:stage='压盘压回 → 两侧重新贴合'
        elif r['gap']>.000005:stage='压盘退开 → 摩擦片不再被夹紧'
        else:stage='飞轮、摩擦片、压盘：看中间的接触面'
        width=d.textlength(stage,font=font(40))/S
        x=(1920-width)/2
        d.rounded_rectangle(((x-24)*S,852*S,(x+width+24)*S,916*S),radius=10*S,fill=(7,15,20,218))
        text((960,885),stage,40,WHITE,'mm')
        if r['gap']>.0008 and 3.1<t<5.775:
            a,b=r['gapA'],r['gapB'];c='#ffd08a'
            line([a,b],c,3)
            for p in [a,b]:line([(p[0],p[1]-15),(p[0],p[1]+15)],c,3)
            line([(a[0]+7,a[1]-5),a,(a[0]+7,a[1]+5)],c,2)
            line([(b[0]-7,b[1]-5),b,(b[0]-7,b[1]+5)],c,2)
        for key,c in [('activeMarker',BLUE),('drivenMarker',ORANGE)]:
            m=r[key];x,y=m['pixel']
            if m['visible'] and 35<x<1885 and 115<y<820:dot((x,y),c,9)
    elif t<2:
        text((80,72),'动力从这里接上',40)
        p=r['anchors']['disc'];x,y=p
        d.rounded_rectangle(((x-72)*S,(y-72)*S,(x+72)*S,(y+72)*S),radius=12*S,outline=ORANGE,width=3*S)
        text((x+96,y-16),'离合器',34,ORANGE)
        line([(x+72,y),(x+88,y)],ORANGE,3)
    elif t<12.8:
        text((80,72),'接上以后，整条动力链继续转',40)
    result=Image.alpha_composite(base,overlay.resize((1920,1080),Image.Resampling.LANCZOS)).convert('RGB')
    return result

def ass_time(t):
    n=round(t*100);return f'{n//360000}:{n//6000%60:02}:{n//100%60:02}.{n%100:02}'
def write_subtitles():
    intervals=[(.065,1.825,'装回去，再检查联动。'),(2.075,2.675,'看这里：'),
      (2.765,3.565,'离合断开，'),(3.775,5.075,'后面的传动轴停下；'),
      (5.185,5.995,'重新接上，'),(5.995,7.525,'它们又一起转起来。'),
      (7.875,8.975,'能拆，能装，'),(9.005,10.575,'接上以后能连着动，'),
      (10.725,12.645,'这三道题就都摆在眼前了。'),
      (13.405,14.5,'这一趟从十五个大块头，改到现在这些细节，')]
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Speech,Microsoft YaHei,46,&H00F3F5F7,&H00FFFFFF,&H00101418,&H88000000,0,0,0,0,100,100,0,0,1,2.7,0,2,110,110,54,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    (ROOT/'clutch_subtitles.ass').write_text(header+'\n'.join(f'Dialogue: 1,{ass_time(a)},{ass_time(b)},Speech,,0,0,0,,{s}' for a,b,s in intervals)+'\n',encoding='utf-8-sig')
def main():
    write_subtitles()
    if 'all' not in sys.argv:
        for i in [24,60,84,108,130,140,156,180,240]:draw_frame(i).save(PRE/f'{i:04d}.jpg',quality=95)
        return
    first='first' in sys.argv;frames=192 if first else 348
    out=ROOT/('clutch_patch_first8s_picture.mp4' if first else 'clutch_patch_picture.mp4')
    args=['ffmpeg','-hide_banner','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080','-framerate','24','-i','-',
        '-vf','scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p,setsar=1,ass=clutch_subtitles.ass',
        '-an','-frames:v',str(frames),'-c:v','libx264','-threads','6','-preset','veryfast','-crf','16','-color_range','tv','-colorspace','bt709','-color_trc','bt709','-color_primaries','bt709','-movflags','+faststart',str(out)]
    with (ROOT/'patch_encode.log').open('w',encoding='utf8') as log:
        p=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.PIPE,stderr=log)
        try:
            for i in range(frames):p.stdin.write(draw_frame(i).tobytes())
        finally:p.stdin.close()
        if p.wait():raise RuntimeError('patch encoder failed')
    print(str(out),flush=True)
if __name__=='__main__':main()
