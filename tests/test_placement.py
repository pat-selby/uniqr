"""Where result cards land on multi-monitor desktops.

The bug: cards were clamped against Tk's screen size, and Tk only knows the
primary monitor. A code on a second screen at x=2500 had its card dragged
back to the primary's right edge, on the wrong screen entirely.
"""

import pytest
from uniqr.backends import portable
from uniqr.backends.base import Rect
from uniqr.overlay import place_within

PRIMARY = Rect(left=0, top=0, width=1920, height=1020)
SECONDARY = Rect(left=1920, top=0, width=1920, height=1032)
LEFT_OF_PRIMARY = Rect(left=-1920, top=0, width=1920, height=1080)
CARD = (340, 130)


def inside(pos, size, bounds) -> bool:
    x, y = pos
    w, h = size
    return (
        x >= bounds.left and y >= bounds.top
        and x + w <= bounds.right and y + h <= bounds.bottom
    )


def test_regression_card_stays_on_the_secondary_monitor():
    """The reported case: code at x~2500 on the right-hand screen."""
    pos = place_within((2500, 620), CARD, SECONDARY)
    assert pos[0] >= SECONDARY.left, "card was dragged back to the primary"
    assert inside(pos, CARD, SECONDARY)


def test_card_near_the_right_edge_is_pulled_inside_its_own_monitor():
    pos = place_within((3800, 300), CARD, SECONDARY)
    assert inside(pos, CARD, SECONDARY)
    assert pos[0] == SECONDARY.right - CARD[0] - 8


def test_monitor_left_of_primary_keeps_negative_coordinates():
    """The old code floored x at 8, which threw these cards onto the primary."""
    pos = place_within((-1500, 400), CARD, LEFT_OF_PRIMARY)
    assert pos[0] < 0
    assert inside(pos, CARD, LEFT_OF_PRIMARY)


def test_unconstrained_card_sits_exactly_at_the_anchor():
    assert place_within((400, 300), CARD, PRIMARY) == (400, 300)


def test_card_that_would_run_off_the_bottom_flips_above():
    anchor = (400, 950)
    pos = place_within(anchor, CARD, PRIMARY)
    assert pos[1] < anchor[1]
    assert inside(pos, CARD, PRIMARY)


def test_card_wider_than_the_monitor_pins_to_the_left_margin():
    tiny = Rect(left=0, top=0, width=300, height=800)
    assert place_within((150, 100), (500, 100), tiny)[0] == 8


@pytest.mark.parametrize("anchor", [(0, 0), (1919, 1019), (960, 500), (-50, -50)])
def test_result_is_always_inside_the_monitor(anchor):
    assert inside(place_within(anchor, CARD, PRIMARY), CARD, PRIMARY)


# -- portable backend: choosing the monitor ---------------------------------


class _FakeSct:
    # mss convention: index 0 is every monitor combined, then one per display.
    monitors = [
        {"left": 0, "top": 0, "width": 3840, "height": 1080},
        {"left": 0, "top": 0, "width": 1920, "height": 1080},
        {"left": 1920, "top": 0, "width": 1920, "height": 1080},
    ]


@pytest.fixture
def fake_monitors(monkeypatch):
    monkeypatch.setattr(portable, "_sct", lambda: _FakeSct)


def test_portable_picks_the_monitor_containing_the_point(fake_monitors):
    assert portable.monitor_at(2500, 500).left == 1920
    assert portable.monitor_at(100, 500).left == 0


def test_portable_seam_pixel_belongs_to_the_right_monitor(fake_monitors):
    assert portable.monitor_at(1919, 500).left == 0
    assert portable.monitor_at(1920, 500).left == 1920


def test_portable_off_screen_point_falls_back_to_the_nearest(fake_monitors):
    assert portable.monitor_at(9000, 500).left == 1920
    assert portable.monitor_at(-500, 500).left == 0
