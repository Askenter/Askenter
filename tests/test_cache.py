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
