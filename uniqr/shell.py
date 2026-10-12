"""The Windows shell: an invisible window that owns the hotkey and tray icon.

Windows delivers input and tray events as messages, and only a window can
receive messages - so a background app needs a window even though it never
shows one. This module creates that window and routes what arrives at it.
"""

import ctypes
from ctypes import wintypes
from typing import Callable

import win32api
import win32con
import win32event
import win32gui

from uniqr.icon import ensure_icon

WM_TRAYICON = win32con.WM_USER + 20
NIN_BALLOONUSERCLICK = win32con.WM_USER + 5

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

IDM_SCAN = 1001
IDM_EXIT = 1002
IDM_AUTOSTART = 1003

HOTKEY_ID = 1
HEARTBEAT_ID = 2
HEARTBEAT_MS = 1000

# Tried in order. Win+Shift+Q is the one we want; the rest are escape hatches
# for when another app already claimed it.
HOTKEY_CHOICES = [
    (MOD_WIN | MOD_SHIFT, ord("Q"), "Win+Shift+Q"),
    (MOD_CONTROL | MOD_ALT, ord("Q"), "Ctrl+Alt+Q"),
    (MOD_CONTROL | MOD_SHIFT, ord("9"), "Ctrl+Shift+9"),
]


class SingleInstance:
    """A named mutex so a second copy exits instead of fighting for the hotkey."""

    def __init__(self, name: str = "UniQR.SingleInstance") -> None:
        self._handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
        self.already_running = ctypes.windll.kernel32.GetLastError() == 183  # EXISTS
        if self.already_running:
            # Hand back the handle we just opened to the other copy's mutex.
            # Left open, it would keep that mutex alive after the other copy
            # exits, and a restarted UniQR would find itself "already running"
            # because of its own earlier attempt.
            ctypes.windll.kernel32.CloseHandle(self._handle)


