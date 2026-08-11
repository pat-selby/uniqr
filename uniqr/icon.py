"""Generate the tray icon.

Drawing it in code beats shipping a binary asset: no file to lose, and the
icon scales to whatever size the tray asks for.
"""

import os
from pathlib import Path

from PIL import Image, ImageDraw

SIZES = [16, 20, 24, 32, 48, 64, 256]


def _draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    unit = size / 8.0
    fg = (255, 255, 255, 255)

    def finder(col: float, row: float) -> None:
        x, y = col * unit, row * unit
        d.rectangle([x, y, x + unit * 3 - 1, y + unit * 3 - 1], fill=fg)
        d.rectangle(
            [x + unit * 0.75, y + unit * 0.75, x + unit * 2.25, y + unit * 2.25],
            fill=(0, 0, 0, 0),
        )

    # Three corner squares: the part of a QR code everyone recognises.
    finder(0.25, 0.25)
    finder(4.75, 0.25)
    finder(0.25, 4.75)

    # A few data-ish dots in the empty corner.
    for col, row in [(5, 5), (6.25, 5), (5, 6.25), (6.25, 6.25), (5.6, 5.6)]:
        d.rectangle(
            [col * unit, row * unit, col * unit + unit * 0.8, row * unit + unit * 0.8],
            fill=fg,
        )
    return img


def icon_image(size: int = 64) -> Image.Image:
    """The icon as a PIL image, for tray libraries that want one directly."""
    return _draw(size)


def ensure_icon() -> str:
    """Write the .ico to the local app data folder and return its path."""
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "UniQR"
    base.mkdir(parents=True, exist_ok=True)
    path = base / "tray.ico"
    if not path.exists():
        largest = _draw(256)
        largest.save(path, format="ICO", sizes=[(s, s) for s in SIZES])
    return str(path)
