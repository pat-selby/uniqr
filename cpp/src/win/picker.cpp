#include "picker.hpp"

#include <algorithm>
#include <cmath>
#include <memory>
#include <string>

#include "capture.hpp"
#include "card_paint.hpp"
#include "link.hpp"

namespace uniqr::win {

namespace {

constexpr wchar_t kClass[] = L"UniQRCppPicker";
constexpr double kDim = 0.38;    // the screenshot's brightness behind the codes
constexpr int kHighlightPad = 10;

struct PickerState {
    RECT area{};                 // the captured area, in screen pixels
    std::vector<Detection> found;
    std::vector<RECT> boxes;     // each code's bright area, in window pixels
    HBITMAP base = nullptr;      // the dimmed screenshot with markers
    HWND notify = nullptr;
    double scale = 1;
    int hover = -1;              // the code the pointer is on
    int hover_button = -1;
    std::unique_ptr<CardPainter> card;
    POINT card_at{};
    bool done = false;
};

PickerState* state_of(HWND hwnd) { return reinterpret_cast<PickerState*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA)); }

void finish(HWND hwnd, PickerState* s, int index, bool open) {
    if (s->done) return;
    s->done = true;
    PostMessageW(s->notify, WM_APP_PICKED, static_cast<WPARAM>(index), open ? 1 : 0);
    DestroyWindow(hwnd);
}

int code_at(const PickerState* s, POINT p) {
    for (size_t i = 0; i < s->boxes.size(); ++i)
        if (PtInRect(&s->boxes[i], p)) return static_cast<int>(i);
    return -1;
}

void set_hover(HWND hwnd, PickerState* s, int index) {
    if (index == s->hover) return;
    s->hover = index;
    s->hover_button = -1;
    s->card.reset();
    if (index >= 0) {
        const Detection& d = s->found[index];
        std::vector<Button> buttons;
        if (can_open(d.text)) buttons.push_back(Button{L"Open", true});
        buttons.push_back(Button{L"Copy", false});
        s->card = std::make_unique<CardPainter>(d.text, "", std::move(buttons), s->scale);
        // Under the code, kept inside the monitor it is on, then into window pixels.
        const RECT& box = s->boxes[index];
        const POINT anchor{s->area.left + box.left, s->area.top + box.bottom + 16};
        RECT bounds = work_area_at(anchor);
        const POINT at = place_within(anchor, s->card->size(), bounds);
        s->card_at = POINT{at.x - s->area.left, at.y - s->area.top};
    }
    InvalidateRect(hwnd, nullptr, FALSE);
}

