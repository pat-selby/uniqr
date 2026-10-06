"""Start UniQR at login on macOS, with this Mac's own paths filled in.

    python3 tools/install_mac_agent.py                      # install and start
    python3 tools/install_mac_agent.py --hotkey '<cmd>+<shift>+8'
    python3 tools/install_mac_agent.py --uninstall
    python3 tools/install_mac_agent.py --print              # show the file, change nothing

macOS starts programs at login from a small settings file called a launch
agent. That file has to hold full paths: the program to run, the folder to run
it in, and where to write the log. launchd does not expand "~" or "$HOME", so
a file copied from someone else's Mac points at their username, and launchd
fails with status 78 and no useful message. This writes a file with the paths
of the copy you are running it from instead.

It also creates the log folder. launchd refuses to start a job whose log folder
does not exist, which looks exactly like the username problem.

Uses only the standard library, so any python3 will do, including the one that
ships with macOS.
"""

from __future__ import annotations

import argparse
import plistlib
import subprocess
import sys
from pathlib import Path

LABEL = "com.patselby.uniqr"


def build_plist(repo: Path, home: Path, hotkey: str | None = None) -> dict:
    """The launch agent for the UniQR copy in `repo`, run by the user at `home`.

    Starts from tools/com.patselby.uniqr.plist so the settings that matter
    (restart if it stops, but not in a tight loop) live in one reviewable file,
    and replaces every path in it.
    """
    with (repo / "tools" / f"{LABEL}.plist").open("rb") as handle:
        data = plistlib.load(handle)

    log = home / "Library" / "Logs" / "UniQR" / "launchd.log"
    data["ProgramArguments"] = [str(repo / ".venv" / "bin" / "python"), str(repo / "app.py")]
    data["WorkingDirectory"] = str(repo)
    data["StandardOutPath"] = str(log)
    data["StandardErrorPath"] = str(log)

    # The default hotkey is Control+Option+Q. A virtual machine often swallows
    # Ctrl+Alt, which is the only reason to override it.
    if hotkey:
        data["EnvironmentVariables"] = {"UNIQR_HOTKEY": hotkey}
    else:
        data.pop("EnvironmentVariables", None)
    return data


def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--hotkey", help="pynput syntax, for example '<cmd>+<shift>+8'")
    parser.add_argument("--uninstall", action="store_true", help="stop it and remove the file")
    parser.add_argument("--print", dest="show", action="store_true", help="print the file, change nothing")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent
    home = Path.home()
    dest = home / "Library" / "LaunchAgents" / f"{LABEL}.plist"

    if args.show:
        sys.stdout.write(plistlib.dumps(build_plist(repo, home, args.hotkey)).decode())
        return 0

    if sys.platform != "darwin":
        print("This sets up a macOS launch agent, so it only runs on a Mac.", file=sys.stderr)
        return 1

    if args.uninstall:
        _launchctl("unload", str(dest))
        dest.unlink(missing_ok=True)
        print(f"Stopped UniQR and removed {dest}")
        print("Remove Terminal and the Python entries from Screen Recording and Accessibility if you added them only for this.")
        return 0

    python = repo / ".venv" / "bin" / "python"
    if not python.exists():
        print(f"No virtual environment at {python}.", file=sys.stderr)
        print("Create it first, from the UniQR folder:", file=sys.stderr)
        print("  python3 -m venv .venv && source .venv/bin/activate && pip install -e .", file=sys.stderr)
        return 1

    # Without this folder launchd cannot open the log and the job never starts.
    (home / "Library" / "Logs" / "UniQR").mkdir(parents=True, exist_ok=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as handle:
        plistlib.dump(build_plist(repo, home, args.hotkey), handle)

    check = subprocess.run(["plutil", "-lint", str(dest)], capture_output=True, text=True)
    if check.returncode != 0:
        print(f"macOS rejected the file it just wrote: {check.stdout or check.stderr}", file=sys.stderr)
        return 1

    _launchctl("unload", str(dest))  # fine if it was not loaded yet
    loaded = _launchctl("load", str(dest))
    if loaded.returncode != 0:
        print(f"launchctl could not load it: {loaded.stderr or loaded.stdout}", file=sys.stderr)
        return 1

    print(f"Installed. UniQR will start at login, and has been started now.\n  {dest}")
    print()
    print("One more step, and macOS makes you do it by hand.")
    print("Open System Settings > Privacy & Security, and under both Screen Recording")
    print("and Accessibility, add this program and switch it on:")
    print(f"  {python}")
    print("A Finder window is about to open with it selected. Drag it into each list.")
    print("(The folder is hidden. Cmd+Shift+. shows hidden files in a file picker.)")
    print()
    print("Then restart UniQR so it sees the new permission:")
    print(f"  launchctl unload {dest} && launchctl load {dest}")
    print()
    print("If it does not start, the reason is in:")
    print(f"  {home / 'Library' / 'Logs' / 'UniQR' / 'uniqr.log'}")
    subprocess.run(["open", "-R", str(python)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
