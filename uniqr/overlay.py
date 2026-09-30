"""The picker overlay and the result card.

Rather than fight the window manager for a truly transparent click-through
window, the picker shows the screenshot we already captured, darkened, with
each detected code restored to full brightness. It looks like a spotlight and
behaves like a plain image, which sidesteps per-pixel alpha on every platform.

Both windows are Toplevels over one shared hidden root. macOS requires Tk to
own the main thread, so the portable shell keeps a root alive for the life of
the process; creating a second tk.Tk() alongside it would break Tk outright.

Everything here has one foot in each of UniQR's two coordinate spaces. The
screenshot and the detections in it are in image pixels; every Tk number -
window geometry, canvas size, canvas item coordinates, mouse events - is in
screen points. `scale_factor()` converts, and on a Retina Mac it is 2.0, so
skipping the conversion draws every highlight at twice the offset of the code
it belongs to. `to_points` and `below` are the only two places that divide.
"""

import sys
import tkinter as tk
from collections.abc import Callable
from tkinter import font as tkfont

import cv2
import numpy as np
from PIL import Image, ImageTk

from uniqr import actions, backends, capture
from uniqr.backends.base import Rect
from uniqr.decode import Detection, payload_kind

QUNS_ACCEPTS_NOTIFICATIONS = 5

# How long a result card stays up, and the shorter grace period once the
# pointer has been over it - by then it has already been read.
TOAST_MS = 2200
TOAST_AFTER_HOVER_MS = 700

DIM = 0.38
ACCENT = "#4ea1ff"
ACCENT_HOVER = "#7ab8ff"
BADGE_TEXT = "#0b1220"
CARD_BG = "#111826"
CARD_FG = "#e8eefc"
CARD_MUTED = "#8fa3c8"
CARD_BORDER = "#2a3752"
CARD_RAISED = "#1c2740"
BUTTON_BG = "#1f2a40"
BUTTON_HOVER = "#2c3a58"
OK_FG = "#3fb27f"
WARN_FG = "#e0a33e"
TIP_BG = "#0b1220"
HIGHLIGHT_PAD = 10

# Hover pop-up for the full link: a short pause so it doesn't flicker as the
# pointer passes over, and a width after which long links wrap.
TIP_DELAY_MS = 400
TIP_WRAP_PX = 460

# Card fade-in: FADE_STEPS frames, FADE_MS apart.
FADE_STEPS = 6
FADE_MS = 18

# Friendly names for payload kinds, shown as a small label on the card.
KIND_LABELS = {
    "url": "Link", "wifi": "Wi-Fi", "email": "Email", "phone": "Phone",
    "geo": "Location", "contact": "Contact", "event": "Event",
    "secret": "Secret", "uri": "App link", "text": "Text",
}

_root: tk.Tk | None = None


def shared_root() -> tk.Tk:
    """The one hidden Tk root every UniQR window hangs off."""
    global _root
    if _root is None or not _root.winfo_exists():
        _root = tk.Tk()
        _root.withdraw()
    return _root


def to_points(x: float, y: float, scale: float) -> tuple[int, int]:
    """Image pixels to screen points."""
    return int(round(x / scale)), int(round(y / scale))


def below(
    bbox: tuple[int, int, int, int],
    origin: tuple[int, int] = (0, 0),
    gap: int = 14,
    scale: float | None = None,
) -> tuple[int, int]:
    """Where to put a card that sits just under a code, in screen points.

    `bbox` is capture-local image pixels, `origin` is the captured region's
    top-left in screen points, and `gap` is a visual margin - so the gap is
    added after the conversion, not scaled along with it.
    """
    if scale is None:
        scale = capture.scale_factor()
    left, top, _w, h = bbox
    x, y = to_points(left, top + h, scale)
    return origin[0] + x, origin[1] + y + gap


def _ui_font(size: int, bold: bool = False) -> tkfont.Font:
    family = {"win32": "Segoe UI", "darwin": "SF Pro Text"}.get(sys.platform, "DejaVu Sans")
    return tkfont.Font(family=family, size=size, weight="bold" if bold else "normal")


def _mono_font(size: int, bold: bool = False) -> tkfont.Font:
    """Fixed-width type for addresses.

    Lookalike tricks such as "rn" posing as "m", or "1" as "l", are much easier
    to spot when every character has the same width.
    """
    family = {"win32": "Consolas", "darwin": "Menlo"}.get(sys.platform, "DejaVu Sans Mono")
    return tkfont.Font(family=family, size=size, weight="bold" if bold else "normal")


