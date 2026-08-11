"""Build a source zip that unpacks cleanly on macOS and Linux.

PowerShell's Compress-Archive writes Windows path separators into the archive,
which makes `unzip` on macOS warn and guess. Writing the entries here with
explicit forward slashes avoids that, and skips build/cache junk.

    python tools/make_zip.py -o uniqr-mac.zip
"""

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INCLUDE_FILES = ["app.py", "scan.py", "requirements.txt", "README.md"]
INCLUDE_DIRS = ["uniqr", "tests", "tools"]
INCLUDE_FIXTURES = [
    "american.png",
    "morningstar.png",
    "sap_flyer.png",
    "color_scene.png",
]

SKIP_DIRS = {"__pycache__", ".venv", ".git", "build", "dist", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".log"}


def wanted(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    return path.suffix not in SKIP_SUFFIXES


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-o", "--out", default="uniqr-mac.zip")
    p.add_argument("--no-fixtures", action="store_true", help="code only")
    args = p.parse_args()

    out = ROOT / args.out
    names: list[tuple[Path, str]] = []

    for name in INCLUDE_FILES + ([] if args.no_fixtures else INCLUDE_FIXTURES):
        path = ROOT / name
        if path.exists():
            names.append((path, name))

    for directory in INCLUDE_DIRS:
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_file() and wanted(path):
                # as_posix keeps forward slashes regardless of host OS.
                names.append((path, path.relative_to(ROOT).as_posix()))

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in names:
            zf.write(path, arcname)

    print(f"wrote {out.name}  {len(names)} files  "
          f"{out.stat().st_size / 1_048_576:.2f} MB")
    bad = [n for _, n in names if "\\" in n]
    if bad:
        print("WARNING: backslashes in entries:", bad, file=sys.stderr)
        return 1
    print("all entries use forward slashes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
