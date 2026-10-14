"""A small code on a screen-sized frame is enlarged and read.

A real screen is bigger than the scanner's enlargement limit, so a code only two
pixels per module wide was never enlarged and was missed: it read when cropped on
its own and not when it sat on a 1080p page. The fixture is a QR code from a
campus poster that UniQR missed on a real desktop. It is about 90 pixels across,
two pixels per module, with a logo in the middle.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest
from uniqr import decode

FIXTURE = Path(__file__).parent / "fixtures" / "small_poster_code.png"
TEXT = "https://qrco.de/bgyYxV"


@pytest.fixture(scope="module")
def code():
    image = cv2.imread(str(FIXTURE))
    assert image is not None, "fixture missing"
    return image


def on_screen(code, width, height, x, y, background=24):
    screen = np.full((height, width, 3), background, np.uint8)
    h, w = code.shape[:2]
    screen[y : y + h, x : x + w] = code
    return screen


SCREENS = [
    (1280, 800, 500, 300),  # a laptop
    (1920, 1080, 600, 400),  # the common one
    (1920, 1080, 1700, 900),  # near the corner
    (3840, 2160, 2000, 1000),  # 4K
    (4600, 900, 4400, 400),  # two monitors side by side, the code on the second
    (4600, 900, 2000, 400),  # the same, the code in the overlap of two pieces
]


@pytest.mark.parametrize(("width", "height", "x", "y"), SCREENS)
def test_a_small_code_on_a_big_screen_is_read_and_reported_where_it_is(
    scanner, code, width, height, x, y
):
    """Enlarging, and reading in pieces, must not move it."""
    found = scanner.scan(on_screen(code, width, height, x, y))
    assert [d.text for d in found] == [TEXT]
    h, w = code.shape[:2]
    cx, cy = found[0].center
    assert x <= cx <= x + w and y <= cy <= y + h


def test_a_light_page_works_too(scanner, code):
    assert [d.text for d in scanner.scan(on_screen(code, 1920, 1080, 600, 400, 255))] == [TEXT]


def test_the_code_on_its_own_still_reads(scanner, code):
    assert [d.text for d in scanner.scan(code)] == [TEXT]


# -- enlarging a big frame must not invent codes --------------------------------


@pytest.mark.parametrize("size", [(1920, 1080), (4600, 900)])
def test_a_blank_screen_still_holds_nothing(scanner, size):
    assert scanner.scan(np.full((size[1], size[0], 3), 128, np.uint8)) == []


def test_noise_on_a_big_screen_still_holds_nothing(scanner):
    rng = np.random.default_rng(1)
    assert scanner.scan(rng.integers(0, 256, (1080, 1920, 3), dtype=np.uint8)) == []


# -- reading in pieces ----------------------------------------------------------


@pytest.mark.parametrize("length", [1, 100, 3999, 4000, 4001, 5120, 7680, 12000])
def test_the_pieces_cover_everything_and_none_is_too_long(length):
    limit, overlap = 4000, 400
    runs = decode._spans(length, limit, overlap)
    assert runs[0][0] == 0 and runs[-1][1] == length
    assert all(b - a <= limit and b > a for a, b in runs)
    for (_, end), (start, _) in zip(runs, runs[1:], strict=False):
        assert start < end  # they overlap, so a code on a join lies whole in one


def test_a_short_frame_is_one_piece():
    assert decode._spans(1920, 4000, 400) == [(0, 1920)]


def test_no_piece_is_enlarged_past_the_cap(scanner, code, monkeypatch):
    """Whatever the screen, no single enlarged frame is bigger than the cap."""
    sizes = []
    real = scanner._robust_read

    def spy(image, scale=1.0):
        sizes.append(max(image.shape[:2]))
        return real(image, scale)

    monkeypatch.setattr(scanner, "_robust_read", spy)
    scanner.scan(np.full((600, 4600, 3), 128, np.uint8))
    assert sizes, "the big-frame step did not run"
    assert max(sizes) <= decode.BIG_FRAME_MAX_PX


def test_the_big_frame_step_only_runs_after_everything_else_finds_nothing(scanner, monkeypatch):
    """A frame with a normal code on it must not pay for the enlargement."""
    calls = []
    monkeypatch.setattr(scanner, "_enlarged_big_frame", lambda image: calls.append(1) or [])
    from tests.helpers.qr_synth import make_qr

    qr = make_qr("https://example.com/plain", size=240)
    screen = np.full((1080, 1920, 3), 255, np.uint8)
    h, w = qr.shape[:2]
    screen[100 : 100 + h, 100 : 100 + w] = qr
    assert [d.text for d in scanner.scan(screen)] == ["https://example.com/plain"]
    assert calls == []
