"""Checking for a newer UniQR: reading versions, reading GitHub's reply, and the rules
about when to ask and when to check.

Nothing here touches the internet. A stand-in answers where GitHub would.
"""

import json
import sys

import pytest
from uniqr import settings, updates

LATEST = "https://api.github.com/repos/pat-selby/uniqr/releases/latest"


@pytest.fixture(autouse=True)
def own_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("UNIQR_CONFIG_DIR", str(tmp_path / "config"))


class FakeReply:
    """What urlopen hands back, as far as UniQR uses it."""

    def __init__(self, body, url=LATEST):
        self.body = body if isinstance(body, bytes) else body.encode()
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]

    def geturl(self):
        return self.url


def opener_returning(reply, seen=None):
    def opener(request, timeout=None):
        if seen is not None:
            seen.append((request, timeout))
        return reply

    return opener


def release_json(tag="v0.1.8", **extra):
    return json.dumps({"tag_name": tag, **extra})


# -- versions -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "parts"),
    [("0.1.8", (0, 1, 8)), ("v0.1.8", (0, 1, 8)), ("V1.2", (1, 2)), (" 2.0.0.1 ", (2, 0, 0, 1)), ("7", (7,))],
)
def test_versions_are_read(text, parts):
    assert updates.parse_version(text) == parts


@pytest.mark.parametrize(
    "text", ["", "latest", "0.1.8-rc1", "0.1.x", "1.2.3.4.5", "v", "0..1", "０.１", "0.1.8; rm -rf /"]
)
def test_what_is_not_a_plain_version_is_refused(text):
    assert updates.parse_version(text) is None


@pytest.mark.parametrize(
    ("latest", "current", "newer"),
    [
        ("0.1.8", "0.1.7", True),
        ("0.1.7", "0.1.7", False),
        ("0.1.6", "0.1.7", False),
        ("0.2.0", "0.1.9", True),
        ("0.10.0", "0.9.0", True),  # numbers, not text: 10 is more than 9
        ("1.0", "0.9.9", True),
        ("0.2.0", "0.2", False),  # the same version written two ways
        ("0.2", "0.2.0", False),
        ("v0.1.8", "0.1.7", True),
    ],
)
def test_which_version_is_newer(latest, current, newer):
    assert updates.is_newer(latest, current) is newer


def test_an_unreadable_version_is_never_called_newer():
    assert updates.is_newer("banana", "0.1.7") is False
    assert updates.is_newer("0.1.8", "banana") is False


# -- reading GitHub's reply -----------------------------------------------------


def test_the_newest_release_is_read_from_the_reply():
    release = updates.parse_release(release_json("v0.1.8"))
    assert release.version == "0.1.8"
    assert release.url == "https://github.com/pat-selby/uniqr/releases/tag/v0.1.8"


def test_the_page_offered_is_built_here_and_never_taken_from_the_reply():
    """The reply is untrusted. A link in it must not become a link we offer."""
    hostile = release_json("v0.1.8", html_url="https://evil.example/uniqr", url="file:///etc/passwd")
    release = updates.parse_release(hostile)
    assert release.url.startswith("https://github.com/pat-selby/uniqr/")
    assert "evil" not in release.url


@pytest.mark.parametrize(
    "body",
    [
        "",
        "not json",
        "[]",
        "null",
        "42",
        "{}",
        '{"tag_name": null}',
        '{"tag_name": 8}',
        '{"tag_name": "latest"}',
        '{"tag_name": "v0.2.0-rc1"}',
        '{"tag_name": "v0.1.8/../../x"}',
        b"\xff\xfe\x00",
    ],
)
def test_a_reply_that_makes_no_sense_is_refused(body):
    with pytest.raises(updates.UpdateError):
        updates.parse_release(body)


# -- asking GitHub --------------------------------------------------------------


def test_the_request_names_uniqr_and_has_a_time_limit():
    seen = []
    updates.fetch_latest("0.1.7", opener=opener_returning(FakeReply(release_json()), seen))
    request, timeout = seen[0]
    assert request.full_url == updates.API_URL
    assert request.get_header("User-agent") == "UniQR/0.1.7"
    assert timeout == updates.TIMEOUT_S


def test_the_request_goes_over_https_to_github():
    assert updates.API_URL.startswith("https://api.github.com/")


def test_nothing_about_the_computer_is_in_the_request():
    seen = []
    updates.fetch_latest("0.1.7", opener=opener_returning(FakeReply(release_json()), seen))
    request, _ = seen[0]
    sent = {k.lower(): v for k, v in request.header_items()}
    assert set(sent) == {"accept", "user-agent"}
    assert request.data is None  # a plain GET, no body


