"""The macOS launch agent installer.

Fails with launchd status 78 and no message when a path in the file is wrong, so
the part worth testing is that every path comes from the machine it runs on and
none from the author's. The launchctl calls need a Mac and are not tested here.
"""

import importlib.util
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "install_mac_agent.py"


@pytest.fixture(scope="module")
def installer():
    spec = importlib.util.spec_from_file_location("install_mac_agent", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repo(tmp_path):
    """A pretend UniQR folder somewhere other than the author's."""
    folder = tmp_path / "Some Other Place" / "uniqr"
    (folder / "tools").mkdir(parents=True)
    shutil.copy(ROOT / "tools" / "com.patselby.uniqr.plist", folder / "tools")
    return folder


def test_every_path_comes_from_this_machine(installer, repo, tmp_path):
    home = tmp_path / "Users" / "someoneelse"
    data = installer.build_plist(repo, home)

    assert data["ProgramArguments"] == [str(repo / ".venv" / "bin" / "python"), str(repo / "app.py")]
    assert data["WorkingDirectory"] == str(repo)
    log = str(home / "Library" / "Logs" / "UniQR" / "launchd.log")
    assert data["StandardOutPath"] == log
    assert data["StandardErrorPath"] == log


def test_nothing_of_the_authors_survives(installer, repo, tmp_path):
    """The example username in the template is what broke the first install."""
    text = plistlib.dumps(installer.build_plist(repo, tmp_path / "home")).decode()
    assert "pescybers" not in text


def test_it_keeps_the_settings_that_are_not_paths(installer, repo, tmp_path):
    data = installer.build_plist(repo, tmp_path / "home")
    assert data["Label"] == "com.patselby.uniqr"
    assert data["RunAtLoad"] is True
    assert data["KeepAlive"] is True
    assert data["ThrottleInterval"] >= 10, "a restart loop must not run flat out"


def test_the_default_hotkey_is_left_alone(installer, repo, tmp_path):
    """Control+Option+Q is the documented default; the template's override was
    for a virtual machine and must not leak onto a real Mac."""
    assert "EnvironmentVariables" not in installer.build_plist(repo, tmp_path / "home")


def test_a_chosen_hotkey_is_passed_through(installer, repo, tmp_path):
    data = installer.build_plist(repo, tmp_path / "home", hotkey="<cmd>+<shift>+8")
    assert data["EnvironmentVariables"] == {"UNIQR_HOTKEY": "<cmd>+<shift>+8"}


def test_the_result_is_a_valid_plist_even_with_spaces_in_paths(installer, repo, tmp_path):
    data = installer.build_plist(repo, tmp_path / "home", hotkey="<cmd>+<shift>+8")
    assert plistlib.loads(plistlib.dumps(data)) == data


def test_print_mode_changes_nothing_and_runs_on_any_system():
    """--print is how this is checked without a Mac."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--print"], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    data = plistlib.loads(result.stdout.encode())
    assert data["WorkingDirectory"] == str(ROOT)
    assert "pescybers" not in result.stdout


def test_it_refuses_politely_off_a_mac():
    if sys.platform == "darwin":
        pytest.skip("this is the case where it would really install")
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 1
    assert "only runs on a Mac" in result.stderr
