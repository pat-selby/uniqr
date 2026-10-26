"""UniQR on a Linux Wayland session, and `UniQR --scan`.

Wayland lets no app read the screen or hear a global hotkey. UniQR reads the
screen through the desktop's screenshot portal instead, and a keyboard shortcut
the person sets in their desktop runs `UniQR --scan`. None of this can run on a
real Wayland desktop here, so the desktop is played by fakes, and what is
checked is UniQR's side: what it asks, how it reads the answer, what it cuts
out, and that it takes no picture except when a scan is asked for.
"""

import socket
import sys
import tempfile
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from uniqr import portal, remote
from uniqr.backends import portable
from uniqr.backends.base import Rect

# -- the portal's small rules ----------------------------------------------------------


def test_the_answer_comes_to_the_path_the_specification_names():
    assert portal.request_path(":1.42", "uniqrab12") == "/org/freedesktop/portal/desktop/request/1_42/uniqrab12"


def test_a_file_address_becomes_a_path():
    assert portal.path_from_uri("file:///tmp/Screenshot%20from%20today.png") == Path("/tmp/Screenshot from today.png")


def test_anything_but_a_file_address_is_refused():
    with pytest.raises(portal.PortalError):
        portal.path_from_uri("https://example.com/shot.png")


# -- a whole screenshot, with the desktop played by a fake -----------------------------------


class FakeDesktop:
    """Enough of a D-Bus connection for portal.screenshot to talk to."""

    def __init__(self, answer_code: int, shot: Path | None):
        self.unique_name = ":1.7"
        self.answer_code = answer_code
        self.shot = shot
        self.sent = []
        self.queue = deque()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def send_and_get_reply(self, message, timeout=None):
        self.sent.append(message)
        return SimpleNamespace(header=SimpleNamespace(message_type=SimpleNamespace(name="method_return")), body=())

    def filter(self, rule):
        desktop = self

        class Subscription:
            def __enter__(self):
                return desktop.queue

            def __exit__(self, *exc):
                return False

        return Subscription()

    def recv_until_filtered(self, queue, timeout=None):
        results = {"uri": ("s", self.shot.as_uri())} if self.shot else {}
        return SimpleNamespace(body=(self.answer_code, results))


@pytest.fixture
def desktop(monkeypatch, tmp_path):
    pytest.importorskip("jeepney")
    import jeepney.io.blocking as blocking

    shot = tmp_path / "Screenshot.png"
    cv2.imwrite(str(shot), np.full((40, 60, 3), 200, np.uint8))
    fake = FakeDesktop(portal.OK, shot)
    monkeypatch.setattr(blocking, "open_dbus_connection", lambda bus="SESSION": fake)
    return fake


def test_a_screenshot_is_read_and_its_file_deleted(desktop):
    image = portal.screenshot()
    assert image.shape == (40, 60, 3)
    assert not desktop.shot.exists(), "no picture of the screen may be left behind"


def test_it_asks_without_the_interactive_dialog(desktop):
    portal.screenshot()
    call = desktop.sent[-1]
    assert call.header.fields[3] == "Screenshot"  # the member
    parent, options = call.body
    assert options["interactive"] == ("b", False)
    assert options["handle_token"][1].startswith("uniqr")


def test_a_refusal_is_an_error_not_a_blank_screen(desktop):
    desktop.answer_code = portal.CANCELLED
    with pytest.raises(portal.PortalError, match="not allowed"):
        portal.screenshot()


# -- the backend on Wayland ---------------------------------------------------------------


@pytest.fixture
def wayland(monkeypatch):
    monkeypatch.setattr(portable, "_on_wayland", lambda: True)
    monkeypatch.setattr(portable, "_scale", None)
    monkeypatch.setattr(portable, "virtual_screen", lambda: Rect(left=0, top=0, width=100, height=50))


