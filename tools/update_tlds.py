"""Refresh UniQR's list of real top-level domains from IANA.

    python tools/update_tlds.py

IANA, which runs the internet's names, publishes every top-level domain in one
text file. This writes it out twice, for the Python and the C++ UniQR, so both
read bare addresses like "example.org/apply" by the same list, offline. Run it
before each release so new domains are picked up.
"""

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"
PY_OUT = ROOT / "uniqr" / "tlds.py"
CPP_OUT = ROOT / "cpp" / "src" / "core" / "tlds.inc"


def wrap(names: list[str], width: int = 76) -> list[str]:
    lines, line = [], ""
    for name in names:
        if line and len(line) + 1 + len(name) > width:
            lines.append(line)
            line = name
        else:
            line = f"{line} {name}" if line else name
    return [*lines, line] if line else lines


def main() -> int:
    with urllib.request.urlopen(SOURCE, timeout=30) as response:  # noqa: S310 - a fixed https address
        text = response.read().decode("ascii")
    lines = text.splitlines()
    version = lines[0].lstrip("# ").strip()
    names = sorted(line.strip().lower() for line in lines[1:] if line.strip() and not line.startswith("#"))
    if len(names) < 1000 or "com" not in names:
        print(f"The list from {SOURCE} looks wrong ({len(names)} names). Nothing written.", file=sys.stderr)
        return 1

    body = "\n".join(wrap(names))
    PY_OUT.write_text(
        f'"""Every top-level domain, from {SOURCE}\n\n'
        f"{version}.\nMade by tools/update_tlds.py: do not edit by hand.\n"
        f'"""\n\n_NAMES = """\n{body}\n"""\nTLDS = frozenset(_NAMES.split())\n',
        encoding="utf-8",
        newline="\n",
    )
    cpp_body = "\n".join(f'"{line} "' for line in wrap(names, 72))
    CPP_OUT.write_text(
        f"// Every top-level domain, from {SOURCE}\n"
        f"// {version}.\n// Made by tools/update_tlds.py: do not edit by hand.\n"
        f"// Included by link.cpp as one space-separated string.\n{cpp_body}\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{len(names)} top-level domains ({version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
