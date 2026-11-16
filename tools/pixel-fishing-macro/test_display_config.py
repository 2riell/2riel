import unittest
from unittest.mock import patch
from types import SimpleNamespace
import cv2
import numpy as np
from display_config import ScreenMap,PRESETS
from screen_capture import FastCapture
from vision import Detector,template
from test_vision import scene

class DisplayTests(unittest.TestCase):
    def test_presets_and_retina_coordinate_round_trip(self):
        for preset in PRESETS[1:]:
            w,h=map(int,preset.split('x'))
            for scale in (1,2):
                m=ScreenMap(round(w/scale),round(h/scale),preset)
                point=(int(m.width*.7),int(m.height*.8))
                actual=m.to_screen(m.to_tracker(point))
                self.assertLessEqual(abs(actual[0]-point[0]),1)
                self.assertLessEqual(abs(actual[1]-point[1]),1)
                with self.assertRaises(ValueError):m.to_tracker((m.width,0))

    def test_mismatched_aspect_is_explained(self):
        with self.assertRaisesRegex(ValueError,'proportions'):
            ScreenMap(1408,881,'1920x1080')
        with self.assertRaises(ValueError):ScreenMap(100,100)

    def test_tracking_at_every_preset(self):
        for preset in PRESETS[1:]:
            w,h=map(int,preset.split('x'));m=ScreenMap(w,h,preset)
            canonical=np.zeros((m.tracker_height,1920,3),dtype=np.uint8)
            canonical[:1080]=scene(fish=1200,target=800)
            source=cv2.resize(canonical,(w,h))
            cap=FastCapture.__new__(FastCapture);cap.mapping=m
            cap.monitor={'width':w,'height':h}
            cap.screen=SimpleNamespace(grab=lambda monitor:source)
            obs=Detector().inspect(cap.grab())
            self.assertIsNotNone(obs.bar,preset)
            self.assertAlmostEqual(obs.fish_x,1200,delta=5,msg=preset)
            self.assertAlmostEqual(obs.target_x,800,delta=5,msg=preset)

    def test_collection_below_old_1080_boundary(self):
        im=np.zeros((1200,1920,3),dtype=np.uint8)
        for name,x,y in [('CAUGHT',880,600),('TAKE',842,1072)]:
            t=template(name);h,w=t.shape
            im[y:y+h,x:x+w]=cv2.cvtColor(t,cv2.COLOR_GRAY2BGR)
        self.assertEqual(Detector().inspect(im).take,(960,1106))
