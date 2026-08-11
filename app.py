"""UniQR - press a hotkey, read any QR code on screen.

    python app.py

Runs in the system tray. Press the hotkey (Win+Shift+Q by default) and any QR
code visible anywhere on screen gets decoded and copied to the clipboard.
"""

import sys

from uniqr import actions, backends, capture, overlay
from uniqr.decode import Scanner, payload_kind


def build_shell(on_hotkey, on_notification_click):
    """Pick the shell that matches the capture backend.

    The Win32 shell reserves its hotkey and owns a real message loop; the
    portable one observes keys and hands work to Tk. They expose the same
    surface, so nothing above this line has to know which is in use.
    """
    if backends.NAME == "windows":
        from uniqr.shell import Shell

        return Shell(on_hotkey=on_hotkey, on_notification_click=on_notification_click)

    from uniqr.shell_portable import PortableShell

    return PortableShell(
        on_hotkey=on_hotkey, on_notification_click=on_notification_click
    )


class UniQR:
    def __init__(self) -> None:
        capture.set_dpi_aware()
        self.scanner = Scanner()
        self.last_payload: str | None = None
        self._scanning = False
        self.shell = build_shell(self.scan, self.open_last)

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
        left, top, w, h = det.bbox
        at = (origin[0] + left, origin[1] + top + h + 14)
        kind = payload_kind(det.text)
        opened = overlay.toast(det.text, f"copied {kind}", at)
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
        self.shell.run()
        return 0


def main() -> int:
    if backends.NAME == "windows":
        from uniqr.shell import SingleInstance

        if SingleInstance().already_running:
            print("UniQR is already running - check the system tray.")
            return 1
    try:
        return UniQR().run()
    except KeyboardInterrupt:
        print("\nstopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
