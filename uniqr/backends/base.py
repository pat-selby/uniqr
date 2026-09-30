"""Types and contract shared by every platform backend.

A backend supplies screen geometry, a pixel grab, the pointer position, the
clipboard, and answers to three questions the OS alone can settle: how big a
captured pixel is on screen, and whether we are allowed to read the screen and
the keyboard at all. Everything else in UniQR - detection, the picker, the
result card - is written against these and does not care which OS is
underneath.

Two coordinate spaces run through the whole program, and mixing them up is
what puts highlight boxes next to codes instead of on them:

  screen points   what `Rect`, `cursor_pos` and window geometry all use. One
                  unit is one unit of whatever the OS calls a screen position.
  image pixels    what `grab` hands back, and therefore what a Detection's
                  quad and bbox are measured in.

`scale_factor()` is the ratio between them. It is 1.0 wherever the two agree -
Windows once DPI-aware, and any ordinary display - and 2.0 on a Retina Mac,
where a captured frame comes back at twice the size of the region asked for.
"""

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class Rect:
    """A screen region in screen points, in virtual-desktop coordinates."""

    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height


class Backend(Protocol):
    NAME: str

    def set_dpi_aware(self) -> None:
        """Opt out of OS display scaling, where the OS has such a thing."""

    def virtual_screen(self) -> Rect:
        """Bounding box of every monitor combined. Origin may be negative."""

    def grab(self, rect: Rect | None = None) -> np.ndarray:
        """Capture a region as a BGR array. None means every monitor."""

    def cursor_pos(self) -> tuple[int, int]:
        """Pointer position in the same coordinate space as virtual_screen."""

    def monitor_at(self, x: int, y: int) -> Rect:
        """Usable area of the monitor holding a point, or the nearest one.

        Excludes the taskbar where the OS reports it. Needed to keep cards
        on the monitor the code is on: toolkits such as Tk only report the
        primary screen's size.
        """

    def copy_text(self, text: str) -> None:
        """Replace the clipboard contents."""

    def round_corners(self, handle: int) -> None:
        """Ask the OS to draw a window with rounded corners, where it can.

        Cosmetic only: a platform without the option does nothing.
        """

    def scale_factor(self) -> float:
        """Image pixels per screen point. See the note at the top."""

    def probe(self) -> tuple[bool, str]:
        """Can we actually read the screen? (ok, human-readable detail)."""

    def input_status(self) -> tuple[bool | None, str]:
        """Will the OS deliver global key events? (answer, readable detail).

        True or False where the OS can be asked, None where there is nothing
        to ask - which is not the same as no, and callers must not treat it
        as a failure.
        """
