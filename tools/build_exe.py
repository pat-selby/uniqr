"""Build UniQR.exe: one file that runs without Python installed.

    pip install -e ".[windows]" pyinstaller
    python tools/build_exe.py

The result is dist/UniQR.exe. Run this from a clean virtual environment, not
your everyday Python. PyInstaller packs in what the program imports, but a
crowded environment gives its hooks more to find, and the file gets bigger.

What the choices are for:

  --onefile     one file to hand to someone. The cost is that it unpacks itself
                to a temporary folder on every start, a few seconds.
  --noconsole   no black window. UniQR lives in the tray and logs to a file.
  an icon       the tray icon is drawn in code, so the same drawing is written
                to an .ico here and baked into the file.
  version info  the Name and Details shown in the file's Properties. Without
                them Windows shows a blank, which looks like malware.

Not used on purpose: UPX compression. It shrinks the file and makes antivirus
programs much likelier to flag it.

The file is not code-signed, so Windows SmartScreen will say "unknown publisher"
the first time. Signing needs a certificate, which costs money each year.
"""

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from uniqr import __version__  # noqa: E402
from uniqr.icon import SIZES, _draw  # noqa: E402

BUILD = ROOT / "build" / "pyinstaller"
DIST = ROOT / "dist"
NAME = "UniQR"

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

    BUILD.mkdir(parents=True, exist_ok=True)
    pyinstaller.run(
        [
            str(ROOT / "app.py"),
            "--name", NAME,
            "--onefile",
            "--noconsole",
            "--noconfirm",
            "--clean",
            "--icon", str(write_icon()),
            "--version-file", str(write_version_file()),
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

    exe = DIST / f"{NAME}.exe"
    if not exe.exists():
        print("The build did not produce an exe.", file=sys.stderr)
        return 1
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    print()
    print(f"Built {exe}")
    print(f"  size    {exe.stat().st_size / 1_000_000:.0f} MB")
    print(f"  sha256  {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
