"""Phase 9.3: the chase camera button and hotkey, smooth chase cameras, pause, reload, and large chase views."""
import json
import math
import re
import sys
from pathlib import Path
from PIL import Image, ImageChops

folder = Path(sys.argv[1])
types = sys.argv[2].split(',')
log = (folder / 'stderr.log').read_text(errors='replace')
assert not re.search(r'3D proof failed|3D proof OpenGL error|Assertion failed|Your script made an error', log)
TYPE_IDS = {'train': 0, 'road': 1, 'ship': 2, 'aircraft': 3}
BACK, UP, SNAP = 56, 24, 64  # CHASE_BACK, CHASE_UP and CHASE_SNAP in terrain3d_math.h
FOG = (158, 181, 199)  # PROOF_FOG in proof3d_impl.h
result = {}


def load(name):
    return Image.open(folder / 'screenshot' / f'{name}.bmp').convert('RGB')


# Button and hotkey: each press moves every window on through normal, cab and chase, in the order the script pressed them.
presses = re.findall(r'PHASE9 PRESS vehicle=(\d+) by=(\w+) camera=(\d+)', log)
windows = sorted({v for v, _, _ in presses})
for vehicle in windows:
    sequence = [(by, int(c)) for v, by, c in presses if v == vehicle]
    assert sequence == [('button', 1), ('button', 2), ('button', 0), ('button', 1), ('button', 2), ('hotkey', 0), ('hotkey', 1), ('hotkey', 2)], (vehicle, sequence)
result['windows'] = len(windows)
assert len(windows) >= 2, windows

views = re.findall(r'PHASE9 VIEW vehicle=(\d+) camera=(\w+) viewport=(-?\d+),(-?\d+),(\d+),(\d+) centre_pick=(-?\d+),(-?\d+)', log)
rects = {}
for vehicle, _, left, top, width, height, _, _ in views[:len(windows)]:
    rects[vehicle] = (int(left), int(top), int(left) + int(width), int(top) + int(height))
assert len(rects) == len(windows), rects
for vehicle, camera, *_, px, py in views:
    assert (px, py) == ('-1', '-1') if camera != 'normal' else int(px) >= 0, (vehicle, camera, px, py)


