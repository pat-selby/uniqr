"""A scan has a time limit, and a checkerboard no longer takes minutes.

A 1920x1080 checkerboard of 10 pixel squares took about 100 seconds to scan and
come back empty. OpenCV's Aruco detector needs 18 to 26 seconds for one call on
it, a scan makes a dozen, the scan runs on the main thread, and the watchdog
restarts the app after 45 seconds without a heartbeat.

These tests use a 960x540 board, which took about 30 seconds before the fix, so
the suite stays fast.
"""

import threading
import time

import cv2
import numpy as np
import pytest
from tests.helpers.qr_synth import make_qr
from uniqr import decode

TEXT = "https://example.com/uniqr-test"


def checkerboard(cell: int, height: int = 540, width: int = 960) -> np.ndarray:
    yy, xx = np.indices((height, width))
    grey = (((yy // cell) + (xx // cell)) % 2 * 255).astype(np.uint8)
    return cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR)


class Tripwire:
    """Stands in for a detector and counts how often it is used."""

    def __init__(self) -> None:
        self.calls = 0

    def detectAndDecodeMulti(self, image):  # noqa: N802 - OpenCV's name
        self.calls += 1
        return False, [], None, None

    def detectMulti(self, image):  # noqa: N802
        self.calls += 1
        return False, None

    def detectAndDecode(self, image):  # noqa: N802
        self.calls += 1
        return "", None, None


class Stuck(Tripwire):
    """A detector that does not come back for a while, as OpenCV's can."""

    def __init__(self, seconds: float) -> None:
        super().__init__()
        self.seconds = seconds

    def detectAndDecodeMulti(self, image):  # noqa: N802
        time.sleep(self.seconds)
        return super().detectAndDecodeMulti(image)

    def detectMulti(self, image):  # noqa: N802
        time.sleep(self.seconds)
        return super().detectMulti(image)

    def detectAndDecode(self, image):  # noqa: N802
        time.sleep(self.seconds)
        return super().detectAndDecode(image)


# -- telling a pattern from a picture --------------------------------------------


def test_a_checkerboard_counts_as_repetitive():
    assert decode._repeat_count(checkerboard(10)) > decode.ARUCO_MAX_REPEAT


def test_a_ruled_grid_counts_as_repetitive():
    grid = np.full((540, 960, 3), 255, np.uint8)
    grid[::10, :] = 0
    grid[:, ::10] = 0
    assert decode._repeat_count(grid) > decode.ARUCO_MAX_REPEAT


def test_ordinary_frames_are_nowhere_near_the_line():
    noise = np.random.default_rng(0).integers(0, 256, (540, 960, 3), dtype=np.uint8)
    for frame in (make_qr(TEXT), make_qr(TEXT, size=500), noise, np.full((540, 960, 3), 255, np.uint8)):
        assert decode._repeat_count(frame) < decode.ARUCO_MAX_REPEAT / 4


def test_squares_too_small_for_aruco_to_care_about_do_not_count():
    """9 px squares cost Aruco 0.05 s on 1080p, and 10 px squares 18 s."""
    assert decode._repeat_count(checkerboard(4, 1080, 1920)) == 0
    assert decode._repeat_count(checkerboard(10, 1080, 1920)) > decode.ARUCO_MAX_REPEAT


# -- a scan of a pattern -----------------------------------------------------------


def test_a_checkerboard_never_reaches_aruco():
    """Not the first read, not the stylised retries, not the locator."""
    scanner = decode.Scanner()
    tripwire = Tripwire()
    scanner._aruco = tripwire
    assert scanner.scan(checkerboard(10)) == []
    assert tripwire.calls == 0


def test_a_checkerboard_scan_is_quick(scanner):
    started = time.perf_counter()
    assert scanner.scan(checkerboard(10)) == []
    assert time.perf_counter() - started < 10  # about 30 s before, and 100 s at 1080p
    assert not scanner.timed_out


def test_an_ordinary_frame_still_uses_aruco():
    scanner = decode.Scanner()
    tripwire = Tripwire()
    scanner._aruco = tripwire
    scanner.scan(np.full((540, 960, 3), 128, np.uint8))
    assert tripwire.calls > 0


def test_a_code_on_a_checkerboard_is_still_read(scanner):
    board = checkerboard(10)
    code = make_qr(TEXT, size=160, pad=20)
    h, w = code.shape[:2]
    board[100 : 100 + h, 300 : 300 + w] = code
    started = time.perf_counter()
    assert [d.text for d in scanner.scan(board)] == [TEXT]
    assert time.perf_counter() - started < 10


def test_the_verdict_does_not_outlive_the_scan():
    scanner = decode.Scanner()
    scanner.scan(checkerboard(10))
    assert scanner._aruco_allowed is None
    assert scanner._repeat_checked is None  # it would hold a whole frame


# -- the budget ----------------------------------------------------------------------


def test_a_scan_gives_up_on_a_detector_that_does_not_come_back():
    scanner = decode.Scanner()
    scanner._classic = Stuck(4)
    blank = np.full((300, 300, 3), 255, np.uint8)

    started = time.perf_counter()
    assert scanner.scan(blank, budget=0.3) == []
    assert time.perf_counter() - started < 2
    assert scanner.timed_out

    # The stuck one is replaced, so the next scan does not meet it again.
    assert not isinstance(scanner._classic, Stuck)
    assert scanner.scan(blank) == []
    assert not scanner.timed_out


@pytest.mark.skipif(not decode.zxing_available(), reason="the first read is zxing's")
def test_a_scan_out_of_time_still_returns_what_the_first_read_found():
    scanner = decode.Scanner()
    found = scanner.scan(make_qr(TEXT), budget=0)
    assert [d.text for d in found] == [TEXT]
    assert scanner.timed_out


def test_no_budget_means_no_limit():
    scanner = decode.Scanner()
    assert [d.text for d in scanner.scan(make_qr(TEXT), budget=None)] == [TEXT]
    assert not scanner.timed_out


def test_a_scan_inside_its_budget_does_not_report_a_timeout(scanner):
    assert [d.text for d in scanner.scan(make_qr(TEXT))] == [TEXT]
    assert not scanner.timed_out


def test_the_default_budget_is_well_inside_the_watchdog():
    from uniqr import watchdog

    assert decode.SCAN_BUDGET_S <= watchdog.HANG_AFTER
    assert decode.SCAN_BUDGET_S < watchdog.RESTART_AFTER / 2


# -- giving up on a call ---------------------------------------------------------------


def test_a_guarded_call_returns_its_value_and_raises_its_error():
    scanner = decode.Scanner()
    scanner._deadline = time.monotonic() + 5
    assert scanner._guarded(lambda: 7, None) == 7
    with pytest.raises(ZeroDivisionError):
        scanner._guarded(lambda: 1 / 0, None)
    assert not scanner.timed_out


def test_a_guarded_call_that_overruns_is_given_up_on():
    scanner = decode.Scanner()
    scanner._deadline = time.monotonic() + 0.2
    started = time.perf_counter()
    assert scanner._guarded(lambda: time.sleep(3), "gave up") == "gave up"
    assert time.perf_counter() - started < 2
    assert scanner.timed_out


def test_given_up_calls_do_not_pile_up():
    scanner = decode.Scanner()
    scanner._deadline = time.monotonic() + 5
    release = threading.Event()
    scanner._abandoned = [
        threading.Thread(target=release.wait, daemon=True)
        for _ in range(decode.MAX_ABANDONED_CALLS)
    ]
    for thread in scanner._abandoned:
        thread.start()
    ran = []
    try:
        assert scanner._guarded(lambda: ran.append(1), "skipped") == "skipped"
        assert ran == []
        assert scanner.timed_out
    finally:
        release.set()
