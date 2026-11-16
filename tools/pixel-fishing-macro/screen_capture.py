"""Fast desktop capture; create and close on the worker thread."""
import sys
import cv2
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
        frame=np.asarray(self.screen.grab(self.monitor))[:,:,:3].copy()
        # macOS input uses logical points; Retina capture may use 2x backing pixels.
        width,height=self.monitor['width'],self.monitor['height']
        if sys.platform=='darwin' and frame.shape[:2] != (height,width):
            if frame.shape[:2] != (height*2,width*2):
                raise ValueError('Unexpected macOS capture scale; use a 1920×1080 primary display')
            frame=cv2.resize(frame,(width,height),interpolation=cv2.INTER_AREA)
        return frame

    def close(self):
        self.screen.close()