def differing(a, b, region=None):
    """Fraction of pixels inside (True), outside (False) or anywhere (None) in the vehicle viewports that differ, ignoring the message."""
    diff = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v > 6 else 0)
    m = Image.new('L', a.size, 0 if region is not None else 255)
    if region is not None:
        for r in rects.values():
            m.paste(255, r)
        if not region:
            m = m.point(lambda v: 255 - v)
    w, h = a.size
    m.paste(0, (w // 2 - 250, h // 2 - 50, w // 2 + 250, h // 2 + 50))  # The 'Screenshot saved' message.
    if region is False:
        for r in rects.values():
            m.paste(0, (r[2] - 4, r[1], r[2] + 40, r[3] + 8))  # The window's button column: the camera button shows pressed in chase.
    total = sum(1 for v in m.getdata() if v)
    changed = sum(1 for d, v in zip(diff.getdata(), m.getdata()) if d and v)
    return changed / max(total, 1)


normal, button, view, off, on = (load(f'p9-c-{n}') for n in ('normal', 'button', 'view', 'hotkey-off', 'hotkey-on'))
result['button_outside'] = differing(normal, button, False)
result['button_inside'] = differing(normal, button, True)
result['button_vs_console'] = differing(button, view)
result['hotkey_off_vs_normal'] = differing(normal, off)
result['hotkey_on_vs_button'] = differing(button, on)
assert result['button_outside'] == 0 and result['button_inside'] > .2, result
assert result['button_vs_console'] == 0 and result['hotkey_off_vs_normal'] == 0 and result['hotkey_on_vs_button'] == 0, result

# Paused: the chase cameras settle, so nothing on the screen changes.
result['paused_differing'] = differing(load('p9-paused-a'), load('p9-paused-b'))
assert result['paused_differing'] == 0, result

# Reload: no chase camera survives the old game; the windows game_start.scr opens again are normal.
loaded = log[log.rindex('PHASE9 WINDOW'):]
reloaded = re.findall(r'PHASE9 VIEW vehicle=\d+ camera=(\w+)', loaded)
result['windows_after_reload'] = len(reloaded)
assert reloaded and all(c == 'normal' for c in reloaded) and 'Loading failed' not in log, reloaded
targets = re.findall(r'PHASE9 TARGET target=(\w+) windows=(\d+)', log)
assert [(t, int(n)) for t, n in targets[-len(types):]] == [(t, 1) for t in types], targets[-len(types):]


def forward(heading):
    a = math.radians(heading)
    return (-(math.cos(a) + math.sin(a)) / math.sqrt(2), (math.sin(a) - math.cos(a)) / math.sqrt(2))


# Smoothness, from every chase camera update over a month at normal speed. A camera snaps when it moves much further
# in one frame than the vehicle does; the unsmoothed camera (always straight behind the vehicle) is shown for contrast.
chase = re.findall(r'PHASE9 CHASE vehicle=(\d+) type=(\d+) tile_type=(\d+) ground=(-?\d+) ms=(\d+) target=(\S+) smooth=(\S+) eye=(\S+) pitch=(\S+)', log)
tracks = {}
for vehicle, kind, tile_type, ground, ms, target, smooth, eye, _ in chase:
    tracks.setdefault(vehicle, []).append((int(kind), int(tile_type), int(ground), int(ms), [float(v) for v in target.split(',')], [float(v) for v in smooth.split(',')], [float(v) for v in eye.split(',')]))
per_type = {}
for vehicle, track in tracks.items():
    kind = track[0][0]
    stats = per_type.setdefault(kind, {'vehicles': 0, 'updates': 0, 'turns': 0, 'climbs': 0, 'station': 0, 'bridge': 0, 'tunnel': 0, 'max_turn_step': 0, 'max_excess': 0, 'max_raw_excess': 0, 'max_eye_step': 0})
    stats['vehicles'] += 1
    stats['updates'] += len(track)
    steps = [0] + [math.dist(track[i][4][:3], track[i - 1][4][:3]) for i in range(1, len(track))]
    for i, (_, tile_type, ground, ms, target, smooth, eye) in enumerate(track):
        on_tunnel_bridge = tile_type == 9
        stats['station'] += tile_type == 5
        stats['bridge'] += on_tunnel_bridge and target[2] > ground + 4
        stats['tunnel'] += on_tunnel_bridge and target[2] < ground - 4
        if i == 0:
            continue
        previous = track[i - 1]
        stats['turns'] += target[3] != previous[4][3]
        stats['climbs'] += target[2] != previous[4][2] and not on_tunnel_bridge
        if ms >= 100 or steps[i] > SNAP:
            continue  # A stalled frame (screenshot) or a jump the camera deliberately restarts from.
        nearby = max(steps[max(0, i - 2):i + 3])
        eye_step = math.dist(eye, previous[6])
        f, g = forward(target[3]), forward(previous[4][3])
        raw = (target[0] - f[0] * BACK, target[1] - f[1] * BACK, target[2] + UP)
        raw_previous = (previous[4][0] - g[0] * BACK, previous[4][1] - g[1] * BACK, previous[4][2] + UP)
        stats['max_turn_step'] = max(stats['max_turn_step'], abs(math.remainder(smooth[3] - previous[5][3], 360)))
        stats['max_excess'] = max(stats['max_excess'], eye_step - nearby)
        stats['max_raw_excess'] = max(stats['max_raw_excess'], math.dist(raw, raw_previous) - nearby)
        stats['max_eye_step'] = max(stats['max_eye_step'], eye_step)
names = {v: k for k, v in TYPE_IDS.items()}
result['chase'] = {names[k]: {s: round(v, 2) for s, v in stats.items()} for k, stats in sorted(per_type.items())}
for name in types:
    stats = per_type.get(TYPE_IDS[name])
    assert stats is not None and stats['updates'] > 500, (name, stats)
    assert stats['turns'] >= 2 and stats['max_turn_step'] <= 8 and stats['max_excess'] <= 8, (name, stats)
assert any(per_type[TYPE_IDS[n]]['climbs'] > 0 for n in types), result['chase']
if 'train' in types:
    assert all(per_type[TYPE_IDS[n]]['station'] > 0 for n in types), result['chase']
    assert any(per_type[TYPE_IDS[n]]['bridge'] > 0 for n in types), result['chase']
else:
    assert per_type[TYPE_IDS['aircraft']]['station'] > 0, result['chase']

# Large chase windows: the ground below the horizon has no holes through to the sky.
sized = re.findall(r'PHASE9 WINDOW vehicle=(\d+) size=\d+x\d+ viewport=(\d+)x(\d+) at=(-?\d+),(-?\d+)', log)
for name, (vehicle, width, height, left, top) in zip(types, sized[-len(types):]):
    width, height, left, top = int(width), int(height), int(left), int(top)
    assert width >= 800 and height >= 500, (name, width, height)
    image = load(f'p9-big-{name}')
    pixels = list(image.crop((left, top + height // 2, left + width, top + height)).getdata())
    result[f'big_{name}_sky_lower'] = sum(1 for p in pixels if all(abs(c - f) <= 3 for c, f in zip(p, FOG))) / len(pixels)
    # Aircraft fly out over the edge of the map, where there is no ground to see.
    assert result[f'big_{name}_sky_lower'] == 0 or name == 'aircraft', result

for kind in ('gpu', 'kept', 'instance'):
    frames = [(v, int(d), int(n)) for v, d, n, p in re.findall(rf'{kind}-reference valid=(\w+) differing=(\d+) pixels=(\d+) perspective=(\w+)', log) if p == 'true']
    assert all(v == 'true' for v, _, _ in frames), kind
    result[f'{kind}_references'] = len(frames)
    result[f'max_{kind}_differing'] = max((d / n for _, d, n in frames), default=0)
assert result['gpu_references'] >= 10 and result['max_gpu_differing'] < .005, result
assert result['max_kept_differing'] < .0005 and result['max_instance_differing'] < .005, result
print(json.dumps(result, indent=1))
