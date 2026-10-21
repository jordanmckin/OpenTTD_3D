"""Phase 9.2: perspective cameras change only their own windows, match the unculled reference, and fade into the sky."""
import json
import re
import sys
from pathlib import Path
from PIL import Image, ImageChops

folder = Path(sys.argv[1])
fleet = not (folder / 'screenshot' / 'p9-normal.bmp').exists()
log = (folder / 'stderr.log').read_text(errors='replace')
assert not re.search(r'3D proof failed|3D proof OpenGL error|Assertion failed|Your script made an error', log)

views = re.findall(r'PHASE9 VIEW vehicle=(\d+) camera=(\w+) viewport=(-?\d+),(-?\d+),(\d+),(\d+) centre_pick=(-?\d+),(-?\d+)', log)
eyes = re.findall(r'PHASE9 EYE vehicle=(\d+) eye=', log)
assert len(views) >= (5 if fleet else 4 * 3) and len(eyes) >= (5 if fleet else 4 * 2), (len(views), len(eyes))
for vehicle, camera, *_, px, py in views:
    own = camera != 'normal'
    assert (px, py) == ('-1', '-1') if own else int(px) >= 0, (vehicle, camera, px, py)
*_, big_left, big_top, big_width, big_height, _, _ = views[-1]
big = (int(big_left), int(big_top), int(big_left) + int(big_width), int(big_top) + int(big_height))
assert int(big_width) >= 800 and int(big_height) >= 500, big


def load(name):
    return Image.open(folder / 'screenshot' / f'{name}.bmp').convert('RGB')


FOG = (158, 181, 199)  # PROOF_FOG in proof3d_impl.h


def band(image, rows):
    """Pixels in the given fraction of rows of the large view."""
    left, top, right, bottom = big
    return list(image.crop((left, top + int(rows[0] * (bottom - top)), right, top + int(rows[1] * (bottom - top)))).getdata())


def sky(image, rows):
    """Fraction of pixels in the rows that are exactly the fog colour (allowing rounding)."""
    pixels = band(image, rows)
    return sum(1 for p in pixels if all(abs(c - f) <= 3 for c, f in zip(p, FOG))) / len(pixels)


def haze(image, rows):
    """Mean colour distance from the fog colour: small where the scene has faded into it."""
    pixels = band(image, rows)
    return sum(sum(abs(c - f) for c, f in zip(p, FOG)) for p in pixels) / len(pixels)


result = {}
if not fleet:
    rects = {}
    for vehicle, _, left, top, width, height, _, _ in views[:4]:
        rects[vehicle] = (int(left), int(top), int(left) + int(width), int(top) + int(height))
    assert len(rects) == 4, rects

    def differing(a, b, region):
        """Fraction of pixels inside (region=True) or outside the vehicle viewports that differ, ignoring the message."""
        diff = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v > 6 else 0)
        m = Image.new('L', a.size, 0)
        for r in rects.values():
            m.paste(255, r)
        if not region:
            m = m.point(lambda v: 255 - v)
            for r in rects.values():
                m.paste(0, (r[2] - 4, r[1], r[2] + 40, r[3] + 8))  # The window's button column: the camera button shows pressed (Phase 9.3).
        w, h = a.size
        m.paste(0, (w // 2 - 250, h // 2 - 50, w // 2 + 250, h // 2 + 50))  # The 'Screenshot saved' message.
        total = sum(1 for v in m.getdata() if v)
        changed = sum(1 for d, v in zip(diff.getdata(), m.getdata()) if d and v)
        return changed / max(total, 1)

    normal, eye, back = (load(n) for n in ('p9-normal', 'p9-eye', 'p9-back'))
    result['back_vs_normal'] = differing(normal, back, True) + differing(normal, back, False)
    result['eye_outside'] = differing(normal, eye, False)
    result['eye_inside'] = differing(normal, eye, True)
    assert result['back_vs_normal'] == 0 and result['eye_outside'] == 0 and result['eye_inside'] > .2, result
    # Every view shows sky in its upper part, below the banner rows, and ground with no holes through to the sky below it.
    for name in ('p9-horizon', 'p9-big-ahead', 'p9-big-n', 'p9-big-e', 'p9-big-s', 'p9-big-w', 'p9-low'):
        image = load(name)
        result[f'{name}_sky_upper'] = sky(image, (.15, .3))
        result[f'{name}_sky_lower'] = sky(image, (.6, 1))
        assert result[f'{name}_sky_upper'] > .2 and result[f'{name}_sky_lower'] == 0, result
else:
    # Views of a large map: nothing near is missing, and the ground fades into the fog towards the draw distance.
    for name in ('p9-far-n', 'p9-far-e', 'p9-far-s', 'p9-far-w', 'p9-far-high'):
        image = load(name)
        result[f'{name}_sky_lower'] = sky(image, (.7, 1))
        result[f'{name}_haze_near'] = haze(image, (.85, 1))
        horizon = min(((r / 100, (r + 2) / 100) for r in range(20, 80, 2)), key=lambda rows: abs(sky(image, rows) - .5))
        result[f'{name}_haze_horizon'] = haze(image, (horizon[1], horizon[1] + .04))
        assert result[f'{name}_sky_lower'] == 0 or name == 'p9-far-high', result
    # From high up the ground is open to the draw distance, so the lower corners already reach full fog; at eye level near trees hide it.
    assert result['p9-far-high_haze_horizon'] < result['p9-far-high_haze_near'] / 2, result

for kind in ('gpu', 'kept', 'instance'):
    frames = [(v, int(d), int(n)) for v, d, n, p in re.findall(rf'{kind}-reference valid=(\w+) differing=(\d+) pixels=(\d+) perspective=(\w+)', log) if p == 'true']
    assert all(v == 'true' for v, _, _ in frames), kind
    result[f'{kind}_references'] = len(frames)
    result[f'max_{kind}_differing'] = max((d / n for _, d, n in frames), default=0)
assert result['gpu_references'] >= (3 if fleet else 10) and result['max_gpu_differing'] < .005, result
assert result['max_kept_differing'] < .0005 and result['max_instance_differing'] < .005, result
print(json.dumps(result, indent=1))
