"""Recreate the two failures: a coloured code, and a stylised code with a logo."""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniqr.decode import Scanner  # noqa: E402

TEXT = "https://morningstar.com/mlt-summer-seminar-checkin"


def modules(text):
    """The raw QR grid, one pixel per module."""
    img = cv2.QRCodeEncoder.create().encode(text)
    return (img < 128).astype(np.uint8)  # 1 = dark module


def render(grid, scale=10, dark=(0, 0, 0), light=(255, 255, 255), dots=False):
    n = grid.shape[0]
    out = np.zeros((n * scale, n * scale, 3), dtype=np.uint8)
    out[:] = light
    for y in range(n):
        for x in range(n):
            if not grid[y, x]:
                continue
            cx, cy = x * scale, y * scale
            if dots:
                cv2.circle(
                    out,
                    (cx + scale // 2, cy + scale // 2),
                    max(1, int(scale * 0.42)),
                    dark,
                    -1,
                )
            else:
                out[cy : cy + scale, cx : cx + scale] = dark
    return out


def quiet(img, colour, pad=40):
    h, w = img.shape[:2]
    canvas = np.zeros((h + pad * 2, w + pad * 2, 3), dtype=np.uint8)
    canvas[:] = colour
    canvas[pad : pad + h, pad : pad + w] = img
    return canvas


def add_logo(img, frac=0.18):
    h, w = img.shape[:2]
    s = int(min(h, w) * frac)
    y, x = (h - s) // 2, (w - s) // 2
    cv2.rectangle(img, (x, y), (x + s, y + s), (255, 255, 255), -1)
    pts = np.array(
        [[x + s // 2, y], [x + s, y + s // 2], [x + s // 2, y + s], [x, y + s // 2]]
    )
    cv2.fillPoly(img, [pts], (40, 40, 200))
    return img


def rotate(img, angle, bg):
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=bg)


def shrink(img, px):
    h, w = img.shape[:2]
    scale = px / max(h, w)
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


MAROON = (60, 20, 140)  # BGR - the Morningstar card background
NAVY = (60, 25, 20)     # BGR - dark blue modules

grid = modules(TEXT)

CASES = {
    "plain black on white": quiet(render(grid), (255, 255, 255)),
    "MORNINGSTAR navy on maroon": quiet(render(grid, dark=NAVY, light=MAROON), MAROON),
    "  same, shrunk to 150px": shrink(
        quiet(render(grid, dark=NAVY, light=MAROON), MAROON), 150
    ),
    "  same, shrunk + tilted": rotate(
        shrink(quiet(render(grid, dark=NAVY, light=MAROON), MAROON), 150), 8, MAROON
    ),
    "LOGO dotted modules": quiet(
        add_logo(render(grid, dots=True)), (255, 255, 255)
    ),
    "  dotted, no logo": quiet(render(grid, dots=True), (255, 255, 255)),
    "  square modules + logo": quiet(add_logo(render(grid)), (255, 255, 255)),
    "  dotted + logo + rot 8": rotate(
        quiet(add_logo(render(grid, dots=True)), (255, 255, 255)),
        8,
        (255, 255, 255),
    ),
}


def grey_contrast(img):
    """How separable are the two tones after the usual BGR->grey collapse?"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return int(g.max()) - int(g.min()), g.std()


def main() -> int:
    s = Scanner()
    fails = []
    print(f"{'case':<32} {'result':<7} {'grey range':<11} {'grey std'}")
    print("-" * 64)
    for name, img in CASES.items():
        rng, std = grey_contrast(img)
        ok = any(d.text == TEXT for d in s.scan(img))
        print(f"{name:<32} {'ok' if ok else 'FAIL':<7} {rng:<11} {std:.1f}")
        if not ok:
            fails.append(name)
    print("-" * 64)
    print(f"{len(CASES) - len(fails)}/{len(CASES)} passing")
    if fails:
        print("failing:", ", ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
