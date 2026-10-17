#include "capture.hpp"  // brings windows.h first

#include <shellscalingapi.h>

namespace uniqr::win {

RECT virtual_screen() {
    // The process is per-monitor DPI aware (see the manifest), so these are
    // physical pixels: a code is captured at full sharpness on a scaled display.
    const int x = GetSystemMetrics(SM_XVIRTUALSCREEN), y = GetSystemMetrics(SM_YVIRTUALSCREEN);
    return RECT{x, y, x + GetSystemMetrics(SM_CXVIRTUALSCREEN), y + GetSystemMetrics(SM_CYVIRTUALSCREEN)};
}

Image capture(const RECT& area) {
    const int w = area.right - area.left, h = area.bottom - area.top;
    if (w <= 0 || h <= 0) return {};
    HDC screen = GetDC(nullptr);
    HDC mem = CreateCompatibleDC(screen);
    BITMAPINFO bi{};
    bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bi.bmiHeader.biWidth = w;
    bi.bmiHeader.biHeight = -h;  // top-down rows
    bi.bmiHeader.biPlanes = 1;
    bi.bmiHeader.biBitCount = 32;
    bi.bmiHeader.biCompression = BI_RGB;
    void* bits = nullptr;
    HBITMAP dib = CreateDIBSection(screen, &bi, DIB_RGB_COLORS, &bits, nullptr, 0);
    Image out;
    if (dib && bits) {
        HGDIOBJ old = SelectObject(mem, dib);
        if (BitBlt(mem, 0, 0, w, h, screen, area.left, area.top, SRCCOPY | CAPTUREBLT)) {
            out = Image(w, h, 3);
            const auto* src = static_cast<const uint8_t*>(bits);
            for (size_t i = 0, n = static_cast<size_t>(w) * h; i < n; ++i) {
                out.pixels[3 * i] = src[4 * i];          // blue
                out.pixels[3 * i + 1] = src[4 * i + 1];  // green
                out.pixels[3 * i + 2] = src[4 * i + 2];  // red
            }
        }
        SelectObject(mem, old);
        DeleteObject(dib);
    }
    DeleteDC(mem);
    ReleaseDC(nullptr, screen);
    return out;
}

RECT work_area_at(POINT p) {
    MONITORINFO mi{sizeof(mi)};
    GetMonitorInfoW(MonitorFromPoint(p, MONITOR_DEFAULTTONEAREST), &mi);
    return mi.rcWork;
}

double dpi_scale_at(POINT p) {
    UINT dx = 96, dy = 96;
    if (FAILED(GetDpiForMonitor(MonitorFromPoint(p, MONITOR_DEFAULTTONEAREST), MDT_EFFECTIVE_DPI, &dx, &dy))) return 1.0;
    return dx / 96.0;
}

}  // namespace uniqr::win
