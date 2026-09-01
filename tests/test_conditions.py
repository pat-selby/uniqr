"""Regression: synthetic screen conditions that once broke detection."""

import pytest
from tests.helpers.qr_synth import CONDITION_CASES, CONDITIONS_TEXT


@pytest.mark.parametrize("case_name", list(CONDITION_CASES.keys()))
def test_condition(scanner, case_name: str):
    img = CONDITION_CASES[case_name]()
    found = scanner.scan(img)
    assert any(d.text == CONDITIONS_TEXT for d in found), case_name
