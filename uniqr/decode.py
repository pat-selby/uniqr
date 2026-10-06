"""QR detection and decoding.

OpenCV ships two QR detectors with different blind spots. The Aruco-based one
is much stronger on multiple codes and codes at an angle; the classic one
still wins on some low-contrast captures. Running both and merging costs a few
milliseconds and measurably raises the hit rate on real screen content.

Both detectors assume dark modules on a light background, so neither sees an
inverted (light-on-dark) code at all - measured at 0% across every rotation.
Dark-themed sites and slide decks produce those constantly, so every scan also
runs against an inverted copy. Upscaling for very small codes costs more, so
it only runs when the cheap passes come back empty.
"""

from dataclasses import dataclass, replace
from typing import Any

import cv2
import numpy as np

# The decoders log a warning per attempt on payloads using ECI encoding, even
# when they go on to decode them fine. Several passes per scan turns that into
# pages of noise, so keep OpenCV to real errors.
cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)

# zxing-cpp is a second, independent decoder. It reads several stylised codes
# that OpenCV locates but cannot decode - a real "Scan to download" card with
# rounded finder patterns decoded at native scale with no preprocessing while
# both OpenCV detectors failed on the same pixels. Optional: a missing install
# degrades to OpenCV alone rather than breaking the scanner.
zxingcpp: Any
_ZXING_FORMATS: Any
_OTHER_FORMATS: Any
_MAXICODE: Any
_BINARIZERS: Any

try:
    import zxingcpp

    _fmts = zxingcpp.BarcodeFormat
    # The QR family: cheap, and read in every step of the ladder.
    _ZXING_FORMATS = [
        getattr(_fmts, n) for n in ("QRCode", "MicroQRCode", "RMQRCode") if hasattr(_fmts, n)
    ]
    # The other 2D codes. Each costs a few times what the QR family does on a
    # full screen, so they get one pass per scan rather than a place in every
    # step. Linear barcodes (EAN, Code 128 ...) are left out on purpose: they
    # are what a screen is full of, and nobody pressed a hotkey to read a
    # product label.
    _OTHER_FORMATS = [
        getattr(_fmts, n) for n in ("DataMatrix", "Aztec", "PDF417") if hasattr(_fmts, n)
    ]
    # MaxiCode is a bullseye and hexagons, and zxing's default thresholding
    # does not reliably separate the hexagons from the page. Measured on the
    # benchmark: a fixed threshold read all four codes the default missed.
    _MAXICODE = [_fmts.MaxiCode] if hasattr(_fmts, "MaxiCode") else []
    _BINARIZERS = zxingcpp.Binarizer
except ImportError:  # pragma: no cover - exercised by the no-zxing test
    zxingcpp = None
    _ZXING_FORMATS = None
    _OTHER_FORMATS = None
    _MAXICODE = None
    _BINARIZERS = None

# Names for the cards. Keyed by zxing's own format name.
SYMBOLOGY_NAMES = {
    "QRCode": "QR Code",
    "MicroQRCode": "Micro QR",
    "RMQRCode": "rMQR",
    "DataMatrix": "Data Matrix",
    "Aztec": "Aztec",
    "PDF417": "PDF417",
    "MaxiCode": "MaxiCode",
}


def _format_for(symbology: str) -> Any:
    """The zxing format behind a card label, or None for one we do not read."""
    if zxingcpp is None:
        return None
    for name, label in SYMBOLOGY_NAMES.items():
        if label == symbology:
            return getattr(zxingcpp.BarcodeFormat, name, None)
    return None


def zxing_available() -> bool:
    """Whether the second decoder is installed."""
    return zxingcpp is not None


# Below roughly this many pixels a code needs upscaling before it will decode.
SMALL_CODE_PX = 60

# Tiled pass: an overlapping grid, each tile enlarged before decoding. The
# grid adapts to the frame, because a tile smaller than the code it is hunting
# defeats the whole point. A fixed 3x3 on a 579x381 image produced 158px-tall
# tiles while the code was 215px, so no tile could ever contain it.
TILE_GRID = 3
TILE_MIN_PX = 360
TILE_OVERLAP = 0.25
TILE_SCALE = 2.0

