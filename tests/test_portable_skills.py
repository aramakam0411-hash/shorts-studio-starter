import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
class PortableSkills(unittest.TestCase):
    def test_standalone_render_then_review_detects_missing_sound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            render=root/'render-skill';review=root/'review-skill'
            for name,dest in [('render-vertical-video',render),('review-short-export',review)]:
                shutil.copytree(ROOT/'skills'/name,dest,ignore=shutil.ignore_patterns('__pycache__'))
            manifest=root/'short.json'
            manifest.write_text(json.dumps({'fps':12,'scenes':[{'title':'Portable demo','seconds':1,'steps':['Input','Result'],'credit':'Original test'}]}))
            out=root/'rendered'
            subprocess.run([sys.executable,str(render/'scripts/render_short.py'),str(manifest),'--out',str(out),'--width','360'],cwd=tmp,capture_output=True,check=True)
            command=[sys.executable,str(review/'scripts/inspect_export.py'),str(out/'short.mp4'),'--times','0.15','0.75']
            result=subprocess.run([*command,'--out',str(root/'reviewed'),'--expect-audio'],cwd=tmp,capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            receipt=json.loads(result.stdout)
            self.assertIn('Expected audio stream is missing',receipt['findings'])
            self.assertAlmostEqual(receipt['pictures'][0]['actual_seconds'],1/6,places=5)
            self.assertTrue((root/'reviewed/frame-00.png').is_file())
            result=subprocess.run([*command,'--out',str(root/'silent-accepted')],cwd=tmp,capture_output=True,text=True,check=True)
            self.assertTrue(json.loads(result.stdout)['technical_passed'])

    def test_actual_audio_signal_and_invalid_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);video=root/'tone.mp4'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=red:size=180x320:rate=12:duration=1','-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-threads','2','-c:a','aac','-shortest',str(video)],check=True)
            helper=ROOT/'skills/review-short-export/scripts/inspect_export.py'
            result=subprocess.run([sys.executable,str(helper),str(video),'--out',str(root/'review'),'--times','0.15','0.75','--expect-audio'],capture_output=True,text=True,check=True)
            receipt=json.loads(result.stdout)
            self.assertTrue(receipt['audio']['nonzero'])
            self.assertGreater(receipt['audio']['rms'],0)
            self.assertEqual(receipt['audio']['perceptual_quality'],'not_assessed')
            result=subprocess.run([sys.executable,str(helper),str(video),'--out',str(root/'bad'),'--times','0.9','0.2'],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((root/'bad').exists())
