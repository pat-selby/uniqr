"""The picker overlay and the result card.

Rather than fight the window manager for a truly transparent click-through
window, the picker shows the screenshot we already captured, darkened, with
each detected code restored to full brightness. It looks like a spotlight and
behaves like a plain image, which sidesteps per-pixel alpha on every platform.

Both windows are Toplevels over one shared hidden root. macOS requires Tk to
own the main thread, so the portable shell keeps a root alive for the life of
the process; creating a second tk.Tk() alongside it would break Tk outright.
"""

import sys
import tkinter as tk
from tkinter import font as tkfont

import cv2
import numpy as np
from PIL import Image, ImageTk

from uniqr import actions
from uniqr.decode import Detection, payload_kind

QUNS_ACCEPTS_NOTIFICATIONS = 5

# How long a result card stays up, and the shorter grace period once the
# pointer has been over it - by then it has already been read.
TOAST_MS = 2200
TOAST_AFTER_HOVER_MS = 700

DIM = 0.38
ACCENT = "#4ea1ff"
BADGE_TEXT = "#0b1220"
CARD_BG = "#111826"
CARD_FG = "#e8eefc"
CARD_MUTED = "#8fa3c8"
HIGHLIGHT_PAD = 10

_root: tk.Tk | None = None


def shared_root() -> tk.Tk:
    """The one hidden Tk root every UniQR window hangs off."""
    global _root
    if _root is None or not _root.winfo_exists():
        _root = tk.Tk()
        _root.withdraw()
    return _root


def _ui_font(size: int, bold: bool = False) -> tkfont.Font:
    family = {"win32": "Segoe UI", "darwin": "SF Pro Text"}.get(sys.platform, "DejaVu Sans")
    return tkfont.Font(family=family, size=size, weight="bold" if bold else "normal")


def _button(parent, label, command, primary: bool) -> None:
    tk.Button(
        parent,
        text=label,
        command=command,
        bg=ACCENT if primary else "#243049",
        fg=BADGE_TEXT if primary else CARD_FG,
        activebackground=ACCENT if primary else "#2e3c5c",
        highlightbackground=CARD_BG,
        relief="flat",
        bd=0,
        padx=16,
        pady=5,
        cursor="hand2",
        font=_ui_font(9, bold=True),
    ).pack(side="left", padx=(0, 8))


