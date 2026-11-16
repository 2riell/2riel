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


def tracking_mask(image):
    # Track the silhouette/outline even when they change from green to red.
    b,g,r = cv2.split(image.astype(np.int16))
    bright = np.maximum(r,g)
    return ((bright > 100) & (bright > b*1.35) & (bright-b > 45)).astype('uint8')*255


def template(name):
    return np.frombuffer(zlib.decompress(base64.b64decode(getattr(templates, name+'_DATA'))), dtype='uint8').reshape(getattr(templates, name+'_SHAPE'))


@dataclass
class Observation:
    full: bool = False
    caught: bool = False
    take: tuple | None = None
    strike: bool = False
    bar: tuple | None = None
    fish_x: float | None = None
    target_x: float | None = None
    target_width: float = 0


def progress_full(frame, bar):
    x,y,w,h = bar
    # 21 meter segments measured from the supplied 1920x1080 UI.
    for offset in range(171,652,24):
        cx=x+offset
        patch=frame[y+94:y+107,cx-4:cx+5]
        if patch.shape[:2] != (13,9):
            return False
        b,g,r=cv2.split(patch.astype(np.int16))
        if ((r>150)&(g>100)&(b<g*.8)).mean() < .55:
            return False
    return True


def direction(obs, deadband_pixels=8):
    if obs.fish_x is None or obs.target_x is None:
        return None
    # Release inside the central zone to reduce oscillation.
    error = obs.fish_x - obs.target_x
    deadband = deadband_pixels
    return 'd' if error > deadband else 'a' if error < -deadband else None


