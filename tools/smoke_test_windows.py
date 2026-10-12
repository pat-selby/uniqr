"""Start the packaged Windows exe and check it comes up and exits cleanly.

    python tools/smoke_test_windows.py dist/UniQR.exe

Used by the Windows build workflow, so a build that starts and dies is caught
before anyone signs or downloads it. It checks what can be checked on a build
machine with nobody at the keyboard:

  login       it asks the exe to add itself to Windows' list of programs to start
              at login, reads the command back out of the registry, and starts
              the exe with exactly that command, as a login would. A quoting
              mistake in the stored command would show up here. It removes the
              entry afterward, whatever happens.
  it starts   the log says "UniQR is running", so every module the program
              needs was packed in and the hotkey was claimed
  it exits    Exit from the tray menu stops both of the exe's processes. A
              one-file build is two processes, and a leftover one keeps the
              unpacked folder alive.

It does not press the hotkey or read a QR code. That was checked by hand on a
real machine, and a build server has no screen anyone is looking at.

Do not run it on a computer where you rely on UniQR starting at login: it adds
and then removes the entry named UniQR.
"""

import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

LOG = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "UniQR" / "uniqr.log"
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
WM_COMMAND = 0x0111
IDM_EXIT = 1002  # what the tray menu's Exit sends
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def log_lines() -> list[str]:
    return LOG.read_text(encoding="utf-8", errors="replace").splitlines() if LOG.exists() else []


def running(image: str) -> bool:
    out = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {image}", "/NH"], capture_output=True, text=True
    ).stdout
    return image.lower() in out.lower()


def run_entry() -> str | None:
    """What Windows has stored under UniQR in its list of programs to start at login."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return str(winreg.QueryValueEx(key, "UniQR")[0])
    except FileNotFoundError:
        return None


def start_and_exit(exe: Path, command_line: str) -> int:
    before = len(log_lines())
    started = time.time()
    # A string, not a list: this is the stored command line, and Windows has to
    # read it back the way it will at login.
    subprocess.Popen(
        command_line, creationflags=DETACHED, close_fds=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    while time.time() - started < 90:
        new = log_lines()[before:]
        if any("UniQR is running" in line for line in new):
            break
        if any("already running" in line for line in new):
            print("Another UniQR is already running, so this copy stepped aside. Quit it from")
            print("the tray icon (or end it in Task Manager) and run this test again.")
            return 2
        time.sleep(0.5)
    else:
        print("FAIL: the exe never said it was running. Its log:")
        print("\n".join(log_lines()[before:]) or "(nothing was written)")
        subprocess.run(["taskkill", "/F", "/IM", exe.name], capture_output=True)
        return 1
    print(f"ok: started in {time.time() - started:.1f} s")
    print("    " + [ln for ln in log_lines()[before:] if "UniQR is running" in ln][-1])

    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW("UniQRHiddenWindow", "UniQR")
    if not hwnd:
        print("FAIL: started, but its hidden window is missing, so Exit cannot be sent")
        subprocess.run(["taskkill", "/F", "/IM", exe.name], capture_output=True)
        return 1
    after_exit = len(log_lines())
    user32.PostMessageW(hwnd, WM_COMMAND, IDM_EXIT, 0)

    end = time.time() + 20
    while time.time() < end and running(exe.name):
        time.sleep(0.5)
    if running(exe.name):
        print("FAIL: Exit was sent and the exe is still running. Its log since then:")
        print(chr(10).join(log_lines()[after_exit:]) or "(nothing was written)")
        subprocess.run(["taskkill", "/F", "/IM", exe.name], capture_output=True)
        return 1
    print("ok: Exit stopped it, and nothing was left running")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    exe = Path(sys.argv[1]).resolve()
    if not exe.exists():
        print(f"no exe at {exe}")
        return 2

    # --quiet: no message box, which would wait for a click nobody will make.
    installed = subprocess.run([str(exe), "--install-autostart", "--quiet"], timeout=120)
    stored = run_entry()
    if installed.returncode != 0 or not stored:
        print("FAIL: --install-autostart did not add the entry to the registry")
        return 1
    if str(exe).lower() not in stored.lower():
        print(f"FAIL: the stored command does not point at the exe: {stored}")
        subprocess.run([str(exe), "--uninstall-autostart", "--quiet"], timeout=120)
        return 1
    print(f"ok: --install-autostart stored: {stored}")

    try:
        result = start_and_exit(exe, stored)
    finally:
        subprocess.run([str(exe), "--uninstall-autostart", "--quiet"], timeout=120)
    if run_entry() is not None:
        print("FAIL: --uninstall-autostart did not remove the entry")
        return 1
    print("ok: --uninstall-autostart removed it")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
