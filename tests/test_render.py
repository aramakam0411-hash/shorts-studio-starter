import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import wave

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('render',ROOT/'render.py')
renderer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class Validation(unittest.TestCase):
    def setUp(self):
        self.data={'fps':12,'scenes':[{'title':'Show the change','seconds':1,'steps':['Input','Change','Result'],'credit':'Original test'}],
                   'captions':[{'start':0.1,'end':0.9,'text':'A visible change'}]}

    def write(self,folder,data=None):
        path=Path(folder)/'short.json'
        path.write_text(json.dumps(self.data if data is None else data))
        return path

    def test_bad_clock_and_asset_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            for seconds in (float('nan'),True,-1,1.01):
                data=copy.deepcopy(self.data);data['scenes'][0]['seconds']=seconds
                with self.assertRaises(ValueError): renderer.load(self.write(tmp,data))
            data=copy.deepcopy(self.data);data['captions'][0]['end']=2
            with self.assertRaises(ValueError): renderer.load(self.write(tmp,data))
            data=copy.deepcopy(self.data);data['scenes'][0]['media']={'kind':'image','path':'../outside.png'}
            with self.assertRaises(ValueError): renderer.load(self.write(tmp,data))

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
    def test_real_images_clip_audio_music_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            image=root/'demo.png';Image.new('RGB',(180,320),'#ce483a').save(image)
            self.data['scenes'][0]['media']={'kind':'image','path':'demo.png'}
            second=copy.deepcopy(self.data['scenes'][0]);second['media']={'kind':'video','path':'demo.mp4'}
            self.data['scenes'].append(second)
            subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=blue:size=180x320:rate=12:duration=1','-c:v','libx264','-threads','2',str(root/'demo.mp4')],check=True)
            sound=root/'tone.wav'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','sine=frequency=440:duration=2','-c:a','pcm_s16le',str(sound)],check=True)
            manifest=self.write(root)
            out=root/'rendered'
            receipt=renderer.render(manifest,out,360,audio=sound,music=sound)
            self.assertFalse(receipt['silent'])
            self.assertEqual(len(receipt['media']),2)
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(out/'short.mp4')]))
            self.assertAlmostEqual(float(probe['format']['duration']),2,places=1)
            self.assertEqual({s['codec_type'] for s in probe['streams']},{'video','audio'})
            video=next(s for s in probe['streams'] if s['codec_type']=='video')
            self.assertEqual((video['width'],video['height']),(360,640))
            pictures=[]
            for stamp in ('0.1','0.8','1.5'):
                raw=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-ss',stamp,'-i',str(out/'short.mp4'),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
                self.assertEqual(len(raw),360*640*3);pictures.append(raw)
            self.assertNotEqual(pictures[0],pictures[1])
            self.assertNotEqual(pictures[1],pictures[2])
            pcm=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(out/'short.mp4'),'-vn','-f','s16le','pipe:1'])
            self.assertTrue(any(pcm))
            with self.assertRaises(FileExistsError): renderer.render(manifest,out,360)
            # Refuse insufficient narration before creating output.
            self.data['scenes'].append(copy.deepcopy(second))
            self.write(root)
            with self.assertRaises(ValueError): renderer.render(manifest,root/'bad',360,audio=sound)
            self.assertFalse((root/'bad').exists())
