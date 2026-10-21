"""Compare dirty snapshots and same-state CPU/GPU rasterization references."""
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from PIL import Image

folder = Path(sys.argv[1])
log = (folder / 'stderr.log').read_text(errors='replace')
if folder.name.endswith('construction'):
    assert 'PHASE4 ROUTE_READY' in log
if folder.name.endswith('railway'):
    assert log.count('PHASE4 RELOADED') >= 2
    assert re.search(r'terrain raise 32,32: command accepted=true north height 1 -> 2', log)
    assert re.search(r'terrain lower 32,32: command accepted=true north height 2 -> 1', log)
assert not re.search(r'3D proof failed|3D proof OpenGL error|Assertion failed|Your script made an error|Fixture failed', log)
if (folder/'roam-tile.txt').exists() and int((folder/'roam-tile.txt').read_text()) > 0:
    far = int((folder/'roam-tile.txt').read_text())
    edits = re.findall(rf'terrain (raise|lower) {far},{far}: command accepted=(\w+)', log)
    assert edits == [('raise','true'),('lower','true'),('raise','true'),('lower','true')], edits
    assert re.search(r'3D screen pick 640,450 -> tile \d+,\d+', log), 'Missing rotated re-entry pick'
    assert (folder/'screenshot/phase7-reentry.bmp').is_file()
dirty = [int(x) for x in re.findall(r'dirty-reference missed_chunks=(\d+)', log)]
assert len(dirty) > 20 and max(dirty) == 0, (len(dirty), max(dirty, default=-1))
meshes = [(int(n), int(m)) for n, m in re.findall(r'mesh-reference chunks=(\d+) mismatches=(\d+)', log)]
assert meshes and sum(n for n, _ in meshes) > 20 and all(m == 0 for _, m in meshes), meshes[-10:]
bounds = [(int(n), int(m)) for n, m in re.findall(r'bounds-reference chunks=(\d+) failures=(\d+)', log)]
if bounds:
    assert sum(n for n, _ in bounds) > 20 and all(m == 0 for _, m in bounds), bounds[-10:]
frames = re.findall(r'gpu-reference valid=(\w+) differing=(\d+) pixels=(\d+)', log)
assert len(frames) > 20
assert all(v == 'true' for v, _, _ in frames)
# CPU/GPU float arithmetic may choose different edge pixels; bound substantial colour differences.
ratios = [int(d) / int(n) for _, d, n in frames]
assert max(ratios) < .005, max(ratios)
# Images kept through scoped invalidation (priority 7) must still match a fresh render of the same view.
kept = re.findall(r'kept-reference valid=(\w+) differing=(\d+) pixels=(\d+)', log)
assert len(kept) > 5 and all(v == 'true' for v, _, _ in kept), len(kept)
kept_ratios = [int(d) / int(n) for _, d, n in kept]
assert max(kept_ratios) < .0005, max(kept_ratios)
# Model batches must match the previous per-instance uniform path, including overlap and stippling.
instances = re.findall(r'instance-reference valid=(\w+) differing=(\d+) pixels=(\d+)', log)
assert len(instances) > 20 and all(v == 'true' and int(d) == 0 for v, d, _ in instances), instances[-10:]
timestamp = (folder/'started.txt').read_text().strip().replace('Z', '+00:00')
timestamp = re.sub(r'(\.\d{6})\d+', r'\1', timestamp)
started = datetime.fromisoformat(timestamp).timestamp()
captures = ['phase7-final', 'phase7-reloaded', 'phase7-restored']
focused_lod = (folder/'lod-focused.txt').exists() and (folder/'lod-focused.txt').read_text().strip() == 'on'
if focused_lod:
    captures = ['phase7-final', 'phase7-reloaded', 'phase7-lod-uniform']
