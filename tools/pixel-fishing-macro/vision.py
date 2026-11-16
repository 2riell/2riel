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
    item: bool = False
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
        self.take_mask = np.full(self.take.shape,255,dtype=np.uint8)
        self.take_mask[10:60,15:221] = 0

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
        # Ingredient results share the dialog shell but use different title/button text.
        # Match the button surround, then require the cyan panel on both sides.
        lower=frame[250:1040].astype(np.int16)
        bb,gg,rr=cv2.split(lower)
        lime=((gg>130)&(gg>bb*1.4)&(rr>70)).astype('uint8')*255
        contours,_=cv2.findContours(lime,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            bx,by,bw,bh=cv2.boundingRect(contour);by+=250
            if not (190 <= bw <= 250 and 40 <= bh <= 80):
                continue
            left,top=max(0,bx-20),max(0,by-20)
            roi=gray[top:by+bh+20,left:bx+bw+20]
            if roi.shape[0]<self.take.shape[0] or roi.shape[1]<self.take.shape[1]:
                continue
            result=cv2.matchTemplate(roi,self.take,cv2.TM_CCORR_NORMED,mask=self.take_mask)
            result=np.nan_to_num(result,nan=-1,posinf=-1,neginf=-1)
            _,confidence,_,point=cv2.minMaxLoc(result)
            cx=left+point[0]+self.take.shape[1]//2;cy=top+point[1]+self.take.shape[0]//2
            if confidence >= .95 and self.item_shell(frame,cx,cy):
                return Observation(item=True,caught=True,take=(cx,cy))
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

    def item_shell(self,frame,cx,cy):
        # Ingredients can use a shorter/narrower panel. Validate paired cyan
        # borders immediately above the button, rather than a fish-sized panel.
        if not (410 <= cx < 1510 and 200 <= cy < 1040):
            return False
        patch=frame[cy-150:cy-50,cx-400:cx+401].astype(np.int16)
        b,g,r=cv2.split(patch)
        cyan=(b>120)&(g>120)&(r<g*.8)
        columns=cyan.mean(axis=0)>.65
        left=np.flatnonzero(columns[:221])-400
        right=np.flatnonzero(columns[580:])+180
        paired=any(np.count_nonzero(np.abs(right+x)<=12)>=4 for x in left)
        button=frame[cy-22:cy+22,cx-95:cx+95].astype(np.int16)
        b,g,r=cv2.split(button)
        return paired and ((g>130)&(g>b*1.4)&(r>70)).mean()>.45

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
        # A horizontal border separates the target from nearby fish pixels.
        # Do not abandon fish detection when this independent target search fails.
        horizontal=cv2.morphologyEx(band,cv2.MORPH_OPEN,np.ones((1,45),np.uint8))
        columns=np.flatnonzero((horizontal>0).sum(axis=0)>=3)
        groups=np.split(columns,np.where(np.diff(columns)>3)[0]+1) if len(columns) else []
        groups=[a for a in groups if 65<=a[-1]-a[0]<=160]
        if len(groups)==1:
            target=groups[0]
            obs.target_x=left+(target[0]+target[-1])/2
            obs.target_width=float(target[-1]-target[0])
        # Search the full track plus edge padding, independent of the target.
        fish_left,fish_right=max(0,x-40),min(1920,x+w+40)
        fish_top,fish_bottom=max(0,y-12),min(1080,y+h+12)
        fish_frame=frame[fish_top:fish_bottom,fish_left:fish_right]
        roi=tracking_mask(fish_frame)
        matches = [cv2.minMaxLoc(cv2.matchTemplate(roi,t,cv2.TM_CCOEFF_NORMED)) for t in (self.fish,cv2.flip(self.fish,1))]
        _,confidence,_,location = max(matches,key=lambda m:m[1])
        if confidence >= .70:
            obs.fish_x = fish_left+location[0]+self.fish.shape[1]/2
        if obs.fish_x is None:
            gray = cv2.cvtColor(fish_frame,cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray,40,100)
            candidates = [cv2.minMaxLoc(cv2.matchTemplate(edges,cv2.Canny(t,40,100),cv2.TM_CCORR_NORMED)) for t in (self.fish,cv2.flip(self.fish,1))]
            _,score,_,point = max(candidates,key=lambda m:m[1])
            if score >= .55:
                obs.fish_x = fish_left+point[0]+self.fish.shape[1]/2
        return obs


class MotionSteering:
    """Bridge brief recognition gaps using independently sampled positions."""
    def __init__(self):
        self.samples={}
        self.bar=None
        self.chase_direction=None
        self.last_command=None

    def reset(self):
        self.samples.clear()
        self.bar=None
        self.chase_direction=None
        self.last_command=None

    def key(self,obs,now,deadband,chase_lost=False):
        if obs.bar is None:
            self.reset()
            return None
        if self.bar is not None and any(abs(a-b)>limit for a,b,limit in zip(self.bar,obs.bar,(8,8,16,8))):
            self.reset()
        self.bar=obs.bar
        for name,value in (('fish',obs.fish_x),('target',obs.target_x)):
            if value is None:
                continue
            old=self.samples.get(name)
            velocity=0.
            if old is not None and 0<now-old[1]<=.2:
                velocity=float(np.clip((value-old[0])/(now-old[1]),-1800,1800))
            self.samples[name]=(value,now,velocity)
        if obs.fish_x is not None:
            target=self.samples.get('target')
            # The current fish side overrides its old heading immediately.
            # Near the center, its measured velocity supplies the escape direction.
            side=direction(Observation(fish_x=obs.fish_x,target_x=target[0]),deadband) if target is not None and now-target[1]<=.2 else None
            velocity=self.samples['fish'][2]
            if target is not None and now-target[1]<=.2:
                self.chase_direction=side or ('d' if velocity>0 else 'a' if velocity<0 else None)
        elif chase_lost and self.chase_direction is not None:
            # Hold continuously until a fresh fish observation or the track ends.
            self.last_command=self.chase_direction
            return self.last_command
        positions={}
        for name in ('fish','target'):
            sample=self.samples.get(name)
            if sample is None or now-sample[1]>.2:
                if chase_lost and name=='target':
                    return self.last_command
                self.last_command=None
                return None
            value,seen,velocity=sample
            # Extrapolate only while the track remains visible, at most 200 ms.
            positions[name]=float(np.clip(value+velocity*(now-seen),obs.bar[0],obs.bar[0]+obs.bar[2]))
        error=positions['fish']-positions['target']
        # Hysteresis avoids repeatedly releasing/repressing at the tolerance edge.
        # Clear alignment still releases; a measured opposite-side error reverses now.
        key=direction(Observation(fish_x=positions['fish'],target_x=positions['target']),deadband)
        if key is None and self.last_command=='d' and error>deadband*.5:
            key='d'
        elif key is None and self.last_command=='a' and error < -deadband*.5:
            key='a'
        self.last_command=key
        return key


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
    """Foreground gate, checked again immediately before each input."""
    if sys.platform == 'darwin':
        from mac_support import focused_game as mac_focused
        return mac_focused()
    if sys.platform != 'win32':
        raise RuntimeError('Visual assist supports Windows and macOS.')
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
    from session import SessionReporter
    emit = SessionReporter(p,stop,emit)
    deadline = emit.deadline
    held = None
    state = 'waiting'
    completed = 0
    last_seen = time.monotonic()
    strike_cleared = True
    catch_pressed = False
    full_since = None
    motion = MotionSteering()
    strikes = 0
    cast_sent = False
    cast_time = None
    take_since = None
    take_point = None
    close_since = None
    collected_at = None
    collected_item = False
    result_notice = False
    fish_count = 0
    item_count = 0
    capture = None
    stats_start = time.monotonic()
    stats_frames = 0
    stats_processing = 0.0
    focus_paused = False
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
        if stop.is_set() or time.monotonic() >= deadline() or not focused_game():
            return False
        if p.dry_run:
            return True
        backend.moveTo(*point)
        if stop.is_set() or time.monotonic() >= deadline() or not focused_game():
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
        while not stop.is_set() and time.monotonic() < deadline() and (p.unlimited_cycles or completed < p.cycles):
            if not focused_game():
                release()
                motion.reset()
                take_since = close_since = None
                if not focus_paused:
                    emit('state', 'Paused — focus Pixel Worlds (session stays active)')
                    focus_paused = True
                if stop.wait(.3):
                    break
                continue
            if focus_paused:
                emit('state','Game focus restored — resuming')
                focus_paused = False
            before = time.monotonic()
            frame = capture.grab() if capture else cv2.cvtColor(np.asarray(backend.screenshot()),cv2.COLOR_RGB2BGR)
            obs = detector.inspect(frame)
            # Drop slow captures instead of steering using an old frame.
            if time.monotonic()-before > .5 or not focused_game() or stop.is_set():
                release()
                motion.reset()
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
                    if stop.is_set() or time.monotonic() >= deadline() or not focused_game():
                        continue
                    if not p.dry_run:
                        held = 'space'
                        try:
                            backend.keyDown(held)
                            stop.wait(.06)
                        finally:
                            release()
                    motion.reset()
                    catch_pressed = True
                    state = 'await_catch'
                    last_seen = now
                    emit('action',('DRY ' if p.dry_run else '')+'space (full meter — catch fish)')
                    emit('state','Catch pressed — waiting for Fish Caught dialog')
                    continue
            # Collection is separate from tracking: loss of the bar is not success.
            if obs.take is not None:
                release()
                motion.reset()
                close_since = None
                if state == 'collecting':
                    if now-collected_at > 8:
                        emit('timeout','Collection dialog did not close — stopped without another click')
                        break
                else:
                    if take_point is None or abs(obs.take[0]-take_point[0])+abs(obs.take[1]-take_point[1]) > 12:
                        take_since = now
                    take_point = obs.take
                    if take_since is None:
                        take_since = now
                    if now-take_since >= .25 and click(obs.take):
                        collected_item = obs.item
                        emit('action',('DRY ' if p.dry_run else '')+('Take Item click' if obs.item else 'Take Fish click'))
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
                        if collected_item:
                            item_count += 1
                            emit('item',str(item_count))
                        else:
                            fish_count += 1
                            emit('fish',str(fish_count))
                    if (not p.unlimited_cycles and completed >= p.cycles) or not p.repeat:
                        break
                    emit('state','Item collected — cooldown before next cast')
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
                result_notice = False
                full_since = None
                motion.reset()
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
            if (not p.wait_for_strike and cast_time is not None and state == 'waiting'
                    and not obs.strike and obs.bar is None and now-cast_time > p.visual_timeout):
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
            if obs.bar is not None and not catch_pressed:
                complete=obs.fish_x is not None and obs.target_x is not None
                next_state='tracking' if complete else 'reacquiring'
                if state != next_state:
                    if complete:
                        emit('state','Tracking fish — A / D')
                    else:
                        emit('state','Reacquiring — chasing last known side' if p.chase_lost_fish else 'Reacquiring — bridging brief detection gaps')
                state=next_state
                last_seen=now
                key=motion.key(obs,now,p.deadband,p.chase_lost_fish)
                if key != held:
                    release()
                    if key and not p.dry_run and focused_game() and not stop.is_set():
                        held=key
                        backend.keyDown(key)
                    emit('steer',('DRY ' if p.dry_run else '')+(key or 'release'))
            else:
                release()
                motion.reset()
                if state in ('tracking','reacquiring'):
                    if now-last_seen > .6:
                        emit('state','Waiting for Fish Caught dialog')
                        state = 'await_catch'
                        last_seen = now
                elif state == 'await_catch':
                    if ready_to_recast and now-last_seen >= 2 and p.repeat:
                        emit('failed','No catch dialog; bait icon returned — retrying after cooldown')
                        state = 'cooldown'
                        last_seen = now
                    elif now-last_seen > 12 and not result_notice:
                        emit('state','Still waiting for Take Fish / Take Item — Stop or F8 to cancel')
                        result_notice = True
                elif obs.strike and strike_cleared:
                    if strikes:
                        emit('timeout','Strike repeated without a track — stopped for inspection')
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
                elif state == 'struck':
                    if ready_to_recast and now-last_seen >= 2 and p.repeat:
                        emit('failed','Bait icon returned after strike — retrying after cooldown')
                        state = 'cooldown'
                        last_seen = now
                    elif now-last_seen > 12 and not result_notice:
                        emit('state','Still waiting for fishing bar or Take Item — Stop or F8 to cancel')
                        result_notice = True
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