def _button(parent, label, command, primary: bool) -> tk.Label:
    """A clickable card button, drawn as a Label rather than a tk.Button.

    macOS draws a real tk.Button with the native Aqua control, which ignores
    the background color it is given but still honors the foreground one. On
    a dark card that produced a pale button with pale text on it - the
    "Dismiss" control was there, and all but unreadable. A Label accepts
    every color on every platform, so the card looks the same everywhere.
    Clicks and hover come from bindings instead of the widget's own command.
    """
    bg, hover = (ACCENT, ACCENT_HOVER) if primary else (BUTTON_BG, BUTTON_HOVER)
    fg = BADGE_TEXT if primary else CARD_FG
    button = tk.Label(
        parent,
        text=label,
        bg=bg,
        fg=fg,
        highlightthickness=0,
        relief="flat",
        bd=0,
        padx=16,
        pady=6,
        cursor="hand2",
        font=_ui_font(9, bold=True),
    )
    button.bind("<Enter>", lambda _e: button.configure(bg=hover), add="+")
    button.bind("<Leave>", lambda _e: button.configure(bg=bg), add="+")
    # Fire on release, not press, so sliding off the control cancels it the
    # way a real button does.
    button.bind("<ButtonRelease-1>", lambda _e: _if_inside(button, command), add="+")
    button.pack(side="left", padx=(0, 8))
    return button


def _if_inside(widget: tk.Widget, command: Callable[[], None]) -> None:
    """Run `command` only if the pointer is still over `widget`."""
    try:
        px, py = widget.winfo_pointerxy()
        x, y = widget.winfo_rootx(), widget.winfo_rooty()
        w, h = widget.winfo_width(), widget.winfo_height()
    except tk.TclError:
        return
    if x <= px < x + w and y <= py < y + h:
        command()


def _round(win: tk.Toplevel) -> None:
    """Rounded corners where the OS supports them. Purely cosmetic."""
    try:
        backends.round_corners(int(win.wm_frame(), 16))
    except (tk.TclError, ValueError):
        pass


class HoverTip:
    """The full text in a small pop-up while the pointer rests on a widget.

    It waits TIP_DELAY_MS before appearing, so it doesn't flicker as the
    pointer passes by, wraps long links instead of drawing one endless line,
    and stays on the monitor the widget is on.
    """

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.win: tk.Toplevel | None = None
        self._pending: str | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<Destroy>", self.hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._pending = self.widget.after(TIP_DELAY_MS, self._show)

    def _cancel(self) -> None:
        if self._pending is not None:
            try:
                self.widget.after_cancel(self._pending)
            except tk.TclError:
                pass
            self._pending = None

    def _show(self) -> None:
        self._pending = None
        if self.win is not None or not self.widget.winfo_exists():
            return
        win = tk.Toplevel(self.widget)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=CARD_BORDER)
        tk.Label(
            win,
            text=self.text,
            bg=TIP_BG,
            fg=CARD_FG,
            font=_mono_font(9),
            justify="left",
            wraplength=TIP_WRAP_PX,
            padx=10,
            pady=8,
        ).pack(padx=1, pady=1)
        win.update_idletasks()

        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        size = (win.winfo_reqwidth(), win.winfo_reqheight())
        px, py = place_within((x, y), size, capture.monitor_at(x, y))
        win.geometry(f"+{px}+{py}")
        win.deiconify()
        # The card is also always-on-top, and every step of its fade-in brings
        # it back to the front. So the pop-up must only ever appear after the
        # fade has finished, which TIP_DELAY_MS guarantees (a test pins it).
        win.lift()
        _round(win)
        self.win = win

    def hide(self, _event=None) -> None:
        self._cancel()
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None