for name in captures:
    path = folder/'screenshot'/f'{name}.bmp'
    assert path.stat().st_mtime >= started, path
    image = Image.open(path).convert('RGB')
    # Below the management windows, the main viewport must contain real world
    # geometry. Comparing two empty images alone cannot establish correctness.
    if focused_lod:
        # At zoom 4 the whole 64-square map sits in the centre of the screen;
        # the bottom strip is legitimately background. Inspect the main view
        # to the right of the secondary window, retaining the same 20% gate.
        crop = image.crop((int(image.width*.45), int(image.height*.25), int(image.width*.90), int(image.height*.70)))
    else:
        crop = image.crop((0, int(image.height*.60), image.width, int(image.height*.95)))
    pixels = crop.get_flattened_data() if hasattr(crop, 'get_flattened_data') else crop.getdata()
    occupied = sum(max(abs(r-26), abs(g-43), abs(b-59)) > 5 for r, g, b in pixels)
    assert occupied / (crop.width*crop.height) > .20, (name, occupied)
result = dict(instance_comparisons=len(instances), max_instance_differing_pixels=max(int(d) for _, d, _ in instances), dirty_comparisons=len(dirty), missed_chunks=max(dirty), mesh_comparisons=sum(n for n, _ in meshes), mesh_mismatches=max(m for _, m in meshes), image_comparisons=len(frames), max_differing_pixel_fraction=max(ratios), kept_comparisons=len(kept), max_kept_differing_fraction=max(kept_ratios))
if (folder/'lod-requested.txt').exists() and (folder/'lod-requested.txt').read_text().strip() == 'on':
    lod_views = [int(n) for n in re.findall(r'PHASE7 lod-view reduced=(\d+)', log)]
    assert sum(n > 0 for n in lod_views) > 20, 'Need live renders with actual reduced models'
    assert 0 in lod_views, 'Need full-detail close views alongside distant views'
    assert 'PHASE7 lod enabled=false' in log, 'Need runtime switching back to full detail'
    assert (folder/'screenshot/phase7-lod-uniform.bmp').is_file(), 'Need uniform fallback with LOD'
    result.update(lod_views=len(lod_views), reduced_lod_views=sum(n > 0 for n in lod_views), max_reduced_instances=max(lod_views))
if (folder/'static-requested.txt').exists() and (folder/'static-requested.txt').read_text().strip() == 'on':
    assert 'PHASE7 static-sharing enabled=false' in log and 'PHASE7 static-sharing enabled=true' in log
    for name in ('uniform', 'baked', 'shared'):
        assert (folder/'screenshot'/f'phase7-static-{name}.bmp').is_file()
    static_views = [int(n) for n in re.findall(r'PHASE7 static-view instances=(\d+)', log)]
    assert sum(n > 0 for n in static_views) > 20
    result.update(static_runtime_switching=True, static_views=len(static_views), max_static_instances=max(static_views))
if bounds:
    result.update(bounds_comparisons=sum(n for n, _ in bounds), bounds_failures=max(m for _, m in bounds))
if (folder/'streams-requested.txt').exists():
    assert 'PHASE7 retained-streams enabled=false' in log and 'PHASE7 retained-streams enabled=true' in log
    streams = re.findall(r'PHASE7 stream-view rebuild=(\w+) patched=(\w+) bytes=(\d+) entries=(\d+)', log)
    assert len(streams) > 20
    assert all(int(b) <= 32 * 1024**2 and int(n) <= 16 for _, _, b, n in streams)
    assert any(r == 'false' for r, _, _, _ in streams), 'Need reused streams'
    assert any(p == 'true' for _, p, _, _ in streams), 'Need live model-range patches'
    if folder.name.endswith('railway'):
        assert re.search(r'terrain raise 20,25: command accepted=true', log)
        assert re.search(r'terrain lower 20,25: command accepted=true', log)
    for name in ('phase7-streamed', 'phase7-retained-stream'):
        assert (folder/'screenshot'/f'{name}.bmp').is_file()
    result.update(stream_views=len(streams), stream_reuses=sum(r == 'false' for r, _, _, _ in streams),
                  stream_patches=sum(p == 'true' for _, p, _, _ in streams), stream_max_bytes=max(int(b) for _, _, b, _ in streams))
print(json.dumps(result, indent=2))
(folder/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
