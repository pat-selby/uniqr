"""macOS and Linux backend, built on mss / pynput / pyperclip.

mss grabs pixels on all three platforms, so the capture path here is the same
code on macOS, X11 and Wayland-with-XWayland. Both platforms gate this behind
a permission the user has to grant by hand:

  macOS  System Settings > Privacy & Security > Screen Recording
  Linux  works on X11; on pure Wayland a portal-based grab is needed instead

A denied permission does not raise - it hands back a black or empty frame -
so `probe()` exists to tell a blank screen from a blocked one.
"""

import threading

import numpy as np

from uniqr.backends.base import Rect

NAME = "portable"

_local = threading.local()


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


def cursor_pos() -> tuple[int, int]:
    from pynput.mouse import Controller

    x, y = Controller().position
    return int(x), int(y)


def copy_text(text: str) -> None:
    import pyperclip

    pyperclip.copy(text)


def probe() -> tuple[bool, str]:
    """Check that capture actually returns pixels.

    On macOS a process without Screen Recording permission still gets frames,
    they are just uniformly black - which is indistinguishable from a failure
    unless something looks.
    """
    try:
        shot = grab()
    except Exception as exc:  # noqa: BLE001 - report whatever the OS raised
        return False, f"screen capture failed: {exc}"
    if shot.size == 0:
        return False, "screen capture returned an empty frame"
    if int(shot.max()) - int(shot.min()) < 2:
        return False, (
            "screen capture returned a blank frame - on macOS grant Screen "
            "Recording in System Settings > Privacy & Security, then restart"
        )
    return True, f"captured {shot.shape[1]}x{shot.shape[0]}"
