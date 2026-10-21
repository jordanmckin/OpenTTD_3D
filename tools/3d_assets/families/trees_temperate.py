"""Phase 8 family script: the 12 temperate tree species (tree_00..tree_11), every growth and dying state.

Run inside Blender, either through the Blender MCP (exec the file; set KEYS first to limit species) or headless:
  blender -b -P tools/3d_assets/families/trees_temperate.py -- [tree_00 ...]
Each member's .blend must exist (python tools/3d_assets/art.py new tree_XX). Its state collections are rebuilt and saved;
then run `python tools/3d_assets/art.py build tree_00 ...`.

Sizes come from the reference sprites: per state, screen height h and width w in pixels at normal zoom. A crown of
diameter d units is about 2.83·d pixels wide, so d = w / 2.83, and the top of the tree is at about h − 0.37·d units.
"""
import math
import random
import sys
from pathlib import Path

import bpy

BLENDS = Path(__file__).resolve().parents[3] / 'OpenTTD-15.3' / 'OpenTTD-15.3' / 'assets' / '3d' / 'blender' / 'tree' if '__file__' in globals() else None
STATES = ('growth_0', 'growth_1', 'growth_2', 'grown', 'dying_0', 'dying_1', 'dead')
SIDES = 7

# Reference sprite size (h, w) in pixels per state, measured from assets/3d/reference/temperate/tree_XX_*.png.
SIZES = {
	0: [(24, 20), (31, 25), (37, 30), (43, 35), (43, 35), (43, 35), (43, 28)],
	1: [(19, 13), (24, 17), (31, 21), (36, 24), (36, 24), (35, 24), (35, 24)],
	2: [(16, 11), (27, 14), (38, 20), (40, 24), (40, 24), (39, 24), (37, 16)],
	3: [(23, 15), (33, 20), (39, 22), (44, 28), (44, 25), (42, 25), (41, 24)],
	4: [(24, 27), (33, 37), (40, 45), (40, 45), (40, 45), (40, 45), (37, 42)],
	5: [(26, 16), (36, 25), (44, 30), (52, 35), (52, 35), (52, 34), (52, 22)],
	6: [(27, 19), (41, 25), (50, 30), (60, 35), (60, 33), (60, 31), (60, 31)],
	7: [(16, 18), (23, 27), (31, 38), (35, 43), (35, 43), (35, 43), (35, 43)],
	8: [(24, 11), (31, 14), (41, 18), (50, 22), (50, 22), (50, 22), (50, 22)],
	9: [(17, 14), (28, 23), (38, 30), (42, 30), (42, 29), (42, 29), (40, 20)],
	10: [(28, 17), (31, 19), (36, 24), (38, 27), (38, 27), (37, 27), (35, 25)],
	11: [(17, 15), (25, 22), (36, 33), (47, 38), (47, 38), (47, 37), (42, 33)],
}

