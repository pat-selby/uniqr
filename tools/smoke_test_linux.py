"""Start the packaged Linux program and check it really reads a QR code.

    xvfb-run -a python tools/smoke_test_linux.py dist/UniQR-linux-x86_64

xvfb-run gives it a fake screen, so this works on a machine with no monitor, like
a CI runner. The test does what a person would: start UniQR, put a QR code on
screen, press the hotkey, and look for the link. It checks two things:

  the log      the scan wrote the link, so the hotkey arrived and the code read
  the clipboard the link was copied. No clipboard helper (xclip, xsel) is
               installed on the runner, which is how a new install looks, so
               this also covers UniQR copying without one.

It needs xdotool to press the key, and Tk, OpenCV and Pillow in the Python that
runs it, to draw the code and read the clipboard.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

PAYLOAD = "https://example.com/uniqr-linux-test"
HOTKEY = "ctrl+alt+q"

SHOW_QR = f"""
import cv2, tkinter as tk
from PIL import Image, ImageTk
qr = cv2.QRCodeEncoder.create().encode("{PAYLOAD}")
qr = cv2.resize(qr, (320, 320), interpolation=cv2.INTER_NEAREST)
img = cv2.copyMakeBorder(qr, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.geometry("+100+100")
photo = ImageTk.PhotoImage(Image.fromarray(img))
tk.Label(root, image=photo, bd=0).pack()
root.after(25000, root.destroy)
root.mainloop()
"""

READ_CLIPBOARD = """
import tkinter as tk
root = tk.Tk()
root.withdraw()
try:
    print(root.clipboard_get())
except tk.TclError:
    print("")
"""


def log_path() -> Path:
    state = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(state) / "uniqr" / "uniqr.log"


def read_log() -> str:
    path = log_path()
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def wait_for(text: str, seconds: float, start: int = 0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if text in read_log()[start:]:
            return True
        time.sleep(0.5)
    return False


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    program = Path(sys.argv[1]).resolve()
    if not program.exists():
        print(f"no program at {program}")
        return 2

    started = time.time()
    app = subprocess.Popen([str(program)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    qr_window = None
    try:
        if not wait_for("UniQR is running", 90):
            print("FAIL: the program never said it was running. Its log:")
            print(read_log() or "(no log at all)")
            return 1
        print(f"ok: started in {time.time() - started:.1f} s")
        print("    " + [line for line in read_log().splitlines() if "UniQR is running" in line][-1])

        qr_window = subprocess.Popen([sys.executable, "-c", SHOW_QR])
        time.sleep(4)

        before = len(read_log())
        subprocess.run(["xdotool", "key", HOTKEY], check=True)
        if not wait_for(PAYLOAD, 20, start=before):
            print(f"FAIL: pressed {HOTKEY}, and the link never reached the log. Its log:")
            print(read_log())
            return 1
        print("ok: the hotkey arrived and the code was read")

        time.sleep(1)
        copied = subprocess.run(
            [sys.executable, "-c", READ_CLIPBOARD], capture_output=True, text=True, timeout=30
        ).stdout.strip()
        if copied != PAYLOAD:
            print(f"FAIL: the clipboard held {copied!r}, not the link")
            return 1
        print("ok: the link is on the clipboard")
        return 0
    finally:
        for proc in (qr_window, app):
            if proc is not None:
                proc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
