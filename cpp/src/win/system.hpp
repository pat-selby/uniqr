// The Windows services UniQR uses: clipboard, the browser, start at login.

#pragma once

#include <string>
#include <string_view>

#include "win.hpp"

namespace uniqr::win {

bool copy_to_clipboard(HWND owner, std::string_view utf8);
// Only plain http and https links are ever handed to Windows. See can_open.
bool open_link(std::string_view url);

std::wstring exe_path();
// "Windows 10.0.26200": the system's name and version, nothing about the person.
std::string windows_version();

// Start at login: a value in the current user's Run list. No administrator
// rights. Named "UniQR-cpp", so it never touches the Python version's "UniQR".
inline constexpr wchar_t kRunValue[] = L"UniQR-cpp";
bool autostart_enabled();
// The command stored is this exe, quoted, plus the hotkey if one was chosen.
bool set_autostart(bool on, std::string_view hotkey_canonical = {});
std::wstring autostart_command();

void message_box(std::string_view text, bool ok = true);

// Uninstall: start a hidden script that waits for UniQR to quit, then deletes
// this exe and UniQR's log, and the folder if nothing else is in it. Call it
// as the last thing before exiting. False if the script could not start.
bool schedule_removal();

}  // namespace uniqr::win
