#include "card.hpp"

#include <dwmapi.h>

#include <memory>

#include "capture.hpp"
#include "card_paint.hpp"
#include "link.hpp"

namespace uniqr::win {

namespace {

constexpr wchar_t kClass[] = L"UniQRCppCard";
constexpr UINT_PTR kCloseTimer = 1;
constexpr int kAfterHoverMs = 700;  // someone who hovered has read it

struct CardState {
    std::unique_ptr<CardPainter> painter;
    CardOptions options;
    std::function<void()> on_open;
    int hovered = -1;
    bool tracking = false;
};

CardState* state_of(HWND hwnd) { return reinterpret_cast<CardState*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA)); }

LRESULT CALLBACK card_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    CardState* s = state_of(hwnd);
    switch (msg) {
        case WM_NCCREATE:
            SetWindowLongPtrW(hwnd, GWLP_USERDATA,
                              reinterpret_cast<LONG_PTR>(reinterpret_cast<CREATESTRUCTW*>(lp)->lpCreateParams));
            return TRUE;
        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC dc = BeginPaint(hwnd, &ps);
            if (s) s->painter->paint(dc, POINT{0, 0}, s->hovered);
            EndPaint(hwnd, &ps);
            return 0;
        }
        case WM_MOUSEMOVE: {
            if (!s) break;
            if (!s->tracking) {
                TRACKMOUSEEVENT t{sizeof(t), TME_LEAVE, hwnd, 0};
                TrackMouseEvent(&t);
                s->tracking = true;
                if (s->options.hover_pause) KillTimer(hwnd, kCloseTimer);
            }
            const int hot = s->painter->button_at(POINT{static_cast<short>(LOWORD(lp)), static_cast<short>(HIWORD(lp))});
            if (hot != s->hovered) {
                s->hovered = hot;
                InvalidateRect(hwnd, nullptr, FALSE);
            }
            return 0;
        }
        case WM_MOUSELEAVE:
            if (!s) break;
            s->tracking = false;
            s->hovered = -1;
            InvalidateRect(hwnd, nullptr, FALSE);
            if (s->options.hover_pause) SetTimer(hwnd, kCloseTimer, kAfterHoverMs, nullptr);
            return 0;
        case WM_SETCURSOR:
            if (s && s->hovered >= 0) {
                SetCursor(LoadCursorW(nullptr, IDC_HAND));
                return TRUE;
            }
            break;
        case WM_LBUTTONUP: {
            if (!s) break;
            const int hit = s->painter->button_at(POINT{static_cast<short>(LOWORD(lp)), static_cast<short>(HIWORD(lp))});
            if (hit < 0) return 0;
            if (s->painter->buttons()[hit].label == L"Open" && s->on_open) s->on_open();
            DestroyWindow(hwnd);
            return 0;
        }
        case WM_TIMER:
            if (wp == kCloseTimer) DestroyWindow(hwnd);
            return 0;
        case WM_MOUSEACTIVATE:
            return MA_NOACTIVATE;  // a click on the card must not steal focus
        case WM_NCDESTROY:
            delete s;
            SetWindowLongPtrW(hwnd, GWLP_USERDATA, 0);
            return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

}  // namespace

void register_card_class(HINSTANCE instance) {
    WNDCLASSEXW wc{sizeof(wc)};
    wc.lpfnWndProc = card_proc;
    wc.hInstance = instance;
    wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    wc.lpszClassName = kClass;
    RegisterClassExW(&wc);
}

void show_card(HINSTANCE instance, const std::string& text, const std::string& status, POINT anchor,
               const CardOptions& options, std::function<void()> on_open) {
    std::vector<Button> buttons;
    if (!text.empty() && options.offer_open && can_open(text)) buttons.push_back(Button{L"Open", true});
    buttons.push_back(Button{L"Dismiss", false});
    auto state = std::make_unique<CardState>();
    state->painter = std::make_unique<CardPainter>(text, status, std::move(buttons), dpi_scale_at(anchor));
    state->options = options;
    state->on_open = std::move(on_open);
    const SIZE size = state->painter->size();
    const POINT at = place_within(anchor, size, work_area_at(anchor));

    HWND hwnd = CreateWindowExW(WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE, kClass, L"UniQR", WS_POPUP, at.x,
                                at.y, size.cx, size.cy, nullptr, nullptr, instance, state.release());
    if (!hwnd) return;
    // Rounded corners on Windows 11; ignored on older versions.
    const DWORD round = 2;  // DWMWCP_ROUND
    DwmSetWindowAttribute(hwnd, 33 /* DWMWA_WINDOW_CORNER_PREFERENCE */, &round, sizeof(round));
    ShowWindow(hwnd, SW_SHOWNOACTIVATE);
    SetTimer(hwnd, kCloseTimer, options.timeout_ms, nullptr);
}

}  // namespace uniqr::win
