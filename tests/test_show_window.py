"""Showing a window that was built hidden.

On a Mac with Tk 9, a window built hidden and shown once stayed dark. Shown a
second time, it drew. These tests record what show_window asks of a window, so
they need no screen.
"""

from uniqr import overlay


class FakeWindow:
    def __init__(self):
        self.calls = []

    def deiconify(self):
        self.calls.append("show")

    def withdraw(self):
        self.calls.append("hide")

    def update_idletasks(self):
        self.calls.append("settle")


def test_on_a_mac_the_window_is_shown_a_second_time(monkeypatch):
    monkeypatch.setattr(overlay.sys, "platform", "darwin")
    win = FakeWindow()
    overlay.show_window(win)
    assert win.calls == ["show", "settle", "hide", "show"]
    assert win.calls[-1] == "show"  # it ends up visible


def test_elsewhere_it_is_shown_once(monkeypatch):
    for platform in ("win32", "linux"):
        monkeypatch.setattr(overlay.sys, "platform", platform)
        win = FakeWindow()
        overlay.show_window(win)
        assert win.calls == ["show"]


def test_every_window_is_shown_through_it():
    # A window shown any other way would stay dark on a Mac again.
    source = overlay.__file__
    with open(source, encoding="utf-8") as f:
        text = f.read()
    body = text.split("def show_window", 1)[1].split("\ndef ", 1)[1]
    assert ".deiconify()" not in body
