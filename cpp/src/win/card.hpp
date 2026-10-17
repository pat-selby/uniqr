// A small card near a code: what was read, with Open and Dismiss.
//
// The card is its own window, not a system notification, so Do Not Disturb
// cannot hide it, and it appears at the code rather than in a corner. Unlike
// the Python version it does not hold up the program while it is shown.

#pragma once

#include <functional>
#include <string>

#include "win.hpp"

namespace uniqr::win {

struct CardOptions {
    int timeout_ms = 2200;     // closes by itself after this long
    bool hover_pause = true;   // a pointer on the card stops the clock
    bool offer_open = true;    // an Open button for a web link
};

void register_card_class(HINSTANCE instance);
// `on_open` runs when Open is pressed.
void show_card(HINSTANCE instance, const std::string& text, const std::string& status, POINT anchor,
               const CardOptions& options = {}, std::function<void()> on_open = {});

}  // namespace uniqr::win
