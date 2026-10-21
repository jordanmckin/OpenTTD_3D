"""Temperate road vehicles: buses (road_000-003) and lorries (road_007-039), three makers per cargo.
Each lorry is a road_kit cab (style = the maker's place in its cargo group) and chassis with a cargo body.
Run in Blender with the member's .blend open, after vehicle_kit.py and road_kit.py have been executed in the
same namespace, with KEY set to the member's inventory key."""
import math
import bpy

sync_palette()
N = int(KEY.split('_')[1])
GROUPS = {'bus': (0, 1, 2, 3), 'coal': (7, 8, 9), 'mail': (10, 11, 12), 'oil': (16, 17, 18), 'livestock': (19, 20, 21),
	'goods': (22, 23, 24), 'grain': (25, 26, 27), 'wood': (28, 29, 30), 'ore': (31, 32, 33), 'steel': (34, 35, 36),
	'armoured': (37, 38, 39)}
CARGO, STYLE = next((c, g.index(N)) for c, g in GROUPS.items() if N in g)
BW = 1.6  # body half width
BED_Z1 = 3.55  # open body top
VAN_TOP = 4.45  # box body eaves


def side(s, x0, x1, z0, z1, mat, out=0.03, half=BW):
	y = s * half
	return box(f'{COLL.name}_side{s}_{x0:.2f}_{z0:.2f}_{mat}', COLL, (x0, min(y, y + s * out), z0), (x1, max(y, y + s * out), z1), mat)


def subframe(p):
	box(p + 'subframe', COLL, (BED_X0, -1.0, 1.3), (BED_X1, 1.0, BED_Z0), 'black')


def tipper(p, state, mat, load, peak, ribs=4):
	"""Tipper body on a subframe; headboard over the cab; tailgate hinges (the approved coal truck body)."""
	subframe(p)
	open_wagon(p + 'bed', COLL, BED_X0, BED_X1, BW, BED_Z0, BED_Z1, mat, ribs=ribs, floor_mat='concrete_dark')
	box(p + 'headboard', COLL, (BED_X1 - 0.12, -1.48, BED_Z1), (BED_X1, 1.48, 4.25), mat)
	for y in (-1.2, 0, 1.2):
		box(p + f'headboard_rib{y}', COLL, (BED_X1, y - 0.06, BED_Z0), (BED_X1 + 0.06, y + 0.06, 4.25), mat)
	for s in (1, -1):
		box(p + f'tailgate_hinge{s}', COLL, (BED_X0 - 0.1, s * 1.35 - 0.1, BED_Z1 - 0.2), (BED_X0, s * 1.35 + 0.1, BED_Z1 + 0.05), 'black')
		box(p + f'tailgate_catch{s}', COLL, (BED_X0 - 0.08, s * 1.35 - 0.08, BED_Z0 + 0.1), (BED_X0, s * 1.35 + 0.08, BED_Z0 + 0.35), 'black')
	if state == 'loaded':
		bulk_load(p + 'load', COLL, BED_X0 + 0.12, BED_X1 - 0.12, 1.48, BED_Z1 - 0.3, peak, load, nx=10, ny=6, seed=123 if N == 7 else N)  # 123: the approved coal truck's heap


def van_body(p, roof_mat='roof_dark', body='cc1', top=VAN_TOP, rise=0.3):
	"""Box body with a shallow curved roof and rear doors; returns nothing, details are added by the caller."""
	subframe(p)
	box(p + 'body', COLL, (BED_X0, -BW, BED_Z0), (BED_X1, BW, top), body)
	h = BW + 0.05
	prof = [(0.0, top)] + mirror_y([(h, top), (h - 0.05, top + rise * 0.5), (h * 0.7, top + rise * 0.85), (0.0, top + rise)]) + [(0.0, top)]
	loft(p + 'roof', COLL, [(BED_X0 - 0.05, prof), (BED_X1 + 0.05, prof)], roof_mat, cap_front=roof_mat, cap_back=roof_mat)
	for s in (1, -1):
		side(s, BED_X0, BED_X1, BED_Z0, BED_Z0 + 0.12, 'black', out=0.04)
	# Rear doors: centre split, hinges, locking bars.
	box(p + 'door_split', COLL, (BED_X0 - 0.03, -0.03, BED_Z0 + 0.1), (BED_X0, 0.03, top - 0.1), 'black')
	for s in (1, -1):
		for z in (BED_Z0 + 0.5, top - 0.5):
			box(p + f'rear_hinge{s}{z}', COLL, (BED_X0 - 0.05, s * 1.45 - 0.08, z - 0.06), (BED_X0, s * 1.45 + 0.08, z + 0.06), 'black')
		box(p + f'lock_bar{s}', COLL, (BED_X0 - 0.06, s * 0.35 - 0.03, BED_Z0 + 0.2), (BED_X0, s * 0.35 + 0.03, top - 0.2), 'steel_light')


