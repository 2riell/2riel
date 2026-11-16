# Pixel Worlds Fishing Lab

Local Python desktop macro for macOS and Windows. Sends configurable keyboard or mouse inputs, with timed cycles or a calibrated pixel-color bite trigger. This is an independent QA tool, not an official Pixel Worlds integration.

## Retry after a missed fish

With automatic casting and repeat enabled, the app learns the image around your saved bait point before casting. If tracking ends without a catch dialog, it waits for that image to disappear and then return steadily, waits the cooldown, and casts again. Failed rounds are logged and do not increase Fish collected. Time limits, F8 and normal timeout stops remain active. If the bait point moves, the image cannot be learned (for example, the session starts during a minigame), or the icon does not return, it stops instead of guessing.

## Ingredients / Take Item

Collection dialogs can appear after STRIKE without a tracking minigame. The app now accepts the shared cyan result panel and green collection-button surround even when the title and button text differ from Fish Caught/Take Fish. It clicks once, waits for the result to close, and follows the normal cooldown/recast flow. The post-strike wait now allows 12 seconds for either a track or result dialog.

The UI reports **Fish** and **Items** separately. Exact fish-dialog recognition increments Fish; the shared result-shell path increments Items. Counts represent observed collection dialogs, not an inventory audit. The item path was checked with a simulated no-bar result flow and an edited recorded fish dialog with its text removed; an actual ingredient screenshot/live game has not been verified. If the ingredient dialog uses a different layout, it may still require tuning.

## Long waits for a bite

**Wait for STRIKE without a bite timeout** is enabled by default in Advanced, including when loading profiles created before this option existed. The app keeps watching after a long wait and presses Space when STRIKE appears. The numeric Strike timeout is used only when this option is unchecked; even then, a visible STRIKE takes priority over that timeout. The overall session limit still applies unless No time limit is enabled. Stop/F8 and the post-strike/catch checks remain active.

## Running without limits

**No time limit** is enabled by default for new app sessions. Enable **Unlimited cycles** and **Take fish and repeat** as well to keep fishing until Stop/F8 or a detection/collection error. The numeric time and cycle fields are ignored while their respective unlimited options are enabled. Older saved profiles keep their previous time limit until No time limit is enabled and saved. The elapsed timer still runs; bite and collection timeouts remain recovery/error checks.

## Session counters and unlimited cycles

Enable **Unlimited cycles** in Simple to ignore the numeric cycle limit. Keep **Take fish and repeat** enabled for continuous visual fishing. The session time limit applies only when No time limit is off. Timeout stops, Stop and F8 still apply.

**Fish collected** increments after the live visual mode clicks Take Fish and observes the catch dialog closing. It is an observed collection count, not an inventory audit. Dry runs and timed/pixel sequences do not increment it. **Elapsed** shows HH:MM:SS since Start, including countdown and focus pauses, freezes when the session ends, and resets with the fish counter on the next Start. Unlimited mode is saved with profiles.

## Reacquiring fast fish

When the fishing track remains visible but the fish is lost, the app stays in Reacquiring and searches the full track instead of transitioning to collection timeout. It briefly steers toward the last known fish position (at most 0.25 seconds, only with a fresh target position), then releases A/D until recognition recovers. Shape matching supplements color matching when fish graphics change. Normal catch detection, focus gating and F8 remain active. This is tested with a simulated dropout exceeding 12 seconds; live behavior still depends on the displayed graphics.

## Simple and Advanced settings

The redesigned dark window opens on **Simple**: cast position picker, cycle/time limits, Dry run, automatic casting, and repeat. **Advanced** contains tracker tuning, timeouts, timed/pixel controls, and **Window opacity (85–100%)**. Opacity is optional and defaults to fully opaque; it makes the entire window translucent rather than adding a blur effect. Settings persist in saved profiles. New Windows sessions default to visual mode; older profiles preserve their selected mode.

The tracker now targets **60 Hz**, adjustable from **15 to 120 Hz** in Advanced. The status card shows measured FPS and capture/detection time. Actual refresh depends on hardware, screen capture and game rendering. MSS replaces the previous screenshot method, unnecessary input pauses are removed in visual mode, and the detector searches only the fishing track after it has located it. When the track disappears, it resumes searching for strike/catch dialogs.

