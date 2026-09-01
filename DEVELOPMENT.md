# UniQR development notes

My working notes. The constraints and dead ends that are not obvious from
reading the code, written down so I do not rediscover them.

Windows works and is tested. macOS and Linux are written but barely run. That
is the current job.

## Ground rules

**1. Do not break Windows.** It is the only fully tested system and my daily
driver. Run the three test suites before and after any shared change.

**2. Platform code goes behind the backend interface.** `uniqr/backends/base.py`
sets the contract: `set_dpi_aware`, `virtual_screen`, `grab`, `cursor_pos`,
`copy_text`. Windows has its own backend. macOS and Linux share `portable.py`.

Nothing outside `uniqr/backends/` and the two shell modules should hold an
`if sys.platform` check. If one seems necessary elsewhere, the contract is
missing something. Extend the contract instead.

**3. Keep detection platform neutral.** `uniqr/decode.py` is pure OpenCV and
numpy. It passes the same on Windows (OpenCV 4.13) and macOS (OpenCV 5.0). Do
not put OS specific behaviour in it.

**4. Measure before fixing.** Every detection change here came from a benchmark
showing a number move. Inverted codes were at 0 percent, not "seemed flaky".
Write the failing case first.

## How to check your work

```bash
pytest
```

Or run the legacy scripts individually:

```bash
python tests/test_real_photos.py
python tests/test_conditions.py
python tests/test_stylized.py
```

```bash
python tools/diagnose.py
```

Expected: 3 of 3 real photos, 17 of 17 conditions, 8 of 8 stylised, plus selftest.
All suites exit non-zero when they fail.

To test the macOS and Linux code path without a Mac, force the backend:

```
UNIQR_BACKEND=portable python tests/test_real_photos.py
```

## Where things stand

Confirmed on macOS 14, Intel, Python 3.14.7, OpenCV 5.0.0.93:

- all three test suites pass, including the three real photos
- `python scan.py <image>` works

Still to do on macOS:

**1. Screen capture.** mss needs Screen Recording permission. Without it macOS
returns black frames instead of an error, so `backends/portable.py:probe()`
checks pixel spread to tell a blank screen from a blocked one. Confirm that
check actually fires when the permission is missing.

**2. Global hotkey.** pynput needs Input Monitoring. Both permissions attach to
the terminal app, not to Python, and only apply after that app is fully quit
and reopened. Inside a VM the hypervisor may swallow Ctrl+Alt, so
`UNIQR_HOTKEY` overrides the combination.

**3. Picker overlay.** `uniqr/overlay.py` is tkinter and should mostly port. The
coordinate maths is Windows shaped though. Expect trouble with Retina scaling,
because mss returns physical pixels while Tk geometry uses points. Also with a
negative screen origin on multi monitor setups. If the highlight boxes sit
offset from the codes, this is why.

**4. Tray icon.** Expected to fail. pystray wants the main thread on macOS and
Tk already has it. `PortableShell.start_tray()` returns False and the app
carries on with the hotkey only. The real fix is a native menu bar item through
rumps or pyobjc. Do not fight pystray for it.

**5. Linux.** X11 should work on the same portable backend. Wayland blocks both
screen capture and global hotkeys by design, and needs a portal based path that
does not exist yet.

## Things learned the hard way

**Both OpenCV detectors assume dark blocks on a light background.** An inverted
code scores 0 percent at every rotation. So every scan now runs both
polarities.

**Finding one code tells you nothing about the others.** Returning early on the
first hit is what made a three code flyer report one code.

**Fancy codes cannot even be located.** Dotted or rounded blocks defeat the
locator, so nothing further down the pipeline can help. Thresholding and then
growing the blocks rebuilds a grid it can read.

**Decoding fancy codes is knife edge.** The same code decoded at 16, 24 and
30 pixels of crop margin, but not at 33 or 40, because the CLAHE tile
boundaries shift. That is why the scanner tries a range of sizes and contrast
treatments instead of one recipe.

**Colour codes can hide in grayscale.** Navy on crimson measures 33 out of 255
once converted to grey, yet separates cleanly in the red channel alone.

## Safety rules, not up for negotiation

A decoded payload is untrusted input read off the screen.

Only `http://` and `https://` get an Open action. See `actions.can_open`. Never
pass an arbitrary payload to anything that runs it. `file://` and app links like
`ms-settings:` stay copy only. Do not widen this to make a demo look better.

Result cards and the picker are ordinary windows on purpose, not system
notifications. Do Not Disturb silently swallows notifications, which would make
a scan look broken. Keep it that way.
