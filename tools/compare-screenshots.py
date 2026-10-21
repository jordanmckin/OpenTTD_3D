"""Pixel comparison of two screenshots; writes a diff mask."""
import sys
from PIL import Image, ImageChops

a = Image.open(sys.argv[1]).convert('RGB')
b = Image.open(sys.argv[2]).convert('RGB')
assert a.size == b.size, (a.size, b.size)
diff = ImageChops.difference(a, b)
pixels = list(diff.getdata())
differing = sum(1 for p in pixels if max(p) > 2)
print(f'size={a.size} differing={differing} fraction={differing / len(pixels):.6f} max={max(max(p) for p in pixels)}')
mask = diff.point(lambda v: 255 if v > 2 else 0)
mask.save(sys.argv[3])
