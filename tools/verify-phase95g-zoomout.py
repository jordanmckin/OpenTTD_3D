"""Phase 9.5g: zoomed-out management-view costs on fresh seeded maps, LOD off.

Reports presented frame intervals, CPU work, 3D draw work, GPU time, mesh preparation,
uploads, residency and evictions for the timed interval, plus the cold start before it.
Readback must be absent from timed runs; --compare prints the change against a baseline tag.
"""
import json
import re
import sys
from pathlib import Path
from statistics import mean, median

root = Path(__file__).resolve().parents[1]
tag = sys.argv[1]
baseline = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == '--compare' else None


def values(line):
    return {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)}


def percentile(items, fraction):
    return sorted(items)[int((len(items) - 1) * fraction)]


rows = []
for folder in sorted((root / '.runtime').glob(f'{tag}-*')):
    if not (folder / 'measurement.json').exists():
        continue
    meta = json.loads((folder / 'measurement.json').read_text(encoding='utf-8-sig'))
    raw = (folder / 'stderr.log').read_bytes()
    log = raw.decode(errors='replace')
    assert not re.search(r'3D proof failed|3D proof OpenGL error|Assertion failed', log), folder
    assert not meta['lod'], 'Phase 9.5g uses full detail'
    lines = raw[meta['offset']:].decode(errors='replace').splitlines()[1:-1]
    frames = [values(line) for line in lines if 'PHASE7 frame ' in line]
    presents = [values(line) for line in lines if 'PHASE7 present ' in line]
    geometry = [values(line) for line in lines if 'PHASE7 geometry ' in line]
    # A paused, unchanged view may present for the whole interval without drawing any 3D.
    assert len(presents) >= 5 and (len(frames) >= 5 or meta['paused']), (folder, len(frames), len(presents))
    assert all(f['read_us'] == 0 for f in frames) or meta['verify_gpu'], folder
    assert all(f['lod_instances'] == 0 and f['model_triangles'] == f['full_model_triangles'] for f in frames), folder
    # Cold start: everything before the timed offset, from the first 3D view render.
    cold = [values(line) for line in raw[:meta['offset']].decode(errors='replace').splitlines() if 'PHASE7 view ' in line]
    row = {k: meta[k] for k in ('case', 'map', 'camera', 'zoom', 'motion', 'paused', 'resolution', 'shadows')}
    row['samples'] = len(presents)
    row['working_set_mib'] = round(meta['peak_bytes'] / 2**20, 1)
    intervals = [p['interval_us'] for p in presents if p['interval_us'] > 0]
    for label, data in [('frame', intervals), ('work', [p['work_us'] for p in presents]), ('draw', [f['draw_us'] for f in frames] or [0])]:
        row[f'median_{label}_ms'] = round(median(data) / 1000, 2)
        row[f'p95_{label}_ms'] = round(percentile(data, .95) / 1000, 2)
    row['fps'] = round(1e6 / mean(intervals), 1)
    rendered = [f for f in frames if f['renders'] > 0]
    row['renders_per_s'] = round(sum(f['renders'] for f in frames) / (sum(intervals) / 1e6), 1)
    # Per rendered frame: what one full view render costs.
    for key in ('render_us', 'gpu_ns', 'prepare_us', 'scan_us', 'mesh_us', 'upload_us', 'upload_bytes', 'static_instances', 'static_draws', 'chunks_rebuilt', 'cold_chunks', 'evictions'):
        row[f'per_render_{key}'] = round(mean(f[key] for f in rendered), 1) if rendered else 0
    for key in ('resident_chunks', 'retained_bytes', 'cpu_mesh_bytes'):
        row[f'max_{key}'] = max((f[key] for f in frames), default=0)
    row['visible_chunks'] = max((g['visible'] for g in geometry), default=0)
    row['evictions'] = sum(f['evictions'] for f in frames)
    row['cold_views'] = len(cold)
    row['cold_first_prepare_ms'] = round(cold[0]['prepare_us'] / 1000, 1) if cold else 0
    rows.append(row)
assert rows, tag
(root / f'.runtime/{tag}-results.json').write_text(json.dumps(rows, indent=2) + '\n')
before = {}
if baseline:
    before = {r['case']: r for r in json.loads((root / f'.runtime/{baseline}-results.json').read_text())}
print(f'{tag}: {len(rows)} cases passed')
print(f"  {'case':32} {'fps':>6} {'med frame':>9} {'p95 frame':>9} {'draw':>7} {'gpu ms':>7} {'render/s':>8} {'chunks':>6} {'evict':>6}")
for r in rows:
    gpu = r['per_render_gpu_ns'] / 1e6
    line = f"  {r['case']:32} {r['fps']:6.1f} {r['median_frame_ms']:9.2f} {r['p95_frame_ms']:9.2f} {r['median_draw_ms']:7.2f} {gpu:7.2f} {r['renders_per_s']:8.1f} {r['visible_chunks']:6} {r['evictions']:6}"
    if r['case'] in before:
        b = before[r['case']]
        line += f"   was {b['fps']:.1f} fps / {b['median_frame_ms']:.2f} ms"
    print(line)
