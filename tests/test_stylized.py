"""Regression: stylised and colour-on-colour marketing codes."""

import pytest
from tests.helpers.qr_synth import STYLIZED_CASES, STYLIZED_TEXT


@pytest.mark.parametrize("case_name,image", list(STYLIZED_CASES.items()))
def test_stylized(scanner, case_name: str, image):
    found = scanner.scan(image)
    assert any(d.text == STYLIZED_TEXT for d in found), case_name
