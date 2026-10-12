"""Opening a link must really start the browser, and say so when it did not.

On Linux the packaged program runs with its own unpacked folder first in
LD_LIBRARY_PATH. A browser started from it inherits that. These tests stand a
small Python script in for xdg-open, so they can see exactly what a launcher is
handed, on any operating system.
"""

import json
import sys

import pytest
from uniqr import actions

URL = "https://example.com/page?a=1"


@pytest.fixture
def launcher(tmp_path, monkeypatch):
    """A fake launcher that records its arguments and library path, then exits
    with the code in FAKE_EXIT. Linux behavior is switched on for the test."""
    record = tmp_path / "record.json"
    script = tmp_path / "fake_open.py"
    script.write_text(
        "import json, os, sys\n"
        f"open({str(record)!r}, 'w').write(json.dumps({{\n"
        "    'args': sys.argv[1:],\n"
        "    'ld': os.environ.get('LD_LIBRARY_PATH'),\n"
        "}))\n"
        "sys.stderr.write('boom from the launcher')\n"
        "sys.exit(int(os.environ.get('FAKE_EXIT', '0')))\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(actions, "_linux", lambda: True)
    monkeypatch.setattr(actions, "_LINUX_LAUNCHERS", ([sys.executable, str(script)],))
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)

    def seen():
        return json.loads(record.read_text(encoding="utf-8")) if record.exists() else None

    return seen


def test_the_link_is_handed_to_the_launcher(launcher):
    assert actions.open_url(URL) is True
    assert launcher()["args"] == [URL]


def test_a_packaged_program_gives_the_browser_the_users_library_path(launcher, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI123:/usr/lib/mine")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/lib/mine")
    assert actions.open_url(URL) is True
    assert launcher()["ld"] == "/usr/lib/mine"


def test_a_packaged_program_with_no_original_path_gives_the_browser_none(launcher, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI123")
    assert actions.open_url(URL) is True
    assert launcher()["ld"] is None


def test_running_from_source_leaves_the_library_path_alone(launcher, monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/usr/lib/mine")
    assert actions.open_url(URL) is True
    assert launcher()["ld"] == "/usr/lib/mine"


def test_our_own_environment_is_not_changed_by_opening(launcher, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI123")
    actions.open_url(URL)
    assert actions.os.environ["LD_LIBRARY_PATH"] == "/tmp/_MEI123"


def test_a_launcher_that_fails_is_reported_not_swallowed(launcher, monkeypatch, capsys):
    """If every launcher fails the caller must hear False, so the card still
    shows and the link is still on the clipboard."""
    monkeypatch.setenv("FAKE_EXIT", "3")
    monkeypatch.setattr(actions.webbrowser, "open", lambda url: False)
    assert actions.open_url(URL) is False
    out = capsys.readouterr().out
    assert "exit 3" in out
    assert "boom from the launcher" in out


def test_the_next_launcher_is_tried_when_the_first_is_missing(launcher, monkeypatch):
    monkeypatch.setattr(
        actions,
        "_LINUX_LAUNCHERS",
        (["no-such-launcher-anywhere"], *actions._LINUX_LAUNCHERS),
    )
    assert actions.open_url(URL) is True
    assert launcher()["args"] == [URL]


def test_a_launcher_still_running_counts_as_opened(tmp_path, monkeypatch):
    """A browser starting up keeps running. That is success, not a hang."""
    slow = tmp_path / "slow.py"
    slow.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
    monkeypatch.setattr(actions, "_linux", lambda: True)
    monkeypatch.setattr(actions, "_LINUX_LAUNCHERS", ([sys.executable, str(slow)],))
    monkeypatch.setattr(actions, "_LAUNCH_WAIT_S", 0.3)
    assert actions.open_url(URL) is True


def test_the_standard_library_is_the_last_resort(launcher, monkeypatch):
    monkeypatch.setenv("FAKE_EXIT", "1")
    seen = []
    monkeypatch.setattr(actions.webbrowser, "open", lambda url: seen.append(url) or True)
    assert actions.open_url(URL) is True
    assert seen == [URL]


def test_a_link_that_is_not_http_is_never_opened(launcher):
    assert actions.open_url("file:///etc/passwd") is False
    assert launcher() is None


def test_open_url_option_opens_one_link_and_exits(monkeypatch, capsys):
    """`app.py --open-url` must not start UniQR, only try the link."""
    import app

    tried = []
    monkeypatch.setattr(actions, "open_url", lambda url: tried.append(url) or True)
    monkeypatch.setattr(app, "UniQR", lambda **_: pytest.fail("started the whole app"))
    monkeypatch.setattr(sys, "argv", ["app.py", "--open-url", URL])
    assert app.main() == 0
    assert tried == [URL]
    assert "opened it" in capsys.readouterr().out


def test_open_url_option_says_so_when_it_fails(monkeypatch, capsys):
    import app

    monkeypatch.setattr(actions, "open_url", lambda url: False)
    monkeypatch.setattr(sys, "argv", ["app.py", "--open-url", URL])
    assert app.main() == 1
    assert "could not open it" in capsys.readouterr().out
