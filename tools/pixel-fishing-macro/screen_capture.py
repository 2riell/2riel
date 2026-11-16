"""Fast Windows desktop capture; create and close on the worker thread."""
import numpy as np
import mss

class FastCapture:
    def __init__(self, check_resolution=True):
        self.screen = mss.MSS()
        self.monitor = next((m for m in self.screen.monitors[1:] if m['left']==0 and m['top']==0),None)
        if self.monitor is None or (check_resolution and (self.monitor['width'],self.monitor['height']) != (1920,1080)):
            self.close()
            raise ValueError('Visual tracking requires a primary 1920×1080 display')

    def grab(self):
        # MSS provides BGRA, so no PIL conversion is needed.
        return np.asarray(self.screen.grab(self.monitor))[:,:,:3].copy()

    def close(self):
        self.screen.close()
