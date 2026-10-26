from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
draft = '--draft' in sys.argv
grey = '--grey' in sys.argv
kinds = [arg for arg in sys.argv[1:] if not arg.startswith('--')] or ['bricks','balls','disc']
reports = []
for kind in kinds:
    prefix = ('draft_' if draft else '')+f'p2_{kind}'+('_grey' if grey else '')
    directory = ROOT/(prefix+'_frames')
    expected = 64 if draft else 192
    frames = sorted(directory.glob('frame_*.png'))
    assert len(frames) == expected, f'{kind}: expected {expected}, found {len(frames)}'
    output = ROOT/(prefix+'_8s.mp4')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-framerate','8' if draft else '24',
        '-i',str(directory/'frame_%04d.png'),'-frames:v','192','-vf','fps=24',
        '-c:v','libx264','-preset','fast' if draft else 'slow','-crf','21' if draft else '18',
        '-pix_fmt','yuv420p','-an','-movflags','+faststart','-y',str(output)],check=True)
    probe = json.loads(subprocess.run(['ffprobe','-v','error','-count_frames','-show_streams','-show_format',
                                      '-of','json',str(output)],check=True,capture_output=True,text=True).stdout)
    video = next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')
    assert abs(float(probe['format']['duration'])-8) < .06
    assert video['r_frame_rate'] == '24/1' and int(video['nb_read_frames']) == 192
    assert (video['width'],video['height']) == ((960,540) if draft else (1920,1080))
    assert not any(stream['codec_type'] == 'audio' for stream in probe['streams'])
    subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True)
    reports.append({'file':output.name,'duration':8,'fps':24,'resolution':[video['width'],video['height']],
                    'sourceFrames':len(frames),'fullDecode':'passed','draft':draft,'grey':grey})
(ROOT/f'p2_video_report_{"draft" if draft else "final"}{"_grey" if grey else ""}.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps(reports,indent=2))
