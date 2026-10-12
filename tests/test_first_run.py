"""The first-run question about starting at login, and the switch behind it.

The rules that matter: it asks once, it never turns anything on by itself, an
answer is final, and a question that is ignored does not nag forever.
"""

import sys
import tkinter as tk
from types import SimpleNamespace

import app
import pytest
from uniqr import autostart, overlay, settings


@pytest.fixture(autouse=True)
def own_settings(tmp_path, monkeypatch):
    """Every test gets its own settings folder, never the real one."""
    monkeypatch.setenv("UNIQR_CONFIG_DIR", str(tmp_path / "config"))


class FakeRegistry:
    def __init__(self):
        self.values = {}

    def write(self, name, value):
        self.values[name] = value

    def read(self, name):
        return self.values.get(name)

    def delete(self, name):
        return self.values.pop(name, None) is not None


# -- settings -------------------------------------------------------------------


def test_nothing_saved_reads_as_empty():
    assert settings.load() == {}
    assert settings.get("anything", 7) == 7


def test_a_setting_round_trips():
    assert settings.set("autostart_asked", True) is True
    assert settings.get("autostart_asked") is True


def test_settings_do_not_overwrite_each_other():
    settings.set("a", 1)
    settings.set("b", 2)
    assert settings.load() == {"a": 1, "b": 2}


def test_a_damaged_file_reads_as_empty_and_can_be_replaced():
    settings.path().parent.mkdir(parents=True)
    settings.path().write_text("{not json", encoding="utf-8")
    assert settings.load() == {}
    assert settings.set("a", 1) is True
    assert settings.get("a") == 1


def test_a_file_that_is_not_an_object_reads_as_empty():
    settings.path().parent.mkdir(parents=True)
    settings.path().write_text("[1, 2]", encoding="utf-8")
    assert settings.load() == {}


