import json
from datetime import date

import pytest
import requests

import fetch


# --- Dates -----------------------------------------------------------------

def test_last_complete_week_on_a_monday():
    # Spec example: a run on Mon Oct 12 2026 uses the week Oct 5-11 (ISO 2026-W41)
    monday, sunday = fetch.last_complete_week(date(2026, 10, 12))
    assert (monday, sunday) == (date(2026, 10, 5), date(2026, 10, 11))
    assert monday.isocalendar()[:2] == (2026, 41)


def test_last_complete_week_midweek_drops_the_unfinished_week():
    assert fetch.last_complete_week(date(2026, 10, 7)) == (date(2026, 9, 28), date(2026, 10, 4))


def test_fetch_window_is_52_full_weeks_through_yesterday():
    start, end = fetch.fetch_window(date(2026, 10, 12))
    assert start == date(2025, 10, 13)  # a Monday
    assert start.weekday() == 0
    assert end == date(2026, 10, 11)
    assert (end - start).days + 1 == 52 * 7


def test_fetch_window_never_starts_before_the_dataset():
    start, _ = fetch.fetch_window(date(2025, 3, 1))
    assert start == date(2025, 1, 1)


def test_date_chunks_one_piece_when_short():
    assert fetch.date_chunks(date(2026, 1, 1), date(2026, 1, 10)) == [
        (date(2026, 1, 1), date(2026, 1, 10))]


def test_date_chunks_split_long_windows():
    chunks = fetch.date_chunks(date(2025, 1, 1), date(2026, 1, 5))  # 370 days
    assert chunks == [(date(2025, 1, 1), date(2026, 1, 1)),
                      (date(2026, 1, 2), date(2026, 1, 5))]
    assert all((e - s).days + 1 <= 366 for s, e in chunks)


# --- Retries ---------------------------------------------------------------

class FakeResponse:
    def __init__(self, status, text="{}"):
        self.status_code = status
        self.text = text

    def json(self):
        return json.loads(self.text)


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda seconds: None)


def test_get_retries_429_then_succeeds():
    session = FakeSession([FakeResponse(429), FakeResponse(500),
                           requests.ConnectionError("down"), FakeResponse(200)])
    assert fetch.get(session, "/models").status_code == 200
    assert session.calls == 4


def test_get_gives_up_after_three_retries():
    session = FakeSession([FakeResponse(429)] * 4)
    with pytest.raises(fetch.FetchError, match="after 3 retries"):
        fetch.get(session, "/models")
    assert session.calls == 4


def test_get_bad_key_stops_at_once():
    session = FakeSession([FakeResponse(401)])
    with pytest.raises(fetch.FetchError, match="API key"):
        fetch.get(session, "/models")
    assert session.calls == 1


# --- Whole fetch, with a fake API --------------------------------------------

def test_fetch_all_saves_every_file(tmp_path):
    rankings = ('{"data": [{"date": "2026-10-05", "model_permaslug": "a/b", "total_tokens": "5"}],'
                ' "meta": {"as_of": "2026-10-12T02:00:00.000Z"}}')
    session = FakeSession([FakeResponse(200, rankings), FakeResponse(200, '{"data": []}'),
                           FakeResponse(200, '{"data": {}}'), FakeResponse(200, '{"data": []}')])
    summary = fetch.fetch_all("key", date(2026, 10, 12), raw_dir=tmp_path, session=session)

    folder = tmp_path / "2026-10-12"
    assert sorted(p.name for p in folder.iterdir()) == [
        "app_rankings.json", "models.json", "rankings_daily_01.json", "task_classifications.json"]
    assert (folder / "rankings_daily_01.json").read_text() == rankings  # saved exactly as received
    assert summary["rows"] == 1
    assert summary["as_of"] == "2026-10-12T02:00:00.000Z"
    assert session.headers["Authorization"] == "Bearer key"
