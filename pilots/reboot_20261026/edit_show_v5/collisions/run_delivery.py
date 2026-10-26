from pathlib import Path
import subprocess,sys,json,time,hashlib
ROOT=Path(__file__).resolve().parent
BLENDER='C:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
KINDS=['buttons','folders','loading','deadline','errors','vram','crates','danmaku','revision','banana','triple','coins']
OUT=ROOT/'final';RESULT=ROOT/'result';OUT.mkdir(exist_ok=True);RESULT.mkdir(exist_ok=True)
def run(cmd,log):
    with (ROOT/log).open('w',encoding='utf8') as f:
        p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(f'Command failed {p.returncode}, see {log}')
def blender(mode,kind,log):run([BLENDER,'-b','-t','6','--python-exit-code','1','--python',str(ROOT/'make_collisions.py'),'--',mode,kind],log)
def probe(path):
    p=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames:format=duration','-of','json',str(path)],capture_output=True,text=True,check=True)
    r=json.loads(p.stdout);s=r['streams'][0];return {'path':str(path),'duration':float(r['format']['duration']),'width':s['width'],'height':s['height'],'fps':s['avg_frame_rate'],'frames':int(s['nb_read_frames']),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
rows=[]
for kind in KINDS:
    print('START',kind,flush=True);blender('render',kind,kind+'_final_corrected.log');subprocess.run([sys.executable,str(ROOT/'review_encode.py'),kind],check=True)
    main=probe(OUT/(kind+'.mp4'));blender('result',kind,kind+'_result.log')
    run(['ffmpeg','-y','-v','error','-framerate','24','-i',str(ROOT/kind/'result_frames'/'%04d.png'),'-frames:v','30','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart',str(RESULT/(kind+'_result.mp4'))],kind+'_result_encode.log')
    result=probe(RESULT/(kind+'_result.mp4'));phys=json.loads((ROOT/kind/'physics.json').read_text(encoding='utf8'));cache=json.loads((ROOT/kind/'cache_reopen.json').read_text(encoding='utf8'))
    row={'kind':kind,'title':phys['title'],'main':main,'result_closeup':result,'impact_frame':cache['first_target_moves_over_12cm_frame'],'impact_seconds':cache['first_target_moves_over_12cm_seconds'],'impact_estimate_method':'First target centroid displacement exceeds 0.12 m; editor can refine onset on neighboring visible frames.','recommended_action_window':[0,min(4.75,main['duration'])],'recommended_result_window':[0,1.25],'physics_scene':str(ROOT/kind/'scene.blend'),'result_camera_scene':str(ROOT/kind/'result_camera.blend'),'physics_trajectory':str(ROOT/kind/'physics.json'),'cache_validation':cache,'authorship':'Kimi original truck geometry; Codex new target props, contact simulation and cameras'};rows.append(row)
    (ROOT/'manifest_in_progress.json').write_text(json.dumps({'complete':False,'clips':rows},ensure_ascii=False,indent=2),encoding='utf8');print('READY',kind,main['duration'],result['duration'],flush=True)
blender('breakout','breakout','breakout_final.log')
run(['ffmpeg','-y','-v','error','-framerate','24','-i',str(ROOT/'breakout'/'frames_v2'/'%04d.png'),'-frames:v','216','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart',str(OUT/'breakout_9s_v2.mp4')],'breakout_encode.log')
br=probe(OUT/'breakout_9s_v2.mp4')
for r in rows:
    for item in [r['main'],r['result_closeup']]:run(['ffmpeg','-v','error','-xerror','-i',item['path'],'-f','null','-'],r['kind']+('_decode.log' if item is r['main'] else '_result_decode.log'))
run(['ffmpeg','-v','error','-xerror','-i',br['path'],'-f','null','-'],'breakout_decode.log')
manifest={'complete':True,'resolution':'1920x1080','fps':24,'audio_tracks':0,'clips':rows,'breakout':br,'breakout_freeze_start_seconds':8.35,'source_manifest':str(ROOT/'source_manifest.json'),'wheel_contact_check':str(ROOT/'wheel_contact_check.json'),'authorship':'Kimi K3.1 Pro original vehicle. Codex original meme props, animated contact vehicle proxy, Blender Bullet target simulation, cameras, 3D screen mask and render.','scope':'Artistic rigid prop collisions and screen effect. Target trajectories computed by Blender Bullet; vehicle follows an animated path.','count_new_target_types':12,'main_seconds':sum(r['main']['duration'] for r in rows),'closeup_seconds':sum(r['result_closeup']['duration'] for r in rows),'full_decode':'passed','suggested_caption_credit':'整活加赛｜场景制作 Codex'}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');(OUT/'concat.txt').write_text('\n'.join("file '"+r['main']['path'].replace('\\','/')+"'" for r in rows)+"\nfile '"+br['path'].replace('\\','/')+"'\n",encoding='utf8');print('ALL_DELIVERED',manifest['main_seconds'],manifest['closeup_seconds'],flush=True)
