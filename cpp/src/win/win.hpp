// Shared Windows helpers for the desktop app.

#pragma once

#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>

#include <string>
#include <string_view>

namespace uniqr::win {

// UniQR keeps text as UTF-8; Windows wants UTF-16.
std::wstring widen(std::string_view utf8);
std::string narrow(std::wstring_view wide);

// A colour from "#rrggbb", as GDI wants it.
constexpr COLORREF rgb(unsigned hex) { return RGB((hex >> 16) & 0xFF, (hex >> 8) & 0xFF, hex & 0xFF); }

// The card colours, the same as the Python version's.
namespace colour {
inline constexpr COLORREF accent = rgb(0x4ea1ff);
inline constexpr COLORREF accent_hover = rgb(0x7ab8ff);
inline constexpr COLORREF badge_text = rgb(0x0b1220);
inline constexpr COLORREF card_bg = rgb(0x111826);
inline constexpr COLORREF card_fg = rgb(0xe8eefc);
inline constexpr COLORREF card_muted = rgb(0x8fa3c8);
inline constexpr COLORREF card_border = rgb(0x2a3752);
inline constexpr COLORREF card_raised = rgb(0x1c2740);
inline constexpr COLORREF button_bg = rgb(0x1f2a40);
inline constexpr COLORREF button_hover = rgb(0x2c3a58);
inline constexpr COLORREF ok = rgb(0x3fb27f);
inline constexpr COLORREF warn = rgb(0xe0a33e);
}  // namespace colour

// Messages the app posts to its own hidden window.
inline constexpr UINT WM_APP_TRAY = WM_APP + 1;
inline constexpr UINT WM_APP_SCAN_DONE = WM_APP + 2;
inline constexpr UINT WM_APP_PICKED = WM_APP + 3;

}  // namespace uniqr::win
