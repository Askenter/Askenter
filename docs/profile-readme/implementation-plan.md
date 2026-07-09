# Profile README (neofetch style) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Askenter/Askenter profile README with a colored ASCII portrait plus a neofetch style stats panel rendered as SVG and refreshed daily by a GitHub Action.

**Architecture:** Two hand authored SVGs (dark and light palette, shared geometry) are embedded in the README through a `<picture>` element. A Python script queries the GitHub GraphQL and REST APIs and rewrites `<tspan>` values by id inside both SVGs. A scheduled workflow runs the script daily and commits only when values changed. A separate one time script converts the pixel avatar into the colored ASCII portrait fragment.

**Tech Stack:** Python 3.12, requests, python-dateutil, pytest, Pillow (portrait script only), GitHub Actions, GitHub GraphQL + REST APIs.

**Spec:** `docs/profile-readme/design.md` (approved 2026-07-09). The spec's decisions bind this plan.

## Global Constraints

- Runtime dependencies of `update_profile.py` are exactly `requests` and `python-dateutil`. Pillow is dev only (portrait script).
- LOC cache keys MUST be SHA256 hashes of `nameWithOwner`, never the plain name (public repo, private names must not leak).
- No file is written until every API call has succeeded. Any API failure exits nonzero with the SVGs untouched.
- Private repo data appears only as aggregate numbers. No repo names in SVGs, README, cache, or logs.
- Birthday is `2002-04-17`, injected via `BIRTHDAY` env var. Panel username is `askenter`, GitHub login is `Askenter`.
- The panel text content is fixed by the approved mockup in the spec. Do not reword fields.
- Repo root is the working directory for all commands: `~/Documents/GitHub/Askenter`.
- Commit messages are plain imperative sentences without prefixes, matching the repo's existing history.

---

### Task 1: Scaffolding and age string

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `update_profile.py`, `tests/test_age.py`

**Interfaces:**
- Produces: `age_string(birthday: date, today: date) -> str` in `update_profile.py`, e.g. `"24 years, 2 months, 22 days"`, singular units when a component is 1.

- [ ] **Step 1: Write scaffolding files**

`requirements.txt`:
```text
requests==2.32.*
python-dateutil==2.9.*
```

`requirements-dev.txt`:
```text
-r requirements.txt
pytest==8.*
Pillow==11.*
```

`pytest.ini`:
```ini
[pytest]
pythonpath = .
testpaths = tests
```

Then run: `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt` and add `.venv/` to a new `.gitignore` line. Use `.venv/bin/python` and `.venv/bin/pytest` for every later step.

- [ ] **Step 2: Write the failing test**

`tests/test_age.py`:
```python
from datetime import date

from update_profile import age_string


def test_age_on_2026_07_09():
    assert age_string(date(2002, 4, 17), date(2026, 7, 9)) == "24 years, 2 months, 22 days"


def test_age_on_birthday_is_zero_months_days():
    assert age_string(date(2002, 4, 17), date(2026, 4, 17)) == "24 years, 0 months, 0 days"


def test_singular_units():
    assert age_string(date(2002, 4, 17), date(2003, 5, 18)) == "1 year, 1 month, 1 day"


def test_leap_day_birthday_rolls_over_correctly():
    assert age_string(date(2000, 2, 29), date(2026, 3, 1)) == "26 years, 0 months, 1 day"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_age.py -v`
Expected: FAIL with `ImportError` (no `update_profile` module / no `age_string`).

- [ ] **Step 4: Write minimal implementation**

`update_profile.py`:
```python
"""Daily profile updater. Rewrites stats inside dark_mode.svg and light_mode.svg."""
from datetime import date

from dateutil.relativedelta import relativedelta


def age_string(birthday: date, today: date) -> str:
    delta = relativedelta(today, birthday)
    parts = []
    for amount, unit in ((delta.years, "year"), (delta.months, "month"), (delta.days, "day")):
        suffix = "" if amount == 1 else "s"
        parts.append(f"{amount} {unit}{suffix}")
    return ", ".join(parts)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_age.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt requirements-dev.txt pytest.ini .gitignore update_profile.py tests/test_age.py
git commit -m "Add updater scaffolding and age string computation"
```

---

### Task 2: Dot leaders

**Files:**
- Modify: `update_profile.py`
- Test: `tests/test_leaders.py`

**Interfaces:**
- Produces: `ROW_WIDTH = 58` and `dots_for(label: str, value: str, row_width: int = ROW_WIDTH) -> str`. Returns only the dots. Row invariant: `len(label) + len(dots) + 1 + len(value) == row_width` (the 1 is the space between dots and value). Minimum 3 dots even for oversized values.

- [ ] **Step 1: Write the failing test**

`tests/test_leaders.py`:
```python
from update_profile import ROW_WIDTH, dots_for


def test_row_width_invariant():
    label = ". Uptime: "
    value = "24 years, 2 months, 22 days"
    dots = dots_for(label, value)
    assert len(label) + len(dots) + 1 + len(value) == ROW_WIDTH


def test_minimum_three_dots_for_oversized_value():
    dots = dots_for(". Uptime: ", "x" * 100)
    assert dots == "..."


def test_custom_row_width():
    assert dots_for("ab", "cd", row_width=10) == "....."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_leaders.py -v`
