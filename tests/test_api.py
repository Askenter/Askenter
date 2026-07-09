import json

import pytest

import update_profile
from update_profile import (
    ApiError,
    StatsPending,
    cache_key,
    fetch_loc,
    gql,
    repo_loc,
)


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {"x-ratelimit-remaining": "100"}
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


CONTRIBUTORS = [
    {"author": {"login": "Someone"}, "weeks": [{"a": 1, "d": 1}]},
    {"author": {"login": "Askenter"}, "weeks": [{"a": 10, "d": 3}, {"a": 5, "d": 1}]},
]


def test_gql_raises_on_graphql_errors(monkeypatch):
    monkeypatch.setattr(
        update_profile.requests,
        "post",
        lambda *a, **k: FakeResponse(200, {"errors": [{"message": "boom"}]}),
    )
    with pytest.raises(ApiError):
        gql("query {}", {}, "tok")


def test_repo_loc_retries_202_then_succeeds(monkeypatch):
    responses = [FakeResponse(202), FakeResponse(202), FakeResponse(200, CONTRIBUTORS)]
    sleeps = []
    monkeypatch.setattr(update_profile.requests, "get", lambda *a, **k: responses.pop(0))
    assert repo_loc("tok", "Askenter/x", "Askenter", sleep=sleeps.append) == (15, 4)
    assert sleeps == [1, 2]


def test_repo_loc_gives_up_after_five_202s(monkeypatch):
    monkeypatch.setattr(update_profile.requests, "get", lambda *a, **k: FakeResponse(202))
    with pytest.raises(StatsPending):
        repo_loc("tok", "Askenter/x", "Askenter", sleep=lambda s: None)


def test_repo_loc_rate_limit_exhausted_raises(monkeypatch):
    monkeypatch.setattr(
        update_profile.requests,
        "get",
        lambda *a, **k: FakeResponse(200, CONTRIBUTORS, {"x-ratelimit-remaining": "0"}),
    )
    with pytest.raises(ApiError):
        repo_loc("tok", "Askenter/x", "Askenter")


def test_fetch_loc_uses_cache_when_pushed_at_matches(monkeypatch):
    repo = {"nameWithOwner": "Askenter/x", "pushedAt": "2026-01-01T00:00:00Z"}
    cache = {cache_key("Askenter/x"): {"pushed_at": "2026-01-01T00:00:00Z", "add": 7, "del": 2}}

    def explode(*a, **k):
        raise AssertionError("must not refetch cached repo")

    monkeypatch.setattr(update_profile, "repo_loc", explode)
    adds, dels, new_cache = fetch_loc("tok", [repo], cache, "Askenter")
    assert (adds, dels) == (7, 2)
    assert new_cache == cache


def test_fetch_loc_falls_back_to_stale_cache_on_pending(monkeypatch):
    repo = {"nameWithOwner": "Askenter/x", "pushedAt": "2026-02-02T00:00:00Z"}
    cache = {cache_key("Askenter/x"): {"pushed_at": "2026-01-01T00:00:00Z", "add": 7, "del": 2}}

    def pending(*a, **k):
        raise StatsPending("Askenter/x")

    monkeypatch.setattr(update_profile, "repo_loc", pending)
    adds, dels, _ = fetch_loc("tok", [repo], cache, "Askenter")
    assert (adds, dels) == (7, 2)


def test_fetch_loc_pending_without_cache_raises(monkeypatch):
    repo = {"nameWithOwner": "Askenter/x", "pushedAt": "2026-02-02T00:00:00Z"}

    def pending(*a, **k):
        raise StatsPending("Askenter/x")

    monkeypatch.setattr(update_profile, "repo_loc", pending)
    with pytest.raises(StatsPending):
        fetch_loc("tok", [repo], {}, "Askenter")