def mail(p, state):
	van_body(p)
	for s in (1, -1):
		side(s, -1.6, -0.6, BED_Z0 + 0.15, VAN_TOP - 0.25, 'black', out=0.035)  # side door
		side(s, -1.55, -0.65, BED_Z0 + 0.2, VAN_TOP - 0.3, 'cc1', out=0.05)
		side(s, -0.82, -0.74, 2.9, 3.2, 'steel_light', out=0.07)
		side(s, -3.3, -2.0, 3.3, 3.9, 'plaster_white', out=0.04)  # post panel
		side(s, -3.2, -2.1, 3.55, 3.65, 'signal_red', out=0.05)
		side(s, BED_X0, BED_X1, 2.55, 2.65, 'cc2', out=0.04)


def goods(p, state):
	van_body(p)
	for s in (1, -1):
		for k in range(9):
			x = BED_X0 + 0.15 + (BED_X1 - BED_X0 - 0.3) * k / 8
			side(s, x - 0.05, x + 0.05, BED_Z0 + 0.12, VAN_TOP - 0.05, 'cc1', out=0.07)
		side(s, BED_X0, BED_X1, VAN_TOP - 0.15, VAN_TOP, 'black', out=0.05)


def livestock(p, state):
	van_body(p, top=VAN_TOP)
	# Slatted sides: dark openings between cc1 slats on the upper body.
	for s in (1, -1):
		side(s, BED_X0 + 0.15, BED_X1 - 0.15, 2.7, VAN_TOP - 0.15, 'black', out=0.02)
		for z in (2.7, 3.15, 3.6, 4.05):
			side(s, BED_X0, BED_X1, z, z + 0.18, 'cc1', out=0.05)
		for k in range(7):
			x = BED_X0 + 0.1 + (BED_X1 - BED_X0 - 0.2) * k / 6
			side(s, x - 0.07, x + 0.07, BED_Z0 + 0.12, VAN_TOP, 'cc1', out=0.08)
	box(p + 'ramp', COLL, (BED_X0 - 0.08, -1.3, BED_Z0 + 0.15), (BED_X0, 1.3, 3.6), 'cc1')  # loading ramp door
	for z in (2.3, 3.0):
		box(p + f'ramp_bar{z}', COLL, (BED_X0 - 0.12, -1.25, z), (BED_X0 - 0.08, 1.25, z + 0.06), 'black')


def armoured(p, state):
	van_body(p, roof_mat='cc1', top=4.3, rise=0.42)
	for s in (1, -1):
		for k in range(1, 5):
			x = BED_X0 + (BED_X1 - BED_X0) * k / 5
			side(s, x - 0.025, x + 0.025, BED_Z0 + 0.12, 4.2, 'black', out=0.04)
		for z in (2.15, 4.05):
			for k in range(11):
				x = BED_X0 + 0.2 + (BED_X1 - BED_X0 - 0.4) * k / 10
				side(s, x - 0.05, x + 0.05, z - 0.05, z + 0.05, 'steel', out=0.06)
		side(s, -0.9, -0.1, BED_Z0 + 0.2, 3.9, 'cc1', out=0.07)  # side door
		side(s, -0.75, -0.25, 2.85, 3.1, 'plaster_white', out=0.08)
		side(s, -0.25, -0.15, 2.5, 2.65, 'steel_light', out=0.1)
		for x in (-3.0, 0.6):  # barred spy windows
			side(s, x - 0.18, x + 0.18, 3.45, 3.75, 'glass_dark', out=0.04)
			side(s, x - 0.02, x + 0.02, 3.45, 3.75, 'black', out=0.06)


