"""Ways a code gets worse between the page and the scanner.

Each function takes an image and returns a worse one. They are sized relative
to the code, not in absolute pixels: a blur that is gentle on a code drawn 10
pixels per module erases one drawn 2 pixels per module, so "blur" always means
a fraction of a module.

`s` is severity from 0 to 1. A single-distortion case runs at s=1, which is
meant to be bad but fair: the damage stays inside what a phone would still
read. Combined cases stack three distortions at s=0.5 each.
"""

from collections.abc import Callable

import cv2
import numpy as np

from benchmarks.generate import EC_CAPACITY


def _bg(img: np.ndarray) -> tuple[int, int, int]:
    """The page color, taken from a corner of the quiet zone."""
    b, g, r = (int(v) for v in img[2, 2])
    return b, g, r


def rotate(img: np.ndarray, rng: np.random.Generator, ppm: float, ec: str, s: float):
    # Any angle at all. A phone is held at any angle, and screens show rotated
    # codes in posters and slides.
    angle = float(rng.uniform(0, 360))
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    m[0, 2] += nw / 2 - w / 2
    m[1, 2] += nh / 2 - h / 2
    return cv2.warpAffine(img, m, (nw, nh), flags=cv2.INTER_CUBIC, borderValue=_bg(img))


def perspective(img: np.ndarray, rng: np.random.Generator, ppm: float, ec: str, s: float):
    h, w = img.shape[:2]
    j = 0.18 * s
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    jit = rng.uniform(-j, j, (4, 2)) * np.array([w, h])
    pad = int(0.2 * max(w, h))
    dst = (src + jit + pad).astype(np.float32)
    m = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(
        img, m, (w + 2 * pad, h + 2 * pad), flags=cv2.INTER_CUBIC, borderValue=_bg(img)
    )


def blur(img: np.ndarray, rng: np.random.Generator, ppm: float, ec: str, s: float):
    # A fraction of one module. Past about half a module the squares merge.
    sigma = float(rng.uniform(0.15, 0.40)) * ppm * s
    return cv2.GaussianBlur(img, (0, 0), max(0.3, sigma))


def noise(img: np.ndarray, rng: np.random.Generator, ppm: float, ec: str, s: float):
    sigma = float(rng.uniform(8, 28)) * s
    out = img.astype(np.float32) + rng.normal(0, sigma, img.shape)
    return np.clip(out, 0, 255).astype(np.uint8)


def jpeg(img: np.ndarray, rng: np.random.Generator, ppm: float, ec: str, s: float):
    quality = int(np.interp(s, [0, 1], [70, 18]) + rng.integers(-4, 5))
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, max(5, quality)])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR) if ok else img


def low_contrast(img: np.ndarray, rng: np.random.Generator, ppm: float, ec: str, s: float):
    # factor 1 is untouched, 0 is flat grey.
    factor = float(np.interp(s, [0, 1], [0.7, 0.28]))
    mid = np.full_like(img, 128)
    return cv2.addWeighted(img, factor, mid, 1 - factor, 0)


def glare(img: np.ndarray, rng: np.random.Generator, ppm: float, ec: str, s: float):
    """A bright soft blob, like a window reflecting off a screen."""
    h, w = img.shape[:2]
    cy, cx = float(rng.uniform(0.2, 0.8)) * h, float(rng.uniform(0.2, 0.8)) * w
    radius = float(rng.uniform(0.25, 0.45)) * max(h, w)
    yy, xx = np.mgrid[0:h, 0:w]
    falloff = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (radius / 2) ** 2)))
    add = (falloff * 140 * s)[..., None]
    return np.clip(img.astype(np.float32) + add, 0, 255).astype(np.uint8)


def shadow(img: np.ndarray, rng: np.random.Generator, ppm: float, ec: str, s: float):
    """Uneven light: one side darker than the other."""
    h, w = img.shape[:2]
    angle = float(rng.uniform(0, 2 * np.pi))
    yy, xx = np.mgrid[0:h, 0:w]
    ramp = (xx * np.cos(angle) + yy * np.sin(angle)) / max(h, w)
    ramp = (ramp - ramp.min()) / (ramp.max() - ramp.min() + 1e-6)
    gain = (1 - 0.6 * s * ramp)[..., None]
    return np.clip(img.astype(np.float32) * gain, 0, 255).astype(np.uint8)


