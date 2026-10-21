"""Phase 9.5: tunnel fades, snapping back to normal, and riding through the edge cases of each vehicle type."""
import json
import math
import re
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

folder = Path(sys.argv[1])
save = sys.argv[2]
log = (folder / 'stderr.log').read_text(errors='replace')
assert not re.search(r'3D proof failed|3D proof OpenGL error|Assertion failed|Your script made an error|Fixture failed', log)
TICK_STEP = 8  # CHASE_TICK_STEP in terrain3d_math.h: further than this a tick is a jump, which a cab cuts to.
TURN_RATE = 240  # CAB_TIMING.turn_rate and CHASE_TURN_RATE in terrain3d_math.h, degrees a second.
FADE_IN, FADE_OUT, FADE_DISTANCE = 0.4, 0.2, 8  # TUNNEL_FADE_* in terrain3d_math.h
result = {}


def floats(text):
    return [float(v) for v in text.split(',')]


# Every cab and chase camera update, in order.
updates = re.findall(r'PHASE9 CHASE vehicle=(\d+) type=(\d+) tile_type=(\d+) ground=(-?\d+) ms=(\d+) target=(\S+) smooth=(\S+) eye=(\S+) pitch=(\S+) camera=(\w+) grade=(\S+) dark=(\S+) inside=(\w+) to_go=(\S+) state=(-?\d+),(-?\d+)', log)
tracks = {}
for vehicle, kind, tile_type, ground, ms, target, smooth, eye, pitch, camera, grade, dark, inside, to_go, state, detail in updates:
    tracks.setdefault(int(vehicle), []).append({'kind': int(kind), 'tile_type': int(tile_type), 'ground': int(ground), 'ms': int(ms), 'target': floats(target), 'smooth': floats(smooth),
                                                 'eye': floats(eye), 'camera': camera, 'dark': float(dark), 'inside': inside == 'true', 'to_go': float(to_go), 'state': int(state), 'detail': int(detail)})
events = [(int(v), e, float(d)) for v, e, d in re.findall(r'PHASE9 EVENT vehicle=(\d+) event=(\w+) dark=(\S+) tick=\d+', log)]
rides = re.findall(r'PHASE9 RIDE vehicle=(\d+) action=(\w+) ok=(\w+)', log)
for vehicle, action, ok in rides:
    assert ok == 'true', (vehicle, action)
result['rides'] = [f'{v} {a}' for v, a, _ in rides]
result['events'] = sorted({f'{v} {e}' for v, e, _ in events})
result['max_frame_ms'] = max((u['ms'] for t in tracks.values() for u in t), default=0)
views = re.findall(r'PHASE9 VIEW vehicle=(\d+) camera=(\w+) viewport=(-?\d+),(-?\d+),(\d+),(\d+)', log)
rects = {}
for vehicle, _, left, top, width, height in views:
    rects.setdefault(int(vehicle), (int(left), int(top), int(left) + int(width), int(top) + int(height)))


def load(name):
    return Image.open(folder / 'screenshot' / f'{name}.bmp').convert('RGB')


def inside_view(image, vehicle):
    """The vehicle window's view, without the corner label."""
    left, top, right, bottom = rects[vehicle]
    view = image.crop((left, top, right, bottom)).copy()
    view.paste((0, 0, 0), (0, view.height - 16, 90, view.height))
    return view


def black_fraction(view):
    return sum(1 for p in view.getdata() if max(p) <= 8) / (view.width * view.height)


def brightness(view):
    return sum(ImageStat.Stat(view.convert('L')).mean)


def differing(a, b):
    diff = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v > 6 else 0)
    return sum(1 for d in diff.getdata() if d) / (a.width * a.height)


def ride(track, name):
    """Turn rate and how far the eye moves beyond the vehicle per frame, outside jumps and stalled frames."""
    stats = {'updates': len(track), 'cuts': 0, 'max_turn_rate_excess': 0, 'max_excess': 0}
    for i in range(1, len(track)):
        u, p = track[i], track[i - 1]
        step = math.dist(u['target'][:3], p['target'][:3])
        if u['ms'] > 100:
            continue
        if step > TICK_STEP + 1:
            stats['cuts'] += 1
            continue
        nearby = max(math.dist(track[j]['target'][:3], track[j - 1]['target'][:3]) for j in range(max(1, i - 2), min(len(track), i + 3)))
        stats['max_turn_rate_excess'] = max(stats['max_turn_rate_excess'], abs(math.remainder(u['smooth'][3] - p['smooth'][3], 360)) - TURN_RATE * u['ms'] / 1000)
        stats['max_excess'] = max(stats['max_excess'], math.dist(u['eye'], p['eye']) - nearby)
    assert stats['max_turn_rate_excess'] <= .05 and stats['max_excess'] <= 3, (name, stats)
    return {k: round(v, 2) for k, v in stats.items()}


