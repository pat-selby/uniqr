"""Record an animated GIF of the real picker overlay.

Displays a scene full-screen, runs the actual Scanner and Picker over it, and
grabs the desktop while driving the hover from code to code. The frames are
the real UI, not a mock-up.

    python tools\\record_demo.py sap_flyer.png -o demo.gif
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniqr import capture  # noqa: E402
from uniqr.decode import Scanner  # noqa: E402
from uniqr.overlay import Picker  # noqa: E402

HOLD_MS = 900          # how long each code stays highlighted
FRAME_MS = 110         # capture interval
GIF_WIDTH = 900


def build_scene(path: str, screen) -> np.ndarray:
    """Letterbox an image to fill the screen, as if it were open on-screen."""
    img = cv2.imread(path)
    if img is None:
        raise SystemExit(f"could not read {path}")
    scale = min(screen.width / img.shape[1], screen.height / img.shape[0])
    resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    scene = np.full((screen.height, screen.width, 3), 24, dtype=np.uint8)
    y = (screen.height - resized.shape[0]) // 2
    x = (screen.width - resized.shape[1]) // 2
    scene[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return scene


def record(scene: np.ndarray, out: str) -> int:
    scanner = Scanner()
    dets = scanner.scan(scene)
    if not dets:
        print("no codes in the scene - nothing to demo", file=sys.stderr)
        return 1
    dets.sort(key=lambda d: (d.center[1] // 100, d.center[0]))
    print(f"{len(dets)} codes found; recording...")

    picker = Picker(scene, dets, origin=(0, 0))
    frames: list[Image.Image] = []

    def grab_frame() -> None:
        shot = capture.grab()
        rgb = cv2.cvtColor(shot, cv2.COLOR_BGR2RGB)
        small = cv2.resize(
            rgb,
            (GIF_WIDTH, int(GIF_WIDTH * rgb.shape[0] / rgb.shape[1])),
            interpolation=cv2.INTER_AREA,
        )
        frames.append(Image.fromarray(small))

    # Timeline: settle, then walk the pointer across each code, then finish on
    # the first one as if the user were about to click it.
    t = 250
    for _ in range(4):
        picker.root.after(t, grab_frame)
        t += FRAME_MS

    for index in list(range(len(dets))) + [0]:
        picker.root.after(t, lambda i=index: picker._show_card(i))
        for _ in range(max(1, HOLD_MS // FRAME_MS)):
            t += FRAME_MS
            picker.root.after(t, grab_frame)

    picker.root.after(t + 400, picker._dismiss)
    picker.show()

    if not frames:
        print("captured no frames", file=sys.stderr)
        return 1

    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=True,
    )
    size_mb = Path(out).stat().st_size / 1_048_576
    print(f"wrote {out}  {len(frames)} frames  {size_mb:.1f} MB")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("image", help="scene to display and scan")
    p.add_argument("-o", "--out", default="demo.gif")
    args = p.parse_args()

    capture.set_dpi_aware()
    scene = build_scene(args.image, capture.virtual_screen())
    return record(scene, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
