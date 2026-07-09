# Profile README, neofetch style — Design

Date 2026-07-09. Status approved by Anthony during brainstorming.

## Purpose

Replace the current badge based profile README of `Askenter/Askenter` with a terminal style profile in the spirit of Andrew6rant. The left half shows an ASCII portrait generated from Anthony's pixel avatar. The right half shows a neofetch style info panel whose statistics refresh themselves daily through a GitHub Action.

## Decisions taken during brainstorming

1. The new design replaces the existing README entirely. The old content (selected work, writing, toolbox) is retired in favour of the panel fields.
2. Stats are fully dynamic, including lines of code, recomputed daily by a scheduled workflow.
3. The portrait source is Anthony's pixel avatar (dark hair, tan skin, pink polo, olive jacket with blue collar). The ASCII characters are colored in the SVG to match the avatar palette, which goes one step beyond the monochrome original.
4. Uptime shows Anthony's real age computed from his date of birth, 2002-04-17. Anthony accepted that this exposes his date of birth publicly.
5. Stats include private repositories as aggregate numbers only. Repo names are never rendered. A personal access token stored as an Actions secret unlocks the private counts.
6. Custom build. No code is copied from Andrew6rant's repository because it carries no license. Only the architectural idea is reused.

## Approved panel content

Dots act as leaders and get replaced by dynamic values where marked. Static values render as written.

```
askenter@github ————————————————————————————
. OS: ................ macOS, Linux
. Uptime: ............ {age}                          (dynamic, from DOB 2002-04-17)
. Host: .............. Aevori (Founder)
. Kernel: ............ Aerospace MEng, Imperial College London
. IDE: ............... VS Code, Claude Code

. Languages.Programming: Python, TypeScript, C++
. Languages.Computer: .. PyTorch, JAX, CUDA, FastAPI, Next.js
. Languages.Real: ...... English, Greek

. Hobbies.Software: .... GPU parallel RL simulators
. Hobbies.Hardware: .... Drones, embodied AI

- Contact ——————————————————————————————————
. Website: ........... anthonyskenter.com
. LinkedIn: .......... anthony-skenter
. X: ................. @AntonisIoanno17
. Email: ............. ioannouskenter@gmail.com

- GitHub Stats —————————————————————————————
. Repos: {repos} (Contributed: {contributed}) | Stars: {stars}
. Commits: {commits} | Followers: {followers}
. Lines of Code on GitHub: {loc_net} ( {loc_add}++, {loc_del}-- )
```

Contact lines render as plain text. GitHub serves README images through its camo proxy, so anchors inside an embedded SVG are not clickable. The real links live in a small footer under the image.

## Architecture

All work lives in the existing public repo `Askenter/Askenter`.

```
Askenter/
├── README.md                     picture element choosing dark or light SVG
├── dark_mode.svg                 rendered panel, dark palette
├── light_mode.svg                rendered panel, light palette
├── update_profile.py             daily updater, run by the workflow
├── ascii_portrait.py             one time converter, pixel avatar to colored ASCII
├── cache/
│   └── loc_cache.json            per repo lines of code cache
├── .github/workflows/
│   └── update-profile.yml        cron 05:00 UTC daily plus manual dispatch
└── docs/profile-readme/          this documentation set
```

### README

The README body shrinks to a `<picture>` element with a `prefers-color-scheme: dark` source pointing at `dark_mode.svg` and a fallback `img` pointing at `light_mode.svg`. Under the image sits a single footer line carrying the clickable contact links (website, LinkedIn, X, email) and a credit to Andrew6rant for the layout inspiration.

### SVG design

Both SVGs share one geometry and differ only in palette. Monospace font stack (`Consolas, Menlo, monospace`), roughly 1000×540 viewBox, portrait block left, panel block right, matching the reference screenshot proportions.

Dark palette. Background `#0d1117` (GitHub dark), field keys in orange `#ffa657`, values in light grey `#c9d1d9`, section rules in dim grey, additions in green `#3fb950`, deletions in red `#f85149`. Light palette mirrors the same roles on white `#ffffff` with GitHub light equivalents (`#953800` keys, `#24292f` values, `#1a7f37` additions, `#cf222e` deletions).