def tunnel_fades(vehicle):
    """Every passage: black on the way in by the time the vehicle hides, black throughout, and a fade back in that is
    seen (not skipped) and over in time. Away from tunnels the view is clear."""
    track = tracks[vehicle]
    passages, fade_ins, worst_in_step = 0, [], 0
    since_inside = None  # Seconds since the vehicle came out, while fading back in.
    for i, u in enumerate(track):
        seconds = min(u['ms'], 100) / 1000
        if u['inside']:
            if i == 0 or not track[i - 1]['inside']:
                passages += 1
                straight = i > 0 and track[i - 1]['to_go'] >= 0
                # Vehicles move a whole unit or more a tick, so a chase view (eye on the vehicle) is a step short of black.
                assert not straight or u['dark'] >= 1 - 2 / FADE_DISTANCE, (vehicle, i, u)
            if not (u['dark'] == 1 or u['dark'] >= track[i - 1]['dark'] + seconds / FADE_OUT - .001):
                raise AssertionError((vehicle, 'not black in the tunnel', i, u))
            since_inside = 0
            continue
        if since_inside is not None:
            since_inside += seconds  # Fade time: a stalled frame (the event screenshots) counts as at most 0.1 s.
            step = track[i - 1]['dark'] - u['dark']
            worst_in_step = max(worst_in_step, step - seconds / FADE_IN)
            if u['dark'] == 0:
                fade_ins.append(since_inside)
                since_inside = None
            continue
        if u['to_go'] >= 0:
            assert u['dark'] >= max(0, 1 - u['to_go'] / FADE_DISTANCE) - .001, (vehicle, i, u)
        else:
            assert u['dark'] == 0, (vehicle, 'dark away from tunnels', i, u)
    assert passages >= 1 and len(fade_ins) >= 1, (vehicle, passages, fade_ins)
    assert worst_in_step <= .001 and min(fade_ins) >= FADE_IN * .75 and max(fade_ins) <= FADE_IN + .5, (vehicle, worst_in_step, fade_ins)
    return {'passages': passages, 'fade_in_seconds': [round(s, 2) for s in fade_ins]}


def fade_shots(vehicle, prefix):
    shots = {e: inside_view(load(f'{prefix}-{e}'), vehicle) for e in ('entering', 'black', 'leaving', 'clear')}
    out = {f'{e}_black': round(black_fraction(v), 3) for e, v in shots.items()}
    out.update({f'{e}_brightness': round(brightness(v), 1) for e, v in shots.items()})
    assert out['black_black'] > .97 and out['clear_black'] < .2, out
    assert out['entering_black'] < .97 and out['entering_brightness'] < out['clear_brightness'], out
    assert out['leaving_black'] < .97 and out['leaving_brightness'] < out['clear_brightness'], out
    return out


def snapped(vehicle, reason):
    lines = re.findall(rf'PHASE9 SNAPBACK vehicle={vehicle} camera=\w+ crashed=(\w+) depot=(\w+)', log)
    assert any((reason == 'crash' and c == 'true') or (reason == 'depot' and d == 'true') for c, d in lines), (vehicle, reason, lines)
    return len(lines)


