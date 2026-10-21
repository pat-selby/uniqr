"""Helping a Mac user switch on Screen Recording and Accessibility.

A downloaded UniQR.app has no Terminal to print advice in, so a missing
permission has to show up on screen. Nothing here touches a real Mac setting.
"""

import sys
import types

import app
import pytest
from uniqr import mac_permissions


@pytest.mark.parametrize(("frozen", "who"), [(True, "UniQR"), (False, "Terminal")])
def test_the_card_names_what_to_switch_on(monkeypatch, frozen, who):
    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
    heading, note = mac_permissions.message("screen")
    assert heading == "UniQR needs permission to see your screen"
    assert "Screen Recording" in note and f"switch on {who}." in note
    _, note = mac_permissions.message("keys")
    assert "Accessibility" in note


def test_nothing_happens_off_a_mac(monkeypatch):
    monkeypatch.setattr(mac_permissions.sys, "platform", "win32")
    mac_permissions.ask_macos("screen")  # no error, no prompt
    assert mac_permissions.open_settings("screen") is False


def test_open_settings_goes_to_the_right_page(monkeypatch):
    monkeypatch.setattr(mac_permissions.sys, "platform", "darwin")
    seen = []
    monkeypatch.setattr(
        mac_permissions.subprocess, "run",
        lambda args, **k: seen.append(args) or types.SimpleNamespace(returncode=0),
    )
    assert mac_permissions.open_settings("keys")
    assert seen == [["open", mac_permissions.SETTINGS["keys"]]]


def _fake_app(quiet=False):
    shell = types.SimpleNamespace(stopping=False)
    return types.SimpleNamespace(quiet=quiet, shell=shell)


def test_yes_on_the_card_opens_settings(monkeypatch):
    calls = []
    monkeypatch.setattr(mac_permissions, "ask_macos", lambda kind: calls.append(("prompt", kind)))
    monkeypatch.setattr(mac_permissions, "open_settings", lambda kind: calls.append(("open", kind)))
    monkeypatch.setattr(app.capture, "monitor_at", lambda x, y: types.SimpleNamespace(right=1920, bottom=1080))
    monkeypatch.setattr(app.overlay, "ask", lambda *a, **k: True)
    app.UniQR._help_mac_permission(_fake_app(), "screen")
    assert calls == [("prompt", "screen"), ("open", "screen")]


def test_not_now_leaves_settings_closed(monkeypatch):
    calls = []
    monkeypatch.setattr(mac_permissions, "ask_macos", lambda kind: calls.append("prompt"))
    monkeypatch.setattr(mac_permissions, "open_settings", lambda kind: calls.append("open"))
    monkeypatch.setattr(app.capture, "monitor_at", lambda x, y: types.SimpleNamespace(right=1920, bottom=1080))
    monkeypatch.setattr(app.overlay, "ask", lambda *a, **k: False)
    app.UniQR._help_mac_permission(_fake_app(), "keys")
    assert calls == ["prompt"]


def test_a_quiet_start_shows_no_card(monkeypatch):
    monkeypatch.setattr(mac_permissions, "ask_macos", lambda kind: None)

    def no_card(*a, **k):
        raise AssertionError("a quiet start must not show a card")

    monkeypatch.setattr(app.overlay, "ask", no_card)
    app.UniQR._help_mac_permission(_fake_app(quiet=True), "screen")
