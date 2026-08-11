"""macOS / Linux shell: pynput for the hotkey, pystray for the tray icon.

Threading here is dictated by Tk, not by preference. macOS requires Tk to own
the main thread, so the Tk root's mainloop is the process's main loop and
everything else reports in to it:

    pynput listener thread  --\
                               >-- queue --> Tk main loop --> scan / overlay
    pystray tray thread     --/

A hotkey callback must never touch Tk from its own thread, so it only ever
puts a token on the queue; the Tk loop polls and does the work.

Two platform caveats, both of which need the user's involvement:

  * macOS needs Input Monitoring (or Accessibility) permission before pynput
    receives any keys, and Screen Recording before capture returns pixels.
    Neither failure raises - they just silently do nothing.
  * pynput observes keys rather than reserving them, so unlike Win32's
    RegisterHotKey it cannot report that a combination is already taken. If
    another app owns the shortcut, both will fire.
"""

import os
import queue
import sys
import threading
from typing import Callable

from uniqr.icon import icon_image

POLL_MS = 60

# pynput hotkey syntax. Deliberately avoiding cmd+shift+q on macOS, which is
# Log Out, and cmd+q, which is Quit.
HOTKEY_CHOICES = {
    "darwin": [
        ("<ctrl>+<alt>+q", "Control+Option+Q"),
        ("<ctrl>+<shift>+q", "Control+Shift+Q"),
        ("<cmd>+<ctrl>+q", "Command+Control+Q"),
    ],
    "default": [
        ("<ctrl>+<alt>+q", "Ctrl+Alt+Q"),
        ("<ctrl>+<shift>+q", "Ctrl+Shift+Q"),
        ("<super>+<shift>+q", "Super+Shift+Q"),
    ],
}


def hotkey_choices() -> list[tuple[str, str]]:
    """Candidate combinations, best first.

    UNIQR_HOTKEY overrides the list entirely, in pynput syntax - for example
    `UNIQR_HOTKEY='<cmd>+<shift>+8'`. This matters inside a virtual machine,
    where the hypervisor often claims Ctrl+Alt as its host key and the guest
    never sees it.
    """
    override = os.environ.get("UNIQR_HOTKEY", "").strip()
    if override:
        return [(override, override)]
    return HOTKEY_CHOICES.get(sys.platform, HOTKEY_CHOICES["default"])


class PortableShell:
    """Same surface as the Windows Shell, different machinery underneath."""

    def __init__(
        self,
        on_hotkey: Callable[[], None],
        on_notification_click: Callable[[], None] | None = None,
        tooltip: str = "UniQR",
    ) -> None:
        from uniqr import overlay

        self.on_hotkey = on_hotkey
        self.on_notification_click = on_notification_click
        self.tooltip = tooltip
        self.hotkey_label = ""
        self.tray_available = False

        self._queue: queue.Queue[str] = queue.Queue()
        self._listener = None
        self._icon = None
        self._stopping = False
        self.root = overlay.shared_root()

    # -- setup ---------------------------------------------------------------

    def register_hotkey(self) -> str | None:
        """Start listening for the first combination pynput will take.

        Success here means "the listener started", not "the shortcut is ours" -
        see the note at the top of this module.
        """
        from pynput import keyboard

        for combo, label in hotkey_choices():
            try:
                listener = keyboard.GlobalHotKeys(
                    {combo: lambda: self._queue.put("scan")}
                )
                listener.daemon = True
                listener.start()
            except Exception:  # noqa: BLE001 - backend-specific failures vary
                continue
            self._listener = listener
            self.hotkey_label = label
            return label
        return None

    def start_tray(self) -> bool:
        """Best-effort tray icon.

        pystray wants the main thread on macOS, which Tk already owns, so this
        is expected to fail there. The hotkey is the primary interface; the
        tray is a convenience, so a failure is reported and not fatal.
        """
        try:
            import pystray

            menu = pystray.Menu(
                pystray.MenuItem(
                    lambda _item: (
                        f"Scan now ({self.hotkey_label})"
                        if self.hotkey_label
                        else "Scan now"
                    ),
                    lambda: self._queue.put("scan"),
                    default=True,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit UniQR", lambda: self._queue.put("quit")),
            )
            self._icon = pystray.Icon(
                "UniQR", icon_image(64), self.tooltip, menu=menu
            )
            thread = threading.Thread(target=self._icon.run, daemon=True)
            thread.start()
            thread.join(timeout=1.5)
            self.tray_available = thread.is_alive()
            return self.tray_available
        except Exception as exc:  # noqa: BLE001
            print(f"tray icon unavailable ({exc}); hotkey still works")
            self._icon = None
            return False

    # -- output --------------------------------------------------------------

    def set_tooltip(self, text: str) -> None:
        if self._icon is not None:
            try:
                self._icon.title = text[:127]
            except Exception:  # noqa: BLE001
                pass

    def notify(self, title: str, message: str) -> None:
        """Prefer a system notification, but never depend on one."""
        if self._icon is not None:
            try:
                self._icon.notify(message, title)
                return
            except Exception:  # noqa: BLE001
                pass
        print(f"{title}: {message}")

    # -- lifecycle -----------------------------------------------------------

    def _pump(self) -> None:
        """Drain the queue on the Tk thread, where UI work is legal."""
        try:
            while True:
                item = self._queue.get_nowait()
                if item == "scan":
                    self.on_hotkey()
                elif item == "quit":
                    self.stop()
                    return
        except queue.Empty:
            pass
        if not self._stopping:
            self.root.after(POLL_MS, self._pump)

    def run(self) -> None:
        self.root.after(POLL_MS, self._pump)
        self.root.mainloop()

    def stop(self) -> None:
        self._stopping = True
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:  # noqa: BLE001
                pass
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:  # noqa: BLE001
                pass
        try:
            self.root.quit()
        except Exception:  # noqa: BLE001
            pass