def test_a_setting_that_cannot_be_saved_is_reported_not_raised(tmp_path, monkeypatch, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("UNIQR_CONFIG_DIR", str(blocker / "inside"))  # a file is in the way
    assert settings.set("a", 1) is False
    assert "could not save" in capsys.readouterr().out


# -- when to ask ----------------------------------------------------------------


@pytest.fixture
def packaged(monkeypatch):
    """A packaged program on a system that supports start at login."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(autostart, "supported", lambda: True)
    monkeypatch.setattr(autostart, "is_enabled", lambda *a, **k: False)


def test_the_packaged_program_asks_the_first_time(packaged):
    assert autostart.should_ask() is True


def test_running_from_source_never_asks(packaged, monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert autostart.should_ask() is False


def test_a_mac_is_never_asked(packaged, monkeypatch):
    monkeypatch.setattr(autostart, "supported", lambda: False)
    assert autostart.should_ask() is False


def test_it_does_not_ask_when_already_set_up(packaged, monkeypatch):
    monkeypatch.setattr(autostart, "is_enabled", lambda *a, **k: True)
    assert autostart.should_ask() is False


def test_it_does_not_ask_on_a_quiet_start_or_a_watchdog_restart(packaged):
    assert autostart.should_ask(quiet=True) is False
    assert autostart.should_ask(restarted=True) is False


def test_an_answer_is_final(packaged):
    autostart.record_answer(False)
    assert autostart.should_ask() is False


def test_a_yes_is_final_too(packaged):
    autostart.record_answer(True)
    assert autostart.should_ask() is False


def test_ignoring_it_three_times_ends_the_asking(packaged):
    for _ in range(autostart.MAX_IGNORED - 1):
        autostart.record_answer(None)
        assert autostart.should_ask() is True
    autostart.record_answer(None)
    assert autostart.should_ask() is False


def test_a_card_closed_because_uniqr_was_quitting_is_not_an_ignored_question(packaged):
    for _ in range(10):
        autostart.record_answer(None, stopping=True)
    assert autostart.should_ask() is True


# -- the switch -----------------------------------------------------------------


def test_the_switch_on_windows_writes_and_removes_the_run_entry(monkeypatch):
    monkeypatch.setattr(autostart.sys, "platform", "win32")
    store = FakeRegistry()
    assert autostart.is_enabled(store=store) is False
    assert autostart.set_enabled(True, store=store) is True
    assert autostart.is_enabled(store=store) is True
    assert autostart.RUN_VALUE in store.values
    assert autostart.set_enabled(False, store=store) is True
    assert autostart.is_enabled(store=store) is False


def test_the_switch_on_linux_writes_and_removes_the_desktop_file(tmp_path, monkeypatch):
    monkeypatch.setattr(autostart.sys, "platform", "linux")
    monkeypatch.delenv("UNIQR_HOTKEY", raising=False)
    assert autostart.is_enabled(config=tmp_path) is False
    assert autostart.set_enabled(True, config=tmp_path) is True
    assert autostart.is_enabled(config=tmp_path) is True
    assert autostart.entry_path(tmp_path).exists()
    assert autostart.set_enabled(False, config=tmp_path) is True
    assert not autostart.entry_path(tmp_path).exists()


def test_a_hotkey_chosen_for_this_run_is_kept_for_the_login_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(autostart.sys, "platform", "linux")
    monkeypatch.setenv("UNIQR_HOTKEY", "<ctrl>+<alt>+<shift>+q")
    autostart.set_enabled(True, config=tmp_path)
    assert "UNIQR_HOTKEY=" in autostart.entry_path(tmp_path).read_text(encoding="utf-8")


def test_the_switch_does_nothing_on_a_mac(monkeypatch):
    monkeypatch.setattr(autostart.sys, "platform", "darwin")
    assert autostart.is_enabled() is False
    assert autostart.set_enabled(True) is False


# -- the app's side of it -------------------------------------------------------


class Recorder:
    """Stands in for the card and the switch, and remembers what was called."""

    def __init__(self, monkeypatch, answer, enable_ok=True, asks=True):
        self.calls = []
        screen = SimpleNamespace(right=1920, bottom=1080)
        monkeypatch.setattr(app.capture, "monitor_at", lambda *a: screen)
        monkeypatch.setattr(app.autostart, "should_ask", lambda *a, **k: asks)
        monkeypatch.setattr(
            app.overlay, "ask", lambda *a, **k: self.calls.append("ask") or answer
        )
        monkeypatch.setattr(
            app.overlay, "toast", lambda text, heading, *a, **k: self.calls.append("toast: " + heading)
        )
        monkeypatch.setattr(
            app.autostart, "set_enabled", lambda on, *a, **k: self.calls.append(f"set {on}") or enable_ok
        )


def make_app(stopping=False):
    uniqr = app.UniQR.__new__(app.UniQR)
    uniqr.quiet = False
    uniqr.restarted = False
    uniqr.shell = SimpleNamespace(stopping=stopping, tray_available=True)
    return uniqr


def test_a_yes_turns_it_on_and_says_so(monkeypatch):
    rec = Recorder(monkeypatch, answer=True)
    make_app()._greet("Win+Shift+Q")
    assert rec.calls == ["ask", "set True", "toast: UniQR will start when you log in."]
    assert settings.get("autostart_asked") is True


def test_a_no_turns_nothing_on(monkeypatch):
    rec = Recorder(monkeypatch, answer=False)
    make_app()._greet("Win+Shift+Q")
    assert rec.calls == ["ask"]
    assert settings.get("autostart_asked") is True


def test_no_answer_turns_nothing_on_and_counts_as_ignored(monkeypatch):
    rec = Recorder(monkeypatch, answer=None)
    make_app()._greet("Win+Shift+Q")
    assert rec.calls == ["ask"]
    assert settings.get("autostart_asked") is None
    assert settings.get("autostart_ignored") == 1


def test_quitting_during_the_question_is_not_counted_as_ignoring_it(monkeypatch):
    Recorder(monkeypatch, answer=None)
    make_app(stopping=True)._greet("Win+Shift+Q")
    assert settings.get("autostart_ignored") is None


def test_a_failed_setup_is_reported_on_the_card(monkeypatch):
    rec = Recorder(monkeypatch, answer=True, enable_ok=False)
    make_app()._greet("Win+Shift+Q")
    assert rec.calls[-1].startswith("toast: Could not set up")


def test_when_not_asking_it_is_only_the_plain_greeting(monkeypatch):
    rec = Recorder(monkeypatch, answer=True, asks=False)
    make_app()._greet("Win+Shift+Q")
    assert rec.calls == ["toast: UniQR is running. Press Win+Shift+Q to scan."]


def test_a_quiet_start_shows_no_card_at_all(monkeypatch):
    rec = Recorder(monkeypatch, answer=True)
    quiet = make_app()
    quiet.quiet = True
    quiet._greet("Win+Shift+Q")
    assert rec.calls == []


def test_the_tray_switch_flips_it_and_counts_as_an_answer(monkeypatch):
    state = {"on": False}
    monkeypatch.setattr(app.autostart, "is_enabled", lambda *a, **k: state["on"])
    monkeypatch.setattr(
        app.autostart, "set_enabled", lambda on, *a, **k: state.update(on=on) or True
    )
    uniqr = make_app()
    uniqr.toggle_autostart()
    assert state["on"] is True
    assert settings.get("autostart_asked") is True
    uniqr.toggle_autostart()
    assert state["on"] is False


def test_the_tray_switch_leaves_the_answer_alone_when_it_fails(monkeypatch):
    monkeypatch.setattr(app.autostart, "is_enabled", lambda *a, **k: False)
    monkeypatch.setattr(app.autostart, "set_enabled", lambda *a, **k: False)
    make_app().toggle_autostart()
    assert settings.get("autostart_asked") is None


# -- the real card --------------------------------------------------------------


@pytest.fixture
def root():
    """A real Tk root, on Windows only.

    A shared Tk window left alive inside the test process hung the macOS test run
    in CI, and Linux has no display there. The card is covered on Linux by the
    packaged-program smoke test, which answers it with a real key press.
    """
    if sys.platform != "win32":
        pytest.skip("real Tk windows in the test process are only run on Windows")
    try:
        shared = overlay.shared_root()
        shared.winfo_exists()
    except tk.TclError:
        pytest.skip("no display for Tk")
    return shared


def question(root, timeout=4000, until=None):
    return overlay.Toast(
        "", "UniQR is running.", (200, 200), timeout,
        choices=("Yes, start at login", "Not now"), note="Start it at login?", until=until,
    )


def test_the_first_button_answers_yes(root):
    card = question(root)
    root.after(80, lambda: card._answer(True))
    card.show()
    assert card.answer is True


def test_the_second_button_answers_no(root):
    card = question(root)
    root.after(80, lambda: card._answer(False))
    card.show()
    assert card.answer is False


def test_escape_closes_it_unanswered(root):
    card = question(root)
    root.after(80, card._close)
    card.show()
    assert card.answer is None


def test_it_times_out_unanswered(root):
    card = question(root, timeout=300)
    card.show()
    assert card.answer is None


def test_it_closes_at_once_when_asked_to(root):
    """Choosing Exit from the tray while the question is up must not wait it out."""
    flag = {"stop": False}
    card = question(root, timeout=30000, until=lambda: flag["stop"])
    root.after(200, lambda: flag.update(stop=True))
    import time

    start = time.time()
    card.show()
    assert card.answer is None
    assert time.time() - start < 3


def test_hovering_does_not_shorten_a_question(root):
    """A normal card closes 0.7 s after the pointer leaves. A question keeps its time."""

    def delay_after_hover(card):
        delays = []
        card.win.after = lambda ms, *a: delays.append(ms) or "id"
        card._left_once = True
        card._start_timer()
        card.win.destroy()
        return delays[-1]

    assert delay_after_hover(question(root, timeout=5000)) == 5000
    plain = overlay.Toast("", "Copied", (200, 200), 5000)
    assert delay_after_hover(plain) == overlay.TOAST_AFTER_HOVER_MS


@pytest.mark.skipif(sys.platform != "win32", reason="key focus needs a real desktop; the Linux smoke test covers it there")
@pytest.mark.parametrize(("key", "expected"), [("y", True), ("Return", True), ("n", False)])
def test_the_question_can_be_answered_from_the_keyboard(root, key, expected):
    card = question(root)
    root.after(150, lambda: card.win.event_generate(f"<Key-{key}>"))
    card.show()
    assert card.answer is expected


def test_a_report_card_closes_on_time_even_when_hovered(root):
    """The confirmation after Yes has nothing to read, and start-up waits behind it."""
    bound = []
    card = overlay.Toast("", "Done", (200, 200), 400, hover_pause=False)
    card.win.event_generate("<Enter>")  # pointer arrives, as it would
    bound.append(card.win.bind("<Enter>"))
    card.show()
    assert bound == [""]  # nothing is bound to Enter, so nothing can pause the timer
