"""Regression suite of real photographs that once failed.

Synthetic distortions miss what real signage does - stylised modules, centre
logos, glare through acrylic, colour codes on colour backgrounds. Each of
these images broke the scanner at some point; keep them passing.
"""

import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniqr.decode import Scanner  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

EXPECTED = {
    # photo -> payloads that must be recovered
    "sap_flyer.png": {
        "https://bit.ly/4jQ5iLN",
        "https://bit.ly/40HVnio",
        "https://bit.ly/3WHdJiw",
    },
    # Stylised rounded modules, centre logo, partly shadowed, slight rotation.
    "american.png": {"https://go.bofa.com/q/7b5032"},
    # Small, dotted modules, dark navy on crimson, behind glare-y acrylic.
    "morningstar.png": {
        "https://linktr.ee/qr/45d45578-8152-4e47-8609-2fb8a62923c4"
    },
}


def main() -> int:
    scanner = Scanner()
    failures = 0
    for name, expected in EXPECTED.items():
        path = ROOT / name
        if not path.exists():
            print(f"{name:<20} SKIP (not found)")
            continue
        found = {d.text for d in scanner.scan(cv2.imread(str(path)))}
        missing = expected - found
        status = "ok" if not missing else "FAIL"
        print(f"{name:<20} {status}  {len(expected & found)}/{len(expected)}")
        for m in missing:
            print(f"    missing: {m}")
            failures += 1
    print("-" * 44)
    print("all real photos pass" if not failures else f"{failures} payload(s) missing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
