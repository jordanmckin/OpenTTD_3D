"""Phase 8.5 vehicle kit: shared parts for train and road vehicle models.

Run inside Blender (through the MCP, or `blender -b -P`). Units follow CONVENTIONS.md: +X forward,
Z = 0 at the rail/road contact, Y across. Standard train rails are at Y = +-1.6 with their top at Z 0.65.
Every builder returns one mesh object linked into the given collection; normals are recalculated outwards.
"""
import math
import bmesh
import bpy

RAIL_Y = 1.6
RAIL_TOP = 0.65


def mesh(name, coll, verts, faces, mats, recalc=True):
	"""Make an object from polygons; mats gives one palette material name per face."""
	me = bpy.data.meshes.new(name)
	me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
	order = list(dict.fromkeys(mats))
	for m in order:
		me.materials.append(bpy.data.materials[m])
	for p, m in zip(me.polygons, mats):
		p.material_index = order.index(m)
	if recalc:
		bm = bmesh.new()
		bm.from_mesh(me)
		bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
		bm.to_mesh(me)
		bm.free()
	me.update()
	ob = bpy.data.objects.new(name, me)
	coll.objects.link(ob)
	return ob


def box(name, coll, lo, hi, mat, bottom=False):
	(x0, y0, z0), (x1, y1, z1) = lo, hi
	v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
	f = [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)] + ([(3, 2, 1, 0)] if bottom else [])
	return mesh(name, coll, v, f, [mat] * len(f))


def mirror_y(points):
	"""Half profile [(y, z)] from the bottom of the +Y side up to the centreline -> full closed-top profile."""
	right = [(y, z) for y, z in points]
	left = [(-y, z) for y, z in reversed(points) if y > 1e-6]
	return right + left


def loft(name, coll, stations, mat, cap_front=None, cap_back=None, mat_fn=None):
	"""Skin profiles along X. stations = [(x, [(y, z), ...])], all with the same point count.
	mat_fn(x0, x1, zmid, i) may pick a material per quad; caps are fans in the given material."""
	n = len(stations[0][1])
	verts, faces, mats = [], [], []
	for x, prof in stations:
		verts += [(x, y, z) for y, z in prof]
	for s in range(len(stations) - 1):
		for i in range(n - 1):
			a, b = s * n + i, s * n + i + 1
			faces.append((a, b, b + n, a + n))
			zmid = (verts[a][2] + verts[b][2]) / 2
			mats.append(mat_fn(stations[s][0], stations[s + 1][0], zmid, i) if mat_fn else mat)
	for cap, s in ((cap_back, 0), (cap_front, len(stations) - 1)):
		if cap:
			x = stations[s][0]
			c = len(verts)
			ys = [p[0] for p in stations[s][1]]
			zs = [p[1] for p in stations[s][1]]
			verts.append((x, sum(ys) / n, sum(zs) / n))
			for i in range(n - 1):
				faces.append((s * n + i, s * n + i + 1, c))
				mats.append(cap(zs[i], zs[i + 1]) if callable(cap) else cap)
	return mesh(name, coll, verts, faces, mats)


def ring(cx, cz, r, seg, y, start=0.0):
	return [(cx + r * math.cos(start + 2 * math.pi * k / seg), y, cz + r * math.sin(start + 2 * math.pi * k / seg)) for k in range(seg)]


def disc_y(name, coll, cx, cz, r, y0, y1, seg, mat, side_mat=None, cap_both=False, cap=True):
	"""Cylinder along Y from y0 to y1 (the y1 end is capped; the y0 end too when cap_both)."""
	a, b = ring(cx, cz, r, seg, y0), ring(cx, cz, r, seg, y1)
	v = a + b + [(cx, y1, cz), (cx, y0, cz)]
	f = [(k, (k + 1) % seg, seg + (k + 1) % seg, seg + k) for k in range(seg)]
	m = [side_mat or mat] * seg
	if cap:
		f += [(seg + k, seg + (k + 1) % seg, 2 * seg) for k in range(seg)]
		m += [mat] * seg
	if cap_both:
		f += [((k + 1) % seg, k, 2 * seg + 1) for k in range(seg)]
		m += [mat] * seg
	return mesh(name, coll, v, f, m)


