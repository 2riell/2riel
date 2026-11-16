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
