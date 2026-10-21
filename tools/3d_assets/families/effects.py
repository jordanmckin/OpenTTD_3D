"""Phase 8 family script: effect vehicles (effectvehicle.cpp), one model per sprite frame.

Run inside Blender, through the Blender MCP (exec the file and call main(keys)) or headless:
  blender -b -P tools/3d_assets/families/effects.py -- [keys]
The .blend files must exist (python tools/3d_assets/art.py new <key>); then `art.py build <key>`.

Conventions (see rail3d_impl.h, RefreshEffects3D):
- The origin is the effect vehicle's position (x_pos, y_pos, z_pos). Smoke rises by moving its vehicle, so a puff is
  modelled round its origin; plumes that stay put (chimney smoke, breakdown smoke) rise from it.
- The classic plumes lean up and to the right on screen, which is towards world -X.
- Frames follow the sprite sequence: puffs grow, then break up into smaller blobs as the sprite thins out.
- The bulldozer is one model driving along +X, turned by the renderer to the sprite's direction.
Low-poly and opaque: a puff is a few jittered icosahedra (20 triangles each).
"""
import math
import random
import sys
from pathlib import Path

import bpy

BLENDS = Path(__file__).resolve().parents[3] / 'OpenTTD-15.3' / 'OpenTTD-15.3' / 'assets' / '3d' / 'blender' / 'effect' if '__file__' in globals() else None

PHI = (1 + 5 ** 0.5) / 2
ICO_V = [(-1, PHI, 0), (1, PHI, 0), (-1, -PHI, 0), (1, -PHI, 0), (0, -1, PHI), (0, 1, PHI), (0, -1, -PHI), (0, 1, -PHI),
	(PHI, 0, -1), (PHI, 0, 1), (-PHI, 0, -1), (-PHI, 0, 1)]
ICO_F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
	(3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]


class Mesh:
	def __init__(self):
		self.v, self.f, self.m = [], [], []

	def add(self, verts, faces, mat):
		o = len(self.v)
		self.v += verts
		for f in faces:
			self.f.append(tuple(i + o for i in f))
			self.m.append(mat)

	def blob(self, c, r, mat, seed, squash=0.85, jitter=0.18):
		"""A lumpy ball: an icosahedron with its vertices pushed in and out by up to `jitter` of the radius."""
		rnd = random.Random(seed)
		n = math.sqrt(1 + PHI * PHI)
		v = []
		for x, y, z in ICO_V:
			k = r * (1 + rnd.uniform(-jitter, jitter)) / n
			v.append((c[0] + x * k, c[1] + y * k, c[2] + z * k * squash))
		self.add(v, ICO_F, mat)

	def spike(self, c, d, length, w, mat):
		"""A thin three-sided spike from c along unit direction d (sparks, explosion debris)."""
		ax = (0, 0, 1) if abs(d[2]) < 0.9 else (1, 0, 0)
		u = (d[1] * ax[2] - d[2] * ax[1], d[2] * ax[0] - d[0] * ax[2], d[0] * ax[1] - d[1] * ax[0])
		ul = math.sqrt(sum(a * a for a in u))
		u = tuple(a / ul for a in u)
		t = (d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0])
		base = [tuple(c[i] + w * (math.cos(a) * u[i] + math.sin(a) * t[i]) for i in range(3)) for a in (0, 2.094, 4.189)]
		tip = tuple(c[i] + d[i] * length for i in range(3))
		self.add(base + [tip], [(0, 1, 3), (1, 2, 3), (2, 0, 3), (2, 1, 0)], mat)


def unit(rnd, up=0.0):
	"""Random direction, biased upwards by `up`."""
	z = rnd.uniform(-1 + up, 1)
	a = rnd.uniform(0, 2 * math.pi)
	s = math.sqrt(1 - z * z)
	return (s * math.cos(a), s * math.sin(a), z)


def puff(frame, frames, r0, r1, mats, seed, blobs=4, spread=0.6, break_at=0.6):
	"""A smoke puff growing from r0 to r1; from break_at on it parts into smaller blobs that drift apart."""
	mesh = Mesh()
	t = frame / max(1, frames - 1)
	r = r0 + (r1 - r0) * min(1.0, t / break_at)
	part = max(0.0, (t - break_at) / (1 - break_at))
	rnd = random.Random(seed)
	for k in range(blobs):
		d = unit(rnd, 0.2)
		off = r * spread * (0.4 + 1.2 * part)
		c = (d[0] * off, d[1] * off, d[2] * off * 0.7)
		size = r * (0.75 if k else 1.0) * (1 - 0.55 * part)
		mesh.blob(c, size, mats[min(len(mats) - 1, int(part * len(mats)))] if k else mats[0], seed * 31 + k)
	return mesh


def plume(frame, frames, blobs, rise, drift, r0, r1, mat, seed, wobble=1.0):
	"""A plume rising from the origin and leaning towards -X; blobs ride up it one frame step at a time and loop."""
	mesh = Mesh()
	for k in range(blobs):
		t = (k + frame / frames) / blobs
		rnd = random.Random(seed * 97 + k)
		c = (-drift * t ** 1.3 + rnd.uniform(-wobble, wobble) * t, rnd.uniform(-wobble, wobble) * t, rise * t)
		mesh.blob(c, r0 + (r1 - r0) * t, mat, seed * 13 + k)
	return mesh


