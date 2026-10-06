"""Notice when UniQR stops answering, say where it got stuck, and recover.

Windows closed UniQR twice with "stopped interacting with Windows", and the log
had nothing to say about it: a frozen program cannot write down what it was
doing. So the checking is done from outside the part that can freeze.

    main loop        --- beat() once a second --->  "I am still here"
    watchdog thread  looks at the clock instead     "when did I last hear?"

Quiet for HANG_AFTER seconds, and the thread writes every thread's stack to the
log, which names the exact line the app is stuck on. Quiet for RESTART_AFTER,
and it starts a fresh copy of UniQR and exits. A deliberate Exit never gets
here, so quitting stays quitting.

A small marker file records when UniQR was last seen alive, and whether it
left cleanly. A crash, a kill, or a freeze leaves it saying "alive", and the
next start reports that.
"""

import faulthandler
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import IO, Any

from uniqr import logbook

HANG_AFTER = 10.0
# Longer than any honest scan. The slowest retry ladder measured is under a
# second on one monitor, so this leaves room for a very large desktop.
RESTART_AFTER = 45.0

POLL = 1.0
# If the watchdog thread itself slept far longer than it asked to, the whole
# computer was asleep, not UniQR. Silence across a sleep means nothing.
SUSPEND_GAP = 5.0
# beat() is cheap to call as often as you like; it only does work this often.
BEAT_EVERY = 0.5
ALIVE_EVERY = 30.0
# A second, independent dump, armed in C so it needs no Python thread. It only
# matters if something holds the interpreter so tightly that the watchdog
# thread cannot run; in every other case the thread cancels it first.
BACKUP_GRACE = 5.0

# A freeze that comes straight back after a restart is not going to be fixed
# by restarting again. After this many quick restarts it stops trying.
MAX_QUICK_RESTARTS = 3
STABLE_AFTER = 600.0

RESTARTS_ENV = "UNIQR_RESTARTS"


class AliveMarker:
    """A one-line file: was UniQR running, and did it leave on purpose?"""

    def __init__(self, path: Path, wall: Callable[[], float] = time.time) -> None:
        self.path = path
        self._wall = wall

    def _write(self, state: str) -> None:
        stamp = datetime.fromtimestamp(self._wall()).strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.path.write_text(f"{state} {stamp}\n", encoding="utf-8")
        except OSError:
            pass  # a locked file must never be the reason the app misbehaves

    def previous_unclean(self) -> str | None:
        """When the last run was last seen alive, if it never said goodbye."""
        try:
            text = self.path.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        state, _, when = text.partition(" ")
        return when if state == "alive" and when else None

    def alive(self) -> None:
        self._write("alive")

    def clean(self) -> None:
        self._write("clean")


