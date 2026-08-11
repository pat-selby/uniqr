"""Types and contract shared by every platform backend.

A backend supplies four things: screen geometry, a pixel grab, the pointer
position, and the clipboard. Everything else in UniQR - detection, the picker,
the result card - is written against these and does not care which OS is
underneath.
"""

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class Rect:
    """A screen region in physical pixels, in virtual-desktop coordinates."""

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

    def copy_text(self, text: str) -> None:
        """Replace the clipboard contents."""
