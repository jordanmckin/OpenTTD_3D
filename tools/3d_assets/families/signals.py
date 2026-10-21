"""Phase 8 family script: the 12 base rail signals (electric/semaphore × block, entry, exit, combo, path, path_oneway),
states red and green.

Run inside Blender, through the Blender MCP (exec the file and call main(keys)) or headless:
  blender -b -P tools/3d_assets/families/signals.py -- [signal_electric_block ...]
Each member's .blend must exist (python tools/3d_assets/art.py new <key>); then `art.py build <key> ...`.

Local frame (see convert_gltf.py and rail3d_impl.h): origin at the foot of the post, Z up, +X the direction of travel.
Lamps and arms face -X, towards the approaching train; the track is on the -Y side. Heights follow the reference
sprites (about 15 pixels, so 15 units).
"""
import math
import sys
from pathlib import Path

import bpy

BLENDS = Path(__file__).resolve().parents[3] / 'OpenTTD-15.3' / 'OpenTTD-15.3' / 'assets' / '3d' / 'blender' / 'rail_furniture' if '__file__' in globals() else None
VARIANTS = ('electric', 'semaphore')
TYPES = ('block', 'entry', 'exit', 'combo', 'path', 'path_oneway')
POST_TOP = 14.0


class Mesh:
	def __init__(self):
		self.v, self.f, self.m = [], [], []

	def add(self, verts, faces, mat):
		o = len(self.v)
		self.v += verts
		for f in faces:
			self.f.append(tuple(i + o for i in f))
			self.m.append(mat)

	def box(self, x0, y0, z0, x1, y1, z1, mat):
		v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
		self.add(v, [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)

	def lamp(self, y, z, r, mat, x=-0.62):
		"""Square lamp on the -X face of a head."""
		self.add([(x, y + r, z - r), (x, y - r, z - r), (x, y - r, z + r), (x, y + r, z + r)], [(0, 1, 2, 3)], mat)

	def arm(self, pivot, length, angle, width, mat, tip_mat=None):
		"""Semaphore arm: a flat blade from the pivot towards -Y, raised by angle (degrees) above horizontal."""
		px, py, pz = pivot
		a = math.radians(angle)
		dy, dz = -math.cos(a), math.sin(a)
		ny, nz = -dz, dy  # in-plane normal of the blade
		h = width / 2
		def blade(t0, t1, mat):
			p0 = (py + dy * t0, pz + dz * t0); p1 = (py + dy * t1, pz + dz * t1)
			v = [(px - 0.15, p0[0] + ny * h, p0[1] + nz * h), (px - 0.15, p0[0] - ny * h, p0[1] - nz * h),
				(px - 0.15, p1[0] - ny * h, p1[1] - nz * h), (px - 0.15, p1[0] + ny * h, p1[1] + nz * h)]
			self.add(v, [(0, 1, 2, 3), (3, 2, 1, 0)], mat)
		blade(0, length * 0.72, mat)
		blade(length * 0.72, length * 0.82, tip_mat or 'plaster_white')
		blade(length * 0.82, length, mat)


def marker(mesh, kind, z=4.5):
	"""Presignal/path markers on the post, below the head."""
	if kind == 'entry':
		mesh.box(-0.7, -0.6, z, -0.3, 0.6, z + 1.0, 'lamp_yellow')
	elif kind == 'exit':
		mesh.box(-0.7, -0.7, z, -0.3, 0.7, z + 1.6, 'plaster_white')
		mesh.box(-0.75, -0.35, z + 0.35, -0.65, 0.35, z + 1.25, 'black')
	elif kind == 'combo':
		mesh.box(-0.7, -0.7, z, -0.3, 0.7, z + 1.6, 'lamp_yellow')
		mesh.box(-0.75, -0.35, z + 0.35, -0.65, 0.35, z + 1.25, 'black')
	elif kind == 'path_oneway':
		mesh.box(-0.7, -0.9, 1.4, -0.3, 0.9, 2.6, 'plaster_white')
		mesh.box(-0.75, -0.6, 1.8, -0.65, 0.6, 2.2, 'signal_red')


def build(variant, kind, green):
	mesh = Mesh()
	path = kind in ('path', 'path_oneway')
	post = 'steel_light' if not path else 'stone'
	mesh.box(-0.25, -0.25, 0, 0.25, 0.25, POST_TOP if variant == 'semaphore' else 10.0, post)
	mesh.box(-0.6, -0.6, 0, 0.6, 0.6, 0.4, 'concrete_dark')
	if variant == 'electric':
		head = 'black' if not path else 'roof_slate'
		mesh.box(-0.6, -0.75, 10.0, 0.4, 0.75, 14.6, head)
		mesh.box(-0.6, -0.75, 14.6, 0.4, 0.75, 14.8, 'black')
		mesh.lamp(0, 13.4, 0.5, 'signal_green' if green else 'leaf_dark')
		mesh.lamp(0, 11.4, 0.5, 'signal_red' if not green else 'brick_dark')
		marker(mesh, kind, 6.5)
	else:
		mesh.box(-0.3, -0.3, POST_TOP, 0.3, 0.3, POST_TOP + 0.4, 'black')
		angle = 45 if green else 0
		mesh.arm((-0.3, -0.25, 12.6), 3.2, angle, 0.7, 'brick_red')
		mesh.lamp(0.0, 12.6, 0.3, 'signal_green' if green else 'signal_red', x=-0.45)
		if path:
			mesh.arm((-0.3, -0.25, 9.6), 2.6, angle, 0.6, 'lamp_yellow', 'black')
		marker(mesh, kind, 5.0)
	return mesh


def fill(key):
	variant, kind = key[len('signal_'):].split('_', 1)
	bpy.ops.wm.open_mainfile(filepath=str(BLENDS / f'{key}.blend'))
	tris = {}
	for state in ('red', 'green'):
		coll = bpy.data.collections[state]
		for o in list(coll.objects):
			bpy.data.objects.remove(o, do_unlink=True)
		mesh = build(variant, kind, state == 'green')
		me = bpy.data.meshes.new(f'{key}_{state}')
		me.from_pydata(mesh.v, [], mesh.f)
		mats = list(dict.fromkeys(mesh.m))
		for m in mats:
			me.materials.append(bpy.data.materials[m])
		for poly, m in zip(me.polygons, mesh.m):
			poly.material_index = mats.index(m)
		me.update()
		coll.objects.link(bpy.data.objects.new(f'{key}_{state}', me))
		tris[state] = sum(len(p.vertices) - 2 for p in me.polygons)
	bpy.ops.wm.save_mainfile()
	return tris


def main(keys):
	return {key: fill(key) for key in keys}


ALL = [f'signal_{v}_{k}' for v in VARIANTS for k in TYPES]

if __name__ == '__main__':
	argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
	print(main(argv or globals().get('KEYS') or ALL))
