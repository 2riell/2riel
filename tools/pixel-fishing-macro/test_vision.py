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
        p=Profile(visual=True,cast_x=1185,cast_y=755,dry_run=dry,minutes=.12,visual_timeout=5,countdown=1,wait_for_strike=False)
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
        for x,y in [(-1,755),(32768,755),(1185,32768)]:
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

class FailureRecoveryTests(unittest.TestCase):
    def test_ready_requires_disappearance_and_stable_return(self):
        from vision import CastReady
        r=CastReady();rng=np.random.default_rng(123)
        icon=rng.integers(0,255,(1080,1920,3),dtype=np.uint8)
        blank=np.zeros_like(icon);point=(1185,755)
        r.learn(icon,point)
        self.assertFalse(r.returned(icon,point,0))
        self.assertFalse(r.returned(blank,point,1))
        self.assertFalse(r.returned(icon,point,2))
        self.assertTrue(r.returned(icon,point,3))
        r.learn(icon,point)
        self.assertFalse(r.returned(icon,point,4))

    def test_failed_round_recasts_without_counting_fish(self):
        with patch('vision.CastReady') as ready:
            ready.return_value.returned.return_value=True
            clicks,events=CollectionTests().simulate(no_dialog=True)
        self.assertGreaterEqual(clicks.count((1185,755)),2)
        self.assertTrue(any(e[0]=='failed' for e in events))
        self.assertFalse(any(e[0]=='fish' for e in events))

class FullMeterTests(unittest.TestCase):
    def test_full_requires_last_segment(self):
        from vision import progress_full
        im=scene();bar=(549,100,822,70)
        for x in range(720,1201,24):
            cv2.rectangle(im,(x-5,194),(x+5,207),(20,220,240),-1)
        self.assertTrue(progress_full(im,bar))
        self.assertTrue(Detector().inspect(im).full)
        im[194:208,1195:1206]=0
        self.assertFalse(progress_full(im,bar))

    def test_space_once_per_full_meter_and_dry_run(self):
        for dry in (False,True):
            class Clock:
                now=0.
                def is_set(self):return False
                def wait(self,n):self.now+=n;return False
            clock=Clock()
            class Backend:
                FAILSAFE=True
                def __init__(self):self.keys=[]
                def screenshot(self):clock.now+=.1;return np.zeros((1080,1920,3),dtype='uint8')
                def keyDown(self,k):self.keys.append(('down',k))
                def keyUp(self,k):self.keys.append(('up',k))
            b=Backend();events=[]
            with patch('vision.time.monotonic',lambda:clock.now),patch('vision.focused_game',return_value=True),patch('vision.Detector') as d:
                d.return_value.inspect.return_value=Observation(full=True,bar=(549,100,822,70),fish_x=960,target_x=960,target_width=120)
                run_visual(Profile(visual=True,auto_cast=False,dry_run=dry,minutes=.06,countdown=1),clock,lambda *e:events.append(e),b)
            self.assertEqual(b.keys,[] if dry else [('down','space'),('up','space')])
            self.assertEqual(sum('full meter' in e[1] for e in events),1)

class ReacquireTests(unittest.TestCase):
    def test_long_dropout_keeps_searching_and_resumes(self):
        class Clock:
            now=0.
            def is_set(self):return False
            def wait(self,n):self.now+=n;return False
        clock=Clock()
        class Backend:
            FAILSAFE=True
            def __init__(self):self.keys=[]
            def screenshot(self):clock.now+=.1;return np.zeros((1080,1920,3),dtype='uint8')
            def keyDown(self,k):self.keys.append(k)
            def keyUp(self,k):pass
        def observe(frame):
            fish=1100 if clock.now<2 else None if clock.now<16 else 600
            return Observation(bar=(549,100,822,70),fish_x=fish,target_x=800,target_width=120)
        b=Backend();events=[]
        with patch('vision.time.monotonic',lambda:clock.now),patch('vision.focused_game',return_value=True),patch('vision.Detector') as d:
            d.return_value.inspect.side_effect=observe
            run_visual(Profile(visual=True,auto_cast=False,dry_run=False,minutes=.32,countdown=1),clock,lambda *e:events.append(e),b)
        self.assertIn('d',b.keys);self.assertIn('a',b.keys)
        self.assertTrue(any('Reacquiring' in e[1] for e in events))
        self.assertFalse(any(e[0]=='timeout' for e in events))

