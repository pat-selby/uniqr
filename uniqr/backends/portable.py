"""macOS and Linux backend, built on mss / pynput / pyperclip.

mss grabs pixels on all three platforms, so the capture path here is the same
code on macOS, X11 and Wayland-with-XWayland. Both platforms gate this behind
a permission the user has to grant by hand:

  macOS  System Settings > Privacy & Security > Screen Recording
  Linux  works on X11; on pure Wayland a portal-based grab is needed instead

A denied permission does not raise - it hands back a frame anyway - so
`probe()` exists to tell a working capture from a blocked one. On macOS it
asks the OS outright; everywhere else it falls back to looking at the pixels.

macOS also gates global key events behind Input Monitoring / Accessibility,
and pynput starts a listener happily without it and then hears nothing. Both
permissions attach to the app that launched Python - Terminal, iTerm, an IDE -
not to Python itself, and only take effect once that app is fully quit and
reopened.
"""

import ctypes
import ctypes.util
import sys
import threading

import numpy as np

from uniqr.backends.base import Rect

NAME = "portable"

_local = threading.local()
_scale: float | None = None


def _framework(name: str):
    """Load a system framework, or None where it does not exist."""
    path = ctypes.util.find_library(name)
    if not path:
        return None
    try:
        return ctypes.cdll.LoadLibrary(path)
    except OSError:
        return None


def _ask_bool(framework_name: str, symbol: str) -> bool | None:
    """Call a no-argument BOOL system function, or None if unavailable."""
    if sys.platform != "darwin":
        return None
    lib = _framework(framework_name)
    fn = getattr(lib, symbol, None) if lib is not None else None
    if fn is None:
        return None
    fn.restype = ctypes.c_bool
    fn.argtypes = []
    try:
        return bool(fn())
    except Exception:  # noqa: BLE001 - an unusable symbol is just "unknown"
        return None


def screen_capture_allowed() -> bool | None:
    """Has this process been granted Screen Recording?

    The authoritative answer, and the only reliable one: a denied process is
    not always handed a black frame. Depending on the macOS version it may get
    the desktop picture with every window left out, which has a perfectly
    normal pixel spread and looks like a working capture of an empty desktop.

    None on Linux and on macOS too old to have the call (pre-10.15).
    """
    return _ask_bool("CoreGraphics", "CGPreflightScreenCaptureAccess")


GRANT_TO = (
    "Grant it to the app that launched UniQR - Terminal, iTerm, your IDE - "
    "not to Python, then quit that app completely and reopen it"
)


def input_status() -> tuple[bool | None, str]:
    """Will the OS deliver global key events to this process?

    macOS has two separate switches here and they are easy to confuse:

      Input Monitoring  CGPreflightListenEventAccess
      Accessibility     AXIsProcessTrusted

    pynput's macOS backend gates on Accessibility, so that is the one that
    decides whether a hotkey ever fires. Input Monitoring can be granted, and
    the listener still hear nothing. Both are reported because being told to
    grant the permission you already granted is worse than no advice.
    """
    trusted = _ask_bool("ApplicationServices", "AXIsProcessTrusted")
    if trusted is None:
        return None, "this OS has no permission gate on keyboard input"
    if trusted:
        return True, "Accessibility granted, key events will be delivered"

    listening = _ask_bool("CoreGraphics", "CGPreflightListenEventAccess")
    if listening:
        missing = (
            "Input Monitoring is granted but Accessibility is not, and it is "
            "Accessibility that pynput needs"
        )
    else:
        missing = "neither Accessibility nor Input Monitoring is granted"
    return False, f"{missing}. {GRANT_TO}"


def _sct():
    """One mss instance per thread; mss objects are not thread-safe."""
    import mss

    if getattr(_local, "sct", None) is None:
        _local.sct = mss.mss()
    return _local.sct


def set_dpi_aware() -> None:
    """No-op.

    macOS reports points and hands back Retina pixels without asking, and
    there is no equivalent global switch on Linux.
    """


def virtual_screen() -> Rect:
    # monitors[0] is mss's combined "all monitors" rectangle.
    m = _sct().monitors[0]
    return Rect(left=m["left"], top=m["top"], width=m["width"], height=m["height"])


def grab(rect: Rect | None = None) -> np.ndarray:
    if rect is None:
        rect = virtual_screen()
    raw = _sct().grab(
        {
            "left": rect.left,
            "top": rect.top,
            "width": rect.width,
            "height": rect.height,
        }
    )
    # mss hands back BGRA; drop alpha to match the Windows backend.
    return np.ascontiguousarray(np.asarray(raw, dtype=np.uint8)[:, :, :3])


def scale_factor() -> float:
    """Image pixels per screen point, measured rather than assumed.

    mss reports monitor geometry in points but the frame it returns is
    whatever the display actually holds, so on Retina a 100-point region comes
    back 200 pixels wide. Which of the two you get depends on the mss version
    and on its IMAGE_OPTIONS flags, so the only answer worth trusting is the
    one you get by grabbing a small region and comparing.

    Measured once and cached; a display swapped mid-run is rare enough, and a
    stale value only costs a slightly misplaced overlay.
    """
    global _scale
    if _scale is not None:
        return _scale

    screen = virtual_screen()
    probe_rect = Rect(
        left=screen.left,
        top=screen.top,
        width=min(64, screen.width),
        height=min(64, screen.height),
    )
    try:
        shot = grab(probe_rect)
        _scale = shot.shape[1] / probe_rect.width if probe_rect.width else 1.0
    except Exception:  # noqa: BLE001 - a failed grab is probe()'s problem
        _scale = 1.0
    if not 0.1 <= _scale <= 8.0:  # nonsense; better to be 1:1 than wildly off
        _scale = 1.0
    return _scale


def cursor_pos() -> tuple[int, int]:
    from pynput.mouse import Controller

    x, y = Controller().position
    return int(x), int(y)


def copy_text(text: str) -> None:
    import pyperclip

    pyperclip.copy(text)


DENIED = (
    "on macOS grant Screen Recording in System Settings > Privacy & Security "
    "to the app that launched this - Terminal, iTerm, your IDE - then quit "
    "that app completely and reopen it"
)


def probe() -> tuple[bool, str]:
    """Check that we can actually read the screen.

    A denied permission never raises, so this asks two questions. The OS one
    is definitive where it exists. The pixel one is a fallback for Linux and
    for old macOS, and it can only catch the obvious case: a frame with no
    variation at all is either a blocked capture or a screen worth nothing to
    a QR scanner either way.
    """
    allowed = screen_capture_allowed()
    if allowed is False:
        return False, f"Screen Recording permission denied - {DENIED}"

    try:
        shot = grab()
    except Exception as exc:  # noqa: BLE001 - report whatever the OS raised
        return False, f"screen capture failed: {exc}"
    if shot.size == 0:
        return False, "screen capture returned an empty frame"
    if int(shot.max()) - int(shot.min()) < 2:
        return False, (
            f"screen capture returned a blank frame - {DENIED}"
            if allowed is None
            else "screen capture returned a blank frame despite permission "
            "being granted - is the display asleep?"
        )

    detail = f"captured {shot.shape[1]}x{shot.shape[0]}"
    if allowed:
        detail += ", Screen Recording granted"
    return True, detail