# Species parameters.
#   kind: 'blobs' (ellipsoids), 'pads' (flat layers on a tall trunk) or 'cones' (stacked cones)
#   base: crown base as a fraction of tree height
#   parts: blobs/pads (u, v, w, s, t): centre offset u, v (× crown radius / 2), height w (fraction of crown height),
#          horizontal radius s (× crown radius), vertical radius t (× crown height / 2); cones (w0, w1, s).
#   leaf: growing/grown colour; dying: (dying_0, dying_1); dead: ('bare', bark colour) or ('crown', colour)
SPECIES = {
	0: dict(kind='blobs', base=0.35, trunk='bark', leaf='leaf', dying=('leaf_olive', 'leaf_olive'), dead=('bare', 'bark_grey'),
		parts=[(-0.6, 0.3, 0.40, 0.60, 0.50), (0.6, -0.4, 0.50, 0.60, 0.50), (0.1, 0.5, 0.75, 0.55, 0.45), (0.0, -0.2, 0.25, 0.50, 0.40)]),
	1: dict(kind='blobs', base=0.25, trunk='bark_grey', leaf='leaf_red', dying=('leaf_red', 'leaf_brown'), dead=('crown', 'leaf_brown'),
		parts=[(0.0, 0.0, 0.50, 1.00, 0.95), (0.4, 0.3, 0.75, 0.50, 0.45)]),
	2: dict(kind='blobs', base=0.12, trunk='bark', leaf='leaf_yellow', dying=('leaf_orange', 'leaf_orange'), dead=('bare', 'bark'),
		parts=[(0.0, 0.0, 0.50, 1.00, 1.00)]),
	3: dict(kind='blobs', base=0.30, trunk='bark_white', leaf='leaf_light', dying=('leaf_orange', 'leaf_orange'), dead=('bare', 'bark_white'),
		parts=[(0.0, 0.0, 0.35, 0.75, 0.45), (0.3, -0.3, 0.65, 0.70, 0.45), (-0.2, 0.3, 0.85, 0.50, 0.30)]),
	4: dict(kind='blobs', base=0.35, trunk='bark_grey', leaf='leaf_light', dying=('leaf_olive', 'leaf_olive'), dead=('bare', 'bark_grey'),
		parts=[(0.0, 0.0, 0.55, 1.00, 0.60), (-0.5, 0.4, 0.45, 0.60, 0.50), (0.5, -0.3, 0.50, 0.60, 0.50), (0.1, 0.2, 0.85, 0.55, 0.30)]),
	5: dict(kind='pads', base=0.35, trunk='bark_grey', leaf='leaf_dark', dying=('leaf_olive', 'leaf_olive'), dead=('bare', 'bark_grey'),
		parts=[(0.0, 0.0, 0.15, 0.90, 0.25), (0.3, -0.2, 0.45, 0.85, 0.25), (-0.2, 0.2, 0.72, 0.70, 0.25), (0.0, 0.0, 0.92, 0.45, 0.16)]),
	6: dict(kind='pads', base=0.30, trunk='bark_grey', leaf='leaf', dying=('leaf_olive', 'leaf_olive'), dead=('bare', 'bark_grey'),
		parts=[(0.0, 0.0, 0.12, 0.95, 0.22), (0.2, 0.2, 0.40, 0.85, 0.22), (-0.2, -0.1, 0.66, 0.80, 0.22), (0.0, 0.0, 0.90, 0.55, 0.20)]),
	7: dict(kind='blobs', base=0.25, trunk='bark', leaf='leaf_dark', dying=('leaf_brown', 'leaf_olive'), dead=('crown', 'leaf_olive'),
		parts=[(0.0, 0.0, 0.45, 1.00, 0.75), (-0.5, 0.3, 0.40, 0.55, 0.50), (0.5, -0.3, 0.55, 0.55, 0.50)]),
	8: dict(kind='cones', base=0.08, trunk='bark', leaf='leaf', dying=('leaf_olive', 'leaf_brown'), dead=('crown', 'leaf_brown'),
		parts=[(0.0, 0.60, 1.00), (0.35, 1.00, 0.70)]),
	9: dict(kind='cones', base=0.10, trunk='bark', leaf='leaf_blue', dying=('leaf_orange', 'leaf_orange'), dead=('bare', 'wood_dark'),
		parts=[(0.0, 0.55, 1.00), (0.30, 0.80, 0.75), (0.55, 1.00, 0.50)]),
	10: dict(kind='blobs', base=0.12, trunk='bark_grey', leaf='leaf', dying=('leaf_orange', 'leaf_orange'), dead=('bare', 'bark_grey'),
		parts=[(0.0, 0.0, 0.50, 1.00, 1.00), (0.3, -0.2, 0.70, 0.50, 0.40)]),
	11: dict(kind='blobs', base=0.20, trunk='bark', leaf='leaf_blue', dying=('leaf_orange', 'leaf_orange'), dead=('bare', 'bark'),
		parts=[(0.0, 0.0, 0.45, 0.90, 0.60), (-0.5, 0.3, 0.60, 0.60, 0.50), (0.4, -0.4, 0.70, 0.60, 0.50), (0.0, 0.2, 0.85, 0.50, 0.30)]),
}


class Mesh:
	def __init__(self):
		self.v, self.f, self.m = [], [], []

	def add(self, verts, faces, mat):
		o = len(self.v)
		self.v += verts
		for f in faces:
			self.f.append(tuple(i + o for i in f))
			self.m.append(mat)

	def lathe(self, cx, cy, profile, mat, rnd, top=None, bottom=None, sides=SIDES):
		"""Rings of (z, r) bottom to top with optional point caps; ring angles and radii are jittered by rnd."""
		verts, faces, rings = [], [], []
		for z, r in profile:
			rings.append(len(verts))
			a0 = rnd.uniform(0, 2 * math.pi / sides)
			for i in range(sides):
				a = a0 + 2 * math.pi * i / sides
				rr = r * rnd.uniform(0.88, 1.08)
				verts.append((cx + rr * math.cos(a), cy + rr * math.sin(a), z))
		for a, b in zip(rings, rings[1:]):
			for i in range(sides):
				j = (i + 1) % sides
				faces.append((a + i, a + j, b + j, b + i))
		if top is not None:
			c = len(verts); verts.append((cx, cy, top))
			faces += [(rings[-1] + i, rings[-1] + (i + 1) % sides, c) for i in range(sides)]
		if bottom is not None:
			c = len(verts); verts.append((cx, cy, bottom))
			faces += [(rings[0] + (i + 1) % sides, rings[0] + i, c) for i in range(sides)]
		self.add(verts, faces, mat)

	def ellipsoid(self, cx, cy, cz, r, rz, mat, rnd):
		self.lathe(cx, cy, [(cz - 0.6 * rz, 0.80 * r), (cz + 0.1 * rz, r), (cz + 0.6 * rz, 0.72 * r)], mat, rnd, top=cz + rz, bottom=cz - rz)

	def beam(self, p0, p1, w, mat):
		"""Square branch from p0 to p1, w thick, tapering to 60% at p1."""
		d = [b - a for a, b in zip(p0, p1)]
		n = math.sqrt(sum(c * c for c in d)) or 1.0
		d = [c / n for c in d]
		side = (d[1], -d[0], 0.0)
		sl = math.hypot(side[0], side[1])
		side = (1.0, 0.0, 0.0) if sl < 1e-6 else (side[0] / sl, side[1] / sl, 0.0)
		up = (side[1] * d[2] - side[2] * d[1], side[2] * d[0] - side[0] * d[2], side[0] * d[1] - side[1] * d[0])
		verts = []
		for p, k in ((p0, 1.0), (p1, 0.6)):
			h = w * k / 2
			for su, uu in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
				verts.append(tuple(p[i] + su * h * side[i] + uu * h * up[i] for i in range(3)))
		self.add(verts, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], mat)


