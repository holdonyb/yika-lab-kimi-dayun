from pathlib import Path
import json, subprocess, hashlib
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'source_manifest.json').read_text(encoding='utf8'))
manifest['segments'][1]['treatment']='11 actual source execution checkpoints; fixed observation camera; direct cuts, no white flash, no fly-in. Bottom caption: 原建模脚本重跑.'
manifest['segments'][2]['treatment']='10 actual source execution checkpoints; small-part camera framed on assembly bounds followed by fixed six-cylinder camera; direct cuts, no white flash, no fly-in.'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def probe(p):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
final=Path(manifest['final'])
data=probe(final);s=data['streams'][0]
assert (s['width'],s['height'])==(1920,1080)
assert s['r_frame_rate']=='24/1' and s['avg_frame_rate']=='24/1'
assert int(s['nb_frames'])==864 and float(s['start_time'])==0
assert abs(float(data['format']['duration'])-36)<.001
decode=subprocess.run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'],capture_output=True)
(ROOT/'decode.log').write_bytes(decode.stderr)
assert decode.returncode==0 and not decode.stderr
checks=[]
for c in manifest['clips']:
    v=probe(c['path'])['streams'][0]
    assert int(v['nb_frames'])==c['frames']
    assert sha(c['path'])==c['sha256']
    checks.append({'id':c['id'],'frames':int(v['nb_frames']),'seconds':float(v['duration']),'sha256':sha(c['path'])})
observations=[]
for mode in ('truck','engine'):
    r=json.loads((ROOT/f'observed/{mode}/receipt.json').read_text(encoding='utf8'))
    assert sha(r['source'])==r['source_sha256_before']==r['source_sha256_after']==r['frozen_sha256']
    obs=json.loads((ROOT/f'observed/{mode}/observations.json').read_text(encoding='utf8'))
    for p in obs:
        im=Image.open(p['file']).convert('RGBA')
        bbox=im.getchannel('A').getbbox()
        observations.append({'mode':mode,'file':p['file'],'alpha_bbox':bbox,'touches_frame_edge':bool(bbox and (bbox[0]==0 or bbox[1]==0 or bbox[2]==im.width or bbox[3]==im.height))})
review=ROOT/'encoded_review';review.mkdir(exist_ok=True)
times=[1,4.2,7,11.3,12.3,16,19.2,20.4,22,24.3,26.5,27.2,28.7,30.5,31.7,32.5,35.1]
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
sheetpaths=[]
for sheetno in range((len(times)+5)//6):
    sheet=Image.new('RGB',(1280,3*385),'#0b141d');d=ImageDraw.Draw(sheet)
    for k,t in enumerate(times[sheetno*6:sheetno*6+6]):
        p=review/f'{t:04.1f}.jpg'
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(final),'-frames:v','1',str(p)],check=True,capture_output=True)
        im=Image.open(p).resize((640,360),Image.Resampling.LANCZOS)
        xx=(k%2)*640;yy=(k//2)*385
        sheet.paste(im,(xx,yy+25));d.text((xx+8,yy),f'{t:.1f} s',font=font,fill='#e5f0ef')
    sp=review/f'contact_{sheetno+1}.jpg';sheet.save(sp,quality=92);sheetpaths.append(str(sp))
report={'final':str(final),'sha256':sha(final),'duration':36,'frames':864,'width':1920,'height':1080,'fps':24,
        'full_decode':'passed','clips':checks,'source_original_hashes':'unchanged','observations':observations,
        'encoded_review_sheets':sheetpaths,'visual_review':'pending actual inspection'}
(ROOT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
manifest['validation']={'technical_passed':True,'visual_review':'pending actual encoded-frame inspection','report':str(ROOT/'validation.json')}
(ROOT/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'sha256':sha(final),'decode':'passed','observed_frames':len(observations),'touches_edges':[o['file'] for o in observations if o['touches_frame_edge']],'review_sheets':sheetpaths},ensure_ascii=False))