def spark(frame, frames, seed):
	"""Blue sparks from an electric engine's pantograph: a bright knot that scatters into short spikes."""
	mesh = Mesh()
	t = frame / max(1, frames - 1)
	rnd = random.Random(seed)
	if t < 0.5:
		mesh.blob((0, 0, 0), 0.5 + 1.2 * t, 'spark_blue', seed, jitter=0.35)
	for k in range(4 + frame):
		d = unit(rnd, 0.1)
		off = 0.6 + 3.5 * t
		mesh.spike(tuple(a * off for a in d), d, 0.9 + 0.6 * t, 0.12, 'spark_blue' if k % 3 else 'plaster_white')
	return mesh


def explosion(frame, frames, size, seed):
	"""A fireball: a yellow core inside orange lobes, then scattered orange and red bits as it burns out."""
	mesh = Mesh()
	t = frame / max(1, frames - 1)
	rnd = random.Random(seed)
	r = size * (0.55 + 0.45 * min(1.0, t * 4))
	fade = max(0.0, (t - 0.25) / 0.75)
	if fade < 0.5:
		mesh.blob((0, 0, r * 0.45), r * 0.85 * (1 - fade), 'flame_yellow', seed, jitter=0.25)
	lobes = 6
	for k in range(lobes):
		d = unit(rnd, 0.3)
		off = r * (0.6 + 0.9 * fade)
		c = (d[0] * off, d[1] * off, r * 0.3 + d[2] * off + 2.0 * fade * size / 4)
		mat = 'flame_orange' if fade < 0.6 or k % 2 else 'flame_red'
		mesh.blob(c, r * 0.45 * (1 - 0.7 * fade), mat, seed * 7 + k, jitter=0.25)
	for k in range(int(8 * fade)):
		d = unit(rnd, 0.0)
		off = r * (0.8 + 0.8 * fade)
		mesh.blob((d[0] * off, d[1] * off, r * 0.3 + d[2] * off), size * 0.12, 'flame_orange' if k % 2 else 'flame_red', seed * 3 + k, jitter=0.1)
	return mesh


def bulldozer():
	"""A small yellow roadworks bulldozer driving along +X, blade at the front."""
	mesh = Mesh()
	box = lambda x0, y0, z0, x1, y1, z1, mat: mesh.add(
		[(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
		[(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)
	for y in (-1.9, 1.0):
		box(-2.6, y, 0.3, 2.0, y + 0.9, 1.4, 'rubber')
	box(-2.4, -1.1, 0.9, 1.6, 1.1, 2.6, 'hazard_yellow')
	box(-2.4, -1.0, 2.6, -0.4, 1.0, 4.6, 'hazard_yellow')
	box(-2.3, -0.9, 3.0, -0.5, 0.9, 4.2, 'glass_dark')
	box(-2.5, -1.1, 4.6, -0.3, 1.1, 4.9, 'black')
	box(0.6, -0.3, 2.6, 1.0, 0.1, 3.6, 'black')  # exhaust
	box(2.0, -2.3, 0.3, 2.5, 2.3, 2.2, 'steel')
	box(1.6, -1.6, 0.8, 2.0, -1.2, 1.4, 'steel')
	box(1.6, 1.2, 0.8, 2.0, 1.6, 1.4, 'steel')
	return mesh


# key -> (frames, builder(frame)); the states are frame_<n>, or default for the bulldozer.
EFFECTS = {
	'effect_chimney_smoke': (8, lambda f: plume(f, 8, 9, 30, 16, 1.6, 4.2, 'smoke_white', 1, wobble=1.5)),
	'effect_steam_smoke': (5, lambda f: puff(f, 5, 1.2, 3.0, ['smoke_white'], 2)),
	'effect_diesel_smoke': (6, lambda f: puff(f, 6, 0.5, 1.6, ['smoke_brown', 'smoke_grey'], 3, blobs=3)),
	'effect_electric_spark': (6, lambda f: spark(f, 6, 4)),
	'effect_smoke': (5, lambda f: puff(f, 5, 1.4, 3.6, ['smoke_grey', 'smoke_black'], 5, break_at=0.4)),
	'effect_explosion_large': (16, lambda f: explosion(f, 16, 7.0, 6)),
	'effect_breakdown_smoke': (4, lambda f: plume(f, 4, 6, 16, 7, 1.0, 2.4, 'smoke_black', 7, wobble=0.8)),
	'effect_explosion_small': (12, lambda f: explosion(f, 12, 3.5, 8)),
	'effect_bulldozer': (1, lambda f: bulldozer()),
}


def build(key):
	frames, fn = EFFECTS[key]
	bpy.ops.wm.open_mainfile(filepath=str(BLENDS / f'{key}.blend'))
	tris = {}
	for f in range(frames):
		state = 'default' if key == 'effect_bulldozer' else f'frame_{f}'
		coll = bpy.data.collections[state]
		for o in list(coll.objects):
			bpy.data.objects.remove(o, do_unlink=True)
		mesh = fn(f)
		me = bpy.data.meshes.new(f'{key}_{state}')
		me.from_pydata(mesh.v, [], mesh.f)
		mats = list(dict.fromkeys(mesh.m))
		for m in mats:
			me.materials.append(bpy.data.materials[m])
		for poly, m in zip(me.polygons, mesh.m):
			poly.material_index = mats.index(m)
		me.update()
		coll.objects.link(bpy.data.objects.new(f'{key}_{state}', me))
		tris[state] = len(me.polygons)
	bpy.ops.wm.save_mainfile()
	return tris


def main(keys=None):
	return {key: build(key) for key in (keys or EFFECTS)}


if __name__ == '__main__':
	args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
	print(main(args or None))