HBITMAP render_base(const Image& shot, const PickerState& s) {
    // Dim everything, then put each code's area back at full brightness.
    BITMAPINFO bi{};
    bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bi.bmiHeader.biWidth = shot.width;
    bi.bmiHeader.biHeight = -shot.height;
    bi.bmiHeader.biPlanes = 1;
    bi.bmiHeader.biBitCount = 32;
    bi.bmiHeader.biCompression = BI_RGB;
    void* bits = nullptr;
    HBITMAP bmp = CreateDIBSection(nullptr, &bi, DIB_RGB_COLORS, &bits, nullptr, 0);
    if (!bmp) return nullptr;
    auto* px = static_cast<uint8_t*>(bits);
    for (int y = 0; y < shot.height; ++y)
        for (int x = 0; x < shot.width; ++x) {
            bool bright = false;
            for (const RECT& b : s.boxes)
                if (x >= b.left && x < b.right && y >= b.top && y < b.bottom) {
                    bright = true;
                    break;
                }
            const double k = bright ? 1.0 : kDim;
            uint8_t* o = px + (static_cast<size_t>(y) * shot.width + x) * 4;
            for (int c = 0; c < 3; ++c) o[c] = static_cast<uint8_t>(shot.at(x, y, c) * k);
            o[3] = 255;
        }

    // Outline each code and number it.
    HDC dc = CreateCompatibleDC(nullptr);
    HGDIOBJ old = SelectObject(dc, bmp);
    HPEN pen = CreatePen(PS_SOLID, std::max(2, static_cast<int>(std::lround(3 * s.scale))), colour::accent);
    HBRUSH badge = CreateSolidBrush(colour::accent);
    const int r = static_cast<int>(std::lround(15 * s.scale));
    HFONT font = CreateFontW(-static_cast<int>(std::lround(16 * s.scale)), 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
                             DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH,
                             L"Segoe UI");
    SetBkMode(dc, TRANSPARENT);
    for (size_t i = 0; i < s.found.size(); ++i) {
        POINT poly[4];
        for (int k = 0; k < 4; ++k)
            poly[k] = POINT{static_cast<LONG>(s.found[i].quad[k].x), static_cast<LONG>(s.found[i].quad[k].y)};
        HGDIOBJ op = SelectObject(dc, pen), ob = SelectObject(dc, GetStockObject(NULL_BRUSH));
        Polygon(dc, poly, 4);
        SelectObject(dc, op);
        SelectObject(dc, ob);
        if (i >= 9) continue;  // only 1 to 9 have a key
        const Box b = s.found[i].bbox();
        const int cx = b.left - 6, cy = b.top - 6;
        HGDIOBJ ob2 = SelectObject(dc, badge), op2 = SelectObject(dc, GetStockObject(NULL_PEN));
        Ellipse(dc, cx - r, cy - r, cx + r, cy + r);
        SelectObject(dc, ob2);
        SelectObject(dc, op2);
        RECT tr{cx - r, cy - r, cx + r, cy + r};
        SelectObject(dc, font);
        SetTextColor(dc, colour::badge_text);
        const std::wstring n = std::to_wstring(i + 1);
        DrawTextW(dc, n.c_str(), -1, &tr, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    }
    // What to do, across the top.
    const size_t count = s.found.size();
    const std::wstring hint = std::to_wstring(count) + (count == 1 ? L" QR code" : L" QR codes") +
                              L" found  -  hover to inspect, press 1-" + std::to_wstring(std::min<size_t>(count, 9)) +
                              L" to copy, Esc to cancel";
    HFONT hint_font = CreateFontW(-static_cast<int>(std::lround(16 * s.scale)), 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
                                  DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
                                  DEFAULT_PITCH, L"Segoe UI");
    SelectObject(dc, hint_font);
    SetTextColor(dc, colour::card_fg);
    const RECT primary = work_area_at(POINT{0, 0});
    RECT hr{primary.left - s.area.left, static_cast<LONG>(primary.top - s.area.top + 14 * s.scale),
            primary.right - s.area.left, static_cast<LONG>(primary.top - s.area.top + 44 * s.scale)};
    DrawTextW(dc, hint.c_str(), -1, &hr, DT_CENTER | DT_SINGLELINE | DT_NOPREFIX);

    SelectObject(dc, old);
    DeleteObject(pen);
    DeleteObject(badge);
    DeleteObject(font);
    DeleteObject(hint_font);
    DeleteDC(dc);
    return bmp;
}

LRESULT CALLBACK picker_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    PickerState* s = state_of(hwnd);
    switch (msg) {
        case WM_NCCREATE:
            SetWindowLongPtrW(hwnd, GWLP_USERDATA,
                              reinterpret_cast<LONG_PTR>(reinterpret_cast<CREATESTRUCTW*>(lp)->lpCreateParams));
            return TRUE;
        case WM_ERASEBKGND:
            return 1;  // everything is painted in WM_PAINT, without flicker
        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC dc = BeginPaint(hwnd, &ps);
            if (s && s->base) {
                RECT client;
                GetClientRect(hwnd, &client);
                // Draw into memory first, then copy once, so the card never flickers.
                HDC mem = CreateCompatibleDC(dc);
                HBITMAP frame = CreateCompatibleBitmap(dc, client.right, client.bottom);
                HGDIOBJ old = SelectObject(mem, frame);
                HDC src = CreateCompatibleDC(dc);
                HGDIOBJ old_src = SelectObject(src, s->base);
                BitBlt(mem, 0, 0, client.right, client.bottom, src, 0, 0, SRCCOPY);
                SelectObject(src, old_src);
                DeleteDC(src);
                if (s->card) s->card->paint(mem, s->card_at, s->hover_button);
                BitBlt(dc, 0, 0, client.right, client.bottom, mem, 0, 0, SRCCOPY);
                SelectObject(mem, old);
                DeleteObject(frame);
                DeleteDC(mem);
            }
            EndPaint(hwnd, &ps);
            return 0;
        }
        case WM_MOUSEMOVE: {
            if (!s) break;
            const POINT p{static_cast<short>(LOWORD(lp)), static_cast<short>(HIWORD(lp))};
            if (s->card) {
                const POINT rel{p.x - s->card_at.x, p.y - s->card_at.y};
                const RECT card{s->card_at.x, s->card_at.y, s->card_at.x + s->card->size().cx,
                                s->card_at.y + s->card->size().cy};
                if (PtInRect(&card, p)) {  // on the card: keep it, track its buttons
                    const int hot = s->card->button_at(rel);
                    if (hot != s->hover_button) {
                        s->hover_button = hot;
                        InvalidateRect(hwnd, nullptr, FALSE);
                    }
                    return 0;
                }
            }
            set_hover(hwnd, s, code_at(s, p));
            return 0;
        }
        case WM_LBUTTONUP: {
            if (!s) break;
            const POINT p{static_cast<short>(LOWORD(lp)), static_cast<short>(HIWORD(lp))};
            if (s->card && s->hover >= 0) {
                const int hit = s->card->button_at(POINT{p.x - s->card_at.x, p.y - s->card_at.y});
                if (hit >= 0) {
                    finish(hwnd, s, s->hover, s->card->buttons()[hit].label == L"Open");
                    return 0;
                }
                const RECT card{s->card_at.x, s->card_at.y, s->card_at.x + s->card->size().cx,
                                s->card_at.y + s->card->size().cy};
                if (PtInRect(&card, p)) return 0;  // a click on the card itself does nothing
            }
            finish(hwnd, s, code_at(s, p), false);  // a code copies; anywhere else cancels
            return 0;
        }
        case WM_KEYDOWN:
            if (!s) break;
            if (wp == VK_ESCAPE) finish(hwnd, s, -1, false);
            else if (wp >= '1' && wp <= '9' && static_cast<size_t>(wp - '1') < s->found.size())
                finish(hwnd, s, static_cast<int>(wp - '1'), false);
            else if (wp >= VK_NUMPAD1 && wp <= VK_NUMPAD9 && static_cast<size_t>(wp - VK_NUMPAD1) < s->found.size())
                finish(hwnd, s, static_cast<int>(wp - VK_NUMPAD1), false);
            return 0;
        case WM_ACTIVATE:
            // Someone switched away (Alt+Tab): treat it as cancel, never leave a
            // full-screen window stranded on top.
            if (s && LOWORD(wp) == WA_INACTIVE) finish(hwnd, s, -1, false);
            return 0;
        case WM_NCDESTROY:
            if (s) {
                if (!s->done) PostMessageW(s->notify, WM_APP_PICKED, static_cast<WPARAM>(-1), 0);
                if (s->base) DeleteObject(s->base);
                delete s;
            }
            SetWindowLongPtrW(hwnd, GWLP_USERDATA, 0);
            return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

}  // namespace

