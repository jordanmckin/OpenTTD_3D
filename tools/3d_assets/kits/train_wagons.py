"""Temperate wagons 27-37 (rail) and their monorail/maglev twins 57-67: one body per cargo on the shared
rail_underframe or mono_base. The coal trucks (29/59) have their own script, train_coal_wagons.py.
Run in Blender with the member's .blend open, after vehicle_kit.py has been executed in the same namespace,
with KEY set to the member's inventory key."""
import math
import bpy

sync_palette()
N = int(KEY.split('_')[1])
MONO = N >= 57
CARGO = ['passenger', 'mail', None, 'oil', 'livestock', 'goods', 'grain', 'wood', 'ore', 'steel', 'armoured'][N - (57 if MONO else 27)]
X, W, Z0 = 3.4, 1.55, 2.0  # body half length, half width, floor
VAN_TOP = 4.6


def side(s, x0, x1, z0, z1, mat, out=0.03, inset=0.0):
	"""A thin panel on the side s (+1/-1) of the body, proud of the side by out."""
	y = s * (W - inset)
	return box(f'{COLL.name}_side{s}_{x0:.2f}_{z0:.2f}', COLL, (x0, min(y, y + s * out), z0), (x1, max(y, y + s * out), z1), mat)


def roof(p, mat, half=W + 0.08, rise=0.82):
	"""Curved van roof on the body top: overhangs the sides slightly, closed at both ends."""
	# The duplicated centre-bottom point closes the end caps across the bottom edge.
	prof = [(0.0, VAN_TOP)] + mirror_y([(half, VAN_TOP), (half - 0.06, VAN_TOP + rise * 0.42), (half * 0.78, VAN_TOP + rise * 0.74), (half * 0.42, VAN_TOP + rise * 0.93), (0.0, VAN_TOP + rise)]) + [(0.0, VAN_TOP)]
	loft(p + 'roof', COLL, [(-X - 0.06, prof), (X + 0.06, prof)], mat, cap_front=mat, cap_back=mat)


def van(p, roof_mat, body='cc1', top=VAN_TOP):
	box(p + 'body', COLL, (-X, -W, Z0), (X, W, top), body)
	roof(p, roof_mat)
	for s in (1, -1):
		side(s, -X, X, Z0, Z0 + 0.12, 'black', out=0.04)  # sole line under the body
		side(s, -X, X, VAN_TOP - 0.1, VAN_TOP, 'black', out=0.04)  # cant rail under the roof


def gangways(p):
	for e in (1, -1):
		box(p + f'gangway{e}', COLL, (min(e * X, e * (X + 0.2)), -0.65, Z0 + 0.3), (max(e * X, e * (X + 0.2)), 0.65, VAN_TOP - 0.15), 'black')
		for s in (1, -1):
			box(p + f'grab{e}{s}', COLL, (min(e * X, e * (X + 0.04)), s * 1.2 - 0.03, Z0 + 0.6), (max(e * X, e * (X + 0.04)), s * 1.2 + 0.03, VAN_TOP - 0.5), 'steel_light')


def roof_vents(p, n, mat='black'):
	for k in range(n):
		cyl_z(p + f'vent{k}', COLL, -X + 0.8 + (2 * X - 1.6) * k / max(n - 1, 1), 0.0, 0.14, 0.14, VAN_TOP + 0.75, VAN_TOP + 0.95, 8, mat)


def passenger(p, state):
	van(p, 'plaster_white' if MONO else 'roof_dark')
	gangways(p)
	roof_vents(p, 5)
	for s in (1, -1):
		for k in range(7):
			x = -2.55 + 0.85 * k
			side(s, x - 0.3, x + 0.3, 3.35, 4.25, 'glass_dark')
			side(s, x - 0.3, x + 0.3, 3.95, 4.0, 'cc1', out=0.04)  # top-light bar
		for e in (1, -1):  # end doors with a droplight
			x = e * 3.15
			side(s, x - 0.18, x + 0.18, Z0 + 0.25, 4.3, 'black', out=0.035)
			side(s, x - 0.13, x + 0.13, 3.55, 4.2, 'glass_dark', out=0.045)
		side(s, -X, X, 3.2, 3.26, 'cc2', out=0.04)  # waist line


