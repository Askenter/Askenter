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
