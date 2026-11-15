"""Interruptible, bounded desktop fishing test runner."""
from dataclasses import dataclass, asdict
import time

@dataclass
class Profile:
    cast: str = 'space'
    reel: str = 'space'
    hold: float = 0.08
    countdown: float = 5
    bite_wait: float = 4
    cooldown: float = 2
    cycles: int = 30
    minutes: float = 10
    dry_run: bool = True
    pixel: bool = False
    x: int = 0
    y: int = 0
    color: str = '#ffffff'
    tolerance: int = 25

    def validate(self):
        for field, low, high in [('hold', .02, 2), ('countdown', 1, 60), ('bite_wait', .1, 120), ('cooldown', .1, 120), ('minutes', .01, 120)]:
            value = float(getattr(self, field))
            if not low <= value <= high:
                raise ValueError(f'{field} must be between {low} and {high}')
        if not 1 <= self.cycles <= 10000:
            raise ValueError('Cycles must be 1–10000')
        if not 0 <= self.tolerance <= 255:
            raise ValueError('Tolerance must be 0–255')
        if len(self.color) != 7 or not self.color.startswith('#'):
            raise ValueError('Color must be #RRGGBB')
        int(self.color[1:], 16)
        allowed = {'space', 'enter', 'shift', 'ctrl', 'alt', 'up', 'down', 'left', 'right', 'mouse:left', 'mouse:right'}
        for action in (self.cast, self.reel):
            if action not in allowed and not (len(action) == 1 and action.isascii() and action.isalnum()):
                raise ValueError('Action must be a letter, number, space, enter, shift, ctrl, alt, arrow, or mouse:left/right')
        return self

    def dict(self):
        return asdict(self)


def matches(rgb, hex_color, tolerance):
    target = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
    return all(abs(int(a)-b) <= tolerance for a, b in zip(rgb[:3], target))


def run(profile, stop, emit, backend=None):
    p = profile.validate()
    started = time.monotonic()
    deadline = started + p.minutes * 60

    def wait(seconds):
        remaining = max(0, deadline - time.monotonic())
        return not stop.wait(min(seconds, remaining)) and time.monotonic() < deadline

    def action(name):
        emit('action', ('DRY ' if p.dry_run else '') + name)
        if p.dry_run:
            return wait(p.hold)
        mouse = name.startswith('mouse:')
        key = name.split(':')[-1]
        try:
            if mouse:
                backend.mouseDown(button=key)
            else:
                backend.keyDown(key)
            return wait(p.hold)
        finally:
            if mouse:
                backend.mouseUp(button=key)
            else:
                backend.keyUp(key)

    completed = 0
    try:
        emit('state', f'Focus game — starting in {p.countdown:g}s')
        if not wait(p.countdown):
            return
        for cycle in range(1, p.cycles + 1):
            if stop.is_set() or time.monotonic() >= deadline:
                break
            emit('state', f'Cycle {cycle}: casting')
            if not action(p.cast):
                break
            emit('state', 'Waiting for bite')
            if p.pixel and not p.dry_run:
                bite_deadline = min(deadline, time.monotonic() + p.bite_wait)
                # Require the signal to clear before accepting a fresh bite.
                armed = False
                detected = False
                while time.monotonic() < bite_deadline and not stop.is_set():
                    hit = matches(backend.pixel(p.x, p.y), p.color, p.tolerance)
                    if not hit:
                        armed = True
                    if armed and hit:
                        detected = True
                        break
                    if not wait(.08):
                        break
                if not detected:
                    emit('timeout', 'No fresh bite signal; stopped for inspection')
                    break
            elif not wait(p.bite_wait):
                break
            if stop.is_set() or time.monotonic() >= deadline:
                break
            emit('state', f'Cycle {cycle}: reeling')
            if not action(p.reel):
                break
            completed += 1
            emit('cycle', str(completed))
            if not wait(p.cooldown):
                break
    except Exception as exc:
        emit('error', f'{type(exc).__name__}: {exc}')
    finally:
        emit('done', str(completed))
