"""Phase 9.6: actual steady-state frame and draw costs, excluding initialization.

GPU references are an optional separate correctness run; their synchronous readback
costs must not be reported as performance measurements.
"""
import json
import re
import sys
from pathlib import Path
from statistics import mean

root = Path(__file__).resolve().parents[1]
tag = sys.argv[1]
rows = []


def values(line):
    return {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)}


def percentile(items, fraction):
    return sorted(items)[int((len(items) - 1) * fraction)]


for folder in sorted((root / '.runtime').glob(f'{tag}-*')):
    if not (folder / 'measurement.json').exists():
        continue
    meta = json.loads((folder / 'measurement.json').read_text(encoding='utf-8-sig'))
    raw = (folder / 'stderr.log').read_bytes()
    log = raw.decode(errors='replace')
    assert not re.search(r'3D proof failed|3D proof OpenGL error|Assertion failed|Your script made an error|Fixture failed', log), folder
    assert 'PHASE7 FLEET_RELOADED' in log, folder
    measured = raw[meta['offset']:].decode(errors='replace').splitlines()[1:-1]
    frames = [values(line) for line in measured if 'PHASE7 frame ' in line]
    presents = [values(line) for line in measured if 'PHASE7 present ' in line]
    streams = [values(line) for line in measured if 'PHASE7 streams ' in line]
    # CPU reference expansion/readback can take seconds; correctness runs need completed
    # comparisons, not the steady-state performance sample count used by timed runs.
    minimum = 1 if meta['verify_gpu'] else 15
    assert len(frames) >= minimum and len(presents) >= minimum, (folder, len(frames), len(presents))
    assert all(f['read_us'] == 0 for f in frames) or meta['verify_gpu'], folder
    assert all(f['model_triangles'] <= f['full_model_triangles'] for f in frames), folder
    assert all(s['stream_entries'] <= 16 and s['stream_retained_bytes'] <= 32 * 1024**2 for s in streams), folder
    assert not meta['lod'], 'Phase 9.6 uses full detail'
    assert all(f['lod_instances'] == 0 and f['model_triangles'] == f['full_model_triangles'] for f in frames), folder
    views = re.findall(r'PHASE9 VIEW vehicle=(\d+) camera=(\w+) viewport=(-?\d+),(-?\d+),(\d+),(\d+)', log)
    expected = 0 if meta['case'] == 'closed' else 4 if meta['case'] in ('normal4', 'mixed4', 'mixedlarge') else 1
    # `view` itself logs its cameras, then `views` lists them once more.
    by_vehicle = {v: (camera, int(w), int(h)) for v, camera, _, _, w, h in views}
    if meta['case'] == 'normal4':
        # Normal views have no camera_vehicle override; their logged ID is deliberately invalid.
        by_vehicle = {str(i): (camera, int(w), int(h)) for i, (_, camera, _, _, w, h) in enumerate(views)}
    assert len(by_vehicle) == expected, (folder, by_vehicle)
    if meta['case'].startswith('mixed'):
        assert {v[0] for v in by_vehicle.values()} == {'cab', 'chase'}, by_vehicle
    if meta['case'] in ('cablarge', 'chaselarge', 'town'):
        assert all(w > 1700 and h > 800 for _, w, h in by_vehicle.values()), by_vehicle
    row = dict(case=meta['case'], verify_gpu=meta['verify_gpu'], lod=meta['lod'], samples=len(presents),
               views=list(by_vehicle.values()), working_set_mib=round(meta['peak_bytes'] / 2**20, 1))
    row['shadows'] = meta.get('shadows', 'off')
    if 'auto_visibility' in meta:
        row['auto_visibility'] = meta['auto_visibility']
    if 'camera_yaw' in meta:
        row['camera_yaw'] = meta['camera_yaw']
        row['camera_tilt'] = meta['camera_tilt']
    intervals = [p['interval_us'] for p in presents if p['interval_us'] > 0]
    for label, data in [('frame', intervals), ('work', [p['work_us'] for p in presents]), ('draw', [f['draw_us'] for f in frames])]:
        row[f'mean_{label}_ms'] = round(mean(data) / 1000, 3)
        row[f'p95_{label}_ms'] = round(percentile(data, .95) / 1000, 3)
    row['fps'] = round(1e6 / mean(intervals), 1)
    row['game_ticks_per_s'] = round(sum(p['game_ticks'] for p in presents) / (sum(intervals) / 1e6), 2)
    for key in ('gpu_ns', 'prepare_us', 'render_us', 'scan_us', 'static_instances', 'vehicle_instances', 'model_triangles', 'full_model_triangles', 'lod_instances', 'instance_upload_bytes', 'renders', 'resident_chunks'):
        row[f'mean_{key}'] = round(mean(f.get(key, 0) for f in frames), 2)
    if meta['verify_gpu']:
        for kind in ('gpu', 'kept', 'instance'):
            refs = re.findall(rf'{kind}-reference valid=(\w+) differing=(\d+) pixels=(\d+) perspective=true', log)
            if expected and (refs or kind != 'kept'):
                assert refs and all(v == 'true' for v, _, _ in refs), (folder, kind)
                if kind != 'kept':
                    assert len(refs) >= 2, (folder, kind, len(refs))
                row[f'{kind}_references'] = len(refs)
                row[f'{kind}_max_differing'] = max(int(d) / int(n) for _, d, n in refs)
                assert row[f'{kind}_max_differing'] < .005, (folder, kind, row)
    rows.append(row)
assert rows, tag
(root / f'.runtime/{tag}-results.json').write_text(json.dumps(rows, indent=2) + '\n')
print(f'{tag}: {len(rows)} cases passed')
for row in rows:
    print(f"  {row['case']}: draw {row['mean_draw_ms']:.3f} ms; work {row['mean_work_ms']:.3f} ms; p95 frame {row['p95_frame_ms']:.3f} ms")
