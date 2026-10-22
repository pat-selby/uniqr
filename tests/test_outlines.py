"""Outlines in the picker sit on the code they belong to.

On a tester's busy screen, the locate-and-straighten pass found a code again
inside a large shape stitched from several codes' corners, and the picker drew
that shape: long skewed lines over other codes. Two fixes, tested here: the
same code found inside another outline is a duplicate, and a code read from a
rough outline gets zxing's exact corners.
"""

import numpy as np
from tests.helpers.qr_synth import make_qr
from uniqr.decode import Detection, _merge, _true_outline

TEXT = "https://example.com/outline"


def quad(x, y, w, h):
    return np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.float32)


def test_the_same_code_inside_a_bigger_outline_is_a_duplicate():
    real = Detection(TEXT, quad(100, 100, 120, 120))
    ghost = Detection(TEXT, np.array([[60, 90], [600, 60], [620, 400], [80, 260]], dtype=np.float32))
    assert _merge([[real], [ghost]]) == [real]


def test_two_copies_of_one_code_side_by_side_both_stay():
    left = Detection(TEXT, quad(100, 100, 120, 120))
    right = Detection(TEXT, quad(400, 100, 120, 120))
    assert len(_merge([[left], [right]])) == 2


def test_different_codes_in_overlapping_outlines_both_stay():
    a = Detection(TEXT, quad(100, 100, 300, 300))
    b = Detection("https://example.com/other", quad(150, 150, 100, 100))
    assert len(_merge([[a], [b]])) == 2


def test_a_rough_outline_is_replaced_by_the_codes_real_corners():
    code = make_qr(TEXT, size=200)
    page = np.full((600, 800, 3), 255, dtype=np.uint8)
    h, w = code.shape[:2]
    page[150:150 + h, 250:250 + w] = code if code.ndim == 3 else code[:, :, None]
    rough = np.array([[180, 120], [650, 140], [600, 500], [230, 420]], dtype=np.float32)
    exact = _true_outline(page, rough, TEXT)
    xs, ys = exact[:, 0], exact[:, 1]
    assert xs.min() >= 250 and xs.max() <= 250 + w
    assert ys.min() >= 150 and ys.max() <= 150 + h


def test_without_a_matching_read_the_rough_outline_stays():
    page = np.full((300, 300, 3), 255, dtype=np.uint8)
    rough = quad(50, 50, 100, 100)
    assert np.array_equal(_true_outline(page, rough, TEXT), rough)