def _build_card(
    parent: tk.Misc,
    text: str,
    status: str,
    buttons: list[tuple[str, Callable[[], None], bool]],
) -> tk.Frame:
    """The card used by both the result pop-up and the picker.

    Laid out so the part that decides safety reads first. For a link that is
    the real host, in large fixed-width type, with the rest of the address
    dimmed beneath it and any warning in amber. The full link is one hover
    away but never one click away: only the Open button opens anything, so a
    stray click on a card that appeared under the pointer does nothing.
    """
    outer = tk.Frame(parent, bg=CARD_BORDER)
    card = tk.Frame(outer, bg=CARD_BG, padx=18, pady=15)
    card.pack(padx=1, pady=1)

    if not text:
        tk.Label(card, text=status, bg=CARD_BG, fg=CARD_FG, font=_ui_font(10, bold=True)).pack(anchor="w")
    else:
        head = tk.Frame(card, bg=CARD_BG)
        head.pack(fill="x", pady=(0, 8))
        kind = payload_kind(text)
        tk.Label(
            head,
            text=KIND_LABELS.get(kind, "Text").upper(),
            bg=CARD_RAISED,
            fg=CARD_MUTED,
            font=_ui_font(7, bold=True),
            padx=8,
            pady=2,
        ).pack(side="left")
        if status:
            tk.Label(
                head, text="✓ " + status, bg=CARD_BG, fg=OK_FG, font=_ui_font(9, bold=True)
            ).pack(side="right", padx=(24, 0))

        link = actions.describe_link(text)
        if link is not None:
            host = tk.Label(
                card, text=link.host, bg=CARD_BG, fg=CARD_FG,
                font=_mono_font(12, bold=True), justify="left", wraplength=380,
            )
            host.pack(anchor="w")
            HoverTip(host, link.full)
            if link.rest not in ("", "/"):
                rest = tk.Label(
                    card, text=actions.summarize(link.rest, 54), bg=CARD_BG,
                    fg=CARD_MUTED, font=_mono_font(9), cursor="question_arrow",
                )
                rest.pack(anchor="w", pady=(2, 0))
                HoverTip(rest, link.full)
            notes = [(warning, True) for warning in link.warnings]
        else:
            flat = " ".join(text.split())
            body = tk.Label(
                card, text=actions.summarize(text, 90), bg=CARD_BG, fg=CARD_FG,
                font=_ui_font(10), justify="left", wraplength=380,
            )
            body.pack(anchor="w")
            if len(flat) > 90 or "\n" in text.strip():
                HoverTip(body, text.strip())
            notes = [("Not a web link, so UniQR won't open it.", False)]
            if kind == "secret":
                notes.insert(0, ("This is a login secret. Paste it only into your authenticator app.", True))

        # Warnings in amber with a sign; plain notes in muted text.
        for note, is_warning in notes:
            tk.Label(
                card,
                text=("⚠ " + note) if is_warning else note,
                bg=CARD_BG,
                fg=WARN_FG if is_warning else CARD_MUTED,
                font=_ui_font(9),
                justify="left",
                wraplength=380,
            ).pack(anchor="w", pady=(6, 0))

    if buttons:
        row = tk.Frame(card, bg=CARD_BG)
        row.pack(anchor="w", pady=(14, 0))
        for label, command, primary in buttons:
            _button(row, label, command, primary)
    return outer


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
        self.scale = capture.scale_factor()
        self.result: tuple[str, Detection] | None = None
        self._active: int | None = None
        self._card: int | None = None
        self._card_frame: tk.Frame | None = None
        self._marker_ids: list[int] = []
        # Detections converted once, in the same space as every Tk number.
        self._boxes = [self._to_points(d.bbox) for d in detections]

        self.root = shared_root()
        self.win = tk.Toplevel(self.root)
        self.win.withdraw()
        self._build(self._compose(screenshot))

    def _to_points(self, bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        left, top, w, h = bbox
        x0, y0 = to_points(left, top, self.scale)
        x1, y1 = to_points(left + w, top + h, self.scale)
        return x0, y0, x1 - x0, y1 - y0

    # -- image ---------------------------------------------------------------

    def _compose(self, shot: np.ndarray) -> np.ndarray:
        """Darken everything, then restore the area around each code.

        Pure image-pixel work, so the padding - a visual margin measured in
        points everywhere else - is scaled up to match.
        """
        dimmed = (shot.astype(np.float32) * DIM).astype(np.uint8)
        h, w = shot.shape[:2]
        pad = int(round(HIGHLIGHT_PAD * self.scale))
        for det in self.detections:
            left, top, bw, bh = det.bbox
            x0, y0 = max(0, left - pad), max(0, top - pad)
            x1 = min(w, left + bw + pad)
            y1 = min(h, top + bh + pad)
            if x1 > x0 and y1 > y0:
                dimmed[y0:y1, x0:x1] = shot[y0:y1, x0:x1]
        return dimmed

    # -- window --------------------------------------------------------------

    def _build(self, composed: np.ndarray) -> None:
        # The screenshot is image pixels; the window it goes in is points.
        px_h, px_w = composed.shape[:2]
        w, h = to_points(px_w, px_h, self.scale)
        ox, oy = self.origin

        self.win.overrideredirect(True)
        # Negative offsets are legal Tk geometry ("+-1600+0") and are how a
        # monitor to the left of the primary one is addressed.
        self.win.geometry(f"{w}x{h}+{ox}+{oy}")
        self.win.attributes("-topmost", True)
        self.win.configure(bg="black")

        self.canvas = tk.Canvas(
            self.win, width=w, height=h, highlightthickness=0, bd=0, bg="black"
        )
        self.canvas.pack()

        rgb = cv2.cvtColor(composed, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        if (image.width, image.height) != (w, h):
            # Retina: hand Tk an image the size of the window, or it draws the
            # top-left quarter of the screenshot at full size.
            image = image.resize((w, h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(image, master=self.win)
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
        self._marker_ids = []
        for i, (det, box) in enumerate(zip(self.detections, self._boxes)):
            pts = [
                coord
                for point in det.quad
                for coord in to_points(point[0], point[1], self.scale)
            ]
            self._marker_ids.append(
                self.canvas.create_polygon(pts, outline=ACCENT, fill="", width=3)
            )
            left, top, _, _ = box
            # The badge radius is a fixed visual size, so it is not scaled.
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
        """Which code is under a mouse position? Both in screen points."""
        for i, (left, top, w, h) in enumerate(self._boxes):
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

        buttons: list[tuple[str, Callable[[], None], bool]] = []
        if actions.can_open(det.text):
            buttons.append(("Open", lambda: self._finish("open", det), True))
        buttons.append(("Copy", lambda: self._finish("copy", det), False))
        frame = _build_card(self.canvas, det.text, "", buttons)

        # _boxes are already screen points, which is not the same as
        # image pixels on a Retina display.
        left, top, _w, h = self._boxes[index]
        ox, oy = self.origin
        frame.update_idletasks()
        size = (frame.winfo_reqwidth(), frame.winfo_reqheight())
        anchor = (ox + left, oy + top + h + 16)
        # The canvas spans every monitor, so its width says nothing about
        # where one monitor ends. Place in screen space, then convert back.
        sx, sy = place_within(anchor, size, capture.monitor_at(ox + left, oy + top))
        self._card_frame = frame
        self._card = self.canvas.create_window(
            sx - ox, sy - oy, window=frame, anchor="nw"
        )

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


def place_within(
    anchor: tuple[int, int],
    size: tuple[int, int],
    bounds: Rect,
    margin: int = 8,
    flip_gap: int = 24,
) -> tuple[int, int]:
    """Top-left corner for a card near `anchor`, kept inside one monitor.

    Clamping against Tk's screen size was the bug: Tk only knows the primary
    monitor, so a code on a second screen at x=2500 had its card dragged back
    to the primary's right edge. Bounds now come from the monitor the code is
    actually on. Coordinates are virtual-desktop pixels, so a monitor left of
    or above the primary, with negative bounds, works the same way.
    """
    ax, ay = anchor
    w, h = size
    x = max(min(ax, bounds.right - w - margin), bounds.left + margin)
    y = ay
    if y + h > bounds.bottom - margin:
        y = ay - h - flip_gap
    y = max(min(y, bounds.bottom - h - margin), bounds.top + margin)
    return int(x), int(y)


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
        self.win.configure(bg=CARD_BG)

        buttons: list[tuple[str, Callable[[], None], bool]] = []
        if text and offer_open and actions.can_open(text):
            buttons.append(("Open", self._open, True))
        buttons.append(("Dismiss", self._close, False))
        _build_card(self.win, text, heading, buttons).pack()

        self.win.update_idletasks()
        self._place(at)
        self._set_alpha(0.0)
        self.win.deiconify()
        _round(self.win)
        self._fade_in(1)

        self.win.bind("<Escape>", lambda _e: self._close())
        # Bound on the window itself, so these also fire for the text and
        # buttons inside it: hovering anywhere on the card pauses the timer.
        self.win.bind("<Enter>", lambda _e: self._cancel_timer())
        self.win.bind("<Leave>", self._on_leave)
        self._start_timer()

    def _on_leave(self, _event=None) -> None:
        # Tk also reports "left" when the pointer moves onto a button or a
        # line of text inside the card. Taken at face value, that restarted
        # the short timer and closed the card while someone was reading it.
        # So check where the pointer actually is before starting the countdown.
        if self._pointer_inside():
            return
        self._leave()

    def _pointer_inside(self) -> bool:
        try:
            px, py = self.win.winfo_pointerxy()
            x, y = self.win.winfo_rootx(), self.win.winfo_rooty()
            w, h = self.win.winfo_width(), self.win.winfo_height()
        except tk.TclError:
            return False
        return x <= px < x + w and y <= py < y + h

    def _set_alpha(self, value: float) -> None:
        try:
            self.win.attributes("-alpha", value)
        except tk.TclError:
            pass

    def _fade_in(self, step: int) -> None:
        """A quick fade-in, about a tenth of a second."""
        try:
            self._set_alpha(min(1.0, step / FADE_STEPS))
            if step < FADE_STEPS:
                self.win.after(FADE_MS, self._fade_in, step + 1)
        except tk.TclError:
            pass  # closed mid-fade

    def _leave(self) -> None:
        # Someone who hovered has already read it - running the full timer
        # again just leaves the card sitting there.
        self._left_once = True
        self._start_timer()

    def _place(self, at: tuple[int, int]) -> None:
        """Keep the card on screen, in screen points.

        Clamped to the whole virtual desktop rather than to Tk's idea of "the
        screen", which is the primary monitor only - on a second monitor left
        of it every position is negative, and clamping to 8 would yank the
        card across to the primary display, away from the code it describes.
        """
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        x, y = place_within(at, (w, h), capture.monitor_at(*at))
        self.win.geometry(f"+{x}+{y}")

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
