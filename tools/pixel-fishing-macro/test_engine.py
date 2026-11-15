import threading
import unittest
from unittest.mock import patch
from engine import Profile, run, matches

class Clock:
    def __init__(self): self.now = 0; self.cancelled = False
    def wait(self, seconds): self.now += seconds; return self.cancelled
    def is_set(self): return self.cancelled

class EngineTests(unittest.TestCase):
    def execute(self, p, clock=None, backend=None):
        clock = clock or Clock()
        events = []
        with patch('engine.time.monotonic', lambda: clock.now):
            run(p, clock, lambda *row: events.append(row), backend)
        return events

    def test_bounded_cycles(self):
        events = self.execute(Profile(cycles=3))
        self.assertEqual(sum(e[0]=='action' for e in events),6)
        self.assertEqual(events[-1],('done','3'))

    def test_deadline_prevents_reel(self):
        events = self.execute(Profile(minutes=.02, countdown=1))
        self.assertEqual(sum(e[0]=='action' for e in events),1)
        self.assertEqual(events[-1],('done','0'))

    def test_cancel_countdown(self):
        c=Clock(); c.cancelled=True
        self.assertFalse(any(e[0]=='action' for e in self.execute(Profile(),c)))

    def test_release_on_cancel(self):
        c=Clock()
        class Backend:
            def __init__(self): self.released=False
            def keyDown(self,key): c.cancelled=True
            def keyUp(self,key): self.released=True
        b=Backend()
        self.execute(Profile(dry_run=False),c,b)
        self.assertTrue(b.released)

    def test_stale_pixel_stops(self):
        class Backend:
            def keyDown(self,key): pass
            def keyUp(self,key): pass
            def pixel(self,x,y): return (255,255,255)
        events=self.execute(Profile(dry_run=False,pixel=True),backend=Backend())
        self.assertIn(('timeout','No fresh bite signal; stopped for inspection'),events)
        self.assertEqual(events[-1],('done','0'))

    def test_pixel_transition_reels(self):
        class Backend:
            n=0
            def keyDown(self,key): pass
            def keyUp(self,key): pass
            def pixel(self,x,y):
                self.n+=1
                return (0,0,0) if self.n==1 else (255,255,255)
        self.assertEqual(self.execute(Profile(dry_run=False,pixel=True,cycles=1),backend=Backend())[-1],('done','1'))

    def test_validation(self):
        for p in (Profile(cycles=0), Profile(hold=float('nan')), Profile(minutes=float('inf')), Profile(cast='bogus')):
            with self.assertRaises(ValueError): p.validate()
        self.assertTrue(matches((245,255,250),'#ffffff',10))
        self.assertFalse(matches((240,255,250),'#ffffff',10))

if __name__ == '__main__': unittest.main()