class Picker:
    """Shows detections over a screenshot and returns the user's choice.

    result is (action, detection) where action is "open" or "copy", or None
    if the user dismissed the overlay.
    """

    def __init__(
        self, screenshot: np.ndarray, detections: list[Detection], origin=(0, 0)
    ) -> None:
        self.detections = detections
        self.origin = origin
        self.result: tuple[str, Detection] | None = None
        self._active: int | None = None
        self._card: int | None = None
        self._card_frame: tk.Frame | None = None

        self.root = shared_root()
        self.win = tk.Toplevel(self.root)
        self.win.withdraw()
        self._build(self._compose(screenshot))

    # -- image ---------------------------------------------------------------

    def _compose(self, shot: np.ndarray) -> np.ndarray:
        """Darken everything, then restore the area around each code."""
        dimmed = (shot.astype(np.float32) * DIM).astype(np.uint8)
        h, w = shot.shape[:2]
        for det in self.detections:
            left, top, bw, bh = det.bbox
            x0, y0 = max(0, left - HIGHLIGHT_PAD), max(0, top - HIGHLIGHT_PAD)
            x1 = min(w, left + bw + HIGHLIGHT_PAD)
            y1 = min(h, top + bh + HIGHLIGHT_PAD)
            if x1 > x0 and y1 > y0:
                dimmed[y0:y1, x0:x1] = shot[y0:y1, x0:x1]
        return dimmed

    # -- window --------------------------------------------------------------

    def _build(self, composed: np.ndarray) -> None:
        h, w = composed.shape[:2]
        ox, oy = self.origin

        self.win.overrideredirect(True)
        self.win.geometry(f"{w}x{h}+{ox}+{oy}")
        self.win.attributes("-topmost", True)
        self.win.configure(bg="black")

        self.canvas = tk.Canvas(
            self.win, width=w, height=h, highlightthickness=0, bd=0, bg="black"
        )
        self.canvas.pack()

        rgb = cv2.cvtColor(composed, cv2.COLOR_BGR2RGB)
        self._photo = ImageTk.PhotoImage(Image.fromarray(rgb), master=self.win)
        self.canvas.create_image(0, 0, image=self._photo, anchor="nw")

        self._draw_markers()
        self._draw_hint(w)

        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Button-1>", self._on_click)
        self.win.bind("<Escape>", lambda _e: self._dismiss())
        for n in range(1, min(len(self.detections), 9) + 1):
            self.win.bind(str(n), lambda _e, i=n - 1: self._choose_index(i))

        self.win.deiconify()
        self.win.focus_force()
        self.canvas.focus_set()

    def _draw_markers(self) -> None:
        for i, det in enumerate(self.detections):
            pts = [coord for point in det.quad for coord in point]
            self.canvas.create_polygon(pts, outline=ACCENT, fill="", width=3)
            left, top, _, _ = det.bbox
            bx, by, r = left - 6, top - 6, 15
            self.canvas.create_oval(
                bx - r, by - r, bx + r, by + r, fill=ACCENT, outline=""
            )
            self.canvas.create_text(
                bx, by, text=str(i + 1), fill=BADGE_TEXT, font=_ui_font(12, bold=True)
            )

    def _draw_hint(self, w: int) -> None:
        count = len(self.detections)
        plural = "code" if count == 1 else "codes"
        self.canvas.create_text(
            w // 2,
            28,
            text=(
                f"{count} QR {plural} found  -  hover to inspect, "
                f"press 1-{min(count, 9)} to copy, Esc to cancel"
            ),
            fill=CARD_FG,
            font=_ui_font(12),
        )

    # -- hover card ----------------------------------------------------------

    def _hit(self, x: int, y: int) -> int | None:
        for i, det in enumerate(self.detections):
            left, top, w, h = det.bbox
            if left - HIGHLIGHT_PAD <= x <= left + w + HIGHLIGHT_PAD and (
                top - HIGHLIGHT_PAD <= y <= top + h + HIGHLIGHT_PAD
            ):
                return i
        return None

    def _on_motion(self, event) -> None:
        hit = self._hit(event.x, event.y)
        if hit != self._active:
            self._active = hit
            self._show_card(hit)

    def _clear_card(self) -> None:
        if self._card is not None:
            self.canvas.delete(self._card)
            self._card = None
        if self._card_frame is not None:
            self._card_frame.destroy()
            self._card_frame = None

    def _show_card(self, index: int | None) -> None:
        self._clear_card()
        if index is None:
            return
        det = self.detections[index]

        frame = tk.Frame(self.canvas, bg=CARD_BG, padx=14, pady=12)
        tk.Label(
            frame,
            text=payload_kind(det.text).upper(),
            bg=CARD_BG,
            fg=CARD_MUTED,
            font=_ui_font(8, bold=True),
        ).pack(anchor="w")
        tk.Label(
            frame,
            text=actions.summarize(det.text, 68),
            bg=CARD_BG,
            fg=CARD_FG,
            font=_ui_font(10),
            justify="left",
            wraplength=380,
        ).pack(anchor="w", pady=(2, 10))

        row = tk.Frame(frame, bg=CARD_BG)
        row.pack(anchor="w")
        if actions.can_open(det.text):
            _button(row, "Open", lambda: self._finish("open", det), True)
        else:
            tk.Label(
                row,
                text="not a web link - copy only",
                bg=CARD_BG,
                fg=CARD_MUTED,
                font=_ui_font(8),
            ).pack(side="left", padx=(0, 8))
        _button(row, "Copy", lambda: self._finish("copy", det), False)

        left, top, w, h = det.bbox
        x, y = left, top + h + 16
        cw, ch = 420, 130
        x = min(x, self.canvas.winfo_width() - cw)
        if y + ch > self.canvas.winfo_height():
            y = max(0, top - ch)
        self._card_frame = frame
        self._card = self.canvas.create_window(max(0, x), y, window=frame, anchor="nw")

    # -- choices -------------------------------------------------------------

    def _on_click(self, event) -> None:
        hit = self._hit(event.x, event.y)
        if hit is None:
            self._dismiss()
        else:
            self._finish("copy", self.detections[hit])

    def _choose_index(self, index: int) -> None:
        if 0 <= index < len(self.detections):
            self._finish("copy", self.detections[index])

    def _finish(self, action: str, det: Detection) -> None:
        self.result = (action, det)
        self._close()

    def _dismiss(self) -> None:
        self.result = None
        self._close()

    def _close(self) -> None:
        self._clear_card()
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    def show(self) -> tuple[str, Detection] | None:
        # wait_window runs a nested event loop, so this works whether or not a
        # mainloop is already running on this thread.
        self.root.wait_window(self.win)
        return self.result