Expected: FAIL with `ImportError: cannot import name 'ROW_WIDTH'`.

- [ ] **Step 3: Write minimal implementation**

Add to `update_profile.py`:
```python
ROW_WIDTH = 58


def dots_for(label: str, value: str, row_width: int = ROW_WIDTH) -> str:
    count = row_width - len(label) - len(value) - 1
    return "." * max(count, 3)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_leaders.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add update_profile.py tests/test_leaders.py
git commit -m "Add dot leader computation with fixed row width"
```

---

### Task 3: SVG tspan rewrite

**Files:**
- Modify: `update_profile.py`
- Test: `tests/test_svg_rewrite.py`

**Interfaces:**
- Produces: `update_svg(svg_text: str, replacements: dict[str, str]) -> str`. Replaces the text content of each `<tspan ... id="KEY" ...>` with the XML escaped value. Raises `KeyError` when an id is missing. Leaves all other markup byte identical.

- [ ] **Step 1: Write the failing test**

`tests/test_svg_rewrite.py`:
```python
import pytest

from update_profile import update_svg

FIXTURE = (
    '<svg><text>. Uptime: '
    '<tspan class="d" id="age_dots">...</tspan> '
    '<tspan class="v" id="age_data">old</tspan></text></svg>'
)


def test_replaces_tspan_content_by_id():
    out = update_svg(FIXTURE, {"age_data": "24 years", "age_dots": "....."})
    assert '<tspan class="v" id="age_data">24 years</tspan>' in out
    assert '<tspan class="d" id="age_dots">.....</tspan>' in out


def test_escapes_xml_special_characters():
    out = update_svg(FIXTURE, {"age_data": "a<b&c"})
    assert ">a&lt;b&amp;c</tspan>" in out


def test_missing_id_raises_keyerror():
    with pytest.raises(KeyError):
        update_svg(FIXTURE, {"nope": "x"})


def test_untouched_markup_is_identical():
    out = update_svg(FIXTURE, {"age_data": "new"})
    assert out.replace(">new</tspan>", ">old</tspan>") == FIXTURE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_svg_rewrite.py -v`
Expected: FAIL with `ImportError: cannot import name 'update_svg'`.

- [ ] **Step 3: Write minimal implementation**

Add to `update_profile.py` (imports go at the top of the file):
```python
import re
from xml.sax.saxutils import escape


def update_svg(svg_text: str, replacements: dict[str, str]) -> str:
    for tspan_id, value in replacements.items():
        pattern = re.compile(
            rf'(<tspan[^>]*\bid="{re.escape(tspan_id)}"[^>]*>)[^<]*(</tspan>)'
        )
        escaped = escape(value)
        svg_text, count = pattern.subn(
            lambda m, e=escaped: m.group(1) + e + m.group(2), svg_text
        )
        if count == 0:
            raise KeyError(f"tspan id {tspan_id!r} not found in SVG")
    return svg_text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_svg_rewrite.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add update_profile.py tests/test_svg_rewrite.py
git commit -m "Add tspan rewrite by id with escaping and missing id failure"
```

---

### Task 4: LOC cache with hashed keys

**Files:**
- Modify: `update_profile.py`
- Test: `tests/test_cache.py`

**Interfaces:**
- Produces: `CACHE_PATH = Path("cache/loc_cache.json")`, `cache_key(name_with_owner: str) -> str` (SHA256 hex), `load_cache(path: Path) -> dict`, `save_cache(path: Path, cache: dict) -> None`. Cache entries look like `{"pushed_at": "<ISO>", "add": int, "del": int}` keyed by `cache_key(...)`.

- [ ] **Step 1: Write the failing test**

`tests/test_cache.py`:
```python
import hashlib
import json

from update_profile import cache_key, load_cache, save_cache


def test_cache_key_is_sha256_of_name():
    expected = hashlib.sha256(b"Askenter/secret-repo").hexdigest()
    assert cache_key("Askenter/secret-repo") == expected


def test_cache_key_never_contains_repo_name():
    assert "secret" not in cache_key("Askenter/secret-repo")


def test_load_missing_cache_returns_empty(tmp_path):
    assert load_cache(tmp_path / "loc_cache.json") == {}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "loc_cache.json"
    cache = {cache_key("a/b"): {"pushed_at": "2026-01-01T00:00:00Z", "add": 5, "del": 2}}
    save_cache(path, cache)
    assert load_cache(path) == cache
    assert "a/b" not in path.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cache.py -v`
Expected: FAIL with `ImportError: cannot import name 'cache_key'`.

- [ ] **Step 3: Write minimal implementation**

Add to `update_profile.py` (imports at top):
```python
import hashlib
import json
from pathlib import Path

CACHE_PATH = Path("cache/loc_cache.json")


def cache_key(name_with_owner: str) -> str:
    return hashlib.sha256(name_with_owner.encode()).hexdigest()


def load_cache(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=0, sort_keys=True) + "\n")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cache.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add update_profile.py tests/test_cache.py
git commit -m "Add LOC cache with SHA256 hashed repo keys"
```

---

### Task 5: GitHub API client

