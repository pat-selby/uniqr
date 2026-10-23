"""UniQR as a Microsoft Store app.

As a Store app, Windows delivers updates, removes the app from Settings, and
owns start at login. UniQR must step aside on all three, and say where its log
really is. The package itself is checked here too: its manifest and icons.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from uniqr import autostart, report, store, uninstall, updates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_msix  # noqa: E402

FAMILY = "UniQR_8wekyb3d8bbwe"


@pytest.fixture
def as_store_app(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(store, "family_name", lambda: FAMILY)


def test_this_test_run_is_not_a_store_app():
    assert store.packaged() is False


def test_a_store_app_leaves_start_at_login_to_windows(as_store_app):
    assert autostart.supported() is False


def test_a_store_app_leaves_updates_to_the_store(as_store_app):
    assert updates.supported() is False


def test_a_store_app_is_removed_in_settings_not_by_itself(as_store_app, capsys):
    assert uninstall.run_command_line() == 1
    assert "Settings > Apps" in capsys.readouterr().out


def test_a_problem_report_names_the_store_and_the_real_log(as_store_app):
    assert report.how_it_is_run() == "Microsoft Store app"
    assert report.log_location() == f"%LOCALAPPDATA%\\Packages\\{FAMILY}\\LocalCache\\Local\\UniQR\\uniqr.log"


def test_the_downloaded_exe_keeps_its_own_ways(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(store, "family_name", lambda: None)
    assert autostart.supported() is True
    assert updates.supported() is True
    assert report.log_location() == "%LOCALAPPDATA%\\UniQR\\uniqr.log"


# -- the package ------------------------------------------------------------------

NS = {
    "m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
    "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
    "desktop": "http://schemas.microsoft.com/appx/manifest/desktop/windows10",
    "rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities",
}


def parsed(**identity):
    values = {"name": "PatrickSelby.UniQR", "publisher": "CN=ABC-123", "publisher_display": "Patrick Selby"}
    values.update(identity)
    return ET.fromstring(build_msix.manifest(**values))


def test_the_version_has_four_numbers_ending_in_zero():
    version = build_msix.package_version()
    parts = version.split(".")
    assert len(parts) == 4 and parts[-1] == "0"
    assert ".".join(parts[:3]) == build_msix.__version__


def test_the_manifest_carries_the_identity_partner_center_gave():
    root = parsed()
    identity = root.find("m:Identity", NS)
    assert identity.get("Name") == "PatrickSelby.UniQR"
    assert identity.get("Publisher") == "CN=ABC-123"
    assert identity.get("Version") == build_msix.package_version()
    assert root.find("m:Properties/m:PublisherDisplayName", NS).text == "Patrick Selby"


def test_odd_characters_in_the_identity_cannot_break_the_manifest():
    root = parsed(publisher='CN="Smith & Sons", O=x', publisher_display="A & B <C>")
    assert root.find("m:Identity", NS).get("Publisher") == 'CN="Smith & Sons", O=x'
    assert root.find("m:Properties/m:PublisherDisplayName", NS).text == "A & B <C>"


def test_it_runs_as_a_desktop_program_with_start_at_login_off():
    root = parsed()
    app = root.find("m:Applications/m:Application", NS)
    assert app.get("Id") == store.APP_ID
    assert app.get("Executable") == "UniQR\\UniQR.exe"
    assert app.get("EntryPoint") == "Windows.FullTrustApplication"
    task = app.find("m:Extensions/desktop:Extension/desktop:StartupTask", NS)
    assert task.get("Enabled") == "false"
    assert root.find("m:Capabilities/rescap:Capability", NS).get("Name") == "runFullTrust"


def test_every_icon_the_manifest_names_is_drawn_at_its_size(tmp_path):
    from PIL import Image

    build_msix.write_icons(tmp_path)
    text = build_msix.manifest("n", "CN=p", "d")
    for name, size in build_msix.ICONS.items():
        assert f"Assets\\{name}.png" in text
        with Image.open(tmp_path / f"{name}.png") as image:
            assert image.size == size