def mail(p, state):
	van(p, 'plaster_white' if MONO else 'roof_dark')
	gangways(p)
	roof_vents(p, 3)
	for s in (1, -1):
		# Centre double doors with a frame, handles and a white post-office panel; small windows at the ends.
		side(s, -0.8, 0.8, Z0 + 0.15, 4.35, 'black', out=0.035)
		side(s, -0.75, -0.03, Z0 + 0.2, 4.3, 'cc1', out=0.05)
		side(s, 0.03, 0.75, Z0 + 0.2, 4.3, 'cc1', out=0.05)
		side(s, -0.15, -0.08, 3.0, 3.3, 'steel_light', out=0.07)
		side(s, 0.08, 0.15, 3.0, 3.3, 'steel_light', out=0.07)
		side(s, -0.5, 0.5, 3.55, 4.05, 'glass_dark', out=0.06)
		side(s, -2.4, -1.4, 2.7, 3.2, 'plaster_white')
		for x in (-2.85, 2.85):
			side(s, x - 0.25, x + 0.25, 3.5, 4.2, 'glass_dark')
		side(s, 1.4, 2.3, 2.5, 2.6, 'cc2')  # letter slot surround
		side(s, 1.5, 2.2, 2.52, 2.58, 'black', out=0.04)


def oil(p, state):
	r, cz, seg = 1.35, Z0 + 0.15 + 1.35, 20
	ring_at = lambda rr: [(rr * math.cos(2 * math.pi * k / seg), cz + rr * math.sin(2 * math.pi * k / seg)) for k in range(seg + 1)]
	stations = [(-X - 0.1, ring_at(0.55)), (-X, ring_at(1.05)), (-X + 0.12, ring_at(r)), (X - 0.12, ring_at(r)), (X, ring_at(1.05)), (X + 0.1, ring_at(0.55))]
	loft(p + 'tank', COLL, stations, 'cc1', cap_front='cc1', cap_back='cc1')
	# Grey centre band and tank straps.
	loft(p + 'band', COLL, [(-0.55, ring_at(r + 0.02)), (0.55, ring_at(r + 0.02))], 'wagon_grey')
	for x in (-2.3, 2.3):
		loft(p + f'strap{x}', COLL, [(x - 0.05, ring_at(r + 0.03)), (x + 0.05, ring_at(r + 0.03))], 'black')
	# Dome with a hatch, safety valves, walkway and ladders.
	cyl_z(p + 'dome', COLL, 0.0, 0.0, 0.5, 0.5, cz + r - 0.1, cz + r + 0.35, 12, 'wagon_grey')
	cyl_z(p + 'hatch', COLL, 0.0, 0.0, 0.3, 0.3, cz + r + 0.35, cz + r + 0.45, 10, 'black')
	for y in (-0.25, 0.25):
		cyl_z(p + f'valve{y}', COLL, 0.7, y, 0.07, 0.07, cz + r - 0.1, cz + r + 0.2, 6, 'steel_light')
	box(p + 'walkway', COLL, (-0.9, -0.45, cz + r - 0.02), (0.9, 0.45, cz + r + 0.04), 'black')
	for s in (1, -1):
		for k in (-1, 1):
			box(p + f'ladder{s}{k}', COLL, (k * 0.35 - 0.03, s * (r + 0.05) - 0.03, Z0 + 0.2), (k * 0.35 + 0.03, s * (r + 0.05) + 0.03, cz + r), 'steel_light')
		for z in range(5):
			zz = Z0 + 0.5 + 0.48 * z
			box(p + f'rung{s}{z}', COLL, (-0.35, s * (r + 0.05) - 0.03, zz), (0.35, s * (r + 0.05) + 0.03, zz + 0.05), 'steel_light')
		box(p + f'handrail{s}', COLL, (-X + 0.3, s * 0.95 - 0.03, cz + r * 0.72), (X - 0.3, s * 0.95 + 0.03, cz + r * 0.72 + 0.06), 'steel_light')
	# Cradle: a frame under the tank with saddles; outlet valve underneath.
	box(p + 'frame', COLL, (-X, -1.45, Z0), (X, 1.45, Z0 + 0.15), 'black')
	for x in (-2.3, 2.3):
		box(p + f'saddle{x}', COLL, (x - 0.2, -1.2, Z0 + 0.1), (x + 0.2, 1.2, Z0 + 0.6), 'black')
	cyl_z(p + 'outlet', COLL, 0.0, 0.0, 0.15, 0.15, Z0 - 0.45, Z0 + 0.15, 8, 'black')


