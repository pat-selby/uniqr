"""UniQR - press a hotkey, read any QR code on screen.

    python app.py            # run it
    python app.py --quiet    # no card on startup
    python app.py --hotkey '<ctrl>+<alt>+<shift>+q'   # Linux and macOS: another hotkey
    python app.py --install-autostart                  # Linux: start at login
    python app.py --uninstall-autostart
    python app.py --open-url https://example.com       # test opening a link, then exit

Runs in the system tray. Press the hotkey (Win+Shift+Q by default) and any QR
code visible anywhere on screen gets decoded and copied to the clipboard.
"""

import os
import sys
import time

from uniqr import actions, autostart, backends, capture, logbook, overlay, watchdog
from uniqr.decode import Scanner, payload_kind

HOTKEY_BLOCKED = (
    "The hotkey will not reach UniQR: the listener is running but the OS will "
    "not deliver keys to it.\n"
)


def build_shell(on_hotkey, on_notification_click, autostart_enabled=None, on_autostart_toggle=None):
    """Pick the shell that matches the capture backend.

    The Win32 shell reserves its hotkey and owns a real message loop; the
    portable one observes keys and hands work to Tk. They expose the same
    surface, so nothing above this line has to know which is in use.
    """
    if backends.NAME == "windows":
        from uniqr.shell import Shell

        return Shell(
            on_hotkey=on_hotkey,
            on_notification_click=on_notification_click,
            autostart_enabled=autostart_enabled,
            on_autostart_toggle=on_autostart_toggle,
        )

    from uniqr.shell_portable import PortableShell

    return PortableShell(
        on_hotkey=on_hotkey,
        on_notification_click=on_notification_click,
        autostart_enabled=autostart_enabled,
        on_autostart_toggle=on_autostart_toggle,
    )