class Shell:
    def __init__(
        self,
        on_hotkey: Callable[[], None],
        on_notification_click: Callable[[], None] | None = None,
        tooltip: str = "UniQR",
        autostart_enabled: Callable[[], bool] | None = None,
        on_autostart_toggle: Callable[[], None] | None = None,
    ) -> None:
        self.on_hotkey = on_hotkey
        self.on_notification_click = on_notification_click
        # Both given: the tray menu gets a "Start at login" item, checked when on.
        self.autostart_enabled = autostart_enabled
        self.on_autostart_toggle = on_autostart_toggle
        self.tooltip = tooltip
        self.hotkey_label = ""
        self._hicon = None
        self._heartbeat: Callable[[], None] | None = None
        self._quit = False
        self.hwnd = self._create_window()
        self._add_tray_icon()

    # -- setup ---------------------------------------------------------------

    def _create_window(self) -> int:
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "UniQRHiddenWindow"
        wc.lpfnWndProc = {
            WM_TRAYICON: self._on_tray_message,
            win32con.WM_HOTKEY: self._on_hotkey_message,
            win32con.WM_COMMAND: self._on_command,
            win32con.WM_TIMER: self._on_timer,
            win32con.WM_DESTROY: self._on_destroy,
        }
        class_atom = win32gui.RegisterClass(wc)
        return win32gui.CreateWindow(
            class_atom,
            "UniQR",
            0,  # no style: never shown
            0,
            0,
            0,
            0,
            0,
            0,
            wc.hInstance,
            None,
        )

    def _add_tray_icon(self) -> None:
        self._hicon = win32gui.LoadImage(
            0,
            ensure_icon(),
            win32con.IMAGE_ICON,
            0,
            0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
        )
        win32gui.Shell_NotifyIcon(
            win32gui.NIM_ADD,
            (
                self.hwnd,
                0,
                win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
                WM_TRAYICON,
                self._hicon,
                self.tooltip,
            ),
        )

    def register_hotkey(self) -> str | None:
        """Claim the first hotkey combination Windows will give us."""
        for mods, vk, label in HOTKEY_CHOICES:
            try:
                win32gui.RegisterHotKey(self.hwnd, HOTKEY_ID, mods | MOD_NOREPEAT, vk)
            except win32gui.error:
                continue
            self.hotkey_label = label
            self.set_tooltip(f"UniQR - press {label} to scan")
            return label
        return None

    @property
    def stopping(self) -> bool:
        """True once Exit has been chosen, even if run() has not started yet.

        Exit can arrive while the greeting card is still up, before the main
        loop exists. The window is gone by then, and anything that needs it
        (the heartbeat timer, the loop itself) must be skipped.
        """
        return self._quit

    def set_heartbeat(self, beat: Callable[[], None]) -> None:
        """Call `beat` once a second for as long as the message loop is turning.

        A timer on the hidden window, so it only fires if this thread is
        really pulling messages. That includes the nested loops the picker and
        the cards run while they wait, which is why a card left open for a
        minute does not look like a freeze.
        """
        if self._quit:
            return  # the window is already gone
        self._heartbeat = beat
        # Through user32 directly: pywin32 does not expose SetTimer everywhere.
        user32 = ctypes.windll.user32
        user32.SetTimer.argtypes = [
            wintypes.HWND, wintypes.WPARAM, wintypes.UINT, ctypes.c_void_p,
        ]
        user32.SetTimer.restype = wintypes.WPARAM
        if not user32.SetTimer(self.hwnd, HEARTBEAT_ID, HEARTBEAT_MS, None):
            raise ctypes.WinError()

    # -- output --------------------------------------------------------------

    def set_tooltip(self, text: str) -> None:
        win32gui.Shell_NotifyIcon(
            win32gui.NIM_MODIFY,
            (self.hwnd, 0, win32gui.NIF_TIP, 0, 0, text[:127]),
        )

    def notify(self, title: str, message: str) -> None:
        """Show a balloon / toast from the tray icon."""
        win32gui.Shell_NotifyIcon(
            win32gui.NIM_MODIFY,
            (
                self.hwnd,
                0,
                win32gui.NIF_INFO,
                0,
                self._hicon,
                self.tooltip,
                message[:255],
                200,
                title[:63],
                win32gui.NIIF_INFO,
            ),
        )

    # -- message handlers ----------------------------------------------------

    def _on_timer(self, hwnd, msg, wparam, lparam):
        if wparam == HEARTBEAT_ID and self._heartbeat is not None:
            self._heartbeat()
        return 0

    def _on_hotkey_message(self, hwnd, msg, wparam, lparam):
        if wparam == HOTKEY_ID:
            self.on_hotkey()
        return 0

    def _on_tray_message(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_LBUTTONUP:
            self.on_hotkey()
        elif lparam == NIN_BALLOONUSERCLICK and self.on_notification_click:
            self.on_notification_click()
        elif lparam in (win32con.WM_RBUTTONUP, win32con.WM_CONTEXTMENU):
            self._show_menu()
        return 0

    def _show_menu(self) -> None:
        menu = win32gui.CreatePopupMenu()
        label = f"Scan now ({self.hotkey_label})" if self.hotkey_label else "Scan now"
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_SCAN, label)
        if self.autostart_enabled and self.on_autostart_toggle:
            checked = win32con.MF_CHECKED if self.autostart_enabled() else 0
            win32gui.AppendMenu(
                menu, win32con.MF_STRING | checked, IDM_AUTOSTART, "Start at login"
            )
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_EXIT, "Exit UniQR")

        pos = win32gui.GetCursorPos()
        # Required, or the menu refuses to close when you click elsewhere.
        win32gui.SetForegroundWindow(self.hwnd)
        win32gui.TrackPopupMenu(
            menu, win32con.TPM_LEFTALIGN | win32con.TPM_BOTTOMALIGN,
            pos[0], pos[1], 0, self.hwnd, None,
        )
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        win32gui.DestroyMenu(menu)

    def _on_command(self, hwnd, msg, wparam, lparam):
        item = win32api.LOWORD(wparam)
        if item == IDM_SCAN:
            self.on_hotkey()
        elif item == IDM_AUTOSTART and self.on_autostart_toggle:
            self.on_autostart_toggle()
        elif item == IDM_EXIT:
            self.stop()
        return 0

    def _on_destroy(self, hwnd, msg, wparam, lparam):
        ctypes.windll.user32.KillTimer(self.hwnd, HEARTBEAT_ID)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.hwnd, 0))
        # Deliberately no PostQuitMessage. A card that is open runs its own
        # message loop, and if that loop receives the quit message it can stop
        # processing timers altogether, so the card never closes and the
        # program hangs. run() watches this flag instead.
        self._quit = True
        return 0

    # -- lifecycle -----------------------------------------------------------

    def run(self) -> None:
        """Block here, handing messages to the handlers above until told to quit.

        Not PumpMessages(), which waits for the quit message to arrive here. A
        card that is open when Exit is chosen runs its own message loop, and
        that loop takes the quit message for itself. Choosing Exit in the first
        seconds after start, while the greeting card was up, left a process with
        no window, no hotkey and no tray icon, and nothing to close it with.
        The shell now remembers it was told to stop and checks that, waking at
        once for any message and at least four times a second regardless.
        """
        while not self._quit:
            win32event.MsgWaitForMultipleObjects([], False, 250, win32con.QS_ALLINPUT)
            win32gui.PumpWaitingMessages()

    def stop(self) -> None:
        try:
            win32gui.UnregisterHotKey(self.hwnd, HOTKEY_ID)
        except win32gui.error:
            pass
        win32gui.DestroyWindow(self.hwnd)
