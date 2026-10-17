// Laying out and drawing a result card, with GDI.
//
// The same card is a window of its own after a scan, and is drawn inside the
// picker when the pointer rests on a code. The layout matches the Python
// version's: the part that decides safety reads first. For a link that is the
// real host, in large fixed-width type (lookalikes like "rn" for "m" are easier
// to spot), with the rest of the address dimmed beneath it and any warning in
// amber. Only the Open button opens anything.

#pragma once

#include <string>
#include <vector>

#include "win.hpp"

namespace uniqr::win {

struct Button {
    std::wstring label;
    bool primary = false;
    RECT rect{};  // relative to the card's top-left, filled in by layout
};

class CardPainter {
public:
    // `text` is the payload, or empty for a card that only says `status`.
    CardPainter(std::string text, std::string status, std::vector<Button> buttons, double scale);
    ~CardPainter();
    CardPainter(const CardPainter&) = delete;
    CardPainter& operator=(const CardPainter&) = delete;

    SIZE size() const { return size_; }
    void paint(HDC dc, POINT origin, int hovered_button) const;
    int button_at(POINT relative) const;  // -1 if none
    const std::vector<Button>& buttons() const { return buttons_; }

private:
    struct Line {
        std::wstring text;
        HFONT font;
        COLORREF colour;
        RECT rect;  // relative to the card
    };
    void layout();
    HFONT font(int points, bool bold, bool mono);

    std::string text_, status_;
    std::vector<Button> buttons_;
    double scale_;
    std::vector<HFONT> fonts_;
    std::vector<Line> lines_;
    RECT badge_{};
    std::wstring badge_text_;
    HFONT badge_font_ = nullptr, button_font_ = nullptr;
    SIZE size_{};
};

// Keep a card of `size` near `anchor`, inside the monitor holding the anchor:
// flipped above the anchor if it would run off the bottom.
POINT place_within(POINT anchor, SIZE size, const RECT& bounds, int margin = 8, int flip_gap = 24);

}  // namespace uniqr::win