# Size each located code is flattened to before decoding, plus how much
# surrounding area to keep so the quiet zone survives the warp.
# A located code is re-rendered at a few times its source size before
# decoding - small codes need the magnification, large ones are capped.
RECTIFY_ZOOM = 3.0
RECTIFY_MIN = 320
RECTIFY_MAX = 720
RECTIFY_PAD = 0.20

# Extra patch sizes retried when the native one will not decode.
PATCH_SIZES = (384, 512)

# Frames larger than this skip the upscale retry - see the note in scan().
UPSCALE_MAX_DIM = 1200

# Module-growing kernels tried when a code looks stylised (dotted modules).
DESTYLE_KERNELS = (3, 5)

# Enlargements tried, in order, on a frame small enough to afford them. Every
# one runs the full set of readers.
UPSCALE_FACTORS = (2.0, 4.0)

# One more enlargement that only zxing reads. OpenCV can only ever find a QR
# code, and running its detectors on a frame three times the size is most of
# the cost of a step, so it is left out where it adds nothing. This size is
# what the formats only zxing reads (rMQR in particular) gain from.
ZXING_ONLY_FACTORS = (3.0,)

# Past this many pixels on the long side, a robust read tries only zxing's
# default threshold. See Scanner._robust_read.
ROBUST_MAX_PX = 2600

# The softening pass: a blur of about a quarter of a module on a typical
# on-screen code, a few pixels at most. See Scanner._softened_pass.
SOFTEN_SIGMA = 1.2


def _quad_span(quad: np.ndarray) -> float:
    return float(
        max(quad[:, 0].max() - quad[:, 0].min(), quad[:, 1].max() - quad[:, 1].min())
    )


def _resize_max(image: np.ndarray, target: int) -> np.ndarray:
    scale = target / max(image.shape[:2])
    interp = cv2.INTER_LANCZOS4 if scale > 1 else cv2.INTER_AREA
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=interp)


def _bbox_crop(image: np.ndarray, quad: np.ndarray, margin: float = 0.06):
    """The upright rectangle around a quad, with a small quiet-zone margin."""
    pad = max(8, int(_quad_span(quad) * margin))
    h, w = image.shape[:2]
    x0 = max(0, int(quad[:, 0].min()) - pad)
    y0 = max(0, int(quad[:, 1].min()) - pad)
    x1 = min(w, int(quad[:, 0].max()) + pad)
    y1 = min(h, int(quad[:, 1].max()) + pad)
    if x1 <= x0 or y1 <= y0:
        return None
    return image[y0:y1, x0:x1]


def _zxing_detect(
    image: np.ndarray, formats: Any = None, binarizer: Any = None
) -> list["Detection"]:
    """Read with zxing-cpp, keeping each code's corner positions."""
    if zxingcpp is None:
        return []
    options: dict[str, Any] = {}
    if binarizer is not None:
        options["binarizer"] = binarizer
    try:
        results = zxingcpp.read_barcodes(
            image, formats=_ZXING_FORMATS if formats is None else formats, **options
        )
    except Exception:  # noqa: BLE001 - a decoder failure is not a scan failure
        return []

    out: list[Detection] = []
    for result in results:
        if not result.text:
            continue
        p = result.position
        quad = np.array(
            [
                [p.top_left.x, p.top_left.y],
                [p.top_right.x, p.top_right.y],
                [p.bottom_right.x, p.bottom_right.y],
                [p.bottom_left.x, p.bottom_left.y],
            ],
            dtype=np.float32,
        )
        name = result.format.name
        out.append(Detection(result.text, quad, SYMBOLOGY_NAMES.get(name, name)))
    return out


def _zxing_text(image: np.ndarray) -> str:
    """Just the payload, for the patch reader."""
    found = _zxing_detect(image)
    return found[0].text if found else ""