def livestock(p, state):
	# The upper sides are open slats: the body stops at the slat line, a dark inner wall shows between the slats.
	van(p, 'roof_dark', top=3.0)
	roof_vents(p, 2)
	box(p + 'inner', COLL, (-X + 0.08, -W + 0.08, 3.0), (X - 0.08, W - 0.08, VAN_TOP), 'black')
	for e in (1, -1):
		box(p + f'end{e}', COLL, (min(e * X, e * (X - 0.08)), -W, 3.0), (max(e * X, e * (X - 0.08)), W, VAN_TOP), 'cc1')
	for s in (1, -1):
		for z in (3.0, 3.42, 3.84, 4.26):  # slat bands
			side(s, -X, X, z, z + 0.2, 'cc1', out=0.04)
		for k in range(9):
			x = -X + 0.15 + (2 * X - 0.3) * k / 8
			side(s, x - 0.08, x + 0.08, Z0 + 0.12, VAN_TOP - 0.1, 'cc1', out=0.07)
		side(s, -0.75, 0.75, Z0 + 0.12, VAN_TOP - 0.1, 'cc1', out=0.09)  # door
		for z in (Z0 + 0.6, VAN_TOP - 0.5):
			side(s, -0.7, 0.7, z, z + 0.08, 'black', out=0.11)


def goods(p, state):
	van(p, 'roof_dark')
	for s in (1, -1):
		for k in range(10):
			x = -X + 0.2 + (2 * X - 0.4) * k / 9
			if abs(x) < 0.9:
				continue
			side(s, x - 0.06, x + 0.06, Z0 + 0.12, VAN_TOP - 0.1, 'cc1', out=0.07)
		# Sliding door on its top rail and bottom guide, with a handle.
		side(s, -0.85, 0.85, Z0 + 0.1, VAN_TOP - 0.15, 'cc1', out=0.08)
		side(s, -1.0, 2.0, VAN_TOP - 0.2, VAN_TOP - 0.1, 'black', out=0.11)
		side(s, -1.0, 2.0, Z0 + 0.05, Z0 + 0.12, 'black', out=0.11)
		side(s, 0.6, 0.67, 2.9, 3.6, 'steel_light', out=0.12)
		side(s, -0.82, 0.82, 3.3, 3.36, 'black', out=0.09)
	for e in (1, -1):
		for y in (-0.8, 0.0, 0.8):
			box(p + f'endrib{e}{y}', COLL, (min(e * X, e * (X + 0.06)), y - 0.06, Z0), (max(e * X, e * (X + 0.06)), y + 0.06, VAN_TOP - 0.1), 'cc1')


