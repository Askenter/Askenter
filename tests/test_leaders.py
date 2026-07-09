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
