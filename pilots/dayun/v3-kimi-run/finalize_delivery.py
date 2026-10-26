from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
VIDEOS = {
    'p1_explosion_14s.mp4':(14,336),
    'p1_wheel_6s.mp4':(6,144),
    'p1_power_8s.mp4':(8,192),
    'p1_cruise_7s.mp4':(7,168),
    'p1_turn_7s.mp4':(7,168),
    'p1_detail_7s.mp4':(7,168),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(path):
    file = ROOT/path
    if not file.is_file():
        raise FileNotFoundError(path)
    return file


def read_json(path):
    return json.loads(require(path).read_text(encoding='utf-8'))


video_records = []
for name,(duration,frames) in VIDEOS.items():
    path = require(name)
    probe = json.loads(subprocess.run(['ffprobe','-v','error','-count_frames','-show_streams','-show_format',
        '-of','json',str(path)],check=True,capture_output=True,text=True).stdout)
    video = next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')
    assert video['width'] == 1920 and video['height'] == 1080, name
    assert video['r_frame_rate'] == '24/1', name
    assert int(video['nb_read_frames']) == frames, name
    assert abs(float(probe['format']['duration'])-duration) < .06, name
    assert not any(stream['codec_type'] == 'audio' for stream in probe['streams']), name
    subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True)
    video_records.append({'file':name,'width':1920,'height':1080,'fps':24,'frames':frames,
                          'durationSeconds':duration,'audio':False,'fullDecode':'passed',
                          'bytes':path.stat().st_size,'sha256':sha(path)})
(ROOT/'delivery_video_validation.json').write_text(json.dumps(video_records,indent=2),encoding='utf-8')

restore = read_json('p1_reopen_validation.json')
assert not restore['restoreErrors'] and not restore['parentErrors'] and not restore['missingEntityIds']
power = read_json('p1_power_validation.json')
assert all(power['downstreamStoppedFrom72To96'].values())
assert power['engineContinuesWhileClutchOpen'] and power['pistonContinuesWhileClutchOpen']
balls = read_json('p2_balls_cache_check.json')
assert balls['cacheBakedAfterReopen'] and balls['embeddedCache'] and not balls['cachePositionErrors']
assert read_json('p2_balls_support_check.json')['stableBeforeContact']
disc = read_json('p2_disc_study_t1_0_check.json')
assert disc['stableBeforeContact'] and disc['majoritySeparatedAtEnd']
assert disc['threshold'] == 1.0 and disc['firstFragmentationFrame'] == 59
cache = read_json('p2_disc_study_t1_0_cache_check.json')
assert cache['cacheBakedAfterReopen'] and cache['embeddedCache'] and not cache['cachePositionErrors']
assert disc['sourceSha256'] == sha(require('p2_disc_physics_base.blend'))
assert sha(require('p2_disc_final.blend')) == sha(require('p2_disc_study_t1_0.blend'))

physics = {
    'selectedDisc':'p2_disc_final.blend',
    'selectedStudy':'p2_disc_study_t1_0.blend',
    'selectedThreshold':1.0,
    'rebuildBase':'p2_disc_physics_base.blend',
    'rebuildCommand':'Blender --background --python-exit-code 1 --python disc_threshold_study.py -- 1.0',
    'baseSha256':sha(require('p2_disc_physics_base.blend')),
    'finalSha256':sha(require('p2_disc_final.blend')),
    'ballsAsset':'p2_balls.blend',
    'ballsSha256':sha(require('p2_balls.blend')),
    'bricksAsset':'p2_bricks.blend',
    'selectedEvidence':['p2_disc_study_t1_0_check.json','p2_disc_study_t1_0_cache_check.json',
                        'p2_balls_support_check.json','p2_balls_cache_check.json'],
    'firstFragmentationFrame':59,
    'preContactStable':True,
    'endState':'18 independently simulated pre-cut cells, grouped only by the documented approximate center-spacing check',
    'scope':['Animated truck and matching collision hull, not a vehicle dynamics model',
             'Pre-cut cells and breakable fixed constraints solved by Bullet',
             'Art-directed lightweight prop mass, not measured gypsum density or strength',
             'Disc-only speed profile reaching 5.5m/s before a smooth stop',
             'Initial bottom placement corrected from 18.3mm to 1.5mm using actual mesh vertices',
             'No timed deletion of all constraints and no authored fragment flight trajectories',
             'P2 editorial camera, final rendering and compositing are handled by the chief editor'],
}
(ROOT/'p2_physics_delivery.json').write_text(json.dumps(physics,ensure_ascii=False,indent=2),encoding='utf-8')