def test_a_reply_from_another_site_is_refused():
    reply = FakeReply(release_json(), url="https://evil.example/releases/latest")
    with pytest.raises(updates.UpdateError, match="unexpected"):
        updates.fetch_latest(opener=opener_returning(reply))


def test_an_enormous_reply_is_refused():
    reply = FakeReply(b"x" * (updates.MAX_BYTES + 5))
    with pytest.raises(updates.UpdateError, match="larger"):
        updates.fetch_latest(opener=opener_returning(reply))


@pytest.mark.parametrize("problem", [OSError("no route"), TimeoutError(), ConnectionResetError(), ValueError("x")])
def test_being_offline_is_an_error_with_a_plain_message(problem):
    def opener(request, timeout=None):
        raise problem

    with pytest.raises(updates.UpdateError, match="Could not reach GitHub"):
        updates.fetch_latest(opener=opener)


# -- the whole check ------------------------------------------------------------


def stub(release=None, error=None):
    def fetch(current):
        if error:
            raise error
        return release

    return fetch


def rel(version):
    return updates.Release(version=version, url=updates.RELEASE_PAGE + version)


def test_a_newer_release_is_reported():
    outcome = updates.check("0.1.7", stub(rel("0.1.8")))
    assert outcome.status == "newer"
    assert outcome.release.version == "0.1.8"


def test_the_same_version_is_up_to_date():
    assert updates.check("0.1.7", stub(rel("0.1.7"))).status == "current"


def test_being_ahead_of_the_newest_release_is_up_to_date():
    """A copy built from the source can be ahead of the last release."""
    assert updates.check("0.2.0", stub(rel("0.1.7"))).status == "current"


def test_a_failed_check_never_raises_and_says_why():
    outcome = updates.check("0.1.7", stub(error=updates.UpdateError("Could not reach GitHub.")))
    assert outcome.status == "error"
    assert "Could not reach" in outcome.detail


def test_a_surprise_inside_the_check_is_still_an_error_not_a_crash():
    outcome = updates.check("0.1.7", stub(error=RuntimeError("boom")))
    assert outcome.status == "error"
    assert "RuntimeError" in outcome.detail


# -- when to ask ----------------------------------------------------------------


@pytest.fixture
def packaged(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(updates, "supported", lambda: True)


def test_the_packaged_program_asks_the_first_time(packaged):
    assert updates.should_ask() is True


def test_running_from_source_never_asks(packaged, monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert updates.should_ask() is False


def test_a_mac_is_never_asked(packaged, monkeypatch):
    monkeypatch.setattr(updates, "supported", lambda: False)
    assert updates.should_ask() is False


def test_it_does_not_ask_on_a_quiet_start_or_a_watchdog_restart(packaged):
    assert updates.should_ask(quiet=True) is False
    assert updates.should_ask(restarted=True) is False


def test_an_answer_is_final(packaged):
    updates.record_answer(False)
    assert updates.should_ask() is False


def test_a_yes_is_final_too(packaged):
    updates.record_answer(True)
    assert updates.should_ask() is False


def test_it_does_not_ask_when_checking_is_already_on(packaged):
    updates.set_enabled(True)
    assert updates.should_ask() is False


def test_ignoring_it_three_times_ends_the_asking(packaged):
    for _ in range(updates.MAX_IGNORED - 1):
        updates.record_answer(None)
        assert updates.should_ask() is True
    updates.record_answer(None)
    assert updates.should_ask() is False


def test_a_card_closed_because_uniqr_was_quitting_is_not_an_ignored_question(packaged):
    for _ in range(10):
        updates.record_answer(None, stopping=True)
    assert updates.should_ask() is True


# -- what is remembered ---------------------------------------------------------


def test_nothing_is_checked_until_someone_says_yes():
    assert updates.enabled() is False


def test_the_switch_round_trips():
    updates.set_enabled(True)
    assert updates.enabled() is True
    updates.set_enabled(False)
    assert updates.enabled() is False


def test_the_next_check_is_a_day_after_the_last():
    updates.record_check(1_000_000.0)
    assert updates.next_check_at() == 1_000_000.0 + 24 * 60 * 60


def test_with_no_check_yet_one_is_due_now():
    assert updates.next_check_at() < 10 * 24 * 60 * 60  # the start of 1970, plus a day


def test_a_version_is_announced_once():
    assert updates.already_told("0.1.8") is False
    updates.record_told("0.1.8")
    assert updates.already_told("0.1.8") is True
    assert updates.already_told("0.1.9") is False


def test_a_damaged_settings_file_means_nothing_is_on_and_nothing_is_told():
    settings.path().parent.mkdir(parents=True)
    settings.path().write_text("{not json", encoding="utf-8")
    assert updates.enabled() is False
    assert updates.already_told("0.1.8") is False
