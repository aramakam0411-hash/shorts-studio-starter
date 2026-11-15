"""Render a reviewed local absolute-time HTML scene. No downloader or publisher."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from urllib.parse import unquote, urlsplit


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audio_seconds(path):
    result = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries',
        'stream=codec_type,duration:format=duration', '-of', 'json', str(path)]))
    streams = [s for s in result['streams'] if s['codec_type'] == 'audio']
    if len(streams) != 1:
        raise ValueError('Supply a recording with exactly one audio stream')
    return float(streams[0].get('duration', result['format']['duration']))


def validate(scene, out, seconds, fps, width, audio=None):
    if not scene.is_file() or scene.suffix.lower() not in ('.html', '.htm'):
        raise ValueError('Supply an existing local HTML scene')
    if out.exists():
        raise ValueError('Output directory already exists; preserve earlier work')
    frames = seconds * fps
    if (not math.isfinite(seconds) or not .25 <= seconds <= 120
            or abs(frames-round(frames)) > 1e-6 or frames > 3600):
        raise ValueError('Duration must end on a whole frame within the render limit')
    if fps not in (12, 24, 30) or width not in (360, 720, 1080):
        raise ValueError('Unsupported frame rate or width')
    if audio and (not audio.is_file() or abs(audio_seconds(audio)-seconds) > 1/fps):
        raise ValueError('Supplied audio must match duration within one video frame')
    return round(frames)


def render(scene, out, seconds=6.0, fps=24, width=720, audio=None, chromium=None):
    scene = Path(scene).resolve(strict=True)
    out = Path(out).resolve()
    audio = Path(audio).resolve(strict=True) if audio else None
    count = validate(scene, out, seconds, fps, width, audio)
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise ValueError('FFmpeg and FFprobe must already be installed')
    from playwright.sync_api import sync_playwright

    inputs = {str(scene): sha(scene)}
    if audio:
        inputs[str(audio)] = sha(audio)
    blocked = []
    errors = []
    local_assets = set()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path=chromium)
        try:
            page = browser.new_page(viewport={'width': width, 'height': width*16//9},
                                    service_workers='block')

            def local_only(route):
                address = urlsplit(route.request.url)
                if address.scheme == 'data':
                    route.continue_()
                    return
                if address.scheme == 'file' and address.netloc in ('', 'localhost'):
                    path = Path(unquote(address.path)).resolve()
                    if path.is_relative_to(scene.parent) and path.is_file():
                        local_assets.add(path)
                        route.continue_()
                        return
                blocked.append(address.scheme or 'unknown')
                route.abort()

            page.route('**/*', local_only)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(scene.as_uri(), wait_until='load')
            page.evaluate('document.fonts.ready')
            if not page.evaluate("typeof window.frame === 'function'"):
                raise ValueError('Scene must define window.frame(seconds)')
            sample = min(seconds*.25, seconds-1/fps)
            page.evaluate('window.frame', sample)
            picture = page.screenshot(type='jpeg', quality=93)
            page.evaluate('window.frame', max(0, seconds-1/fps))
            page.evaluate('window.frame', sample)
            if picture != page.screenshot(type='jpeg', quality=93):
                raise ValueError('Frame depends on previous state; use absolute time')
            if blocked or errors:
                raise ValueError('Scene requested forbidden resources or raised a browser error')
            for asset in local_assets:
                inputs[str(asset)] = sha(asset)
            out.mkdir(parents=True, exist_ok=False)
            movie = out/'video.mp4'
            command = ['ffmpeg', '-nostdin', '-v', 'error', '-threads', '2',
                       '-f', 'image2pipe', '-vcodec', 'mjpeg', '-r', str(fps),
                       '-i', 'pipe:0']
            if audio:
                command += ['-i', str(audio), '-map', '0:v:0', '-map', '1:a:0',
                            '-af', 'apad', '-t', str(seconds), '-c:a', 'aac', '-b:a', '160k']
            else:
                command += ['-an']
            command += ['-c:v', 'libx264', '-threads', '2', '-crf', '18',
                        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(movie)]
            encoder = subprocess.Popen(command, stdin=subprocess.PIPE,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                for n in range(count):
                    page.evaluate('window.frame', n/fps)
                    picture = page.screenshot(type='jpeg', quality=93)
                    encoder.stdin.write(picture)
                    if n in {0, count//2, count-1}:
                        (out/f'picture-{n:04}.jpg').write_bytes(picture)
                encoder.stdin.close()
                if encoder.wait(timeout=60):
                    raise ValueError('FFmpeg encoding failed; inspect retained output')
            finally:
                if encoder.poll() is None:
                    encoder.kill()
                    encoder.wait()
            if blocked or errors:
                raise ValueError('Scene requested forbidden resources or raised a browser error')
            for asset in local_assets:
                if str(asset) not in inputs:
                    raise ValueError('Scene loaded an asset during rendering; preload assets')
        finally:
            browser.close()
    if any(sha(Path(p)) != digest for p, digest in inputs.items()):
        raise ValueError('Input changed during rendering')
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-count_frames', '-show_entries',
        'stream=codec_type,width,height,nb_read_frames:format=duration',
        '-of', 'json', str(movie)]))
    video = [s for s in probe['streams'] if s['codec_type'] == 'video']
    if (len(video) != 1 or int(video[0]['nb_read_frames']) != count
            or (video[0]['width'], video[0]['height']) != (width, width*16//9)
            or any(s['codec_type']=='audio' for s in probe['streams']) != bool(audio)):
        raise ValueError('Encoded stream or frame count mismatch')
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(movie),
                    '-f', 'null', '-'], check=True, capture_output=True)
    receipt = {'frames': count, 'fps': fps, 'width': width, 'height': width*16//9,
               'duration_seconds': seconds, 'silent': not bool(audio),
               'inputs': inputs, 'helper_sha256': sha(Path(__file__)),
               'video_sha256': sha(movie), 'deterministic_frame_seek': True,
               'blocked_requests': 0, 'full_decode': True,
               'limits': 'No hearing, story-quality, exact speech-sync or publishing verdict.'}
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('scene', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=6)
    p.add_argument('--fps', type=int, default=24, choices=(12,24,30))
    p.add_argument('--width', type=int, default=720, choices=(360,720,1080))
    p.add_argument('--audio', type=Path)
    p.add_argument('--chromium', help='Existing Chromium executable; otherwise Playwright default')
    args = p.parse_args()
    try:
        print(json.dumps(render(args.scene, args.out, args.seconds, args.fps,
                                args.width, args.audio, args.chromium)))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        p.exit(2, f'{type(error).__name__}: {error}\n')


if __name__ == '__main__':
    main()
