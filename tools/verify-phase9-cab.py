"""Phase 9.4: the camera button cycle, cab cameras riding their vehicles, the cab's own vehicle left out, and large cab views."""
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
TICK_STEP = 8  # CHASE_TICK_STEP in terrain3d_math.h: further than this a tick is a jump, which a cab cuts to.
TURN_RATE = 240  # CAB_TIMING.turn_rate in terrain3d_math.h, degrees a second; the grade tips at the same rate.
FOG = (158, 181, 199)  # PROOF_FOG in proof3d_impl.h
result = {}


def load(name):
    return Image.open(folder / 'screenshot' / f'{name}.bmp').convert('RGB')


# Button and hotkey: each press moves every window on through normal (0), cab (1) and chase (2).
presses = re.findall(r'PHASE9 PRESS vehicle=(\d+) by=(\w+) camera=(\d+)', log)
windows = sorted({v for v, _, _ in presses})
for vehicle in windows:
    sequence = [(by, int(c)) for v, by, c in presses if v == vehicle]
    assert sequence == [('button', 1), ('button', 2), ('button', 0), ('button', 1), ('button', 2), ('button', 0), ('hotkey', 1)], (vehicle, sequence)
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
            m.paste(0, (r[2] - 4, r[1], r[2] + 40, r[3] + 8))  # The window's button column: the camera button shows pressed.
    total = sum(1 for v in m.getdata() if v)
    changed = sum(1 for d, v in zip(diff.getdata(), m.getdata()) if d and v)
    return changed / max(total, 1)


normal, cab_button, cab_view, chase_button, chase_view, back, hotkey = (load(f'p9-k-{n}') for n in ('normal', 'cab-button', 'cab-view', 'chase-button', 'chase-view', 'back', 'hotkey-cab'))
result['cab_outside'] = differing(normal, cab_button, False)
result['cab_inside'] = differing(normal, cab_button, True)
result['cab_vs_chase_inside'] = differing(cab_button, chase_button, True)
result['cab_button_vs_console'] = differing(cab_button, cab_view)
result['chase_button_vs_console'] = differing(chase_button, chase_view)
result['back_vs_normal'] = differing(normal, back)
result['hotkey_vs_button'] = differing(cab_button, hotkey)
assert result['cab_outside'] == 0 and result['cab_inside'] > .2 and result['cab_vs_chase_inside'] > .2, result
assert result['cab_button_vs_console'] == 0 and result['chase_button_vs_console'] == 0, result
assert result['back_vs_normal'] == 0 and result['hotkey_vs_button'] == 0, result


def forward(heading):
    a = math.radians(heading)
    return (-(math.cos(a) + math.sin(a)) / math.sqrt(2), (math.sin(a) - math.cos(a)) / math.sqrt(2))


# The ride, from every cab camera update over a month at normal speed. A cab snaps when its eye moves much further in one
# frame than the vehicle does; an unsmoothed cab (on the vehicle's raw position and heading) is shown for contrast.
updates = re.findall(r'PHASE9 CHASE vehicle=(\d+) type=(\d+) tile_type=(\d+) ground=(-?\d+) ms=(\d+) target=(\S+) smooth=(\S+) eye=(\S+) pitch=(\S+) camera=cab grade=(\S+)', log)
tracks = {}
for vehicle, kind, tile_type, ground, ms, target, smooth, eye, pitch, grade in updates:
    tracks.setdefault(vehicle, []).append((int(kind), int(tile_type), int(ground), int(ms), [float(v) for v in target.split(',')], [float(v) for v in smooth.split(',')],
                                           [float(v) for v in eye.split(',')], float(pitch), [float(v) for v in grade.split(',')]))
per_type = {}
for vehicle, track in tracks.items():
    kind = track[0][0]
    stats = per_type.setdefault(kind, {'vehicles': 0, 'updates': 0, 'turns': 0, 'sloped': 0, 'station': 0, 'bridge': 0, 'tunnel': 0, 'cuts': 0,
                                       'max_turn_step': 0, 'max_grade_step': 0, 'max_turn_rate_excess': 0, 'max_excess': 0, 'max_raw_excess': 0, 'min_ahead': 1e9, 'max_ahead': 0})
    stats['vehicles'] += 1
    stats['updates'] += len(track)
    steps = [0] + [math.dist(track[i][4][:3], track[i - 1][4][:3]) for i in range(1, len(track))]
    for i, (_, tile_type, ground, ms, target, smooth, eye, pitch, grade) in enumerate(track):
        on_tunnel_bridge = tile_type == 9
        stats['station'] += tile_type == 5
        stats['bridge'] += on_tunnel_bridge and target[2] > ground + 4
        stats['tunnel'] += on_tunnel_bridge and target[2] < ground - 4
        stats['sloped'] += grade[0] != 0
        ahead = math.hypot(eye[0] - smooth[0], eye[1] - smooth[1])
        stats['min_ahead'] = min(stats['min_ahead'], ahead)
        stats['max_ahead'] = max(stats['max_ahead'], ahead)
        if i == 0:
            continue
        previous = track[i - 1]
        stats['turns'] += target[3] != previous[4][3]
        if ms > 100:
            continue  # A stalled frame (screenshot or GPU reference), covering several game ticks.
        if steps[i] > TICK_STEP + 1:
            stats['cuts'] += 1  # A train reversing: the driver changes ends, so the cab cuts.
            continue
        nearby = max(steps[max(0, i - 2):i + 3])
        f, g = forward(target[3]), forward(previous[4][3])
        raw = (target[0] + f[0] * ahead, target[1] + f[1] * ahead)
        raw_previous = (previous[4][0] + g[0] * ahead, previous[4][1] + g[1] * ahead)
        stats['max_turn_step'] = max(stats['max_turn_step'], abs(math.remainder(smooth[3] - previous[5][3], 360)))
        stats['max_grade_step'] = max(stats['max_grade_step'], abs(grade[1] - previous[8][1]))
        # Turning and tipping are capped per second, so a longer frame may turn further.
        limit = TURN_RATE * ms / 1000
        stats['max_turn_rate_excess'] = max(stats['max_turn_rate_excess'], abs(math.remainder(smooth[3] - previous[5][3], 360)) - limit, abs(grade[1] - previous[8][1]) - limit)
        stats['max_excess'] = max(stats['max_excess'], math.dist(eye, previous[6]) - nearby)
        stats['max_raw_excess'] = max(stats['max_raw_excess'], math.dist(raw, raw_previous) - nearby)
