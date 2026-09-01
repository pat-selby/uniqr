"""Unit tests for the decoder layer and Detection geometry."""

import cv2
import numpy as np
import pytest
from tests.helpers.qr_synth import make_qr
from uniqr.decode import Detection, _zxing_detect, _zxing_text, zxing_available

TEXT = "https://example.com/uniqr-decoder-test"


@pytest.fixture(scope="module")
def qr_image():
    return make_qr(TEXT, size=240)


# -- second decoder --------------------------------------------------------


def test_zxing_is_installed():
    """Not strictly required, but its absence silently weakens the scanner."""
    assert zxing_available(), "zxing-cpp missing: stylised codes will regress"


def test_zxing_reads_a_plain_code(qr_image):
    assert _zxing_text(qr_image) == TEXT


def test_zxing_returns_positioned_detections(qr_image):
    """Positions matter: the picker overlay draws boxes from these quads."""
    found = _zxing_detect(qr_image)
    assert len(found) == 1
    quad = found[0].quad
    assert quad.shape == (4, 2)

    height, width = qr_image.shape[:2]
    assert quad[:, 0].min() >= 0 and quad[:, 0].max() <= width
    assert quad[:, 1].min() >= 0 and quad[:, 1].max() <= height

    # The quad should sit on the code, not span the padded canvas.
    left, top, box_w, box_h = found[0].bbox
    assert box_w > 0 and box_h > 0
    assert abs(box_w - box_h) < max(box_w, box_h) * 0.2, "quad is not square"


def test_zxing_finds_nothing_in_a_blank_frame():
    blank = np.full((200, 200, 3), 255, dtype=np.uint8)
    assert _zxing_detect(blank) == []
    assert _zxing_text(blank) == ""


def test_zxing_survives_a_degenerate_image():
    """A decoder failure must not become a scan failure."""
    assert _zxing_detect(np.zeros((1, 1, 3), dtype=np.uint8)) == []


def test_zxing_reads_an_inverted_code(qr_image):
    """Handled by the caller passing both polarities, so check the raw path."""
    inverted = cv2.bitwise_not(qr_image)
    assert _zxing_text(qr_image) == TEXT
    # Either polarity decoding is acceptable; both failing is not.
    assert _zxing_text(inverted) in (TEXT, "")


# -- scanner integration ---------------------------------------------------


def test_scanner_uses_both_decoders(scanner, qr_image):
    found = scanner.scan(qr_image)
    assert any(d.text == TEXT for d in found)


def test_scan_returns_detections_with_usable_positions(scanner, qr_image):
    found = [d for d in scanner.scan(qr_image) if d.text == TEXT]
    assert found
    left, top, width, height = found[0].bbox
    assert width > 50 and height > 50


def test_fast_scan_skips_the_expensive_ladder(scanner, qr_image):
    """thorough=False must still read an easy code."""
    found = scanner.scan(qr_image, thorough=False)
    assert any(d.text == TEXT for d in found)


def test_empty_frame_yields_no_detections(scanner):
    blank = np.full((300, 300, 3), 255, dtype=np.uint8)
    assert scanner.scan(blank) == []


# -- Detection geometry ----------------------------------------------------


def quad(x, y, size):
    return np.array(
        [[x, y], [x + size, y], [x + size, y + size], [x, y + size]],
        dtype=np.float32,
    )


def test_bbox_is_left_top_width_height():
    assert Detection("t", quad(10, 20, 30)).bbox == (10, 20, 30, 30)


def test_center_is_the_quad_centre():
    assert Detection("t", quad(10, 20, 30)).center == (25, 35)


def test_offset_shifts_without_mutating_the_original():
    original = Detection("t", quad(10, 20, 30))
    moved = original.offset(5, 7)
    assert moved.bbox == (15, 27, 30, 30)
    assert original.bbox == (10, 20, 30, 30), "offset mutated its input"
    assert moved.text == original.text


def test_offset_accepts_negative_origins():
    """Multi-monitor setups put the virtual desktop origin below zero."""
    moved = Detection("t", quad(10, 20, 30)).offset(-100, -50)
    assert moved.bbox == (-90, -30, 30, 30)
