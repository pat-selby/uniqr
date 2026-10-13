"""Reading a hotkey a person typed, for Windows."""

import pytest
from uniqr import hotkeys
from uniqr.hotkeys import MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, parse_windows


@pytest.mark.parametrize(
    ("text", "mods", "vk", "label"),
    [
        ("ctrl+alt+k", MOD_CONTROL | MOD_ALT, ord("K"), "Ctrl+Alt+K"),
        ("Ctrl+Alt+K", MOD_CONTROL | MOD_ALT, ord("K"), "Ctrl+Alt+K"),
        ("CTRL + ALT + k", MOD_CONTROL | MOD_ALT, ord("K"), "Ctrl+Alt+K"),
        ("<ctrl>+<alt>+k", MOD_CONTROL | MOD_ALT, ord("K"), "Ctrl+Alt+K"),
        ("win+shift+q", MOD_WIN | MOD_SHIFT, ord("Q"), "Shift+Win+Q"),
        ("<cmd>+<shift>+8", MOD_WIN | MOD_SHIFT, ord("8"), "Shift+Win+8"),
        ("super+j", MOD_WIN, ord("J"), "Win+J"),
        ("shift+alt+ctrl+z", MOD_CONTROL | MOD_ALT | MOD_SHIFT, ord("Z"), "Ctrl+Alt+Shift+Z"),
        ("ctrl+f5", MOD_CONTROL, 0x74, "Ctrl+F5"),
        ("ctrl+F24", MOD_CONTROL, 0x87, "Ctrl+F24"),
        ("control+0", MOD_CONTROL, ord("0"), "Ctrl+0"),
    ],
)
def test_what_people_type_is_understood(text, mods, vk, label):
    assert parse_windows(text) == (mods, vk, label)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "k",  # no modifier: it would take the letter from every program
        "ctrl",  # no key
        "ctrl+",
        "+k",
        "ctrl++k",
        "ctrl+alt",  # alt is not a key
        "banana+k",
        "ctrl+kk",
        "ctrl+f25",
        "ctrl+f0",
        "ctrl+é",
        "ctrl+<k>+alt",  # the key must come last
    ],
)
def test_what_cannot_work_is_refused_with_a_reason(text):
    with pytest.raises(ValueError) as caught:
        parse_windows(text)
    assert str(caught.value)  # says what is wrong


def test_the_reason_names_an_example():
    with pytest.raises(ValueError, match="ctrl\\+alt\\+k"):
        parse_windows("k")


def test_the_stored_form_is_plain_and_the_same_for_every_spelling():
    assert hotkeys.canonical("<Ctrl>+<Alt>+K") == "ctrl+alt+k"
    assert hotkeys.canonical("alt+control+k") == "ctrl+alt+k"


def test_the_stored_form_reads_back_as_the_same_hotkey():
    for text in ("<cmd>+<shift>+8", "ctrl+f5", "super+j"):
        assert parse_windows(hotkeys.canonical(text)) == parse_windows(text)


def test_with_no_choice_the_usual_list_is_used():
    choices, wanted, problem = hotkeys.windows_choices(None)
    assert choices == hotkeys.WINDOWS_DEFAULTS
    assert wanted is None and problem is None
    assert choices[0][2] == "Win+Shift+Q"


@pytest.mark.parametrize("blank", ["", "   "])
def test_a_blank_choice_counts_as_none(blank):
    assert hotkeys.windows_choices(blank)[0] == hotkeys.WINDOWS_DEFAULTS


def test_a_readable_choice_goes_first_and_the_usual_list_follows():
    choices, wanted, problem = hotkeys.windows_choices("ctrl+alt+k")
    assert problem is None
    assert wanted == choices[0]
    assert wanted[2] == "Ctrl+Alt+K"
    assert choices[1:] == hotkeys.WINDOWS_DEFAULTS


def test_choosing_one_of_the_usual_ones_does_not_list_it_twice():
    choices, wanted, _ = hotkeys.windows_choices("ctrl+alt+q")
    assert [c[:2] for c in choices].count(wanted[:2]) == 1
    assert choices[0][2] == "Ctrl+Alt+Q"


def test_an_unreadable_choice_gives_a_reason_and_still_leaves_the_usual_list():
    choices, wanted, problem = hotkeys.windows_choices("banana")
    assert choices == hotkeys.WINDOWS_DEFAULTS
    assert wanted is None
    assert problem
