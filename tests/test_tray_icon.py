"""The Windows tray icon, and what happens when Windows says no to it.

A scan that had already copied its code went on to change the tray icon's
tooltip, Windows refused, and the error escaped. The log then said "UniQR
stopped because of an error", though the app was still running. Windows refuses
any change to an icon it is not showing, which is what happens after Explorer
restarts, and nothing put the icon back.
"""

import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="the Win32 shell is Windows only"
)
win32gui = pytest.importorskip("win32gui")

from uniqr.shell import Shell  # noqa: E402 - only importable once pywin32 is known

REFUSED = (-2147467259, "Shell_NotifyIcon", "Unspecified error")


class FakeTray:
    """Stands in for Shell_NotifyIcon, and refuses what the real one refuses.

    Checked on Windows 11: changing or removing an icon that is not there
    fails, and so does adding one that already is, all with the same error.
    """

    def __init__(self, showing: bool = True, refuse_add: bool = False) -> None:
        self.showing = showing
        self.refuse_add = refuse_add
        self.calls: list[tuple[int, tuple]] = []

    def __call__(self, action: int, data: tuple) -> None:
        self.calls.append((action, data))
        if action == win32gui.NIM_ADD:
            if self.showing or self.refuse_add:
                raise win32gui.error(*REFUSED)
            self.showing = True
        elif not self.showing:
            raise win32gui.error(*REFUSED)
        elif action == win32gui.NIM_DELETE:
            self.showing = False

    def actions(self) -> list[int]:
        return [action for action, _ in self.calls]


@pytest.fixture
def tray(monkeypatch):
    fake = FakeTray()
    monkeypatch.setattr(win32gui, "Shell_NotifyIcon", fake)
    return fake


def bare_shell() -> Shell:
    """A Shell with no window behind it, so Shell_NotifyIcon is all it touches."""
    shell = Shell.__new__(Shell)
    shell.hwnd = 1234
    shell._hicon = None
    shell.tooltip = "UniQR"
    shell._quit = False
    shell._heartbeat = None
    return shell


def test_a_tooltip_change_on_a_missing_icon_puts_the_icon_back(tray, capsys):
    """The crash after a scan: the icon had gone, so the change was refused."""
    tray.showing = False
    shell = bare_shell()

    shell.set_tooltip("UniQR - copied https://example.com")

    assert tray.actions() == [win32gui.NIM_MODIFY, win32gui.NIM_ADD, win32gui.NIM_MODIFY]
    assert tray.showing
    added = tray.calls[1][1]
    assert added[-1] == "UniQR - copied https://example.com", "re-added with the old text"
    assert capsys.readouterr().out == "The tray icon was missing, so UniQR added it again.\n"


def test_a_refused_change_that_cannot_be_fixed_is_one_line_not_a_crash(tray, capsys):
    """Windows can also refuse while the icon is there, when Explorer is busy.
    Adding it then fails too, and the scan must still count as done."""
    tray.showing = False
    tray.refuse_add = True
    shell = bare_shell()

    shell.set_tooltip("UniQR - copied https://example.com")

    assert tray.actions() == [win32gui.NIM_MODIFY, win32gui.NIM_ADD]
    out = capsys.readouterr().out
    assert out.count("\n") == 1, out
    assert "Unspecified error" in out
    assert "still running" in out


def test_a_balloon_on_a_missing_icon_puts_the_icon_back_and_shows(tray, capsys):
    tray.showing = False
    shell = bare_shell()

    shell.notify("Hotkey unavailable", "Use the tray icon to scan.")

    assert tray.actions() == [win32gui.NIM_MODIFY, win32gui.NIM_ADD, win32gui.NIM_MODIFY]
    balloon = tray.calls[-1][1]
    assert balloon[2] == win32gui.NIF_INFO
    assert "added it again" in capsys.readouterr().out


def test_a_working_tooltip_change_says_nothing(tray, capsys):
    shell = bare_shell()
    shell.set_tooltip("UniQR - press Win+Shift+Q to scan")
    assert tray.actions() == [win32gui.NIM_MODIFY]
    assert capsys.readouterr().out == ""


