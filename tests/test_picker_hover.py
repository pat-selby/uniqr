"""Hovering over a code in the picker shows its card, and the card stays while the
pointer is on it, so its buttons can be pressed.

On a Mac the picker heard the mouse only while a button was held, so it now asks
where the pointer is instead. These tests drive that path with a made-up pointer
position; nothing moves the real mouse.
"""

import sys
import tkinter as tk
import types

import numpy as np
import pytest
from uniqr import capture, overlay
from uniqr.decode import Detection

# Like the other Tk tests: Windows and Linux with a display only.
pytestmark = pytest.mark.skipif(sys.platform == "darwin", reason="Tk tests are off on macOS CI")


def _detection(left, top, size, text):
    quad = np.array(
        [(left, top), (left + size, top), (left + size, top + size), (left, top + size)],
        dtype=np.float32,
    )
    return Detection(text=text, quad=quad)


@pytest.fixture
def picker(monkeypatch):
    try:
        overlay.shared_root()
    except tk.TclError as exc:
        pytest.skip(f"no display: {exc}")
    monkeypatch.setattr(capture, "scale_factor", lambda: 1.0)
    shot = np.full((400, 600, 3), 180, dtype=np.uint8)
    dets = [
        _detection(100, 80, 120, "https://example.com/one"),
        _detection(360, 220, 100, "https://example.com/two"),
    ]
    p = overlay.Picker(shot, dets, origin=(0, 0))
    p.win.update_idletasks()
    yield p
    p._close()
    p.root.update()


def test_hovering_a_code_shows_its_card(picker):
    picker._hover_at(160, 140)
    assert picker._active == 0
    assert picker._card is not None


def test_the_card_stays_while_the_pointer_is_on_it(picker):
    picker._hover_at(160, 140)
    picker.win.update_idletasks()
    x0, y0, x1, y1 = picker.canvas.bbox(picker._card)
    picker._hover_at((x0 + x1) // 2, (y0 + y1) // 2)
    assert picker._active == 0 and picker._card is not None


def test_moving_off_both_code_and_card_hides_it(picker):
    picker._hover_at(160, 140)
    picker._hover_at(590, 10)
    assert picker._active is None and picker._card is None


def test_the_pointer_check_follows_the_pointer(picker, monkeypatch):
    left, top = picker.canvas.winfo_rootx(), picker.canvas.winfo_rooty()
    monkeypatch.setattr(picker.win, "winfo_pointerx", lambda: left + 410)
    monkeypatch.setattr(picker.win, "winfo_pointery", lambda: top + 270)
    picker._poll_pointer()
    assert picker._active == 1


def test_the_pointer_check_stops_quietly_once_the_picker_closes(picker):
    picker._close()
    picker.root.update()
    picker._poll_pointer()  # must not raise


def test_clicking_a_safe_link_opens_it(picker):
    picker._on_click(types.SimpleNamespace(x=160, y=140))
    assert picker.result[0] == "open"


def test_clicking_a_link_with_a_warning_copies_and_shows_its_card(picker):
    picker.detections[0] = Detection("http://example.com/one", picker.detections[0].quad)
    picker._on_click(types.SimpleNamespace(x=160, y=140))
    assert picker.result[0] == "copy"