**Files:**
- Modify: `update_profile.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `cache_key`, `load_cache` from Task 4.
- Produces, all in `update_profile.py`:
  - `API = "https://api.github.com"`
  - `class ApiError(RuntimeError)` and `class StatsPending(ApiError)`
  - `gql(query: str, variables: dict, token: str) -> dict` returns the `data` object, raises `ApiError` on HTTP != 200 or GraphQL errors
  - `fetch_overview(token: str) -> dict` returns the viewer object with keys `login`, `createdAt`, `followers.totalCount`, `repositoriesContributedTo.totalCount`
  - `fetch_repos(token: str) -> list[dict]` paginated nodes, each `{"nameWithOwner": str, "stargazerCount": int, "pushedAt": str}`
  - `fetch_commits_total(token: str, created_at: str, today: date) -> int`
  - `repo_loc(token: str, name_with_owner: str, login: str, sleep=time.sleep) -> tuple[int, int]` additions and deletions for that login, retries HTTP 202 five times with exponential backoff then raises `StatsPending`, treats HTTP 204 or absent login as `(0, 0)`, raises `ApiError` when the REST rate limit hits zero
  - `fetch_loc(token: str, repos: list[dict], cache: dict, login: str) -> tuple[int, int, dict]` totals plus the new cache, reusing entries whose `pushed_at` matches and falling back to stale cache on `StatsPending`

- [ ] **Step 1: Write the failing test**

`tests/test_api.py`:
```python
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


def test_repo_loc_gives_up_after_five_202s_without_final_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(update_profile.requests, "get", lambda *a, **k: FakeResponse(202))
    with pytest.raises(StatsPending) as exc_info:
        repo_loc("tok", "Askenter/x", "Askenter", sleep=sleeps.append)
    assert sleeps == [1, 2, 4, 8]
    assert "Askenter/x" not in str(exc_info.value)


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_api.py -v`
Expected: FAIL with `ImportError: cannot import name 'ApiError'`.

- [ ] **Step 3: Write the implementation**

Add to `update_profile.py` (`import os`, `import time`, `import requests` at top):
```python
API = "https://api.github.com"


class ApiError(RuntimeError):
    pass


class StatsPending(ApiError):
    pass


def gql(query: str, variables: dict, token: str) -> dict:
    response = requests.post(
        f"{API}/graphql",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"bearer {token}"},
        timeout=30,
    )
    if response.status_code != 200:
        raise ApiError(f"GraphQL HTTP {response.status_code}: {response.text[:200]}")
    body = response.json()
    if "errors" in body:
        raise ApiError(f"GraphQL errors: {body['errors']}")
    return body["data"]


OVERVIEW_QUERY = """
query {
  viewer {
    login
    createdAt
    followers { totalCount }
    repositoriesContributedTo(
      contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY, PULL_REQUEST_REVIEW]
    ) { totalCount }
  }
}
"""

REPOS_QUERY = """
query($cursor: String) {
  viewer {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER) {
      pageInfo { hasNextPage endCursor }
      nodes { nameWithOwner stargazerCount pushedAt }
    }
  }
}
"""

COMMITS_QUERY = """
query($from: DateTime!, $to: DateTime!) {
  viewer {
    contributionsCollection(from: $from, to: $to) { totalCommitContributions }
  }
}
"""


def fetch_overview(token: str) -> dict:
    return gql(OVERVIEW_QUERY, {}, token)["viewer"]


def fetch_repos(token: str) -> list[dict]:
    nodes, cursor = [], None
    while True:
        page = gql(REPOS_QUERY, {"cursor": cursor}, token)["viewer"]["repositories"]
        nodes.extend(node for node in page["nodes"] if node["pushedAt"] is not None)
        if not page["pageInfo"]["hasNextPage"]:
            return nodes
        cursor = page["pageInfo"]["endCursor"]


