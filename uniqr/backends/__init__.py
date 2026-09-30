"""Backend selection.

Windows gets its native backend because it is tuned and proven. Everything
else gets the portable one. `UNIQR_BACKEND=portable` forces the portable path
on Windows too, which is how the cross-platform code stays testable here.
"""

import os
import sys

_forced = os.environ.get("UNIQR_BACKEND", "").strip().lower()

if _forced == "portable" or (not _forced and sys.platform != "win32"):
    from uniqr.backends import portable as backend
elif _forced in ("", "windows"):
    from uniqr.backends import windows as backend
else:
    raise ImportError(f"unknown UNIQR_BACKEND {_forced!r}")

from uniqr.backends.base import Rect  # noqa: E402,F401

NAME = backend.NAME
set_dpi_aware = backend.set_dpi_aware
virtual_screen = backend.virtual_screen
grab = backend.grab
cursor_pos = backend.cursor_pos
monitor_at = backend.monitor_at
copy_text = backend.copy_text
round_corners = backend.round_corners


def scale_factor() -> float:
    """Image pixels per screen point. See uniqr/backends/base.py."""
    return backend.scale_factor()


def probe() -> tuple[bool, str]:
    """Verify capture works, where the backend can tell."""
    return backend.probe()


def input_status() -> tuple[bool | None, str]:
    """Whether the OS will deliver global key events, and why not if it will
    not. None means the OS has no such gate, which is not a failure."""
    return backend.input_status()
