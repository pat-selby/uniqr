// Seeing the screen: the whole virtual desktop (every monitor, in one grid of
// physical pixels) and the edges of the monitor a point is on.

#pragma once

#include "image.hpp"
#include "win.hpp"

namespace uniqr::win {

RECT virtual_screen();
// Every monitor, copied with GDI BitBlt into a BGR image. Empty on failure.
Image capture(const RECT& area);
// The usable part (no taskbar) of the monitor holding a point.
RECT work_area_at(POINT p);
// How much bigger than 96 DPI that monitor draws: 1.0, 1.25, 1.5 ...
double dpi_scale_at(POINT p);

}  // namespace uniqr::win
