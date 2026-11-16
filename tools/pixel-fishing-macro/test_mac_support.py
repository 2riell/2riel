import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from mac_support import focused_game,check_permissions
from screen_capture import FastCapture

class MacTests(unittest.TestCase):
    def test_focus_gate(self):
        for name,expected in [('Pixel Worlds',True),('FishingLab',False),('Safari',False)]:
            app=SimpleNamespace(localizedName=lambda:name)
            ws=SimpleNamespace(frontmostApplication=lambda:app)
            module=SimpleNamespace(NSWorkspace=SimpleNamespace(sharedWorkspace=lambda:ws))
            with patch.dict('sys.modules',{'AppKit':module}):
                self.assertEqual(focused_game(),expected)

    def test_missing_permissions_are_actionable(self):
        q=SimpleNamespace(CGPreflightScreenCaptureAccess=lambda:False,CGRequestScreenCaptureAccess=lambda:False)
        a=SimpleNamespace(kAXTrustedCheckOptionPrompt='prompt',AXIsProcessTrustedWithOptions=lambda args:False)
        with patch.dict('sys.modules',{'Quartz':q,'ApplicationServices':a}):
            with self.assertRaisesRegex(RuntimeError,'Screen Recording and Accessibility'):
                check_permissions()

    def test_retina_capture_uses_logical_coordinates(self):
        cap=FastCapture.__new__(FastCapture)
        cap.monitor={'width':1920,'height':1080}
        frame=np.zeros((2160,3840,4),dtype=np.uint8)
        frame[200:220,400:420,:3]=(10,20,30)
        cap.screen=SimpleNamespace(grab=lambda monitor:frame)
        with patch('screen_capture.sys.platform','darwin'):
            got=cap.grab()
        self.assertEqual(got.shape,(1080,1920,3))
        self.assertEqual(tuple(got[105,205]),(10,20,30))

class MacHotkeyTests(unittest.TestCase):
    class Root:
        def __init__(self):self.pending={};self.sequence=0
        def after(self,delay,callback):
            assert delay==20
            self.sequence+=1;self.pending[self.sequence]=callback
            return self.sequence
        def after_cancel(self,key):self.pending.pop(key,None)
        def tick(self):
            key=next(iter(self.pending));self.pending.pop(key)()

    def test_f8_polling_and_cleanup_without_layout_listener(self):
        import threading
        from mac_support import MacStopHotkey
        root=self.Root();events=[];errors=[];states=iter([False,True,True,False,True])
        def read(source,key):
            self.assertIs(threading.current_thread(),threading.main_thread())
            self.assertEqual((source,key),(0,100))
            return next(states)
        quartz=SimpleNamespace(CGEventSourceKeyState=read,kCGEventSourceStateCombinedSessionState=0)
        with patch.dict('sys.modules',{'Quartz':quartz}):
            monitor=MacStopHotkey(root,lambda:events.append('F8'),errors.append)
            monitor.start()
            for _ in range(4):root.tick()
            monitor.stop()
        self.assertEqual(events,['F8','F8']);self.assertEqual(errors,[])
        self.assertFalse(root.pending)

    def test_monitor_failure_reports_and_stops_polling(self):
        from mac_support import MacStopHotkey
        root=self.Root();errors=[]
        def read(*args):raise RuntimeError('test failure')
        quartz=SimpleNamespace(CGEventSourceKeyState=read,kCGEventSourceStateCombinedSessionState=0)
        with patch.dict('sys.modules',{'Quartz':quartz}):
            monitor=MacStopHotkey(root,lambda:None,errors.append);monitor.start()
        self.assertFalse(monitor.running);self.assertFalse(root.pending)
        self.assertIn('test failure',errors[0])

    def test_background_start_is_rejected_before_native_api(self):
        import threading
        from mac_support import MacStopHotkey
        errors=[]
        with patch.dict('sys.modules',{'Quartz':SimpleNamespace()}):
            monitor=MacStopHotkey(self.Root(),lambda:None,errors.append)
        def worker():
            try:monitor.start()
            except RuntimeError as exc:errors.append(str(exc))
        thread=threading.Thread(target=worker);thread.start();thread.join()
        self.assertIn('main thread',errors[0]);self.assertFalse(monitor.running)
