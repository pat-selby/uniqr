"""Which real-world screen conditions actually break detection?"""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniqr.decode import Scanner  # noqa: E402

TEXT = "https://example.com/uniqr-test"


def make_qr(size=240, pad=None, invert=False):
    qr = cv2.QRCodeEncoder.create().encode(TEXT)
    qr = cv2.resize(qr, (size, size), interpolation=cv2.INTER_NEAREST)
    pad = pad if pad is not None else max(20, size // 2)
    canvas = np.full((size + pad * 2, size + pad * 2), 255, dtype=np.uint8)
    canvas[pad : pad + size, pad : pad + size] = qr
    if invert:
        canvas = 255 - canvas
    return cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)


def rotate(img, angle):
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    bg = (255, 255, 255) if img[0, 0].mean() > 127 else (0, 0, 0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=bg)


def perspective(img, strength=0.25):
    """Simulate a photo of a screen / slide taken at an angle."""
    h, w = img.shape[:2]
    dx = w * strength
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[dx, 0], [w - dx * 0.3, 0], [w, h], [0, h]])
    m = cv2.getPerspectiveTransform(src, dst)
    bg = (255, 255, 255) if img[0, 0].mean() > 127 else (0, 0, 0)
    return cv2.warpPerspective(img, m, (w, h), borderValue=bg)


def low_contrast(img, factor=0.25):
    mid = np.full_like(img, 128)
    return cv2.addWeighted(img, factor, mid, 1 - factor, 0)


def blur(img, k=5):
    return cv2.GaussianBlur(img, (k, k), 0)


def jpeg(img, quality=30):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


CASES = {
    "baseline 240px": lambda: make_qr(240),
    "small 120px": lambda: make_qr(120),
    "tiny 70px": lambda: make_qr(70),
    "very tiny 45px": lambda: make_qr(45),
    "tight quiet zone": lambda: make_qr(240, pad=8),
    "no quiet zone": lambda: make_qr(240, pad=0),
    "INVERTED (dark mode)": lambda: make_qr(240, invert=True),
    "inverted + rotated 20": lambda: rotate(make_qr(240, invert=True), 20),
    "rotated 20": lambda: rotate(make_qr(240), 20),
    "rotated 45": lambda: rotate(make_qr(240), 45),
    "perspective tilt": lambda: perspective(make_qr(240)),
    "perspective + rot 15": lambda: perspective(rotate(make_qr(240), 15)),
    "low contrast": lambda: low_contrast(make_qr(240)),
    "blurred": lambda: blur(make_qr(240)),
    "jpeg q30": lambda: jpeg(make_qr(240)),
    "small + rotated 30": lambda: rotate(make_qr(110), 30),
    "small + jpeg + rot 10": lambda: rotate(jpeg(make_qr(110)), 10),
}


def main():
    scanner = Scanner()
    fails = []
    print(f"{'case':<24} {'result'}")
    print("-" * 40)
    for name, build in CASES.items():
        img = build()
        found = scanner.scan(img)
        ok = any(d.text == TEXT for d in found)
        print(f"{name:<24} {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(name)
    print("-" * 40)
    print(f"{len(CASES) - len(fails)}/{len(CASES)} passing")
    if fails:
        print("failing:", ", ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
