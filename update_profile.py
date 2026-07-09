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


ROW_WIDTH = 58


def dots_for(label: str, value: str, row_width: int = ROW_WIDTH) -> str:
    count = row_width - len(label) - len(value) - 1
    return "." * max(count, 3)