Portrait characters carry per color classes derived from the avatar palette. Hair near black, skin tan `#e0ac69` range, polo pink `#e64980` range, jacket olive `#5c5f3d` range, collar blue `#3b5bdb` range. Exact values are sampled from the avatar file during implementation.

Every dynamic value sits in its own `<tspan>` with a stable id (`age_data`, `repo_data`, `contrib_data`, `star_data`, `commit_data`, `follower_data`, `loc_data`, `loc_add`, `loc_del`). Dot leaders around dynamic values are also tspans so the updater can repad them and keep the right edge aligned.

### Updater script

`update_profile.py` runs under Python 3.12 with `requests` and `python-dateutil` only.

1. Computes age from `BIRTHDAY` env value with `dateutil.relativedelta`, rendered as `N years, N months, N days`.
2. Queries the GitHub GraphQL API as the token owner for owned repo count, stars across owned repos, total commit contributions (all time, via `contributionsCollection` per year range), follower count, and count of repositories contributed to.
3. Lines of code come from the REST endpoint `/repos/{owner}/{repo}/stats/contributors` for every owned repo, summing additions and deletions authored by `Askenter`. Results are cached per repo in `cache/loc_cache.json`, and unchanged repos (same pushed_at) are never refetched. Cache keys are SHA256 hashes of the repo name, never the name itself, because the cache file is committed to the public repo and must not leak private repo names.
4. Rewrites the identified tspans in both SVGs, recomputing dot leader lengths so columns stay aligned.
5. Writes files only when at least one value changed. The workflow commits only when git reports a diff.

A `--dry-run` flag prints the rendered values and exits without touching the SVGs, for local testing.

### Portrait pipeline

`ascii_portrait.py` runs once, locally. It loads the avatar image, downsamples it to a character grid around 40 columns wide (final width tuned by eye against the panel height), maps each cell's luminance to a character ramp (` .,:;i1tfLCG08@`), quantizes each cell's color to the nearest of the avatar's palette classes, and emits SVG text lines with per class fills, ready to paste into both SVG templates. Transparent cells become spaces. The script stays in the repo for reproducibility.

### Workflow and secrets

`update-profile.yml` triggers on `schedule` (cron `0 5 * * *`) and `workflow_dispatch`. Steps are checkout, setup Python, install the two dependencies, run the updater with `PROFILE_TOKEN` and `BIRTHDAY=2002-04-17` in the environment, then commit and push `dark_mode.svg`, `light_mode.svg`, and `cache/loc_cache.json` when changed, using the default `GITHUB_TOKEN` with `contents: write` permission.

`PROFILE_TOKEN` is a fine grained personal access token owned by Anthony, read only, scoped to all owned repositories with contents and metadata read, stored as an Actions repository secret. It is used exclusively for reading stats.

## Error handling

1. Any API failure exits nonzero before any file is written. The workflow run fails visibly and the last good SVGs stay live on the profile.
2. The contributor stats endpoint answers 202 while GitHub computes stats in the background. The script retries up to 5 times with exponential backoff, then falls back to the cached value for that repo, and only fails if the repo has no cached value at all.
3. Rate limits are respected by checking the remaining quota header and aborting cleanly with a message when exhausted.
4. The run is idempotent. Two consecutive runs on the same day produce byte identical SVGs and no second commit.

## Testing

Pytest covers the pure logic. Age string across month and year rollovers including leap years, dot leader padding for short and long values, tspan rewrite as a round trip on a fixture SVG, and LOC cache invalidation on changed pushed_at. API calls are mocked with recorded fixtures. A manual `workflow_dispatch` run serves as the end to end check after deploy, followed by an eyeball check of the rendered profile in both GitHub themes.

## Prerequisites before implementation

1. Anthony saves the pixel avatar to `~/Downloads/avatar.png` (it currently exists only in the chat).
2. Anthony creates the fine grained PAT and adds it as the `PROFILE_TOKEN` secret on `Askenter/Askenter` (I can drive this via `gh` with his approval).

## Out of scope

Contribution graphs, GitHub trophy widgets, WakaTime style coding time stats, and any redesign of anthonyskenter.com. The retired README content remains recoverable from git history.