def oil(p, state):
	subframe(p)
	box(p + 'deck', COLL, (BED_X0, -1.5, BED_Z0), (BED_X1, 1.5, BED_Z0 + 0.12), 'black')
	ry, rz, seg = 1.42, 1.08, 20
	cz = BED_Z0 + 0.12 + rz
	ring_at = lambda k: [(ry * k * math.cos(2 * math.pi * i / seg), cz + rz * k * math.sin(2 * math.pi * i / seg)) for i in range(seg + 1)]
	x0, x1 = BED_X0 + 0.05, BED_X1 - 0.1
	loft(p + 'tank', COLL, [(x0 - 0.12, ring_at(0.55)), (x0, ring_at(0.92)), (x0 + 0.12, ring_at(1.0)), (x1 - 0.12, ring_at(1.0)), (x1, ring_at(0.92)), (x1 + 0.1, ring_at(0.55))], 'cc1', cap_front='cc1', cap_back='cc1')
	mid = (x0 + x1) / 2
	loft(p + 'band', COLL, [(mid - 0.5, ring_at(1.02)), (mid + 0.5, ring_at(1.02))], 'wagon_grey')
	for x in (x0 + 0.8, x1 - 0.8):
		loft(p + f'strap{x}', COLL, [(x - 0.05, ring_at(1.03)), (x + 0.05, ring_at(1.03))], 'black')
	cyl_z(p + 'manhole', COLL, mid, 0.0, 0.38, 0.38, cz + rz - 0.1, cz + rz + 0.18, 12, 'wagon_grey')
	cyl_z(p + 'lid', COLL, mid, 0.0, 0.24, 0.24, cz + rz + 0.18, cz + rz + 0.26, 10, 'black')
	box(p + 'walkway', COLL, (x0 + 0.3, -0.35, cz + rz - 0.02), (x1 - 0.3, 0.35, cz + rz + 0.03), 'black')
	for s in (1, -1):
		box(p + f'handrail{s}', COLL, (x0 + 0.3, s * 0.95 - 0.03, cz + rz * 0.8), (x1 - 0.3, s * 0.95 + 0.03, cz + rz * 0.8 + 0.06), 'steel_light')
		box(p + f'hose_box{s}', COLL, (-1.5, min(s * 1.2, s * 1.55), 1.2), (-0.4, max(s * 1.2, s * 1.55), BED_Z0), 'black')
	box(p + 'ladder', COLL, (BED_X0 - 0.12, -0.3, BED_Z0), (BED_X0 - 0.06, 0.3, cz + rz), 'steel_light')
	cyl_x(p + 'outlet', COLL, 0.0, 1.55, 0.12, BED_X0 - 0.2, BED_X0 + 0.1, 8, 'black')


def flat(p, stakes):
	subframe(p)
	box(p + 'deck', COLL, (BED_X0, -BW, BED_Z0), (BED_X1, BW, BED_Z0 + 0.22), 'wood')
	for k in range(10):
		x = BED_X0 + 0.2 + (BED_X1 - BED_X0 - 0.4) * k / 9
		box(p + f'plank{k}', COLL, (x - 0.02, -BW, BED_Z0 + 0.22), (x + 0.02, BW, BED_Z0 + 0.24), 'wood_dark')
	for s in (1, -1):
		side(s, BED_X0, BED_X1, BED_Z0 - 0.08, BED_Z0 + 0.25, 'black', out=0.05)
		for k in range(stakes):
			x = BED_X0 + 0.25 + (BED_X1 - BED_X0 - 0.5) * k / max(stakes - 1, 1)
			box(p + f'stake{s}{k}', COLL, (x - 0.07, s * (BW - 0.02) - 0.07, BED_Z0 + 0.1), (x + 0.07, s * (BW - 0.02) + 0.07, BED_Z0 + 1.7), 'black')
	# Headboard: a cc1 frame behind the cab with a mesh of bars.
	box(p + 'headboard', COLL, (BED_X1 - 0.1, -1.5, BED_Z0 + 0.22), (BED_X1, 1.5, 4.3), 'black')
	for y in (-1.5, 1.4):
		box(p + f'headboard_post{y}', COLL, (BED_X1 - 0.14, y, BED_Z0 + 0.22), (BED_X1 + 0.02, y + 0.1, 4.35), 'cc1')
	box(p + 'headboard_top', COLL, (BED_X1 - 0.14, -1.5, 4.25), (BED_X1 + 0.02, 1.5, 4.35), 'cc1')
	for z in (2.8, 3.5):
		box(p + f'headboard_rail{z}', COLL, (BED_X1 - 0.13, -1.5, z), (BED_X1 + 0.01, 1.5, z + 0.07), 'cc1')


