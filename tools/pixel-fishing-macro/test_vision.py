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
                    if delay<1: self.cancelled=True
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

class CastingTests(unittest.TestCase):
    def simulate(self, dry=False, lose_focus=False, stop_on_down=False, active=False):
        class Clock:
            now=0.
            cancelled=False
            def is_set(self): return self.cancelled
            def wait(self,seconds):
                self.now+=seconds
                return self.cancelled
        clock=Clock()
        class Backend:
            FAILSAFE=True
            focused=True
            def __init__(self): self.actions=[]
            def screenshot(self):
                clock.now+=.05
                return np.zeros((1080,1920,3),dtype='uint8')
            def moveTo(self,x,y):
                self.actions.append(('move',x,y))
                if lose_focus: self.focused=False
            def mouseDown(self,button):
                self.actions.append(('down',button))
                if stop_on_down: clock.cancelled=True
            def mouseUp(self,button): self.actions.append(('up',button))
            def keyDown(self,key): self.actions.append(('key',key))
            def keyUp(self,key): self.actions.append(('release',key))
        b=Backend();events=[]
        obs=Observation(bar=(549,100,822,70),fish_x=960,target_x=960,target_width=120) if active else Observation()
        p=Profile(visual=True,cast_x=1185,cast_y=755,dry_run=dry,minutes=.12,visual_timeout=5,countdown=1)
        with patch('vision.time.monotonic',lambda:clock.now), patch('vision.focused_game',lambda:b.focused), patch('vision.Detector') as d:
            d.return_value.inspect.return_value=obs
            run_visual(p,clock,lambda *a:events.append(a),b)
        return b.actions,events

    def test_click_once_then_timeout(self):
        actions,events=self.simulate()
        self.assertEqual(actions,[('move',1185,755),('down','left'),('up','left')])
        self.assertTrue(any(e[0]=='timeout' for e in events))

    def test_dry_cast_no_mouse_input(self):
        actions,events=self.simulate(dry=True)
        self.assertEqual(actions,[])
        self.assertEqual(sum(e[0]=='action' and 'cast click' in e[1] for e in events),1)

    def test_focus_lost_during_move_prevents_click(self):
        actions,_=self.simulate(lose_focus=True)
        self.assertEqual(actions,[('move',1185,755)])

    def test_mouse_released_on_stop(self):
        actions,events=self.simulate(stop_on_down=True)
        self.assertEqual(actions[-2:],[('down','left'),('up','left')])
        self.assertEqual(events[-1][0],'done')

    def test_existing_minigame_skips_cast(self):
        actions,_=self.simulate(active=True)
        self.assertEqual(actions,[])

    def test_requires_valid_coordinates_only_when_automatic(self):
        for x,y in [(-1,755),(1920,755),(1185,1080)]:
            with self.assertRaises(ValueError): Profile(visual=True,cast_x=x,cast_y=y).validate()
        Profile(visual=True,auto_cast=False).validate()
        Profile(visual=True,cast_x=1185,cast_y=755).validate()

