import unittest
from unittest.mock import patch
from engine import Profile,run
from vision import run_visual
from session import StopSignal,SessionReporter

class SessionTests(unittest.TestCase):
    def test_stop_source_is_preserved(self):
        stop=StopSignal();stop.set('F8 hotkey');stop.set('App window closed')
        self.assertEqual(stop.reason,'F8 hotkey')
        stop.clear();self.assertIsNone(stop.reason)
        stop.set('Escape key');self.assertEqual(stop.reason,'Escape key')

    def test_unlimited_focus_pause_does_not_end_session(self):
        p=Profile(visual=True,unlimited_cycles=True,no_time_limit=True,minutes=.01,countdown=1)
        class Clock:
            now=0
            reason='Test explicitly stopped after 30 minutes'
            def is_set(self):return self.now>=1800
            def wait(self,n):self.now+=n;return self.is_set()
        clock=Clock();events=[]
        with patch('vision.time.monotonic',lambda:clock.now),patch('vision.focused_game',return_value=False):
            run_visual(p,clock,lambda *e:events.append(e),None)
        self.assertGreaterEqual(clock.now,1800)
        self.assertEqual(sum(e[0]=='state' and 'Paused' in e[1] for e in events),1)
        self.assertIn(('stop_reason',clock.reason),events)
        self.assertEqual(events[-1],('done','0'))

    def test_enable_no_time_limit_during_countdown(self):
        p=Profile(visual=True,no_time_limit=False,unlimited_cycles=True,minutes=.01,countdown=1)
        class Clock:
            now=0
            reason='Test cancellation'
            def is_set(self):return self.now>=5
            def wait(self,n):
                p.no_time_limit=True
                self.now+=n
                return self.is_set()
        clock=Clock();events=[]
        with patch('vision.time.monotonic',lambda:clock.now),patch('vision.focused_game',return_value=False):
            run_visual(p,clock,lambda *e:events.append(e),None)
        self.assertGreaterEqual(clock.now,5)
        self.assertIn(('stop_reason','Test cancellation'),events)

    def test_live_cycle_limit_change_in_timed_mode(self):
        p=Profile(cycles=1,no_time_limit=True,countdown=1,bite_wait=.1,cooldown=.1)
        class Clock:
            now=0
            cancelled=False
            reason='Test cancellation'
            def is_set(self):return self.cancelled
            def wait(self,n):self.now+=n;return self.cancelled
        clock=Clock();events=[]
        def emit(kind,message):
            events.append((kind,message))
            if kind=='cycle':
                p.unlimited_cycles=True
                if message=='3':clock.cancelled=True
        with patch('engine.time.monotonic',lambda:clock.now):run(p,clock,emit)
        self.assertEqual(events[-1],('done','3'))
        self.assertIn(('stop_reason','Test cancellation'),events)

    def test_limit_and_unexpected_exit_reasons(self):
        for p,now,done,expected in [
            (Profile(minutes=1),61,'18','Session time limit reached'),
            (Profile(cycles=18,no_time_limit=True),1,'18','Cycle limit reached'),
            (Profile(visual=True,repeat=False,no_time_limit=True),1,'1','Collect and repeat was disabled'),
            (Profile(unlimited_cycles=True,no_time_limit=True),1000,'18','Unexpected runner exit — export the session log')]:
            events=[]
            with patch('session.time.monotonic',return_value=0):report=SessionReporter(p,StopSignal(),lambda *e:events.append(e))
            with patch('session.time.monotonic',return_value=now):report('done',done)
            self.assertIn(('stop_reason',expected),events)