names = {v: k for k, v in TYPE_IDS.items()}
result['cab'] = {names[k]: {s: round(v, 2) for s, v in stats.items()} for k, stats in sorted(per_type.items())}
for name in types:
    stats = per_type.get(TYPE_IDS[name])
    assert stats is not None and stats['updates'] > 500, (name, stats)
    assert stats['turns'] >= 2 and stats['max_turn_rate_excess'] <= .05 and stats['max_turn_step'] <= 8 and stats['max_excess'] <= 3, (name, stats)
    assert 1 <= stats['min_ahead'] and stats['max_ahead'] <= 24, (name, stats)
if 'train' in types:
    assert all(per_type[TYPE_IDS[n]]['station'] > 0 for n in types), result['cab']
    assert any(per_type[TYPE_IDS[n]]['bridge'] > 0 for n in types), result['cab']
    assert all(per_type[TYPE_IDS[n]]['sloped'] > 0 for n in types), result['cab']
else:
    assert per_type[TYPE_IDS['aircraft']]['station'] > 0, result['cab']

# The cab's own vehicle: every cab render leaves out at most one vehicle, and nearly always exactly its own. It is not
# drawn while underground or in a depot, so there is nothing to leave out then.
hidden = [int(h) for h in re.findall(r'PHASE9 CABDRAW hidden=(\d+)', log)]
result['cab_renders'] = len(hidden)
result['cab_renders_hiding_one'] = sum(1 for h in hidden if h == 1) / max(len(hidden), 1)
assert len(hidden) > 100 and max(hidden) == 1 and result['cab_renders_hiding_one'] > .8, result

# Large cab windows: the ground below the horizon has no holes through to the sky, at every capture. The cab pitches with
# slopes, so the horizon is placed from its pitch at the capture, and the check starts a tenth of the view below it.
# Captures with the vehicle underground are left out and counted.
sized = re.findall(r'PHASE9 WINDOW vehicle=(\d+) size=\d+x\d+ viewport=(\d+)x(\d+) at=(-?\d+),(-?\d+)', log)
# Each type's captures follow its window being resized; the views lines logged with them give the pitches.
pitches = []
for start in [m.end() for m in re.finditer(r'PHASE9 WINDOW', log)][-len(types):]:
    pitches += [(float(p), u == 'true') for p, u in re.findall(r'PHASE9 VIEW vehicle=\d+ camera=cab viewport=\S+ centre_pick=\S+ pitch=(\S+) underground=(\w+)', log[start:])][:6]
CAB_FOV = 70  # CAB_FOV in terrain3d_math.h
for index, (name, (vehicle, width, height, left, top)) in enumerate(zip(types, sized[-len(types):])):
    width, height, left, top = int(width), int(height), int(left), int(top)
    assert width >= 800 and height >= 500, (name, width, height)
    worst = 0
    for shot in range(6):
        pitch, underground = pitches[index * 6 + shot]
        result.setdefault(f'big_{name}_pitches', []).append(round(pitch, 1))
        if underground:
            result[f'big_{name}_underground'] = result.get(f'big_{name}_underground', 0) + 1
            continue  # In a tunnel the cab sees the hill from below until the 9.5 fade.
        if pitch > 0:
            # Climbing to a crest the ground ahead falls away below the pitched horizon, so real sky shows there.
            result[f'big_{name}_climbing'] = result.get(f'big_{name}_climbing', 0) + 1
            continue
        horizon = height / 2 + math.tan(math.radians(pitch)) / math.tan(math.radians(CAB_FOV / 2)) * height / 2
        below = min(height - 20, max(0, int(horizon + height / 10)))
        image = load(f'p9-cab-{name}-{shot}')
        pixels = list(image.crop((left, top + below, left + width, top + height)).getdata())
        worst = max(worst, sum(1 for p in pixels if all(abs(c - f) <= 3 for c, f in zip(p, FOG))) / len(pixels))
    result[f'big_{name}_sky_lower'] = worst
    # Aircraft fly out over the edge of the map, where there is no ground to see.
    assert worst == 0 or name == 'aircraft', result

for kind in ('gpu', 'kept', 'instance'):
    frames = [(v, int(d), int(n)) for v, d, n, p in re.findall(rf'{kind}-reference valid=(\w+) differing=(\d+) pixels=(\d+) perspective=(\w+)', log) if p == 'true']
    assert all(v == 'true' for v, _, _ in frames), kind
    result[f'{kind}_references'] = len(frames)
    result[f'max_{kind}_differing'] = max((d / n for _, d, n in frames), default=0)
assert result['gpu_references'] >= 10 and result['max_gpu_differing'] < .005, result
assert result['max_kept_differing'] < .0005 and result['max_instance_differing'] < .005, result
(folder / 'check-results.json').write_text(json.dumps(result, indent=1))
print(json.dumps(result, indent=1))
