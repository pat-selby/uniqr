"""Engine round-trip without a screen."""

import cv2
import numpy as np
from uniqr.decode import Scanner


def test_selftest_roundtrip():
    expected = "https://example.com/uniqr-selftest?id=42"
    qr = cv2.QRCodeEncoder.create().encode(expected)
    qr = cv2.resize(qr, (240, 240), interpolation=cv2.INTER_NEAREST)
    canvas = np.full((400, 400), 255, dtype=np.uint8)
    canvas[80:320, 80:320] = qr
    image = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)

    found = Scanner().scan(image)
    assert len(found) == 1
    assert found[0].text == expected
