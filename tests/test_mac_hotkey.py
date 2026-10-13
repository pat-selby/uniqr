"""The Mac default hotkey must not be one slip away from Command+Q.

A Mac user pressed Control+Option+Q, the old default, and closed their browser on
the first try. macOS cannot say a shortcut is taken, so only the first choice in
the list is ever used: that one has to be safe.
"""

import pytest
from uniqr import shell_portable


@pytest.fixture
def mac(monkeypatch):
    monkeypatch.setattr(shell_portable.sys, "platform", "darwin")
    monkeypatch.delenv("UNIQR_HOTKEY", raising=False)


def test_the_first_choice_on_a_mac_is_command_shift_8(mac):
    combo, label = shell_portable.hotkey_choices()[0]
    assert combo == "<cmd>+<shift>+8"
    assert label == "Command+Shift+8"


def test_the_old_default_is_no_longer_first(mac):
    assert shell_portable.hotkey_choices()[0][0] != "<ctrl>+<alt>+q"


def test_no_choice_is_command_q_or_one_that_logs_you_out_or_locks_the_screen(mac):
    dangerous = {"<cmd>+q", "<cmd>+<shift>+q", "<cmd>+<ctrl>+q", "<ctrl>+<cmd>+q"}
    assert not dangerous & {combo for combo, _ in shell_portable.hotkey_choices()}


def test_the_old_choices_are_still_there_as_later_fallbacks(mac):
    combos = [combo for combo, _ in shell_portable.hotkey_choices()]
    assert "<ctrl>+<alt>+q" in combos and "<ctrl>+<shift>+q" in combos


def test_a_hotkey_the_person_chose_still_replaces_the_list(mac, monkeypatch):
    monkeypatch.setenv("UNIQR_HOTKEY", "<cmd>+<shift>+9")
    assert shell_portable.hotkey_choices() == [("<cmd>+<shift>+9", "<cmd>+<shift>+9")]


def test_linux_is_unchanged(monkeypatch):
    monkeypatch.setattr(shell_portable.sys, "platform", "linux")
    monkeypatch.delenv("UNIQR_HOTKEY", raising=False)
    assert shell_portable.hotkey_choices()[0] == ("<ctrl>+<alt>+q", "Ctrl+Alt+Q")
