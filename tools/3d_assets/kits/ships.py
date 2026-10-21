"""Phase 8.5 ships: the four temperate hull images (tanker, ferry, hovercraft, cargo ship).

Exec'd after vehicle_kit.py with KEY set to the member's inventory key. Ships are authored at world size
(1 unit = 1 world pixel, a tile is 16): +X is the bow, Z = 0 is the waterline, Y across (+Y is port).
Proportions come from the sprites: length from the diagonal views, beam from the end-on view.
"""
import math

sync_palette()
N = int(KEY.split('_')[1])
COLL = bpy.data.collections['default']
clear(COLL)
P = 'default_'


def hull(name, x0, x1, hw, keel, deck, rail, bow, stern, sheer, boot=0.35):
	"""Ship hull lofted along X: dark bottom, cc1 topsides with a bulwark, olive deck. The bow fines to a raked stem
	over `bow` units and the stern rounds over `stern` units to a transom; both ends are closed with n-gon caps."""
	xs = [x0, x0 + stern * 0.35, x0 + stern * 0.7, x0 + stern]
	mid = x1 - bow
	xs += [xs[-1] + (mid - xs[-1]) * k / 3 for k in (1, 2, 3)]
	xs += [mid + bow * t for t in (0.25, 0.45, 0.62, 0.76, 0.87, 0.95, 1.0)]
	verts, faces, mats = [], [], []
	D, C, O = 'hull_dark', 'cc1', 'deck_olive'
	ring_mats = [D, D, D, C, C, C, O, O, C, C, C, D, D, D]
	n = len(ring_mats)
	for x in xs:
		tb = max(0.0, (x - mid) / bow)
		ts = max(0.0, (x0 + stern - x) / stern)
		w = max(0.02, (1 - tb ** 1.7) ** 0.75) * (1 - 0.22 * ts ** 2)
		h = hw * w
		kz = keel + (boot + 0.5 - keel) * tb ** 2 + 0.55 * ts ** 2
		bt = max(boot, kz)
		bz = min(kz + 0.3, bt)
		dk, rt = deck + sheer * tb ** 2, rail + sheer * tb ** 2
		hi = max(h - 0.14, h * 0.5)
		right = [(0.0, kz), (0.72 * h, kz), (0.95 * h, bz), (h, bt), (h, rt), (hi, rt), (hi, dk), (0.0, dk)]
		left = [(-y, z) for y, z in reversed(right[1:-1])]
		verts += [(x, y, z) for y, z in right + left]
	for s in range(len(xs) - 1):
		for i in range(n):
			a, b = s * n + i, s * n + (i + 1) % n
			faces.append((a, b, b + n, a + n))
			mats.append(ring_mats[i])
	last = (len(xs) - 1) * n
	faces += [tuple(range(n)), tuple(range(last, last + n))]
	mats += [C, C]
	return mesh(name, COLL, verts, faces, mats)


def deck_top(x, sheer_x, deck, sheer, bow):
	"""Deck height at x, following the hull's sheer towards the bow."""
	tb = max(0.0, (x - sheer_x) / bow)
	return deck + sheer * tb ** 2


def panes(name, xs, y, z0, z1, w, mat='glass_dark', out=0.03):
	"""A row of window panes on the side at Y = y (sign gives the facing), one quad each, centred on xs."""
	v, f = [], []
	yy = y + math.copysign(out, y)
	for x in xs:
		k = len(v)
		v += [(x - w / 2, yy, z0), (x + w / 2, yy, z0), (x + w / 2, yy, z1), (x - w / 2, yy, z1)]
		f.append((k, k + 1, k + 2, k + 3) if y > 0 else (k + 3, k + 2, k + 1, k))
	return mesh(name, COLL, v, f, [mat] * len(f), recalc=False)


