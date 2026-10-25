"""Small CPU renderer: authored motion, optional images/clips, captions and audio."""
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_asset(root, value):
    path = (root/value).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Assets must be files inside the manifest folder')
    return path


def load(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding='utf-8'))
    fps = data.get('fps', 24)
    if type(fps) is not int or not 12 <= fps <= 30:
        raise ValueError('Use an integer frame rate from 12 to 30')
    scenes = data.get('scenes', [])
    if not 1 <= len(scenes) <= 30:
        raise ValueError('Provide 1 to 30 scenes')
    for scene in scenes:
        seconds = scene.get('seconds')
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 1 <= seconds <= 60:
            raise ValueError('Scene length must be 1 to 60 seconds')
        if abs(seconds*fps-round(seconds*fps)) > 1e-6:
            raise ValueError('Scene duration must align with the frame rate')
        if not isinstance(scene.get('title'), str) or not 1 <= len(scene['title']) <= 100:
            raise ValueError('Provide a title of 1 to 100 characters')
        steps = scene.get('steps', [])
        if not 1 <= len(steps) <= 4 or any(not isinstance(x, str) or not 1 <= len(x) <= 24 for x in steps):
            raise ValueError('Provide 1 to 4 steps of at most 24 characters')
        if not isinstance(scene.get('credit'), str) or not 1 <= len(scene['credit']) <= 150:
            raise ValueError('Each scene needs a short credit or original label')
        if scene.get('media'):
            if scene['media'].get('kind') not in ('image', 'video'):
                raise ValueError('Media kind must be image or video')
            local_asset(path.parent, scene['media']['path'])
    total = sum(s['seconds'] for s in scenes)
    if total > 180:
        raise ValueError('Maximum total duration is 180 seconds')
    for caption in data.get('captions', []):
        start, end = caption['start'], caption['end']
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in (start,end)) or not 0 <= start < end <= total:
            raise ValueError('Caption timestamps must be inside the video')
        if not isinstance(caption.get('text'), str) or not 1 <= len(caption['text']) <= 100:
            raise ValueError('Caption text must have 1 to 100 characters')
    return data


