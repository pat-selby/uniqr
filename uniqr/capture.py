"""Screen capture, delegated to whichever backend fits the OS.

This module is the capture API the rest of UniQR imports. The platform detail
lives in uniqr/backends; the geometry helpers below are plain arithmetic and
are shared by every platform.
"""

from uniqr.backends import (  # noqa: F401
    NAME,
    Rect,
    copy_text,
    cursor_pos,
    grab,
    probe,
    set_dpi_aware,
    virtual_screen,
)


def region_around(x: int, y: int, size: int = 600) -> Rect:
    """A square region centred on a point, clipped to the virtual desktop."""
    screen = virtual_screen()
    half = size // 2
    width = min(size, screen.width)
    height = min(size, screen.height)
    left = max(screen.left, min(x - half, screen.right - width))
    top = max(screen.top, min(y - half, screen.bottom - height))
    return Rect(left=left, top=top, width=width, height=height)
