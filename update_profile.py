"""Daily profile updater. Rewrites stats inside dark_mode.svg and light_mode.svg."""
import hashlib
import json
import re
import time
import requests
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from dateutil.relativedelta import relativedelta


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


def age_string(birthday: date, today: date) -> str:
    delta = relativedelta(today, birthday)
    parts = []
    for amount, unit in ((delta.years, "year"), (delta.months, "month"), (delta.days, "day")):
        suffix = "" if amount == 1 else "s"
        parts.append(f"{amount} {unit}{suffix}")
    return ", ".join(parts)


ROW_WIDTH = 58


def dots_for(label: str, value: str, row_width: int = ROW_WIDTH) -> str:
    count = row_width - len(label) - len(value) - 1
    return "." * max(count, 3)


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
            sleep(2 ** attempt)
            continue
        if response.status_code == 204:
            return 0, 0
        raise ApiError(f"stats HTTP {response.status_code} for a repo")
    raise StatsPending(name_with_owner)


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