class Detector:
    def __init__(self):
        self.strike = template('STRIKE')
        self.fish = template('FISH')
        self.last_bar = None
        self.caught = template('CAUGHT')
        self.take = template('TAKE')

    def inspect(self, frame):
        if frame.shape[:2] != (1080, 1920):
            raise ValueError('Visual assist requires a 1920×1080 game view at maximum zoom')
        # Fast path: once acquired, process only the small fishing track.
        if self.last_bar is not None:
            tracked = self.track(frame,self.last_bar)
            if tracked is not None:
                return tracked
            self.last_bar = None
        # Require both the catch title and Take Fish button at the dialog spacing.
        gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        _,score,_,point = cv2.minMaxLoc(cv2.matchTemplate(gray,self.caught,cv2.TM_CCOEFF_NORMED))
        caught = score >= .85
        if caught:
            hx,hy = point
            left,top = max(0,hx-80), max(0,hy+440)
            roi = gray[top:min(1080,hy+560),left:min(1920,hx+240)]
            if roi.shape[0] >= self.take.shape[0] and roi.shape[1] >= self.take.shape[1]:
                _,confidence,_,location = cv2.minMaxLoc(cv2.matchTemplate(roi,self.take,cv2.TM_CCOEFF_NORMED))
                if confidence >= .80:
                    return Observation(caught=True,take=(left+location[0]+self.take.shape[1]//2,top+location[1]+self.take.shape[0]//2))
        # Search the upper half, independent of the character's horizontal position.
        mask = green(frame[:540])
        score = cv2.minMaxLoc(cv2.matchTemplate(mask, self.strike, cv2.TM_CCOEFF_NORMED))[1]
        obs = Observation(caught=caught,strike=score >= .78)
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
        return self.track(frame,self.last_bar) or obs

    def track(self, frame, bar):
        x,y,w,h = bar
        strip = frame[y+15:y+h-15,x+10:x+w-10].astype(np.int16)
        b,g,r = cv2.split(strip)
        if ((b > 120) & (b > r*1.4) & (g > 60)).mean() < .60:
            return None
        obs = Observation(bar=bar,full=progress_full(frame,bar))
        left,right = max(0,x-80),min(1920,x+w+80)
        top = max(0,y-6)
        mask = tracking_mask(frame[top:y+h,left:right])
        band = mask[:y+15-top]
        columns = np.flatnonzero((band > 0).sum(axis=0) >= 5)
        if len(columns) < 50:
            return obs
        groups = np.split(columns,np.where(np.diff(columns)>3)[0]+1)
        groups = [a for a in groups if 65 <= a[-1]-a[0] <= 160]
        if len(groups) != 1:
            return obs
        target = groups[0]
        obs.target_x = left+(target[0]+target[-1])/2
        obs.target_width = float(target[-1]-target[0])
        # Search the FULL track; distance from the target does not limit detection.
        roi = mask[y-top:y-top+h,x-left:x-left+w]
        matches = [cv2.minMaxLoc(cv2.matchTemplate(roi,t,cv2.TM_CCOEFF_NORMED)) for t in (self.fish,cv2.flip(self.fish,1))]
        _,confidence,_,location = max(matches,key=lambda m:m[1])
        if confidence >= .70:
            obs.fish_x = x+location[0]+self.fish.shape[1]/2
        return obs


class CastReady:
    """Learn the selected bait icon; require disappearance before accepting return."""
    def __init__(self):
        self.reference = None
        self.hidden = False
        self.since = None

    def crop(self, frame, point):
        x,y = point
        if not (48 <= x < 1872 and 48 <= y < 1032):
            return None
        return cv2.cvtColor(frame[y-48:y+48,x-48:x+48],cv2.COLOR_BGR2GRAY)

    def learn(self, frame, point):
        patch = self.crop(frame,point)
        if patch is not None and patch.std() >= 12:
            self.reference = patch.copy()
        self.hidden = False
        self.since = None

    def returned(self, frame, point, now):
        patch = self.crop(frame,point)
        if self.reference is None or patch is None:
            return False
        score = float(cv2.matchTemplate(patch,self.reference,cv2.TM_CCOEFF_NORMED)[0,0])
        if score < .6:
            self.hidden = True
        if self.hidden and score >= .85:
            if self.since is None:
                self.since = now
            return now-self.since >= .8
        self.since = None
        return False


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
    """Coordinate cast, strike, steering, collection, and bounded repeat cycles."""
    detector = Detector()
    cast_ready = CastReady()
    deadline = float("inf") if p.no_time_limit else time.monotonic() + p.minutes*60
    held = None
    state = 'waiting'
    completed = 0
    last_seen = time.monotonic()
    strike_cleared = True
    catch_pressed = False
    full_since = None
    strikes = 0
    cast_sent = False
    cast_time = None
    take_since = None
    take_point = None
    close_since = None
    collected_at = None
    capture = None
    stats_start = time.monotonic()
    stats_frames = 0
    stats_processing = 0.0
    requested_period = 1.0/p.tracker_hz

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

    def click(point):
        if stop.is_set() or time.monotonic() >= deadline or not focused_game():
            return False
        if p.dry_run:
            return True
        backend.moveTo(*point)
        if stop.is_set() or time.monotonic() >= deadline or not focused_game():
            return False
        try:
            backend.mouseDown(button='left')
            stop.wait(.06)
        finally:
            previous = backend.FAILSAFE
            try:
                backend.FAILSAFE = False
                backend.mouseUp(button='left')
            finally:
                backend.FAILSAFE = previous
        return True

    try:
        if getattr(backend, '__name__', '') == 'pyautogui':
            from screen_capture import FastCapture
            capture = FastCapture()
        emit('state', 'Focus Pixel Worlds — casting after countdown' if p.auto_cast else 'Visual assist: focus Pixel Worlds and cast manually')
        if stop.wait(p.countdown):
            return
        while not stop.is_set() and time.monotonic() < deadline and (p.unlimited_cycles or completed < p.cycles):
            if not focused_game():
                release()
                take_since = close_since = None
                emit('state', 'Paused — focus Pixel Worlds')
                if stop.wait(.3):
                    break
                continue
            before = time.monotonic()
            frame = capture.grab() if capture else cv2.cvtColor(np.asarray(backend.screenshot()),cv2.COLOR_RGB2BGR)
            obs = detector.inspect(frame)
            # Drop slow captures instead of steering using an old frame.
            if time.monotonic()-before > .5 or not focused_game() or stop.is_set():
                release()
                take_since = close_since = None
                continue
            now = time.monotonic()
            stats_frames += 1
            stats_processing += now-before
            if now-stats_start >= 1:
                emit('metrics', f'{stats_frames/(now-stats_start):.1f} FPS | {1000*stats_processing/stats_frames:.1f} ms capture + detect')
                stats_start,stats_frames,stats_processing = now,0,0.0
            ready_to_recast = cast_ready.returned(frame,(p.cast_x,p.cast_y),now) if p.auto_cast else False
            if not obs.full:
                full_since = None
            elif not catch_pressed and obs.bar is not None:
                if full_since is None:
                    full_since = now
                if now-full_since >= .05:
                    release()
                    if stop.is_set() or time.monotonic() >= deadline or not focused_game():
                        continue
                    if not p.dry_run:
                        held = 'space'
                        try:
                            backend.keyDown(held)
                            stop.wait(.06)
                        finally:
                            release()
                    catch_pressed = True
                    state = 'await_catch'
                    last_seen = now
                    emit('action',('DRY ' if p.dry_run else '')+'space (full meter — catch fish)')
                    emit('state','Catch pressed — waiting for Fish Caught dialog')
                    continue
            # Collection is separate from tracking: loss of the bar is not success.
            if obs.take is not None:
                release()
                close_since = None
                if state == 'collecting':
                    if now-collected_at > 8:
                        emit('timeout','Take Fish dialog did not close — stopped without another click')
                        break
                else:
                    if take_point is None or abs(obs.take[0]-take_point[0])+abs(obs.take[1]-take_point[1]) > 12:
                        take_since = now
                    take_point = obs.take
                    if take_since is None:
                        take_since = now
                    if now-take_since >= .25 and click(obs.take):
                        emit('action',('DRY ' if p.dry_run else '')+'Take Fish click')
                        emit('state','Waiting for collection dialog to close')
                        state = 'collecting'
                        collected_at = now
                stop.wait(max(0,requested_period-(time.monotonic()-before)))
                continue
            take_since = None
            take_point = None
            if state == 'collecting':
                release()
                if obs.caught:
                    close_since = None
                    if now-collected_at > 8:
                        emit('timeout','Catch dialog still visible — stopped')
                        break
                    stop.wait(max(0,requested_period-(time.monotonic()-before)))
                    continue
                if close_since is None:
                    close_since = now
                if now-close_since >= .5:
                    completed += 1
                    emit('cycle',str(completed))
                    if not p.dry_run:
                        emit('fish',str(completed))
                    if (not p.unlimited_cycles and completed >= p.cycles) or not p.repeat:
                        break
                    emit('state','Fish dialog closed — cooldown before next cast')
                    state = 'cooldown'
                    last_seen = now
                stop.wait(max(0,requested_period-(time.monotonic()-before)))
                continue
            if state == 'cooldown':
                if now-last_seen < p.cooldown:
                    stop.wait(max(0,requested_period-(time.monotonic()-before)))
                    continue
                state = 'waiting'
                cast_sent = False
                cast_time = None
                strikes = 0
                catch_pressed = False
                full_since = None
                strike_cleared = True
                detector.last_bar = None
            if obs.caught:
                release()
                stop.wait(max(0,requested_period-(time.monotonic()-before)))
                continue
            if p.auto_cast and not cast_sent and state == 'waiting':
                # Attach to a strike/minigame already in progress without clicking.
                if obs.strike or obs.bar is not None:
                    cast_sent = True
                else:
                    if not (0 <= p.cast_x < 1920 and 0 <= p.cast_y < 1080):
                        raise ValueError('Pick a valid cast point before starting')
                    cast_ready.learn(frame,(p.cast_x,p.cast_y))
                    if not click((p.cast_x,p.cast_y)):
                        continue
                    cast_sent = True
                    cast_time = now
                    emit('action', ('DRY ' if p.dry_run else '') + f'cast click at ({p.cast_x}, {p.cast_y})')
                    emit('state', 'Waiting for STRIKE (dry run: cast manually)' if p.dry_run else 'Cast clicked — waiting for STRIKE')
                    continue
            if cast_time is not None and state == 'waiting' and now-cast_time > p.visual_timeout:
                emit('timeout', 'No strike after casting — check cast point; no repeated clicks sent')
                break
            if not obs.strike:
                strike_cleared = True
            if catch_pressed and state == 'await_catch' and obs.bar is not None:
                release()
                if now-last_seen > 12:
                    emit('timeout','Catch did not complete after Space')
                    break
                stop.wait(max(0,requested_period-(time.monotonic()-before)))
                continue
            if obs.bar is not None and obs.fish_x is not None and obs.target_x is not None:
                if state != 'tracking':
                    emit('calibration', f'Fishing track located at {obs.bar}')
                    emit('state', 'Tracking fish — A / D')
                state = 'tracking'
                last_seen = now
                key = direction(obs,p.deadband)
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
                        emit('state','Waiting for Fish Caught dialog')
                        state = 'await_catch'
                        last_seen = now
                elif state == 'await_catch':
                    if ready_to_recast and now-last_seen >= 2 and p.repeat:
                        emit('failed','No catch dialog; bait icon returned — retrying after cooldown')
                        state = 'cooldown'
                        last_seen = now
                    elif now-last_seen > 12:
                        emit('timeout','No catch dialog — stopped without collecting or recasting')
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
            stop.wait(max(0,requested_period-(time.monotonic()-before)))
    except Exception as exc:
        emit('error',f'{type(exc).__name__}: {exc}')
    finally:
        try:
            release()
        finally:
            if capture is not None:
                capture.close()
        emit('done',str(completed))
