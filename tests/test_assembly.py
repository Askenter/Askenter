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
