"""Phase 8.5 aircraft: the sixteen temperate aircraft images (planes and helicopters).

Exec'd after vehicle_kit.py with KEY set to the member's inventory key. Aircraft are authored at world size (1 unit = 1 world
pixel, a tile is 16) with +X the nose and Z = 0 at the ground under the wheels. Span comes from the nose-on sprite, length
from the side-on sprite. Helicopter rotors are part of the model, since the game's separate rotor sprite is not drawn in 3D.
"""
import math

sync_palette()
N = int(KEY.split('_')[1])
COLL = bpy.data.collections['default']
clear(COLL)
P = 'default_'
GROUND = 0.3


# --- paint schemes: (h, tn, x) -> material; h is the height on the fuselage section (-1 belly, +1 crown), tn how far into the nose

def blue(h, tn, x):
	return 'cc1'


def white_cheat(h, tn, x):
	if -0.2 < h < 0.08:
		return 'cc1'
	return 'plaster_white' if h >= 0.08 else 'steel_light'


def white_line(h, tn, x):
	return 'cc1' if -0.1 < h < 0.02 else 'plaster_white'


def blue_belly(h, tn, x):
	return 'cc1' if h > -0.5 else 'plaster_white'


def blue_top(h, tn, x):
	if h > 0.35:
		return 'cc1'
	return 'cc1' if -0.12 < h < 0.02 else 'plaster_white'


def dark_nose(h, tn, x):
	return 'black' if tn > 0.82 else 'cc1'


# --- parts -----------------------------------------------------------------------------------------------------------------

def fuselage(name, L, r, zc, nose, tail, paint, wide=1.0, seg=16, droop=0.15, tail_f=0.18, x_off=0.0, y_off=0.0, glass=True,
		nose_power=2.2, tail_lift=0.85):
	"""Fuselage lofted along X: a round nose (with the windscreen when glass) and a tail cone that sweeps up."""
	x0, x1 = x_off - L / 2, x_off + L / 2
	xs = [x0 + tail * k for k in (0.0, 0.12, 0.3, 0.5, 0.7, 0.88, 1.0)]
	xs += [xs[-1] + (x1 - nose - xs[-1]) * k for k in (0.5, 1.0)]
	xs += [x1 - nose * (1 - t) for t in (0.25, 0.45, 0.62, 0.76, 0.87, 0.94, 0.985, 1.0)]

	def section(x):
		tn = max(0.0, (x - (x1 - nose)) / nose)
		tt = max(0.0, ((x0 + tail) - x) / tail)
		f, cz = 1.0, zc
		if tn > 0:
			f = math.sqrt(max(0.0, 1 - tn ** nose_power))
			cz = zc - droop * r * tn
		if tt > 0:
			f = 1 - (1 - tail_f) * tt ** 1.4
			cz = zc + r * (1 - f) * tail_lift
		return max(f, 0.03), cz, tn

	verts, faces, mats = [], [], []
	angles = [-math.pi / 2 + 2 * math.pi * k / seg for k in range(seg)]
	for x in xs:
		f, cz, tn = section(x)
		verts += [(x, y_off + wide * r * f * math.cos(a), cz + r * f * math.sin(a)) for a in angles]
	for s in range(len(xs) - 1):
		xm = (xs[s] + xs[s + 1]) / 2
		tn = max(0.0, (xm - (x1 - nose)) / nose)
		for k in range(seg):
			a, b = s * seg + k, s * seg + (k + 1) % seg
			faces.append((a, b, b + seg, a + seg))
			am = angles[k] + math.pi / seg
			h = math.sin(am)
			if glass and 0.3 < tn < 0.6 and 0.12 < h < 0.8:
				mats.append('glass_dark')
			else:
				mats.append(paint(h, tn, xm))
	last = (len(xs) - 1) * seg
	faces += [tuple(range(seg)), tuple(range(last, last + seg))]
	mats += [paint(0.0, 0.0, x0), paint(0.0, 1.0, x1)]
	return mesh(name, COLL, verts, faces, mats)


SECTION = [(0.0, 0.0), (0.1, 0.45), (0.4, 0.5), (1.0, 0.0), (0.4, -0.4), (0.1, -0.35)]


