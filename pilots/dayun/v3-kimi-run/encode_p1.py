from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DRAFT = '--draft' in sys.argv
shots = {'explosion':14,'wheel':6,'power':8,'cruise':7,'turn':7,'detail':7}
selected = [argument for argument in sys.argv[1:] if argument != '--draft']
if selected:
    shots = {selected[0]:shots[selected[0]]}
reports = []
for shot,duration in shots.items():
    folder = f"{'draft_' if DRAFT else ''}p1_{shot}_frames"
    if shot in ['cruise','turn','detail']:
        folder = f"{'draft_' if DRAFT else ''}mv_{shot}_frames"
    directory = ROOT/folder
    expected = duration*(8 if DRAFT else 24)
    frames = sorted(directory.glob('frame_*.png'))
    assert len(frames) == expected, f'{folder}: expected {expected}, found {len(frames)}'
    output = ROOT/f"{'draft_' if DRAFT else ''}p1_{shot}_{duration}s.mp4"
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-framerate',str(8 if DRAFT else 24),
        '-i',str(directory/'frame_%04d.png'),'-frames:v',str(duration*24),'-vf','fps=24',
        '-c:v','libx264','-preset','fast' if DRAFT else 'slow','-crf','21' if DRAFT else '18',
        '-pix_fmt','yuv420p','-an','-movflags','+faststart','-y',str(output)],check=True)
    probe = json.loads(subprocess.run(['ffprobe','-v','error','-count_frames','-show_streams','-show_format',
                                      '-of','json',str(output)],check=True,capture_output=True,text=True).stdout)
    video = next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')
    assert abs(float(probe['format']['duration'])-duration) < .06
    assert video['r_frame_rate'] == '24/1'
    assert int(video['nb_read_frames']) == duration*24
    assert (video['width'],video['height']) == ((960,540) if DRAFT else (1920,1080))
    assert not any(stream['codec_type'] == 'audio' for stream in probe['streams'])
    subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True)
    reports.append({'file':output.name,'durationSeconds':duration,'sourceFrames':len(frames),
                    'resolution':[video['width'],video['height']],'fps':24,'encodedFrames':duration*24,
                    'audio':False,'fullDecode':'passed','draft':DRAFT})
(ROOT/f"video_report_{'draft' if DRAFT else 'final'}.json").write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps(reports,indent=2))
