"""The log file, which is the only evidence UniQR leaves under pythonw.

Started from a shortcut there is no console: Python sets sys.stdout to None
and print() quietly does nothing. Without this file, an app that crashed on
startup looks exactly like an app that was never started.
"""

import sys

import pytest
from uniqr import logbook


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    """Point the log at a temp folder and put the streams back afterwards."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    out, err, hook = sys.stdout, sys.stderr, sys.excepthook
    yield tmp_path / "UniQR"
    sys.stdout, sys.stderr, sys.excepthook = out, err, hook


def read(path):
    return path.read_text(encoding="utf-8")


def test_start_creates_the_log_and_records_the_launch(log_dir):
    path = logbook.start(["app.py"])
    assert path.exists()
    text = read(path)
    assert "UniQR starting" in text
    assert "command: app.py" in text


def test_print_is_captured_with_a_timestamp(log_dir):
    path = logbook.start()
    print("hello from the app")
    line = [row for row in read(path).splitlines() if "hello from the app" in row]
    assert len(line) == 1
    assert line[0][:4].isdigit()  # starts with a year


def test_one_line_per_print_with_no_blank_padding(log_dir):
    path = logbook.start()
    print("first")
    print("second")
    body = read(path).splitlines()
    assert "" not in body[-3:], "blank lines mean the newline was logged too"
    assert body[-2].endswith("first")
    assert body[-1].endswith("second")


def test_a_crash_is_written_to_the_log(log_dir):
    """The whole point: something must survive the process dying."""
    path = logbook.start()
    try:
        raise ValueError("boom while starting")
    except ValueError:
        sys.excepthook(*sys.exc_info())
    text = read(path)
    assert "UniQR stopped because of an error" in text
    assert "ValueError: boom while starting" in text
    assert "Traceback" in text


def test_keyboard_interrupt_is_not_treated_as_a_crash(log_dir):
    path = logbook.start()
    try:
        raise KeyboardInterrupt
    except KeyboardInterrupt:
        sys.excepthook(*sys.exc_info())
    assert "stopped because of an error" not in read(path)


def test_the_console_still_gets_output_when_there_is_one(log_dir, capsys):
    logbook.start()
    print("visible in the terminal too")
    sys.stdout.flush()
    assert "visible in the terminal too" in capsys.readouterr().out


def test_an_oversized_log_is_rotated_not_grown_forever(log_dir):
    path = logbook.log_path()
    path.write_text("x" * (logbook.MAX_BYTES + 10), encoding="utf-8")
    logbook.start()
    assert path.with_suffix(".log.1").exists()
    assert path.stat().st_size < logbook.MAX_BYTES


def test_a_small_log_is_kept(log_dir):
    path = logbook.log_path()
    path.write_text("earlier run\n", encoding="utf-8")
    logbook.start()
    assert "earlier run" in read(path)


# -- where the log goes ------------------------------------------------------


@pytest.mark.parametrize(
    "platform,expected",
    [
        ("darwin", ("Library", "Logs", "UniQR")),
        ("win32", ("UniQR",)),
        ("linux", ("uniqr",)),
    ],
)
def test_log_goes_where_the_platform_expects(tmp_path, monkeypatch, platform, expected):
    """A UniQR folder dumped in the home directory is untidy on a Mac and
    wrong on Linux, so each platform gets its own conventional place."""
    monkeypatch.setattr(logbook.sys, "platform", platform)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr(logbook.Path, "home", classmethod(lambda cls: tmp_path))

    path = logbook.log_path()
    assert path.name == "uniqr.log"
    for part in expected:
        assert part in path.parts, f"{platform}: expected {part!r} in {path}"
