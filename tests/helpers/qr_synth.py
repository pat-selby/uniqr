"""Synthetic QR images for regression testing."""

from collections.abc import Callable

import cv2
import numpy as np

CONDITIONS_TEXT = "https://example.com/uniqr-test"
STYLIZED_TEXT = "https://morningstar.com/mlt-summer-seminar-checkin"


def make_qr(text: str, size: int = 240, pad: int | None = None, invert: bool = False):
    qr = cv2.QRCodeEncoder.create().encode(text)
    qr = cv2.resize(qr, (size, size), interpolation=cv2.INTER_NEAREST)
    pad = pad if pad is not None else max(20, size // 2)
    canvas = np.full((size + pad * 2, size + pad * 2), 255, dtype=np.uint8)
    canvas[pad : pad + size, pad : pad + size] = qr
    if invert:
        canvas = 255 - canvas
    return cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)


def rotate(img: np.ndarray, angle: float, bg: tuple[int, int, int] | None = None):
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    if bg is None:
        bg = (255, 255, 255) if img[0, 0].mean() > 127 else (0, 0, 0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=bg)


def perspective(img: np.ndarray, strength: float = 0.25):
    h, w = img.shape[:2]
    dx = w * strength
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[dx, 0], [w - dx * 0.3, 0], [w, h], [0, h]])
    m = cv2.getPerspectiveTransform(src, dst)
    bg = (255, 255, 255) if img[0, 0].mean() > 127 else (0, 0, 0)
    return cv2.warpPerspective(img, m, (w, h), borderValue=bg)


def low_contrast(img: np.ndarray, factor: float = 0.25):
    mid = np.full_like(img, 128)
    return cv2.addWeighted(img, factor, mid, 1 - factor, 0)


def blur(img: np.ndarray, k: int = 5):
    return cv2.GaussianBlur(img, (k, k), 0)


def jpeg(img: np.ndarray, quality: int = 30):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def modules(text: str):
    img = cv2.QRCodeEncoder.create().encode(text)
    return (img < 128).astype(np.uint8)


def render(
    grid: np.ndarray,
    scale: int = 10,
    dark=(0, 0, 0),
    light=(255, 255, 255),
    dots: bool = False,
):
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


def quiet(img: np.ndarray, colour, pad: int = 40):
    h, w = img.shape[:2]
    canvas = np.zeros((h + pad * 2, w + pad * 2, 3), dtype=np.uint8)
    canvas[:] = colour
    canvas[pad : pad + h, pad : pad + w] = img
    return canvas


def add_logo(img: np.ndarray, frac: float = 0.18):
    h, w = img.shape[:2]
    s = int(min(h, w) * frac)
    y, x = (h - s) // 2, (w - s) // 2
    cv2.rectangle(img, (x, y), (x + s, y + s), (255, 255, 255), -1)
    pts = np.array(
        [[x + s // 2, y], [x + s, y + s // 2], [x + s // 2, y + s], [x, y + s // 2]]
    )
    cv2.fillPoly(img, [pts], (40, 40, 200))
    return img


def shrink(img: np.ndarray, px: int):
    h, w = img.shape[:2]
    scale = px / max(h, w)
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


MAROON = (60, 20, 140)
NAVY = (60, 25, 20)

CONDITION_CASES: dict[str, Callable[[], np.ndarray]] = {
    "baseline 240px": lambda: make_qr(CONDITIONS_TEXT, 240),
    "small 120px": lambda: make_qr(CONDITIONS_TEXT, 120),
    "tiny 70px": lambda: make_qr(CONDITIONS_TEXT, 70),
    "very tiny 45px": lambda: make_qr(CONDITIONS_TEXT, 45),
    "tight quiet zone": lambda: make_qr(CONDITIONS_TEXT, 240, pad=8),
    "no quiet zone": lambda: make_qr(CONDITIONS_TEXT, 240, pad=0),
    "INVERTED (dark mode)": lambda: make_qr(CONDITIONS_TEXT, 240, invert=True),
    "inverted + rotated 20": lambda: rotate(
        make_qr(CONDITIONS_TEXT, 240, invert=True), 20
    ),
    "rotated 20": lambda: rotate(make_qr(CONDITIONS_TEXT, 240), 20),
    "rotated 45": lambda: rotate(make_qr(CONDITIONS_TEXT, 240), 45),
    "perspective tilt": lambda: perspective(make_qr(CONDITIONS_TEXT, 240)),
    "perspective + rot 15": lambda: perspective(
        rotate(make_qr(CONDITIONS_TEXT, 240), 15)
    ),
    "low contrast": lambda: low_contrast(make_qr(CONDITIONS_TEXT, 240)),
    "blurred": lambda: blur(make_qr(CONDITIONS_TEXT, 240)),
    "jpeg q30": lambda: jpeg(make_qr(CONDITIONS_TEXT, 240)),
    "small + rotated 30": lambda: rotate(make_qr(CONDITIONS_TEXT, 110), 30),
    "small + jpeg + rot 10": lambda: rotate(jpeg(make_qr(CONDITIONS_TEXT, 110)), 10),
}


def _stylized_cases() -> dict[str, np.ndarray]:
    grid = modules(STYLIZED_TEXT)
    return {
        "plain black on white": quiet(render(grid), (255, 255, 255)),
        "MORNINGSTAR navy on maroon": quiet(
            render(grid, dark=NAVY, light=MAROON), MAROON
        ),
        "same shrunk to 150px": shrink(
            quiet(render(grid, dark=NAVY, light=MAROON), MAROON), 150
        ),
        "same shrunk + tilted": rotate(
            shrink(quiet(render(grid, dark=NAVY, light=MAROON), MAROON), 150),
            8,
            MAROON,
        ),
        "LOGO dotted modules": quiet(add_logo(render(grid, dots=True)), (255, 255, 255)),
        "dotted no logo": quiet(render(grid, dots=True), (255, 255, 255)),
        "square modules + logo": quiet(add_logo(render(grid)), (255, 255, 255)),
        "dotted + logo + rot 8": rotate(
            quiet(add_logo(render(grid, dots=True)), (255, 255, 255)),
            8,
            (255, 255, 255),
        ),
    }


STYLIZED_CASES = _stylized_cases()

REAL_PHOTO_EXPECTED = {
    "sap_flyer.png": {
        "https://bit.ly/4jQ5iLN",
        "https://bit.ly/40HVnio",
        "https://bit.ly/3WHdJiw",
    },
    "american.png": {"https://go.bofa.com/q/7b5032"},
    "morningstar.png": {
        "https://linktr.ee/qr/45d45578-8152-4e47-8609-2fb8a62923c4"
    },
    # Rounded finder patterns and dotted modules on a small frame. Failed
    # because the fixed 3x3 tile grid produced tiles smaller than the code.
    "codesignal_card.png": {
        "https://codesignal.com/learn/get-cosmo"
        "?utm_source=learn&utm_medium=qr_code&utm_content=celebration"
    },
}
