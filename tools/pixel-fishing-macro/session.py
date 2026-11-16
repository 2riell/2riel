"""Session limits and explicit termination reporting, independent of desktop input."""
import threading
import time

class StopSignal(threading.Event):
    def __init__(self):
        super().__init__()
        self.reason=None
        self.reason_lock=threading.Lock()

    def set(self,reason='Stop signal received'):
        with self.reason_lock:
            if not self.is_set():
                self.reason=reason
                super().set()

    def clear(self):
        with self.reason_lock:
            self.reason=None
            super().clear()

class SessionReporter:
    def __init__(self,profile,stop,emit):
        self.profile,self.stop,self.emit=profile,stop,emit
        self.started=time.monotonic()
        self.failure=None
        self.emit('session',f'Start: unlimited cycles={profile.unlimited_cycles}, no time limit={profile.no_time_limit}, repeat={profile.repeat}, cycle limit={profile.cycles}, minutes={profile.minutes}')

    def deadline(self):
        return float('inf') if self.profile.no_time_limit else self.started+self.profile.minutes*60

    def __call__(self,kind,message):
        if kind in ('timeout','error'):
            self.failure=f'{kind}: {message}'
        if kind=='done':
            if self.failure:
                reason=self.failure
            elif self.stop.is_set():
                reason=getattr(self.stop,'reason',None) or 'Stop signal received'
            elif time.monotonic()>=self.deadline():
                reason='Session time limit reached'
            elif not self.profile.unlimited_cycles and int(message)>=self.profile.cycles:
                reason='Cycle limit reached'
            elif self.profile.visual and not self.profile.repeat and int(message)>0:
                reason='Collect and repeat was disabled'
            else:
                reason='Unexpected runner exit — export the session log'
            self.emit('stop_reason',reason)
        self.emit(kind,message)