if save == 'Railway':
    TRAIN, TUNNEL_TRUCK, CHASE_TRUCK, TURN_TRUCK, FRONT, BEHIND = 3, 0, 1, 2, 12, 15
    result['fades'] = {v: tunnel_fades(v) for v in (TRAIN, TUNNEL_TRUCK, CHASE_TRUCK)}
    result['fade_shots'] = {v: fade_shots(v, f'p95-tunnel-{v}') for v in (TRAIN, TUNNEL_TRUCK, CHASE_TRUCK)}
    result['ride'] = {v: ride(t, v) for v, t in tracks.items()}
    # Trains reverse: the cab cuts to the other end, facing the other way.
    assert result['ride'][TRAIN]['cuts'] >= 1, result['ride'][TRAIN]
    result['reverse_differing'] = differing(inside_view(load('p95-reverse-before'), TRAIN), inside_view(load('p95-reverse-after'), TRAIN))
    assert result['reverse_differing'] > .2, result
    # Road vehicles: turning round at the road ends and on command, and overtaking a stopped truck.
    assert f'{FRONT} turning' in result['events'] and f'{BEHIND} overtaking' in result['events'], result['events']
    overtaking = [u for u in tracks[BEHIND] if u['detail'] != 0]
    result['overtaking_updates'] = len(overtaking)
    assert len(overtaking) > 30, result
    turns = [u for t in (tracks[FRONT], tracks[BEHIND]) for u in t if (u['state'] & 0x07) >= 6 and u['state'] < 0x20]
    result['turning_updates'] = len(turns)
    assert len(turns) > 30, result
    for name in ('p95-turning-end', 'p95-overtaking', 'p95-overtaking-passing'):
        assert (folder / 'screenshot' / f'{name}.bmp').exists(), name
    # Exits: the depot (twice: on its own way through and when sent), a crash seen by its window and an extra viewport.
    result['depot_snapbacks'] = snapped(TUNNEL_TRUCK, 'depot')
    result['crash_snapbacks'] = snapped(CHASE_TRUCK, 'crash')
    assert result['crash_snapbacks'] == 2, result
    for name in ('p95-depot-snapback', 'p95-crash-before', 'p95-crash-snapback'):
        load(name)
    result['crash_snapback_differing'] = differing(inside_view(load('p95-crash-before'), CHASE_TRUCK), inside_view(load('p95-crash-snapback'), CHASE_TRUCK))
    # Each `views` logs window views (VIEW) then any other view still naming a vehicle (OTHERVIEW).
    chunks = re.split(r'(?=PHASE9 VIEW vehicle=3 )', log)
    last = chunks[-1]
    after_crash = [c for c in chunks if f'OTHERVIEW class=' in c]
    assert after_crash and re.search(rf'OTHERVIEW class=\d+ vehicle={CHASE_TRUCK} valid=true camera=normal', after_crash[0]), after_crash[:1]
    assert re.search(rf'PHASE9 VIEW vehicle={CHASE_TRUCK} camera=normal', after_crash[0]), 'crashed truck window not back to normal'
    assert re.search(rf'PHASE9 VIEW vehicle={TUNNEL_TRUCK} camera=normal', chunks[-2]) or re.search(rf'PHASE9 VIEW vehicle={TUNNEL_TRUCK} camera=normal', chunks[-3]), 'depot truck not back to normal'
    # Sold, and the crashed truck cleared away: their windows closed and no view names either any more.
    assert not re.search(rf'PHASE9 (VIEW|OTHERVIEW class=\d+) vehicle=({TUNNEL_TRUCK}|{CHASE_TRUCK}) ', last), last
    result['last_views'] = re.findall(r'PHASE9 (?:VIEW|OTHERVIEW) \S+ \S+', last)
else:
    PLANE, PLANE_CHASE, HELI, HELI_CHASE = 2, 4, 8, 11
    for v, wanted in ((PLANE, ('takeoff', 'landing')), (HELI, ('helitakeoff', 'helilanding'))):
        for e in wanted:
            assert f'{v} {e}' in result['events'], (v, e, result['events'])
    assert any(e == 'holding' for _, e, _ in events), result['events']
    result['ride'] = {v: ride(t, v) for v, t in tracks.items()}
    result['altitude'] = {v: [min(u['target'][2] for u in t), max(u['target'][2] for u in t)] for v, t in tracks.items()}
    for v in (PLANE, PLANE_CHASE, HELI, HELI_CHASE):
        low, high = result['altitude'][v]
        assert high - low > 40, (v, low, high)
        assert all(u['dark'] == 0 for u in tracks[v]), v
    result['hangar_snapbacks'] = snapped(PLANE, 'depot')
    shots = ['p95-air-plane-takeoff', 'p95-air-plane-takeoff-later', 'p95-air-plane-landing', 'p95-air-plane-landing-later', 'p95-air-heli-helitakeoff',
             'p95-air-heli-helitakeoff-later', 'p95-air-heli-helilanding', 'p95-air-heli-helilanding-later', 'p95-air-holding', 'p95-air-holding-later', 'p95-air-hangar-snapback']
    for name in shots:
        load(name)
    last = re.split(r'(?=PHASE9 VIEW vehicle=)', log)
    assert re.search(rf'PHASE9 VIEW vehicle={PLANE} camera=normal', log[log.rfind('PHASE9 SNAPBACK'):]), 'plane not back to normal after the hangar'

for kind in ('gpu', 'kept', 'instance'):
    frames = [(v, int(d), int(n)) for v, d, n, p in re.findall(rf'{kind}-reference valid=(\w+) differing=(\d+) pixels=(\d+) perspective=(\w+)', log) if p == 'true']
    assert all(v == 'true' for v, _, _ in frames), kind
    result[f'{kind}_references'] = len(frames)
    result[f'max_{kind}_differing'] = max((d / n for _, d, n in frames), default=0)
    result[f'{kind}_references_over_0.05%'] = sum(1 for _, d, n in frames if d / n > .0005)
# Air: close to the eye at the city airport, the thin radar and lattice towers and light poles come out a pixel apart along
# their edges between the two paths (single-pixel slivers, up to 2.5% of a small view); the railway views match.
assert result['gpu_references'] >= 10 and result['max_gpu_differing'] < (.03 if save == 'Air' else .005), result
assert result['max_kept_differing'] < .0005 and result['max_instance_differing'] < .005, result
(folder / 'check-results.json').write_text(json.dumps(result, indent=1, default=str))
print(json.dumps(result, indent=1, default=str))
