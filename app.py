"""UniQR - press a hotkey, read any QR code on screen.

    python app.py            # run it
    python app.py --quiet    # no card on startup
    python app.py --hotkey '<ctrl>+<alt>+<shift>+q'   # Linux and macOS: another hotkey
    python app.py --hotkey ctrl+alt+k                  # Windows: another hotkey
    python app.py --install-autostart                  # Linux: start at login
    python app.py --uninstall-autostart
    python app.py --open-url https://example.com       # test opening a link, then exit
    python app.py --check-updates                      # ask GitHub for a newer version, then exit
    python app.py --report-problem                     # open a pre-filled GitHub issue, then exit

Runs in the system tray. Press the hotkey (⊞+Shift+Q by default, ⊞ being the Windows logo key) and any QR
code visible anywhere on screen gets decoded and copied to the clipboard.
"""

import os
import sys
import threading
import time

from uniqr import (
    __version__,
    actions,
    autostart,
    backends,
    capture,
    logbook,
    mac_permissions,
    overlay,
    report,
    updates,
    watchdog,
)
from uniqr.decode import Scanner, payload_kind

HOTKEY_BLOCKED = (
    "The hotkey will not reach UniQR: the listener is running but the OS will "
    "not deliver keys to it.\n"
)


def build_shell(
    on_hotkey,
    on_notification_click,
    autostart_enabled=None,
    on_autostart_toggle=None,
    update_enabled=None,
    on_update_toggle=None,
    on_update_check=None,
    on_report=None,
):
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
            update_enabled=update_enabled,
            on_update_toggle=on_update_toggle,
            on_update_check=on_update_check,
            on_report=on_report,
        )

    from uniqr.shell_portable import PortableShell

    return PortableShell(
        on_hotkey=on_hotkey,
        on_notification_click=on_notification_click,
        autostart_enabled=autostart_enabled,
        on_autostart_toggle=on_autostart_toggle,
        update_enabled=update_enabled,
        on_update_toggle=on_update_toggle,
        on_update_check=on_update_check,
        on_report=on_report,
    )


