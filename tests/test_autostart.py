"""Start-at-login on Linux.

The file this writes is read by the desktop at login, with no one watching, so a
mistake in it fails silently: UniQR simply is not there after a restart. These
check what can be checked without a desktop: the text, the quoting for paths with
awkward characters, that it parses, and that install and removal behave.
"""

import configparser
import shlex
import sys
import types
from pathlib import Path

import pytest
from uniqr import autostart


@pytest.fixture
def linux(monkeypatch):
    monkeypatch.setattr(autostart, "_on_linux", lambda: True)


def parse(text: str) -> dict:
    parser = configparser.RawConfigParser(interpolation=None)
    parser.optionxform = str  # keep the keys' case
    parser.read_string(text)
    return dict(parser["Desktop Entry"])


def test_the_file_is_a_valid_desktop_entry():
    entry = parse(autostart.desktop_entry(["/opt/uniqr/UniQR-linux-x86_64"]))
    assert entry["Type"] == "Application"
    assert entry["Name"] == "UniQR"
    assert entry["Exec"] == "/opt/uniqr/UniQR-linux-x86_64"
    assert entry["Terminal"] == "false"


def test_a_path_with_spaces_is_quoted():
    entry = parse(autostart.desktop_entry(["/home/me/My Apps/UniQR-linux-x86_64"]))
    assert entry["Exec"] == '"/home/me/My Apps/UniQR-linux-x86_64"'
    assert shlex.split(entry["Exec"]) == ["/home/me/My Apps/UniQR-linux-x86_64"]


def test_a_percent_sign_is_doubled_because_percent_codes_are_special():
    entry = parse(autostart.desktop_entry(["/home/me/100%/UniQR-linux-x86_64"]))
    assert "100%%" in entry["Exec"]


def test_a_hotkey_is_passed_through_env_and_quoted():
    """The angle brackets would otherwise be read as redirection."""
    entry = parse(autostart.desktop_entry(["/opt/UniQR-linux-x86_64"], "<ctrl>+<alt>+<shift>+q"))
    assert entry["Exec"] == 'env "UNIQR_HOTKEY=<ctrl>+<alt>+<shift>+q" /opt/UniQR-linux-x86_64'
    assert shlex.split(entry["Exec"]) == [
        "env", "UNIQR_HOTKEY=<ctrl>+<alt>+<shift>+q", "/opt/UniQR-linux-x86_64",
    ]


def test_no_hotkey_means_no_env_wrapper():
    entry = parse(autostart.desktop_entry(["/opt/UniQR-linux-x86_64"]))
    assert "env" not in entry["Exec"] and "UNIQR_HOTKEY" not in entry["Exec"]


def test_a_source_install_starts_with_its_own_python(monkeypatch):
    monkeypatch.delattr(autostart.sys, "frozen", raising=False)
    command = autostart.program_command()
    # On Windows it is pythonw.exe, the same Python without a console window.
    assert Path(command[0]).name.lower().startswith("python")
    assert command[1].endswith("app.py")


def test_the_packaged_program_is_its_own_command(monkeypatch):
    monkeypatch.setattr(autostart.sys, "frozen", True, raising=False)
    monkeypatch.setattr(autostart.sys, "executable", "/opt/UniQR-linux-x86_64")
    # Resolved to an absolute path, which on Windows gains a drive letter.
    assert autostart.program_command() == [str(Path("/opt/UniQR-linux-x86_64").resolve())]


def test_install_writes_the_file_and_uninstall_removes_it(linux, tmp_path, capsys):
    assert autostart.install(config=tmp_path) == 0
    path = tmp_path / "autostart" / "uniqr.desktop"
    assert path.exists()
    assert parse(path.read_text())["Type"] == "Application"
    assert "next log in" in capsys.readouterr().out

    assert autostart.uninstall(config=tmp_path) == 0
    assert not path.exists()


def test_installing_twice_just_overwrites(linux, tmp_path):
    autostart.install(config=tmp_path)
    autostart.install("<ctrl>+<shift>+9", config=tmp_path)
    text = (tmp_path / "autostart" / "uniqr.desktop").read_text()
    assert text.count("[Desktop Entry]") == 1
    assert "<ctrl>+<shift>+9" in text


def test_removing_when_nothing_is_installed_is_not_an_error(linux, tmp_path, capsys):
    assert autostart.uninstall(config=tmp_path) == 0
    assert "nothing to remove" in capsys.readouterr().out