def panes_x(name, x, ys, z0, z1, w, mat='glass_dark', out=0.03):
	"""A row of window panes on an end wall at X = x, facing +X when `out` > 0."""
	v, f = [], []
	xx = x + out
	for y in ys:
		k = len(v)
		v += [(xx, y - w / 2, z0), (xx, y + w / 2, z0), (xx, y + w / 2, z1), (xx, y - w / 2, z1)]
		f.append((k, k + 1, k + 2, k + 3) if out > 0 else (k + 3, k + 2, k + 1, k))
	return mesh(name, COLL, v, f, [mat] * len(f), recalc=False)


def spread(a, b, n):
	return [a + (b - a) * (k + 0.5) / n for k in range(n)]


def deckhouse(name, x0, x1, hw, z0, z1, mat='plaster_white', rows=(), front_rows=(), pane=0.32, pitch=0.62, roof=None):
	"""Superstructure block with rows of side windows ((z0, z1) per row) and front windows."""
	box(name, COLL, (x0, -hw, z0), (x1, hw, z1), mat)
	if roof:
		box(name + '_roof', COLL, (x0 - 0.06, -hw - 0.06, z1), (x1 + 0.06, hw + 0.06, z1 + 0.08), roof)
	cols = spread(x0 + 0.2, x1 - 0.2, max(1, int((x1 - x0 - 0.4) / pitch)))
	for r, (a, b) in enumerate(rows):
		for s in (1, -1):
			panes(f'{name}_win{r}{s}', cols, s * hw, a, b, pane)
	fcols = spread(-hw + 0.25, hw - 0.25, max(1, int((2 * hw - 0.5) / pitch)))
	for r, (a, b) in enumerate(front_rows):
		panes_x(f'{name}_fwin{r}', x1, fcols, a, b, pane)
		panes_x(f'{name}_bwin{r}', x0, fcols, a, b, pane, out=-0.03)


def bridge(name, x0, x1, hw, z0, z1, wing, mat='plaster_white'):
	"""Wheelhouse with a wrap-round window band, an overhanging roof and open bridge wings out to Y = +-wing."""
	box(name, COLL, (x0, -hw, z0), (x1, hw, z1), mat)
	zw0, zw1 = z0 + (z1 - z0) * 0.45, z1 - 0.15
	box(name + '_glass', COLL, (x0 + 0.15, -hw - 0.03, zw0), (x1 + 0.03, hw + 0.03, zw1), 'glass_dark')
	box(name + '_roof', COLL, (x0 - 0.1, -hw - 0.15, z1), (x1 + 0.25, hw + 0.15, z1 + 0.12), mat)
	for s in (1, -1):
		box(f'{name}_wing{s}', COLL, (x1 - 1.0, min(s * hw, s * wing), z0 - 0.12), (x1 - 0.1, max(s * hw, s * wing), z0), mat)
		box(f'{name}_wing_rail{s}', COLL, (x1 - 1.0, min(s * (wing - 0.06), s * wing), z0), (x1 - 0.1, max(s * (wing - 0.06), s * wing), z0 + 0.45), mat)
		box(f'{name}_light{s}', COLL, (x1 - 0.55, min(s * wing, s * (wing + 0.12)), z0 + 0.1), (x1 - 0.3, max(s * wing, s * (wing + 0.12)), z0 + 0.35),
			'signal_red' if s > 0 else 'signal_green')


def funnel(name, x, y, rx, ry, z0, z1, mat='cc1', top='black'):
	cyl_z(name, COLL, x, y, rx, ry, z0, z1 - 0.35, 12, mat)
	cyl_z(name + '_top', COLL, x, y, rx * 1.02, ry * 1.02, z1 - 0.35, z1, 12, top, cap_mat='black')


def mast(name, x, z0, z1, yard=1.0, r=0.07):
	cyl_z(name, COLL, x, 0.0, r, r, z0, z1, 6, 'steel_light')
	box(name + '_yard', COLL, (x - 0.05, -yard, z1 - 0.6), (x + 0.05, yard, z1 - 0.5), 'steel_light')
	cyl_z(name + '_lamp', COLL, x, 0.0, r * 1.6, r * 1.6, z1, z1 + 0.14, 6, 'lamp_yellow')