def fonts(path, width):
    choices = [path] if path else [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Supplemental/Arial.ttf', 'C:/Windows/Fonts/arial.ttf']
    selected = next((p for p in choices if p and Path(p).is_file()), None)
    if not selected:
        raise ValueError('Set --font to a local TrueType font')
    return {name: ImageFont.truetype(selected, max(10, round(size*width/360)))
            for name,size in [('title',29), ('body',19), ('small',11), ('caption',20)]}


def wrapped(draw, text, font, max_width):
    lines, current = [], ''
    for word in text.split():
        if draw.textlength(word, font=font) > max_width:
            raise ValueError('A word is too wide; shorten it or insert spaces')
        candidate = (current+' '+word).strip()
        if draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current: lines.append(current)
    return '\n'.join(lines)


def frame(scene, t, absolute, total, width, f, captions, background=None):
    height, scale = width*16//9, width/360
    im = Image.new('RGB', (width,height), '#101821')
    d = ImageDraw.Draw(im)
    def box(coords, fill, outline=None):
        d.rounded_rectangle(tuple(round(v*scale) for v in coords), radius=round(11*scale), fill=fill, outline=outline, width=max(1,round(2*scale)))
    def text(x,y,value,font='body',fill='#eef4fa'):
        d.multiline_text((round(x*scale),round(y*scale)), value, font=f[font], fill=fill, spacing=round(5*scale))
    text(26,30,'SHORTS STUDIO','small','#8ce6c8')
    title = wrapped(d, scene['title'], f['title'], width-52*scale)
    text(26,67,title,'title')
    steps = scene['steps']
    if background is not None:
        fitted = ImageOps.fit(background, (round(308*scale),round(200*scale)))
        im.paste(fitted, (round(26*scale),round(205*scale)))
        d = ImageDraw.Draw(im)
        base, gap = 427, 35
    else:
        base, gap = 218, 77
    # The same flow builds in order, moves into place, then holds on the result.
    for index, label in enumerate(steps):
        start = index*0.35
        progress = min(1, max(0, (t-start)/0.6))
        if not progress: continue
        ease = 1-(1-progress)**3
        y = base+index*gap
        offset = (1-ease)*40
        active = index == min(len(steps)-1, int(max(0,t-0.4)/(scene['seconds']/len(steps))))
        if index:
            d.line((width//2,round((y-gap+29)*scale),width//2,round((y-5)*scale)),fill='#54716e',width=max(2,round(2*scale)))
        box((26+offset,y,334+offset,y+(29 if background is not None else 48)), '#21493f' if active else '#1d2b38', '#8ce6c8' if active else '#344655')
        text(40+offset,y+(3 if background is not None else 11),label,'small' if background is not None else 'body')
    # A persistent packet travels along the visible flow, connecting action
    # and result instead of adding an unrelated decorative movement.
    if background is None and t > 1.1 and len(steps)>1:
        position=min(len(steps)-1,(t-1.1)/max(0.5,(scene['seconds']-2)/(len(steps)-1)))
        y=base+24+position*gap
        radius=4*scale
        x=width-40*scale
        d.ellipse((x-radius,y*scale-radius,x+radius,y*scale+radius),fill='#8ce6c8')
    # Captions occupy a fixed lower safe zone and use explicit supplied timing.
    current = [c['text'] for c in captions if c['start'] <= absolute < c['end']]
    if current:
        value = wrapped(d, current[-1], f['caption'], width-72*scale)
        if len(value.splitlines()) > 3: raise ValueError('Caption exceeds three lines; split its interval')
        box((24,522,336,595),'#071018')
        text(36,530,value,'caption')
    credit = wrapped(d, scene['credit'], f['small'], width-52*scale)
    if len(credit.splitlines()) > 2: raise ValueError('Credit exceeds two lines; use a short source label')
    text(26,604,credit,'small','#9db0c1')
    d.rectangle((0,height-round(4*scale),round(width*absolute/total),height),fill='#8ce6c8')
    return im


def render(manifest, output, width=720, font=None, audio=None, music=None):
    manifest, output = Path(manifest).resolve(), Path(output)
    data = load(manifest)
    if width not in (360,720,1080): raise ValueError('Width must be 360, 720 or 1080')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'): raise ValueError('Install FFmpeg and FFprobe')
    f = fonts(font,width)
    total = sum(s['seconds'] for s in data['scenes'])
    # Require actual audio long enough for the film; never silently truncate it.
    inputs = {}
    for name,value in [('narration',audio),('music',music)]:
        if value:
            p=Path(value).resolve()
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
            if not any(s['codec_type']=='audio' for s in probe['streams']): raise ValueError('Input has no audio')
            if name=='narration' and float(probe['format']['duration'])+0.05 < total: raise ValueError('Narration is shorter than the film; fix timing first')
            inputs[name]=p
    output.mkdir(parents=True, exist_ok=False)
    fps, cursor = data.get('fps',24), 0
    media_receipts=[]
    with tempfile.TemporaryDirectory(dir=output) as work:
        silent=Path(work)/'picture.mp4'
        encoder=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{width*16//9}','-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',str(silent)],stdin=subprocess.PIPE)
        try:
            for scene in data['scenes']:
                background, decoder = None,None
                try:
                    if scene.get('media'):
                        asset=local_asset(manifest.parent,scene['media']['path'])
                        media_receipts.append({'path':scene['media']['path'],'sha256':digest(asset)})
                        if scene['media']['kind']=='image':
                            with Image.open(asset) as src: background=src.convert('RGB')
                        else:
                            decoder=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-stream_loop','-1','-i',str(asset),'-an','-vf',f'scale={width}:{width*16//9}:force_original_aspect_ratio=increase,crop={width}:{width*16//9},fps={fps}','-t',str(scene['seconds']),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
                    for index in range(round(scene['seconds']*fps)):
                        if decoder:
                            raw=decoder.stdout.read(width*(width*16//9)*3)
                            if len(raw)!=width*(width*16//9)*3: raise ValueError('Clip decoding failed')
                            background=Image.frombytes('RGB',(width,width*16//9),raw)
                        picture=frame(scene,index/fps,cursor+index/fps,total,width,f,data.get('captions',[]),background)
                        encoder.stdin.write(picture.tobytes())
                    cursor+=scene['seconds']
                finally:
                    if decoder:
                        decoder.stdout.close()
                        decoder.wait(timeout=15)
            encoder.stdin.close()
            if encoder.wait(timeout=60): raise ValueError('Video encoding failed')
        finally:
            if encoder.poll() is None:
                encoder.kill();encoder.wait()
        destination=output/'short.mp4'
        command=['ffmpeg','-nostdin','-v','error','-i',str(silent)]
        if audio:
            # Normalize separately: short buffered loudnorm+amix graphs can emit
            # no audio on some FFmpeg versions. Probe the final output below.
            normalized=Path(work)/'narration.wav'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(inputs['narration']),'-vn','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-ar','48000','-c:a','pcm_s16le',str(normalized)],check=True,timeout=90)
            command+=['-i',str(normalized)]
        if music: command+=['-stream_loop','-1','-i',str(inputs['music'])]
        if audio and music:
            command+=['-filter_complex','[2:a]volume=0.10[m];[1:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.84:level=0:latency=1[a]','-map','0:v','-map','[a]']
        elif audio or music:
            command+=['-map','0:v','-map','1:a']
            if not audio: command+=['-af','volume=0.10']
        command+=['-c:v','copy','-c:a','aac','-t',str(total),'-movflags','+faststart',str(destination)]
        subprocess.run(command,check=True,timeout=90)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(destination)]))
    if bool(inputs) != any(s['codec_type']=='audio' for s in probe['streams']):
        raise ValueError('Final audio stream mismatch; output is not accepted')
    if abs(float(probe['format']['duration'])-total)>0.1:
        raise ValueError('Final duration mismatch; output is not accepted')
    subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(destination),'-f','null','-'],check=True,timeout=90)
    receipt={'video':'short.mp4','sha256':digest(destination),'manifest_sha256':digest(manifest),'duration_seconds':total,
        'width':width,'height':width*16//9,'fps':fps,'silent':not bool(audio or music),
        'audio':{name:{'sha256':digest(path)} for name,path in inputs.items()},'media':media_receipts,
        'speech_alignment':'manual timestamps only; not automatic recognition','published':False}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--width',type=int,default=720,choices=(360,720,1080))
    parser.add_argument('--font')
    parser.add_argument('--audio',type=Path)
    parser.add_argument('--music',type=Path)
    args=parser.parse_args()
    try: print(json.dumps(render(args.manifest,args.out,args.width,args.font,args.audio,args.music)))
    except (ValueError,FileExistsError,KeyError) as exc: parser.exit(2,f'{exc}\n')
