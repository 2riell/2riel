"""macOS focus and permissions, imported only on macOS."""
def focused_game():
    from AppKit import NSWorkspace
    app=NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return False
    name=''.join((app.localizedName() or '').casefold().split())
    return 'pixelworlds' in name


def check_permissions():
    import Quartz
    import ApplicationServices
    missing=[]
    if not Quartz.CGPreflightScreenCaptureAccess():
        Quartz.CGRequestScreenCaptureAccess()
        missing.append('Screen Recording')
    if not ApplicationServices.AXIsProcessTrustedWithOptions({ApplicationServices.kAXTrustedCheckOptionPrompt:True}):
        missing.append('Accessibility')
    if missing:
        raise RuntimeError('Enable '+ ' and '.join(missing)+' for FishingLab in System Settings → Privacy & Security, then quit and reopen the app. Allow Input Monitoring too if macOS requests it for F8.')


class MacStopHotkey:
    """Poll physical F8 on Tk's main thread without keyboard-layout APIs."""
    KEYCODE_F8 = 100

    def __init__(self,root,on_press,on_error):
        import Quartz
        self.quartz=Quartz
        self.root=root
        self.on_press=on_press
        self.on_error=on_error
        self.running=False
        self.after_id=None
        self.was_down=False

    def start(self):
        import threading
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('The macOS F8 monitor must start on the main thread')
        if self.running:
            return
        self.running=True
        self.was_down=False
        self._poll()

    def _poll(self):
        self.after_id=None
        if not self.running:
            return
        try:
            down=bool(self.quartz.CGEventSourceKeyState(
                self.quartz.kCGEventSourceStateCombinedSessionState,self.KEYCODE_F8))
            if down and not self.was_down:
                self.on_press()
            self.was_down=down
        except Exception as exc:
            self.running=False
            self.on_error(f'macOS F8 monitor failed: {type(exc).__name__}: {exc}')
            return
        if self.running:
            self.after_id=self.root.after(20,self._poll)

    def stop(self):
        self.running=False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id=None
