"""Phase 8 family script: electrified rail catenary (catenary_rail), states pylon, pylon_diagonal, wire_both and wire_half.

Run inside Blender, through the Blender MCP (exec the file and call main()) or headless:
  blender -b -P tools/3d_assets/families/catenary.py
The .blend must exist (python tools/3d_assets/art.py new catenary_rail); then `art.py build catenary_rail`.

The renderer places the pieces where the classic elrail.cpp would draw its sprites (see rail3d_impl.h):
- pylon, pylon_diagonal: origin at the foot of the mast, Z up. The cantilever reaches along +X to the pylon control
  point over the track centre: 4 units for pylons beside straight track, 2.83 for the diagonal positions.
- wire_both, wire_half: one tile of wire from the control point at x = 0 to the one at x = 16, at the track base
  height (z = 0). wire_both hangs between pylons at both ends; wire_half has its pylon at x = 0 and ends at the
  middle of a two-tile span. The renderer stretches them along the track and shears them on slopes.
Heights: the contact wire sits just above the raised pantographs of the electric locomotives (train_locos.py).
"""
import math
import sys
from pathlib import Path

import bpy

BLEND = Path(__file__).resolve().parents[3] / 'OpenTTD-15.3' / 'OpenTTD-15.3' / 'assets' / '3d' / 'blender' / 'rail_furniture' / 'catenary_rail.blend' if '__file__' in globals() else None
CONTACT_Z = 7.3
SUPPORT_Z = 10.6
MAST_TOP = 12.0
WIRE = 0.2
MAST = 'concrete'
INSULATOR = 'brick_red'
WIRE_MAT = 'concrete_dark'


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

	def bar(self, a, b, w, mat):
		"""Square bar from a to b in the XZ plane (y = 0): top, bottom and both sides; the ends stay open."""
		dx, dz = b[0] - a[0], b[2] - a[2]
		length = math.hypot(dx, dz)
		nx, nz = -dz / length * w / 2, dx / length * w / 2  # in-plane normal
		h = w / 2
		v = [(a[0] - nx, -h, a[2] - nz), (b[0] - nx, -h, b[2] - nz), (b[0] + nx, -h, b[2] + nz), (a[0] + nx, -h, a[2] + nz),
			(a[0] - nx, h, a[2] - nz), (b[0] - nx, h, b[2] - nz), (b[0] + nx, h, b[2] + nz), (a[0] + nx, h, a[2] + nz)]
		self.add(v, [(0, 1, 2, 3), (7, 6, 5, 4), (3, 2, 6, 7), (4, 5, 1, 0)], mat)


def pylon(reach):
	mesh = Mesh()
	mesh.box(-0.8, -0.8, 0, 0.8, 0.8, 0.5, 'concrete_dark')
	mesh.box(-0.45, -0.45, 0.5, 0.45, 0.45, MAST_TOP, MAST)
	mesh.box(-0.3, -0.3, MAST_TOP, 0.3, 0.3, MAST_TOP + 0.6, MAST)
	# Cantilever: a level tie carrying the messenger wire and a strut from lower on the mast, as the sprite's triangle.
	tip = reach + 0.35
	mesh.bar((0.45, 0, SUPPORT_Z), (tip, 0, SUPPORT_Z), 0.3, MAST)
	mesh.bar((0.45, 0, SUPPORT_Z - 2.4), (reach, 0, SUPPORT_Z - 0.15), 0.25, MAST)
	# Registration arm holding the contact wire, hung from the tie end.
	mesh.bar((reach, 0, SUPPORT_Z), (reach, 0, CONTACT_Z), 0.15, WIRE_MAT)
	for z in (SUPPORT_Z, SUPPORT_Z - 2.4):
		mesh.box(0.45, -0.3, z - 0.3, 0.9, 0.3, z + 0.3, INSULATOR)
	return mesh


def wire(half):
	"""Contact wire, messenger wire sagging between supports, and droppers."""
	mesh = Mesh()
	span, sag = (32, 1.6) if half else (16, 1.2)
	messenger = lambda x: SUPPORT_Z - sag * 4 * (x / span) * (1 - x / span)
	mesh.bar((0, 0, CONTACT_Z), (16, 0, CONTACT_Z), WIRE, WIRE_MAT)
	xs = [0, 4, 8, 12, 16]
	for a, b in zip(xs, xs[1:]):
		mesh.bar((a, 0, messenger(a)), (b, 0, messenger(b)), WIRE, WIRE_MAT)
	for x in (4, 8, 12):
		mesh.bar((x, 0, messenger(x)), (x, 0, CONTACT_Z), 0.1, WIRE_MAT)
	return mesh


BUILDERS = {
	'pylon': lambda: pylon(4.0),
	'pylon_diagonal': lambda: pylon(2 * math.sqrt(2)),
	'wire_both': lambda: wire(False),
	'wire_half': lambda: wire(True),
}


def main():
	bpy.ops.wm.open_mainfile(filepath=str(BLEND))
	tris = {}
	for state, build in BUILDERS.items():
		coll = bpy.data.collections[state]
		for o in list(coll.objects):
			bpy.data.objects.remove(o, do_unlink=True)
		mesh = build()
		me = bpy.data.meshes.new(f'catenary_{state}')
		me.from_pydata(mesh.v, [], mesh.f)
		mats = list(dict.fromkeys(mesh.m))
		for m in mats:
			me.materials.append(bpy.data.materials[m])
		for poly, m in zip(me.polygons, mesh.m):
			poly.material_index = mats.index(m)
		me.update()
		coll.objects.link(bpy.data.objects.new(f'catenary_{state}', me))
		tris[state] = sum(len(p.vertices) - 2 for p in me.polygons)
	bpy.ops.wm.save_mainfile()
	return tris


if __name__ == '__main__':
	print(main())
