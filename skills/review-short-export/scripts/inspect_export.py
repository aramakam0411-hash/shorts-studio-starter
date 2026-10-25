"""Bounded technical/selected-picture evidence for an actual short export."""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import subprocess


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(source, output, times=None, expect_audio=False):
    source, output = Path(source).resolve(), Path(output)
    if not source.is_file() or source.stat().st_size>512*1024*1024: raise ValueError('Use a local file up to512MiB')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(source)],timeout=30))
    duration=float(probe['format']['duration'])
    if not math.isfinite(duration) or not 0<duration<=180: raise ValueError('Use a short of at most180seconds')
    video=next((s for s in probe['streams'] if s['codec_type']=='video'),None)
    if not video: raise ValueError('No video stream')
    if times is None: times=sorted(set(min(t,max(0,duration-0.1)) for t in (0.5,1,3)))
    if not 1<=len(times)<=12 or any(isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) or not 0<=t<duration for t in times) or sorted(set(times))!=times: raise ValueError('Use 1 to12distinct increasing in-range timestamps')
    output.mkdir(parents=True,exist_ok=False)
    subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(source),'-f','null','-'],check=True,timeout=90)
    findings=[]
    has_audio=any(s['codec_type']=='audio' for s in probe['streams'])
    if expect_audio and not has_audio: findings.append('Expected audio stream is missing')
    audio={'stream_present':has_audio,'perceptual_quality':'not_assessed'}
    if has_audio:
        raw=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(source),'-vn','-ac','1','-ar','16000','-f','s16le','pipe:1'],timeout=90)
        samples=array('h');samples.frombytes(raw)
        import sys
        if sys.byteorder!='little': samples.byteswap()
        nonzero=any(samples)
        audio.update({'samples':len(samples),'nonzero':nonzero,'peak':max((abs(x) for x in samples),default=0)/32768,
                      'rms':math.sqrt(sum(x*x for x in samples)/len(samples))/32768 if samples else 0})
        if expect_audio and not nonzero: findings.append('Expected audio has no decoded signal')
    clock_text=subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','csv=p=0',str(source)],text=True,timeout=45)
    clock=[]
    for line in clock_text.splitlines():
        try: value=float(line.split(',')[0])
        except ValueError: continue
        if math.isfinite(value): clock.append(value)
    if not clock: raise ValueError('No decoded presentation timestamps')
    origin=clock[0]
    pictures=[]
    for index,stamp in enumerate(times):
        dest=output/f'frame-{index:02d}.png'
        subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(source),'-vf',f"setpts=PTS-STARTPTS,select=gte(t\\,{stamp}),scale=360:-2",'-frames:v','1',str(dest)],check=True,timeout=45)
        if not dest.is_file(): raise ValueError('No picture at requested timestamp')
        # The first selected presentation time is resolved with FFprobe, rather
        # than asserting that requested fractional seconds equal a frame time.
        actual=next((value-origin for value in clock if value-origin>=stamp-1e-9),None)
        pictures.append({'file':dest.name,'requested_seconds':stamp,'actual_seconds':actual,'sha256':sha(dest)})
    result={'source_sha256':sha(source),'duration_seconds':duration,'width':video['width'],'height':video['height'],
            'decode_passed':True,'audio':audio,'pictures':pictures,'findings':findings,'technical_passed':not findings,'visual_review':'pending','published':False}
    (output/'review.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--times',type=float,nargs='+');parser.add_argument('--expect-audio',action='store_true')
    args=parser.parse_args()
    try:
        result=inspect(args.video,args.out,args.times,args.expect_audio)
        print(json.dumps(result));raise SystemExit(0 if result['technical_passed'] else 2)
    except (ValueError,FileExistsError,KeyError) as exc: parser.exit(2,str(exc)+'\n')