class LateStrikeTests(unittest.TestCase):
    def test_late_strike_and_timeout_boundary(self):
        for unlimited,arrival in [(True,150),(False,6.0)]:
            class Clock:
                now=0.
                cancelled=False
                def is_set(self):return self.cancelled
                def wait(self,n):self.now+=max(n,1);return self.cancelled
            clock=Clock()
            class Backend:
                FAILSAFE=True
                def __init__(self):self.keys=[]
                def screenshot(self):clock.now+=.01;return np.zeros((1080,1920,3),dtype='uint8')
                def moveTo(self,*args):pass
                def mouseDown(self,button):pass
                def mouseUp(self,button):pass
                def keyDown(self,key):self.keys.append(key);clock.cancelled=True
                def keyUp(self,key):self.keys.append('release '+key)
            b=Backend();events=[]
            p=Profile(visual=True,cast_x=1185,cast_y=755,dry_run=False,no_time_limit=True,wait_for_strike=unlimited,visual_timeout=5,countdown=1)
            with patch('vision.time.monotonic',lambda:clock.now),patch('vision.focused_game',return_value=True),patch('vision.Detector') as d:
                d.return_value.inspect.side_effect=lambda frame:Observation(strike=clock.now>=arrival)
                run_visual(p,clock,lambda *e:events.append(e),b)
            self.assertEqual(b.keys,['space','release space'])
            self.assertFalse(any(e[0]=='timeout' for e in events))

class IngredientTests(unittest.TestCase):
    def simulate_ingredient(self, arrival=2, cancel=False, track_first=False):
        class Clock:
            now=0.
            def is_set(self):return cancel and self.now>20
            def wait(self,n):self.now+=n;return self.is_set()
        clock=Clock()
        class Backend:
            FAILSAFE=True
            def __init__(self):self.clicks=0;self.keys=[]
            def screenshot(self):clock.now+=.1;return np.zeros((1080,1920,3),dtype='uint8')
            def moveTo(self,*p):pass
            def mouseDown(self,button):self.clicks+=1
            def mouseUp(self,button):pass
            def keyDown(self,k):self.keys.append(k)
            def keyUp(self,k):pass
        b=Backend();events=[]
        def obs(frame):
            if clock.now<2:return Observation(strike=True)
            if track_first and clock.now<3:
                return Observation(bar=(549,100,822,70),fish_x=960,target_x=960)
            if arrival<=clock.now<arrival+2:return Observation(item=True,caught=True,take=(960,788))
            return Observation()
        with patch('vision.time.monotonic',lambda:clock.now),patch('vision.focused_game',return_value=True),patch('vision.Detector') as d:
            d.return_value.inspect.side_effect=obs
            run_visual(Profile(visual=True,auto_cast=False,dry_run=False,cycles=1,countdown=1,no_time_limit=True),clock,lambda *e:events.append(e),b)
        return b,events

    def test_collect_without_minigame_and_separate_count(self):
        b,events=self.simulate_ingredient()
        self.assertEqual(b.keys,['space'])
        self.assertEqual(b.clicks,1)
        self.assertIn(('item','1'),events)
        self.assertFalse(any(e[0]=='fish' for e in events))
        self.assertEqual(events[-1],('done','1'))

    def test_delayed_ingredient_survives_old_timeout(self):
        b,events=self.simulate_ingredient(arrival=30)
        self.assertEqual(b.keys,['space'])
        self.assertEqual(b.clicks,1)
        self.assertIn(('item','1'),events)
        self.assertEqual(events[-1],('done','1'))
        self.assertFalse(any(e[0]=='timeout' for e in events))

    def test_unrecognized_result_keeps_waiting_and_can_stop(self):
        b,events=self.simulate_ingredient(arrival=100,cancel=True)
        self.assertEqual(b.clicks,0)
        self.assertEqual(events[-1],('done','0'))
        self.assertFalse(any(e[0]=='timeout' for e in events))

    def test_short_and_narrow_ingredient_shell(self):
        for half_width in (200,250,300,350):
            im=np.zeros((1080,1920,3),dtype=np.uint8)
            cx,cy=960,650
            im[cy-160:cy-40,cx-half_width:cx-half_width+8]=(200,180,30)
            im[cy-160:cy-40,cx+half_width-8:cx+half_width]=(200,180,30)
            im[cy-22:cy+22,cx-95:cx+95]=(30,220,150)
            self.assertTrue(Detector().item_shell(im,cx,cy))
            im[:,:cx]=0
            self.assertFalse(Detector().item_shell(im,cx,cy))

    def test_result_after_track_disappears_survives_old_timeout(self):
        b,events=self.simulate_ingredient(arrival=30,track_first=True)
        self.assertEqual(b.clicks,1)
        self.assertIn(('item','1'),events)
        self.assertEqual(events[-1],('done','1'))
        self.assertFalse(any(e[0]=='timeout' for e in events))


