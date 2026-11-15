import unittest
from unittest.mock import patch
import numpy as np
import cv2
from vision import Detector, Observation, direction, template, run_visual
from engine import Profile


def scene(fish=1000, target=960):
    im = np.zeros((1080,1920,3),dtype='uint8')
    cv2.rectangle(im,(549,100),(1370,169),(250,250,250),5)
    cv2.rectangle(im,(555,106),(1364,163),(200,120,40),-1)
    cv2.rectangle(im,(target-60,99),(target+60,166),(0,220,0),7)
    shape=template('FISH');h,w=shape.shape
    roi=im[112:112+h,fish-w//2:fish-w//2+w]
    roi[shape>0]=(0,220,0)
    return im


class VisionTests(unittest.TestCase):
    def test_strike_and_idle(self):
        d=Detector();im=np.zeros((1080,1920,3),dtype='uint8')
        self.assertFalse(d.inspect(im).strike)
        t=template('STRIKE');h,w=t.shape
        im[240:240+h,800:800+w][t>0]=(0,220,0)
        self.assertTrue(d.inspect(im).strike)

    def test_track_and_direction(self):
        for fish,target,expected in [(1000,960,'d'),(920,960,'a'),(960,960,None)]:
            o=Detector().inspect(scene(fish,target))
            self.assertIsNotNone(o.bar)
            self.assertAlmostEqual(o.fish_x,fish,delta=3)
            self.assertEqual(direction(o),expected)

    def test_translation(self):
        im=cv2.warpAffine(scene(),np.float32([[1,0,-80],[0,1,35]]),(1920,1080))
        o=Detector().inspect(im)
        self.assertAlmostEqual(o.target_x,880,delta=3)
        self.assertAlmostEqual(o.fish_x,920,delta=3)

    def test_disappearance(self):
        d=Detector();self.assertIsNotNone(d.inspect(scene()).bar)
        self.assertIsNone(d.inspect(np.zeros((1080,1920,3),dtype='uint8')).bar)
        self.assertIsNone(direction(Observation()))

    def test_wrong_resolution(self):
        with self.assertRaises(ValueError): Detector().inspect(np.zeros((720,1280,3),dtype='uint8'))

    def test_key_released_on_stop_and_no_input_in_dry_run(self):
        for dry in (False,True):
            class Stop:
                cancelled=False
                def is_set(self): return self.cancelled
                def wait(self,delay):
                    if delay==.03: self.cancelled=True
                    return self.cancelled
            class Backend:
                FAILSAFE=True
                def __init__(self):self.keys=[]
                def screenshot(self):return cv2.cvtColor(scene(),cv2.COLOR_BGR2RGB)
                def keyDown(self,key):self.keys.append(('down',key))
                def keyUp(self,key):self.keys.append(('up',key))
            b=Backend();events=[]
            with patch('vision.focused_game',return_value=True):
                run_visual(Profile(visual=True,dry_run=dry),Stop(),lambda *a:events.append(a),b)
            self.assertEqual(b.keys,[] if dry else [('down','d'),('up','d')])
            self.assertEqual(events[-1][0],'done')

if __name__=='__main__':unittest.main()
