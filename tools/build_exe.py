"""Build UniQR as one file that runs without Python installed.

    pip install -e ".[windows]" pyinstaller     # on Linux or a Mac: pip install -e . pyinstaller
    python tools/build_exe.py

On Windows the result is dist/UniQR.exe. On Linux it is dist/UniQR-linux-<chip>,
a single executable with no extension (Linux has no ".exe"). On a Mac it is
dist/UniQR.app, packed into dist/UniQR-macOS-<chip>.dmg with a shortcut to
Applications so it can be dragged in. Each has to be built on the system it is
for: PyInstaller cannot build a Linux or Mac program on Windows.
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

The Mac app is signed "ad hoc": a signature with no name behind it, which an
Apple Silicon Mac needs before it will run a program at all. It is not signed
with an Apple Developer ID or notarized (that membership costs money each
year), so the first open needs System Settings > Privacy & Security > Open
Anyway. A Mac app is a folder, so it is built as one (onedir), not one file.
"""

import hashlib
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from uniqr import __version__  # noqa: E402
from uniqr.icon import SIZES, _draw  # noqa: E402

BUILD = ROOT / "build" / "pyinstaller"
DIST = ROOT / "dist"

WINDOWS = sys.platform == "win32"
LINUX = sys.platform.startswith("linux")
MAC = sys.platform == "darwin"
CHIP = platform.machine()  # x86_64, or arm64 on Apple Silicon
# "UniQR.exe" is the name people know. On Linux the chip is part of the name,
# because a program built for one will not run on the other. On a Mac the app is
# UniQR.app, and the chip goes in the name of the .dmg it is shipped in.
NAME = "UniQR" if (WINDOWS or MAC) else f"UniQR-linux-{CHIP}"
OUTPUT = f"{NAME}.exe" if WINDOWS else f"{NAME}.app" if MAC else NAME
DMG = f"UniQR-macOS-{CHIP}.dmg"
BUNDLE_ID = "com.patselby.uniqr"

# Modules that are only ever imported by name at run time, so the packager cannot
# see them, and that a program can start fine without. Each one here was found
# missing from a published build because a person hit the failure. After a
# build, the archive is checked for them and the build fails if one is absent.
#
#   PIL._tkinter_finder   Pillow's ImageTk loads it when the picker draws the
#                         screenshot. Missing, the picker crashed whenever a
#                         screen held more than one code. The single-code path
#                         never touches it, so a start-up test passed.
#   pynput.keyboard._xorg the Linux keyboard listener, chosen at run time.
#   pynput.keyboard._darwin  the same, on a Mac.
#   jeepney.io.blocking   Wayland's screenshot portal, imported only when a
#                         scan runs on Wayland (uniqr/portal.py).
REQUIRED_MODULES = {
    "win32": ["PIL._tkinter_finder"],
    "linux": ["PIL._tkinter_finder", "pynput.keyboard._xorg", "jeepney.io.blocking"],
    "darwin": ["PIL._tkinter_finder", "pynput.keyboard._darwin"],
}

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


def write_icns() -> Path | None:
    """The Mac icon, from the same drawing. None if Pillow can't write .icns."""
    path = BUILD / "uniqr.icns"
    try:
        _draw(1024).save(path, format="ICNS")
    except Exception as exc:  # noqa: BLE001 - an app without an icon still works
        print(f"no Mac icon: {exc}")
        return None
    return path


def finish_mac_app(app: Path) -> None:
    """Name, version and signature in the app's Info.plist.

    Without a CFBundleName the menu bar says "Python". The version is what
    Finder's Get Info shows. Changing Info.plist breaks the signature, so the
    app is signed again afterwards, ad hoc.
    """
    plist_path = app / "Contents" / "Info.plist"
    with plist_path.open("rb") as f:
        info = plistlib.load(f)
    info.update(
        {
            "CFBundleName": "UniQR",
            "CFBundleDisplayName": "UniQR",
            "CFBundleShortVersionString": __version__,
            "CFBundleVersion": __version__,
            "NSHumanReadableCopyright": "Copyright (c) 2026 Patrick Selby. MIT License.",
            # numpy and OpenCV ship Mac builds for macOS 14 and newer only.
            "LSMinimumSystemVersion": "14.0",
            "NSHighResolutionCapable": True,
        }
    )
    with plist_path.open("wb") as f:
        plistlib.dump(info, f)
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)