class MotionGapTests(unittest.TestCase):
    def test_target_dropout_does_not_hide_visible_fish(self):
        im=scene(fish=1200,target=800)
        im[90:115,730:870]=0
        obs=Detector().track(im,(549,100,822,70))
        self.assertIsNone(obs.target_x)
        self.assertAlmostEqual(obs.fish_x,1200,delta=3)

    def test_fish_at_both_track_edges(self):
        for fish in (550,1370):
            obs=Detector().track(scene(fish=fish,target=950),(549,100,822,70))
            self.assertAlmostEqual(obs.fish_x,fish,delta=3)

    def test_short_gap_predicts_motion_then_expires(self):
        from vision import MotionSteering
        m=MotionSteering();bar=(549,100,822,70)
        m.key(Observation(bar=bar,fish_x=900,target_x=1000),1,8)
        m.key(Observation(bar=bar,fish_x=950,target_x=1000),1.05,8)
        self.assertEqual(m.key(Observation(bar=bar,target_x=1000),1.15,8),'d')
        self.assertIsNone(m.key(Observation(bar=bar,target_x=1000),1.26,8))
        # A new detection overrides the old prediction immediately.
        self.assertEqual(m.key(Observation(bar=bar,fish_x=800,target_x=1000),1.27,8),'a')

    def test_target_gap_and_track_disappearance(self):
        from vision import MotionSteering
        m=MotionSteering();bar=(549,100,822,70)
        self.assertEqual(m.key(Observation(bar=bar,fish_x=1200,target_x=900),1,8),'d')
        self.assertEqual(m.key(Observation(bar=bar,fish_x=1250),1.1,8),'d')
        self.assertIsNone(m.key(Observation(),1.11,8))
        self.assertIsNone(m.key(Observation(bar=bar,fish_x=1250),1.12,8))


class PersistentChaseTests(unittest.TestCase):
    def test_hold_during_long_dropout_then_reverse_immediately(self):
        from vision import MotionSteering
        m=MotionSteering();bar=(549,100,822,70)
        self.assertEqual(m.key(Observation(bar=bar,fish_x=1250,target_x=900),1,8,True),'d')
        for t in (1.1,2,10):
            self.assertEqual(m.key(Observation(bar=bar,target_x=1300),t,8,True),'d')
        self.assertEqual(m.key(Observation(bar=bar,fish_x=600,target_x=1300),10.01,8,True),'a')
        self.assertEqual(m.key(Observation(bar=bar,target_x=600),20,8,True),'a')
        self.assertIsNone(m.key(Observation(),20.01,8,True))
        self.assertIsNone(m.key(Observation(bar=bar),20.02,8,True))

    def test_centered_moving_fish_uses_latest_heading(self):
        from vision import MotionSteering
        m=MotionSteering();bar=(549,100,822,70)
        m.key(Observation(bar=bar,fish_x=950,target_x=1000),1,8,True)
        m.key(Observation(bar=bar,fish_x=1000,target_x=1000),1.05,8,True)
        self.assertEqual(m.key(Observation(bar=bar,target_x=1000),2,8,True),'d')

    def test_disabled_chase_still_expires(self):
        from vision import MotionSteering
        m=MotionSteering();bar=(549,100,822,70)
        m.key(Observation(bar=bar,fish_x=1250,target_x=900),1,8,False)
        self.assertIsNone(m.key(Observation(bar=bar,target_x=900),2,8,False))

    def test_new_option_defaults_on_for_old_profiles(self):
        self.assertTrue(Profile(**{'tracker_hz':60}).chase_lost_fish)


class SteeringContinuityTests(unittest.TestCase):
    def test_visible_fish_missing_target_preserves_hold(self):
        from vision import MotionSteering
        m=MotionSteering();bar=(549,100,822,70)
        self.assertEqual(m.key(Observation(bar=bar,fish_x=1200,target_x=900),1,8,True),'d')
        for t in (1.1,1.5,2,5):
            self.assertEqual(m.key(Observation(bar=bar,fish_x=1200),t,8,True),'d')
        self.assertEqual(m.key(Observation(bar=bar,fish_x=800,target_x=1000),5.01,8,True),'a')
        self.assertIsNone(m.key(Observation(),5.02,8,True))

    def test_small_track_box_jitter_keeps_chase(self):
        from vision import MotionSteering
        m=MotionSteering();bar=(549,100,822,70)
        m.key(Observation(bar=bar,fish_x=1200,target_x=900),1,8,True)
        self.assertEqual(m.key(Observation(bar=(551,101,820,69)),2,8,True),'d')
        self.assertIsNone(m.key(Observation(bar=(200,200,822,70)),3,8,True))

    def test_tolerance_boundary_does_not_pulse_key(self):
        from vision import MotionSteering
        for sign,key in ((1,'d'),(-1,'a')):
            m=MotionSteering();bar=(549,100,822,70)
            for i,error in enumerate((10,7,9,6,8)):
                self.assertEqual(m.key(Observation(bar=bar,fish_x=1000+sign*error,target_x=1000),i*.02,8,True),key)
            self.assertIsNone(m.key(Observation(bar=bar,fish_x=1000,target_x=1000),.12,8,True))
            self.assertEqual(m.key(Observation(bar=bar,fish_x=1000-sign*20,target_x=1000),.14,8,True),'a' if key=='d' else 'd')