def damage(img: np.ndarray, rng: np.random.Generator, ppm: float, ec: str, s: float):
    """Cover part of the data, sized from what the error correction can lose.

    A smudge, sticker or crease, kept away from the finder corners. The share
    is a fifth of the stated recovery figure: those figures assume the damaged
    spots are known, and a real reader has to find them, so half is the honest
    limit, and a block (not scattered specks) costs more than its area. Formats
    with no level to read (Micro QR, Data Matrix, ...) get a flat small share.

    Even so, some placements land on something critical. The runner checks
    every miss against an enlarged copy and reports the ones that no reader
    could recover separately, rather than counting them against UniQR.
    """
    h, w = img.shape[:2]
    budget = EC_CAPACITY.get(ec, 0.06) * 0.2 * s
    side = int(np.sqrt(budget) * min(h, w))
    if side < 3:
        return img
    cx = int(rng.uniform(0.35, 0.65) * w)
    cy = int(rng.uniform(0.35, 0.65) * h)
    color = tuple(int(v) for v in rng.integers(0, 256, 3))
    out = img.copy()
    cv2.rectangle(out, (cx - side // 2, cy - side // 2), (cx + side // 2, cy + side // 2), color, -1)
    return out


Distortion = Callable[[np.ndarray, np.random.Generator, float, str, float], np.ndarray]

DISTORTIONS: dict[str, Distortion] = {
    "rotate": rotate,
    "perspective": perspective,
    "blur": blur,
    "noise": noise,
    "jpeg": jpeg,
    "low_contrast": low_contrast,
    "glare": glare,
    "shadow": shadow,
    "damage": damage,
}

# Mild enough to stack three of them and still have a fair chance.
STACKABLE = ["rotate", "perspective", "blur", "noise", "jpeg", "shadow"]


def apply(
    img: np.ndarray,
    names: list[str],
    rng: np.random.Generator,
    ppm: float,
    ec: str,
    s: float,
) -> np.ndarray:
    for name in names:
        img = DISTORTIONS[name](img, rng, ppm, ec, s)
    return img


def on_page(img: np.ndarray, size: tuple[int, int], rng: np.random.Generator) -> np.ndarray:
    """Put a code somewhere on a screen-sized page with other things on it.

    The page has a gradient background, lines of text, and boxes, so the scan
    has to find a small code in clutter, as it does on a real desktop.
    """
    pw, ph = size
    h, w = img.shape[:2]
    if w >= pw or h >= ph:
        return img
    base = rng.integers(200, 250, 3)
    page = np.empty((ph, pw, 3), dtype=np.uint8)
    page[:] = base
    ramp = np.linspace(0, 1, pw, dtype=np.float32)[None, :, None]
    page = np.clip(page.astype(np.float32) - 30 * ramp, 0, 255).astype(np.uint8)
    for _ in range(int(rng.integers(8, 20))):
        y = int(rng.integers(10, ph - 10))
        x = int(rng.integers(10, pw // 2))
        cv2.putText(
            page, "Lorem ipsum dolor sit amet consectetur", (x, y),
            cv2.FONT_HERSHEY_SIMPLEX, float(rng.uniform(0.5, 1.1)),
            (int(rng.integers(0, 90)),) * 3, 1, cv2.LINE_AA,
        )
    for _ in range(int(rng.integers(3, 8))):
        x0, y0 = int(rng.integers(0, pw - 60)), int(rng.integers(0, ph - 60))
        cv2.rectangle(
            page, (x0, y0), (x0 + int(rng.integers(40, 300)), y0 + int(rng.integers(20, 160))),
            tuple(int(v) for v in rng.integers(60, 230, 3)), 2,
        )
    x = int(rng.integers(0, pw - w))
    y = int(rng.integers(0, ph - h))
    page[y : y + h, x : x + w] = img
    return page
