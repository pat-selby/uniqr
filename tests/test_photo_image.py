"""Handing the picker's picture to Tk.

With Tk 9 on macOS, Pillow's ImageTk bridge gave the picker a picture that never
drew, so it showed as a dark empty window. With Tk 9 the picture now goes to Tk
as PPM, which Tk reads itself. These tests check that route gives exactly the
same pixels, and that it is the one chosen for Tk 9.
"""

import sys
import tkinter as tk

import numpy as np
import pytest
from PIL import Image
from uniqr import overlay

# Tk windows in the test process hung the macOS run in CI before, so like the
# other Tk tests these run on Windows and Linux only, and need a display.
pytestmark = pytest.mark.skipif(sys.platform == "darwin", reason="Tk tests are off on macOS CI")


@pytest.fixture(scope="module")
def root():
    try:
        r = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"no display: {exc}")
    r.withdraw()
    yield r
    r.destroy()


@pytest.fixture
def picture():
    pixels = np.random.default_rng(7).integers(0, 256, (90, 160, 3), dtype=np.uint8)
    return Image.fromarray(pixels)


def same_pixels(photo, image):
    assert (photo.width(), photo.height()) == image.size
    for x, y in [(0, 0), (159, 89), (80, 45), (13, 77), (151, 3)]:
        assert tuple(photo.get(x, y)) == image.getpixel((x, y))


def test_the_tk9_route_gives_exactly_the_same_pixels(root, picture):
    same_pixels(overlay.photo_image(picture, root, bridge=False), picture)


def test_tk9_skips_the_bridge(root, picture, monkeypatch):
    monkeypatch.setattr(overlay.tk, "TkVersion", 9.0)

    def broken(*args, **kwargs):
        raise AssertionError("the ImageTk bridge must not be used with Tk 9")

    monkeypatch.setattr(overlay.ImageTk, "PhotoImage", broken)
    same_pixels(overlay.photo_image(picture, root), picture)


def test_tk86_keeps_the_fast_bridge(root, picture, monkeypatch):
    monkeypatch.setattr(overlay.tk, "TkVersion", 8.6)
    used = []
    real = overlay.ImageTk.PhotoImage
    monkeypatch.setattr(overlay.ImageTk, "PhotoImage", lambda *a, **k: used.append(1) or real(*a, **k))
    overlay.photo_image(picture, root)
    assert used == [1]


def test_png_is_the_backup_when_ppm_is_refused(root, picture, monkeypatch):
    real = tk.PhotoImage

    def no_ppm(*args, data=None, **kwargs):
        if data is not None and data[:2] == b"P6":
            raise tk.TclError("couldn't recognize image data")
        return real(*args, data=data, **kwargs)

    monkeypatch.setattr(overlay.tk, "PhotoImage", no_ppm)
    same_pixels(overlay.photo_image(picture, root, bridge=False), picture)


def test_a_picture_with_transparency_is_flattened(root):
    rgba = Image.new("RGBA", (20, 10), (10, 200, 30, 128))
    photo = overlay.photo_image(rgba, root, bridge=False)
    assert (photo.width(), photo.height()) == (20, 10)
