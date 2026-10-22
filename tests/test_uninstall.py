"""The tray menu's "Uninstall UniQR", and UniQR --uninstall.

It must take away everything UniQR left, and nothing it did not: the C++
version keeps its log in the same Windows folder, so only known files go, and
a folder goes only once it is empty.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import app
import pytest
from uniqr import uninstall


@pytest.fixture
def linux_home(tmp_path, monkeypatch):
    """A Linux layout under tmp_path, with start at login switched on."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("UNIQR_CONFIG_DIR", str(tmp_path / "config" / "uniqr"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    calls = []
    monkeypatch.setattr(uninstall.autostart, "supported", lambda: True)
    monkeypatch.setattr(uninstall.autostart, "is_enabled", lambda: True)
    monkeypatch.setattr(uninstall.autostart, "set_enabled", lambda on: calls.append(on) or True)
    for f in uninstall.our_files():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
    return SimpleNamespace(root=tmp_path, autostart_calls=calls)


def test_everything_uniqr_wrote_is_removed(linux_home):
    files = uninstall.our_files()
    assert uninstall.remove() == []
    assert not any(f.exists() for f in files)
    assert not (linux_home.root / "config" / "uniqr").exists()
    assert not (linux_home.root / "state" / "uniqr").exists()
    assert linux_home.autostart_calls == [False]


def test_a_file_uniqr_did_not_write_is_kept_with_its_folder(linux_home):
    stranger = linux_home.root / "state" / "uniqr" / "notes.txt"
    stranger.write_text("not ours")
    uninstall.remove()
    assert stranger.exists()


def test_a_folder_not_named_uniqr_is_never_touched(tmp_path, monkeypatch):
    monkeypatch.setenv("UNIQR_CONFIG_DIR", str(tmp_path / "Documents"))
    assert tmp_path / "Documents" not in uninstall.our_folders()


def test_the_program_file_is_removed_when_packaged(linux_home, monkeypatch):
    exe = linux_home.root / "UniQR-linux-x86_64"
    exe.write_text("binary")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert uninstall.remove() == []
    assert not exe.exists()


def test_running_from_source_leaves_the_code_alone(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert uninstall.program() is None


def test_on_a_mac_the_whole_app_is_found(tmp_path, monkeypatch):
    exe = tmp_path / "Applications" / "UniQR.app" / "Contents" / "MacOS" / "UniQR"
    exe.parent.mkdir(parents=True)
    exe.write_text("binary")
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert uninstall.program() == (tmp_path / "Applications" / "UniQR.app").resolve()


def test_a_mac_app_goes_to_the_trash_not_away(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".Trash" / "UniQR.app").mkdir(parents=True)  # an older one already there
    app_dir = tmp_path / "Applications" / "UniQR.app"
    app_dir.mkdir(parents=True)
    uninstall._to_trash(app_dir)
    assert not app_dir.exists()
    assert (tmp_path / ".Trash" / "UniQR 2.app").is_dir()


def test_the_windows_script_waits_for_the_exe_then_cleans_up():
    exe = Path(r"C:\Apps\UniQR.exe")
    files = [Path(r"C:\Users\a\AppData\Local\UniQR\uniqr.log")]
    folders = [Path(r"C:\Users\a\AppData\Local\UniQR")]
    script = uninstall.windows_script(files, folders, exe)
    assert f'del /f /q "{exe}"' in script
    assert "goto retry" in script and "geq 30" in script
    assert f'del /f /q "{files[0]}"' in script
    assert f'rmdir "{folders[0]}"' in script
    assert "/s" not in script.replace("/f /q", ""), "never delete a folder with what is inside"
    assert script.rstrip().endswith('(goto) 2>nul & del /f /q "%~f0"')
    assert "\r\n" in script


def test_on_windows_files_wait_until_after_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("UNIQR_CONFIG_DIR", str(tmp_path / "UniQR"))
    monkeypatch.setattr(uninstall.autostart, "supported", lambda: False)
    settings_file = tmp_path / "UniQR" / "settings.json"
    settings_file.parent.mkdir()
    settings_file.write_text("{}")
    assert uninstall.remove() == []
    assert settings_file.exists()  # the script deletes it once UniQR has quit


def make_app():
    uniqr = app.UniQR.__new__(app.UniQR)
    uniqr._uninstalled = False
    uniqr.shell = SimpleNamespace(stopping=False, stopped=[])
    uniqr.shell.stop = lambda: uniqr.shell.stopped.append(True)
    return uniqr


@pytest.fixture
def tray(monkeypatch):
    calls = SimpleNamespace(removed=0, toasts=[], answer=None)
    monkeypatch.setattr(app.capture, "monitor_at", lambda *a: SimpleNamespace(right=1920, bottom=1080))
    monkeypatch.setattr(app.overlay, "ask", lambda *a, **k: calls.answer)
    monkeypatch.setattr(app.overlay, "toast", lambda text, heading, *a, **k: calls.toasts.append(heading))

    def remove():
        calls.removed += 1
        return []

    monkeypatch.setattr(app.uninstall, "remove", remove)
    return calls


@pytest.mark.parametrize("answer", [False, None])
def test_cancel_or_no_answer_removes_nothing(tray, answer):
    tray.answer = answer
    uniqr = make_app()
    uniqr.remove_uniqr()
    assert tray.removed == 0
    assert uniqr.shell.stopped == []


def test_yes_removes_says_so_and_quits(tray):
    tray.answer = True
    uniqr = make_app()
    uniqr.remove_uniqr()
    assert tray.removed == 1
    assert tray.toasts == ["UniQR is removed."]
    assert uniqr.shell.stopped == [True]
    assert uniqr._uninstalled is True


def test_the_command_line_flag_is_handled_before_anything_starts(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["UniQR.exe", "--uninstall"])
    monkeypatch.setattr(app.uninstall, "run_command_line", lambda: 7)
    monkeypatch.setattr(app.logbook, "start", lambda *a: pytest.fail("the log must not start"))
    assert app.main() == 7