class UniQR:
    def __init__(self, quiet: bool = False, restarted: bool = False) -> None:
        self.quiet = quiet
        self.restarted = restarted
        capture.set_dpi_aware()
        self.scanner = Scanner()
        self.last_payload: str | None = None
        self._scanning = False
        # Update checks: a worker thread does the one request and leaves its answer
        # here. The main thread picks it up on the next heartbeat (see _on_tick),
        # because only that thread may draw a card.
        self._update_enabled = updates.enabled()
        self._update_due = updates.next_check_at()
        self._update_result: tuple[updates.Outcome, bool] | None = None
        self._update_thread: threading.Thread | None = None
        self._update_showing = False
        # Set when the browser would not open the report page, so the next
        # heartbeat can put the address on the clipboard and say so.
        self._report_failed: str | None = None
        can_toggle = autostart.supported()
        can_update = updates.supported()
        self.shell = build_shell(
            self.scan,
            self.open_last,
            autostart.is_enabled if can_toggle else None,
            self.toggle_autostart if can_toggle else None,
            (lambda: self._update_enabled) if can_update else None,
            self.toggle_updates if can_update else None,
            self.check_updates_now if can_update else None,
            self.report_problem,
        )

    def report_problem(self) -> None:
        """The tray menu's "Report a problem": open a pre-filled GitHub issue.

        Nothing is sent. The person reads it, edits it and presses Submit in
        their own browser. This can run on a thread that may not draw, so a
        failure is left for the heartbeat to report.
        """
        url = report.issue_url(__version__)
        print("opening the report page")
        if not actions.open_url(url):
            print("the browser would not open the report page")
            self._report_failed = url

    # -- update checks -----------------------------------------------------------

    def toggle_updates(self) -> None:
        """The tray menu's "Check for updates automatically". A choice made here
        counts as an answer, so the first-run question is not asked afterward."""
        turn_on = not self._update_enabled
        if updates.set_enabled(turn_on):
            self._update_enabled = turn_on
            self._update_due = 0.0  # turned on: check at the next heartbeat
            updates.record_answer(turn_on)
            print(f"automatic update checks are now {'on' if turn_on else 'off'}")
        else:
            print("could not change automatic update checks")

    def check_updates_now(self) -> None:
        """The tray menu's "Check for updates now". Asked for, so it always answers."""
        self._start_update_check(manual=True)

    def _start_update_check(self, manual: bool) -> None:
        thread = self._update_thread
        if thread is not None and thread.is_alive():
            return  # one at a time

        def work() -> None:
            self._update_result = (updates.check(__version__), manual)

        self._update_thread = threading.Thread(target=work, name="update-check", daemon=True)
        self._update_thread.start()

    def _on_tick(self) -> None:
        """Once a second on the main thread: start a check that is due, and show
        the result of one that has finished."""
        if self.shell.stopping:
            return
        if self._report_failed is not None and not self._scanning:
            url, self._report_failed = self._report_failed, None
            self._tell_report_failed(url)
        if self._update_enabled and time.time() >= self._update_due:
            self._update_due = time.time() + updates.CHECK_EVERY_S
            updates.record_check()
            self._start_update_check(manual=False)
        if self._update_result is None or self._update_showing or self._scanning:
            return
        outcome, manual = self._update_result
        self._update_result = None
        self._update_showing = True
        try:
            self._show_update(outcome, manual)
        finally:
            self._update_showing = False

    def _tell_report_failed(self, url: str) -> None:
        """The browser would not open: leave the address where it can be pasted."""
        try:
            actions.copy(url)
            message = "Could not open your browser. The report page address is on your clipboard."
        except Exception as exc:  # noqa: BLE001
            print(f"could not copy the report address either: {exc}")
            message = "Could not open your browser. See the log."
        screen = capture.monitor_at(0, 0)
        overlay.toast("", message, self._corner(screen), 4500, hover_pause=False)

    def _show_update(self, outcome: updates.Outcome, manual: bool) -> None:
        screen = capture.monitor_at(0, 0)
        if outcome.status == "newer" and outcome.release is not None:
            version = outcome.release.version
            if not manual and updates.already_told(version):
                return  # once per version, not once a day
            updates.record_told(version)
            print(f"update available: {version}")
            answer = overlay.ask(
                f"UniQR {version} is available.",
                f"You have {__version__}. Open the download page?",
                ("Open download page", "Later"),
                (screen.right - 400, screen.bottom - 175),
                timeout_ms=20000,
                until=lambda: self.shell.stopping,
            )
            if answer:
                actions.open_url(outcome.release.url)
        elif outcome.status == "current":
            print(f"update check: UniQR {__version__} is up to date")
            if manual:
                overlay.toast(
                    "", f"UniQR is up to date ({__version__}).", self._corner(screen), 2500,
                    hover_pause=False,
                )
        else:
            print(f"update check failed: {outcome.detail}")
            if manual:
                overlay.toast(
                    "", "Could not check for updates. See the log.", self._corner(screen), 3500,
                    hover_pause=False,
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
            if sys.platform == "darwin":
                self._help_mac_permission("screen")
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
                    "macOS: if the hotkey does nothing, switch on "
                    f"{mac_permissions.who()} under Accessibility in\n"
                    "System Settings > Privacy & Security, then restart UniQR."
                )
            # A started listener is not a working one. Where the OS can be
            # asked, say so up front rather than letting the user press the
            # hotkey at a program that will never hear it.
            allowed, detail = capture.input_status()
            if allowed is False:
                print(HOTKEY_BLOCKED + detail)
                if sys.platform == "darwin":
                    self._help_mac_permission("keys")
        self._greet(label)

        if self.shell.stopping:
            # Exit was chosen while the greeting card was up. Everything below
            # needs the shell's window, which is gone, and carrying on crashed
            # start-up with "Invalid window handle".
            return 0

        dog = watchdog.start(self.shell, self._on_tick)
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
            elif updates.should_ask(self.quiet, self.restarted):
                # One question per start. This one waits for a start where the
                # login question is not being asked.
                self._greet_and_ask_updates(message, screen)
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

    def _greet_and_ask_updates(self, message: str, screen) -> None:
        """The same card with the other question. Nothing is sent unless it is yes."""
        print("asking whether to check for updates")
        answer = overlay.ask(
            message,
            "Check for new versions once a day? UniQR asks GitHub and sends nothing else.",
            ("Yes, check daily", "No thanks"),
            (screen.right - 400, screen.bottom - 175),
            until=lambda: self.shell.stopping,
        )
        updates.record_answer(answer, stopping=self.shell.stopping)
        if not answer:
            print("update checks: no thanks" if answer is False else "update checks: no answer")
            return
        if updates.set_enabled(True):
            self._update_enabled = True
            self._update_due = 0.0  # check at the first heartbeat
            print("update checks: on. Turn them off from the tray menu.")
        else:
            print("update checks: could not be saved")

    def _help_mac_permission(self, kind: str) -> None:
        """A Mac permission is missing: say so on screen, not only in the log.

        A downloaded UniQR.app has no Terminal to print to, so without this it
        would quit, or sit deaf to the hotkey, with nothing visible at all.
        """
        mac_permissions.ask_macos(kind)
        if self.quiet:
            return
        heading, note = mac_permissions.message(kind)
        print(f"{heading}. {note}")
        screen = capture.monitor_at(0, 0)
        try:
            answer = overlay.ask(
                heading, note, ("Open Settings", "Not now"),
                (screen.right - 420, screen.bottom - 200),
                until=lambda: self.shell.stopping,
            )
        except Exception as exc:  # noqa: BLE001 - help must not stop start-up
            print(f"could not show the permission card: {exc}")
            return
        if answer:
            mac_permissions.open_settings(kind)

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
    if "--report-problem" in sys.argv:
        url = report.issue_url(__version__)
        print("Opening a pre-filled report page in your browser. Nothing is sent:")
        print("you read it, change it and press Submit yourself.")
        if actions.open_url(url):
            return 0
        print("Could not open a browser. Open this address yourself:")
        print(url)
        return 1
    if "--check-updates" in sys.argv:
        outcome = updates.check(__version__)
        if outcome.status == "newer" and outcome.release is not None:
            print(f"UniQR {outcome.release.version} is available. You have {__version__}.")
            print(outcome.release.url)
            return 0
        if outcome.status == "current":
            print(f"UniQR is up to date ({__version__}).")
            return 0
        print(f"Could not check for updates: {outcome.detail}")
        return 1
    link = autostart.option(sys.argv, "--open-url")
    if link:
        opened = actions.open_url(link)
        print("opened it" if opened else "could not open it (see the lines above)")
        return 0 if opened else 1
    # The same setting as the UNIQR_HOTKEY environment variable, without needing
    # to know it exists. Read when the hotkey is registered, so setting it here is
    # early enough. Windows reads it too, in its own plain form: ctrl+alt+k.
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
