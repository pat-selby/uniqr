"""How the app uses update checks: the background check, the heartbeat that shows its
result, the cards, the tray switch, the first-run question and the command line.

No internet and no real windows: the card, the check and the browser are stand-ins.
"""

import sys
import threading
import time
from types import SimpleNamespace

import app
import pytest
from uniqr import settings, updates, watchdog

VERSION = app.__version__


@pytest.fixture(autouse=True)
def own_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("UNIQR_CONFIG_DIR", str(tmp_path / "config"))


def rel(version):
    return updates.Release(version=version, url=updates.RELEASE_PAGE + version)


def newer(version="9.9.9"):
    return updates.Outcome("newer", rel(version))


CURRENT = updates.Outcome("current", rel(VERSION))
FAILED = updates.Outcome("error", detail="Could not reach GitHub (OSError).")


class Stage:
    """Stands in for the cards and the browser, and remembers what was called."""

    def __init__(self, monkeypatch, answer=True, asks=False):
        self.calls = []
        self.opened = []
        screen = SimpleNamespace(right=1920, bottom=1080)
        monkeypatch.setattr(app.capture, "monitor_at", lambda *a: screen)
        monkeypatch.setattr(
            app.overlay, "ask",
            lambda heading, note, choices, at, **k: self.calls.append(("ask", heading, note, choices)) or answer,
        )
        monkeypatch.setattr(
            app.overlay, "toast",
            lambda text, heading, *a, **k: self.calls.append(("toast", heading)),
        )
        monkeypatch.setattr(app.actions, "open_url", lambda url: self.opened.append(url) or True)
        monkeypatch.setattr(app.autostart, "should_ask", lambda *a, **k: asks)


def make_app(stopping=False):
    uniqr = app.UniQR.__new__(app.UniQR)
    uniqr.quiet = False
    uniqr.restarted = False
    uniqr._scanning = False
    uniqr.shell = SimpleNamespace(stopping=stopping, tray_available=True)
    uniqr._update_enabled = False
    uniqr._update_due = float("inf")
    uniqr._update_result = None
    uniqr._update_thread = None
    uniqr._update_showing = False
    uniqr._report_failed = None
    return uniqr


# -- showing a result -----------------------------------------------------------


def test_a_newer_version_asks_and_yes_opens_the_download_page(monkeypatch):
    stage = Stage(monkeypatch, answer=True)
    make_app()._show_update(newer("9.9.9"), manual=False)
    kind, heading, note, choices = stage.calls[0]
    assert "9.9.9" in heading and VERSION in note
    assert choices == ("Open download page", "Later")
    assert stage.opened == [updates.RELEASE_PAGE + "9.9.9"]


def test_later_opens_nothing(monkeypatch):
    stage = Stage(monkeypatch, answer=False)
    make_app()._show_update(newer(), manual=False)
    assert stage.opened == []


def test_no_answer_opens_nothing(monkeypatch):
    stage = Stage(monkeypatch, answer=None)
    make_app()._show_update(newer(), manual=False)
    assert stage.opened == []


def test_a_version_is_announced_once_not_every_day(monkeypatch):
    stage = Stage(monkeypatch, answer=False)
    uniqr = make_app()
    uniqr._show_update(newer("9.9.9"), manual=False)
    uniqr._show_update(newer("9.9.9"), manual=False)
    assert [c[0] for c in stage.calls] == ["ask"]
    uniqr._show_update(newer("9.9.10"), manual=False)  # a still newer one is news
    assert [c[0] for c in stage.calls] == ["ask", "ask"]


def test_asking_by_hand_always_answers_even_if_already_told(monkeypatch):
    stage = Stage(monkeypatch, answer=False)
    uniqr = make_app()
    uniqr._show_update(newer("9.9.9"), manual=False)
    uniqr._show_update(newer("9.9.9"), manual=True)
    assert [c[0] for c in stage.calls] == ["ask", "ask"]


def test_up_to_date_is_silent_unless_asked_for(monkeypatch):
    stage = Stage(monkeypatch)
    uniqr = make_app()
    uniqr._show_update(CURRENT, manual=False)
    assert stage.calls == []
    uniqr._show_update(CURRENT, manual=True)
    assert stage.calls == [("toast", f"UniQR is up to date ({VERSION}).")]


def test_a_failed_check_is_silent_unless_asked_for(monkeypatch, capsys):
    stage = Stage(monkeypatch)
    uniqr = make_app()
    uniqr._show_update(FAILED, manual=False)
    assert stage.calls == []
    assert "update check failed" in capsys.readouterr().out  # but it is in the log
    uniqr._show_update(FAILED, manual=True)
    assert stage.calls[0][0] == "toast" and "Could not check" in stage.calls[0][1]


def test_the_card_for_a_new_version_closes_when_uniqr_quits(monkeypatch):
    captured = {}
    Stage(monkeypatch)
    monkeypatch.setattr(
        app.overlay, "ask",
        lambda *a, **k: captured.update(until=k.get("until")) or None,
    )
    uniqr = make_app()
    uniqr._show_update(newer(), manual=False)
    assert captured["until"]() is False
    uniqr.shell.stopping = True
    assert captured["until"]() is True