def cyl_x(name, coll, cy, cz, r, x0, x1, seg, mat, cap_mat=None):
	"""Cylinder along X, capped at x1 (buffers, chimneys lying down, pipes)."""
	a = [(x0, cy + r * math.cos(2 * math.pi * k / seg), cz + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
	b = [(x1, p[1], p[2]) for p in a]
	v = a + b + [(x1, cy, cz)]
	f = [(k, (k + 1) % seg, seg + (k + 1) % seg, seg + k) for k in range(seg)] + [(seg + k, seg + (k + 1) % seg, 2 * seg) for k in range(seg)]
	return mesh(name, coll, v, f, [mat] * seg + [cap_mat or mat] * seg)


def cyl_z(name, coll, cx, cy, rx, ry, z0, z1, seg, mat, cap_mat=None):
	"""Upright (elliptic) cylinder, capped on top: chimneys, domes, lamps."""
	a = [(cx + rx * math.cos(2 * math.pi * k / seg), cy + ry * math.sin(2 * math.pi * k / seg), z0) for k in range(seg)]
	b = [(p[0], p[1], z1) for p in a]
	v = a + b + [(cx, cy, z1)]
	f = [(k, (k + 1) % seg, seg + (k + 1) % seg, seg + k) for k in range(seg)] + [(seg + k, seg + (k + 1) % seg, 2 * seg) for k in range(seg)]
	return mesh(name, coll, v, f, [mat] * seg + [cap_mat or mat] * seg)


def wheel(name, coll, x, r, side, width=0.22, spokes=0, seg=16, mat='steel', tyre='steel_light', hub='black', z=None):
	"""Rail wheel on the given side (+1/-1) with its tread centred on the rail. Spoked when spokes > 0:
	an outer tyre ring, a hub and radial spokes; otherwise a plain disc with a hub boss."""
	cz = (RAIL_TOP + r) if z is None else z
	s = side
	yi, yo = s * (RAIL_Y - width / 2), s * (RAIL_Y + width / 2)
	parts = []
	parts.append(disc_y(f'{name}_tread', coll, x, cz, r, yi, yo, seg, tyre, cap=not spokes))
	if spokes:
		# Spoked centre: rim ring as an annulus just outside the tread face, spokes, boss.
		ri = r * 0.78
		outer, inner = ring(x, cz, r, seg, yo + s * 0.01), ring(x, cz, ri, seg, yo + s * 0.01)
		v = outer + inner
		f = [(k, (k + 1) % seg, seg + (k + 1) % seg, seg + k) for k in range(seg)]
		parts.append(mesh(f'{name}_rim', coll, v, f, [mat] * seg))
		back = ring(x, cz, ri, seg, yi + s * 0.04)
		parts.append(mesh(f'{name}_back', coll, back + [(x, yi + s * 0.04, cz)], [(k, (k + 1) % seg, seg) for k in range(seg)], [hub] * seg))
		for k in range(spokes):
			a = 2 * math.pi * k / spokes
			ca, sa = math.cos(a), math.sin(a)
			w = r * 0.07
			p0, p1 = r * 0.18, ri
			quad = [(x + ca * p0 - sa * w, cz + sa * p0 + ca * w), (x + ca * p1 - sa * w, cz + sa * p1 + ca * w),
				(x + ca * p1 + sa * w, cz + sa * p1 - ca * w), (x + ca * p0 + sa * w, cz + sa * p0 - ca * w)]
			ya, yb = yi + s * 0.06, yo
			v = [(px, ya, pz) for px, pz in quad] + [(px, yb, pz) for px, pz in quad]
			f = [(4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6)]
			parts.append(mesh(f'{name}_spoke{k}', coll, v, f, [mat] * 3))
		parts.append(disc_y(f'{name}_boss', coll, x, cz, r * 0.22, yo - s * 0.05, yo + s * 0.08, 8, mat))
	else:
		parts.append(disc_y(f'{name}_face', coll, x, cz, r * 0.85, yo, yo + s * 0.02, seg, mat))
		parts.append(disc_y(f'{name}_boss', coll, x, cz, r * 0.25, yo, yo + s * 0.07, 8, hub))
	return join(name, parts)


def rod(name, coll, a, b, y, thick, depth, mat):
	"""Flat bar in the XZ plane between points a=(x, z) and b=(x, z), at side offset y (depth along Y)."""
	(ax, az), (bx, bz) = a, b
	dx, dz = bx - ax, bz - az
	l = math.hypot(dx, dz)
	nx, nz = -dz / l * thick / 2, dx / l * thick / 2
	q = [(ax + nx, az + nz), (bx + nx, bz + nz), (bx - nx, bz - nz), (ax - nx, az - nz)]
	y0, y1 = y, y + math.copysign(depth, y)
	v = [(px, y0, pz) for px, pz in q] + [(px, y1, pz) for px, pz in q]
	f = [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
	return mesh(name, coll, v, f, [mat] * 5)


def buffers(name, coll, x, direction, z=1.55, y=1.15, mat='steel_light', stock='black', length=0.45, r=0.22):
	"""A pair of sprung buffers on a beam end; direction +1 at the front, -1 at the back."""
	parts = []
	for s in (1, -1):
		x0, x1 = x, x + direction * length * 0.55
		parts.append(cyl_x(f'{name}_stock{s}', coll, s * y, z, r * 0.6, x0, x1, 8, stock))
		parts.append(cyl_x(f'{name}_head{s}', coll, s * y, z, r, x1, x + direction * length, 10, mat))
	parts.append(box(f'{name}_hook', coll, (min(x, x + direction * 0.35), -0.12, z - 0.15), (max(x, x + direction * 0.35), 0.12, z + 0.05), 'black'))
	return join(name, parts)


def join(name, objs):
	objs = [o for o in objs if o is not None]
	with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
		bpy.ops.object.join()
	objs[0].name = name
	objs[0].data.name = name
	return objs[0]


def clear(coll):
	for o in list(coll.objects):
		bpy.data.objects.remove(o, do_unlink=True)


def triangles(coll):
	return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in coll.all_objects if o.type == 'MESH')


def sync_palette():
	"""Add palette colours created after this .blend was made, exactly as new_blend.py makes them, and update changed ones."""
	import json
	path = r"D:\G ttd\OpenTTD-15.3\OpenTTD-15.3\assets\3d\blender\palette.json"
	pal = json.load(open(path, encoding="utf-8"))["colours"]
	lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
	added = []
	for name, rgb in pal.items():
		linear = [lin(c) for c in rgb] + [1.0]
		if name in bpy.data.materials:
			mat = bpy.data.materials[name]  # follow palette edits
			mat.diffuse_color = linear
			bsdf = mat.node_tree.nodes.get('Principled BSDF') if mat.node_tree else None
			if bsdf:
				bsdf.inputs['Base Color'].default_value = linear
			continue
		mat = bpy.data.materials.new(name)
		mat.diffuse_color = linear
		mat.use_nodes = True
		bsdf = mat.node_tree.nodes.get('Principled BSDF')
		if bsdf:
			bsdf.inputs['Base Color'].default_value = linear
			bsdf.inputs['Roughness'].default_value = 1.0
		mat.use_fake_user = True
		added.append(name)
	return added


def open_wagon(name, coll, x0, x1, half_w, z0, z1, mat, ribs=6, rib_mat=None, floor_mat='black', wall=0.12):
	"""Open wagon body: floor, four walls with thickness, a top rim and outside ribs on sides and ends."""
	rm = rib_mat or mat
	parts = [box(f'{name}_floor', coll, (x0, -half_w, z0), (x1, half_w, z0 + 0.15), floor_mat)]
	inner_x0, inner_x1, inner_w = x0 + wall, x1 - wall, half_w - wall
	for s in (1, -1):
		parts.append(box(f'{name}_side{s}', coll, (x0, min(s * half_w, s * inner_w), z0), (x1, max(s * half_w, s * inner_w), z1), mat))
		parts.append(box(f'{name}_rim{s}', coll, (x0 - 0.05, min(s * (half_w + 0.06), s * (inner_w - 0.02)), z1 - 0.12), (x1 + 0.05, max(s * (half_w + 0.06), s * (inner_w - 0.02)), z1 + 0.04), rm))
		for k in range(ribs + 1):
			x = x0 + 0.15 + (x1 - x0 - 0.3) * k / ribs
			parts.append(box(f'{name}_rib{s}_{k}', coll, (x - 0.07, min(s * half_w, s * (half_w + 0.07)), z0), (x + 0.07, max(s * half_w, s * (half_w + 0.07)), z1 - 0.12), rm))
	for e, (a, b) in (('back', (x0, inner_x0)), ('front', (inner_x1, x1))):
		parts.append(box(f'{name}_end_{e}', coll, (a, -inner_w, z0), (b, inner_w, z1), mat))
		xo = a - 0.07 if e == 'back' else b
		for y in (-0.7, 0.7):
			parts.append(box(f'{name}_endrib_{e}{y}', coll, (xo, y - 0.07, z0), (xo + 0.07, y + 0.07, z1 - 0.12), rm))
	return join(name, parts)


def bulk_load(name, coll, x0, x1, half_w, z_base, peak, mat, nx=10, ny=5, seed=1):
	"""Heaped bulk cargo (coal, ore, grain): a jittered grid mound, highest along the centre line."""
	import random
	rnd = random.Random(seed)
	verts, faces = [], []
	for i in range(nx + 1):
		for j in range(ny + 1):
			u, v = i / nx, j / ny
			x, y = x0 + (x1 - x0) * u, -half_w + 2 * half_w * v
			edge = min(u, 1 - u, v, 1 - v) * 2
			h = 0 if edge == 0 else peak * (math.sin(math.pi * u) ** 0.6) * (math.sin(math.pi * v) ** 0.8)
			if 0 < edge:
				h += rnd.uniform(-0.12, 0.12)
				x += rnd.uniform(-0.05, 0.05)
			verts.append((x, y, z_base + max(h, 0)))
	for i in range(nx):
		for j in range(ny):
			a = i * (ny + 1) + j
			faces += [(a, a + ny + 1, a + ny + 2), (a, a + ny + 2, a + 1)]
	return mesh(name, coll, verts, faces, [mat] * len(faces))


def bogie(name, coll, x, frame_mat, wheel_r=0.42, wheelbase=1.25, spokes=0):
	"""Two-axle diamond-frame freight bogie centred at x, side frames outside the wheels."""
	parts = []
	cz = RAIL_TOP + wheel_r
	for s in (1, -1):
		for k in (-1, 1):
			parts.append(wheel(f'{name}_w{k}{s}', coll, x + k * wheelbase / 2, wheel_r, s, seg=12, spokes=spokes))
		y0, y1 = s * (RAIL_Y + 0.2), s * (RAIL_Y + 0.32)
		lo, hi = min(y0, y1), max(y0, y1)
		hw = wheelbase / 2 + wheel_r * 0.9
		# Diamond frame: top chord, sloping bottom chords, centre bolster window.
		parts.append(box(f'{name}_top{s}', coll, (x - hw, lo, cz + 0.12), (x + hw, hi, cz + 0.32), frame_mat))
		for k in (-1, 1):
			parts.append(rod(f'{name}_chord{k}{s}', coll, (x + k * hw, cz + 0.2), (x + k * 0.35, cz - 0.3), y0, 0.18, 0.12, frame_mat))
			parts.append(box(f'{name}_axlebox{k}{s}', coll, (x + k * wheelbase / 2 - 0.16, lo - 0.03, cz - 0.18), (x + k * wheelbase / 2 + 0.16, hi + 0.03, cz + 0.14), 'black'))
		parts.append(box(f'{name}_bottom{s}', coll, (x - 0.38, lo, cz - 0.38), (x + 0.38, hi, cz - 0.2), frame_mat))
		parts.append(box(f'{name}_column{s}', coll, (x - 0.38, lo, cz - 0.38), (x - 0.26, hi, cz + 0.2), frame_mat))
		parts.append(box(f'{name}_column2{s}', coll, (x + 0.26, lo, cz - 0.38), (x + 0.38, hi, cz + 0.2), frame_mat))
		parts.append(box(f'{name}_spring{s}', coll, (x - 0.24, lo + 0.02 * s, cz - 0.2), (x + 0.24, hi, cz + 0.1), 'steel'))
	parts.append(box(f'{name}_bolster', coll, (x - 0.3, -RAIL_Y - 0.2, cz + 0.05), (x + 0.3, RAIL_Y + 0.2, cz + 0.3), frame_mat))
	return join(name, parts)


ROAD_LIFT = 0.3  # wheels start above Z 0 so they do not fight the road surface


def road_wheel(name, coll, x, r, side, y_out, width=0.4, seg=16, tyre='rubber', hub='steel_light', inner=False):
	"""Road wheel: rubber tyre with a sidewall and a hub disc with a boss, outer face at y_out on the given side.
	inner=True draws only the tyre (the inner half of a dual pair, its face hidden by the outer wheel)."""
	cz = ROAD_LIFT + r
	yo, yi = side * y_out, side * (y_out - width)
	parts = [disc_y(f'{name}_tyre', coll, x, cz, r, yi, yo, seg, tyre, cap=not inner)]
	if not inner:
		parts.append(disc_y(f'{name}_hub', coll, x, cz, r * 0.62, yo, yo + side * 0.02, 10, hub))
		parts.append(disc_y(f'{name}_boss', coll, x, cz, r * 0.22, yo, yo + side * 0.1, 8, 'black'))
	return join(name, parts)


def rail_underframe(p, coll, z0, bogie_mat='cc1', length=3.7):
	"""Standard wagon underframe below a body floor at z0: solebars, headstocks, buffers and couplings,
	steps, brake gear and two diamond bogies."""
	for s in (1, -1):
		box(p + f'solebar{s}', coll, (-length, s * 1.45 - 0.1, 1.55), (length, s * 1.45 + 0.1, z0), 'black')
		rod(p + f'brake_lever{s}', coll, (-1.2, 1.35), (0.6, 1.7), s * 1.55, 0.08, 0.04, 'steel_light')
		box(p + f'step{s}', coll, (3.0, s * 1.5 - 0.1, 1.15), (3.4, s * 1.5 + 0.1, 1.25), 'black')
		box(p + f'step_back{s}', coll, (-3.4, s * 1.5 - 0.1, 1.15), (-3.0, s * 1.5 + 0.1, 1.25), 'black')
	for e in (1, -1):
		box(p + f'headstock{e}', coll, (min(e * (length - 0.1), e * (length + 0.05)), -1.5, 1.4), (max(e * (length - 0.1), e * (length + 0.05)), 1.5, z0), 'black')
		buffers(p + f'buffers{e}', coll, e * (length + 0.05), e, z=1.7, y=1.1, length=0.25, r=0.2)
		bogie(p + f'bogie{e}', coll, e * 2.2, bogie_mat)
		box(p + f'pivot{e}', coll, (e * 2.2 - 0.3, -0.45, 1.35), (e * 2.2 + 0.3, 0.45, 1.6), 'black')
	cyl_x(p + 'brake_cylinder', coll, 0.0, 1.35, 0.25, -0.5, 0.5, 10, 'black')
	cyl_x(p + 'brake_pipe', coll, -0.9, 1.45, 0.05, -3.6, 3.6, 6, 'black')


def mono_base(p, coll, z0, base_mat='wagon_grey', pod_mat='cc1'):
	"""Monorail/maglev wagon base below a body floor at z0: a closed skirt over the beam with a hazard stripe,
	side pods with grilles, couplers and end lamps."""
	box(p + 'base', coll, (-3.5, -1.45, 0.95), (3.5, 1.45, z0), base_mat)
	box(p + 'stripe', coll, (-3.52, -1.47, 0.75), (3.52, 1.47, 0.97), 'hazard_yellow')
	box(p + 'base_lip', coll, (-3.45, -1.5, z0 - 0.12), (3.45, 1.5, z0), 'black')
	for s in (1, -1):
		for k, x in enumerate((-2.0, 2.0)):
			y = s * 1.45
			box(p + f'pod{s}{k}', coll, (x - 0.95, min(y, y + s * 0.05), 1.1), (x + 0.95, max(y, y + s * 0.05), 1.75), pod_mat)
			for g in range(4):
				gx = x - 0.7 + 0.47 * g
				box(p + f'grille{s}{k}{g}', coll, (gx - 0.05, min(y, y + s * 0.08), 1.2), (gx + 0.05, max(y, y + s * 0.08), 1.65), 'black')
	for e in (1, -1):
		box(p + f'coupler{e}', coll, (min(e * 3.5, e * 3.85), -0.25, 1.2), (max(e * 3.5, e * 3.85), 0.25, 1.55), 'black')
		box(p + f'end_lamp{e}', coll, (min(e * 3.5, e * 3.54), -1.2, 1.7), (max(e * 3.5, e * 3.54), -0.9, 1.85), 'signal_red')
