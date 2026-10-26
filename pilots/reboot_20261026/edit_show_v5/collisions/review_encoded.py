from pathlib import Path
import subprocess,sys,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'encoded_review';OUT.mkdir(exist_ok=True);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
for kind in sys.argv[1:]:
    src=ROOT/'final'/(kind+'.mp4');samples=[0,1.9,2.65,3.3,4.2,5.5]
    if kind.startswith('breakout_9s'):samples=[0,3,5,6.2,7.5,8.8]
    folder=OUT/kind;folder.mkdir(exist_ok=True);sheet=Image.new('RGB',(1152,480),(8,16,25));d=ImageDraw.Draw(sheet)
    for i,t in enumerate(samples):
        p=folder/f'{i:02d}.png';subprocess.run(['ffmpeg','-y','-v','error','-ss',str(t),'-i',str(src),'-frames:v','1',str(p)],check=True)
        im=Image.open(p).convert('RGB').resize((384,216));x=(i%3)*384;y=(i//3)*240;sheet.paste(im,(x,y));d.text((x+5,y+216),f'{kind} {t:.2f}s',font=font,fill='white')
    sheet.save(OUT/(kind+'_encoded.jpg'),quality=92)
