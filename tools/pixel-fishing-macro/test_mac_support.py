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