# -- the background check -------------------------------------------------------


def test_the_check_runs_in_the_background_and_leaves_its_answer(monkeypatch):
    release = threading.Event()
    monkeypatch.setattr(updates, "check", lambda current: release.wait(5) and newer())
    uniqr = make_app()
    started = time.time()
    uniqr._start_update_check(manual=True)
    assert time.time() - started < 1  # the caller did not wait for it
    assert uniqr._update_result is None
    release.set()
    uniqr._update_thread.join(5)
    outcome, manual = uniqr._update_result
    assert outcome.status == "newer" and manual is True


def test_only_one_check_runs_at_a_time(monkeypatch):
    gate = threading.Event()
    calls = []
    monkeypatch.setattr(updates, "check", lambda current: calls.append(1) or gate.wait(5) or CURRENT)
    uniqr = make_app()
    uniqr._start_update_check(manual=True)
    uniqr._start_update_check(manual=True)
    uniqr._start_update_check(manual=False)
    gate.set()
    uniqr._update_thread.join(5)
    assert calls == [1]


# -- the heartbeat --------------------------------------------------------------


def test_a_finished_check_is_shown_on_the_next_heartbeat_and_only_once(monkeypatch):
    stage = Stage(monkeypatch, answer=False)
    uniqr = make_app()
    uniqr._update_result = (newer(), False)
    uniqr._on_tick()
    uniqr._on_tick()
    assert [c[0] for c in stage.calls] == ["ask"]
    assert uniqr._update_result is None


def test_nothing_is_shown_while_a_scan_is_in_progress(monkeypatch):
    stage = Stage(monkeypatch)
    uniqr = make_app()
    uniqr._update_result = (newer(), False)
    uniqr._scanning = True
    uniqr._on_tick()
    assert stage.calls == []
    uniqr._scanning = False
    uniqr._on_tick()
    assert stage.calls  # waited, then shown


def test_nothing_is_shown_while_another_card_is_up(monkeypatch):
    stage = Stage(monkeypatch)
    uniqr = make_app()
    uniqr._update_result = (newer(), False)
    uniqr._update_showing = True
    uniqr._on_tick()
    assert stage.calls == []


def test_nothing_happens_once_uniqr_is_quitting(monkeypatch):
    stage = Stage(monkeypatch)
    uniqr = make_app(stopping=True)
    uniqr._update_result = (newer(), False)
    uniqr._update_enabled, uniqr._update_due = True, 0.0
    started = []
    monkeypatch.setattr(uniqr, "_start_update_check", lambda manual: started.append(manual))
    uniqr._on_tick()
    assert stage.calls == [] and started == []


def test_a_check_is_started_when_one_is_due_and_checking_is_on(monkeypatch):
    uniqr = make_app()
    uniqr._update_enabled, uniqr._update_due = True, 0.0
    started = []
    monkeypatch.setattr(uniqr, "_start_update_check", lambda manual: started.append(manual))
    uniqr._on_tick()
    assert started == [False]  # automatic, so quiet unless there is news
    assert uniqr._update_due > time.time() + 23 * 3600  # the next one is a day away
    assert updates.next_check_at() > time.time() + 23 * 3600  # and that is remembered
    uniqr._on_tick()
    assert started == [False]  # not again in the same minute


def test_nothing_is_checked_when_it_is_off_however_overdue(monkeypatch):
    uniqr = make_app()
    uniqr._update_enabled, uniqr._update_due = False, 0.0
    started = []
    monkeypatch.setattr(uniqr, "_start_update_check", lambda manual: started.append(manual))
    uniqr._on_tick()
    assert started == []


def test_nothing_is_checked_before_it_is_due(monkeypatch):
    uniqr = make_app()
    uniqr._update_enabled, uniqr._update_due = True, time.time() + 3600
    started = []
    monkeypatch.setattr(uniqr, "_start_update_check", lambda manual: started.append(manual))
    uniqr._on_tick()
    assert started == []


# -- the watchdog hook ----------------------------------------------------------


class FakeShell:
    def __init__(self):
        self.beat = None

    def set_heartbeat(self, beat):
        self.beat = beat


class FakeDog:
    def __init__(self, *a, **k):
        self.beats = 0

    def beat(self):
        self.beats += 1

    def start(self):
        pass


@pytest.fixture
def fake_dog(monkeypatch):
    dog = FakeDog()
    monkeypatch.setattr(watchdog, "Watchdog", lambda *a, **k: dog)
    monkeypatch.setattr(watchdog, "AliveMarker", lambda path: SimpleNamespace(previous_unclean=lambda: None))
    monkeypatch.setattr(watchdog.logbook, "handle", lambda: None)
    return dog


def test_each_heartbeat_also_runs_the_hook(fake_dog):
    shell, ticks = FakeShell(), []
    watchdog.start(shell, lambda: ticks.append(1))
    shell.beat()
    shell.beat()
    assert fake_dog.beats == 2 and ticks == [1, 1]