def wood(p, state):
	flat(p, 4)
	if state != 'loaded':
		return
	# Two bundles of logs lying across the deck, chained down with company-colour binders.
	r, base = 0.34, BED_Z0 + 0.24
	for b, xc in enumerate((-2.55, -0.55)):
		for j, n in enumerate((3, 2, 1)):
			for k in range(n):
				x = xc + (k - (n - 1) / 2) * 2 * r
				z = base + r + j * r * 1.72
				ys = 1.42 - 0.06 * ((b + j + k) % 3)
				disc_y(p + f'log{b}{j}{k}', COLL, x, z, r, -ys, ys, 8, 'wood', side_mat='bark', cap_both=True)
		for y in (-0.9, 0.9):
			path = [(xc - 3 * r - 0.04, base + 0.05), (xc - 3 * r - 0.04, base + r + 0.1), (xc - r - 0.1, base + 2 * r * 1.72 + 0.2), (xc, base + 2 * r * 1.72 + r + 0.04)]
			outer = path + [(2 * xc - x, z) for x, z in reversed(path[:-1])]
			inner = [(xc + (x - xc) * 0.96, z - 0.05) for x, z in reversed(outer)]
			band = outer + inner + [outer[0]]
			v = [(x, y - 0.06, z) for x, z in band] + [(x, y + 0.06, z) for x, z in band]
			n = len(band)
			faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)] + [tuple(range(n - 1)), tuple(range(2 * n - 2, n - 1, -1))]
			mesh(p + f'binder{b}{y}', COLL, v, faces, ['cc1'] * (n + 1))


def steel(p, state):
	flat(p, 0)
	if state != 'loaded':
		return
	r, base = 0.78, BED_Z0 + 0.24
	for x in (-2.55, -0.45):
		cz = base + r + 0.1
		disc_y(p + f'coil{x}', COLL, x, cz, r, -1.0, 1.0, 16, 'steel_light', cap_both=True)
		for s in (1, -1):
			disc_y(p + f'eye{x}{s}', COLL, x, cz, 0.28, s * 1.0, s * 1.02, 10, 'black')
			disc_y(p + f'wrap{x}{s}', COLL, x, cz, 0.58, s * 0.99, s * 1.01, 14, 'steel')
		for k in (-1, 1):
			box(p + f'chock{x}{k}', COLL, (x + k * 0.5 - 0.2, -1.05, base), (x + k * 0.5 + 0.2, 1.05, base + 0.22), 'wood_dark')
		box(p + f'band{x}', COLL, (x - 0.06, -1.03, cz + r - 0.03), (x + 0.06, 1.03, cz + r + 0.03), 'cc1')


BODIES = {
	'coal': lambda p, st: tipper(p, st, 'wagon_grey', 'coal', 1.2),
	'grain': lambda p, st: tipper(p, st, 'wagon_grey', 'grain', 0.55, ribs=2),
	'ore': lambda p, st: tipper(p, st, 'cc1', 'rust', 0.8, ribs=6),
	'mail': mail, 'goods': goods, 'livestock': livestock, 'armoured': armoured, 'oil': oil, 'wood': wood, 'steel': steel,
}


