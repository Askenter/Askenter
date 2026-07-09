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