def armoured(p, state):
	van(p, 'plaster_white' if MONO else 'cc1')
	for s in (1, -1):
		for k in range(1, 6):  # panel seams
			x = -X + 2 * X * k / 6
			side(s, x - 0.025, x + 0.025, Z0 + 0.12, VAN_TOP - 0.1, 'black', out=0.04)
		for z in (2.45, 4.25):  # rivet rows
			for k in range(14):
				x = -X + 0.25 + (2 * X - 0.5) * k / 13
				side(s, x - 0.05, x + 0.05, z - 0.05, z + 0.05, 'steel', out=0.06)
		side(s, -0.5, 0.5, Z0 + 0.2, 4.1, 'cc1', out=0.07)  # armoured door
		side(s, -0.55, 0.55, 4.1, 4.15, 'black', out=0.08)
		side(s, -0.3, 0.3, 3.05, 3.35, 'plaster_white', out=0.08)  # number plate
		side(s, 0.3, 0.42, 2.7, 2.85, 'steel_light', out=0.1)  # lock
		for x in (-2.4, 2.4):  # barred spy windows
			side(s, x - 0.2, x + 0.2, 3.75, 4.0, 'glass_dark', out=0.04)
			side(s, x - 0.02, x + 0.02, 3.75, 4.0, 'black', out=0.06)


def open_body(p, mat, ribs, load, peak, z1=4.3, half=W):
	open_wagon(p + 'body', COLL, -X + 0.1, X - 0.1, half, Z0, z1, mat, ribs=ribs, floor_mat='concrete_dark')
	if load:
		bulk_load(p + 'load', COLL, -X + 0.22, X - 0.22, half - 0.12, z1 - 0.3, peak, load, nx=12, ny=6, seed=N)


def grain(p, state):
	open_body(p, 'wagon_grey', 2, 'grain' if state == 'loaded' else None, 0.45, z1=4.4)
	for s in (1, -1):
		side(s, -X + 0.1, X - 0.1, Z0, Z0 + 0.35, 'cc1', out=0.05)  # company stripe along the foot
		for x in (-1.6, 1.6):
			side(s, x - 0.06, x + 0.06, Z0 + 0.35, 4.28, 'wagon_grey', out=0.05)
	# Hopper chutes between the bogies, sloping to discharge doors.
	for k, x in enumerate((-0.75, 0.75)):
		prof = mirror_y([(0.35, 1.25), (1.2, Z0), (0.0, Z0)])
		loft(p + f'chute{k}', COLL, [(x - 0.6, prof), (x + 0.6, prof)], 'wagon_grey', cap_front='wagon_grey', cap_back='wagon_grey')
		box(p + f'gate{k}', COLL, (x - 0.4, -0.4, 1.12), (x + 0.4, 0.4, 1.25), 'black')


def ore(p, state):
	open_body(p, 'cc1', 6, 'rust' if state == 'loaded' else None, 0.65)
	for s in (1, -1):
		side(s, -0.75, 0.75, Z0 + 0.35, 4.0, 'cc1', out=0.1)  # side door
		for z in (Z0 + 0.6, 3.7):
			side(s, -0.7, 0.7, z - 0.05, z + 0.05, 'black', out=0.13)


def flat(p, stakes, stake_h=1.6):
	box(p + 'deck', COLL, (-X - 0.1, -W, Z0), (X + 0.1, W, Z0 + 0.25), 'wood')
	for s in (1, -1):
		side(s, -X - 0.1, X + 0.1, Z0 - 0.1, Z0 + 0.3, 'black', out=0.06)
		for k in range(stakes):
			x = -X + 0.3 + (2 * X - 0.6) * k / max(stakes - 1, 1)
			box(p + f'stake{s}{k}', COLL, (x - 0.07, s * (W - 0.02) - 0.07, Z0 + 0.1), (x + 0.07, s * (W - 0.02) + 0.07, Z0 + stake_h), 'black')
			box(p + f'stake_pocket{s}{k}', COLL, (x - 0.12, min(s * W, s * (W + 0.1)), Z0 - 0.1), (x + 0.12, max(s * W, s * (W + 0.1)), Z0 + 0.3), 'black')
	for k in range(14):  # plank seams across the deck
		x = -X + 0.2 + (2 * X - 0.4) * k / 13
		box(p + f'plank{k}', COLL, (x - 0.02, -W, Z0 + 0.25), (x + 0.02, W, Z0 + 0.27), 'wood_dark')
	for e in (1, -1):
		box(p + f'bulkhead{e}', COLL, (min(e * X, e * (X + 0.1)), -W + 0.1, Z0 + 0.25), (max(e * X, e * (X + 0.1)), W - 0.1, Z0 + 0.9), 'wood_dark')


