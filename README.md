# UniQR

Read any QR code on your screen with a keypress. No phone, no screenshots.

Press **Win+Shift+Q** and UniQR decodes every QR code visible anywhere on your
screen - a webpage, a PDF, a Zoom call, a paused video, a photo of a flyer.
One code gets copied straight to your clipboard. Several, and you get a picker
showing you where each one is so you choose.

## Running it

Needs Python 3.11 or newer.

```
pip install -r requirements.txt
python app.py
```

It lives in the system tray. Right-click the tray icon to exit.

On Windows the hotkey is `Win+Shift+Q`, falling back to `Ctrl+Alt+Q` then
`Ctrl+Shift+9` if another app already owns it. On macOS and Linux it is
`Ctrl+Alt+Q`. UniQR prints which one it got on startup.

## Platform support

Detection is plain OpenCV and identical everywhere. Only the four things that
touch the OS differ, and they live behind one interface in `uniqr/backends/`.

| | Windows | macOS | Linux |
|---|---|---|---|
| Detection | ✅ | ✅ | ✅ |
| Scan an image file | ✅ | ✅ | ✅ |
| Live screen capture | ✅ GDI BitBlt | ⚠️ mss, needs permission | ⚠️ mss, X11 |
| Global hotkey | ✅ `RegisterHotKey` | ⚠️ pynput, needs permission | ⚠️ pynput |
| Tray icon | ✅ | ❌ see below | ⚠️ pystray |
| Picker + result card | ✅ | ⚠️ untested | ⚠️ untested |

✅ tested · ⚠️ implemented, not yet run on that OS · ❌ known limitation

**Honest status:** the Windows path is tested. The macOS and Linux path is
written and its machinery is exercised on Windows via
`UNIQR_BACKEND=portable`, which runs the same mss / pynput / pystray / tkinter
code - but it has not been run on an actual Mac or Linux box yet. Expect to
fix things.

### macOS notes

Two permissions must be granted by hand in **System Settings → Privacy &
Security**, and neither failure raises an error - they just silently do
nothing:

- **Screen Recording** - without it capture returns uniformly black frames.
  UniQR checks for this on startup and says so rather than reporting "no codes
  found".
- **Input Monitoring** - without it the hotkey never fires.

The tray icon is expected **not** to work: pystray needs the main thread on
macOS, and Tk already owns it (Tk has the same requirement). The hotkey is the
primary interface, so UniQR reports the missing tray and carries on. A proper
fix means a native menu-bar item via `rumps`/pyobjc.

Also note `pynput` observes keys rather than reserving them, so unlike Win32 it
cannot detect that a shortcut is already taken - if another app owns it, both
will fire.

### Linux notes

Works under X11. Pure Wayland blocks both screen capture and global key
grabbing by design; that needs a portal-based capture path, which is not
written yet.

### Forcing a backend

```
UNIQR_BACKEND=portable python app.py    # macOS/Linux path, on any OS
UNIQR_BACKEND=windows  python app.py    # native path
```

## Using it

| Situation | What happens |
|---|---|
| One code on screen | Copied to clipboard, small card appears with an **Open** button |
| Several codes | Screen dims, each code lit up and numbered - hover, click, or press 1-9 |
| No code found | Brief "nothing found" card near the cursor |
| Not a web link | Copy only, no Open button (see Safety) |

The card and the picker are ordinary windows, not system notifications, so
they show up even with Do Not Disturb on.

## Scanning an image file instead

```
python scan.py photo.png
python scan.py photo.png --exhaustive   # slower, tries much harder
python scan.py --selftest
```

## Safety

A QR code is untrusted input - it is a stranger's writing that you are
pointing your computer at. UniQR will only **Open** plain `http://` and
`https://` links. Everything else (Wi-Fi credentials, contact cards,
`file://`, app schemes like `ms-settings:`) is copy-only, so you read it and
decide yourself.

Nothing is captured until you press the hotkey. There is no background
scanning, no polling, no history file, and nothing leaves your machine.

## What it can read

Beyond ordinary codes, the scanner handles the awkward real-world cases:

- Inverted / dark-mode codes (light modules on a dark background)
- Rotation at any angle, and perspective from a photographed page
- Several codes in one frame, at different sizes
- Stylised marketing codes - rounded or dotted modules, centre logos
- Colour codes on colour backgrounds, where grey-scale contrast nearly vanishes
- Small codes, down to roughly 45 px

Tested against real photographs in `tests/`:

```
python tests\test_real_photos.py
```

## How it works

```
Win+Shift+Q
    -> capture every monitor (GDI BitBlt, DPI-aware)
    -> locate and decode (OpenCV, both detectors, both polarities)
    -> retry harder: tiles, upscaling, CLAHE contrast, channel separation
    -> one code: copy + card   |   several: picker overlay
```

Detection is deliberately layered cheapest-first. A plain code on a clean
screen resolves in about 140 ms; the full fallback ladder only runs when the
cheap passes come back empty, and costs about 900 ms.
