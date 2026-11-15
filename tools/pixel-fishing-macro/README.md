# Pixel Worlds Fishing Lab

Local Python desktop macro for macOS and Windows. Sends configurable keyboard or mouse inputs, with timed cycles or a calibrated pixel-color bite trigger. This is an independent QA tool, not an official Pixel Worlds integration.

## Install and run

Install **Python 3.11 or newer** from python.org, including Tcl/Tk. Extract this folder first.

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

macOS Terminal:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

On macOS allow the launching Terminal/Python app in System Settings → Privacy & Security → Accessibility (input) and Screen Recording (pixel sampling). Relaunch after granting permissions. F8 may require Fn+F8 depending on keyboard settings. Screen Recording is needed only for pixel detection/sampling. Use the primary display at a fixed resolution; Retina scaling may require manually correcting sample coordinates.

## First session

1. Leave **Dry run** checked and run a short session. This simulates the sequence without touching the game.
2. Configure cast/reel controls to match your build. Supported actions: letters, digits, `space`, `enter`, `shift`, `ctrl`, `alt`, `up`, `down`, `left`, `right`, `mouse:left`, `mouse:right`. Mouse actions use the current cursor position.
3. Set hold duration, bite wait, cooldown, maximum cycles and session time limit. A completed cycle counts a cast/reel sequence, **not a verified fish catch**.
4. Uncheck Dry run, click Start, then focus your game during the countdown. For mouse mode, place the pointer over the game action target. Inputs go to the focused application; the tool does not identify or lock to the game window.
5. Stop with **F8**, the Stop button, **Escape while this app is focused**, or PyAutoGUI's screen-corner failsafe. The failsafe is checked during automation calls; F8 and Stop interrupt waits directly. Test F8 with a short live session before a longer run.

For pixel detection, use **Sample pixel in 3s** while your game's bite indicator is visible. Move the pointer onto that indicator during the countdown. Enable detection and choose a timeout that covers the expected bite delay. The sampled pixel must first leave the target color after casting and then return to it. A constantly matching pixel will time out and stop. Dry run simulates the configured bite wait and does not read the screen. Animations, UI changes, overlays, and display scaling can affect detection.

Profiles can be saved/loaded as JSON. Export CSV to inspect actions, timeouts and errors. CSV contains up to the most recent 20,000 events per app session. Timing is best effort, not a precision benchmark. The app runs one local input stream and requires the game to remain focused; it is not a multi-client server load generator. A game that ignores synthesized input needs a developer-side test hook instead.

## Validate / package

```sh
python -m unittest -v test_engine.py
```

Optional standalone build on each target OS (build macOS on macOS, Windows on Windows):

```sh
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --windowed --name FishingLab app.py
```

Output is in `dist/`. Unsigned local builds may trigger OS prompts. Dependencies must be installed in the same Python environment first. No prebuilt or signed binaries are included.

Engine tests cover cancellation, time limits, cycle bounds, input release, stale/fresh pixel signals, and configuration validation. Live game behavior and OS permissions must be tested on the target machines.