def log(name, x0, x1, y, z, r, seg=8):
	prof = [(y + r * math.cos(2 * math.pi * k / seg), z + r * math.sin(2 * math.pi * k / seg)) for k in range(seg + 1)]
	loft(name, COLL, [(x0, prof), (x1, prof)], 'bark', cap_front='wood', cap_back='wood')


def wood(p, state):
	flat(p, 4, 2.0)
	if state != 'loaded':
		return
	r, base = 0.36, Z0 + 0.27
	rows = [(-1.08, -0.36, 0.36, 1.08), (-0.72, 0.0, 0.72), (-0.36, 0.36)]
	for j, ys in enumerate(rows):
		z = base + r + j * r * 1.72
		for y in ys:
			# Log ends staggered so they do not line up.
			off = 0.12 * ((hash((j, y)) % 3) - 1)
			log(p + f'log{j}{y}', -X + 0.2 + off, X - 0.2 + off, y, z, r)
	# Company-colour binders wrapped over the stack: a thin closed band (outer path, then inner) in the YZ plane.
	zc = [base + r + j * r * 1.72 for j in range(3)]
	path = [(1.48, base + 0.05), (1.48, zc[0] + 0.15), (1.14, zc[1] + 0.3), (0.74, zc[2] + 0.38), (0.0, zc[2] + r + 0.04)]
	outer = mirror_y(path)
	inner = [(y * 0.96, z - 0.05) for y, z in reversed(outer)]
	band = outer + inner + [outer[0]]
	for x in (-2.2, 0.0, 2.2):
		loft(p + f'binder{x}', COLL, [(x - 0.06, band), (x + 0.06, band)], 'cc1')


def steel(p, state):
	flat(p, 0)
	if state != 'loaded':
		return
	r, base = 0.82, Z0 + 0.27
	for x in (-2.25, 0.0, 2.25):
		cz = base + r + 0.12
		disc_y(p + f'coil{x}', COLL, x, cz, r, -1.0, 1.0, 16, 'steel_light', cap_both=True)
		for s in (1, -1):  # the coil eye, darker wraps on the faces
			disc_y(p + f'eye{x}{s}', COLL, x, cz, 0.3, s * 1.0, s * 1.02, 10, 'black')
			disc_y(p + f'wrap{x}{s}', COLL, x, cz, 0.62, s * 0.99, s * 1.01, 14, 'steel')
		for k in (-1, 1):  # wooden chocks
			box(p + f'chock{x}{k}', COLL, (x + k * 0.55 - 0.22, -1.05, base), (x + k * 0.55 + 0.22, 1.05, base + 0.25), 'wood_dark')
		box(p + f'band{x}', COLL, (x - 0.06, -1.03, cz + r - 0.03), (x + 0.06, 1.03, cz + r + 0.03), 'cc1')


def build(state):
	global COLL
	COLL = bpy.data.collections[state]
	clear(COLL)
	p = state + '_'
	globals()[CARGO](p, state)
	if MONO:
		mono_base(p, COLL, Z0)
	else:
		rail_underframe(p, COLL, Z0, bogie_mat='cc1' if CARGO in ('grain', 'wood', 'steel') else 'black')
	return triangles(COLL)


result = {c.name: build(c.name) for c in bpy.data.collections if c.name in ('default', 'empty', 'loaded')}