def _spawn_self(env: dict[str, str]) -> None:
    """Start another UniQR exactly the way this one was started."""
    # orig_argv keeps `python app.py` and `python -m ...` intact. argv alone
    # would lose the interpreter, and sys.executable alone would lose the script.
    argv = [sys.executable, *sys.orig_argv[1:]]
    options: dict[str, Any] = {
        "env": env,
        "cwd": os.getcwd(),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP: outlive this process.
        options["creationflags"] = 0x00000008 | 0x00000200
    else:
        options["start_new_session"] = True
    subprocess.Popen(argv, **options)


def _hard_exit(code: int) -> None:
    """Leave now. A frozen main thread will never take a polite request."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (AttributeError, ValueError, OSError):
            pass
    os._exit(code)


class Watchdog:
    def __init__(
        self,
        handle: IO[str] | None = None,
        marker: AliveMarker | None = None,
        hang_after: float = HANG_AFTER,
        restart_after: float = RESTART_AFTER,
        clock: Callable[[], float] = time.monotonic,
        spawn: Callable[[dict[str, str]], None] = _spawn_self,
        leave: Callable[[int], None] = _hard_exit,
    ) -> None:
        self._handle = handle
        self._marker = marker
        self.hang_after = hang_after
        self.restart_after = restart_after
        self._clock = clock
        self._spawn = spawn
        self._leave = leave

        now = clock()
        self._started = now
        self._last_beat = now
        self._last_check = now
        self._last_arm = float("-inf")
        self._last_alive = float("-inf")
        self._dumped = False
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None

    # -- called from the main loop -------------------------------------------

    def beat(self) -> None:
        """The main loop's way of saying it is still turning over."""
        now = self._clock()
        if self._dumped:
            print(f"UniQR is answering again after {now - self._last_beat:.0f} seconds.")
            self._dumped = False
        self._last_beat = now
        if now - self._last_arm >= BEAT_EVERY:
            self._last_arm = now
            self._arm_backup()
        if self._marker is not None and now - self._last_alive >= ALIVE_EVERY:
            self._last_alive = now
            self._marker.alive()

    def _arm_backup(self) -> None:
        if self._handle is None:
            return
        try:
            faulthandler.dump_traceback_later(
                self.hang_after + BACKUP_GRACE, file=self._handle
            )
        except (ValueError, OSError, AttributeError):
            pass

    def _disarm_backup(self) -> None:
        try:
            faulthandler.cancel_dump_traceback_later()
        except (ValueError, OSError):
            pass

    # -- the watchdog thread -------------------------------------------------

    def start(self) -> None:
        if self._marker is not None:
            self._marker.alive()
            self._last_alive = self._clock()
        self._arm_backup()
        self._thread = threading.Thread(
            target=self._run, name="uniqr-watchdog", daemon=True
        )
        self._thread.start()

    def _run(self) -> None:
        while not self._stopped.wait(POLL):
            self._check()

    def _check(self) -> None:
        """One look at the clock. Separate from the loop so it can be tested."""
        now = self._clock()
        gap, self._last_check = now - self._last_check, now
        if gap > SUSPEND_GAP:
            # The machine slept. Start counting from now.
            self._last_beat = now
            self._dumped = False
            return

        silent = now - self._last_beat
        if silent >= self.hang_after and not self._dumped:
            self._dumped = True
            self._report(silent)
        if silent >= self.restart_after:
            self._recover(now)

    def _report(self, silent: float) -> None:
        print(
            f"UniQR has not answered for {silent:.0f} seconds. "
            "Where each thread is stuck, most recent call first:"
        )
        if self._handle is not None:
            try:
                faulthandler.dump_traceback(file=self._handle, all_threads=True)
            except (ValueError, OSError):
                pass
        # The thread worked, so the C-level backup is no longer needed.
        self._disarm_backup()

    def _recover(self, now: float) -> None:
        quick = 0
        if now - self._started < STABLE_AFTER:
            quick = int(os.environ.get(RESTARTS_ENV, "0") or 0)
        if quick >= MAX_QUICK_RESTARTS:
            print(
                f"UniQR froze again after {quick} quick restarts, so it is not "
                "trying again. It will stay closed until you start it."
            )
            self._leave(1)
            return
        print(
            f"UniQR still has not answered after {now - self._last_beat:.0f} seconds. "
            "Starting a fresh copy and closing this one."
        )
        env = dict(os.environ)
        env[RESTARTS_ENV] = str(quick + 1)
        try:
            self._spawn(env)
        except OSError as exc:
            print(f"could not start a fresh copy: {exc}")
        self._leave(3)

    def stop(self, clean: bool = True) -> None:
        """Called on the way out. `clean` records that leaving was deliberate."""
        self._stopped.set()
        self._disarm_backup()
        if clean and self._marker is not None:
            self._marker.clean()


def start(shell) -> Watchdog:
    """Watch this process. The shell's own loop is what supplies the heartbeat."""
    marker = AliveMarker(logbook.log_path().with_name("uniqr.alive"))
    earlier = marker.previous_unclean()
    if earlier:
        print(
            f"The last run did not exit cleanly. It was last seen alive at {earlier}. "
            "A shutdown, a crash or a freeze would all look like this."
        )
    dog = Watchdog(handle=logbook.handle(), marker=marker)
    shell.set_heartbeat(dog.beat)
    dog.start()
    return dog
