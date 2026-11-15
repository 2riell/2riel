"""Visual assist for the recorded 1920x1080 UI; no desktop input on import."""
import base64
import zlib
import time
import sys
import ctypes
from dataclasses import dataclass
import cv2
import numpy as np
import vision_templates as templates


def green(image):
    b, g, r = cv2.split(image.astype(np.int16))
    return ((g > 110) & (g > r * 1.4) & (g > b * 1.35)).astype('uint8') * 255


def template(name):
    return np.frombuffer(zlib.decompress(base64.b64decode(getattr(templates, name+'_DATA'))), dtype='uint8').reshape(getattr(templates, name+'_SHAPE'))


@dataclass
class Observation:
    strike: bool = False
    bar: tuple | None = None
    fish_x: float | None = None
    target_x: float | None = None
    target_width: float = 0


def direction(obs):
    if obs.fish_x is None or obs.target_x is None:
        return None
    # Release inside the central zone to reduce oscillation.
    error = obs.fish_x - obs.target_x
    deadband = max(6, obs.target_width * .18)
    return 'd' if error > deadband else 'a' if error < -deadband else None


class Detector:
    def __init__(self):
        self.strike = template('STRIKE')
        self.fish = template('FISH')
        self.last_bar = None

    def inspect(self, frame):
        if frame.shape[:2] != (1080, 1920):
            raise ValueError('Visual assist requires a 1920×1080 game view at maximum zoom')
        # Search the upper half, independent of the character's horizontal position.
        mask = green(frame[:540])
        score = cv2.minMaxLoc(cv2.matchTemplate(mask, self.strike, cv2.TM_CCOEFF_NORMED))[1]
        obs = Observation(strike=score >= .78)
        # Locate the wide white frame surrounding the blue fishing track.
        white = cv2.inRange(frame[:400], (205,205,205), (255,255,255))
        contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = [cv2.boundingRect(c) for c in contours]
        parts = [b for b in boxes if 50 <= b[3] <= 90 and b[2] >= 30]
        candidates = []
        for a in parts:
            for b in parts:
                x,y = min(a[0],b[0]), min(a[1],b[1])
                w = max(a[0]+a[2],b[0]+b[2])-x
                h = max(a[1]+a[3],b[1]+b[3])-y
                if abs(a[1]-b[1]) < 8 and 760 <= w <= 880 and 50 <= h <= 90:
                    candidates.append((x,y,w,h))
        candidates = list(set(candidates))
        if len(candidates) == 1:
            self.last_bar = candidates[0]
        elif self.last_bar is None:
            return obs
        x,y,w,h = self.last_bar
        strip = frame[y+15:y+h-15,x+10:x+w-10].astype(np.int16)
        b,g,r = cv2.split(strip)
        if ((b > 120) & (b > r*1.4) & (g > 60)).mean() < .60:
            self.last_bar = None
            return obs
        obs.bar = (x,y,w,h)
        # The target outline has a long green horizontal edge at the top.
        left, right = max(0,x-80), min(1920,x+w+80)
        band = mask[max(0,y-6):y+15,left:right]
        columns = np.flatnonzero((band > 0).sum(axis=0) >= 5)
        if len(columns) < 50:
            return obs
        groups = np.split(columns, np.where(np.diff(columns) > 3)[0]+1)
        groups = [a for a in groups if 65 <= a[-1]-a[0] <= 160]
        if len(groups) != 1:
            return obs
        target = groups[0]
        obs.target_x = left + (target[0]+target[-1])/2
        obs.target_width = float(target[-1]-target[0])
        roi = mask[y:y+h,x:x+w]
        matches = [cv2.minMaxLoc(cv2.matchTemplate(roi,t,cv2.TM_CCOEFF_NORMED)) for t in (self.fish, cv2.flip(self.fish,1))]
        _, confidence, _, location = max(matches,key=lambda m:m[1])
        if confidence >= .70:
            obs.fish_x = x + location[0] + self.fish.shape[1]/2
        return obs


def focused_game():
    """Windows foreground gate. Called again immediately before each input."""
    if sys.platform != 'win32':
        raise RuntimeError('Visual assist currently supports Windows. Timed/pixel mode remains available on macOS.')
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    window = user32.GetForegroundWindow()
    title = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(window,title,512)
    return 'pixel worlds' in title.value.casefold()


def run_visual(p, stop, emit, backend):
    """Manual cast, automatic strike and feedback steering; never guesses catches."""
    detector = Detector()
    deadline = time.monotonic() + p.minutes*60
    held = None
    state = 'waiting'
    completed = 0
    last_seen = time.monotonic()
    strike_cleared = True
    strikes = 0

    def release():
        nonlocal held
        if held:
            # PyAutoGUI's corner failsafe must not prevent releasing our own key.
            previous = backend.FAILSAFE
            try:
                backend.FAILSAFE = False
                backend.keyUp(held)
            finally:
                backend.FAILSAFE = previous
                held = None

    try:
        emit('state', 'Visual assist: focus Pixel Worlds and cast manually')
        if stop.wait(p.countdown):
            return
        while not stop.is_set() and time.monotonic() < deadline and completed < p.cycles:
            if not focused_game():
                release()
                emit('state', 'Paused — focus Pixel Worlds')
                if stop.wait(.3):
                    break
                continue
            before = time.monotonic()
            frame = cv2.cvtColor(np.asarray(backend.screenshot()),cv2.COLOR_RGB2BGR)
            obs = detector.inspect(frame)
            # Drop slow captures instead of steering using an old frame.
            if time.monotonic()-before > .5 or not focused_game() or stop.is_set():
                release()
                continue
            now = time.monotonic()
            if not obs.strike:
                strike_cleared = True
            if obs.bar is not None and obs.fish_x is not None and obs.target_x is not None:
                if state != 'tracking':
                    emit('calibration', f'Fishing track located at {obs.bar}')
                    emit('state', 'Tracking fish — A / D')
                state = 'tracking'
                last_seen = now
                key = direction(obs)
                if key != held:
                    release()
                    if key and not p.dry_run and focused_game() and not stop.is_set():
                        held = key
                        backend.keyDown(key)
                    emit('steer', ('DRY ' if p.dry_run else '') + (key or 'release'))
            else:
                release()
                if state == 'tracking':
                    if now-last_seen > .6:
                        # An occluded bar and an ended round are ambiguous; stop.
                        emit('state','Track disappeared — stopped; catch outcome unverified')
                        completed += 1
                        break
                elif obs.strike and strike_cleared:
                    if strikes:
                        emit('state','Strike repeated without a track — stopped for inspection')
                        break
                    strikes += 1
                    strike_cleared = False
                    state = 'struck'
                    last_seen = now
                    emit('action', ('DRY ' if p.dry_run else '')+'space (strike)')
                    if not p.dry_run and focused_game() and not stop.is_set():
                        held = 'space'
                        try:
                            backend.keyDown(held)
                            stop.wait(.06)
                        finally:
                            release()
                elif state == 'struck' and now-last_seen > 5:
                    emit('timeout','Fishing track did not appear after strike')
                    break
            stop.wait(.03)
    except Exception as exc:
        emit('error',f'{type(exc).__name__}: {exc}')
    finally:
        release()
        emit('done',str(completed))
