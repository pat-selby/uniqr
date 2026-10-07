"""The watchdog: notice a freeze, record where it is, restart, and not loop.

Most of this runs on a fake clock, so "ten seconds of silence" costs nothing.
One test uses a real thread and a real clock, to prove the pieces are actually
connected rather than only correct in isolation.
"""

import sys
import threading
from pathlib import Path

import pytest
from uniqr import watchdog
from uniqr.watchdog import AliveMarker, Watchdog


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Recorder:
    """Stands in for 'start a new copy' and 'exit', which tests must not do."""

    def __init__(self) -> None:
        self.spawned: list[dict[str, str]] = []
        self.left: list[int] = []

    def spawn(self, env: dict[str, str]) -> None:
        self.spawned.append(env)

    def leave(self, code: int) -> None:
        self.left.append(code)


@pytest.fixture
def rig(tmp_path, monkeypatch):
    monkeypatch.delenv(watchdog.RESTARTS_ENV, raising=False)
    clock, rec = Clock(), Recorder()
    log = (tmp_path / "log.txt").open("a+", encoding="utf-8")
    dog = Watchdog(
        handle=log,
        marker=AliveMarker(tmp_path / "uniqr.alive"),
        hang_after=10,
        restart_after=45,
        clock=clock,
        spawn=rec.spawn,
        leave=rec.leave,
    )
    yield clock, rec, dog, log
    dog.stop(clean=False)
    log.close()


def advance(clock: Clock, dog: Watchdog, seconds: float, beating: bool) -> None:
    """Move time on one second at a time, the way the real thread would."""
    for _ in range(int(seconds)):
        clock.now += 1
        if beating:
            dog.beat()
        dog._check()


def test_a_running_app_is_left_alone(rig):
    clock, rec, dog, _ = rig
    advance(clock, dog, 120, beating=True)
    assert rec.spawned == [] and rec.left == []


def test_a_freeze_writes_the_stack_to_the_log(rig, capsys):
    clock, _, dog, log = rig
    advance(clock, dog, 11, beating=False)
    log.flush()
    assert "has not answered for 10 seconds" in capsys.readouterr().out
    written = Path(log.name).read_text(encoding="utf-8")
    # faulthandler's own format: it names the thread and the line of code.
    assert "most recent call first" in written
    assert "test_watchdog.py" in written


def test_the_stack_is_written_once_not_every_second(rig):
    clock, _, dog, log = rig
    advance(clock, dog, 30, beating=False)
    log.flush()
    assert Path(log.name).read_text(encoding="utf-8").count("most recent call first") == 1


def test_a_short_stall_that_recovers_says_so(rig, capsys):
    clock, rec, dog, _ = rig
    advance(clock, dog, 12, beating=False)
    advance(clock, dog, 1, beating=True)
    assert "answering again after" in capsys.readouterr().out
    assert rec.spawned == [] and rec.left == []


def test_a_long_freeze_starts_a_fresh_copy_and_exits(rig):
    clock, rec, dog, _ = rig
    advance(clock, dog, 46, beating=False)
    assert len(rec.spawned) >= 1
    assert rec.spawned[0][watchdog.RESTARTS_ENV] == "1"
    assert rec.left[0] == 3


def test_restarting_stops_after_repeated_quick_failures(rig, monkeypatch):
    clock, rec, dog, _ = rig
    monkeypatch.setenv(watchdog.RESTARTS_ENV, str(watchdog.MAX_QUICK_RESTARTS))
    advance(clock, dog, 46, beating=False)
    assert rec.spawned == [], "must not start another copy of a copy that keeps freezing"
    assert rec.left[0] == 1


def test_a_long_healthy_run_forgives_earlier_restarts(rig, monkeypatch):
    clock, rec, dog, _ = rig
    monkeypatch.setenv(watchdog.RESTARTS_ENV, str(watchdog.MAX_QUICK_RESTARTS))
    advance(clock, dog, int(watchdog.STABLE_AFTER) + 5, beating=True)
    advance(clock, dog, 46, beating=False)
    assert rec.spawned[0][watchdog.RESTARTS_ENV] == "1"