def test_a_fault_in_the_hook_never_stops_the_heartbeat(fake_dog, capsys):
    shell = FakeShell()

    def broken():
        raise RuntimeError("boom")

    watchdog.start(shell, broken)
    shell.beat()  # must not raise
    shell.beat()
    assert fake_dog.beats == 2
    assert "a periodic task failed" in capsys.readouterr().out


def test_without_a_hook_the_heartbeat_is_the_watchdogs_own(fake_dog):
    shell = FakeShell()
    watchdog.start(shell)
    assert shell.beat == fake_dog.beat


# -- the tray switch ------------------------------------------------------------


def test_the_tray_switch_turns_checking_on_and_counts_as_an_answer():
    uniqr = make_app()
    uniqr.toggle_updates()
    assert uniqr._update_enabled is True
    assert updates.enabled() is True
    assert settings.get("update_asked") is True
    assert uniqr._update_due == 0.0  # check at the next heartbeat


def test_the_tray_switch_turns_it_off_again():
    uniqr = make_app()
    uniqr.toggle_updates()
    uniqr.toggle_updates()
    assert uniqr._update_enabled is False
    assert updates.enabled() is False


def test_check_now_from_the_tray_is_a_manual_check(monkeypatch):
    uniqr = make_app()
    seen = []
    monkeypatch.setattr(uniqr, "_start_update_check", lambda manual: seen.append(manual))
    uniqr.check_updates_now()
    assert seen == [True]


# -- the first-run question -----------------------------------------------------


@pytest.fixture
def packaged(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(updates, "supported", lambda: True)


def question_calls(stage):
    return [c for c in stage.calls if c[0] == "ask"]


def test_the_question_is_put_with_the_plain_greeting(monkeypatch, packaged):
    stage = Stage(monkeypatch, answer=True)
    make_app()._greet("Win+Shift+Q")
    kind, heading, note, choices = question_calls(stage)[0]
    assert "Press Win+Shift+Q to scan" in heading
    assert "once a day" in note and "sends nothing else" in note
    assert choices == ("Yes, check daily", "No thanks")


def test_yes_turns_checking_on_and_checks_at_the_first_heartbeat(monkeypatch, packaged):
    Stage(monkeypatch, answer=True)
    uniqr = make_app()
    uniqr._greet("Win+Shift+Q")
    assert updates.enabled() is True
    assert uniqr._update_enabled is True and uniqr._update_due == 0.0
    assert settings.get("update_asked") is True


def test_no_turns_nothing_on_and_is_final(monkeypatch, packaged):
    stage = Stage(monkeypatch, answer=False)
    uniqr = make_app()
    uniqr._greet("Win+Shift+Q")
    assert updates.enabled() is False and uniqr._update_enabled is False
    uniqr._greet("Win+Shift+Q")
    assert len(question_calls(stage)) == 1  # not asked again


def test_no_answer_turns_nothing_on_and_counts_as_ignored(monkeypatch, packaged):
    Stage(monkeypatch, answer=None)
    make_app()._greet("Win+Shift+Q")
    assert updates.enabled() is False
    assert settings.get("update_ignored") == 1


def test_quitting_during_the_question_is_not_counted_as_ignoring_it(monkeypatch, packaged):
    Stage(monkeypatch, answer=None)
    make_app(stopping=True)._greet("Win+Shift+Q")
    assert settings.get("update_ignored") is None


def test_the_login_question_comes_first_and_this_one_waits_for_a_later_start(monkeypatch, packaged):
    stage = Stage(monkeypatch, answer=False, asks=True)  # the login question is due
    make_app()._greet("Win+Shift+Q")
    heading_note = question_calls(stage)[0][2]
    assert "log in" in heading_note
    assert len(question_calls(stage)) == 1  # one question per start
    assert settings.get("update_asked") is None


def test_running_from_source_is_never_asked(monkeypatch, packaged):
    monkeypatch.delattr(sys, "frozen", raising=False)
    stage = Stage(monkeypatch, answer=True)
    make_app()._greet("Win+Shift+Q")
    assert question_calls(stage) == []


# -- the command line -----------------------------------------------------------


def run_cli(monkeypatch, capsys, outcome):
    monkeypatch.setattr(updates, "check", lambda current: outcome)
    monkeypatch.setattr(app, "UniQR", lambda **_: pytest.fail("started the whole app"))
    monkeypatch.setattr(sys, "argv", ["app.py", "--check-updates"])
    code = app.main()
    return code, capsys.readouterr().out


def test_the_command_line_says_when_there_is_a_newer_version(monkeypatch, capsys):
    code, out = run_cli(monkeypatch, capsys, newer("9.9.9"))
    assert code == 0
    assert "9.9.9 is available" in out and updates.RELEASE_PAGE + "9.9.9" in out


def test_the_command_line_says_when_up_to_date(monkeypatch, capsys):
    code, out = run_cli(monkeypatch, capsys, CURRENT)
    assert code == 0 and "up to date" in out


def test_the_command_line_fails_with_a_reason_when_it_cannot_check(monkeypatch, capsys):
    code, out = run_cli(monkeypatch, capsys, FAILED)
    assert code == 1 and "Could not check for updates" in out and "OSError" in out
