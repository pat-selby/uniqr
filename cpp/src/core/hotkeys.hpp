// Reading a hotkey a person typed, such as "ctrl+alt+k" or "<ctrl>+<alt>+k".
// A port of uniqr/hotkeys.py, with the same rules and messages. No Windows
// headers, so it is tested on every system.

#pragma once

#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace uniqr {

// The Win32 RegisterHotKey modifier flags.
constexpr unsigned MOD_ALT_FLAG = 0x0001;
constexpr unsigned MOD_CONTROL_FLAG = 0x0002;
constexpr unsigned MOD_SHIFT_FLAG = 0x0004;
constexpr unsigned MOD_WIN_FLAG = 0x0008;

struct Hotkey {
    unsigned modifiers = 0;
    unsigned key = 0;   // a Windows virtual-key code
    std::string label;  // "Ctrl+Alt+K"
    bool operator==(const Hotkey& o) const { return modifiers == o.modifiers && key == o.key; }
};

// The hotkey, or nothing with `problem` saying what is wrong in plain words.
std::optional<Hotkey> parse_hotkey(std::string_view text, std::string* problem = nullptr);
// The same hotkey written one plain way, such as "ctrl+alt+k".
std::string canonical_hotkey(const Hotkey& hotkey);

// Tried in order when no hotkey was asked for, or the one asked for is taken.
const std::vector<Hotkey>& default_hotkeys();

struct HotkeyChoices {
    std::vector<Hotkey> order;     // what to try registering, in order
    std::optional<Hotkey> wanted;  // the person's own, if it could be read
    std::string problem;           // why it could not be read, if not
};
HotkeyChoices hotkey_choices(std::string_view custom);

}  // namespace uniqr
