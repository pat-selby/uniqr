// Reading a hotkey a person typed. Ported from the Python tests/test_hotkeys.py.

#include <doctest/doctest.h>

#include "hotkeys.hpp"

using namespace uniqr;

TEST_CASE("what people type is understood") {
    struct Case {
        const char* text;
        unsigned mods;
        unsigned key;
        const char* label;
    };
    const Case cases[] = {
        {"ctrl+alt+k", MOD_CONTROL_FLAG | MOD_ALT_FLAG, 'K', "Ctrl+Alt+K"},
        {"Ctrl+Alt+K", MOD_CONTROL_FLAG | MOD_ALT_FLAG, 'K', "Ctrl+Alt+K"},
        {"CTRL + ALT + k", MOD_CONTROL_FLAG | MOD_ALT_FLAG, 'K', "Ctrl+Alt+K"},
        {"<ctrl>+<alt>+k", MOD_CONTROL_FLAG | MOD_ALT_FLAG, 'K', "Ctrl+Alt+K"},
        {"win+shift+q", MOD_WIN_FLAG | MOD_SHIFT_FLAG, 'Q', "Shift+Win+Q"},
        {"<cmd>+<shift>+8", MOD_WIN_FLAG | MOD_SHIFT_FLAG, '8', "Shift+Win+8"},
        {"super+j", MOD_WIN_FLAG, 'J', "Win+J"},
        {"shift+alt+ctrl+z", MOD_CONTROL_FLAG | MOD_ALT_FLAG | MOD_SHIFT_FLAG, 'Z', "Ctrl+Alt+Shift+Z"},
        {"ctrl+f5", MOD_CONTROL_FLAG, 0x74, "Ctrl+F5"},
        {"ctrl+F24", MOD_CONTROL_FLAG, 0x87, "Ctrl+F24"},
        {"control+0", MOD_CONTROL_FLAG, '0', "Ctrl+0"},
    };
    for (const auto& c : cases) {
        const auto hk = parse_hotkey(c.text);
        REQUIRE_MESSAGE(hk, c.text);
        CHECK(hk->modifiers == c.mods);
        CHECK(hk->key == c.key);
        CHECK(hk->label == c.label);
    }
}

TEST_CASE("what cannot work is refused with a reason") {
    for (const char* t : {"", "k", "ctrl", "ctrl+", "+k", "ctrl++k", "ctrl+alt", "banana+k", "ctrl+kk", "ctrl+f25",
                          "ctrl+f0", "ctrl+\xC3\xA9", "ctrl+<k>+alt"}) {
        std::string problem;
        CHECK_MESSAGE(!parse_hotkey(t, &problem), t);
        CHECK_MESSAGE(!problem.empty(), t);
    }
}

TEST_CASE("the reason names an example") {
    std::string problem;
    parse_hotkey("k", &problem);
    CHECK(problem.find("ctrl+alt+k") != std::string::npos);
}

TEST_CASE("the stored form is plain and the same for every spelling") {
    CHECK(canonical_hotkey(*parse_hotkey("<Ctrl>+<Alt>+K")) == "ctrl+alt+k");
    CHECK(canonical_hotkey(*parse_hotkey("alt+control+k")) == "ctrl+alt+k");
}

TEST_CASE("with no choice the usual list is used, Win+Shift+Q first") {
    const auto c = hotkey_choices("");
    CHECK(c.order.size() == default_hotkeys().size());
    CHECK(c.order.front().label == "Win+Shift+Q");
    CHECK(!c.wanted);
    CHECK(c.problem.empty());
}

TEST_CASE("a readable choice goes first and the usual list follows") {
    const auto c = hotkey_choices("ctrl+alt+k");
    REQUIRE(c.wanted);
    CHECK(c.order.front().label == "Ctrl+Alt+K");
    CHECK(c.order.size() == 1 + default_hotkeys().size());
}

TEST_CASE("choosing one of the usual ones does not list it twice") {
    const auto c = hotkey_choices("ctrl+alt+q");
    CHECK(c.order.size() == default_hotkeys().size());
    CHECK(c.order.front().label == "Ctrl+Alt+Q");
}

TEST_CASE("an unreadable choice gives a reason and still leaves the usual list") {
    const auto c = hotkey_choices("banana");
    CHECK(!c.wanted);
    CHECK(!c.problem.empty());
    CHECK(c.order.size() == default_hotkeys().size());
}

TEST_CASE("the Windows key is shown as its logo, and only where people read it") {
    CHECK(shown_hotkey("Win+Shift+Q") == "\xE2\x8A\x9E+Shift+Q");
    CHECK(shown_hotkey("Shift+Win+8") == "Shift+\xE2\x8A\x9E+8");
    CHECK(shown_hotkey("Ctrl+Alt+Q") == "Ctrl+Alt+Q");
    // The stored setting keeps the word, so it reads back.
    const auto hk = parse_hotkey("win+shift+q");
    REQUIRE(hk);
    CHECK(canonical_hotkey(*hk) == "shift+win+q");
    CHECK(parse_hotkey(canonical_hotkey(*hk)));
}