def test_it_does_not_pretend_on_other_systems(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(autostart, "_on_linux", lambda: False)
    assert autostart.install(config=tmp_path) == 1
    assert "install_mac_agent.py" in capsys.readouterr().err
    assert not (tmp_path / "autostart").exists()


def test_a_hotkey_pynput_cannot_parse_is_refused(linux, tmp_path, monkeypatch, capsys):
    fake = types.ModuleType("pynput.keyboard")

    class HotKey:
        @staticmethod
        def parse(text):
            raise ValueError(f"cannot parse {text}")

    fake.HotKey = HotKey
    pynput = types.ModuleType("pynput")
    pynput.keyboard = fake
    monkeypatch.setitem(sys.modules, "pynput", pynput)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", fake)

    assert autostart.install("ctrl-alt-q", config=tmp_path) == 1
    assert "will not work" in capsys.readouterr().err
    assert not (tmp_path / "autostart").exists(), "a bad hotkey must not leave a file behind"


def test_the_command_line_options():
    assert autostart.option(["app", "--hotkey", "<ctrl>+q"], "--hotkey") == "<ctrl>+q"
    assert autostart.option(["app", "--hotkey=<ctrl>+q"], "--hotkey") == "<ctrl>+q"
    assert autostart.option(["app", "--quiet"], "--hotkey") is None
    assert autostart.option(["app", "--hotkey"], "--hotkey") is None  # no value given
    assert autostart.handle_command_line(["app", "--quiet"]) is None


# -- Windows: the registry's Run list -----------------------------------------


class FakeRegistry:
    """Stands in for the real Run list, so no test touches anyone's startup."""

    def __init__(self):
        self.values = {}

    def write(self, name, value):
        self.values[name] = value

    def read(self, name):
        return self.values.get(name)

    def delete(self, name):
        return self.values.pop(name, None) is not None


def test_windows_install_stores_the_command_under_the_name(capsys):
    store = FakeRegistry()
    code = autostart.install_windows(
        store=store, command=[r"C:\Apps\UniQR.exe"], quiet=True
    )
    assert code == 0
    assert store.values == {"UniQR": r"C:\Apps\UniQR.exe"}
    assert "next time you log in" in capsys.readouterr().out


def test_a_windows_path_with_spaces_is_quoted_so_it_still_starts():
    """An unquoted path with a space is read as a program and its arguments."""
    store = FakeRegistry()
    autostart.install_windows(
        store=store, command=[r"C:\Program Files\UniQR\UniQR.exe"], quiet=True
    )
    assert store.values["UniQR"] == r'"C:\Program Files\UniQR\UniQR.exe"'


def test_windows_install_twice_just_replaces_the_entry():
    store = FakeRegistry()
    autostart.install_windows(store=store, command=[r"C:\One\UniQR.exe"], quiet=True)
    autostart.install_windows(store=store, command=[r"C:\Two\UniQR.exe"], quiet=True)
    assert store.values == {"UniQR": r"C:\Two\UniQR.exe"}


def test_windows_uninstall_removes_it_and_is_fine_when_absent(capsys):
    store = FakeRegistry()
    autostart.install_windows(store=store, command=[r"C:\Apps\UniQR.exe"], quiet=True)
    assert autostart.uninstall_windows(quiet=True, store=store) == 0
    assert store.values == {}
    assert autostart.uninstall_windows(quiet=True, store=store) == 0
    assert "nothing to remove" in capsys.readouterr().out


def test_windows_install_says_so_when_the_registry_refuses(capsys):
    class Refusing(FakeRegistry):
        def write(self, name, value):
            raise PermissionError("access denied")

    assert autostart.install_windows(store=Refusing(), command=["x"], quiet=True) == 1
    assert "could not be set to start at login" in capsys.readouterr().err


def test_a_windows_hotkey_is_stored_on_the_command_line():
    """The Run list has no environment, so the choice must ride on the command."""
    store = FakeRegistry()
    autostart.install_windows("Ctrl+Alt+K", store=store, command=[r"C:\Apps\UniQR.exe"], quiet=True)
    assert store.values["UniQR"] == r"C:\Apps\UniQR.exe --hotkey ctrl+alt+k"


def test_the_linux_style_hotkey_is_stored_in_the_plain_windows_form():
    store = FakeRegistry()
    autostart.install_windows("<ctrl>+<alt>+k", store=store, command=["x.exe"], quiet=True)
    assert store.values["UniQR"] == "x.exe --hotkey ctrl+alt+k"


def test_no_hotkey_adds_nothing_to_the_windows_command():
    store = FakeRegistry()
    autostart.install_windows(store=store, command=["x.exe"], quiet=True)
    assert store.values["UniQR"] == "x.exe"


def test_a_windows_hotkey_that_cannot_work_is_refused_and_nothing_is_written(capsys):
    store = FakeRegistry()
    assert autostart.install_windows("k", store=store, command=["x.exe"], quiet=True) == 1
    assert store.values == {}
    assert "will not work" in capsys.readouterr().err


def test_the_windows_confirmation_names_the_hotkey(capsys):
    autostart.install_windows("ctrl+alt+k", store=FakeRegistry(), command=["x.exe"], quiet=True)
    assert "ctrl+alt+k" in capsys.readouterr().out


def _fake_ctypes(opened):
    user32 = types.SimpleNamespace(MessageBoxW=lambda *args: opened.append(args))
    return types.SimpleNamespace(windll=types.SimpleNamespace(user32=user32))


def test_no_message_box_when_run_from_source(monkeypatch):
    """Only the packaged program, which has no console, shows one."""
    monkeypatch.delattr(autostart.sys, "frozen", raising=False)
    opened = []
    monkeypatch.setitem(sys.modules, "ctypes", _fake_ctypes(opened))
    autostart._tell("hello")
    assert opened == []


@pytest.mark.skipif(sys.platform != "win32", reason="message boxes are a Windows feature")
def test_the_packaged_windows_program_shows_a_message_box_unless_quiet(monkeypatch):
    monkeypatch.setattr(autostart.sys, "frozen", True, raising=False)
    opened = []
    monkeypatch.setitem(sys.modules, "ctypes", _fake_ctypes(opened))
    autostart._tell("done", quiet=True)
    assert opened == []
    autostart._tell("done")
    assert len(opened) == 1 and opened[0][1] == "done"


@pytest.mark.skipif(sys.platform != "win32", reason="the Run list is a Windows registry key")
def test_the_real_registry_round_trips_and_cleans_up():
    """One real trip through the registry. A unique name and a command that does
    nothing, removed in a finally, so it cannot start anything at anyone's login."""
    import uuid

    name = "UniQRTest-" + uuid.uuid4().hex[:8]
    store = autostart._Registry()
    try:
        assert autostart.install_windows(
            store=store, name=name, command=["cmd.exe", "/c", "exit"], quiet=True
        ) == 0
        assert store.read(name) == "cmd.exe /c exit"
    finally:
        autostart.uninstall_windows(quiet=True, store=store, name=name)
    assert store.read(name) is None