# Buses: single-deck body over both axles; style 3 (Foster MkII) has the raked dark front.
BUS_X, BUS_FRONT, BUS_REAR = 3.8, 2.15, -2.1


def bus(p, state):
	modern = N == 3
	arch = WHEEL_R + 0.12
	lift = ROAD_LIFT + 2 * WHEEL_R + 0.12
	# Lower body in three pieces between the wheel arches.
	box(p + 'lower_back', COLL, (-BUS_X, -BW, 0.95), (BUS_REAR - arch, BW, 2.9), 'cc1')
	box(p + 'lower_arch_r', COLL, (BUS_REAR - arch, -BW, lift), (BUS_REAR + arch, BW, 2.9), 'cc1')
	box(p + 'lower_mid', COLL, (BUS_REAR + arch, -BW, 0.95), (BUS_FRONT - arch, BW, 2.9), 'cc1')
	box(p + 'lower_arch_f', COLL, (BUS_FRONT - arch, -BW, lift), (BUS_FRONT + arch, BW, 2.9), 'cc1')
	box(p + 'lower_front', COLL, (BUS_FRONT + arch, -BW, 0.95), (BUS_X, BW, 2.9), 'cc1')
	for x in (BUS_FRONT, BUS_REAR):  # arch liners, so the arches do not show daylight through the body
		box(p + f'arch_liner{x}', COLL, (x - arch, -1.0, 0.95), (x + arch, 1.0, lift), 'black')
	# Upper body: window band and roof as one loft; the front is raked on the modern bus.
	prof = mirror_y([(BW, 2.9), (BW, 4.3), (1.5, 4.6), (1.25, 4.82), (0.7, 4.95), (0.0, 4.98)])
	if modern:
		stations = [(-BUS_X, prof), (2.9, prof), (BUS_X, mirror_y([(BW, 2.9), (BW - 0.05, 3.0), (BW - 0.1, 3.05), (BW - 0.2, 3.08), (0.7, 3.1), (0.0, 3.1)]))]
		glass = lambda x0, x1, z, i: 'glass_dark' if x0 >= 2.9 and 0 < i < 9 else 'cc1'
	else:
		stations = [(-BUS_X, prof), (BUS_X - 0.08, prof), (BUS_X, mirror_y([(BW - 0.05, 2.9), (BW - 0.05, 4.25), (1.42, 4.55), (1.18, 4.75), (0.66, 4.88), (0.0, 4.9)]))]
		glass = lambda x0, x1, z, i: 'cc1'
	loft(p + 'upper', COLL, stations, 'cc1', cap_back='cc1', cap_front='cc1', mat_fn=glass)
	for s in (1, -1):
		# Entrance door: ahead of the front wheel, or on the raked-front bus just behind it, where the sides are full height.
		d0, d1 = (0.55, 1.18) if modern else (3.05, 3.68)
		dm = (d0 + d1) / 2
		side(s, d0, d1, 1.05, 4.2, 'black', out=0.025)
		side(s, d0 + 0.05, d1 - 0.05, 1.4, 4.1, 'glass_dark', out=0.035)
		side(s, dm - 0.015, dm + 0.015, 1.4, 4.1, 'black', out=0.045)
		# Window band: glass panes between pillars, in runs either side of a mid-body door.
		runs = [(-BUS_X + 0.35, d0 - 0.1, 4), (d1 + 0.14, 2.9, 2)] if modern else [(-BUS_X + 0.35, 2.9, 5 if N == 0 else 6)]
		for xs, xe, panes in runs:
			for k in range(panes):
				xa = xs + (xe - xs) * k / panes
				xb = xs + (xe - xs) * (k + 1) / panes - 0.14
				side(s, xa, xb, 3.15, 4.2, 'glass_dark')
		side(s, -BUS_X, BUS_X, 2.9, 3.0, 'cc2' if N == 1 else 'black', out=0.04)  # waist rail
		side(s, -BUS_X, BUS_X, 0.95, 1.1, 'black', out=0.04)
		box(p + f'tail_light{s}', COLL, (-BUS_X - 0.05, s * 1.25 - 0.12, 1.5), (-BUS_X, s * 1.25 + 0.12, 1.9), 'signal_red')
		if modern:
			box(p + f'headlight{s}', COLL, (BUS_X, s * 1.1 - 0.28, 1.6), (BUS_X + 0.05, s * 1.1 + 0.28, 1.85), 'lamp_yellow')
		else:
			cyl_x(p + f'headlight{s}', COLL, s * 1.15, 1.75, 0.22, BUS_X - 0.05, BUS_X + 0.08, 10, 'steel_light', cap_mat='lamp_yellow')
		mx = 3.05 if modern else BUS_X  # on the raked bus, mount the mirrors where the sides are still full height
		box(p + f'mirror{s}', COLL, (mx - 0.1, min(s * 1.6, s * 1.95), 3.6), (mx, max(s * 1.6, s * 1.95), 4.1), 'black')
	if not modern:
		box(p + 'windscreen', COLL, (BUS_X, -1.4, 3.0), (BUS_X + 0.03, 1.4, 4.15), 'glass_dark')
		box(p + 'screen_pillar', COLL, (BUS_X + 0.03, -0.04, 3.0), (BUS_X + 0.05, 0.04, 4.15), 'cc1')
		box(p + 'destination', COLL, (BUS_X - 0.02, -1.1, 4.25), (BUS_X + 0.02, 1.1, 4.55), 'black')
		box(p + 'destination_text', COLL, (BUS_X + 0.02, -0.9, 4.33), (BUS_X + 0.03, 0.9, 4.47), 'lamp_yellow')
		box(p + 'grille', COLL, (BUS_X, -0.7, 1.4), (BUS_X + 0.04, 0.7, 2.3), 'steel_light')
	else:
		box(p + 'grille', COLL, (BUS_X, -1.4, 1.3), (BUS_X + 0.04, 1.4, 2.3), 'black')
	box(p + 'bumper', COLL, (BUS_X, -BW, 0.95), (BUS_X + 0.15, BW, 1.3), 'black')
	box(p + 'bumper_rear', COLL, (-BUS_X - 0.15, -BW, 0.95), (-BUS_X, BW, 1.3), 'black')
	box(p + 'rear_window', COLL, (-BUS_X - 0.03, -1.3, 3.2), (-BUS_X, 1.3, 4.15), 'glass_dark')
	box(p + 'engine_grille', COLL, (-BUS_X - 0.03, -1.0, 1.5), (-BUS_X, 1.0, 2.5), 'black')
	for k in range(4):
		box(p + f'engine_slat{k}', COLL, (-BUS_X - 0.06, -0.95, 1.6 + 0.24 * k), (-BUS_X - 0.03, 0.95, 1.68 + 0.24 * k), 'steel')
	for k in range(3 if N != 3 else 2):  # roof vents / air conditioning pod on the modern bus
		x = -2.2 + 2.0 * k
		if modern:
			box(p + f'ac{k}', COLL, (x - 0.7, -0.8, 4.92), (x + 0.7, 0.8, 5.15), 'wagon_grey')
		else:
			box(p + f'vent{k}', COLL, (x - 0.3, -0.3, 4.9), (x + 0.3, 0.3, 5.05), 'black')
	for s in (1, -1):
		road_wheel(p + f'front{s}', COLL, BUS_FRONT, WHEEL_R, s, 1.5, width=0.42)
		road_wheel(p + f'rear{s}', COLL, BUS_REAR, WHEEL_R, s, 1.5, width=0.42)
		road_wheel(p + f'rear_in{s}', COLL, BUS_REAR, WHEEL_R, s, 1.06, width=0.38, inner=True)


def build(state):
	global COLL
	COLL = bpy.data.collections[state]
	clear(COLL)
	p = state + '_'
	if CARGO == 'bus':
		bus(p, state)
	else:
		cab(p, COLL, STYLE)
		BODIES[CARGO](p, state)
		chassis(p, COLL, ram=CARGO in ('coal', 'grain', 'ore'))
		rear(p, COLL)
		truck_wheels(p, COLL)
	return triangles(COLL)


result = {c.name: build(c.name) for c in bpy.data.collections if c.name in ('default', 'empty', 'loaded')}
