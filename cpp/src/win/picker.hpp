// Choosing one of several codes on screen.
//
// A see-through window is awkward on Windows, so the picker does what the
// Python one does: it shows the screenshot it already took, dimmed, with each
// code drawn back at full brightness and numbered. It looks like a spotlight but
// it is a picture. Hover a code for its card; click it or press its number to
// copy it; Esc or a click elsewhere cancels.

#pragma once

#include <vector>

#include "image.hpp"
#include "scanner.hpp"
#include "win.hpp"

namespace uniqr::win {

void register_picker_class(HINSTANCE instance);
// When done, posts WM_APP_PICKED to `notify`: wParam is the chosen index or -1,
// lParam is 1 when Open was chosen rather than Copy.
void show_picker(HINSTANCE instance, const Image& shot, const RECT& area, const std::vector<Detection>& found,
                 HWND notify);

}  // namespace uniqr::win
