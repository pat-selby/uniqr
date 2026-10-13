"""Reporting a problem: the pre-filled GitHub issue, and the menu item that opens it.

UniQR sends nothing. These tests check that what it pre-fills is only the version
and a plain description of the system, never a log, a name or a path with a name in it.
"""

import getpass
import platform
import socket
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import app
import pytest
from uniqr import report

ROOT = Path(__file__).resolve().parent.parent


def body_of(url):
    return parse_qs(urlsplit(url).query)["body"][0]


# -- the address ----------------------------------------------------------------


def test_the_address_is_a_new_issue_on_this_project_over_https():
    parts = urlsplit(report.issue_url("0.1.9"))
    assert (parts.scheme, parts.netloc, parts.path) == ("https", "github.com", "/pat-selby/uniqr/issues/new")


def test_the_address_is_short_enough_for_every_browser():
    assert len(report.issue_url("0.1.9")) < 2000


def test_only_a_body_is_filled_in():
    assert set(parse_qs(urlsplit(report.issue_url("0.1.9")).query)) == {"body"}


def test_the_body_asks_the_three_questions():
    body = body_of(report.issue_url("0.1.9"))
    assert "What happened?" in body
    assert "What did you expect to happen?" in body
    assert "Can you make it happen again?" in body


def test_the_body_names_the_version_and_the_system():
    body = body_of(report.issue_url("0.1.9"))
    assert "UniQR 0.1.9" in body
    assert platform.platform() in body


def test_it_says_whether_it_is_the_downloaded_file_or_the_source(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert "downloaded file" in body_of(report.issue_url("0.1.9"))
    monkeypatch.delattr(sys, "frozen")
    assert "run from the source" in body_of(report.issue_url("0.1.9"))


def test_the_text_survives_being_put_in_an_address_and_read_back():
    body = report.issue_body("0.1.9")
    assert body_of(report.issue_url("0.1.9")) == body


# -- what is NOT in it ----------------------------------------------------------


@pytest.mark.parametrize("platform_name", ["win32", "linux", "darwin"])
def test_nothing_that_names_the_person_or_their_computer_is_in_it(monkeypatch, platform_name):
    monkeypatch.setattr(report.sys, "platform", platform_name)
    url = report.issue_url("0.1.9")
    text = url + body_of(url)
    for secret in (str(Path.home()), Path.home().name, getpass.getuser(), socket.gethostname()):
        if len(secret) >= 4:  # a short name would match by accident
            assert secret.lower() not in text.lower(), secret


def test_the_log_is_never_included_only_where_it_is():
    body = report.issue_body("0.1.9")
    assert "uniqr.log" in body
    assert "look through it" in body.lower()
    assert "Traceback" not in body


@pytest.mark.parametrize(
    ("platform_name", "expected"),
    [
        ("win32", "%LOCALAPPDATA%\\UniQR\\uniqr.log"),
        ("linux", "~/.local/state/uniqr/uniqr.log"),
        ("darwin", "~/Library/Logs/UniQR/uniqr.log"),
    ],
)
def test_the_log_is_named_in_a_way_that_holds_no_name(monkeypatch, platform_name, expected):
    monkeypatch.setattr(report.sys, "platform", platform_name)
    assert report.log_location() == expected


def test_the_template_on_github_asks_the_same_questions():
    template = (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md").read_text(encoding="utf-8")
    assert template.startswith("---\n")
    for question in ("What happened?", "What did you expect to happen?", "Can you make it happen again?"):
        assert question in template


# -- the menu item --------------------------------------------------------------


def make_app():
    uniqr = app.UniQR.__new__(app.UniQR)
    uniqr._scanning = False
    uniqr._report_failed = None
    uniqr.shell = SimpleNamespace(stopping=False, tray_available=True)
    uniqr._update_enabled = False
    uniqr._update_due = float("inf")
    uniqr._update_result = None
    uniqr._update_thread = None
    uniqr._update_showing = False
    return uniqr


@pytest.fixture
def stage(monkeypatch):
    calls = SimpleNamespace(opened=[], copied=[], toasts=[], opens=True)
    monkeypatch.setattr(
        app.actions, "open_url", lambda url: calls.opened.append(url) or calls.opens
    )
    monkeypatch.setattr(app.actions, "copy", lambda text: calls.copied.append(text))
    monkeypatch.setattr(
        app.overlay, "toast", lambda text, heading, *a, **k: calls.toasts.append(heading)
    )
    monkeypatch.setattr(app.capture, "monitor_at", lambda *a: SimpleNamespace(right=1920, bottom=1080))
    return calls


def test_the_menu_item_opens_the_pre_filled_page(stage):
    make_app().report_problem()
    assert stage.opened == [report.issue_url(app.__version__)]


def test_when_it_opens_nothing_else_happens(stage):
    uniqr = make_app()
    uniqr.report_problem()
    uniqr._on_tick()
    assert stage.copied == [] and stage.toasts == []


def test_when_the_browser_will_not_open_it_is_said_on_the_next_heartbeat(stage):
    stage.opens = False
    uniqr = make_app()
    uniqr.report_problem()
    assert stage.toasts == []  # this may be on a thread that cannot draw
    uniqr._on_tick()
    assert stage.copied == [report.issue_url(app.__version__)]
    assert "clipboard" in stage.toasts[0]


def test_that_is_said_once_not_every_second(stage):
    stage.opens = False
    uniqr = make_app()
    uniqr.report_problem()
    uniqr._on_tick()
    uniqr._on_tick()
    assert len(stage.toasts) == 1


def test_it_waits_while_a_scan_is_in_progress(stage):
    stage.opens = False
    uniqr = make_app()
    uniqr.report_problem()
    uniqr._scanning = True
    uniqr._on_tick()
    assert stage.toasts == []
    uniqr._scanning = False
    uniqr._on_tick()
    assert stage.toasts


# -- the command line -----------------------------------------------------------


def run_cli(monkeypatch, capsys, opens):
    monkeypatch.setattr(app.actions, "open_url", lambda url: opens)
    monkeypatch.setattr(app, "UniQR", lambda **_: pytest.fail("started the whole app"))
    monkeypatch.setattr(sys, "argv", ["app.py", "--report-problem"])
    code = app.main()
    return code, capsys.readouterr().out


def test_the_command_line_opens_the_page_and_says_nothing_is_sent(monkeypatch, capsys):
    code, out = run_cli(monkeypatch, capsys, opens=True)
    assert code == 0
    assert "Nothing is sent" in out


def test_the_command_line_gives_the_address_when_no_browser_opens(monkeypatch, capsys):
    code, out = run_cli(monkeypatch, capsys, opens=False)
    assert code == 1
    assert report.NEW_ISSUE in out
