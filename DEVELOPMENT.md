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

## The benchmark lab

`benchmarks/` scores the scanner on thousands of generated codes. It is the
tool for rule 4 above: do not fix what you have not measured.

```bash
python -m benchmarks.run                  # ~1,000 codes, a few minutes
python -m benchmarks.run --seed 7         # a different, reproducible set
python -m benchmarks.run --formats qr --tags rotate,blur
python -m benchmarks.search               # what would have read the misses?
python -m benchmarks.run --replay         # re-scan saved misses after a change
```

Each case is a code with known contents, drawn in some style and size, then
damaged. A case is a handful of numbers, so the same seed rebuilds the same
pixels and any miss can be reproduced from its metadata.

**The loop for improving the scanner:**

1. Run the benchmark. Read the misses, not the percentage.
2. Run `benchmarks.search`. It tries hundreds of treatments against every miss
   and lists what recovers each one.
3. Put a recipe that helps several misses into `uniqr/decode.py`.
4. `--replay` to confirm those misses now decode.
5. Run a seed you have never run before. A recipe that fixes the misses it was
   found on and nothing else is overfitting.

**Rules the numbers depend on:**

- **Report a seed you did not tune on.** Seeds 1 to 4 were used to find and
  check the fixes, so seeds 5, 6 and 7 are the ones quoted. A seed stops being
  clean the moment you read its misses. Use a new one.
- **A miss is not always the scanner's fault.** Damage can destroy a code. Each
  miss is retried with the same code enlarged to 12 pixels per module, read by
  UniQR and by zxing directly. If that fails too it is counted as
  *unreadable*, not as a miss. Without this the early results blamed UniQR for
  damage no reader could survive.
- **Wrong answers are tracked on their own.** Returning the wrong text is worse
  than returning nothing. One showed up: a PDF417 under three kinds of damage
  came back as 51 characters of garbage that the reader called valid, and the
  same code read under other treatments gave different garbage each time. The
  fix is `Scanner._confirm`, which makes every non-QR code agree with a second
  read before it is believed. The case is pinned in `tests/test_formats.py`.
  If a wrong answer ever appears again, that is the first thing to fix.
- **Images with no code in them are part of the test.** Adding a format raises
  the chance of seeing a code that is not there. Blank pages, noise, text,
  checkerboards and linear barcodes must all come back empty.
- **Each change earns its place.** Two changes made on a hunch (a blur and a
  second threshold in the patch reader) fixed nothing when each was switched
  off in turn, and were removed. Check by turning a change off and replaying.
- **Cost matters.** The scan runs on a hotkey press. `uniqr/decode.py` keeps
  the extra formats to one pass per scan, and the expensive recoveries to
  frames small enough to afford them.

`benchmarks/failures/` holds saved misses and is ignored by git. Do not commit
screenshots of a real screen: they hold whatever was open at the time.

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
