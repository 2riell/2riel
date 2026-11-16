"""Fast desktop capture; create and close on the worker thread."""
import sys
import cv2
import numpy as np
import mss
from display_config import ScreenMap

class FastCapture:
    def __init__(self, check_resolution=True, preset="Auto-detect"):
        self.screen = mss.MSS()
        self.monitor = next((m for m in self.screen.monitors[1:] if m['left']==0 and m['top']==0),None)
        if self.monitor is None:
            self.close()
            raise ValueError('Primary display was not found')
        try:
            self.mapping=ScreenMap(self.monitor['width'],self.monitor['height'],preset)
        except Exception:
            self.close()
            raise

    def grab(self):
        frame=np.asarray(self.screen.grab(self.monitor))[:,:,:3].copy()
        # MSS monitor bounds use logical desktop points on macOS. Captured Retina
        # pixels can be 2x; normalize directly without an extra intermediate resize.
        mapping=getattr(self,'mapping',None) or ScreenMap(self.monitor['width'],self.monitor['height'])
        height,width=frame.shape[:2]
        if abs(width/height-mapping.width/mapping.height)>.025:
            raise ValueError('Capture proportions changed; stop and reselect the display preset')
        size=(mapping.tracker_width,mapping.tracker_height)
        if (width,height)!=size:
            frame=cv2.resize(frame,size,interpolation=cv2.INTER_AREA if width>size[0] else cv2.INTER_LINEAR)
        return frame

    def close(self):
        self.screen.close()
