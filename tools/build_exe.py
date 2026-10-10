"""Build UniQR as one file that runs without Python installed.

    pip install -e ".[windows]" pyinstaller     # on Linux: pip install -e . pyinstaller
    python tools/build_exe.py

On Windows the result is dist/UniQR.exe. On Linux it is dist/UniQR-linux-<chip>,
a single executable with no extension (Linux has no ".exe"). It has to be built
on the system it is for: PyInstaller cannot build a Linux program on Windows.
Run this from a clean virtual environment, not your everyday Python. PyInstaller packs in what the program imports, but a
crowded environment gives its hooks more to find, and the file gets bigger.

What the choices are for:

  --onefile     one file to hand to someone. The cost is that it unpacks itself
                to a temporary folder on every start, a few seconds.
  --noconsole   no black window. UniQR lives in the tray and logs to a file.
  an icon       the tray icon is drawn in code, so the same drawing is written
                to an .ico here and baked into the file.
  version info  the Name and Details shown in the file's Properties. Without
                them Windows shows a blank, which looks like malware.

The last three are Windows features. On Linux there is no file icon, no
Properties dialog and no console window to hide, so they are left out.

Build Linux on the oldest system you want it to run on. A Linux program needs
at least the C library (glibc) version it was built against, so a build made on
a new system will not start on an older one. GitHub's ubuntu-22.04 is used for
that reason.

Not used on purpose: UPX compression. It shrinks the file and makes antivirus
programs much likelier to flag it.

The file is not code-signed, so Windows SmartScreen will say "unknown publisher"
the first time. Signing needs a certificate, which costs money each year.
"""

import hashlib
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from uniqr import __version__  # noqa: E402
from uniqr.icon import SIZES, _draw  # noqa: E402

BUILD = ROOT / "build" / "pyinstaller"
DIST = ROOT / "dist"

WINDOWS = sys.platform == "win32"
LINUX = sys.platform.startswith("linux")
# "UniQR.exe" is the name people know. On Linux the chip is part of the name,
# because a program built for one will not run on the other.
NAME = "UniQR" if WINDOWS else f"UniQR-linux-{platform.machine()}"
OUTPUT = f"{NAME}.exe" if WINDOWS else NAME

VERSION_FILE = """\
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)
  ),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('FileDescription', 'UniQR: read QR codes on your screen'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', '{name}'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 Patrick Selby. MIT License.'),
      StringStruct('OriginalFilename', '{name}.exe'),
      StringStruct('ProductName', '{name}'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def write_icon() -> Path:
    path = BUILD / "uniqr.ico"
    _draw(256).save(path, format="ICO", sizes=[(s, s) for s in SIZES])
    return path


def write_version_file() -> Path:
    major, minor, patch = (int(x) for x in __version__.split(".")[:3])
    path = BUILD / "version.txt"
    path.write_text(
        VERSION_FILE.format(
            major=major, minor=minor, patch=patch, version=__version__, name=NAME
        ),
        encoding="utf-8",
    )
    return path


def main() -> int:
    try:
        import PyInstaller.__main__ as pyinstaller
    except ImportError:
        print("PyInstaller is not installed. Run: pip install pyinstaller", file=sys.stderr)
        return 1

    if not (WINDOWS or LINUX):
        print("This builds for Windows and Linux. A Mac needs an .app, which is not set up yet.", file=sys.stderr)
        return 1

    BUILD.mkdir(parents=True, exist_ok=True)
    windows_only = (
        ["--noconsole", "--icon", str(write_icon()), "--version-file", str(write_version_file())]
        if WINDOWS
        else [
            # pynput and python-xlib choose their parts at run time, by
            # importing a module whose name is built from the platform. The
            # packager cannot see that, and left out pynput.keyboard._xorg: the
            # program started, then died with "this platform is not supported".
            # Found by running it, not by building it.
            "--collect-submodules", "pynput",
            "--collect-submodules", "Xlib",
        ]
    )
    pyinstaller.run(
        [
            str(ROOT / "app.py"),
            "--name", NAME,
            "--onefile",
            "--noconfirm",
            "--clean",
            *windows_only,
            "--distpath", str(DIST),
            "--workpath", str(BUILD),
            "--specpath", str(BUILD),
            "--paths", str(ROOT),
            # The backends are chosen at run time, so make sure none is missed.
            "--collect-submodules", "uniqr",
            # Never part of the program, and heavy if an environment has them.
            "--exclude-module", "pytest",
            "--exclude-module", "benchmarks",
        ]
    )

    exe = DIST / OUTPUT
    if not exe.exists():
        print("The build did not produce a program.", file=sys.stderr)
        return 1
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    print()
    print(f"Built {exe}")
    print(f"  size    {exe.stat().st_size / 1_000_000:.0f} MB")
    print(f"  sha256  {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
