"""A coloured code that grey flattens, on a screen that also holds other codes.

UniQR's README picture shows six coloured codes. Scanned off the screen at the
zoom a browser uses, the navy-on-crimson one was missed. Navy and crimson are
both dark, so in grey they nearly match. In the red channel alone they are far
apart: crimson is mostly red, navy has almost none.

The red channel was already tried, but only on spots the locator had marked as
a code, and at these sizes it did not mark this one. The later fallback steps
run only when nothing at all was found, and the other five codes meant
something was. So a whole-screen read of the red channel now runs with the
first, cheap pass.

The fixture is a frame of the old README animation, which includes the
picker's dimmed background. Its teal dotted code stays unreadable: its dots are
about three pixels wide there, and the detail is gone from the image.
"""

from pathlib import Path

import cv2
import pytest
from uniqr.decode import Scanner

FIXTURE = Path(__file__).parent / "fixtures" / "colour_codes_in_old_demo.png"
CRIMSON = "https://uniqr.dev/crimson"
OTHERS = {
    "https://uniqr.dev/plain",
    "https://uniqr.dev/inverted",
    "https://uniqr.dev/green",
    "https://uniqr.dev/purple",
}


@pytest.fixture(scope="module")
def picture():
    image = cv2.imread(str(FIXTURE))
    assert image is not None
    return image


# Resized smoothly, as a browser draws a zoomed image. A harsh resize at exactly
# 1.5x alternates 1- and 2-pixel modules and defeats every reader tried.
@pytest.mark.parametrize("zoom", [1.0, 1.16, 1.25, 1.4, 1.5, 1.75])
def test_the_navy_on_crimson_code_is_read_beside_the_others(scanner, picture, zoom):
    image = picture if zoom == 1.0 else cv2.resize(picture, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_CUBIC)
    found = {d.text for d in scanner.scan(image)}
    assert CRIMSON in found
    assert found >= OTHERS


def test_a_grey_screenshot_gains_nothing_and_loses_nothing(scanner):
    """Without colour the red channel is the grey image again: same answer."""
    image = cv2.cvtColor(cv2.cvtColor(cv2.imread(str(FIXTURE)), cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    found = {d.text for d in scanner.scan(image)}
    assert found >= {"https://uniqr.dev/plain", "https://uniqr.dev/inverted"}
    assert all(text.startswith("https://uniqr.dev/") for text in found)


def test_it_does_not_invent_codes_on_a_plain_red_screen(scanner):
    import numpy as np

    red = np.zeros((600, 900, 3), np.uint8)
    red[..., 2] = 200
    assert Scanner().scan(red) == []