assets = [
    'assets/dayun_base_frozen.blend','assets/engine_core_frozen.blend',
    'truck_stage1.blend','truck_systems.blend','p1_explosion.blend','p1_wheel.blend','p1_power.blend',
    'mv_cruise.blend','mv_turn.blend','mv_detail.blend',
    'p2_balls.blend','p2_bricks.blend','p2_disc_physics_base.blend',
    'p2_disc_study_t1_0.blend','p2_disc_final.blend',
]
asset_records = [{'file':name,'bytes':require(name).stat().st_size,'sha256':sha(require(name))} for name in assets]
manifest = {
    'title':'大运重卡 P1 原生视频与 P2 物理源',
    'videos':video_records,
    'editableAssets':asset_records,
    'physics':physics,
    'verification':['delivery_video_validation.json','p1_reopen_validation.json','p1_power_validation.json',
                    'p2_balls_support_check.json','p2_balls_cache_check.json',
                    'p2_disc_study_t1_0_check.json','p2_disc_study_t1_0_cache_check.json'],
    'remaining':['P2 最终摄影、连续验收与成片由主编负责，本包不含本代理生成的 P2 成片',
                 '未覆盖完整原厂 BOM、制造公差、全部油液/电气系统、燃烧、扭矩、材料强度和整车动力学',
                 '未取得官方 token 统计；主编负责原生导出实际 usage',
                 '失败版本保留在工作目录；ZIP 选择交付资产、源码、关键证据和部分失败记录，不重复打包全部失败 BLEND'],
    'officialSource':'https://www.dayungroup.com/product-productdetail-27-229',
    'usageStatistics':'未取得官方 token 统计；主编负责核实',
}
(ROOT/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

files = {Path(name) for name in VIDEOS}
files.update(Path(name) for name in assets)
files.update(ROOT.glob('*.py'))
files.update(ROOT.glob('*.md'))
files.update(ROOT.glob('*_failure.log'))
files.update(ROOT.glob('*failed*.json'))
files.update(ROOT.glob('*failed*.png'))
files.update(ROOT.glob('*resume*status.json'))
files.update((ROOT/'mv_failed_dark_checks').glob('*.png'))
for name in [
    'asset_sources.json','vehicle_entities.json','stage1_entities.json','stage1_state.json',
    'p1_explosion_map.json','p1_motion_validation.json','p1_reopen_validation.json','p1_power_validation.json',
    'p2_balls_support_check.json','p2_balls_cache_check.json','p2_bricks_cache_check.json',
    'p2_disc_initial_state.json','p2_disc_speed_profile.json','p2_disc_study_t1_0_check.json',
    'p2_disc_study_t1_0_cache_check.json','p2_disc_threshold_study_all.json',
    'p2_disc_study_t0_3_check.json','p2_disc_mostly_intact_t8_5_frame_check.json',
    'p2_bricks_disk_cache_stack.txt','p2_physics_delivery.json',
    'delivery_video_validation.json','delivery_manifest.json',
    'p1_explosion_frames/frame_0264.png','p1_explosion_frames/frame_0265.png',
    'p1_wheel_frames/frame_0112.png','p1_power_frames/frame_0001.png','p1_power_frames/frame_0080.png',
    'mv_cruise_frames/frame_0056.png','mv_turn_frames/frame_0056.png','mv_detail_frames/frame_0056.png',
    'p2_balls_support_f0013.png','p2_balls_support_f0048.png',
]:
    if (ROOT/name).exists():
        files.add(Path(name))

files = {path.relative_to(ROOT) if path.is_absolute() else path for path in files}
archive = ROOT/'dayun_v3_delivery.zip'
with zipfile.ZipFile(archive,'w',allowZip64=True) as package:
    for relative in sorted(files,key=lambda path:path.as_posix()):
        source = ROOT/relative
        require(relative.as_posix())
        method = zipfile.ZIP_STORED if relative.suffix.lower() in ['.mp4','.png'] else zipfile.ZIP_DEFLATED
        package.write(source,arcname=relative.as_posix(),compress_type=method,compresslevel=6 if method == zipfile.ZIP_DEFLATED else None)
with zipfile.ZipFile(archive) as package:
    bad = package.testzip()
    assert bad is None, f'ZIP CRC failure: {bad}'
    members = len(package.namelist())
result = {'archive':archive.name,'files':members,'bytes':archive.stat().st_size,
          'sha256':sha(archive),'zipCrc':'passed','videoValidation':'six native 1080p24 files fully decoded',
          'physicsCacheValidation':'selected t1.0 disc and balls reopened with zero position errors'}
(ROOT/'dayun_v3_delivery.zip.sha256').write_text(result['sha256']+'  '+archive.name+'\n',encoding='utf-8')
(ROOT/'package_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
