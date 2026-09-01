"""Unit tests for the tiled pass geometry.

A fixed 3x3 grid shipped a real bug: on a 579x381 frame it produced tiles
158px tall while the code in it was 215px, so no tile could ever contain the
code and the pass that exists to isolate codes was guaranteed to fail.
"""

import pytest
from uniqr.decode import TILE_GRID, TILE_MIN_PX, _tile_rects, tile_grid_for


def sizes(width: int, height: int) -> list[tuple[int, int]]:
    return [(x1 - x0, y1 - y0) for x0, y0, x1, y1 in _tile_rects(width, height)]


@pytest.mark.parametrize(
    "width,height,expected",
    [
        (1920, 1080, 3),   # a full screen splits fully
        (2560, 1440, 3),   # and never beyond the cap
        (579, 381, 1),     # the frame that exposed the bug
        (400, 400, 1),     # too small to split usefully
        (800, 800, 2),     # mid-size gets an intermediate grid
    ],
)
def test_grid_adapts_to_frame(width, height, expected):
    assert tile_grid_for(width, height) == expected


def test_grid_never_exceeds_cap():
    assert tile_grid_for(10_000, 10_000) == TILE_GRID


def test_grid_is_at_least_one():
    """A frame smaller than one tile still has to produce a usable tile."""
    assert tile_grid_for(50, 40) == 1
    assert len(_tile_rects(50, 40)) == 1


@pytest.mark.parametrize(
    "width,height", [(1920, 1080), (579, 381), (800, 800), (1280, 720)]
)
def test_tiles_are_large_enough_to_hold_a_code(width, height):
    """Every tile must be at least as big as the smallest useful tile.

    Splitting past this point slices codes across tile boundaries, which is
    the failure this geometry exists to prevent.
    """
    grid = tile_grid_for(width, height)
    if grid == 1:
        return  # single tile is the whole frame by definition
    for tile_w, tile_h in sizes(width, height):
        assert min(tile_w, tile_h) >= TILE_MIN_PX


def test_regression_579x381_tile_can_contain_a_215px_code():
    """The exact case from the CodeSignal card."""
    code_px = 215
    for tile_w, tile_h in sizes(579, 381):
        if tile_w >= code_px and tile_h >= code_px:
            return
    pytest.fail("no tile can contain the code, which is the original bug")


@pytest.mark.parametrize("width,height", [(1920, 1080), (579, 381), (640, 480)])
def test_tiles_cover_the_whole_frame(width, height):
    rects = _tile_rects(width, height)
    assert min(x0 for x0, _, _, _ in rects) == 0
    assert min(y0 for _, y0, _, _ in rects) == 0
    assert max(x1 for _, _, x1, _ in rects) == width
    assert max(y1 for _, _, _, y1 in rects) == height


def test_tiles_overlap_so_codes_on_a_seam_survive():
    """Neighbouring tiles must share area, or a code on the seam is lost."""
    rects = _tile_rects(1920, 1080, grid=3)
    row = sorted([r for r in rects if r[1] == 0], key=lambda r: r[0])
    assert len(row) == 3
    first, second = row[0], row[1]
    assert first[2] > second[0], "adjacent tiles do not overlap"


def test_tile_rects_respects_an_explicit_grid():
    assert len(_tile_rects(1920, 1080, grid=2)) == 4
    assert len(_tile_rects(1920, 1080, grid=3)) == 9
