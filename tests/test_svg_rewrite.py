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