Recognition now accepts green, red and yellow fish/target graphics across the entire track, including large distances between the fish and target. Center tolerance defaults to **8 pixels**, replacing the earlier roughly 21-pixel neutral zone. A/D stays held until the target reaches that zone or tracking/focus is lost. This changes reaction latency, not the game's maximum movement speed; use the actual FPS display to diagnose slow capture.

Offline benchmark on 45 recorded tracking frames: median detection processing **84.15 ms before → 2.39 ms after**, with 42/45 successful fish detections in both runs. These figures exclude screen capture, input delivery, and the game, and do not establish live catch performance.

## Visual assist (experimental, Windows)

Enable **Visual assist** and **Automatically left-click the saved cast point**. Click **Pick bait position**, then click either bait icon through the translucent selection overlay. The overlay captures the click and saves X/Y; it does not forward the cast click to the game. Escape, F8 or right-click cancels. Alternatively type Cast click X/Y manually. Use **Save profile** to keep the point for later sessions.

Keep **Dry run** enabled for an initial check. Click Start and focus Pixel Worlds during the countdown. The app logs its planned cast click without moving or clicking the mouse; cast manually to test recognition in this mode. For automatic casting, uncheck Dry run. The app left-clicks the saved point once, waits for STRIKE, presses **Space**, and uses **A/D** to keep the target aligned with the fish. F8 stops the session. The cast key field applies only to timed mode.

Use the primary display at **1920×1080 and maximum zoom**. The Windows foreground title must contain “Pixel Worlds”. Re-pick the point if the game window, camera, zoom, or interface moves. Coordinates are absolute screen pixels, not relative to the game window. No bait-icon recognition is performed: the user-selected point must be over a visible bait icon before starting. If a strike or fishing track is already visible, the app joins that round without clicking.

Enable **Collect fish and repeat** to run the full cycle: cast → Space at STRIKE → A/D tracking → Space at full progress → wait for the Fish Caught dialog → click Take Fish → confirm the dialog closes → cooldown → cast again. Disable it to collect once and stop. Maximum cycles and session time limit bound the loop. When all 21 segments of the lower progress meter are filled, the app releases A/D and presses Space once to catch the fish. It then waits for Fish Caught and clicks Take Fish. The Space latch resets for each new round; it does not spam Space while the full meter remains visible. The app releases A/D when the track disappears, waits up to 12 seconds for the catch dialog, and clicks only after recognizing both its title and Take Fish button. It clicks Take Fish once, waits up to 8 seconds for the dialog to close, and stops on a timeout. A cycle counts a recognized collection dialog followed by its disappearance, not an independent inventory check. The strike timeout defaults to 60 seconds; a missed or ineffective cast stops at that timeout without repeated clicks. The overall session time limit still applies. Uncheck automatic casting to cast manually. macOS retains the previous timed/pixel modes; visual assist supports Windows only.

Validation: 28 automated tests pass, including cast coordinates, one-click behavior, timeout, dry run, focus loss, input release, title/button recognition, repeat cycles, collection timeout, and cycle limits. Additional tests cover distant fish at both ends of the track, red/yellow graphics, center tolerance and tracker settings. Offline replay detected Take Fish in 7 sampled frames of the supplied recording, with no detections outside the catch dialog. Offline recognition was checked on the supplied recorded round, not live gameplay. Live casting and steering still need a supervised trial on your computer.

## Windows app download

Open the repository's **Actions → Fishing Lab Windows EXE**, select the latest successful run, then download **FishingLab-Windows-x64** under **Artifacts** (sign in to GitHub if prompted). Extract the ZIP and double-click **FishingLab.exe**. Python is bundled; no separate Python installation is needed. The unsigned executable targets Windows 10/11 x64 and may prompt Windows SmartScreen.

To build locally on Windows, install Python 3.12 and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

The build runs the engine tests, creates a single executable, and tests packaged GUI startup without sending game input. Find it in `dist/FishingLab.exe`.

## Install and run from source

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

Output is in `dist/`. Unsigned local builds may trigger OS prompts. Dependencies must be installed in the same Python environment first. Windows builds are available as GitHub Actions artifacts; binaries are unsigned.

Engine tests cover cancellation, time limits, cycle bounds, input release, stale/fresh pixel signals, and configuration validation. Live game behavior and OS permissions must be tested on the target machines.
