"""Daily profile updater. Rewrites stats inside dark_mode.svg and light_mode.svg."""
import re
from datetime import date
from xml.sax.saxutils import escape

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
