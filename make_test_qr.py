"""Make a QR code picture you can put on screen to test UniQR.

    python make_test_qr.py                       # writes test_qr.png
    python make_test_qr.py "hello" small.png 120 # your own text and size
"""

import sys

import cv2
import numpy as np

DEFAULT_TEXT = "https://example.com/uniqr-works"


def make(text: str, path: str, size: int) -> None:
    qr = cv2.QRCodeEncoder.create().encode(text)
    qr = cv2.resize(qr, (size, size), interpolation=cv2.INTER_NEAREST)

    # The white border ("quiet zone") is not decoration - detectors need it.
    pad = max(16, size // 8)
    canvas = np.full((size + pad * 2, size + pad * 2), 255, dtype=np.uint8)
    canvas[pad : pad + size, pad : pad + size] = qr

    cv2.imwrite(path, canvas)
    print(f"wrote {path} ({canvas.shape[1]}x{canvas.shape[0]}) holding: {text}")


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TEXT
    path = sys.argv[2] if len(sys.argv) > 2 else "test_qr.png"
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    make(text, path, size)