def test_the_taskbar_starting_again_brings_the_icon_back(tray, capsys):
    tray.showing = False
    shell = bare_shell()
    shell.tooltip = "UniQR - press Win+Shift+Q to scan"

    assert shell._on_taskbar_created(shell.hwnd, 0, 0, 0) == 0

    assert tray.showing
    assert tray.calls[0][1][-1] == "UniQR - press Win+Shift+Q to scan"
    assert "added its tray icon back" in capsys.readouterr().out


def test_the_taskbar_message_with_the_icon_still_there_says_nothing(tray, capsys):
    """Windows sends the same message on some display changes."""
    shell = bare_shell()
    shell._on_taskbar_created(shell.hwnd, 0, 0, 0)
    assert capsys.readouterr().out == ""


def test_exit_with_no_icon_left_still_ends_the_message_loop(tray):
    """Removing a missing icon raises too. Raised there, it skipped the flag
    run() watches, and Exit would have left the app running."""
    tray.showing = False
    shell = bare_shell()

    shell._on_destroy(shell.hwnd, 0, 0, 0)

    assert shell.stopping


def test_an_error_in_a_message_handler_is_logged_as_survived(capsys, monkeypatch):
    """pywin32 keeps going after a handler raises, but passes the error to
    sys.excepthook first, and UniQR's hook said "UniQR stopped"."""
    hooked = []
    monkeypatch.setattr(sys, "excepthook", lambda *exc: hooked.append(exc))
    shell = bare_shell()

    def broken(hwnd, msg, wparam, lparam):
        raise RuntimeError("the scan went wrong")

    assert shell._guard(broken)(shell.hwnd, 0, 0, 0) == 0

    out = capsys.readouterr().out
    assert "UniQR is still running" in out
    assert "RuntimeError: the scan went wrong" in out
    assert "stopped" not in out
    assert not hooked


def test_a_handler_that_works_returns_its_own_answer():
    shell = bare_shell()
    assert shell._guard(lambda *a: 7)(shell.hwnd, 0, 0, 0) == 7


LOST_ICON = """
import sys, win32con, win32gui
from uniqr import logbook
logbook.start()
from uniqr.shell import Shell

def scan():
    shell.set_tooltip("UniQR - copied https://example.com")
    raise RuntimeError("a scan that fails after copying")

shell = Shell(on_hotkey=scan)
# What Explorer restarting does to the icon.
win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (shell.hwnd, 0))
win32gui.SendMessage(shell.hwnd, win32con.WM_HOTKEY, 1, 0)

win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (shell.hwnd, 0))
win32gui.SendMessage(shell.hwnd, win32gui.RegisterWindowMessage("TaskbarCreated"), 0, 0)
win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, (shell.hwnd, 0, win32gui.NIF_TIP, 0, 0, "x"))
print("icon is back")
shell.stop()
"""


def test_the_real_shell_survives_a_lost_icon_and_a_failing_scan(tmp_path):
    """The whole path on a real window, in its own process: Windows allows one
    of these hidden windows per process, and its own log folder keeps the real
    log untouched."""
    import os
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    env = {**os.environ, "LOCALAPPDATA": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-c", LOST_ICON],
        cwd=root, capture_output=True, text=True, timeout=60, env=env,
    )
    log = (tmp_path / "UniQR" / "uniqr.log").read_text(encoding="utf-8", errors="replace")
    if "Error" in result.stderr and "window" in result.stderr.lower():
        pytest.skip("no desktop session to create a window in")
    assert result.returncode == 0, result.stderr[-1500:] + log[-1500:]
    assert "The tray icon was missing, so UniQR added it again." in log
    assert "Something went wrong, but UniQR is still running" in log
    assert "RuntimeError: a scan that fails after copying" in log
    assert "added its tray icon back" in log
    assert "icon is back" in log
    assert "stopped because of an error" not in log
    assert "WNDPROC handler failed" not in log + result.stderr