def fetch_commits_total(token: str, created_at: str, today: date) -> int:
    total = 0
    for year in range(int(created_at[:4]), today.year + 1):
        data = gql(
            COMMITS_QUERY,
            {"from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
            token,
        )
        total += data["viewer"]["contributionsCollection"]["totalCommitContributions"]
    return total


def repo_loc(token: str, name_with_owner: str, login: str, sleep=time.sleep) -> tuple[int, int]:
    url = f"{API}/repos/{name_with_owner}/stats/contributors"
    headers = {"Authorization": f"bearer {token}", "Accept": "application/vnd.github+json"}
    for attempt in range(5):
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            if int(response.headers.get("x-ratelimit-remaining", "1")) == 0:
                raise ApiError("REST rate limit exhausted")
            for contributor in response.json() or []:
                author = contributor.get("author")
                if author and author["login"] == login:
                    adds = sum(week["a"] for week in contributor["weeks"])
                    dels = sum(week["d"] for week in contributor["weeks"])
                    return adds, dels
            return 0, 0
        if response.status_code == 202:
            if attempt < 4:
                sleep(2 ** attempt)
            continue
        if response.status_code == 204:
            return 0, 0
        raise ApiError(f"stats HTTP {response.status_code} for a repo")
    raise StatsPending("contributor stats pending for a repo")


def fetch_loc(token: str, repos: list[dict], cache: dict, login: str) -> tuple[int, int, dict]:
    adds = dels = 0
    new_cache = {}
    for repo in repos:
        key = cache_key(repo["nameWithOwner"])
        cached = cache.get(key)
        if cached and cached["pushed_at"] == repo["pushedAt"]:
            entry = cached
        else:
            try:
                add, delete = repo_loc(token, repo["nameWithOwner"], login)
                entry = {"pushed_at": repo["pushedAt"], "add": add, "del": delete}
            except StatsPending:
                if cached is None:
                    raise
                entry = cached
        new_cache[key] = entry
        adds += entry["add"]
        dels += entry["del"]
    return adds, dels, new_cache
```

Note both error texts in `repo_loc` (the `ApiError` and the `StatsPending`) deliberately omit the repo name so private names never reach public workflow logs, and no sleep happens after the final attempt since nothing follows it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_api.py -v`
Expected: 7 passed.

- [ ] **Step 5: Run the whole suite**

Run: `.venv/bin/pytest -q`
Expected: all tests pass (15 at this point).

- [ ] **Step 6: Commit**

```bash
git add update_profile.py tests/test_api.py
git commit -m "Add GitHub GraphQL and REST client with retry, rate limit guard, and cached LOC"
```

---

### Task 6: Stats assembly, replacements, and main with dry run

**Files:**
- Modify: `update_profile.py`
- Test: `tests/test_assembly.py`

**Interfaces:**
- Consumes: everything from Tasks 1 to 5.
- Produces:
  - `@dataclass Stats` with fields `age: str, repos: int, contributed: int, stars: int, commits: int, followers: int, loc_add: int, loc_del: int` and property `loc_net`
  - `build_replacements(stats: Stats) -> dict[str, str]` producing exactly the tspan ids `age_data, age_dots, repo_data, contrib_data, star_data, commit_dots, commit_data, follower_data, loc_data, loc_add, loc_del`
  - `collect_stats(token: str, birthday: date, today: date) -> tuple[Stats, dict]`
  - `main(argv=None) -> int` with `--dry-run`

- [ ] **Step 1: Write the failing test**

`tests/test_assembly.py`:
```python
from update_profile import ROW_WIDTH, Stats, build_replacements

STATS = Stats(
    age="24 years, 2 months, 22 days",
    repos=25,
    contributed=13,
    stars=4,
    commits=2116,
    followers=2,
    loc_add=523178,
    loc_del=76902,
)


def test_loc_net_is_add_minus_del():
    assert STATS.loc_net == 446276


def test_number_formatting_with_separators():
    r = build_replacements(STATS)
    assert r["loc_data"] == "446,276"
    assert r["loc_add"] == "523,178++"
    assert r["loc_del"] == "76,902--"
    assert r["commit_data"] == "2,116"
    assert r["repo_data"] == "25"


def test_uptime_row_width_invariant():
    r = build_replacements(STATS)
    assert len(". Uptime: ") + len(r["age_dots"]) + 1 + len(r["age_data"]) == ROW_WIDTH


def test_all_expected_ids_present():
    expected = {
        "age_data", "age_dots", "repo_data", "contrib_data", "star_data",
        "commit_dots", "commit_data", "follower_data", "loc_data", "loc_add", "loc_del",
    }
    assert set(build_replacements(STATS)) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_assembly.py -v`
Expected: FAIL with `ImportError: cannot import name 'Stats'`.

- [ ] **Step 3: Write the implementation**

Add to `update_profile.py` (`import argparse`, `from dataclasses import dataclass` at top):
```python
@dataclass
class Stats:
    age: str
    repos: int
    contributed: int
    stars: int
    commits: int
    followers: int
    loc_add: int
    loc_del: int

    @property
    def loc_net(self) -> int:
        return self.loc_add - self.loc_del


def build_replacements(stats: Stats) -> dict[str, str]:
    commit_value = f"{stats.commits:,}"
    commit_tail = f"{commit_value} | Followers: {stats.followers:,}"
    return {
        "age_data": stats.age,
        "age_dots": dots_for(". Uptime: ", stats.age),
        "repo_data": f"{stats.repos:,}",
        "contrib_data": f"{stats.contributed:,}",
        "star_data": f"{stats.stars:,}",
        "commit_dots": dots_for(". Commits: ", commit_tail),
        "commit_data": commit_value,
        "follower_data": f"{stats.followers:,}",
        "loc_data": f"{stats.loc_net:,}",
        "loc_add": f"{stats.loc_add:,}++",
        "loc_del": f"{stats.loc_del:,}--",
    }


def collect_stats(token: str, birthday: date, today: date) -> tuple[Stats, dict]:
    viewer = fetch_overview(token)
    repos = fetch_repos(token)
    cache = load_cache(CACHE_PATH)
    adds, dels, new_cache = fetch_loc(token, repos, cache, viewer["login"])
    stats = Stats(
        age=age_string(birthday, today),
        repos=len(repos),
        contributed=viewer["repositoriesContributedTo"]["totalCount"],
        stars=sum(repo["stargazerCount"] for repo in repos),
        commits=fetch_commits_total(token, viewer["createdAt"], today),
        followers=viewer["followers"]["totalCount"],
        loc_add=adds,
        loc_del=dels,
    )
    return stats, new_cache


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print values, write nothing")
    args = parser.parse_args(argv)

    token = os.environ["PROFILE_TOKEN"]
    birthday = date.fromisoformat(os.environ["BIRTHDAY"])
    stats, new_cache = collect_stats(token, birthday, date.today())
    replacements = build_replacements(stats)

    if args.dry_run:
        for key, value in replacements.items():
            print(f"{key:15} {value}")
        return 0

    changed = False
    for svg_path in (Path("dark_mode.svg"), Path("light_mode.svg")):
        old = svg_path.read_text()
        new = update_svg(old, replacements)
        if new != old:
            svg_path.write_text(new)
            changed = True
    save_cache(CACHE_PATH, new_cache)
    print("updated" if changed else "no change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/pytest -q`
Expected: all tests pass (19 at this point).

- [ ] **Step 5: Live dry run against the real API**

The executor's local `gh` token works for a read check. Run:
```bash
PROFILE_TOKEN=$(gh auth token) BIRTHDAY=2002-04-17 .venv/bin/python update_profile.py --dry-run
```
Expected: eleven lines printed, `age_data` equal to today's real age, `repo_data` around 25, no traceback. This validates the GraphQL queries against reality before any SVG exists.

- [ ] **Step 6: Commit**

```bash
git add update_profile.py tests/test_assembly.py
git commit -m "Assemble stats into tspan replacements and add main with dry run"
```

---

### Task 7: ASCII portrait generator

**Files:**
- Create: `ascii_portrait.py`
- Input: `~/Downloads/avatar.png` (USER ASSET. If missing, pause and ask Anthony to save the pixel avatar from the chat to that path before continuing.)
- Output: `portrait_fragment.svg` (working file, committed for reproducibility)

**Interfaces:**
- Produces: CLI `python ascii_portrait.py <image> [--cols 40] [--invert] [-o portrait_fragment.svg]`. Emits one `<text x="30" y="...">` line per character row with `<tspan class="X">` runs. Classes: `h` hair and outlines, `s` skin, `p` polo, `j` jacket, `c` collar, `g` drawstring, `w` highlights. Task 8's SVG templates define fills for exactly these class names.

- [ ] **Step 1: Verify the input asset exists**

Run: `ls -l ~/Downloads/avatar.png`
Expected: the file listing. If absent, STOP and ask the user for the file.

- [ ] **Step 2: Write the script**

`ascii_portrait.py`:
```python
"""One time converter. Pixel avatar to a colored ASCII SVG fragment.

Run locally, output is pasted between the PORTRAIT markers of both SVG templates.
Dev dependency only (Pillow), never runs in CI.
"""
import argparse
from pathlib import Path

from PIL import Image

RAMP = " .:-=+*#%@"

PALETTE = {
    "h": (26, 26, 26),
    "s": (232, 180, 130),
    "p": (230, 73, 128),
    "j": (92, 95, 61),
    "c": (59, 91, 219),
    "g": (64, 192, 87),
    "w": (222, 226, 230),
}

LEFT_MARGIN = 30
TOP = 60
LINE_HEIGHT = 16


def nearest_class(rgb: tuple[int, int, int]) -> str:
    def dist(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b))

    return min(PALETTE, key=lambda name: dist(PALETTE[name], rgb))


def luminance(rgb: tuple[int, int, int]) -> float:
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def cell_char(rgb: tuple[int, int, int], alpha: int, invert: bool) -> tuple[str, str | None]:
    if alpha < 128:
        return " ", None
    level = luminance(rgb) / 255
    if not invert:
        level = 1 - level
    index = max(1, min(len(RAMP) - 1, round(level * (len(RAMP) - 1))))
    return RAMP[index], nearest_class(rgb)


def render(image_path: str, cols: int, invert: bool) -> str:
    img = Image.open(image_path).convert("RGBA")
    img = img.crop(img.getbbox())
    cell_width = img.width / cols
    rows = max(1, round(img.height / (cell_width * 2)))
    img = img.resize((cols, rows), Image.BOX)

    lines = []
    for y in range(rows):
        runs: list[tuple[str | None, list[str]]] = []
        for x in range(cols):
            r, g, b, a = img.getpixel((x, y))
            char, cls = cell_char((r, g, b), a, invert)
            if runs and runs[-1][0] == cls:
                runs[-1][1].append(char)
            else:
                runs.append((cls, [char]))
        tspans = "".join(
            "".join(chars) if cls is None
            else f'<tspan class="{cls}">{"".join(chars)}</tspan>'
            for cls, chars in runs
        )
        lines.append(
            f'<text x="{LEFT_MARGIN}" y="{TOP + y * LINE_HEIGHT}" '
            f'xml:space="preserve">{tspans}</text>'
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("--cols", type=int, default=40)
    parser.add_argument("--invert", action="store_true",
                        help="bright pixels get dense characters (for dark backgrounds)")
    parser.add_argument("-o", "--out", default="portrait_fragment.svg")
    args = parser.parse_args()
    fragment = render(args.image, args.cols, args.invert)
    Path(args.out).write_text(fragment)
    print(f"wrote {args.out} ({fragment.count(chr(10))} rows x {args.cols} cols)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Generate the fragment**

Run: `.venv/bin/python ascii_portrait.py ~/Downloads/avatar.png --cols 40 -o portrait_fragment.svg`
Expected: `wrote portrait_fragment.svg (~28 rows x 40 cols)`. Row count varies with the avatar's aspect ratio; anything between 20 and 35 is fine.

- [ ] **Step 4: Eyeball the raw fragment**

Wrap it temporarily for viewing:
```bash
{ echo '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="560"><rect width="100%" height="100%" fill="#0d1117"/><style>text{font-family:Menlo,monospace;font-size:12px;fill:#c9d1d9}.h{fill:#c9d1d9}.s{fill:#e3b587}.p{fill:#ff7eb6}.j{fill:#9e9e6e}.c{fill:#6c8cff}.g{fill:#56d364}.w{fill:#adbac7}</style>'; cat portrait_fragment.svg; echo '</svg>'; } > /tmp/portrait_preview.svg && open /tmp/portrait_preview.svg
```
Expected: a recognizable colored ASCII rendering of the avatar (hair, face, pink polo, olive jacket, blue collar). If the face reads as a blob, retry with `--cols 48` or `--invert` and pick the better output by eye.

- [ ] **Step 5: Commit**

```bash
git add ascii_portrait.py portrait_fragment.svg
git commit -m "Add pixel avatar to ASCII converter and generated portrait fragment"
```

---

### Task 8: SVG templates for dark and light mode

**Files:**
- Create: `dark_mode.svg`, `light_mode.svg`
- Consumes: `portrait_fragment.svg` from Task 7 (pasted between the PORTRAIT markers), tspan ids from Task 6, portrait classes `h s p j c g w` from Task 7.

- [ ] **Step 1: Author dark_mode.svg**

The panel below is the approved mockup verbatim, split into classed tspans. Initial dynamic values are `0` placeholders; the first updater run replaces them.

`dark_mode.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="500" viewBox="0 0 1000 500" role="img" aria-label="Anthony Skenter, ASCII portrait and GitHub stats">
<style>
  rect.bg { fill: #0d1117; }
  text { font-family: "SFMono-Regular", Consolas, Menlo, monospace; font-size: 14px; fill: #c9d1d9; }
  g.portrait text { font-size: 12px; }
  .k { fill: #ffa657; }
  .v { fill: #c9d1d9; }
  .d { fill: #484f58; }
  .rule { fill: #8b949e; }
  .add { fill: #3fb950; }
  .del { fill: #f85149; }
  .h { fill: #c9d1d9; } .s { fill: #e3b587; } .p { fill: #ff7eb6; }
  .j { fill: #9e9e6e; } .c { fill: #6c8cff; } .g { fill: #56d364; } .w { fill: #adbac7; }
</style>
<rect class="bg" width="1000" height="500"/>
<g class="portrait">
<!-- PORTRAIT -->
<!-- /PORTRAIT -->
</g>
<g class="panel">
<text x="360" y="60" xml:space="preserve"><tspan class="k">askenter@github</tspan> <tspan class="rule">────────────────────────────</tspan></text>
<text x="360" y="84" xml:space="preserve"><tspan class="k">. OS: </tspan><tspan class="d">................</tspan><tspan class="v"> macOS, Linux</tspan></text>
<text x="360" y="102" xml:space="preserve"><tspan class="k">. Uptime: </tspan><tspan class="d" id="age_dots">..................</tspan> <tspan class="v" id="age_data">0</tspan></text>
<text x="360" y="120" xml:space="preserve"><tspan class="k">. Host: </tspan><tspan class="d">..............</tspan><tspan class="v"> Aevori (Founder)</tspan></text>
<text x="360" y="138" xml:space="preserve"><tspan class="k">. Kernel: </tspan><tspan class="d">............</tspan><tspan class="v"> Aerospace MEng, Imperial College London</tspan></text>
<text x="360" y="156" xml:space="preserve"><tspan class="k">. IDE: </tspan><tspan class="d">...............</tspan><tspan class="v"> VS Code, Claude Code</tspan></text>
<text x="360" y="180" xml:space="preserve"><tspan class="k">. Languages.Programming: </tspan><tspan class="v">Python, TypeScript, C++</tspan></text>
<text x="360" y="198" xml:space="preserve"><tspan class="k">. Languages.Computer: </tspan><tspan class="d">..</tspan><tspan class="v"> PyTorch, JAX, CUDA, FastAPI, Next.js</tspan></text>
<text x="360" y="216" xml:space="preserve"><tspan class="k">. Languages.Real: </tspan><tspan class="d">......</tspan><tspan class="v"> English, Greek</tspan></text>
<text x="360" y="240" xml:space="preserve"><tspan class="k">. Hobbies.Software: </tspan><tspan class="d">....</tspan><tspan class="v"> GPU parallel RL simulators</tspan></text>
<text x="360" y="258" xml:space="preserve"><tspan class="k">. Hobbies.Hardware: </tspan><tspan class="d">....</tspan><tspan class="v"> Drones, embodied AI</tspan></text>
<text x="360" y="282" xml:space="preserve"><tspan class="k">- Contact </tspan><tspan class="rule">──────────────────────────────────</tspan></text>
<text x="360" y="306" xml:space="preserve"><tspan class="k">. Website: </tspan><tspan class="d">...........</tspan><tspan class="v"> anthonyskenter.com</tspan></text>
<text x="360" y="324" xml:space="preserve"><tspan class="k">. LinkedIn: </tspan><tspan class="d">..........</tspan><tspan class="v"> anthony-skenter</tspan></text>
<text x="360" y="342" xml:space="preserve"><tspan class="k">. X: </tspan><tspan class="d">.................</tspan><tspan class="v"> @AntonisIoanno17</tspan></text>
<text x="360" y="360" xml:space="preserve"><tspan class="k">. Email: </tspan><tspan class="d">.............</tspan><tspan class="v"> ioannouskenter@gmail.com</tspan></text>
<text x="360" y="384" xml:space="preserve"><tspan class="k">- GitHub Stats </tspan><tspan class="rule">─────────────────────────────</tspan></text>
<text x="360" y="408" xml:space="preserve"><tspan class="k">. Repos: </tspan><tspan class="v" id="repo_data">0</tspan><tspan class="k"> (Contributed: </tspan><tspan class="v" id="contrib_data">0</tspan><tspan class="k">) | Stars: </tspan><tspan class="v" id="star_data">0</tspan></text>
<text x="360" y="426" xml:space="preserve"><tspan class="k">. Commits: </tspan><tspan class="d" id="commit_dots">........</tspan> <tspan class="v" id="commit_data">0</tspan><tspan class="k"> | Followers: </tspan><tspan class="v" id="follower_data">0</tspan></text>
<text x="360" y="444" xml:space="preserve"><tspan class="k">. Lines of Code on GitHub: </tspan><tspan class="v" id="loc_data">0</tspan><tspan class="v"> ( </tspan><tspan class="add" id="loc_add">0++</tspan><tspan class="v">, </tspan><tspan class="del" id="loc_del">0--</tspan><tspan class="v"> )</tspan></text>
</g>
</svg>
```

Then paste the contents of `portrait_fragment.svg` between the `<!-- PORTRAIT -->` markers.

- [ ] **Step 2: Author light_mode.svg**

Copy `dark_mode.svg` and replace only the `<style>` block:
```xml
<style>
  rect.bg { fill: #ffffff; }
  text { font-family: "SFMono-Regular", Consolas, Menlo, monospace; font-size: 14px; fill: #24292f; }
  g.portrait text { font-size: 12px; }
  .k { fill: #953800; }
  .v { fill: #24292f; }
  .d { fill: #d0d7de; }
  .rule { fill: #6e7781; }
  .add { fill: #1a7f37; }
  .del { fill: #cf222e; }
  .h { fill: #24292f; } .s { fill: #b07d48; } .p { fill: #d6336c; }
  .j { fill: #5c5f3d; } .c { fill: #3b5bdb; } .g { fill: #1a7f37; } .w { fill: #6e7781; }
</style>
```
Everything outside the style block must stay byte identical to dark_mode.svg (same portrait fragment, same ids).

- [ ] **Step 3: Populate real values with a live local run**

```bash
PROFILE_TOKEN=$(gh auth token) BIRTHDAY=2002-04-17 .venv/bin/python update_profile.py
```
Expected: prints `updated`, both SVGs now show real numbers, `cache/loc_cache.json` exists with only hex keys.

- [ ] **Step 4: Verify idempotence**

Run the same command again.
Expected: prints `no change` and `git status` shows no new modifications beyond the first run.

- [ ] **Step 5: Visual check of both themes**

Run: `open dark_mode.svg && open light_mode.svg` and inspect: portrait recognizable in both palettes, panel columns aligned, uptime row right edge flush with the OS row right edge, no overlapping text. Tune static dot counts in BOTH files identically if a row looks off, then rerun Step 3 and 4.

- [ ] **Step 6: Confirm no private repo names anywhere**

Run:
```bash
gh repo list Askenter --visibility private --json name --jq '.[].name' \
  | grep -iFf /dev/stdin dark_mode.svg light_mode.svg cache/loc_cache.json \
  && echo LEAK || echo clean
```
Expected: `clean`. (Names are piped from gh at run time so no private name is ever written into this plan, which is itself pushed to the public repo.)

- [ ] **Step 7: Commit**

```bash
git add dark_mode.svg light_mode.svg cache/loc_cache.json
git commit -m "Add dark and light SVG panels with portrait and live stats"
```

---

### Task 9: README, workflow, secret, deploy, docs

**Files:**
- Modify: `README.md` (full replacement)
- Create: `.github/workflows/update-profile.yml`
- Create: `docs/profile-readme/implementation.md`, `docs/profile-readme/overview.md`, `docs/profile-readme/tests.md`

**Interfaces:**
- Consumes: both SVGs from Task 8, `update_profile.py` CLI from Task 6, secret name `PROFILE_TOKEN` fixed by the spec.

- [ ] **Step 1: Replace README.md**

```markdown
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="dark_mode.svg">
  <img alt="Anthony Skenter. ASCII portrait and GitHub stats panel, refreshed daily." src="light_mode.svg">
</picture>

<p>
  <a href="https://anthonyskenter.com">anthonyskenter.com</a> ·
  <a href="https://www.linkedin.com/in/anthony-skenter">LinkedIn</a> ·
  <a href="https://x.com/AntonisIoanno17">X</a> ·
  <a href="mailto:ioannouskenter@gmail.com">Email</a>
</p>

<sub>Layout inspired by <a href="https://github.com/Andrew6rant">Andrew6rant</a>. Pipeline documented in <a href="docs/profile-readme">docs/profile-readme</a>.</sub>
```

- [ ] **Step 2: Write the workflow**

`.github/workflows/update-profile.yml`:
```yaml
name: Update profile stats

on:
  schedule:
    - cron: "0 5 * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python update_profile.py
        env:
          PROFILE_TOKEN: ${{ secrets.PROFILE_TOKEN }}
          BIRTHDAY: "2002-04-17"
      - name: Commit refreshed stats
        run: |
          if ! git diff --quiet; then
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
            git add dark_mode.svg light_mode.svg cache/loc_cache.json
            git commit -m "Refresh profile stats"
            git push
          fi
```

- [ ] **Step 3: USER ACTION, create and store the PAT**

Ask Anthony to create a fine grained token at https://github.com/settings/personal-access-tokens/new with Resource owner Askenter, All repositories, Repository permissions Contents Read only and Metadata Read only, expiration 1 year. Then store it (he can paste it when prompted):
```bash
gh secret set PROFILE_TOKEN -R Askenter/Askenter
```
Verify: `gh secret list -R Askenter/Askenter` shows `PROFILE_TOKEN`.
Fallback note: if the first workflow run later shows zero private repos in the count, fine grained tokens may be the cause; swap for a classic PAT with `repo` scope at https://github.com/settings/tokens and set the secret again.

- [ ] **Step 4: Update the feature docs**

`docs/profile-readme/overview.md`:
```markdown
# Profile README — Overview

The Askenter/Askenter profile renders a colored ASCII portrait next to a
neofetch style panel. Stats (age, repos, contributed, stars, commits,
followers, lines of code) refresh daily at 05:00 UTC via GitHub Actions.
See design.md for decisions, implementation.md for the moving parts,
tests.md for the test map.
```

`docs/profile-readme/implementation.md`:
```markdown
# Profile README — Implementation

`update_profile.py` runs daily. It computes age from the BIRTHDAY env var,
pulls repo, star, follower, contributed and commit counts from the GraphQL
API, sums lines of code per owned repo through the REST contributor stats
endpoint (SHA256 hashed cache in cache/loc_cache.json, invalidated by
pushed_at), then rewrites tspan values by id in dark_mode.svg and
light_mode.svg. Nothing is written unless every API call succeeded.
`ascii_portrait.py` is the one time avatar converter. The workflow lives in
.github/workflows/update-profile.yml and commits only when values changed.
The PROFILE_TOKEN secret is a read only fine grained PAT.
```

`docs/profile-readme/tests.md`:
```markdown
# Profile README — Tests

Run with `.venv/bin/pytest -q` from the repo root.

test_age.py — age math incl. leap day and singular units
test_leaders.py — dot leader row width invariant
test_svg_rewrite.py — tspan replacement, escaping, missing id failure
test_cache.py — SHA256 keys, roundtrip, no plain repo names on disk
test_api.py — GraphQL errors, 202 retry/backoff, rate limit guard,
cache hit skips fetch, stale cache fallback, pending without cache raises
test_assembly.py — number formatting, loc_net, replacement id set

End to end check is a workflow_dispatch run plus an eyeball of the profile
in both GitHub themes.
```

- [ ] **Step 5: Run the full suite one last time**

Run: `.venv/bin/pytest -q`
Expected: all tests pass.

- [ ] **Step 6: Push everything**

```bash
git add README.md .github/workflows/update-profile.yml docs/profile-readme/
git commit -m "Replace profile README with SVG panel and add daily update workflow"
git push origin main
```

- [ ] **Step 7: End to end verification**

```bash
gh workflow run update-profile.yml -R Askenter/Askenter
sleep 30 && gh run list -R Askenter/Askenter --workflow=update-profile.yml --limit 1
gh run watch -R Askenter/Askenter $(gh run list -R Askenter/Askenter --workflow=update-profile.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```
Expected: run concludes `success`. Then screenshot https://github.com/Askenter with the agent-browser CLI and confirm the profile renders the panel with nonzero stats. Check both themes. If the run failed, read the log with `gh run view --log-failed`, fix, and rerun before declaring done.

- [ ] **Step 8: Final tidy**

Confirm no dead code and no leftover working files: `git status` clean, `portrait_fragment.svg` committed (reproducibility) and referenced in implementation.md. Done.

---

## Self-Review Notes

- Spec coverage: replacement README (T9), dynamic stats incl. LOC (T5, T6), colored portrait (T7, T8), dark plus light SVGs via picture element (T8, T9), hashed cache keys (T4, T8 Step 6), fail loudly without partial writes (T6 main ordering, fetch before write), 202 retry with stale fallback (T5), rate limit guard (T5), idempotence (T8 Step 4), dry run (T6), footer links and credit (T9), PAT as Actions secret (T9), docs set per user convention (T9). No gaps found.
- Placeholder scan: none. Every code step carries full code.
- Type consistency: `Stats` fields match `build_replacements` and `collect_stats`; tspan ids in T6 match the SVG templates in T8; portrait classes in T7 match both style blocks in T8; `dots_for(label, value)` signature consistent across T2 and T6.
