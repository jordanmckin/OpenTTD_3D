"""Check the Phase 8.3 ground gate run: textured ground active, dirty/mesh/GPU references clean,
pick and height audits unchanged, every capture present and textured ground visibly different
from the flat fallback."""
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

folder = Path(sys.argv[1])
scene = sys.argv[2] if len(sys.argv) > 2 else 'town'
log = (folder / 'stderr.log').read_text(errors='replace')
assert not re.search(r'3D proof failed|3D proof OpenGL error|Assertion failed|Your script made an error|unavailable \(OpenGL error', log)
assert '3D ground: textured' in log, 'ground textures were not created'

dirty = [int(x) for x in re.findall(r'dirty-reference missed_chunks=(\d+)', log)]
assert len(dirty) > 20 and max(dirty) == 0, (len(dirty), max(dirty, default=-1))
assert 'PHASE7 missed tile' not in log, 'a ground or tile change was not invalidated'
meshes = [(int(n), int(m)) for n, m in re.findall(r'mesh-reference chunks=(\d+) mismatches=(\d+)', log)]
assert meshes and all(m == 0 for _, m in meshes), meshes[-10:]
gpu = [(v, int(d), int(n)) for v, d, n in re.findall(r'gpu-reference valid=(\w+) differing=(\d+) pixels=(\d+)', log)]
assert len(gpu) > 5 and all(v == 'true' for v, _, _ in gpu), len(gpu)
worst_gpu = max(d / n for _, d, n in gpu)
assert worst_gpu < .005, worst_gpu

check = re.search(r'3D CHECK: heights=(\d+) failures=(\d+); interior classic picks=(\d+) failures=(\d+)', log)
assert check and int(check[2]) == 0 and int(check[4]) == 0 and int(check[3]) > 0, check and check.group(0)
if scene == 'town':
	audit = re.search(r'PHASE4 AUDIT .* height_checks=(\d+) failures=(\d+)', log)
	assert audit and int(audit[2]) == 0, audit and audit.group(0)

names = {
	'town': ['town', 'town-flat', 'mine', 'power', 'railway', 'closeup', 'overview', 'orbit', 'transparent', 'classic', 'restored'],
	'farm': ['farm', 'farm-flat', 'farm-closeup', 'rocks', 'farm-orbit', 'farm-classic', 'farm-restored'],
}[scene]
shots = {n: Image.open(folder / 'screenshot' / f'phase8-ground-{n}.bmp').convert('RGB') for n in names}


def difference(a, b):
	"""Mean absolute per-channel difference, 0-255."""
	return sum(ImageStat.Stat(ImageChops.difference(shots[a], shots[b])).mean) / 3


textured_vs_flat = difference(names[0], names[1])
assert textured_vs_flat > 2, textured_vs_flat
classic_vs_3d = difference(names[-2], names[-1])
assert classic_vs_3d > 5, classic_vs_3d
layers = dict(re.findall(r'PHASE8 GROUND layer=(\w+) tiles=(\d+)', log))
if scene == 'farm':
	assert all(f'field_{k}' in layers for k in range(9)) and 'rocks' in layers, layers
print(f'PHASE8 GROUND OK gpu_worst={worst_gpu:.5f} dirty_checks={len(dirty)} mesh_checks={sum(n for n, _ in meshes)} '
	f'picks={check[3]} heights={check[1]} textured_vs_flat={textured_vs_flat:.1f} classic_vs_3d={classic_vs_3d:.1f} '
	f'layers={layers}')
