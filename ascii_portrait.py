"""One time converter. Pixel avatar to a colored ASCII SVG fragment.

Run locally, output is pasted between the PORTRAIT markers of both SVG templates.
Dev dependency only (Pillow), never runs in CI.
"""
import argparse
from pathlib import Path

from PIL import Image

RAMP = " .:-=+*#%@"

PALETTE = {
    "h": (26, 26, 26),
    "s": (232, 180, 130),
    "p": (230, 73, 128),
    "j": (92, 95, 61),
    "c": (59, 91, 219),
    "g": (64, 192, 87),
    "w": (222, 226, 230),
}

LEFT_MARGIN = 30
TOP = 60
LINE_HEIGHT = 16


def nearest_class(rgb: tuple[int, int, int]) -> str:
    def dist(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b))

    return min(PALETTE, key=lambda name: dist(PALETTE[name], rgb))


def luminance(rgb: tuple[int, int, int]) -> float:
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def cell_char(rgb: tuple[int, int, int], alpha: int, invert: bool) -> tuple[str, str | None]:
    if alpha < 128:
        return " ", None
    level = luminance(rgb) / 255
    if not invert:
        level = 1 - level
    index = max(1, min(len(RAMP) - 1, round(level * (len(RAMP) - 1))))
    return RAMP[index], nearest_class(rgb)


def render(image_path: str, cols: int, invert: bool) -> str:
    img = Image.open(image_path).convert("RGBA")
    img = img.crop(img.getbbox())
    cell_width = img.width / cols
    rows = max(1, round(img.height / (cell_width * 2)))
    img = img.resize((cols, rows), Image.BOX)

    lines = []
    for y in range(rows):
        runs: list[tuple[str | None, list[str]]] = []
        for x in range(cols):
            r, g, b, a = img.getpixel((x, y))
            char, cls = cell_char((r, g, b), a, invert)
            if runs and runs[-1][0] == cls:
                runs[-1][1].append(char)
            else:
                runs.append((cls, [char]))
        tspans = "".join(
            "".join(chars) if cls is None
            else f'<tspan class="{cls}">{"".join(chars)}</tspan>'
            for cls, chars in runs
        )
        lines.append(
            f'<text x="{LEFT_MARGIN}" y="{TOP + y * LINE_HEIGHT}" '
            f'xml:space="preserve">{tspans}</text>'
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("--cols", type=int, default=40)
    parser.add_argument("--invert", action="store_true",
                        help="bright pixels get dense characters (for dark backgrounds)")
    parser.add_argument("-o", "--out", default="portrait_fragment.svg")
    args = parser.parse_args()
    fragment = render(args.image, args.cols, args.invert)
    Path(args.out).write_text(fragment)
    print(f"wrote {args.out} ({fragment.count(chr(10))} rows x {args.cols} cols)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
