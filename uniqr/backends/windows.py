"""Windows backend: GDI BitBlt capture and the Win32 clipboard.

Kept in preference to the portable backend on Windows because it is tuned and
proven here - a full 4K virtual desktop grabs in about 50 ms straight into a
numpy array with no image-file round trip.
"""

import ctypes

import numpy as np
import win32clipboard
import win32con
import win32gui
import win32ui

from uniqr.backends.base import Rect

NAME = "windows"

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4


def set_dpi_aware() -> None:
    """Opt into per-monitor DPI awareness.

    Must run before any window is created or any screen is captured. Without
    it Windows hands a scaled-display process a blurry downscale of the screen
    and coordinates that are off by the scale factor - blur that is enough to
    make QR detection fail outright.
    """
    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDpiAwarenessContext(
            ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        )
    except AttributeError:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)


def virtual_screen() -> Rect:
    m = ctypes.windll.user32.GetSystemMetrics
    return Rect(
        left=m(SM_XVIRTUALSCREEN),
        top=m(SM_YVIRTUALSCREEN),
        width=m(SM_CXVIRTUALSCREEN),
        height=m(SM_CYVIRTUALSCREEN),
    )


def grab(rect: Rect | None = None) -> np.ndarray:
    if rect is None:
        rect = virtual_screen()

    desktop = win32gui.GetDesktopWindow()
    src_dc = dc = mem_dc = bitmap = None
    try:
        src_dc = win32gui.GetWindowDC(desktop)
        dc = win32ui.CreateDCFromHandle(src_dc)
        mem_dc = dc.CreateCompatibleDC()

        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(dc, rect.width, rect.height)
        mem_dc.SelectObject(bitmap)
        mem_dc.BitBlt(
            (0, 0),
            (rect.width, rect.height),
            dc,
            (rect.left, rect.top),
            win32con.SRCCOPY,
        )

        buf = bitmap.GetBitmapBits(True)
        bgra = np.frombuffer(buf, dtype=np.uint8).reshape(rect.height, rect.width, 4)
        return np.ascontiguousarray(bgra[:, :, :3])
    finally:
        if bitmap is not None:
            win32gui.DeleteObject(bitmap.GetHandle())
        if mem_dc is not None:
            mem_dc.DeleteDC()
        if dc is not None:
            dc.DeleteDC()
        if src_dc is not None:
            win32gui.ReleaseDC(desktop, src_dc)


def cursor_pos() -> tuple[int, int]:
    return win32gui.GetCursorPos()


def copy_text(text: str) -> None:
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()
