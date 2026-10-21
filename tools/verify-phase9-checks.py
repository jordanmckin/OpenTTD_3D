"""Phase 9.1: vehicle windows with their own cameras change only themselves, never pick, and restore exactly."""
import json
import re
import sys
from pathlib import Path
from PIL import Image, ImageChops

folder = Path(sys.argv[1])
log = (folder / 'stderr.log').read_text(errors='replace')
assert not re.search(r'3D proof failed|3D proof OpenGL error|Assertion failed|Your script made an error', log)

views = re.findall(r'PHASE9 VIEW vehicle=(\d+) camera=(\w+) viewport=(-?\d+),(-?\d+),(\d+),(\d+) centre_pick=(-?\d+),(-?\d+)', log)
assert len(views) >= 4 * 5, len(views)
for vehicle, camera, *_, px, py in views:
    own = camera != 'normal'
    assert (px, py) == ('-1', '-1') if own else int(px) >= 0, (vehicle, camera, px, py)
rects = {}
for vehicle, _, left, top, width, height, _, _ in views[:4]:
    rects[vehicle] = (int(left), int(top), int(left) + int(width), int(top) + int(height))
assert len(rects) == 4, rects


def load(name):
    path = folder / 'screenshot' / f'{name}.bmp'
    return Image.open(path).convert('RGB')


def mask(size):
    m = Image.new('L', size, 0)
    for r in rects.values():
        m.paste(255, r)
    return m


def message_box(size):
    """The centred 'Screenshot successfully saved' message, whose file name differs in every capture."""
    w, h = size
    return (w // 2 - 250, h // 2 - 50, w // 2 + 250, h // 2 + 50)


def differing(a, b, region):
    """Fraction of pixels inside (region=True) or outside the vehicle viewports that differ, ignoring the message."""
    diff = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v > 6 else 0)
    m = mask(a.size)
    if not region:
        m = m.point(lambda v: 255 - v)
        for r in rects.values():
            m.paste(0, (r[2] - 4, r[1], r[2] + 40, r[3] + 8))  # The window's button column: the camera button shows pressed (Phase 9.3).
    m.paste(0, message_box(a.size))
    total = sum(1 for v in m.getdata() if v)
    changed = sum(1 for d, v in zip(diff.getdata(), m.getdata()) if d and v)
    return changed / max(total, 1)


normal, chase, cab, back = (load(n) for n in ('phase9-normal', 'phase9-chase', 'phase9-cab', 'phase9-back'))
result = {}
result['back_vs_normal'] = differing(normal, back, True) + differing(normal, back, False)
assert result['back_vs_normal'] == 0, result
result['chase_outside'] = differing(normal, chase, False)
result['cab_outside'] = differing(normal, cab, False)
assert result['chase_outside'] == 0 and result['cab_outside'] == 0, result
result['chase_inside'] = differing(normal, chase, True)
result['cab_vs_chase_inside'] = differing(chase, cab, True)
assert result['chase_inside'] > .2 and result['cab_vs_chase_inside'] > .1, result

shared, orbit = load('phase9-cab-shared'), load('phase9-cab-orbit')
result['orbit_inside'] = differing(shared, orbit, True)
result['orbit_outside'] = differing(shared, orbit, False)
assert result['orbit_inside'] == 0 and result['orbit_outside'] > .2, result

result['moving_inside'] = differing(load('phase9-moving-start'), load('phase9-moving-end'), True)
assert result['moving_inside'] > .01, result
result['classic_vs_resumed_inside'] = differing(load('phase9-classic'), load('phase9-resumed'), True)
assert result['classic_vs_resumed_inside'] > .2, result

frames = re.findall(r'gpu-reference valid=(\w+) differing=(\d+) pixels=(\d+)', log)
assert len(frames) > 10 and all(v == 'true' for v, _, _ in frames), len(frames)
result['gpu_references'] = len(frames)
result['max_gpu_differing'] = max(int(d) / int(n) for _, d, n in frames)
assert result['max_gpu_differing'] < .005, result
kept = re.findall(r'kept-reference valid=(\w+) differing=(\d+) pixels=(\d+)', log)
assert all(v == 'true' for v, _, _ in kept)
result['kept_references'] = len(kept)
result['max_kept_differing'] = max((int(d) / int(n) for _, d, n in kept), default=0)
assert result['max_kept_differing'] < .0005, result
print(json.dumps(result, indent=1))
