"""Regression: real photographs that once failed detection."""

from pathlib import Path

import cv2
import pytest
from tests.helpers.qr_synth import REAL_PHOTO_EXPECTED

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("filename,expected", list(REAL_PHOTO_EXPECTED.items()))
def test_real_photo(scanner, filename: str, expected: set[str]):
    path = ROOT / filename
    if not path.exists():
        pytest.skip(f"{filename} not in workspace")
    image = cv2.imread(str(path))
    assert image is not None, f"could not read {filename}"
    found = {d.text for d in scanner.scan(image)}
    missing = expected - found
    assert not missing, f"{filename} missing: {missing}"