def radar(name, x, z):
	cyl_z(name + '_post', COLL, x, 0.0, 0.06, 0.06, z, z + 0.45, 6, 'steel_light')
	box(name, COLL, (x - 0.1, -0.7, z + 0.45), (x + 0.1, 0.7, z + 0.55), 'black')


def capsule_x(name, cy, cz, ry, rz, x0, x1, seg, mat, cap_mat=None):
	"""Elliptic cylinder along X with pointed ends: lifeboats, nacelles."""
	a = [(x0 + (x1 - x0) * 0.15, cy + ry * math.cos(2 * math.pi * k / seg), cz + rz * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
	b = [(x1 - (x1 - x0) * 0.15, p[1], p[2]) for p in a]
	v = a + b + [(x0, cy, cz), (x1, cy, cz)]
	f = [(k, (k + 1) % seg, seg + (k + 1) % seg, seg + k) for k in range(seg)]
	f += [((k + 1) % seg, k, 2 * seg) for k in range(seg)] + [(seg + k, seg + (k + 1) % seg, 2 * seg + 1) for k in range(seg)]
	return mesh(name, COLL, v, f, [mat] * seg + [cap_mat or mat] * 2 * seg)


def lifeboat(name, x, y, z, length=1.7, mat='paint_orange'):
	"""Lifeboat on a pair of davits; y is the boat's centreline."""
	capsule_x(name, y, z + 0.3, 0.38, 0.3, x - length / 2, x + length / 2, 8, mat)
	box(name + '_canopy', COLL, (x - length * 0.3, y - 0.3, z + 0.45), (x + length * 0.3, y + 0.3, z + 0.68), 'plaster_white')
	inner = y - math.copysign(0.55, y)
	for dx in (-length * 0.38, length * 0.38):
		rod(f'{name}_davit{dx:.1f}', COLL, (x + dx, z - 0.4), (x + dx, z + 0.9), inner, 0.09, 0.09, 'steel')
		box(f'{name}_arm{dx:.1f}', COLL, (x + dx - 0.05, min(inner, y), z + 0.82), (x + dx + 0.05, max(inner, y), z + 0.92), 'steel')


def bollards(name, xs, y, z):
	for i, x in enumerate(xs):
		for s in (1, -1):
			cyl_z(f'{name}{i}{s}', COLL, x, s * y, 0.12, 0.12, z, z + 0.3, 6, 'black')


def anchors(name, x, hw, z):
	for s in (1, -1):
		box(f'{name}{s}', COLL, (x - 0.3, min(s * hw, s * (hw + 0.06)), z - 0.35), (x + 0.15, max(s * hw, s * (hw + 0.06)), z), 'black')


def rails(name, x0, x1, hw, z, h=0.4):
	"""Guard rails round a deck edge: top rail and stanchions, both sides and the after end."""
	for s in (1, -1):
		box(f'{name}_top{s}', COLL, (x0, s * hw - 0.03, z + h - 0.05), (x1, s * hw + 0.03, z + h), 'steel_light')
		for x in spread(x0, x1, max(2, int((x1 - x0) / 1.2))):
			box(f'{name}_post{s}{x:.1f}', COLL, (x - 0.03, s * hw - 0.03, z), (x + 0.03, s * hw + 0.03, z + h), 'steel_light')
	box(f'{name}_end', COLL, (x0 - 0.03, -hw, z + h - 0.05), (x0 + 0.03, hw, z + h), 'steel_light')


def crane(name, x, z0, jib_to, jib_z):
	"""Deck crane: red post, orange machinery house, orange jib reaching aft over a hold to x = jib_to."""
	cyl_z(name + '_post', COLL, x, 0.0, 0.32, 0.32, z0, z0 + 3.2, 10, 'signal_red')
	box(name + '_house', COLL, (x - 0.55, -0.5, z0 + 3.2), (x + 0.55, 0.5, z0 + 3.9), 'paint_orange')
	box(name + '_house_roof', COLL, (x - 0.6, -0.55, z0 + 3.9), (x + 0.6, 0.55, z0 + 3.98), 'steel')
	for s in (1, -1):
		rod(f'{name}_jib{s}', COLL, (x - 0.3, z0 + 3.5), (jib_to, jib_z), s * 0.2, 0.22, 0.12, 'paint_orange')
	box(name + '_jib_tie', COLL, (jib_to - 0.1, -0.32, jib_z - 0.15), (jib_to + 0.1, 0.32, jib_z + 0.1), 'paint_orange')
	rod(name + '_stay', COLL, (x + 0.3, z0 + 3.95), (jib_to + 1.0, jib_z + 0.05), 0.0, 0.04, 0.04, 'black')
	rod(name + '_fall', COLL, (jib_to, jib_z - 0.1), (jib_to, z0 + 1.5), -0.02, 0.04, 0.04, 'black')
	box(name + '_hook', COLL, (jib_to - 0.12, -0.12, z0 + 1.3), (jib_to + 0.12, 0.12, z0 + 1.5), 'black')


# --- members -------------------------------------------------------------------------------------------------------

def tanker():
	"""MPS / CS-Inc. oil tanker: bridge aft, pipe deck with catwalk, pump houses, hatches and a kingpost."""
	x0, x1, hw, deck, sheer, bow = -12.0, 12.0, 3.1, 1.9, 0.7, 6.0
	hull(P + 'hull', x0, x1, hw, -0.5, deck, 2.3, bow, 2.5, sheer)
	# Accommodation aft: three tiers, the wheelhouse on top, funnel behind it.
	deckhouse(P + 'house0', -11.4, -7.2, 2.7, deck, 3.4, rows=[(2.5, 2.95)], front_rows=[(2.5, 2.95)])
	deckhouse(P + 'house1', -11.1, -7.5, 2.4, 3.4, 4.8, rows=[(3.85, 4.3)], front_rows=[(3.85, 4.3)], roof='plaster_white')
	deckhouse(P + 'house2', -10.7, -7.8, 2.1, 4.88, 6.0, rows=[(5.2, 5.6)], front_rows=[(5.2, 5.6)])
	bridge(P + 'bridge', -9.9, -7.8, 1.9, 6.0, 7.1, 3.15)
	funnel(P + 'funnel', -10.6, 0.0, 0.75, 0.6, 6.0, 8.9)
	box(P + 'funnel_band', COLL, (-11.37, -0.62, 7.9), (-9.83, 0.62, 8.15), 'plaster_white')
	mast(P + 'aft_mast', -8.4, 7.22, 9.4, yard=0.8)
	radar(P + 'radar', -9.3, 7.22)
	rails(P + 'house_rails', -11.1, -7.5, 2.4, 4.88)
	for s in (1, -1):
		lifeboat(P + f'boat{s}', -9.2, s * 3.05, 2.9)
	# Cargo deck: three pipelines and a raised catwalk running forward, hatches, pump houses and the manifold.
	for k, y in enumerate((-0.75, 0.0, 0.75)):
		cyl_x(P + f'pipe{k}', COLL, y, deck + 0.22, 0.12, -7.0, 9.4, 6, 'steel_light')
	box(P + 'catwalk', COLL, (-7.0, -0.35, deck + 0.75), (9.6, 0.35, deck + 0.82), 'steel')
	for x in spread(-6.5, 9.0, 6):
		box(P + f'catwalk_leg{x:.1f}', COLL, (x - 0.06, -0.06, deck), (x + 0.06, 0.06, deck + 0.75), 'steel')
	for x in (-5.4, -2.6, 2.6, 5.4, 8.0):
		for s in (1, -1):
			cyl_z(P + f'hatch{x}{s}', COLL, x, s * 1.75, 0.5, 0.5, deck, deck + 0.3, 10, 'steel_light', cap_mat='steel')
			cyl_z(P + f'hatch_lid{x}{s}', COLL, x, s * 1.75, 0.3, 0.3, deck + 0.3, deck + 0.38, 8, 'black')
	box(P + 'manifold', COLL, (-0.3, -2.6, deck + 0.05), (0.3, 2.6, deck + 0.55), 'steel_light')
	for s in (1, -1):
		cyl_x(P + f'manifold_valve{s}', COLL, s * 2.2, deck + 0.75, 0.18, -0.25, 0.25, 6, 'signal_red')
	box(P + 'pumphouse_aft', COLL, (-6.6, -2.5, deck), (-5.4, -0.9, deck + 1.1), 'cc1')
	box(P + 'pumphouse_fore', COLL, (8.8, 0.9, deck), (10.2, 2.4, deck + 1.1), 'cc1')
	box(P + 'pumphouse_mid', COLL, (0.8, -2.3, deck), (2.0, -1.0, deck + 1.0), 'cc1')
	# Kingpost and derrick for the hoses, forecastle mast, anchors and bollards.
	cyl_z(P + 'kingpost', COLL, 0.0, 0.0, 0.16, 0.16, deck + 0.55, deck + 4.2, 8, 'steel_light')
	rod(P + 'derrick', COLL, (0.0, deck + 1.2), (2.4, deck + 3.4), 0.05, 0.12, 0.1, 'steel_light')
	mast(P + 'fore_mast', 10.6, deck_top(10.6, x1 - bow, deck, sheer, bow), 6.6, yard=0.6)
	anchors(P + 'anchor', 10.9, hw * 0.45, 1.9)
	bollards(P + 'bollard', (-11.6, 9.4), 2.3, deck)


def ferry():
	"""MPS / FFP / Chugger-Chug / Shivershake passenger ferry: two saloon decks with lifeboats, a bridge tower forward."""
	x0, x1, hw, deck, sheer, bow = -8.5, 8.5, 2.75, 1.6, 0.4, 4.3
	hull(P + 'hull', x0, x1, hw, -0.4, deck, 2.0, bow, 1.6, sheer)
	box(P + 'rubbing_strake', COLL, (x0 + 0.6, -hw - 0.05, 1.05), (x1 - bow + 0.5, hw + 0.05, 1.2), 'black')
	# Main saloon, its promenade roof, the upper saloon with the cc1 sun deck roof.
	deckhouse(P + 'saloon', -5.6, 3.9, 2.45, deck, 3.25, rows=[(2.25, 2.85)], front_rows=[(2.25, 2.85)], pane=0.42, pitch=0.6)
	box(P + 'saloon_roof', COLL, (-5.8, -2.6, 3.25), (4.0, 2.6, 3.35), 'plaster_white')
	for s in (1, -1):
		box(P + f'door{s}', COLL, (-4.9, min(s * 2.45, s * 2.48), deck), (-4.3, max(s * 2.45, s * 2.48), 2.9), 'steel')
	deckhouse(P + 'upper', -4.4, 2.6, 2.0, 3.35, 4.55, rows=[(3.75, 4.2)], front_rows=[(3.75, 4.2)], pane=0.4, pitch=0.55)
	box(P + 'sun_deck', COLL, (-4.5, -2.1, 4.55), (2.7, 2.1, 4.65), 'plaster_white')
	box(P + 'sun_deck_panel', COLL, (-2.6, -1.3, 4.65), (1.6, 1.3, 4.7), 'cc1')
	rails(P + 'promenade', -5.8, 2.6, 2.55, 3.35)
	rails(P + 'sun_rails', -4.5, 1.0, 2.05, 4.65, h=0.35)
	for x in (-3.0, -0.5):
		for s in (1, -1):
			lifeboat(P + f'boat{x}{s}', x, s * 2.25, 3.35, length=1.9, mat='signal_red')
	# Bridge tower forward, funnel and mast aft.
	deckhouse(P + 'tower', 2.6, 4.0, 1.5, 3.35, 5.7, rows=[(3.7, 4.0), (4.35, 4.65)], front_rows=[(3.7, 4.0), (4.35, 4.65)], pane=0.28, pitch=0.45)
	bridge(P + 'bridge', 2.5, 4.1, 1.55, 5.7, 6.55, 2.2)
	radar(P + 'radar', 3.0, 6.67)
	mast(P + 'mast', 3.6, 6.67, 8.3, yard=0.6)
	funnel(P + 'funnel', -3.3, 0.0, 0.55, 0.45, 4.65, 6.4, mat='steel_light')
	mast(P + 'aft_mast', -5.3, 3.35, 6.2, yard=0.4)
	# Open decks fore and aft.
	bollards(P + 'bollard', (-7.7, 6.4), 1.9, deck)
	mast(P + 'jack', 7.6, deck_top(7.6, x1 - bow, deck, sheer, bow), 3.6, yard=0.2)
	anchors(P + 'anchor', 7.4, hw * 0.5, 1.6)
	box(P + 'capstan', COLL, (5.8, -0.4, deck), (6.4, 0.4, deck + 0.35), 'steel')


def skirt_profile(h, hw):
	"""Half profile of the hovercraft at plan half-width h: rubber skirt, cc1 band, white topsides, grey deck."""
	k = h / hw
	pts = [(0.0, 0.25), (0.75 * h, 0.25), (h, 0.7), (h - 0.05 * k, 1.2), (h - 0.1 * k, 1.85), (h - 0.12 * k, 2.85),
		(h - 0.35 * k, 3.0), (0.0, 3.0)]
	return pts


def hovercraft():
	"""Bakewell 300 hovercraft: rubber skirt, cc1 band, white hull, four pylon propellers and twin tail fins."""
	x0, x1, hw, R = -9.25, 9.25, 3.7, 2.8
	xs = []
	for k in range(7):
		a = math.pi / 2 * (1 - k / 6)
		xs.append((x0 + R - R * math.sin(a), math.cos(a)))
	xs += [(x1 - R + R * math.sin(math.pi / 2 * k / 6), math.cos(math.pi / 2 * k / 6)) for k in range(7)]
	xs = [(x, max(0.06, c)) for x, c in xs]
	verts, faces, mats = [], [], []
	ring_mats = ['rubber', 'rubber', 'rubber', 'cc1', 'plaster_white', 'plaster_white', 'concrete']
	n = 14
	for x, c in xs:
		h = hw - R + R * c
		right = skirt_profile(h, hw)
		left = [(-y, z) for y, z in reversed(right[1:-1])]
		verts += [(x, y, z) for y, z in right + left]
	for s in range(len(xs) - 1):
		for i in range(n):
			a, b = s * n + i, s * n + (i + 1) % n
			faces.append((a, b, b + n, a + n))
			mats.append(ring_mats[i] if i < 7 else ring_mats[13 - i])
	last = (len(xs) - 1) * n
	faces += [tuple(range(n)), tuple(range(last, last + n))]
	mats += ['plaster_white', 'plaster_white']
	mesh(P + 'hull', COLL, verts, faces, mats)
	# Cabin windows along both sides and the cockpit forward.
	for s in (1, -1):
		panes(P + f'windows{s}', spread(-6.0, 5.8, 18), s * (hw - 0.11), 2.15, 2.5, 0.3)
	box(P + 'cockpit', COLL, (5.2, -1.3, 3.0), (7.3, 1.3, 4.3), 'plaster_white')
	box(P + 'cockpit_glass', COLL, (5.6, -1.33, 3.65), (7.33, 1.33, 4.15), 'glass_dark')
	box(P + 'cockpit_roof', COLL, (5.1, -1.4, 4.3), (7.45, 1.4, 4.4), 'concrete')
	cyl_z(P + 'cockpit_beacon', COLL, 6.0, 0.0, 0.1, 0.1, 4.4, 4.65, 6, 'signal_red')
	box(P + 'cockpit_aerial', COLL, (5.4, -0.04, 4.4), (5.48, 0.04, 5.4), 'steel_light')
	# Passenger cabin roofs either side of the central car deck.
	for s in (1, -1):
		box(P + f'cabin_roof{s}', COLL, (-6.6, min(s * 1.45, s * 3.25), 3.0), (5.0, max(s * 1.45, s * 3.25), 3.3), 'concrete')
		for x in spread(-5.6, 4.0, 5):
			box(P + f'vent{s}{x:.1f}', COLL, (x - 0.3, s * 2.6 - 0.25, 3.3), (x + 0.3, s * 2.6 + 0.25, 3.45), 'concrete_dark')
	box(P + 'car_deck', COLL, (-7.2, -1.45, 3.0), (5.0, 1.45, 3.08), 'concrete_dark')
	# Deck markings and walkways.
	for s in (1, -1):
		for x in (-2.2, 1.6):
			box(P + f'mark{x}{s}', COLL, (x - 1.0, s * 1.9 - 0.12, 3.3), (x + 1.0, s * 1.9 + 0.12, 3.33), 'signal_red')
	# Four propeller pylons: red post on a fairing, nacelle and a four-bladed propeller turning about X, rudder behind.
	for px in (-5.0, 3.4):
		for s in (1, -1):
			y, zc = s * 2.3, 6.5
			nm = P + f'pylon{px}{s}'
			box(nm + '_foot', COLL, (px - 0.7, y - 0.4, 3.3), (px + 0.7, y + 0.4, 3.7), 'signal_red')
			box(nm, COLL, (px - 0.2, y - 0.16, 3.7), (px + 0.3, y + 0.16, zc - 0.2), 'signal_red')
			capsule_x(nm + '_nacelle', y, zc, 0.34, 0.34, px - 0.9, px + 1.1, 8, 'signal_red')
			box(nm + '_rudder', COLL, (px - 1.9, y - 0.05, zc - 1.4), (px - 1.5, y + 0.05, zc + 1.4), 'signal_red')
			box(nm + '_rudder_arm', COLL, (px - 1.6, y - 0.05, zc - 1.5), (px - 0.4, y + 0.05, zc - 1.35), 'signal_red')
			hub_x = px - 0.85
			cyl_x(nm + '_spinner', COLL, y, zc, 0.16, hub_x - 0.25, hub_x, 6, 'black')
			for b in range(4):
				a = math.pi / 4 + b * math.pi / 2
				ca, sa = math.cos(a), math.sin(a)
				w, r0, r1 = 0.14, 0.15, 1.45
				q = [(y + ca * r0 - sa * w, zc + sa * r0 + ca * w), (y + ca * r1 - sa * w * 0.6, zc + sa * r1 + ca * w * 0.6),
					(y + ca * r1 + sa * w * 0.6, zc + sa * r1 - ca * w * 0.6), (y + ca * r0 + sa * w, zc + sa * r0 - ca * w)]
				v = [(hub_x, py, pz) for py, pz in q] + [(hub_x - 0.08, py, pz) for py, pz in q]
				mesh(nm + f'_blade{b}', COLL, v, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (2, 6, 7, 3)], ['black'] * 4)
	# Twin tail fins aft, raked back.
	for s in (1, -1):
		y = s * 1.1
		prof = [(-9.0, 3.0), (-6.6, 3.0), (-7.8, 6.6), (-9.0, 6.9)]
		v = [(x, y - 0.09, z) for x, z in prof] + [(x, y + 0.09, z) for x, z in prof]
		f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
		mesh(P + f'fin{s}', COLL, v, f, ['plaster_white'] * 6)
		box(P + f'fin_stripe{s}', COLL, (-8.9, y - 0.11, 5.6), (-7.6, y + 0.11, 5.85), 'cc1')


def cargo_ship():
	"""Yate / Bakewell / MightyMover / Powernaut cargo ship: two holds, two deck cranes, accommodation aft."""
	x0, x1, hw, deck, sheer, bow = -14.0, 14.0, 3.2, 1.9, 0.8, 6.5
	hull(P + 'hull', x0, x1, hw, -0.5, deck, 2.3, bow, 2.6, sheer)
	# Holds with raised coamings and black hatch covers, panel joints across them.
	for k, (a, b) in enumerate(((-7.6, 1.2), (2.6, 10.4))):
		box(P + f'coaming{k}', COLL, (a, -2.45, deck), (b, 2.45, deck + 0.6), 'deck_olive')
		box(P + f'cover{k}', COLL, (a + 0.1, -2.35, deck + 0.6), (b - 0.1, 2.35, deck + 0.78), 'coal')
		for x in spread(a, b, 4)[:-1]:
			jx = x + (b - a) / 8
			box(P + f'joint{k}{jx:.1f}', COLL, (jx - 0.05, -2.36, deck + 0.78), (jx + 0.05, 2.36, deck + 0.8), 'steel')
		for s in (1, -1):
			box(P + f'cleats{k}{s}', COLL, (a + 0.3, min(s * 2.45, s * 2.5), deck + 0.3), (b - 0.3, max(s * 2.45, s * 2.5), deck + 0.4), 'steel')
	crane(P + 'crane_aft', 1.9, deck, -2.6, deck + 4.6)
	crane(P + 'crane_fore', 11.0, deck_top(11.0, x1 - bow, deck, sheer, bow), 6.6, deck + 5.0)
	# Accommodation: three tiers with window grids, the wheelhouse, funnel and lifeboats.
	deckhouse(P + 'house0', -12.6, -8.4, 2.8, deck, 3.5, rows=[(2.55, 3.0)], front_rows=[(2.55, 3.0)], pane=0.36)
	deckhouse(P + 'house1', -12.3, -8.6, 2.6, 3.5, 5.0, rows=[(3.95, 4.4)], front_rows=[(3.95, 4.4)], roof='plaster_white', pane=0.36)
	deckhouse(P + 'house2', -11.9, -8.9, 2.3, 5.08, 6.2, rows=[(5.4, 5.8)], front_rows=[(5.4, 5.8)], pane=0.36)
	bridge(P + 'bridge', -11.0, -8.9, 2.0, 6.2, 7.3, 3.25)
	funnel(P + 'funnel', -11.6, 0.0, 0.8, 0.65, 6.2, 9.0)
	box(P + 'funnel_band', COLL, (-12.42, -0.67, 7.9), (-10.78, 0.67, 8.15), 'plaster_white')
	mast(P + 'aft_mast', -9.6, 7.42, 9.6, yard=0.8)
	radar(P + 'radar', -10.4, 7.42)
	rails(P + 'house_rails', -12.3, -8.6, 2.6, 5.08)
	for s in (1, -1):
		lifeboat(P + f'boat{s}', -10.6, s * 3.15, 3.0, length=1.9)
	# Poop deck machinery aft: mooring winches and a small stores crane.
	for s in (1, -1):
		cyl_x(P + f'winch{s}', COLL, s * 1.3, deck + 0.45, 0.4, -13.5, -12.9, 10, 'signal_red', cap_mat='steel')
		box(P + f'winch_base{s}', COLL, (-13.6, s * 1.3 - 0.45, deck), (-12.8, s * 1.3 + 0.45, deck + 0.3), 'steel')
	cyl_z(P + 'stores_post', COLL, -12.9, 0.0, 0.14, 0.14, deck, deck + 2.6, 6, 'paint_orange')
	rod(P + 'stores_jib', COLL, (-12.9, deck + 2.3), (-13.8, deck + 2.9), 0.0, 0.12, 0.1, 'paint_orange')
	# Forecastle: mast, windlass, anchors; bollards along the deck.
	mast(P + 'fore_mast', 12.8, deck_top(12.8, x1 - bow, deck, sheer, bow), 6.8, yard=0.5)
	box(P + 'windlass', COLL, (11.9, -0.9, deck_top(11.9, x1 - bow, deck, sheer, bow)), (12.4, 0.9, deck_top(11.9, x1 - bow, deck, sheer, bow) + 0.45), 'steel')
	anchors(P + 'anchor', 12.7, hw * 0.45, 2.0)
	bollards(P + 'bollard', (-13.3, 1.9, 10.8), 2.5, deck)


{0: tanker, 2: ferry, 4: hovercraft, 7: cargo_ship}[N]()
result = {'default': triangles(COLL)}
