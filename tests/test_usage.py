"""Anonymous usage counts: off unless asked for, counts only, never scanned text.

Nothing here touches the internet. A stand-in answers where Aptabase would.
"""

import json
import sys
import threading
import time
import types

import app
import pytest
from uniqr import settings, usage

KEY = "A-EU-1234567890"
SECRET = "https://bank.example/reset?token=hunter2"


@pytest.fixture(autouse=True)
def own_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("UNIQR_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.delenv(usage.KEY_ENV, raising=False)
    monkeypatch.setattr(usage, "APP_KEY", "")


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv(usage.KEY_ENV, KEY)


@pytest.fixture
def on(key):
    assert usage.set_enabled(True)


def counts():
    return json.loads(usage.tally_path().read_text())["counts"]


class FakeReply:
    def __init__(self, url, status=200):
        self.url, self.status = url, status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def geturl(self):
        return self.url


# -- switched off unless there is a key and a yes -------------------------------------


@pytest.mark.parametrize("bad", ["", "A-EU-", "A-XX-1234567890", "B-EU-1234567890", "A-EU-12ab"])
def test_a_missing_or_malformed_key_switches_everything_off(monkeypatch, bad):
    monkeypatch.setenv(usage.KEY_ENV, bad)
    assert not usage.configured()
    settings.set("usage_stats", True)
    assert not usage.enabled()


def test_the_key_picks_the_region(monkeypatch):
    monkeypatch.setenv(usage.KEY_ENV, "A-US-9876543210")
    assert usage.endpoint() == "https://us.aptabase.com/api/v0/events"
    monkeypatch.setenv(usage.KEY_ENV, KEY)
    assert usage.endpoint() == "https://eu.aptabase.com/api/v0/events"


def test_nothing_is_counted_before_a_yes(key):
    usage.record_start()
    usage.record_scan(0.3, ["QR Code"], links=1)
    assert not usage.tally_path().exists()
    assert usage.due() == []


# -- counting ------------------------------------------------------------------------


def test_a_scan_is_counted_by_outcome_time_and_kind(on):
    usage.record_scan(0.4, [], links=0)
    usage.record_scan(1.5, ["QR Code"], links=1)
    usage.record_scan(6.0, ["QR Code", "Data Matrix", "Something New"], links=1)
    c = counts()
    assert c["scans"] == 3
    assert (c["found_none"], c["found_one"], c["found_many"]) == (1, 1, 1)
    assert (c["time_under_1s"], c["time_1_to_2s"], c["time_over_5s"]) == (1, 1, 1)
    assert c["kind_qr"] == 2 and c["kind_data_matrix"] == 1 and c["kind_other"] == 1
    assert (c["payload_link"], c["payload_other"]) == (2, 2)


def test_scanned_text_cannot_reach_the_counts_or_the_request(on):
    # The app hands over kinds, a time and a number. Even if text slipped into
    # a kind's name or into the file, it must not come out the other end.
    usage.record_scan(0.2, [SECRET], links=1)
    data = json.loads(usage.tally_path().read_text())
    data["counts"][SECRET] = 5
    data["counts"]["scans"] = SECRET
    usage.tally_path().write_text(json.dumps(data))
    usage.record_start()
    event = usage.summary_event(json.loads(usage.tally_path().read_text())["counts"], "0.2.2")
    sent = json.dumps(event)
    assert SECRET not in sent and "hunter2" not in sent
    assert set(event["props"]) <= set(usage.COUNTS)
    assert all(isinstance(v, int) for v in event["props"].values())


def test_nothing_about_the_person_is_in_the_system_details(key):
    props = usage.summary_event({"scans": 1}, "0.2.2")["systemProps"]
    assert props["locale"] == "" and props["deviceModel"] == ""
    assert props["appVersion"] == "0.2.2"


def test_each_send_gets_a_fresh_session_so_days_cannot_be_joined(key):
    ids = {usage.summary_event({"scans": 1}, "0.2.2")["sessionId"] for _ in range(20)}
    assert len(ids) == 20


def test_a_finished_day_waits_to_be_sent_and_today_starts_empty(on, monkeypatch):
    monkeypatch.setattr(usage, "_today", lambda: "2026-10-17")
    usage.record_scan(0.2, ["QR Code"], links=1)
    assert usage.due() == []  # the day is not over
    monkeypatch.setattr(usage, "_today", lambda: "2026-10-18")
    waiting = usage.due()
    assert [p["day"] for p in waiting] == ["2026-10-17"]
    assert waiting[0]["counts"]["scans"] == 1
    assert counts() == {}


def test_a_week_offline_keeps_only_the_last_seven_days(on, monkeypatch):
    for day in range(1, 11):
        monkeypatch.setattr(usage, "_today", lambda d=day: f"2026-10-{d:02d}")
        usage.record_start()
    monkeypatch.setattr(usage, "_today", lambda: "2026-10-11")
    days = [p["day"] for p in usage.due()]
    assert days == [f"2026-10-{d:02d}" for d in range(4, 11)]


def test_a_sent_day_is_not_sent_again(on, monkeypatch):
    monkeypatch.setattr(usage, "_today", lambda: "2026-10-17")
    usage.record_start()
    monkeypatch.setattr(usage, "_today", lambda: "2026-10-18")
    usage.mark_sent([p["day"] for p in usage.due()])
    assert usage.due() == []


def test_turning_it_off_deletes_what_was_counted(on):
    usage.record_start()
    assert usage.tally_path().exists()
    usage.set_enabled(False)
    assert not usage.tally_path().exists()
    usage.record_start()
    assert not usage.tally_path().exists()


def test_a_damaged_file_reads_as_empty(on):
    usage.tally_path().parent.mkdir(parents=True, exist_ok=True)
    usage.tally_path().write_text("{not json")
    usage.record_start()
    assert counts() == {"starts": 1}


# -- sending -------------------------------------------------------------------------


def test_the_request_is_what_aptabase_expects(on):
    seen = {}

    def opener(request, timeout):
        seen.update(url=request.full_url, method=request.get_method(), timeout=timeout,
                    headers=dict(request.header_items()), body=json.loads(request.data))
        return FakeReply("https://eu.aptabase.com/api/v0/events")

    days = usage.send([{"day": "2026-10-17", "counts": {"scans": 4}}], "0.2.2", opener)
    assert days == ["2026-10-17"]
    assert seen["url"] == "https://eu.aptabase.com/api/v0/events" and seen["method"] == "POST"
    assert seen["headers"]["App-key"] == KEY
    assert seen["headers"]["Content-type"] == "application/json"
    [event] = seen["body"]
    assert event["eventName"] == "daily_summary" and event["props"] == {"scans": 4}
    assert event["timestamp"].endswith("Z")


@pytest.mark.parametrize(
    "reply",
    [
        lambda r, timeout: (_ for _ in ()).throw(OSError("offline")),
        lambda r, timeout: FakeReply("https://elsewhere.example/api/v0/events"),
        lambda r, timeout: FakeReply("https://eu.aptabase.com/api/v0/events", status=429),
    ],
    ids=["offline", "redirected elsewhere", "refused"],
)
def test_a_failed_send_keeps_the_days_for_later(on, reply):
    assert usage.send([{"day": "2026-10-17", "counts": {"scans": 1}}], "0.2.2", reply) == []


def test_nothing_is_sent_without_a_key():
    def opener(request, timeout):
        raise AssertionError("must not be called")

    assert usage.send([{"day": "2026-10-17", "counts": {"scans": 1}}], "0.2.2", opener) == []


def test_the_app_sends_waiting_days_on_a_thread_then_marks_them(on, monkeypatch):
    monkeypatch.setattr(usage, "_today", lambda: "2026-10-17")
    usage.record_start()
    monkeypatch.setattr(usage, "_today", lambda: "2026-10-18")
    sent = threading.Event()

    def fake_send(waiting, version):
        sent.set()
        return [p["day"] for p in waiting]

    monkeypatch.setattr(usage, "send", fake_send)
    fake = types.SimpleNamespace(
        _usage_sent=None, _usage_enabled=True, _usage_next=0.0, _usage_thread=None
    )
    app.UniQR._usage_tick(fake)
    assert sent.wait(5)
    fake._usage_thread.join(5)
    assert fake._usage_next > time.time() + 60  # the next try waits, even after a success
    app.UniQR._usage_tick(fake)  # the next tick records what went
    assert usage.due() == []


# -- asking --------------------------------------------------------------------------


@pytest.fixture
def frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)


def test_it_asks_only_the_packaged_program_with_a_key(key, frozen):
    assert usage.should_ask()
    assert not usage.should_ask(quiet=True)
    assert not usage.should_ask(restarted=True)


def test_it_never_asks_without_a_key(frozen):
    assert not usage.should_ask()


def test_it_never_asks_from_source(key, monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert not usage.should_ask()


@pytest.mark.parametrize("answer", [True, False])
def test_an_answer_is_final(key, frozen, answer):
    usage.record_answer(answer)
    assert not usage.should_ask()


def test_ignoring_it_three_times_ends_it(key, frozen):
    for _ in range(3):
        assert usage.should_ask()
        usage.record_answer(None)
    assert not usage.should_ask()


def test_quitting_while_it_is_up_is_not_an_answer(key, frozen):
    usage.record_answer(None, stopping=True)
    assert settings.get("usage_ignored") is None


def test_show_usage_prints_the_exact_request(on):
    text = usage.describe("0.2.2")
    assert "https://eu.aptabase.com/api/v0/events" in text
    assert '"eventName": "daily_summary"' in text
