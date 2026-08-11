# UniQR — development notes

Press a hotkey, decode every QR code on screen, act on it. Windows works and is
tested. macOS and Linux are written but barely exercised — that is the current
work.

These are my working notes: the constraints and dead ends that are not obvious
from reading the code, kept so I do not rediscover them.

## Ground rules

**Do not break Windows.** It is the only fully tested platform and my daily
driver. Before touching anything shared, run the three suites below; they must
stay green on both platforms.

**Platform code goes behind the backend interface.** `uniqr/backends/base.py`
defines the contract: `set_dpi_aware`, `virtual_screen`, `grab`, `cursor_pos`,
`copy_text`. Windows has a native backend; macOS and Linux share `portable.py`.
Nothing outside `uniqr/backends/` and the two shell modules should contain an
`if sys.platform` check. If you need one elsewhere, that is a sign the contract
is missing something — extend the contract instead.

**Detection is platform-neutral and stays that way.** `uniqr/decode.py` is pure
OpenCV/numpy and passes identically on Windows (OpenCV 4.13) and macOS
(OpenCV 5.0). Do not add OS-specific behaviour to it.

**Measure before fixing.** Every detection change in this project came from a
benchmark that showed a number moving. Inverted codes were at 0%, not "seemed
flaky". If you are about to fix detection, write the failing case first.

## Verify with

```
python tests/test_real_photos.py     # 3 real photos, must be 3/3
python tests/test_conditions.py      # 17 synthetic distortions, must be 17/17
python tests/test_stylized.py        # 8 colour/stylised cases, must be 8/8
python tools/diagnose.py             # environment + permissions report
```

All three return non-zero on failure, so they chain with `&&`.

`UNIQR_BACKEND=portable` forces the macOS/Linux code path on any OS, including
Windows. Use it to check portable-backend changes without a Mac.

## Where things stand

Confirmed working on macOS 14, Intel, Python 3.14.7, OpenCV 5.0.0.93:

- all three test suites, including the three real photographs
- `python scan.py <image>` for file scanning

Not yet verified on macOS — this is the job:

1. **Screen capture.** mss needs Screen Recording permission. Without it macOS
   returns uniformly black frames rather than an error, so
   `backends/portable.py:probe()` checks pixel spread to tell blank from
   blocked. Confirm the check actually fires when permission is absent.
2. **Global hotkey.** pynput needs Input Monitoring. Both permissions attach to
   the *terminal app*, not to Python, and only take effect after that app is
   fully quit and relaunched. In a VM the hypervisor may swallow Ctrl+Alt
   entirely — `UNIQR_HOTKEY` overrides the combination in pynput syntax.
3. **Picker overlay.** `uniqr/overlay.py` is tkinter and should mostly port,
   but the coordinate assumptions are Windows-shaped. Expect trouble with
   Retina backing scale (mss returns physical pixels; Tk geometry is in points)
   and with a negative virtual-screen origin on multi-monitor setups. If the
   highlight boxes are offset from the codes, that is this.
4. **Tray icon.** Expected to fail. pystray needs the main thread on macOS and
   Tk already owns it. `PortableShell.start_tray()` returns False and the app
   continues hotkey-only. A real fix is a native menu-bar item via rumps or
   pyobjc — do not fight pystray for it.
5. **Linux.** X11 should work through the same portable backend. Pure Wayland
   blocks both screen capture and global key grabbing by design and needs a
   portal-based path that does not exist yet.

## Things already learned the hard way

- Both OpenCV detectors assume dark modules on a light background. An inverted
  code scores 0% at every rotation, so every scan runs both polarities.
- Finding one code says nothing about whether others exist. An early return on
  the first hit is what made a three-code flyer report one code.
- Stylised codes — dotted or rounded modules — cannot even be *located*, so
  no downstream cleverness helps. Thresholding and growing the modules
  reconstructs a decodable grid.
- Decoding stylised codes is knife-edge with respect to framing: the same code
  decoded at 16, 24 and 30 px of crop margin but not at 33 or 40, because CLAHE
  tile boundaries shift. Hence a portfolio of sizes and treatments rather than
  one recipe.
- A colour code can have almost no grey-scale separation (navy on crimson
  measures 33 of 255) while separating cleanly in the red channel alone.

## Safety rules that are not negotiable

A decoded payload is untrusted input read off the screen. Only `http://` and
`https://` get an Open action — see `actions.can_open`. Never hand an arbitrary
payload to a shell-execute equivalent; `file://` and app schemes like
`ms-settings:` must stay copy-only. Do not widen this to make a demo nicer.

Result cards and the picker are ordinary windows rather than system
notifications, deliberately: Do Not Disturb silently swallows notifications,
which would make a scan look broken. Keep it that way.
