#include "card_paint.hpp"

#include <algorithm>
#include <cmath>

#include "link.hpp"

namespace uniqr::win {

namespace {

int px(double v, double scale) { return static_cast<int>(std::lround(v * scale)); }

SIZE measure(HDC dc, HFONT f, const std::wstring& s, int wrap) {
    HGDIOBJ old = SelectObject(dc, f);
    RECT r{0, 0, wrap, 0};
    const UINT flags = DT_CALCRECT | DT_NOPREFIX | (wrap > 0 ? (DT_WORDBREAK | DT_EDITCONTROL) : DT_SINGLELINE);
    DrawTextW(dc, s.c_str(), static_cast<int>(s.size()), &r, flags);
    SelectObject(dc, old);
    return SIZE{r.right - r.left, r.bottom - r.top};
}

std::wstring upper(std::wstring s) {
    for (auto& c : s) c = static_cast<wchar_t>(towupper(c));
    return s;
}

}  // namespace

CardPainter::CardPainter(std::string text, std::string status, std::vector<Button> buttons, double scale)
    : text_(std::move(text)), status_(std::move(status)), buttons_(std::move(buttons)), scale_(scale) {
    layout();
}

CardPainter::~CardPainter() {
    for (HFONT f : fonts_) DeleteObject(f);
}

HFONT CardPainter::font(int points, bool bold, bool mono) {
    // Points to pixels at this monitor's scale: 96 DPI is 4/3 pixels a point.
    const int height = -px(points * 96.0 / 72.0, scale_);
    HFONT f = CreateFontW(height, 0, 0, 0, bold ? FW_BOLD : FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                          OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH,
                          mono ? L"Consolas" : L"Segoe UI");
    fonts_.push_back(f);
    return f;
}

void CardPainter::layout() {
    HDC dc = GetDC(nullptr);
    const int pad_x = px(18, scale_), pad_y = px(15, scale_), wrap = px(380, scale_);
    int y = pad_y, width = 0;
    auto add = [&](const std::wstring& s, HFONT f, COLORREF c, int gap_above, bool wrapped) {
        y += gap_above;
        const SIZE sz = measure(dc, f, s, wrapped ? wrap : 0);
        lines_.push_back(Line{s, f, c, RECT{pad_x, y, pad_x + sz.cx, y + sz.cy}});
        y += sz.cy;
        width = std::max<int>(width, sz.cx);
    };

    if (text_.empty()) {
        add(widen(status_), font(10, true, false), colour::card_fg, 0, true);
    } else {
        // The kind of payload as a badge on the left, the status on the right.
        const std::string kind = payload_kind(text_);
        badge_text_ = upper(widen(kind_label(kind)));
        badge_font_ = font(7, true, false);
        const SIZE bs = measure(dc, badge_font_, badge_text_, 0);
        badge_ = RECT{pad_x, y, pad_x + bs.cx + px(16, scale_), y + bs.cy + px(4, scale_)};
        width = std::max<int>(width, badge_.right - pad_x);
        int header_bottom = badge_.bottom;
        if (!status_.empty()) {  // the picker's hover card has nothing to report yet
            HFONT status_font = font(9, true, false);
            const std::wstring status = L"✓ " + widen(status_);
            const SIZE ss = measure(dc, status_font, status, 0);
            const int status_x = badge_.right + px(24, scale_);
            lines_.push_back(Line{status, status_font, colour::ok, RECT{status_x, y, status_x + ss.cx, y + ss.cy}});
            width = std::max<int>(width, status_x + ss.cx - pad_x);
            header_bottom = std::max<int>(header_bottom, y + ss.cy);
        }
        y = header_bottom + px(8, scale_);

        std::vector<std::pair<std::string, bool>> notes;  // text, is a warning
        if (const auto link = describe_link(text_)) {
            add(widen(link->host), font(12, true, true), colour::card_fg, 0, true);
            if (link->rest != "" && link->rest != "/")
                add(widen(summarize(link->rest, 54)), font(9, false, true), colour::card_muted, px(2, scale_), false);
            for (const auto& w : link->warnings) notes.emplace_back(w, true);
        } else {
            add(widen(summarize(text_, 90)), font(10, false, false), colour::card_fg, 0, true);
            if (kind == "secret")
                notes.emplace_back("This is a login secret. Paste it only into your authenticator app.", true);
            notes.emplace_back("Not a web link, so UniQR won't open it.", false);
        }
        HFONT note_font = font(9, false, false);
        for (const auto& [note, warning] : notes)
            add(widen(warning ? "⚠ " + note : note), note_font, warning ? colour::warn : colour::card_muted,
                px(6, scale_), true);
    }

    if (!buttons_.empty()) {
        button_font_ = font(9, true, false);
        y += px(14, scale_);
        int x = pad_x, row_h = 0;
        for (auto& b : buttons_) {
            const SIZE ts = measure(dc, button_font_, b.label, 0);
            b.rect = RECT{x, y, x + ts.cx + px(28, scale_), y + ts.cy + px(12, scale_)};
            x = b.rect.right + px(8, scale_);
            row_h = std::max<int>(row_h, b.rect.bottom - b.rect.top);
        }
        width = std::max<int>(width, x - px(8, scale_) - pad_x);
        y += row_h;
    }
    size_ = SIZE{width + 2 * pad_x, y + pad_y};
    ReleaseDC(nullptr, dc);
}

void CardPainter::paint(HDC dc, POINT o, int hovered) const {
    const RECT whole{o.x, o.y, o.x + size_.cx, o.y + size_.cy};
    HBRUSH border = CreateSolidBrush(colour::card_border);
    FillRect(dc, &whole, border);
    DeleteObject(border);
    const RECT inner{whole.left + 1, whole.top + 1, whole.right - 1, whole.bottom - 1};
    HBRUSH bg = CreateSolidBrush(colour::card_bg);
    FillRect(dc, &inner, bg);
    DeleteObject(bg);
    SetBkMode(dc, TRANSPARENT);

    if (!badge_text_.empty()) {
        RECT b = badge_;
        OffsetRect(&b, o.x, o.y);
        HBRUSH raised = CreateSolidBrush(colour::card_raised);
        FillRect(dc, &b, raised);
        DeleteObject(raised);
        SelectObject(dc, badge_font_);
        SetTextColor(dc, colour::card_muted);
        DrawTextW(dc, badge_text_.c_str(), -1, &b, DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
    }
    for (const auto& line : lines_) {
        RECT r = line.rect;
        OffsetRect(&r, o.x, o.y);
        SelectObject(dc, line.font);
        SetTextColor(dc, line.colour);
        DrawTextW(dc, line.text.c_str(), static_cast<int>(line.text.size()), &r, DT_NOPREFIX | DT_WORDBREAK | DT_EDITCONTROL);
    }
    for (size_t i = 0; i < buttons_.size(); ++i) {
        const Button& btn = buttons_[i];
        RECT r = btn.rect;
        OffsetRect(&r, o.x, o.y);
        const bool hot = static_cast<int>(i) == hovered;
        HBRUSH fill = CreateSolidBrush(btn.primary ? (hot ? colour::accent_hover : colour::accent)
                                                   : (hot ? colour::button_hover : colour::button_bg));
        FillRect(dc, &r, fill);
        DeleteObject(fill);
        SelectObject(dc, button_font_);
        SetTextColor(dc, btn.primary ? colour::badge_text : colour::card_fg);
        DrawTextW(dc, btn.label.c_str(), -1, &r, DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
    }
}

int CardPainter::button_at(POINT p) const {
    for (size_t i = 0; i < buttons_.size(); ++i)
        if (PtInRect(&buttons_[i].rect, p)) return static_cast<int>(i);
    return -1;
}

POINT place_within(POINT anchor, SIZE size, const RECT& b, int margin, int flip_gap) {
    LONG x = std::max(std::min<LONG>(anchor.x, b.right - size.cx - margin), b.left + margin);
    LONG y = anchor.y;
    if (y + size.cy > b.bottom - margin) y = anchor.y - size.cy - flip_gap;
    y = std::max(std::min<LONG>(y, b.bottom - size.cy - margin), b.top + margin);
    return POINT{x, y};
}

}  // namespace uniqr::win
