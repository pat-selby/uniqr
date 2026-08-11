"""Scan the screen (or an image file) for QR codes and print what they hold.

    python scan.py                # every monitor
    python scan.py --cursor       # 600px box around the mouse
    python scan.py poster.png     # an image on disk
    python scan.py --selftest     # round-trip a generated code, no screen needed
"""

import argparse
import sys

import cv2
import numpy as np

from uniqr.decode import Scanner, payload_kind


def load_capture():
    """Import the screen-capture module, which is Windows-only.

    Detection itself is plain OpenCV and runs anywhere, so scanning an image
    file and --selftest work on macOS and Linux too. Only grabbing the live
    screen needs Win32, so that import stays out of the module top level.
    """
    try:
        from uniqr import capture
    except ImportError as exc:
        print(
            f"screen capture is Windows-only ({exc}).\n"
            "Scanning an image file still works: python scan.py photo.png",
            file=sys.stderr,
        )
        return None
    return capture


def selftest() -> int:
    """Encode a known payload, decode it back, and report."""
    expected = "https://example.com/uniqr-selftest?id=42"
    encoder = cv2.QRCodeEncoder.create()
    qr = encoder.encode(expected)

    # Blow it up to a realistic on-screen size and pad it - detectors need a
    # quiet zone around the code.
    qr = cv2.resize(qr, (240, 240), interpolation=cv2.INTER_NEAREST)
    canvas = np.full((400, 400), 255, dtype=np.uint8)
    canvas[80:320, 80:320] = qr
    image = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)

    found = Scanner().scan(image)
    if len(found) == 1 and found[0].text == expected:
        print(f"selftest ok - decoded {expected}")
        return 0
    print(f"selftest FAILED - got {[d.text for d in found]}", file=sys.stderr)
    return 1


def report(detections, origin=(0, 0)) -> int:
    if not detections:
        print("no QR codes found")
        return 1

    ox, oy = origin
    for i, det in enumerate(detections, 1):
        left, top, w, h = det.bbox
        print(f"[{i}] {payload_kind(det.text)}")
        print(f"    {det.text}")
        print(f"    at ({left + ox}, {top + oy}) size {w}x{h}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", nargs="?", help="image file to scan")
    parser.add_argument(
        "--cursor", action="store_true", help="scan a box around the mouse"
    )
    parser.add_argument("--size", type=int, default=600, help="--cursor box size")
    parser.add_argument("--selftest", action="store_true", help="no screen needed")
    parser.add_argument("--save", help="write the capture to a file for debugging")
    parser.add_argument(
        "--exhaustive",
        action="store_true",
        help="add an overlapping tiled pass - seconds, not milliseconds",
    )
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    if args.image:
        image = cv2.imread(args.image)
        if image is None:
            print(f"could not read {args.image}", file=sys.stderr)
            return 2
        origin = (0, 0)
    else:
        capture = load_capture()
        if capture is None:
            return 3
        capture.set_dpi_aware()
        if args.cursor:
            rect = capture.region_around(*capture.cursor_pos(), size=args.size)
        else:
            rect = capture.virtual_screen()
        image = capture.grab(rect)
        origin = (rect.left, rect.top)

    if args.save:
        cv2.imwrite(args.save, image)

    h, w = image.shape[:2]
    scanner = Scanner()
    print(f"scanning {w}x{h}{' exhaustively' if args.exhaustive else ''}...")
    found = (
        scanner.scan_exhaustive(image) if args.exhaustive else scanner.scan(image)
    )
    return report(found, origin)


if __name__ == "__main__":
    raise SystemExit(main())
