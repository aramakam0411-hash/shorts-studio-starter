"""Real copied-skill renders, audio checks and resource boundary failures."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'skills/render-layered-motion/scripts/render_html.py'
spec = importlib.util.spec_from_file_location('layered_renderer', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
CHROME = os.environ.get('SHORTS_STUDIO_CHROMIUM')
PLAYWRIGHT = importlib.util.find_spec('playwright') is not None
HTML = '''<!doctype html><style>body{margin:0}</style><canvas id="c"></canvas>
<script>c.width=innerWidth;c.height=innerHeight;const x=c.getContext('2d');
window.frame=t=>{x.fillStyle='#f2eee6';x.fillRect(0,0,c.width,c.height);
x.fillStyle='#2477df';x.fillRect(20+100*t,90,80,80)};</script>'''


class Validation(unittest.TestCase):
    def test_invalid_clock_audio_and_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);scene=folder/'scene.html';scene.write_text(HTML)
            for seconds in (float('nan'), .1, 120.5, 1.01):
                with self.assertRaises(ValueError):
                    module.validate(scene,folder/'out',seconds,24,360)
            folder.joinpath('existing').mkdir()
            with self.assertRaises(ValueError):
                module.validate(scene,folder/'existing',1,24,360)
            with self.assertRaises(ValueError):
                module.validate(scene,folder/'out',1,24,360,folder/'missing.wav')


@unittest.skipUnless(PLAYWRIGHT and shutil.which('ffmpeg') and shutil.which('ffprobe'),
                     'Playwright, its Chromium and FFmpeg required')
class RealBrowser(unittest.TestCase):
    def command(self, script, scene, out, *extra):
        args=[sys.executable,str(script),str(scene),'--out',str(out),
              '--seconds','1','--fps','12','--width','360',*extra]
        if CHROME:
            args += ['--chromium',CHROME]
        return subprocess.run(args,capture_output=True,text=True)

    def test_whole_skill_copy_with_real_audio_and_legacy_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);copy=folder/'copied-skill'
            shutil.copytree(SCRIPT.parents[1],copy,
                            ignore=shutil.ignore_patterns('__pycache__'))
            scene=folder/'scene.html';scene.write_text(HTML)
            sound=folder/'sound.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',
                            'sine=frequency=440:duration=1','-c:a','pcm_s16le',
                            str(sound)],check=True,capture_output=True)
            script=copy/'scripts/render_html.py';out=folder/'rendered'
            result=self.command(script,scene,out,'--audio',str(sound))
            self.assertEqual(result.returncode,0,result.stderr)
            receipt=json.loads(result.stdout)
            self.assertEqual(receipt['frames'],12)
            self.assertFalse(receipt['silent'])
            self.assertTrue(receipt['deterministic_frame_seek'])
            self.assertEqual(receipt['width'],360)
            self.assertEqual(receipt['height'],640)
            self.assertNotEqual(out.joinpath('picture-0000.jpg').read_bytes(),
                                out.joinpath('picture-0011.jpg').read_bytes())
            again=self.command(script,scene,out)
            self.assertEqual(again.returncode,2)
            reviewer=ROOT/'skills/review-short-export/scripts/inspect_export.py'
            checked=subprocess.run([sys.executable,str(reviewer),str(out/'video.mp4'),
                '--out',str(folder/'reviewed'),'--times','0.1','0.8','--expect-audio'],
                capture_output=True,text=True)
            self.assertEqual(checked.returncode,0,checked.stderr)
            self.assertTrue(json.loads(checked.stdout)['technical_passed'])

    def test_silence_and_audio_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);scene=folder/'scene.html';scene.write_text(HTML)
            result=self.command(SCRIPT,scene,folder/'silent')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['silent'])
            sound=folder/'short.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',
                            'sine=frequency=440:duration=0.4',str(sound)],
                            check=True,capture_output=True)
            result=self.command(SCRIPT,scene,folder/'bad','--audio',str(sound))
            self.assertEqual(result.returncode,2)
            self.assertFalse(folder.joinpath('bad').exists())

    def test_missing_function_and_external_request_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);scene=folder/'scene.html'
            scene.write_text('<p>No animation function</p>')
            result=self.command(SCRIPT,scene,folder/'missing')
            self.assertEqual(result.returncode,2)
            scene.write_text(HTML+'<img src="https://example.invalid/tracker.png">')
            result=self.command(SCRIPT,scene,folder/'external')
            self.assertEqual(result.returncode,2)
            self.assertFalse(folder.joinpath('external').exists())

    def test_parent_file_request_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);nested=folder/'scene';nested.mkdir()
            # A tiny SVG outside the authorized scene directory must not be loaded.
            folder.joinpath('outside.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            scene=nested/'scene.html';scene.write_text(HTML+'<img src="../outside.svg">')
            result=self.command(SCRIPT,scene,folder/'escape')
            self.assertEqual(result.returncode,2)
            self.assertFalse(folder.joinpath('escape').exists())


if __name__ == '__main__':
    unittest.main()