def make_dmg(app: Path) -> Path:
    """A disk image holding the app and a shortcut to Applications."""
    out = DIST / DMG
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "UniQR"
        stage.mkdir()
        shutil.copytree(app, stage / app.name, symlinks=True)
        (stage / "Applications").symlink_to("/Applications")
        subprocess.run(
            ["hdiutil", "create", "-volname", "UniQR", "-srcfolder", str(stage),
             "-ov", "-format", "UDZO", str(out)],
            check=True,
        )
    return out


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


def missing_from(exe: Path) -> list[str]:
    """Which of the required modules did not make it into the built file."""
    from PyInstaller.archive.readers import CArchiveReader

    archive = CArchiveReader(str(exe))
    pyz = next(name for name in archive.toc if name.lower().endswith(".pyz"))
    present = set(archive.open_embedded_archive(pyz).toc)
    key = "win32" if WINDOWS else "darwin" if MAC else "linux"
    return [m for m in REQUIRED_MODULES[key] if m not in present]


def main() -> int:
    try:
        import PyInstaller.__main__ as pyinstaller
    except ImportError:
        print("PyInstaller is not installed. Run: pip install pyinstaller", file=sys.stderr)
        return 1

    if not (WINDOWS or LINUX or MAC):
        print(f"This builds for Windows, Linux and macOS, not {sys.platform}.", file=sys.stderr)
        return 1

    if LINUX and not os.environ.get("DISPLAY"):
        # The packager imports pynput to find its parts, and pynput refuses to
        # load without an X server. Without one it logs a warning, carries on,
        # and produces a program that dies at start. Failing here is kinder.
        print("There is no display, so the keyboard library cannot be inspected and the", file=sys.stderr)
        print("program would be built without it. On a machine with no screen, run:", file=sys.stderr)
        print("  xvfb-run -a python tools/build_exe.py", file=sys.stderr)
        return 1

    BUILD.mkdir(parents=True, exist_ok=True)
    if MAC:
        icns = write_icns()
        platform_args = [
            "--windowed",  # makes UniQR.app
            "--osx-bundle-identifier", BUNDLE_ID,
            *(["--icon", str(icns)] if icns else []),
            # The keyboard and tray libraries choose their Mac parts at run time.
            "--collect-submodules", "pynput",
            "--collect-submodules", "pystray",
        ]
    windows_only = (
        ["--noconsole", "--icon", str(write_icon()), "--version-file", str(write_version_file())]
        if WINDOWS
        else platform_args
        if MAC
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
            "--onedir" if MAC else "--onefile",
            "--noconfirm",
            "--clean",
            *windows_only,
            "--distpath", str(DIST),
            "--workpath", str(BUILD),
            "--specpath", str(BUILD),
            "--paths", str(ROOT),
            # The backends are chosen at run time, so make sure none is missed.
            "--collect-submodules", "uniqr",
            # Imported by name when the picker draws; see REQUIRED_MODULES.
            "--hidden-import", "PIL._tkinter_finder",
            # Never part of the program, and heavy if an environment has them.
            "--exclude-module", "pytest",
            "--exclude-module", "benchmarks",
        ]
    )

    exe = DIST / OUTPUT
    if not exe.exists():
        print("The build did not produce a program.", file=sys.stderr)
        return 1
    if MAC:
        finish_mac_app(exe)
        program = exe / "Contents" / "MacOS" / NAME
        missing = missing_from(program)
        if missing:
            print(f"The build is missing {', '.join(missing)}, so it would fail for users.", file=sys.stderr)
            return 1
        dmg = make_dmg(exe)
        print()
        print(f"Built {exe}")
        print(f"  {dmg.name}  {dmg.stat().st_size / 1_000_000:.0f} MB")
        print(f"  sha256  {hashlib.sha256(dmg.read_bytes()).hexdigest()}")
        return 0
    missing = missing_from(exe)
    if missing:
        print(f"The build is missing {', '.join(missing)}, so it would fail for users.", file=sys.stderr)
        print("Add it to the build, and keep it in REQUIRED_MODULES.", file=sys.stderr)
        return 1
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    print()
    print(f"Built {exe}")
    print(f"  size    {exe.stat().st_size / 1_000_000:.0f} MB")
    print(f"  sha256  {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