def pick(
    screenshot: np.ndarray, detections: list[Detection], origin=(0, 0)
) -> tuple[str, Detection] | None:
    return Picker(screenshot, detections, origin).show()


def notifications_visible() -> bool:
    """Whether the OS would actually show a system notification right now.

    Windows exposes this directly. Elsewhere there is no reliable query, and
    it does not matter: UniQR draws its own card either way.
    """
    if sys.platform != "win32":
        return True
    import ctypes

    state = ctypes.c_int()
    hr = ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
    if hr != 0:
        return True
    return state.value == QUNS_ACCEPTS_NOTIFICATIONS


class Toast:
    """A small always-on-top card shown next to a code.

    This is our own window, not a system notification, so it appears even
    under Do Not Disturb / Focus modes - and it lands at the code rather than
    in a corner of the screen.
    """

    def __init__(
        self,
        text: str,
        heading: str,
        at: tuple[int, int],
        timeout_ms: int = TOAST_MS,
        offer_open: bool = True,
    ) -> None:
        self.text = text
        self.opened = False
        self._timer: str | None = None
        self._timeout = timeout_ms
        self._left_once = False

        self.root = shared_root()
        self.win = tk.Toplevel(self.root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=ACCENT)

        frame = tk.Frame(self.win, bg=CARD_BG, padx=16, pady=13)
        frame.pack(padx=2, pady=2)

        tk.Label(
            frame,
            text=heading.upper(),
            bg=CARD_BG,
            fg=CARD_MUTED,
            font=_ui_font(8, bold=True),
        ).pack(anchor="w")
        if text:
            tk.Label(
                frame,
                text=actions.summarize(text, 70),
                bg=CARD_BG,
                fg=CARD_FG,
                font=_ui_font(10),
                justify="left",
                wraplength=400,
            ).pack(anchor="w", pady=(2, 10))

        row = tk.Frame(frame, bg=CARD_BG)
        row.pack(anchor="w")
        if text and offer_open and actions.can_open(text):
            _button(row, "Open", self._open, True)
        _button(row, "Dismiss", self._close, False)

        self.win.update_idletasks()
        self._place(at)
        self.win.deiconify()

        self.win.bind("<Escape>", lambda _e: self._close())
        frame.bind("<Enter>", lambda _e: self._cancel_timer())
        frame.bind("<Leave>", lambda _e: self._leave())
        self._start_timer()

    def _leave(self) -> None:
        # Someone who hovered has already read it - running the full timer
        # again just leaves the card sitting there.
        self._left_once = True
        self._start_timer()

    def _place(self, at: tuple[int, int]) -> None:
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        x = max(8, min(at[0], sw - w - 8))
        y = at[1]
        if y + h > sh - 8:
            y = max(8, at[1] - h - 24)
        self.win.geometry(f"+{int(x)}+{int(y)}")

    def _start_timer(self) -> None:
        self._cancel_timer()
        delay = TOAST_AFTER_HOVER_MS if self._left_once else self._timeout
        self._timer = self.win.after(delay, self._close)

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            try:
                self.win.after_cancel(self._timer)
            except tk.TclError:
                pass
            self._timer = None

    def _open(self) -> None:
        self.opened = actions.open_url(self.text)
        self._close()

    def _close(self) -> None:
        self._cancel_timer()
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    def show(self) -> bool:
        self.root.wait_window(self.win)
        return self.opened


def toast(
    text: str, heading: str, at: tuple[int, int], timeout_ms: int = TOAST_MS
) -> bool:
    """Show a card near `at`. Returns True if the user opened the link."""
    return Toast(text, heading, at, timeout_ms).show()