def build(species, state):
	"""Return the Mesh for one species and state index (0..6)."""
	P = SPECIES[species]
	h, w = SIZES[species][state]
	d = w / 2.83
	R = d / 2
	H = h - 0.37 * d
	rnd = random.Random(species * 100 + state)
	zb = P['base'] * H
	hc = H - zb
	trunk_r = max(0.35, 0.09 * d)
	mesh = Mesh()
	dying = state >= 4
	dead_kind, dead_mat = P['dead']
	bare = state == 6 and dead_kind == 'bare'
	trunk_top = H * 0.92 if (bare or P['kind'] in ('pads', 'cones')) else zb + 0.35 * hc
	mesh.lathe(0, 0, [(0, trunk_r), (trunk_top, trunk_r * 0.55)], P['trunk'] if not bare else dead_mat, rnd, top=trunk_top + 0.3)

	if bare or (state == 5 and dead_kind == 'bare'):
		# Branches: visible on the bare dead tree and through the thinning dying_1 crown of species that end bare.
		n = 5 if bare else 3
		mat = dead_mat if bare else P['trunk']
		for i in range(n):
			a = 2 * math.pi * i / n + rnd.uniform(-0.3, 0.3)
			z0 = zb * rnd.uniform(0.9, 1.1) if P['kind'] == 'blobs' else zb + hc * (0.15 + 0.6 * i / n)
			reach = R * rnd.uniform(0.7, 1.0)
			z1 = min(H * 0.95, z0 + hc * rnd.uniform(0.35, 0.6))
			mesh.beam((0, 0, z0), (reach * math.cos(a), reach * math.sin(a), z1), trunk_r * 0.7, mat)
	if bare:
		return mesh

	if state <= 3:
		mat, scale, keep = P['leaf'], 1.0, len(P['parts'])
	elif state == 4:
		mat, scale, keep = P['dying'][0], 0.95, len(P['parts'])
	elif state == 5:
		mat, scale, keep = P['dying'][1], 0.82, max(1, len(P['parts']) - 1)
	else:
		mat, scale, keep = dead_mat, 0.9, len(P['parts'])
	parts = sorted(P['parts'], key=lambda p: -p[3 if len(p) == 5 else 2])[:keep] if keep < len(P['parts']) else P['parts']

	if P['kind'] in ('blobs', 'pads'):
		for (u, v, wz, s, t) in parts:
			rz = t * hc / 2 * scale
			mesh.ellipsoid(u * R * 0.5, v * R * 0.5, zb + wz * hc, s * R * scale, rz, mat, rnd)
	else:
		for (w0, w1, s) in parts:
			z0, z1 = zb + w0 * hc, zb + w1 * hc
			mesh.lathe(0, 0, [(z0, s * R * scale), (z0 + 0.25 * (z1 - z0), s * R * scale * 0.8)], mat, rnd, top=z1, bottom=z0 + 0.05)
	return mesh


def fill(key):
	species = int(key.split('_')[1])
	bpy.ops.wm.open_mainfile(filepath=str(BLENDS / f'{key}.blend'))
	tris = {}
	for i, state in enumerate(STATES):
		coll = bpy.data.collections[state]
		for o in list(coll.objects):
			bpy.data.objects.remove(o, do_unlink=True)
		mesh = build(species, i)
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


if __name__ == '__main__':
	argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
	keys = argv or globals().get('KEYS') or [f'tree_{i:02d}' for i in SPECIES]
	result = main(keys)
	print(result)
