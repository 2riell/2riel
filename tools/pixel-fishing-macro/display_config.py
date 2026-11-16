"""Full-screen presets and mapping between logical desktop and detector coordinates."""
PRESETS=('Auto-detect','2816x1762','2408x1506','2048x1280','1920x1200','1408x881','1920x1080','1600x900','1280x720')

class ScreenMap:
    def __init__(self,width,height,preset='Auto-detect'):
        if preset not in PRESETS:
            raise ValueError('Select a supported screen preset')
        if width<640 or height<360:
            raise ValueError('The game display must be at least 640 × 360')
        ratio=width/height
        if preset!='Auto-detect':
            pw,ph=map(int,preset.split('x'))
            if abs(ratio-pw/ph)>.025:
                raise ValueError('Preset proportions do not match the primary display. Use Auto-detect or a matching full-screen preset.')
        if min(abs(ratio-16/9),abs(ratio-16/10))>.025:
            raise ValueError('Use a full-screen 16:9 or 16:10 game view')
        self.width,self.height=width,height
        self.tracker_width=1920
        self.tracker_height=round(height*1920/width)

    def to_tracker(self,point):
        x,y=point
        if not (0<=x<self.width and 0<=y<self.height):
            raise ValueError('Saved bait point is outside this display. Pick the bait position again.')
        return round(x*1920/self.width),round(y*self.tracker_height/self.height)

    def to_screen(self,point):
        x,y=point
        return (max(0,min(self.width-1,round(x*self.width/1920))),
                max(0,min(self.height-1,round(y*self.height/self.tracker_height))))
