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
    assert command[0] == sys.executable
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