def test_the_portals_picture_is_cut_to_the_part_asked_for(wayland, monkeypatch):
    full = np.arange(100 * 200 * 3, dtype=np.uint32).astype(np.uint8).reshape(100, 200, 3)
    monkeypatch.setattr(portal, "screenshot", lambda: full)  # a scaled display: twice the pixels
    assert portable.grab().shape == (100, 200, 3)
    part = portable.grab(Rect(left=10, top=5, width=20, height=10))
    assert part.shape == (20, 40, 3)
    assert np.array_equal(part, full[10:30, 20:60])
    assert portable.scale_factor() == 2.0


def test_the_start_up_check_takes_no_picture(wayland, monkeypatch):
    monkeypatch.setattr(portal, "screenshot", lambda: pytest.fail("no screenshot at start-up"))
    monkeypatch.setattr(portal, "available", lambda: True)
    ok, detail = portable.probe()
    assert ok and "portal" in detail
    assert portable.scale_factor() == 1.0


def test_no_portal_means_a_clear_reason(wayland, monkeypatch):
    monkeypatch.setattr(portal, "available", lambda: False)
    ok, detail = portable.probe()
    assert not ok and "xdg-desktop-portal" in detail


def test_the_hotkey_advice_names_the_scan_command(wayland):
    allowed, detail = portable.input_status()
    assert allowed is False
    assert "--scan" in detail and "keyboard settings" in detail


# -- --scan: the doorbell to the running app --------------------------------------------------

needs_unix_sockets = pytest.mark.skipif(
    sys.platform == "win32" or not hasattr(socket, "AF_UNIX"), reason="Unix sockets: Linux and macOS"
)


@pytest.fixture
def short_path():
    # A Unix socket path is limited to about 100 characters, and pytest's own
    # temporary folders on macOS are longer than that.
    folder = Path(tempfile.mkdtemp(dir="/tmp" if Path("/tmp").exists() else None))
    return folder / "uniqr.sock"


@needs_unix_sockets
def test_scan_reaches_the_running_app(short_path):
    asked = []
    server = remote.Server(lambda: asked.append(1), short_path)
    assert server.start()
    try:
        assert remote.request_scan(short_path) is True
        assert asked == [1]
        assert short_path.stat().st_mode & 0o777 == 0o600, "only its owner may ask"
    finally:
        server.stop()
    assert not short_path.exists()


@needs_unix_sockets
def test_with_nothing_running_scan_says_so(short_path):
    assert remote.request_scan(short_path) is False


@needs_unix_sockets
def test_a_second_uniqr_does_not_take_over_the_first(short_path):
    first = remote.Server(lambda: None, short_path)
    assert first.start()
    try:
        assert remote.Server(lambda: None, short_path).start() is False
    finally:
        first.stop()


@needs_unix_sockets
def test_a_socket_left_by_a_crash_is_replaced(short_path):
    stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stale.bind(str(short_path))
    stale.close()  # the file stays, with nobody listening
    server = remote.Server(lambda: None, short_path)
    assert server.start()
    server.stop()


# -- the app ----------------------------------------------------------------------------------


def test_scan_with_uniqr_running_hands_over_and_leaves(monkeypatch):
    import app

    monkeypatch.setattr(sys, "argv", ["UniQR", "--scan"])
    monkeypatch.setattr(app.remote, "request_scan", lambda: True)
    monkeypatch.setattr(app.logbook, "start", lambda *a: pytest.fail("must not start a second UniQR"))
    assert app.main() == 0


def test_scan_with_nothing_running_starts_uniqr_and_scans(monkeypatch):
    import app

    started = {}

    class FakeUniQR:
        def __init__(self, **kwargs):
            started.update(kwargs)

        def run(self):
            return 0

    monkeypatch.setattr(sys, "argv", ["UniQR", "--scan"])
    monkeypatch.setattr(app.remote, "request_scan", lambda: False)
    monkeypatch.setattr(app.logbook, "start", lambda *a: None)
    monkeypatch.setattr(app, "_claim_instance", lambda restarted: True)
    monkeypatch.setattr(app, "UniQR", FakeUniQR)
    assert app.main() == 0
    assert started["scan_at_start"] is True