void register_picker_class(HINSTANCE instance) {
    WNDCLASSEXW wc{sizeof(wc)};
    wc.lpfnWndProc = picker_proc;
    wc.hInstance = instance;
    wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    wc.lpszClassName = kClass;
    RegisterClassExW(&wc);
}

void show_picker(HINSTANCE instance, const Image& shot, const RECT& area, const std::vector<Detection>& found,
                 HWND notify) {
    auto s = std::make_unique<PickerState>();
    s->area = area;
    s->found = found;
    s->notify = notify;
    s->scale = dpi_scale_at(POINT{area.left, area.top});
    const int pad = static_cast<int>(std::lround(kHighlightPad * s->scale));
    for (const auto& d : found) {
        const Box b = d.bbox();
        s->boxes.push_back(RECT{b.left - pad, b.top - pad, b.left + b.width + pad, b.top + b.height + pad});
    }
    s->base = render_base(shot, *s);
    HWND hwnd = CreateWindowExW(WS_EX_TOPMOST | WS_EX_TOOLWINDOW, kClass, L"UniQR picker", WS_POPUP, area.left,
                                area.top, area.right - area.left, area.bottom - area.top, nullptr, nullptr, instance,
                                s.release());
    if (!hwnd) {
        PostMessageW(notify, WM_APP_PICKED, static_cast<WPARAM>(-1), 0);
        return;
    }
    ShowWindow(hwnd, SW_SHOW);
    SetForegroundWindow(hwnd);
    SetFocus(hwnd);
}

}  // namespace uniqr::win
