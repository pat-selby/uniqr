"""A screen that changes size while UniQR runs is captured at its new size.

mss looks the monitors up once and keeps the answer. On a tester's Mac VM the
screen grew after UniQR started, and every scan still photographed only the old
top-left corner. A stand-in for mss here reports whatever size the test sets.
"""

import sys
import types

import pytest
from uniqr.backends import portable

SCREEN = {"width": 1204, "height": 928}


class FakeMSS:
    made = 0
    closed = 0

    def __init__(self):
        FakeMSS.made += 1
        # Like mss: the monitor list is fixed when this object first sees it.
        whole = {"left": 0, "top": 0, **SCREEN}
        self.monitors = [whole, dict(whole)]

    def close(self):
        FakeMSS.closed += 1


@pytest.fixture(autouse=True)
def fake_mss(monkeypatch):
    monkeypatch.setitem(sys.modules, "mss", types.SimpleNamespace(mss=FakeMSS))
    monkeypatch.setattr(portable, "_local", types.SimpleNamespace())
    monkeypatch.setitem(SCREEN, "width", 1204)
    FakeMSS.made = FakeMSS.closed = 0


def test_a_screen_made_bigger_is_seen_at_the_next_scan():
    assert portable.virtual_screen().width == 1204
    SCREEN["width"] = 1858
    assert portable.virtual_screen().width == 1858


def test_the_old_handle_is_closed_when_replaced():
    portable.virtual_screen()
    portable.virtual_screen()
    assert FakeMSS.made == 2
    assert FakeMSS.closed == 1


def test_lookups_between_scans_reuse_the_same_handle():
    portable.virtual_screen()
    portable.monitor_at(10, 10)
    portable.monitor_at(500, 500)
    assert FakeMSS.made == 1
