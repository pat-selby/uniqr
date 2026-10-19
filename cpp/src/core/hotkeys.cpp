#include "hotkeys.hpp"

#include <algorithm>
#include <cctype>

#include "link.hpp"

namespace uniqr {

namespace {

constexpr std::string_view kExample = "ctrl+alt+k";

std::optional<unsigned> modifier(std::string_view name) {
    if (name == "ctrl" || name == "control") return MOD_CONTROL_FLAG;
    if (name == "alt") return MOD_ALT_FLAG;
    if (name == "shift") return MOD_SHIFT_FLAG;
    if (name == "win" || name == "windows" || name == "cmd" || name == "super" || name == "meta") return MOD_WIN_FLAG;
    return std::nullopt;
}

std::string strip_brackets(std::string_view s) {
    // Python: part.strip().strip("<>").strip()
    std::string t = trim(s);
    size_t a = 0, b = t.size();
    while (a < b && (t[a] == '<' || t[a] == '>')) ++a;
    while (b > a && (t[b - 1] == '<' || t[b - 1] == '>')) --b;
    return ascii_lower(trim(std::string_view(t).substr(a, b - a)));
}

void fail(std::string* problem, std::string message) {
    if (problem) *problem = std::move(message);
}

}  // namespace

std::optional<Hotkey> parse_hotkey(std::string_view text, std::string* problem) {
    std::vector<std::string> parts;
    size_t i = 0;
    while (true) {
        const size_t j = text.find('+', i);
        parts.push_back(strip_brackets(text.substr(i, j == std::string_view::npos ? std::string_view::npos : j - i)));
        if (j == std::string_view::npos) break;
        i = j + 1;
    }
    if (parts.size() < 2 || std::any_of(parts.begin(), parts.end(), [](const std::string& p) { return p.empty(); })) {
        fail(problem, "Write it like " + std::string(kExample) +
                          ": one or more of ctrl, alt, shift or win, then one key, joined by plus signs.");
        return std::nullopt;
    }
    Hotkey hk;
    for (size_t k = 0; k + 1 < parts.size(); ++k) {
        const auto flag = modifier(parts[k]);
        if (!flag) {
            fail(problem, "'" + parts[k] + "' is not ctrl, alt, shift or win.");
            return std::nullopt;
        }
        hk.modifiers |= *flag;
    }
    const std::string& key = parts.back();
    std::string key_label;
    if (key.size() == 1 && std::isalnum(static_cast<unsigned char>(key[0]))) {
        hk.key = static_cast<unsigned>(std::toupper(static_cast<unsigned char>(key[0])));
        key_label = std::string(1, static_cast<char>(hk.key));
    } else if (key.size() >= 2 && key.size() <= 3 && key[0] == 'f' &&
               std::all_of(key.begin() + 1, key.end(), [](char c) { return c >= '0' && c <= '9'; }) &&
               std::stoi(key.substr(1)) >= 1 && std::stoi(key.substr(1)) <= 24) {
        const int n = std::stoi(key.substr(1));
        hk.key = 0x70 + n - 1;  // VK_F1 onward
        key_label = "F" + std::to_string(n);
    } else {
        fail(problem, "'" + key + "' is not a key UniQR can use. Use one letter or digit, or F1 to F24.");
        return std::nullopt;
    }
    static const std::pair<unsigned, const char*> order[] = {
        {MOD_CONTROL_FLAG, "Ctrl"}, {MOD_ALT_FLAG, "Alt"}, {MOD_SHIFT_FLAG, "Shift"}, {MOD_WIN_FLAG, "Win"}};
    for (const auto& [flag, word] : order)
        if (hk.modifiers & flag) hk.label += std::string(word) + "+";
    hk.label += key_label;
    return hk;
}

std::string canonical_hotkey(const Hotkey& hotkey) { return ascii_lower(hotkey.label); }

constexpr char kWindowsKey[] = "\xE2\x8A\x9E";  // U+229E, the Windows logo key, in UTF-8

std::string shown_hotkey(std::string_view label) {
    std::string out;
    size_t start = 0;
    while (start <= label.size()) {
        const size_t plus = label.find('+', start);
        const std::string_view part = label.substr(start, plus == std::string_view::npos ? label.npos : plus - start);
        if (!out.empty()) out += '+';
        out += part == "Win" ? std::string(kWindowsKey) : std::string(part);
        if (plus == std::string_view::npos) break;
        start = plus + 1;
    }
    return out;
}

const std::vector<Hotkey>& default_hotkeys() {
    static const std::vector<Hotkey> list = {
        {MOD_WIN_FLAG | MOD_SHIFT_FLAG, 'Q', "Win+Shift+Q"},
        {MOD_CONTROL_FLAG | MOD_ALT_FLAG, 'Q', "Ctrl+Alt+Q"},
        {MOD_CONTROL_FLAG | MOD_SHIFT_FLAG, '9', "Ctrl+Shift+9"},
    };
    return list;
}

HotkeyChoices hotkey_choices(std::string_view custom) {
    HotkeyChoices out;
    if (trim(custom).empty()) {
        out.order = default_hotkeys();
        return out;
    }
    std::string problem;
    out.wanted = parse_hotkey(custom, &problem);
    if (!out.wanted) {
        out.problem = problem;
        out.order = default_hotkeys();
        return out;
    }
    out.order.push_back(*out.wanted);
    for (const auto& h : default_hotkeys())
        if (!(h == *out.wanted)) out.order.push_back(h);
    return out;
}

}  // namespace uniqr