class CollectionTests(unittest.TestCase):
    def test_dialog_requires_title_and_button(self):
        im=np.zeros((1080,1920,3),dtype='uint8')
        header=template('CAUGHT');button=template('TAKE')
        def paste(a,x,y):
            h,w=a.shape
            im[y:y+h,x:x+w]=cv2.cvtColor(a,cv2.COLOR_GRAY2BGR)
        paste(button,842,754)
        self.assertIsNone(Detector().inspect(im).take)
        paste(header,880,282)
        self.assertEqual(Detector().inspect(im).take,(960,788))
        shifted=cv2.warpAffine(im,np.float32([[1,0,70],[0,1,-50]]),(1920,1080))
        self.assertEqual(Detector().inspect(shifted).take,(1030,738))

    def simulate(self, stuck=False, no_dialog=False, dry=False, repeat=True, unlimited=False):
        class Clock:
            now=0.
            def is_set(self):return False
            def wait(self,delay):self.now+=delay;return False
        clock=Clock()
        class Backend:
            FAILSAFE=True
            point=None
            def __init__(self):self.clicks=[]
            def screenshot(self):clock.now+=.1;return np.zeros((1080,1920,3),dtype='uint8')
            def moveTo(self,x,y):self.point=(x,y)
            def mouseDown(self,button):self.clicks.append(self.point)
            def mouseUp(self,button):pass
            def keyDown(self,key):pass
            def keyUp(self,key):pass
        def inspect(frame):
            t=clock.now
            if no_dialog and t>=3.5:return Observation()
            if stuck and t>=4.5:return Observation(caught=True,take=(960,788))
            phase=t if t<6 else t-5
            if 2<=phase<2.5:return Observation(strike=True)
            if 2.5<=phase<3.5:return Observation(bar=(549,100,822,70),fish_x=960,target_x=960,target_width=120)
            if 4.5<=phase<5.5:return Observation(caught=True,take=(960,788))
            return Observation()
        b=Backend();events=[]
        p=Profile(visual=True,cast_x=1185,cast_y=755,countdown=1,cooldown=.1,minutes=.35,cycles=1 if unlimited else 2,dry_run=dry,repeat=repeat,unlimited_cycles=unlimited)
        with patch('vision.time.monotonic',lambda:clock.now),patch('vision.focused_game',return_value=True),patch('vision.Detector') as d:
            d.return_value.inspect.side_effect=inspect
            run_visual(p,clock,lambda *a:events.append(a),b)
        return b.clicks,events

    def test_collect_close_and_repeat_to_limit(self):
        clicks,events=self.simulate()
        self.assertEqual(clicks,[(1185,755),(960,788),(1185,755),(960,788)])
        self.assertEqual(events[-1],('done','2'))

    def test_stuck_dialog_never_reclicks_or_recasts(self):
        clicks,events=self.simulate(stuck=True)
        self.assertEqual(clicks,[(1185,755),(960,788)])
        self.assertEqual(events[-1],('done','0'))
        self.assertTrue(any(e[0]=='timeout' for e in events))

    def test_missing_catch_does_not_count_or_repeat(self):
        clicks,events=self.simulate(no_dialog=True)
        self.assertEqual(clicks,[(1185,755)])
        self.assertEqual(events[-1],('done','0'))

    def test_repeat_disabled_collects_one(self):
        clicks,events=self.simulate(repeat=False)
        self.assertEqual(clicks,[(1185,755),(960,788)])
        self.assertEqual(events[-1],('done','1'))

    def test_dry_collection_never_clicks(self):
        clicks,events=self.simulate(dry=True)
        self.assertEqual(clicks,[])
        self.assertEqual(events[-1],('done','2'))

class FastTrackingTests(unittest.TestCase):
    def test_far_fish_both_ends_and_red_yellow_graphics(self):
        for fish,target,expected in [(620,1210,'a'),(1300,700,'d')]:
            for color in [(0,220,0),(0,0,220),(0,220,220)]:
                im=scene(fish,target)
                original=(im[:,:,1]>150)&(im[:,:,0]<50)
                im[original]=color
                d=Detector();o=d.inspect(im)
                self.assertIsNotNone(o.fish_x,(fish,target,color))
                self.assertAlmostEqual(o.fish_x,fish,delta=3)
                self.assertAlmostEqual(o.target_x,target,delta=3)
                self.assertEqual(direction(o),expected)
                # Cached-track path must also recognize a distant fish.
                self.assertEqual(direction(d.inspect(im)),expected)

    def test_small_corrections_and_deadband(self):
        o=Observation(fish_x=975,target_x=960,target_width=120)
        self.assertEqual(direction(o,8),'d')
        self.assertIsNone(direction(o,20))

    def test_tracker_settings_validation(self):
        for kwargs in ({'tracker_hz':0},{'tracker_hz':121},{'deadband':float('nan')},{'opacity':30}):
            with self.assertRaises(ValueError):Profile(**kwargs).validate()
        Profile(tracker_hz=120,deadband=2,opacity=85).validate()

class UnlimitedTests(CollectionTests):
    def test_unlimited_continues_beyond_cycle_limit(self):
        clicks,events=self.simulate(unlimited=True)
        self.assertGreater(sum(e[0]=='cycle' for e in events),1)
        self.assertEqual(sum(e[0]=='fish' for e in events),sum(e[0]=='cycle' for e in events))

    def test_dry_run_has_no_fish_count(self):
        _,events=self.simulate(dry=True)
        self.assertFalse(any(e[0]=='fish' for e in events))