def _contrast_variants(patch: np.ndarray):
    """Successively harder attempts to turn a patch into clean black and white.

    Plain grey-and-threshold fails on real signage for two reasons. A code
    printed in colour loses most of its separation when RGB collapses to
    luminance - navy on crimson measures a grey range of about 33 out of 255.
    And one global threshold cannot serve a frame that is glare-bright at one
    edge and shadowed at the other. CLAHE fixes both by equalising contrast in
    small neighbourhoods rather than across the whole patch, and the red
    channel alone often separates warm-coloured codes that grey flattens.
    """
    yield patch

    grey = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    equalised = clahe.apply(grey)

    _, otsu = cv2.threshold(equalised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, plain_otsu = cv2.threshold(grey, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    red = clahe.apply(cv2.split(patch)[2])

    block = max(11, (patch.shape[0] // 12) * 2 + 1)
    adaptive = cv2.adaptiveThreshold(
        equalised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, 6
    )

    for single in (equalised, otsu, red, plain_otsu, adaptive):
        yield cv2.cvtColor(single, cv2.COLOR_GRAY2BGR)


def tile_grid_for(width: int, height: int) -> int:
    """How many tiles per side this frame can be split into.

    Splitting only helps while each tile is still big enough to hold a whole
    code. Past that the grid slices codes apart and the pass is worse than
    useless, so small frames get fewer tiles - down to a single tile, which is
    just the frame itself at higher magnification.
    """
    return max(1, min(TILE_GRID, int(min(width, height) // TILE_MIN_PX)))


def _tile_rects(
    width: int, height: int, grid: int | None = None, overlap: float = TILE_OVERLAP
) -> list[tuple[int, int, int, int]]:
    """Overlapping tile bounds covering the whole frame."""
    if grid is None:
        grid = tile_grid_for(width, height)
    step_x, step_y = width / grid, height / grid
    pad_x, pad_y = step_x * overlap, step_y * overlap
    rects = []
    for row in range(grid):
        for col in range(grid):
            rects.append(
                (
                    max(0, int(col * step_x - pad_x)),
                    max(0, int(row * step_y - pad_y)),
                    min(width, int((col + 1) * step_x + pad_x)),
                    min(height, int((row + 1) * step_y + pad_y)),
                )
            )
    return rects


@dataclass
class Detection:
    """One decoded code and where it sat in the captured image."""

    text: str
    quad: np.ndarray  # 4x2 float32, corners in capture-local pixels
    symbology: str = "QR Code"  # which kind of code it was; see SYMBOLOGY_NAMES

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """(left, top, width, height) in capture-local pixels."""
        xs, ys = self.quad[:, 0], self.quad[:, 1]
        left, top = int(xs.min()), int(ys.min())
        return left, top, int(xs.max()) - left, int(ys.max()) - top

    @property
    def center(self) -> tuple[int, int]:
        return int(self.quad[:, 0].mean()), int(self.quad[:, 1].mean())

    def offset(self, dx: int, dy: int) -> "Detection":
        """Shift into another coordinate space, e.g. capture-local to screen."""
        return replace(self, quad=self.quad + np.array([dx, dy], dtype=np.float32))


def _run(detector, image: np.ndarray) -> list[Detection]:
    try:
        ok, texts, points, _ = detector.detectAndDecodeMulti(image)
    except cv2.error:
        return []
    if not ok or points is None:
        return []

    out = []
    for text, quad in zip(texts, points):
        # A code can be located but not decoded (blur, occlusion). Skip those:
        # showing an empty result is worse than showing nothing.
        if text:
            out.append(Detection(text, np.asarray(quad, dtype=np.float32)))
    return out


def _merge(groups: list[list[Detection]]) -> list[Detection]:
    """Combine detector results, dropping the same code found twice."""
    merged: list[Detection] = []
    for group in groups:
        for det in group:
            cx, cy = det.center
            duplicate = any(
                other.text == det.text
                and abs(other.center[0] - cx) < 40
                and abs(other.center[1] - cy) < 40
                for other in merged
            )
            if not duplicate:
                merged.append(det)
    return merged


class Scanner:
    """Reusable detector pair. Construction is slow-ish, so keep one around."""

    def __init__(self) -> None:
        self._aruco = cv2.QRCodeDetectorAruco()
        self._classic = cv2.QRCodeDetector()

    def _detect(self, image: np.ndarray, scale: float = 1.0) -> list[Detection]:
        found = _merge([_run(self._aruco, image), _run(self._classic, image)])
        if scale == 1.0:
            return found
        return [replace(d, quad=d.quad / scale) for d in found]

    def _detect_both_polarities(
        self, image: np.ndarray, scale: float = 1.0
    ) -> list[Detection]:
        def rescale(dets: list[Detection]) -> list[Detection]:
            if scale == 1.0:
                return dets
            return [replace(d, quad=d.quad / scale) for d in dets]

        return _merge(
            [
                # zxing first: it is the strongest single reader here. It
                # inverts internally (try_invert defaults on), so unlike the
                # OpenCV detectors it only needs one call, not one per
                # polarity - passing it a flipped copy as well was pure waste.
                rescale(_zxing_detect(image)),
                self._detect(image, scale),
                self._detect(cv2.bitwise_not(image), scale),
            ]
        )

    def _other_formats(self, image: np.ndarray, scale: float = 1.0) -> list[Detection]:
        """Data Matrix, Aztec, PDF417 and MaxiCode. One zxing call, no ladder.

        These have no OpenCV detector, so there is nothing to rectify with, and
        the QR-specific steps below (locate, destyle) do not apply to them.
        Their cost is why this runs once per scan instead of at every step.
        """
        if zxingcpp is None:
            return []
        found = _zxing_detect(image, _OTHER_FORMATS) if _OTHER_FORMATS else []
        if _MAXICODE:
            found += self._maxicode(image)
        return [replace(d, quad=d.quad / scale) for d in found] if scale != 1.0 else found

    def _maxicode(self, image: np.ndarray) -> list[Detection]:
        """MaxiCode, which no single threshold reads in every light.

        A bullseye and hexagons. On a clutter-heavy page the adaptive default
        loses the hexagons and a fixed threshold finds them; under uneven
        lighting it is the other way round. The benchmark had one failure of
        each kind, and each was recovered by the other setting, so both run.
        """
        grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return _zxing_detect(grey, _MAXICODE) or _zxing_detect(
            grey, _MAXICODE, _BINARIZERS.FixedThreshold
        )

    def _robust_read(self, image: np.ndarray, scale: float = 1.0) -> list[Detection]:
        """Every 2D format, on grey, under each of zxing's thresholding modes.

        Several reads where one is normal, so only for frames small enough that
        it costs next to nothing. Different damage wants a different threshold:
        the default adapts to local brightness, the global one ignores local
        detail that is only noise, and the fixed one survives a flat low
        contrast. On the benchmark's misses the right choice differed case by
        case, with no pattern worth hard-coding, so all three are tried.
        """
        if zxingcpp is None:
            return []
        grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        formats = [*_ZXING_FORMATS, *_OTHER_FORMATS, *_MAXICODE]
        modes: tuple[Any, ...] = (None, _BINARIZERS.GlobalHistogram, _BINARIZERS.FixedThreshold)
        if max(image.shape[:2]) > ROBUST_MAX_PX:
            # Reads this big are the slowest there are, and the smaller
            # enlargements already cover what the extra modes catch.
            modes = modes[:1]
        for binarizer in modes:
            found = _zxing_detect(grey, formats, binarizer)
            if found:
                return [replace(d, quad=d.quad / scale) for d in found] if scale != 1.0 else found
        return []

    def _locate(self, image: np.ndarray) -> list[np.ndarray]:
        """Find where codes are, without trying to read them.

        Locating survives conditions that defeat decoding - small, tilted,
        blurry, unevenly lit - so this finds codes a straight decode misses.
        """
        quads: list[np.ndarray] = []
        for variant in (image, cv2.bitwise_not(image)):
            for det in (self._aruco, self._classic):
                try:
                    ok, points = det.detectMulti(variant)
                except cv2.error:
                    continue
                if not ok or points is None:
                    continue
                for quad in points:
                    quad = np.asarray(quad, dtype=np.float32)
                    c = quad.mean(axis=0)
                    near = any(
                        np.linalg.norm(c - q.mean(axis=0)) < 40 for q in quads
                    )
                    if not near:
                        quads.append(quad)
        return quads

    def _rectify_and_decode(
        self, image: np.ndarray, quad: np.ndarray
    ) -> Detection | None:
        """Flatten one located code to a straight-on square and read it.

        The warp removes rotation and perspective in a single step and lands
        the code at a comfortable size, which is why this recovers codes that
        the whole-frame decoders cannot. Because the patch is small, it is
        affordable to retry it under several contrast treatments.
        """
        size = int(np.clip(_quad_span(quad) * RECTIFY_ZOOM, RECTIFY_MIN, RECTIFY_MAX))
        centre = quad.mean(axis=0)
        expanded = (quad - centre) * (1 + RECTIFY_PAD) + centre
        target = np.float32([[0, 0], [size, 0], [size, size], [0, size]])
        try:
            m = cv2.getPerspectiveTransform(expanded, target)
        except cv2.error:
            return None
        patch = cv2.warpPerspective(
            image, m, (size, size), flags=cv2.INTER_LANCZOS4
        )

        # Detectors need a quiet zone; the warp crops right to the edge.
        margin = size // 8
        canvas = np.full(
            (size + margin * 2, size + margin * 2, 3), 255, dtype=np.uint8
        )
        canvas[margin:-margin, margin:-margin] = patch

        text = self._read_patch(canvas)
        if text:
            return Detection(text, quad)

        # Warping is the right move for a tilted code, but on a big flat one
        # the padding drags in surrounding scenery and skews the threshold
        # against the code itself. A straight rectangular cut avoids that.
        text = self._read_patch(_bbox_crop(image, quad))
        return Detection(text, quad) if text else None

    def _read_patch(self, patch: np.ndarray | None) -> str:
        """Try a patch at several sizes under several contrast treatments.

        Heavily stylised codes decode unpredictably: shifting a crop by a few
        pixels moves every CLAHE tile boundary, which moves the threshold, and
        a code that read cleanly stops reading. Measured on real signage, the
        same code decoded at 16, 24 and 30 pixels of margin but not at 33 or
        40. Rather than chase one lucky framing, try a handful and take the
        first that lands - each attempt is cheap on a patch this size.
        """
        if patch is None or patch.size == 0:
            return ""
        for target in (None, *PATCH_SIZES):
            sized = patch if target is None else _resize_max(patch, target)
            for variant in _contrast_variants(sized):
                for polarity in (variant, cv2.bitwise_not(variant)):
                    text = _zxing_text(polarity)
                    if text:
                        return text
                    for det in (self._classic, self._aruco):
                        try:
                            text, _, _ = det.detectAndDecode(polarity)
                        except cv2.error:
                            continue
                        if text:
                            return text
        return ""

    def scan(self, image: np.ndarray, thorough: bool = True) -> list[Detection]:
        """Find every decodable code in a BGR image, and check the unusual ones.

        Anything other than a plain QR code must be read a second way before it
        is believed. See _confirm.
        """
        return self._validated(image, self._scan_raw(image, thorough))

    def _validated(self, image: np.ndarray, found: list[Detection]) -> list[Detection]:
        return [d for d in found if d.symbology == "QR Code" or self._confirm(image, d)]

    def _confirm(self, image: np.ndarray, det: Detection) -> bool:
        """Read a code again, differently, and believe it only if both agree.

        Every reader of these codes corrects errors, and a code damaged past
        what it can correct will occasionally "correct" into a different valid
        message instead of failing. The benchmark caught one: a PDF417 under
        three kinds of damage came back as 51 characters of garbage that zxing
        called valid, and the same code read under other treatments gave
        different garbage each time. Two independent reads agreeing on a
        string of that length is not luck, so agreement is the test, and a
        second read that returns something else is the veto.

        QR codes skip this. Their error correction is far stronger, and in
        thousands of benchmark codes it never returned a wrong answer. The
        other formats have not earned that trust, and a wrong link is worse
        than no link.
        """
        fmt = _format_for(det.symbology)
        if fmt is None or zxingcpp is None:
            return True
        x, y, w, h = det.bbox
        pad = int(0.3 * max(w, h)) + 8
        ih, iw = image.shape[:2]
        crop = image[max(0, y - pad) : min(ih, y + h + pad), max(0, x - pad) : min(iw, x + w + pad)]
        if crop.size == 0:
            return False
        grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        def enlarged(k: float) -> np.ndarray:
            return cv2.resize(grey, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)

        # Many ways to look, because the first read could have come from any
        # of the recovery steps and the second has to be able to find the
        # code in something else. A narrow set confirmed too little: it threw
        # away rMQR codes that had read correctly, a fifth of them on one seed.
        treatments = (
            grey,
            enlarged(2),
            enlarged(3),
            enlarged(4),
            cv2.GaussianBlur(grey, (0, 0), 1.2),
            cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(grey),
            cv2.GaussianBlur(enlarged(2), (0, 0), 1.5),
        )
        modes: tuple[Any, ...] = (
            None,
            _BINARIZERS.GlobalHistogram,
            _BINARIZERS.FixedThreshold,
        )
        for treated in treatments:
            for binarizer in modes:
                options = {} if binarizer is None else {"binarizer": binarizer}
                try:
                    results = zxingcpp.read_barcodes(treated, formats=[fmt], **options)
                except Exception:  # noqa: BLE001 - a failed re-read is not a veto
                    continue
                for r in results:
                    if not r.text:
                        continue
                    # The first thing it reads decides: the same text confirms
                    # it, anything else is the same symbol read another way.
                    return r.text == det.text
        return False

    def _scan_raw(self, image: np.ndarray, thorough: bool = True) -> list[Detection]:
        """Find every decodable code in a BGR image, unchecked.

        Both polarities always run - a screen can hold a light and a dark code
        at once, and merging is the only way to see both. `thorough` adds the
        locate-then-rectify pass, which is what recovers the second and third
        code when several small or tilted ones share a frame.
        """
        whole = _merge([self._detect_both_polarities(image), self._other_formats(image)])
        if not thorough:
            return whole

        # Deliberately NOT short-circuiting on a non-empty result: finding one
        # code says nothing about whether others are present, and stopping
        # early here is exactly what made multi-code frames report just one.
        found = _merge([whole, self._rectify_pass(image)])
        if found:
            return found

        # Nothing found by any conventional route: the code may be stylised.
        found = self._destylized_pass(image)
        if found:
            return found

        found = self._softened_pass(image)
        if found:
            return found

        # Nothing at all: the code may be too small for the locator to see.
        # Enlarging helps, but only where it is affordable - blowing a full
        # 1920x1080 screen up to 4x costs seconds, and "no code on screen" is
        # the common case, so a whole-screen miss must stay cheap.
        if max(image.shape[:2]) > UPSCALE_MAX_DIM:
            return []

        for factor in UPSCALE_FACTORS:
            big = cv2.resize(
                image, None, fx=factor, fy=factor, interpolation=cv2.INTER_LANCZOS4
            )
            hits = _merge(
                [
                    self._detect_both_polarities(big, factor),
                    # Only small frames reach this step, so reading every
                    # format under every threshold is affordable here, and
                    # those are the ones that gain most from being enlarged.
                    # It covers the other formats too, so they are not read
                    # separately.
                    self._robust_read(big, factor),
                    [replace(d, quad=d.quad / factor) for d in self._rectify_pass(big)],
                ]
            )
            if hits:
                return hits

        for factor in ZXING_ONLY_FACTORS:
            big = cv2.resize(
                image, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC
            )
            hits = self._robust_read(big, factor)
            if hits:
                return hits
        return []

    def _destylized_pass(self, image: np.ndarray) -> list[Detection]:
        """Rebuild stylised codes into ones the detectors recognise.

        Marketing codes often draw each module as a rounded dot with a gap
        around it. The detectors sample a module grid, hit mostly background,
        and fail to locate the code at all - so no amount of work further down
        the pipeline helps. Thresholding and then growing the dark modules by
        a module-ish amount closes the gaps and restores a conventional grid.
        Kernel size depends on how many pixels a module occupies, which is not
        known in advance, so a couple of plausible sizes get tried.
        """
        grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(
            grey, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        for k in DESTYLE_KERNELS:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
            # Erode grows the dark modules; dilate does the same for a code
            # printed light-on-dark.
            for op in (cv2.erode, cv2.dilate):
                fixed = cv2.cvtColor(op(binary, kernel), cv2.COLOR_GRAY2BGR)
                # Plain detection is enough here: once the grid is restored
                # the locator finds the code unaided, and adding the rectify
                # pass tripled the cost of every failed scan for no gain.
                found = self._detect_both_polarities(fixed)
                if found:
                    return found
        return []

    def _softened_pass(self, image: np.ndarray) -> list[Detection]:
        """Melt rings and dots into the solid shapes a detector expects.

        Some designs draw each finder pattern as a ring around a dot and each
        module as a separate dot. The OpenCV locators find no corner at all in
        those, so nothing downstream gets a chance - not even the rectify
        pass, which starts from a located quad. Measured on the benchmark: all
        five ring-pattern codes viewed at an angle that nothing else read came
        back with a blur of about a quarter of a module.

        Cheap ones first. Only a small frame can afford the enlargement that
        catches the rest, for the same reason the upscale step below it is
        limited.
        """
        soft = cv2.GaussianBlur(image, (0, 0), SOFTEN_SIGMA)
        found = _zxing_detect(soft)
        if found:
            return found

        grey = cv2.cvtColor(soft, cv2.COLOR_BGR2GRAY)
        equalised = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(grey)
        found = _zxing_detect(cv2.cvtColor(equalised, cv2.COLOR_GRAY2BGR))
        if found:
            return found

        if max(image.shape[:2]) > UPSCALE_MAX_DIM or _BINARIZERS is None:
            return []
        big = cv2.resize(soft, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        return self._robust_read(big, 2.0)

    def _rectify_pass(self, image: np.ndarray) -> list[Detection]:
        return [
            det
            for det in (self._rectify_and_decode(image, q) for q in self._locate(image))
            if det is not None
        ]

    def scan_exhaustive(self, image: np.ndarray) -> list[Detection]:
        """Everything above, plus overlapping upscaled tiles.

        Seconds rather than milliseconds, so this is opt-in: it is for
        squeezing a result out of a hard still image, not for a hotkey press.
        """
        found = self.scan(image)
        h, w = image.shape[:2]
        groups = [found]
        for x0, y0, x1, y1 in _tile_rects(w, h):
            tile = image[y0:y1, x0:x1]
            big = cv2.resize(
                tile, None, fx=TILE_SCALE, fy=TILE_SCALE,
                interpolation=cv2.INTER_LANCZOS4,
            )
            # Both passes stay in the enlarged tile's coordinates, so the
            # scale-back happens exactly once, below. Dividing inside
            # _detect_both_polarities as well would halve them twice and
            # scatter phantom copies across the frame.
            hits = self._detect_both_polarities(big) + self._rectify_pass(big)
            scaled = [replace(d, quad=d.quad / TILE_SCALE).offset(x0, y0) for d in hits]
            groups.append(self._validated(image, scaled))
        return _merge(groups)


def payload_kind(text: str) -> str:
    """Classify a payload so the UI can offer the right action."""
    lowered = text.strip().lower()
    if lowered.startswith(("http://", "https://")):
        return "url"
    if lowered.startswith("wifi:"):
        return "wifi"
    if lowered.startswith("mailto:"):
        return "email"
    if lowered.startswith(("tel:", "sms:", "smsto:")):
        return "phone"
    if lowered.startswith("geo:"):
        return "geo"
    if lowered.startswith(("begin:vcard", "mecard:")):
        return "contact"
    if lowered.startswith("begin:vevent"):
        return "event"
    if lowered.startswith(("bitcoin:", "ethereum:", "otpauth:")):
        return "secret"
    if "://" in lowered:
        return "uri"
    return "text"