def surface(name, root, chord_r, tip, chord_t, t_r, t_t, mat, mirror=True, vertical=False):
	"""Wing, tailplane or fin between a root and a tip section (leading-edge points). Horizontal surfaces are mirrored in Y."""
	sides = (1, -1) if mirror and not vertical else (1,)
	parts = []
	for s in sides:
		verts = []
		for (x, y, z), c, t in ((root, chord_r, t_r), (tip, chord_t, t_t)):
			for u, v in SECTION:
				if vertical:
					verts.append((x - u * c, s * y + v * t, z))
				else:
					verts.append((x - u * c, s * y, z + v * t))
		n = len(SECTION)
		faces = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)] + [tuple(range(n)), tuple(range(n, 2 * n))]
		parts.append(mesh(f'{name}{s}', COLL, verts, faces, [mat] * len(faces)))
	return parts


def cone_x(name, cy, cz, r0, r1, x0, x1, seg, mat, cap0=None, cap1=None):
	"""Frustum along X from radius r0 at x0 to r1 at x1, capped at both ends (a zero radius is a point)."""
	a = [(x0, cy + r0 * math.cos(2 * math.pi * k / seg), cz + r0 * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
	b = [(x1, cy + r1 * math.cos(2 * math.pi * k / seg), cz + r1 * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
	v = a + b + [(x0, cy, cz), (x1, cy, cz)]
	f = [(k, (k + 1) % seg, seg + (k + 1) % seg, seg + k) for k in range(seg)]
	m = [mat] * seg
	if r0 > 0:
		f += [((k + 1) % seg, k, 2 * seg) for k in range(seg)]
		m += [cap0 or mat] * seg
	if r1 > 0:
		f += [(seg + k, seg + (k + 1) % seg, 2 * seg + 1) for k in range(seg)]
		m += [cap1 or mat] * seg
	return mesh(name, COLL, v, f, m)


def jet(name, x_front, length, y, z, r, mat, pylon_z=None):
	"""Turbofan nacelle: dark intake, body tapering aft, exhaust cone; an optional pylon up to pylon_z."""
	cone_x(name, y, z, r * 0.82, r, x_front - length, x_front, 12, mat, cap0=mat, cap1='black')
	cyl_x(name + '_lip', COLL, y, z, r * 1.03, x_front - 0.12, x_front, 12, 'steel_light', cap_mat='black')
	cone_x(name + '_exhaust', y, z, r * 0.45, r * 0.62, x_front - length - 0.4 * r, x_front - length, 8, 'steel')
	if pylon_z is not None:
		lo, hi = sorted((z, pylon_z))
		box(name + '_pylon', COLL, (x_front - length * 0.85, y - 0.08, lo), (x_front - length * 0.1, y + 0.08, hi), 'steel_light')


def prop_engine(name, x_front, length, y, z, r, blade_r, mat='steel_light', blades=3):
	"""Piston or turboprop nacelle with a spinner and a stopped propeller."""
	cone_x(name, y, z, r * 0.45, r, x_front - length, x_front, 10, mat, cap1=mat)
	cone_x(name + '_spinner', y, z, r * 0.55, 0.0, x_front, x_front + r * 0.9, 8, 'cc1')
	for b in range(blades):
		a = math.pi / 2 + b * 2 * math.pi / blades
		ca, sa = math.cos(a), math.sin(a)
		w = blade_r * 0.09
		q = [(y + ca * 0.1 - sa * w, z + sa * 0.1 + ca * w), (y + ca * blade_r - sa * w * 0.6, z + sa * blade_r + ca * w * 0.6),
			(y + ca * blade_r + sa * w * 0.6, z + sa * blade_r - ca * w * 0.6), (y + ca * 0.1 + sa * w, z + sa * 0.1 - ca * w)]
		xb = x_front + r * 0.3
		v = [(xb, py, pz) for py, pz in q] + [(xb - 0.05, py, pz) for py, pz in q]
		mesh(f'{name}_blade{b}', COLL, v, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (2, 6, 7, 3)], ['black'] * 4)


def gear(name, x, y, top, wheel_r=0.3, twin=True):
	"""Landing gear leg from the underside at z = top down to a wheel (pair) resting on GROUND."""
	cz = GROUND + wheel_r
	box(name + '_leg', COLL, (x - 0.07, y - 0.07, cz), (x + 0.07, y + 0.07, top), 'steel_light')
	for dy in ((-0.17, 0.17) if twin else (0.0,)):
		disc_y(f'{name}_wheel{dy}', COLL, x, cz, wheel_r, y + dy - 0.08, y + dy + 0.08, 10, 'steel', side_mat='rubber', cap_both=True)


def windows(name, x0, x1, n, zc, r, wide=1.0, h=0.28, size=(0.2, 0.26), y_off=0.0, sides=(1, -1)):
	y = wide * r * math.cos(math.asin(h)) * 0.985 + 0.02
	z = zc + r * h
	xs = [x0 + (x1 - x0) * (k + 0.5) / n for k in range(n)]
	for s in sides:
		v, f = [], []
		for x in xs:
			k = len(v)
			yy = y_off + s * y
			v += [(x - size[0] / 2, yy, z - size[1] / 2), (x + size[0] / 2, yy, z - size[1] / 2), (x + size[0] / 2, yy, z + size[1] / 2),
				(x - size[0] / 2, yy, z + size[1] / 2)]
			f.append((k, k + 1, k + 2, k + 3) if s > 0 else (k + 3, k + 2, k + 1, k))
		mesh(f'{name}{s}', COLL, v, f, ['glass_dark'] * len(f), recalc=False)


def le_at(root, tip, y):
	"""Leading-edge point of a straight-tapered surface at span station y."""
	t = (y - root[1]) / (tip[1] - root[1])
	return tuple(root[i] + (tip[i] - root[i]) * t for i in range(3))


def underwing_jets(name, root, tip, ys, length, r, mat, ahead=0.9, drop=None):
	for y in ys:
		lx, _, lz = le_at(root, tip, y)
		z = lz - (drop if drop is not None else r + 0.35)
		for s in (1, -1):
			jet(f'{name}{y}{s}', lx + ahead, length, s * y, z, r, mat, pylon_z=lz)


def wing_props(name, root, tip, ys, length, r, blade_r, ahead=0.7):
	for y in ys:
		lx, _, lz = le_at(root, tip, y)
		for s in (1, -1):
			prop_engine(f'{name}{y}{s}', lx + ahead, length, s * y, lz + 0.05, r, blade_r)


def tail_nozzles(name, x, ys, z, r):
	for y in ys:
		cone_x(f'{name}{y}', y, z, r * 0.7, r, x - 0.5, x + 0.2, 10, 'black', cap0='black')


def conventional(L, r, zc, nose, tail, paint, wing, htail, fin, fin_mat='cc1', wing_mat='steel_light', glass=True, tail_f=0.18, win=None,
		gear_x=None, main=None, t_wing=(0.4, 0.15)):
	"""The common airliner layout: fuselage, mirrored wing and tailplane, a fin, windows and tricycle gear."""
	fuselage(P + 'fuselage', L, r, zc, nose, tail, paint, glass=glass, tail_f=tail_f)
	surface(P + 'wing', wing[0], wing[1], wing[2], wing[3], t_wing[0], t_wing[1], wing_mat)
	if htail:
		surface(P + 'tailplane', htail[0], htail[1], htail[2], htail[3], 0.18, 0.08, htail[4] if len(htail) > 4 else wing_mat)
	surface(P + 'fin', fin[0], fin[1], fin[2], fin[3], 0.22, 0.1, fin_mat, vertical=True)
	if win:
		windows(P + 'windows', win[0], win[1], win[2], zc, r)
	if gear_x is not None:
		gear(P + 'nose_gear', gear_x, 0.0, zc - r * 0.8, wheel_r=0.22 + r * 0.06)
	for x, y, top in main or ():
		for s in (1, -1) if y else (0,):
			gear(f'{P}main{x}{s}', x, s * y, top, wheel_r=0.25 + r * 0.08)


# --- members ---------------------------------------------------------------------------------------------------------------

def sampson():  # 0 Sampson U52: small twin piston airliner
	L, r, zc = 10.2, 0.55, 1.65
	wing = ((1.3, 0.55, zc - 0.35), 1.9, (1.0, 5.6, zc + 0.1), 1.0)
	conventional(L, r, zc, 2.0, 4.0, blue, wing, ((-3.6, 0.3, zc + 0.2), 1.1, (-4.0, 2.1, zc + 0.25), 0.6),
		((-3.5, 0, zc + 0.35), 1.4, (-4.3, 0, zc + 1.9), 0.7), win=(-1.2, 1.6, 5), gear_x=3.5, t_wing=(0.3, 0.12))
	wing_props(P + 'engine', wing[0], wing[2], (1.9,), 1.9, 0.32, 0.85)
	for s in (1, -1):
		gear(f'{P}main{s}', 0.9, s * 1.9, zc - 0.55, wheel_r=0.26, twin=False)


def coleman():  # 1 Coleman Count: four-engined turboprop airliner
	L, r, zc = 14.8, 0.8, 2.0
	wing = ((1.7, 0.8, zc - 0.5), 2.6, (0.9, 8.5, zc + 0.05), 1.1)
	conventional(L, r, zc, 2.6, 5.5, white_cheat, wing, ((-5.5, 0.4, zc + 0.25), 1.6, (-6.1, 2.8, zc + 0.3), 0.8),
		((-5.2, 0, zc + 0.5), 2.2, (-6.6, 0, zc + 2.6), 1.0), win=(-3.6, 3.6, 12), gear_x=5.2)
	wing_props(P + 'engine', wing[0], wing[2], (2.5, 4.7), 2.4, 0.34, 0.9)
	for s in (1, -1):
		gear(f'{P}main{s}', 0.6, s * 2.5, zc - 0.6)


def dart():  # 2 FFP Dart: twin rear-engined T-tail jet
	L, r, zc = 19.4, 0.85, 1.75
	wing = ((2.2, 0.8, zc - 0.55), 3.4, (-1.0, 6.7, zc + 0.0), 1.2)
	ht = ((-8.3, 0.2, zc + 3.0), 1.8, (-9.2, 2.6, zc + 3.1), 0.9)
	conventional(L, r, zc, 2.8, 4.5, blue, wing, ht, ((-6.4, 0, zc + 0.5), 2.6, (-8.4, 0, zc + 3.05), 1.8), win=(-3.8, 5.6, 16),
		gear_x=7.6, main=((0.0, 1.5, zc - 0.7),))
	for s in (1, -1):
		jet(f'{P}engine{s}', -3.9, 2.6, s * 1.55, zc + 0.35, 0.48, 'steel_light')
		box(f'{P}engine_pylon{s}', COLL, (-6.0, min(s * 0.6, s * 1.2), zc + 0.25), (-4.6, max(s * 0.6, s * 1.2), zc + 0.45), 'steel_light')


def haugan():  # 3 Yate Haugan: supersonic delta
	L, r, zc = 26.0, 0.72, 2.4
	fuselage(P + 'fuselage', L, r, zc, 6.0, 3.5, white_line, tail_f=0.15, droop=0.3)
	surface(P + 'wing', (5.0, 0.5, zc - 0.45), 13.0, (-6.8, 6.35, zc - 0.35), 2.0, 0.4, 0.1, 'plaster_white')
	surface(P + 'fin', (-5.4, 0, zc + 0.5), 5.5, (-10.4, 0, zc + 3.4), 1.8, 0.24, 0.1, 'cc1', vertical=True)
	windows(P + 'windows', -6.0, 5.0, 20, zc, r, size=(0.16, 0.2))
	for s in (1, -1):
		y0, y1 = sorted((s * 1.3, s * 3.1))
		box(f'{P}nacelle{s}', COLL, (-8.0, y0, zc - 1.3), (-3.0, y1, zc - 0.4), 'plaster_white')
		box(f'{P}intake{s}', COLL, (-3.0, y0 + 0.1, zc - 1.2), (-2.96, y1 - 0.1, zc - 0.55), 'black')
		for dy in (0.45, 1.35):
			cone_x(f'{P}nozzle{s}{dy}', s * (1.3 + dy), zc - 0.85, 0.36, 0.3, -8.5, -8.0, 8, 'steel', cap0='black')
		gear(f'{P}main{s}', -4.0, s * 1.8, zc - 1.3, wheel_r=0.32)
	gear(P + 'nose_gear', 7.8, 0.0, zc - 0.6, wheel_r=0.26)


def cotswald():  # 4 Bakewell Cotswald LB-3: twin piston airliner
	L, r, zc = 11.7, 0.75, 1.9
	wing = ((1.8, 0.7, zc - 0.45), 2.6, (1.0, 8.3, zc + 0.2), 1.0)
	conventional(L, r, zc, 2.0, 4.5, blue, wing, ((-4.4, 0.3, zc + 0.1), 1.4, (-5.0, 3.0, zc + 0.15), 0.7),
		((-4.0, 0, zc + 0.3), 1.8, (-5.3, 0, zc + 2.2), 0.9), win=(-2.6, 1.6, 7), gear_x=3.9)
	wing_props(P + 'engine', wing[0], wing[2], (2.4,), 2.6, 0.42, 1.0)
	for s in (1, -1):
		gear(f'{P}main{s}', 1.2, s * 2.4, zc - 0.75, wheel_r=0.32, twin=False)


def luckett8():  # 5 Bakewell Luckett LB-8: high-wing four-jet with a T-tail
	L, r, zc = 14.8, 0.95, 1.75
	wing = ((1.6, 0.7, zc + 0.75), 2.8, (0.4, 7.05, zc + 0.45), 1.1)
	ht = ((-6.2, 0.2, zc + 2.9), 1.8, (-6.9, 3.1, zc + 2.95), 0.9, 'plaster_white')
	conventional(L, r, zc, 2.5, 4.2, blue, wing, ht, ((-4.7, 0, zc + 0.5), 2.6, (-6.5, 0, zc + 2.95), 1.8), fin_mat='plaster_white',
		win=(-3.2, 3.6, 12), gear_x=5.6)
	underwing_jets(P + 'engine', wing[0], wing[2], (1.9, 3.5), 2.0, 0.36, 'steel_light', ahead=0.4, drop=0.6)
	for s in (1, -1):
		box(f'{P}gear_pod{s}', COLL, (-0.6, min(s * 0.6, s * 1.15), zc - 0.95), (1.6, max(s * 0.6, s * 1.15), zc - 0.35), 'cc1')
		gear(f'{P}main{s}', 0.5, s * 1.0, zc - 0.95)


def luckett10():  # 8 Bakewell Luckett LB-10: trijet widebody
	L, r, zc = 21.5, 1.05, 2.1
	wing = ((2.6, 0.9, zc - 0.65), 4.2, (-2.4, 9.5, zc + 0.05), 1.3)
	conventional(L, r, zc, 3.0, 5.0, blue, wing, ((-7.9, 0.4, zc + 0.25), 2.3, (-9.7, 3.8, zc + 0.6), 0.9),
		((-7.8, 0, zc + 1.8), 2.4, (-9.8, 0, zc + 4.4), 1.4), win=(-6.0, 6.5, 22), gear_x=8.4,
		main=((-0.4, 1.6, zc - 0.8), (-0.6, 0, zc - 1.0)))
	underwing_jets(P + 'engine', wing[0], wing[2], (3.3,), 2.6, 0.55, 'plaster_white')
	jet(P + 'centre_engine', -5.9, 3.4, 0.0, zc + 1.3, 0.6, 'cc1', pylon_z=zc + 0.6)


def darwin200():  # 12 Darwin 200: twin-engined widebody
	L, r, zc = 23.0, 1.1, 2.45
	wing = ((2.4, 0.9, zc - 0.7), 4.4, (-3.4, 11.6, zc + 0.1), 1.3)
	conventional(L, r, zc, 3.0, 5.5, white_cheat, wing, ((-8.7, 0.4, zc + 0.2), 2.4, (-10.5, 4.2, zc + 0.6), 0.9),
		((-8.0, 0, zc + 0.6), 3.2, (-10.4, 0, zc + 4.3), 1.4), win=(-7.0, 7.4, 24), gear_x=8.9, main=((-0.6, 1.8, zc - 0.85),))
	underwing_jets(P + 'engine', wing[0], wing[2], (3.8,), 3.0, 0.65, 'cc1')


def darwin300():  # 13 Darwin 300: four-engined jumbo with the upper deck hump
	L, r, zc = 24.0, 1.25, 2.65
	wing = ((2.6, 1.0, zc - 0.8), 4.8, (-3.8, 11.6, zc + 0.1), 1.4)
	conventional(L, r, zc, 3.2, 5.5, blue_belly, wing, ((-9.0, 0.5, zc + 0.2), 2.8, (-11.0, 4.6, zc + 0.5), 1.0),
		((-8.0, 0, zc + 0.7), 3.6, (-10.8, 0, zc + 4.7), 1.6), win=(-7.6, 8.0, 26), gear_x=9.5,
		main=((-0.8, 1.6, zc - 1.0), (0.4, 2.6, zc - 0.9)))
	fuselage(P + 'upper_deck', 7.4, 0.85, zc + 0.55, 2.6, 3.4, blue_belly, x_off=6.4, tail_f=0.05, tail_lift=-0.4, glass=True, droop=0.0)
	windows(P + 'upper_windows', 4.4, 8.0, 6, zc + 0.55, 0.85, h=0.3)
	underwing_jets(P + 'engine', wing[0], wing[2], (3.6, 6.6), 2.8, 0.6, 'cc1')


def kelling6():  # 27 Kelling K6: twin jet with big nacelles, winglets and a white T-tail
	L, r, zc = 20.0, 0.95, 2.5
	wing = ((2.2, 0.8, zc - 0.6), 3.8, (-1.8, 8.3, zc + 0.1), 1.4)
	ht = ((-8.3, 0.2, zc + 3.1), 2.0, (-9.3, 3.0, zc + 3.2), 1.0, 'plaster_white')
	conventional(L, r, zc, 2.8, 4.8, blue, wing, ht, ((-6.6, 0, zc + 0.5), 2.8, (-8.4, 0, zc + 3.15), 2.0), fin_mat='plaster_white',
		win=(-5.0, 6.0, 18), gear_x=7.6, main=((-0.4, 1.7, zc - 0.75),))
	underwing_jets(P + 'engine', wing[0], wing[2], (2.8,), 3.4, 0.7, 'plaster_white')
	for s in (1, -1):
		surface(f'{P}winglet{s}', (-1.7, s * 8.25, zc + 0.1), 1.4, (-2.5, s * 8.4, zc + 1.4), 0.7, 0.12, 0.06, 'plaster_white', vertical=True)


def kelling7():  # 28 Kelling K7: lifting-body spaceplane
	L, r, zc = 18.0, 1.0, 2.0
	fuselage(P + 'fuselage', L, r, zc, 5.0, 3.0, blue_top, wide=1.6, tail_f=0.55, droop=0.35, nose_power=1.6, tail_lift=0.3)
	surface(P + 'wing', (-1.0, 1.2, zc - 0.4), 6.5, (-6.2, 4.75, zc + 0.15), 1.5, 0.35, 0.1, 'cc1')
	surface(P + 'canard', (5.0, 1.2, zc - 0.1), 1.6, (4.0, 2.6, zc + 0.1), 0.6, 0.12, 0.06, 'cc1')
	surface(P + 'fin', (-4.8, 0, zc + 0.8), 3.6, (-8.0, 0, zc + 3.0), 1.2, 0.22, 0.08, 'cc1', vertical=True)
	tail_nozzles(P + 'nozzle', -9.0, (-0.8, 0.8), zc + 0.1, 0.45)
	windows(P + 'windows', -3.0, 3.0, 9, zc, r, wide=1.6, size=(0.18, 0.22))
	gear(P + 'nose_gear', 5.6, 0.0, zc - 0.8, wheel_r=0.26)
	for s in (1, -1):
		gear(f'{P}main{s}', -2.6, s * 1.4, zc - 0.7)


def hyperdart():  # 30 FFP Hyperdart 2: bulbous-nosed jet with twin canted fins
	L, r, zc = 13.0, 1.0, 2.0

	def paint(h, tn, x):
		if x > -0.5:
			return 'cc1'
		return 'cc1' if h > 0.65 or -0.15 < h < 0.0 else 'plaster_white'
	fuselage(P + 'fuselage', L, r, zc, 4.0, 4.5, paint, tail_f=0.4, nose_power=3.0, droop=0.2, tail_lift=0.4)
	surface(P + 'wing', (0.6, 0.7, zc - 0.5), 3.6, (-3.6, 6.35, zc - 0.2), 1.0, 0.35, 0.1, 'steel_light')
	for s in (1, -1):
		surface(f'{P}wing_tip{s}', (-3.4, s * 6.0, zc - 0.22), 1.3, (-3.6, s * 6.35, zc - 0.2), 1.0, 0.16, 0.1, 'cc1', mirror=False)
		surface(f'{P}fin{s}', (-2.9, s * 0.65, zc + 0.6), 2.2, (-4.7, s * 1.3, zc + 2.4), 1.0, 0.18, 0.08, 'cc1', vertical=True)
	tail_nozzles(P + 'nozzle', -6.6, (0.0,), zc + 0.3, 0.42)
	windows(P + 'windows', -3.6, 1.8, 8, zc, r, size=(0.2, 0.24))
	gear(P + 'nose_gear', 4.2, 0.0, zc - 0.8, wheel_r=0.24)
	for s in (1, -1):
		gear(f'{P}main{s}', -1.6, s * 1.3, zc - 0.75)


def dinger200():  # 31 Dinger 200: three-lobed heavy lifter with a box tail
	r, zc = 1.4, 2.25
	fuselage(P + 'fuselage', 17.0, r, zc, 3.4, 4.0, blue, nose_power=2.6, tail_f=0.3)
	for s in (1, -1):
		fuselage(f'{P}lobe{s}', 13.0, 1.15, zc - 0.25, 3.0, 3.6, blue, x_off=-1.2, y_off=s * 2.15, glass=False, nose_power=2.6, tail_f=0.35)
		windows(f'{P}lobe_windows{s}', -5.0, 2.4, 12, zc - 0.25, 1.15, y_off=s * 2.15, sides=(s,))
		surface(f'{P}fin{s}', (-5.6, s * 2.15, zc + 0.5), 2.4, (-7.0, s * 2.15, zc + 3.1), 1.7, 0.2, 0.1, 'cc1', vertical=True)
		tail_nozzles(f'{P}nozzle{s}', -7.8, (s * 2.15,), zc - 0.15, 0.4)
		gear(f'{P}main{s}', -1.5, s * 2.15, zc - 1.3, wheel_r=0.32)
	surface(P + 'bar', (-6.9, 0.0, zc + 3.1), 1.7, (-7.0, 2.3, zc + 3.1), 1.7, 0.2, 0.2, 'cc1')
	surface(P + 'wing', (0.6, 3.0, zc - 0.5), 4.0, (-2.0, 7.75, zc - 0.2), 1.5, 0.35, 0.12, 'steel_light')
	gear(P + 'nose_gear', 6.0, 0.0, zc - r * 0.85, wheel_r=0.3)


def dinger1000():  # 32 Dinger 1000: three slender hulls on a white bat-wing delta
	zc = 1.95
	fuselage(P + 'fuselage', 21.9, 0.6, zc, 6.0, 3.0, dark_nose, tail_f=0.5, droop=0.1)
	for s in (1, -1):
		fuselage(f'{P}hull{s}', 16.0, 0.55, zc - 0.1, 4.5, 2.6, dark_nose, x_off=-2.6, y_off=s * 2.7, glass=False, tail_f=0.5)
		surface(f'{P}fin{s}', (-7.2, s * 2.7, zc + 0.4), 3.0, (-9.8, s * 2.7, zc + 2.4), 1.2, 0.18, 0.08, 'cc1', vertical=True)
		tail_nozzles(f'{P}nozzle{s}', -10.6, (s * 2.7,), zc - 0.1, 0.32)
		gear(f'{P}main{s}', -3.5, s * 2.7, zc - 0.65, wheel_r=0.28)
	surface(P + 'wing', (3.0, 0.4, zc - 0.25), 12.0, (-6.5, 8.85, zc - 0.05), 2.5, 0.35, 0.08, 'plaster_white')
	surface(P + 'fin', (-7.6, 0, zc + 0.45), 3.4, (-10.6, 0, zc + 2.8), 1.2, 0.18, 0.08, 'cc1', vertical=True)
	tail_nozzles(P + 'nozzle', -11.0, (0.0,), zc, 0.36)
	windows(P + 'windows', -4.0, 4.0, 12, zc, 0.6, size=(0.14, 0.18))
	gear(P + 'nose_gear', 7.5, 0.0, zc - 0.5, wheel_r=0.24)


def rotor(name, x, z, blades, radius, chord=0.24):
	cyl_z(name + '_mast', COLL, x, 0.0, 0.12, 0.12, z - 0.4, z + 0.15, 8, 'steel')
	cyl_z(name + '_hub', COLL, x, 0.0, 0.3, 0.3, z + 0.1, z + 0.32, 10, 'black')
	for b in range(blades):
		a = math.pi / 4 + b * 2 * math.pi / blades
		ca, sa = math.cos(a), math.sin(a)
		w = chord / 2
		q = [(0.25, -w), (radius, -w * 0.8), (radius, w * 0.8), (0.25, w)]
		v = [(x + ca * u - sa * t, ca * t + sa * u, z + 0.2 - u * 0.02) for u, t in q]
		v += [(px, py, pz + 0.06) for px, py, pz in v]
		mesh(f'{name}_blade{b}', COLL, v, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)],
			['steel'] * 6)


def helicopter(L, r, x_off, zc, boom_end, blades, radius, skids, white_above=0.15):
	def paint(h, tn, x):
		return 'plaster_white' if h > white_above else 'cc1'
	fuselage(P + 'cabin', L, r, zc, L * 0.38, L * 0.4, paint, wide=0.9, x_off=x_off, tail_f=0.35, droop=0.25, nose_power=1.8, tail_lift=0.5)
	x_back = x_off - L / 2 + 0.6
	cone_x(P + 'boom', 0.0, zc + 0.35, 0.16, 0.34, boom_end, x_back + 0.5, 8, 'cc1')
	surface(P + 'tail_fin', (boom_end + 1.2, 0, zc + 0.4), 1.2, (boom_end + 0.3, 0, zc + 1.9), 0.7, 0.12, 0.06, 'cc1', vertical=True)
	surface(P + 'stabiliser', (boom_end + 1.8, 0.1, zc + 0.35), 0.7, (boom_end + 1.6, 0.9, zc + 0.4), 0.45, 0.08, 0.05, 'plaster_white')
	tz = zc + 1.2
	for b in range(2):
		a = math.pi / 2 * b + math.pi / 4
		box(f'{P}tail_rotor{b}', COLL, (boom_end + 0.3 - 0.06, 0.24, tz - 0.08), (boom_end + 0.3 + 0.06, 0.3, tz + 0.08), 'black')
		ca, sa = math.cos(a), math.sin(a)
		v = [(boom_end + 0.3 + ca * 0.8 - sa * 0.08, 0.3, tz + sa * 0.8 + ca * 0.08), (boom_end + 0.3 + ca * 0.8 + sa * 0.08, 0.3, tz + sa * 0.8 - ca * 0.08),
			(boom_end + 0.3 - ca * 0.8 + sa * 0.08, 0.3, tz - sa * 0.8 - ca * 0.08), (boom_end + 0.3 - ca * 0.8 - sa * 0.08, 0.3, tz - sa * 0.8 + ca * 0.08)]
		v += [(px, 0.34, pz) for px, _, pz in v]
		mesh(f'{P}tail_blade{b}', COLL, v, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (2, 6, 7, 3)], ['black'] * 4)
	box(P + 'engine_cowl', COLL, (x_off - L * 0.25, -0.55, zc + r * 0.8), (x_off + L * 0.12, 0.55, zc + r * 0.8 + 0.5), 'plaster_white' if white_above < 0.5 else 'cc1')
	for s in (1, -1):
		box(f'{P}intake{s}', COLL, (x_off + L * 0.08, min(s * 0.55, s * 0.6), zc + r * 0.8 + 0.1), (x_off + L * 0.12, max(s * 0.55, s * 0.6), zc + r * 0.8 + 0.4), 'black')
	windows(P + 'windows', x_off - L * 0.15, x_off + L * 0.1, 3, zc, r, wide=0.9, h=0.25, size=(0.4, 0.4))
	rotor(P + 'rotor', x_off, zc + r * 0.8 + 0.6, blades, radius)
	if skids:
		for s in (1, -1):
			y = s * r * 0.95
			box(f'{P}skid{s}', COLL, (x_off - L * 0.35, y - 0.06, GROUND), (x_off + L * 0.35, y + 0.06, GROUND + 0.12), 'steel')
			box(f'{P}skid_tip{s}', COLL, (x_off + L * 0.35, y - 0.06, GROUND + 0.05), (x_off + L * 0.35 + 0.3, y + 0.06, GROUND + 0.35), 'steel')
			for x in (x_off - L * 0.2, x_off + L * 0.2):
				rod(f'{P}skid_leg{s}{x:.1f}', COLL, (x, GROUND + 0.1), (x, zc - r * 0.6), s * r * 0.6, 0.08, 0.06, 'steel')
	else:
		for s in (1, -1):
			box(f'{P}sponson{s}', COLL, (x_off - L * 0.25, min(s * r * 0.8, s * (r * 0.8 + 0.5)), zc - r * 0.7), (x_off + L * 0.05, max(s * r * 0.8, s * (r * 0.8 + 0.5)), zc - r * 0.2), 'cc1')
			gear(f'{P}main{s}', x_off - L * 0.1, s * (r * 0.8 + 0.3), zc - r * 0.7, wheel_r=0.3, twin=False)
		gear(P + 'nose_gear', x_off + L * 0.32, 0.0, zc - r * 0.75, wheel_r=0.24, twin=False)


MEMBERS = {
	0: sampson, 1: coleman, 2: dart, 3: haugan, 4: cotswald, 5: luckett8, 8: luckett10, 12: darwin200, 13: darwin300,
	27: kelling6, 28: kelling7, 30: hyperdart, 31: dinger200, 32: dinger1000,
	38: lambda: helicopter(6.0, 0.95, 2.4, 1.55, -5.4, 4, 5.0, skids=True),  # Tricario
	39: lambda: helicopter(7.6, 1.15, 2.0, 1.85, -6.0, 5, 5.8, skids=False, white_above=0.65),  # Guru X2
}
MEMBERS[N]()
result = {'default': triangles(COLL)}