class UniQR:
    def __init__(self, quiet: bool = False, restarted: bool = False) -> None:
        self.quiet = quiet
        self.restarted = restarted
        capture.set_dpi_aware()
        self.scanner = Scanner()
        self.last_payload: str | None = None
        self._scanning = False
        can_toggle = autostart.supported()
        self.shell = build_shell(
            self.scan,
            self.open_last,
            autostart.is_enabled if can_toggle else None,
            self.toggle_autostart if can_toggle else None,
        )

    def toggle_autostart(self) -> None:
        """The tray menu's "Start at login": flip it. A choice made here counts
        as an answer, so the first-run question is not asked afterward."""
        turn_on = not autostart.is_enabled()
        if autostart.set_enabled(turn_on):
            autostart.record_answer(turn_on)
            print(f"start at login is now {'on' if turn_on else 'off'}")
        else:
            print("could not change start at login")

    def scan(self) -> None:
        # The overlay runs its own event loop inside this handler, so a second
        # hotkey press while it is open would nest another one.
        if self._scanning:
            return
        self._scanning = True
        try:
            self._scan()
        finally:
            self._scanning = False

    def _scan(self) -> None:
        rect = capture.virtual_screen()
        shot = capture.grab(rect)
        found = self.scanner.scan(shot)

        origin = (rect.left, rect.top)

        if not found:
            self.last_payload = None
            overlay.toast(
                "", "No QR code found on screen", capture.cursor_pos(), timeout_ms=1200
            )
            return

        # Reading order, so numbering matches how the codes look on screen.
        found.sort(key=lambda d: (d.center[1] // 100, d.center[0]))
        for det in found:
            print(f"[{payload_kind(det.text)}] {det.text}")

        if len(found) == 1:
            self._take("copy", found[0], origin)
            return

        # Several codes: copying one of them for the user would be a guess, so
        # show them where the codes are and let them pick.
        choice = overlay.pick(shot, found, origin=origin)
        if choice is None:
            return
        action, det = choice
        self._take(action, det, origin)

    def _take(self, action: str, det, origin: tuple[int, int]) -> None:
        self.last_payload = det.text
        actions.copy(det.text)
        if action == "open" and actions.open_url(det.text):
            self.shell.set_tooltip(f"UniQR - opened {actions.summarize(det.text, 60)}")
            return

        # Deliberately our own window rather than a tray balloon: Do Not
        # Disturb swallows balloons, which would leave a scan looking dead.
        # overlay.below turns the code's image-pixel box into the screen
        # point the card goes at, which differs on a Retina display.
        at = overlay.below(det.bbox, origin)
        # The card labels the kind of code itself; this is the status line.
        heading = "Copied" if det.symbology == "QR Code" else f"Copied · {det.symbology}"
        opened = overlay.toast(det.text, heading, at)
        self.shell.set_tooltip(
            f"UniQR - {'opened' if opened else 'copied'} "
            f"{actions.summarize(det.text, 60)}"
        )

    def open_last(self) -> None:
        if self.last_payload:
            actions.open_url(self.last_payload)

    def run(self) -> int:
        print(f"UniQR on {sys.platform} using the {backends.NAME} backend.")

        ok, detail = capture.probe()
        print(f"screen capture: {detail}")
        if not ok:
            print("Cannot read the screen, so scanning would find nothing.")
            return 4

        # The portable shell needs its tray started explicitly, and may not get
        # one at all; the Win32 shell adds its icon during construction.
        if hasattr(self.shell, "start_tray"):
            self.shell.start_tray()

        label = self.shell.register_hotkey()
        if label is None:
            print("Could not register any hotkey.")
            print("UniQR still works: use the tray icon to scan.")
            self.shell.notify("Hotkey unavailable", "Use the tray icon to scan.")
        else:
            print(f"UniQR is running. Press {label} to scan the screen.")
            if getattr(self.shell, "tray_available", True):
                print("Right-click the tray icon to exit.")
            else:
                print("No tray icon on this platform - Ctrl+C here to exit.")
            if sys.platform == "darwin":
                print(
                    "macOS: if the hotkey does nothing, grant Input Monitoring in\n"
                    "System Settings > Privacy & Security, then restart UniQR."
                )
            # A started listener is not a working one. Where the OS can be
            # asked, say so up front rather than letting the user press the
            # hotkey at a program that will never hear it.
            allowed, detail = capture.input_status()
            if allowed is False:
                print(HOTKEY_BLOCKED + detail)
        self._greet(label)

        if self.shell.stopping:
            # Exit was chosen while the greeting card was up. Everything below
            # needs the shell's window, which is gone, and carrying on crashed
            # start-up with "Invalid window handle".
            return 0

        dog = watchdog.start(self.shell)
        clean = False
        try:
            self.shell.run()
            clean = True
        except KeyboardInterrupt:
            clean = True  # Ctrl+C is a deliberate way to leave
            raise
        finally:
            dog.stop(clean=clean)
        return 0

    def _greet(self, label: str | None) -> None:
        """A card on startup, so a silent failure to start is visible.

        Under pythonw there is no console, so without this the only difference
        between "running" and "crashed while starting" is a tray icon nobody
        looks at. It also names the hotkey actually registered, which matters
        because UniQR falls back when the first combination is already taken.
        """
        if self.quiet:
            return
        message = (
            f"UniQR is running. Press {label} to scan."
            if label
            else "UniQR is running, but no hotkey was free. Use the tray icon."
        )
        screen = capture.monitor_at(0, 0)  # the monitor holding the origin
        try:
            if autostart.should_ask(self.quiet, self.restarted):
                self._greet_and_ask(message, screen)
            else:
                overlay.toast("", message, (screen.right - 360, screen.bottom - 130))
        except Exception as exc:  # noqa: BLE001 - a greeting must not stop startup
            print(f"could not show the startup card: {exc}")

    def _greet_and_ask(self, message: str, screen) -> None:
        """The first run: the same card, with one question on it.

        It does not turn anything on by itself. A program that adds itself to
        the start-up list without asking is behaving like malware, and this one
        reads the screen.
        """
        print("asking whether to start at login")
        answer = overlay.ask(
            message,
            "Start UniQR automatically when you log in?",
            ("Yes, start at login", "Not now"),
            (screen.right - 400, screen.bottom - 175),
            # Quitting from the tray while the question is up must not wait for it.
            until=lambda: self.shell.stopping,
        )
        autostart.record_answer(answer, stopping=self.shell.stopping)
        if not answer:
            print("start at login: not now" if answer is False else "start at login: no answer")
            return
        if autostart.set_enabled(True):
            how = (
                "Turn it off from the tray menu."
                if getattr(self.shell, "tray_available", True)
                else "Turn it off with --uninstall-autostart."
            )
            # Logged first: the card below holds up start-up until it closes.
            print(f"start at login: on. {how}")
            overlay.toast(
                "", "UniQR will start when you log in.", self._corner(screen), 2500,
                hover_pause=False,
            )
        else:
            print("start at login: could not be set up")
            overlay.toast(
                "", "Could not set up start at login. See the log.", self._corner(screen), 4000,
                hover_pause=False,
            )

    @staticmethod
    def _corner(screen) -> tuple[int, int]:
        return (screen.right - 360, screen.bottom - 130)


def _claim_instance(restarted: bool) -> bool:
    """False if another UniQR holds the single-instance mutex (Windows only).

    A copy that was started by the watchdog is born while the frozen one is
    still being torn down, so it waits a few seconds for the mutex rather than
    taking the first "already running" as the answer.
    """
    from uniqr.shell import SingleInstance

    for _ in range(20 if restarted else 1):
        if not SingleInstance().already_running:
            return True
        time.sleep(0.5)
    return False


def main() -> int:
    # These two only change a settings file and exit. They run before the log
    # starts and before anything else, so they work with UniQR not running.
    done = autostart.handle_command_line(sys.argv)
    if done is not None:
        return done
    # Opens one link the way the Open button does, says whether it worked, and
    # exits. For finding out why Open does nothing on a given machine.
    link = autostart.option(sys.argv, "--open-url")
    if link:
        opened = actions.open_url(link)
        print("opened it" if opened else "could not open it (see the lines above)")
        return 0 if opened else 1
    # The same setting as the UNIQR_HOTKEY environment variable, without needing
    # to know it exists. Read when the hotkey is registered, so setting it here is
    # early enough. Windows has its own fixed list and ignores it.
    hotkey = autostart.option(sys.argv, "--hotkey")
    if hotkey:
        os.environ["UNIQR_HOTKEY"] = hotkey

    logbook.start(sys.argv)
    quiet = "--quiet" in sys.argv
    restarted = bool(os.environ.get(watchdog.RESTARTS_ENV))
    if restarted:
        print(
            "UniQR restarted itself because the last copy stopped answering "
            f"(restart {os.environ[watchdog.RESTARTS_ENV]})."
        )
        if backends.NAME != "windows":
            time.sleep(1)  # let the old copy finish exiting
    if backends.NAME == "windows" and not _claim_instance(restarted):
        print("UniQR is already running - check the system tray.")
        return 1
    try:
        return UniQR(quiet=quiet, restarted=restarted).run()
    except KeyboardInterrupt:
        print("\nstopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
