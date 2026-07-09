"""Remove a baked in checkerboard background via border flood fill.

The source avatar ships with its transparency flattened into opaque
checkerboard pixels. This keys them out from the image borders inward
so ascii_portrait.py sees real alpha.

Usage: python clean_avatar.py <src.png> <dst.png>
Chain: avatar.png -> clean_avatar.py -> avatar_clean.png -> ascii_portrait.py -> portrait_fragment.svg
Dev only, never runs in CI.
"""
import sys
from collections import deque

from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
img = Image.open(src).convert("RGBA")
px = img.load()
w, h = img.size


def is_bg(p):
    r, g, b = p[:3]
    return abs(r - g) < 14 and abs(g - b) < 14 and abs(r - b) < 14 and r > 175


seen = bytearray(w * h)
queue = deque()
for x in range(w):
    queue.append((x, 0))
    queue.append((x, h - 1))
for y in range(h):
    queue.append((0, y))
    queue.append((w - 1, y))

while queue:
    x, y = queue.popleft()
    if x < 0 or y < 0 or x >= w or y >= h or seen[y * w + x]:
        continue
    seen[y * w + x] = 1
    if not is_bg(px[x, y]):
        continue
    px[x, y] = (0, 0, 0, 0)
    queue.append((x + 1, y))
    queue.append((x - 1, y))
    queue.append((x, y + 1))
    queue.append((x, y - 1))

img.save(dst)
print("done")
