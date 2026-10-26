from pathlib import Path
import json,hashlib,zipfile
ROOT=Path(__file__).resolve().parent
m=json.loads((ROOT/'manifest.json').read_text(encoding='utf8'));assert m['complete']
assert len(m['clips']) == 12 and len({row['kind'] for row in m['clips']}) == 12
w=json.loads((ROOT/'wheel_contact_check.json').read_text(encoding='utf8'));assert all(r['pass'] for r in w)
for row in m['clips']:
    assert row['cache_validation']['pass']
    row['impact_estimate_method']='First target centroid displacement exceeds 0.12 m; visible contact can be 1–3 frames earlier.'
    for key in ['main','result_closeup']:
        r=row[key];p=Path(r['path']);assert r['width']==1920 and r['height']==1080 and r['fps']=='24/1';assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'];assert abs(r['duration']-r['frames']/24)<.002
    row['physics_scene_sha256']=hashlib.sha256(Path(row['physics_scene']).read_bytes()).hexdigest();row['result_camera_scene_sha256']=hashlib.sha256(Path(row['result_camera_scene']).read_bytes()).hexdigest()
br=m['breakout'];assert br['width']==1920 and br['height']==1080 and br['fps']=='24/1'
assert br['frames']==216 and abs(br['duration']-9)<.002
assert hashlib.sha256(Path(br['path']).read_bytes()).hexdigest()==br['sha256']
m['total_new_source_seconds']=m['main_seconds']+m['closeup_seconds']+m['breakout']['duration'];m['wheel_contact_validation_passed']=True
m['source_package']={'path':str(ROOT/'dayun_v5_collision_source.zip'),'receipt':str(ROOT/'package_receipt.json'),'label':'加赛场景工程','credit':'Kimi original truck geometry; Codex collision scenes, cameras and screen effect','contents':'Frozen vehicle, Blender scenes, scripts, compact validation and rebuild instructions'}
temp_manifest=ROOT/'manifest.package.tmp';temp_manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8');temp_manifest.replace(ROOT/'manifest.json')
readme='''DAYUN V5 NEW COLLISION SOURCE\n\nVehicle geometry: frozen from original Kimi K3.1 Pro p2_bricks.blend. Original source stays unchanged.\nCodex: target props, rigid-body scenes, animated collision vehicle proxies, cameras, screen-frame effect and rendering.\n\nEnvironment: Blender 5.1.2, FFmpeg 7.1.1, Windows Microsoft YaHei font (not redistributed), Python/Pillow.\n\nEach <kind>/scene.blend contains native baked rigid-body targets and positive-X wheel animation.\nCompact cache reopen checks are included. Full 228-frame target trajectories remain in the workspace paths linked by manifest.json.\nResult camera files contain the second 1.25-second shot, sampled from frames 169–198.\nBreakout uses four actual black planes; the truck passes in front of them while the floor stays occluded.\n\nmake_collisions.py can rebuild from kimi_truck_frozen.blend, or render saved scenes.\npython run_delivery.py orchestrates main clips, 30-frame result shots, final breakout, encoding and verification.\nRebuilding a target scene regenerates its full physics.json trajectory before verification.\nThe original Kimi session and original token cutoff are untouched.\n'''
(ROOT/'SOURCE_README.txt').write_text(readme,encoding='utf8')
paths=[ROOT/'SOURCE_README.txt',ROOT/'kimi_truck_frozen.blend',ROOT/'manifest.json',ROOT/'source_manifest.json',ROOT/'physics_validation.json',ROOT/'wheel_contact_check.json',ROOT/'failure_history.json']
paths += [ROOT/name for name in ['make_collisions.py','run_delivery.py','review_encode.py','verify_cache.py','check_wheel_contact.py','review_encoded.py','finalize_package.py']]
for row in m['clips']:
    for name in ['scene.blend','result_camera.blend','cache_reopen.json']:paths.append(ROOT/row['kind']/name)
paths += [ROOT/'breakout'/'scene.blend',ROOT/'breakout'/'physics.json']
out=ROOT/'dayun_v5_collision_source.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
(ROOT/'package_receipt.json').write_text(json.dumps({'path':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'entries':len(paths),'scope':'Reproducible frozen vehicle and new collision scenes; no private session exports, secrets or original music'},indent=2),encoding='utf8')
print('PACKAGED',out.stat().st_size,len(paths),m['total_new_source_seconds'])