def test_sleeping_through_the_silence_is_not_a_freeze(rig):
    clock, rec, dog, _ = rig
    advance(clock, dog, 5, beating=True)
    clock.now += 3600  # the lid was closed for an hour
    dog._check()
    advance(clock, dog, 5, beating=True)
    assert rec.spawned == [] and rec.left == []


def test_marker_reports_a_run_that_never_said_goodbye(tmp_path):
    marker = AliveMarker(tmp_path / "uniqr.alive", wall=lambda: 1_700_000_000)
    assert marker.previous_unclean() is None  # first ever run
    marker.alive()
    assert marker.previous_unclean() is not None  # then it vanished
    marker.clean()
    assert marker.previous_unclean() is None  # a proper exit forgives it


def test_leaving_on_purpose_is_recorded_as_clean(rig):
    _, _, dog, _ = rig
    dog.start()
    assert dog._marker.previous_unclean() is not None
    dog.stop(clean=True)
    assert dog._marker.previous_unclean() is None


def test_a_real_thread_notices_a_real_freeze(tmp_path, monkeypatch):
    """The whole chain, with nothing faked but the dangerous two actions."""
    monkeypatch.setattr(watchdog, "POLL", 0.05)
    monkeypatch.delenv(watchdog.RESTARTS_ENV, raising=False)
    rec, left = Recorder(), threading.Event()
    log = (tmp_path / "log.txt").open("a+", encoding="utf-8")
    dog = Watchdog(
        handle=log,
        hang_after=0.2,
        restart_after=0.5,
        spawn=rec.spawn,
        leave=lambda code: (rec.leave(code), left.set()),
    )
    try:
        dog.start()
        dog.beat()  # then silence: the main loop has "frozen"
        assert left.wait(5), "the watchdog never acted on a frozen app"
    finally:
        dog.stop(clean=False)
        log.close()
    assert rec.left[0] == 3 and rec.spawned


@pytest.mark.skipif(sys.platform != "win32", reason="the Win32 shell is Windows only")
def test_the_windows_shell_delivers_heartbeats():
    """The logic above never touches the real shell, and that is where a
    missing SetTimer in pywin32 hid until it was run for real."""
    import time

    import win32gui
    from uniqr.shell import Shell

    try:
        shell = Shell(on_hotkey=lambda: None)
    except win32gui.error:
        pytest.skip("no desktop session to create a window in")
    beats: list[int] = []
    try:
        shell.set_heartbeat(lambda: beats.append(1))
        end = time.monotonic() + 2.4
        while time.monotonic() < end:
            win32gui.PumpWaitingMessages()
            time.sleep(0.02)
    finally:
        shell.stop()
    assert len(beats) >= 2, f"only {len(beats)} beats in 2.4s"


def test_a_packaged_exe_restarts_itself_with_a_clean_environment(monkeypatch):
    """A one-file PyInstaller build must unpack its own folder when it restarts,
    or the new copy runs from a folder the old copy deletes on exit."""
    launched = {}

    def fake_popen(argv, **options):
        launched["argv"], launched["env"] = argv, options["env"]

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/apps/UniQR.exe")
    monkeypatch.setattr(sys, "argv", ["/apps/UniQR.exe", "--quiet"])
    monkeypatch.setattr(watchdog.subprocess, "Popen", fake_popen)

    watchdog._spawn_self({"PATH": "x"})

    assert launched["argv"] == ["/apps/UniQR.exe", "--quiet"]
    assert launched["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    assert launched["env"]["PATH"] == "x"


def test_a_normal_run_restarts_with_the_same_command_line(monkeypatch):
    launched = {}
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "orig_argv", ["python", "app.py", "--quiet"])
    monkeypatch.setattr(
        watchdog.subprocess,
        "Popen",
        lambda argv, **options: launched.update(argv=argv, env=options["env"]),
    )
    watchdog._spawn_self({"A": "1"})
    assert launched["argv"] == [sys.executable, "app.py", "--quiet"]
    assert "PYINSTALLER_RESET_ENVIRONMENT" not in launched["env"]
