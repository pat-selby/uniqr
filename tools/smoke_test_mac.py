"""Check a built UniQR.app and its .dmg on a Mac, the way a person would meet them.

    python tools/smoke_test_mac.py dist/UniQR.app dist/UniQR-macOS-arm64.dmg

1. The disk image opens and holds UniQR.app and a shortcut to Applications.
2. The app runs its update check, which proves it starts and finds its parts.
3. The app starts for real. GitHub's Macs grant no permissions, so it may stop
   at the Screen Recording card instead of running, and either is a pass. A
   crash, or a log that never says it started, is a failure.

It can't test what needs a person: the permission switches, the hotkey, or
the picker on a real screen.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

LOG = Path.home() / "Library" / "Logs" / "UniQR" / "uniqr.log"


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def check_dmg(dmg: Path) -> str | None:
    mount = Path(tempfile.mkdtemp(prefix="uniqr-dmg-"))
    subprocess.run(
        ["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", str(mount), str(dmg)],
        check=True, capture_output=True,
    )
    try:
        names = sorted(p.name for p in mount.iterdir())
        if "UniQR.app" not in names:
            return f"the disk image holds {names}, not UniQR.app"
        link = mount / "Applications"
        if not (link.is_symlink() and os.readlink(link) == "/Applications"):
            return "the disk image has no shortcut to Applications"
    finally:
        subprocess.run(["hdiutil", "detach", str(mount)], check=False, capture_output=True)
    print("ok: the disk image holds UniQR.app and a shortcut to Applications")
    return None


def main() -> int:
    app, dmg = Path(sys.argv[1]), Path(sys.argv[2])
    program = app / "Contents" / "MacOS" / "UniQR"
    if not program.exists():
        return fail(f"{program} is missing")

    problem = check_dmg(dmg)
    if problem:
        return fail(problem)

    out = subprocess.run([str(program), "--check-updates"], capture_output=True, text=True, timeout=180)
    said = (out.stdout + out.stderr).strip()
    if "Traceback" in said or not any(
        s in said for s in ("up to date", "is available", "Could not check")
    ):
        return fail(f"--check-updates did not answer properly:\n{said}")
    print(f"ok: --check-updates answered: {said.splitlines()[-1]}")

    start = LOG.stat().st_size if LOG.exists() else 0
    config = tempfile.mkdtemp(prefix="uniqr-config-")
    env = {**os.environ, "UNIQR_CONFIG_DIR": config}
    t0 = time.time()
    proc = subprocess.Popen([str(program), "--quiet"], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    outcome = None
    log = ""
    while time.time() - t0 < 90:
        time.sleep(1)
        log = LOG.read_text(errors="replace")[start:] if LOG.exists() else ""
        if "UniQR is running" in log:
            outcome = "running"
            break
        if "Cannot read the screen" in log:
            outcome = "stopped at the Screen Recording help, as expected without permission"
            break
        if proc.poll() is not None:
            break
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    if "Traceback" in log or "stopped because of an error" in log:
        return fail(f"the app crashed:\n{log}")
    if outcome is None:
        return fail(f"the app never said it started (exit {proc.returncode}):\n{log}")
    print(f"ok: started in {time.time() - t0:.1f} s and {outcome}")
    print("\n".join("  " + line for line in log.strip().splitlines()[-8:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
