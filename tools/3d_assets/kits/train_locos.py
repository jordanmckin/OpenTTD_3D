"""Temperate locomotives other than the A4: two steam engines and the diesel, electric, monorail and maglev units.
The modern units share one builder: a lofted body whose ends are shaped by a nose (flat cab, short hood, wedge,
bullet), paint zones that follow the nose, roof equipment and a rail, monorail or maglev underframe. The steam
engines are built from the A4's parts. The model is the front unit with its cab towards +X; the renderer turns
the rear head of a multiheaded train around.
Run in Blender with the member's .blend open, after vehicle_kit.py has been executed in the same namespace,
with KEY set to the member's inventory key."""
import math
import bpy

sync_palette()
N = int(KEY.split('_')[1])
X = 3.8  # body half length
ZB = 1.45  # body floor
# Body half profile (y, z) from the floor to the crown; extra points on the flat side so paint bands can follow the nose.
PROF = [(1.68, 1.45), (1.72, 2.0), (1.72, 2.6), (1.72, 3.2), (1.72, 3.8), (1.72, 4.3), (1.7, 4.6), (1.64, 4.85),
	(1.52, 5.1), (1.36, 5.3), (1.1, 5.45), (0.6, 5.57), (0.0, 5.63)]
ZT = PROF[-1][1]
NP = len(PROF)
# Original (unshaped) mid height of each loft quad, by quad index around the mirrored profile.
# The duplicated centre-floor point closes the body underneath and the end caps across the floor edge.
_full = [(0.0, ZB)] + mirror_y(PROF) + [(0.0, ZB)]
QZ = [(_full[i][1] + _full[i + 1][1]) / 2 for i in range(len(_full) - 1)]


def clamp(v):
	return max(0.0, min(1.0, v))


class Nose:
	"""End shape. kind: 'flat' (rounded cab end), 'hood' (cab set back behind a lower nose), 'wedge', 'bullet'."""
	def __init__(self, kind, length, drop=0.0, pinch=0.0, power=1.0, hood_z=4.25):
		self.kind, self.length, self.drop, self.pinch, self.power, self.hood_z = kind, length, drop, pinch, power, hood_z


FLAT = Nose('flat', 0.35, drop=0.04, pinch=0.08, power=2.0)


def nose_t(x, front, back):
	tf = clamp((x - (X - front.length)) / front.length) if front.length else 0.0
	tb = clamp(((-X + back.length) - x) / back.length) if back.length else 0.0
	return (tf, front, 1) if tf >= tb else (tb, back, -1)


def shape(x, front, back):
	t, nose, _ = nose_t(x, front, back)
	out = []
	for y, z in PROF:
		h = (z - ZB) / (ZT - ZB)
		if nose.kind == 'hood':
			# A step down to the nose top just ahead of the cab, then a lightly rounded nose.
			if t > 0:
				z = min(z, nose.hood_z + (z - nose.hood_z) * 0.12) if z > nose.hood_z else z
				y = y * (1 - 0.08 * t ** 3 * (0.2 + 0.8 * h))
			out.append((y, z))
			continue
		k = t ** nose.power
		zz = ZB + (z - ZB) * (1 - nose.drop * k * (0.2 + 0.8 * h))
		yy = y * (1 - nose.pinch * k * (0.12 + 0.88 * h * h))
		if h < 0.12:
			yy = y * (1 - 0.25 * nose.pinch * k)
		out.append((yy, zz))
	return [(0.0, ZB)] + mirror_y(out) + [(0.0, ZB)]


def stations(front, back):
	xs = {-X, X, 0.0}
	for nose, sgn in ((front, 1), (back, -1)):
		if nose.kind == 'hood':
			xb = sgn * (X - nose.length)
			xs |= {xb, xb + sgn * 0.02, sgn * (X - 0.12)}
		elif nose.length:
			for k in range(8 if nose.kind != 'flat' else 4):
				u = k / (7 if nose.kind != 'flat' else 3)
				xs.add(sgn * (X - nose.length + nose.length * u))
	return [(x, shape(x, front, back)) for x in sorted(xs)]


class Spec:
	"""Paint and fittings for one modern unit."""
	def __init__(self, **kw):
		self.front, self.back = FLAT, FLAT
		self.body, self.roof, self.roof_z = 'cc1', 'roof_dark', 4.85
		self.bands = []  # (z0, z1, mat) on the unshaped profile, following the noses
		self.skirt = None  # (z, mat): below z
		self.end_mat, self.end_z, self.end_full = 'hazard_yellow', 3.2, False  # warning panel on the noses
		self.glass = (0.35, 0.85, 4.3, 5.3)  # nose windscreen: t range and unshaped z range (wedge/bullet)
		self.screen = True  # windscreen boxes on a flat or hood cab front
		self.roof_kit, self.pans, self.under = 'diesel', (), 'rail'
		self.side_windows = 'cab'  # 'cab' (two per cab), 'saloon', or None
		self.axles = 2
		self.rear_mat = None  # a different roof/upper colour on the back half (white roofs)
		self.__dict__.update(kw)


def paint(spec):
	def mat(x0, x1, zm, i):
		z = QZ[i]
		xm = (x0 + x1) / 2
		t, nose, _ = nose_t(xm, spec.front, spec.back)
		in_nose = t > 0 and nose.kind not in ('flat',)
		if in_nose and nose.kind in ('wedge', 'bullet'):
			g0, g1, gz0, gz1 = spec.glass
			if g0 <= t <= g1 and gz0 <= z <= gz1:
				return 'glass_dark'
		if nose.kind == 'hood' and t > 0 and nose_t(xm - 0.05 * (1 if xm > 0 else -1), spec.front, spec.back)[0] == 0 and z > nose.hood_z:
			return 'glass_dark'  # the cab front above the nose
		if t > 0 and spec.end_mat and (spec.end_full or z < spec.end_z):
			return spec.end_mat
		for z0, z1, m in spec.bands:
			if z0 <= z < z1:
				return m
		if spec.rear_mat and xm < 0.6 and z > spec.roof_z - 0.6:
			return spec.rear_mat
		if z > spec.roof_z:
			return spec.roof
		if spec.skirt and z < spec.skirt[0]:
			return spec.skirt[1]
		return spec.body
	return mat


def side(s, x0, x1, z0, z1, mat, out=0.03, y=1.72):
	return box(f'{COLL.name}_side{s}_{x0:.2f}_{z0:.2f}_{mat}', COLL, (x0, min(s * y, s * y + s * out), z0), (x1, max(s * y, s * y + s * out), z1), mat)


def pantograph(p, x, folded=False):
	z0 = ZT - 0.02
	box(p + f'pan_base{x}', COLL, (x - 0.5, -0.55, z0), (x + 0.5, 0.55, z0 + 0.12), 'black')
	for y in (-0.5, 0.5):
		cyl_z(p + f'insulator{x}{y}', COLL, x - 0.4, y, 0.07, 0.07, z0 - 0.05, z0 + 0.3, 6, 'plaster_white')
		cyl_z(p + f'insulator_b{x}{y}', COLL, x + 0.4, y, 0.07, 0.07, z0 - 0.05, z0 + 0.3, 6, 'plaster_white')
	knee = (x - 0.55, z0 + 0.75)
	head = (x + 0.05, z0 + 1.45)
	for y in (-0.45, 0.35):
		rod(p + f'pan_lower{x}{y}', COLL, (x + 0.35, z0 + 0.15), knee, y, 0.08, 0.08, 'black')
		rod(p + f'pan_upper{x}{y}', COLL, knee, head, y, 0.06, 0.08, 'black')
	box(p + f'pan_head{x}', COLL, (head[0] - 0.1, -0.85, head[1] - 0.03), (head[0] + 0.1, 0.85, head[1] + 0.05), 'steel')
	for y in (-0.85, 0.85):
		box(p + f'pan_horn{x}{y}', COLL, (head[0] - 0.06, min(y, y * 1.12), head[1] - 0.15), (head[0] + 0.06, max(y, y * 1.12), head[1] + 0.03), 'steel')


def roof_kit(p, spec):
	if spec.roof_kit == 'diesel':
		for k, x in enumerate((-1.4, -0.3, 0.8)):  # radiator fans
			cyl_z(p + f'fan{k}', COLL, x, 0.0, 0.42, 0.42, ZT - 0.08, ZT + 0.04, 14, 'steel', cap_mat='black')
			box(p + f'fan_bar{k}', COLL, (x - 0.42, -0.04, ZT + 0.04), (x + 0.42, 0.04, ZT + 0.07), 'steel')
		box(p + 'exhaust', COLL, (1.6, -0.25, ZT - 0.05), (2.0, 0.25, ZT + 0.12), 'black')
		for s in (1, -1):  # bodyside grilles
			for k in range(3):
				side(s, -1.9 + 1.1 * k, -1.2 + 1.1 * k, 3.95, 4.55, 'black', out=0.025)
	elif spec.roof_kit == 'electric':
		for x in spec.pans:
			pantograph(p, x)
		cyl_x(p + 'roof_line', COLL, 0.0, ZT + 0.12, 0.05, -abs(spec.pans[0]) if spec.pans else -1, abs(spec.pans[-1]) if spec.pans else 1, 6, 'steel_light')
		box(p + 'breaker', COLL, (-0.5, -0.3, ZT - 0.05), (0.5, 0.3, ZT + 0.2), 'steel')
		for s in (1, -1):
			for k in range(4):
				side(s, -1.6 + 0.8 * k, -1.05 + 0.8 * k, 3.9, 4.55, 'black', out=0.025)
	elif spec.roof_kit == 'sleek':
		box(p + 'roof_pod', COLL, (-1.5, -0.6, ZT - 0.08), (1.0, 0.6, ZT + 0.12), spec.roof)


def side_windows(p, spec):
	for s in (1, -1):
		if spec.side_windows == 'saloon':
			for k in range(6):
				x = -2.3 + 0.92 * k
				side(s, x - 0.32, x + 0.32, 3.75, 4.6, 'glass_dark')
			for e in (1, -1):  # cab doors
				side(s, e * 2.95 - 0.2, e * 2.95 + 0.2, 2.0, 4.6, 'black', out=0.02)
				side(s, e * 2.95 - 0.14, e * 2.95 + 0.14, 3.9, 4.5, 'glass_dark', out=0.03)
		elif spec.side_windows == 'cab':
			for e, nose in ((1, spec.front), (-1, spec.back)):
				if nose.kind in ('wedge', 'bullet') and nose.length > 1.5:
					continue  # streamlined noses carry their glass on the nose
				xc = e * (X - max(nose.length, 0.35) - 0.45)
				side(s, xc - 0.3, xc + 0.3, 3.85, 4.6, 'glass_dark')
				side(s, xc - e * 0.55 - 0.06, xc - e * 0.55 + 0.06, 2.1, 4.6, 'black', out=0.02)  # door edge


def cab_screens(p, spec):
	for e, nose in ((1, spec.front), (-1, spec.back)):
		if not spec.screen or nose.kind != 'flat':
			continue
		xe = e * X
		for y in (-0.62, 0.62):
			box(p + f'screen{e}{y}', COLL, (min(xe, xe + e * 0.03), y - 0.48, 4.05), (max(xe, xe + e * 0.03), y + 0.48, 4.8), 'glass_dark')
		box(p + f'screen_bar{e}', COLL, (min(xe, xe + e * 0.04), -0.07, 4.05), (max(xe, xe + e * 0.04), 0.07, 4.8), 'black')


def end_fittings(p, spec):
	for e, nose in ((1, spec.front), (-1, spec.back)):
		xe = e * X
		for s in (1, -1):  # headlights and tail lamps
			cyl_x(p + f'lamp{e}{s}', COLL, s * 1.0, 2.25, 0.13, xe - e * 0.05, xe + e * 0.04, 8, 'black', cap_mat='lamp_yellow' if e > 0 else 'signal_red')
		if spec.under == 'rail':
			box(p + f'beam{e}', COLL, (min(xe - e * 0.15, xe + e * 0.08), -1.55, 1.0), (max(xe - e * 0.15, xe + e * 0.08), 1.55, ZB + 0.05), 'black')
			buffers(p + f'buffers{e}', COLL, xe + e * 0.08, e, z=1.3, y=1.1, length=0.25, r=0.2)
			box(p + f'plough{e}', COLL, (min(xe - e * 0.3, xe + e * 0.1), -1.3, 0.75), (max(xe - e * 0.3, xe + e * 0.1), 1.3, 1.0), 'black')
		else:
			box(p + f'coupler{e}', COLL, (min(xe, xe + e * 0.3), -0.25, 1.0), (max(xe, xe + e * 0.3), 0.25, 1.3), 'black')


def underframe(p, spec):
	if spec.under == 'rail':
		co = spec.axles == 3  # three-axle bogies: smaller wheels, a longer wheelbase and a middle axle
		r, wb, bx = (0.42, 2.0, 2.45) if co else (0.46, 1.5, 2.35)
		for e in (1, -1):
			x = e * bx
			bogie(p + f'bogie{e}', COLL, x, 'black', wheel_r=r, wheelbase=wb)
			if co:
				for s in (1, -1):
					wheel(p + f'mid_wheel{e}{s}', COLL, x, r, s, seg=12)
		tl = 0.95 if co else 1.2
		box(p + 'tank', COLL, (-tl, -1.25, 0.85), (tl, 1.25, ZB), 'black')
		for s in (1, -1):
			cyl_x(p + f'air_tank{s}', COLL, s * 1.32, 1.05, 0.2, -1.1, 1.1, 10, 'steel')
			for e in (1, -1):
				box(p + f'step{e}{s}', COLL, (e * 3.25 - 0.25, min(s * 1.45, s * 1.75), 1.15), (e * 3.25 + 0.25, max(s * 1.45, s * 1.75), 1.25), 'black')
	else:
		maglev = spec.under == 'maglev'
		box(p + 'skirt', COLL, (-X + 0.35, -1.38, 0.72), (X - 0.35, 1.38, ZB), 'black')
		for e in (1, -1):
			for s in (1, -1):
				box(p + f'pod{e}{s}', COLL, (e * 2.3 - 0.9, min(s * 1.38, s * 1.45), 0.85), (e * 2.3 + 0.9, max(s * 1.38, s * 1.45), 1.35), 'steel' if maglev else 'wagon_grey')
		if maglev:
			for s in (1, -1):
				side(s, -X + 0.4, X - 0.4, 0.75, 0.85, 'hazard_yellow', out=0.02, y=1.38)


def modern(p, spec):
	loft(p + 'body', COLL, stations(spec.front, spec.back), spec.body, cap_front=spec.end_mat or spec.body, cap_back=spec.end_mat or spec.body, mat_fn=paint(spec))
	cab_screens(p, spec)
	side_windows(p, spec)
	roof_kit(p, spec)
	end_fittings(p, spec)
	underframe(p, spec)
	if spec.extra:
		spec.extra(p, spec)


# ---- steam ----------------------------------------------------------------------------------------------------

def drivers(p, xs, r, spokes, cyl_x0, cyl_y=RAIL_Y + 0.05):
	"""Coupled driving wheels with balance weights, coupling rods, a connecting rod and outside cylinders."""
	cz = RAIL_TOP + r
	for s in (1, -1):
		for i, x in enumerate(xs):
			wheel(p + f'driver{i}{s}', COLL, x, r, s, spokes=spokes, seg=18)
			pts = [(x + r * 0.78 * math.cos(a), cz + r * 0.78 * math.sin(a)) for a in [math.radians(200 + 14 * k) for k in range(10)]]
			pts += [(x + r * 0.5 * math.cos(a), cz + r * 0.5 * math.sin(a)) for a in reversed([math.radians(200 + 14 * k) for k in range(10)])]
			y = s * (RAIL_Y + 0.12)
			mesh(p + f'weight{i}{s}', COLL, [(px, y, pz) for px, pz in pts], [tuple(range(len(pts)))], ['black'])
		pin = lambda x: (x + r * 0.4, cz + 0.1)
		rod(p + f'coupling{s}', COLL, pin(xs[0]), pin(xs[-1]), s * (RAIL_Y + 0.17), 0.13, 0.06, 'steel_light')
		rod(p + f'connecting{s}', COLL, pin(xs[len(xs) // 2]), (cyl_x0 - 0.05, cz + 0.15), s * (RAIL_Y + 0.23), 0.14, 0.06, 'steel_light')
		box(p + f'slidebar{s}', COLL, (cyl_x0 - 0.9, s * (RAIL_Y + 0.2) - 0.04, cz + 0.3), (cyl_x0, s * (RAIL_Y + 0.2) + 0.04, cz + 0.36), 'steel')
		cyl_x(p + f'cylinder{s}', COLL, s * cyl_y, cz + 0.22, 0.28, cyl_x0, cyl_x0 + 0.6, 10, 'black', cap_mat='black')


def boiler(p, x0, x1, smoke_x, r, cz, chimney_x, dome_x, bands):
	cyl_x(p + 'boiler', COLL, 0.0, cz, r, x0, smoke_x, 18, 'cc1')
	cyl_x(p + 'smokebox', COLL, 0.0, cz, r + 0.04, smoke_x, x1, 18, 'black', cap_mat='black')
	cyl_x(p + 'smokebox_door', COLL, 0.0, cz, r * 0.75, x1, x1 + 0.06, 14, 'black', cap_mat='steel')
	for x in bands:
		cyl_x(p + f'band{x}', COLL, 0.0, cz, r + 0.02, x - 0.04, x + 0.04, 18, 'black')
	cyl_z(p + 'chimney', COLL, chimney_x, 0.0, 0.26, 0.26, cz + r - 0.1, cz + r + 0.65, 12, 'black')
	cyl_z(p + 'chimney_lip', COLL, chimney_x, 0.0, 0.33, 0.33, cz + r + 0.55, cz + r + 0.7, 12, 'black')
	cyl_z(p + 'dome', COLL, dome_x, 0.0, 0.38, 0.38, cz + r - 0.15, cz + r + 0.35, 12, 'cc1', cap_mat='steel_light')
	cyl_z(p + 'safety_valve', COLL, (x0 + dome_x) / 2, 0.0, 0.16, 0.16, cz + r - 0.1, cz + r + 0.3, 8, 'steel_light')
	cyl_z(p + 'whistle', COLL, x0 + 0.25, 0.0, 0.05, 0.05, cz + r - 0.1, cz + r + 0.35, 6, 'steel_light')


def cab(p, x0, x1, z_top, front_x=None):
	"""Cab with side windows, a curved roof and a spectacle plate facing the boiler."""
	prof = mirror_y([(1.7, 1.95), (1.7, z_top - 0.4), (1.58, z_top - 0.12), (1.2, z_top + 0.05), (0.0, z_top + 0.12)])
	loft(p + 'cab', COLL, [(x0, prof), (x1, prof)], 'cc1', cap_front='cc1', cap_back='cc1', mat_fn=lambda a, b, z, i: 'roof_dark' if z > z_top - 0.2 else 'cc1')
	for s in (1, -1):
		side(s, x0 + 0.3, x1 - 0.3, z_top - 1.5, z_top - 0.55, 'glass_dark', y=1.7)
		side(s, x0 + 0.05, x0 + 0.15, 2.2, z_top - 0.5, 'steel_light', out=0.05, y=1.7)
	for y in (-0.8, 0.8):
		box(p + f'spectacle{y}', COLL, (x1, y - 0.3, z_top - 1.1), (x1 + 0.03, y + 0.3, z_top - 0.55), 'glass_dark')


def beams(p, back_x, front_x):
	box(p + 'beam_front', COLL, (front_x - 0.12, -1.55, 1.15), (front_x, 1.55, 1.9), 'signal_red')
	box(p + 'beam_back', COLL, (back_x, -1.55, 1.15), (back_x + 0.12, 1.55, 1.9), 'signal_red')
	buffers(p + 'buffers_front', COLL, front_x, 1, z=1.5, y=1.1, length=0.3, r=0.2)
	buffers(p + 'buffers_back', COLL, back_x, -1, z=1.5, y=1.1, length=0.25, r=0.2)
	for s in (1, -1):
		cyl_z(p + f'lamp{s}', COLL, front_x - 0.1, s * 1.0, 0.12, 0.12, 1.9, 2.2, 8, 'black')
		box(p + f'lamp_lens{s}', COLL, (front_x + 0.02, s * 1.0 - 0.08, 1.97), (front_x + 0.06, s * 1.0 + 0.08, 2.13), 'lamp_yellow')


def tank_engine(p):
	"""Kirby Paul Tank: 0-6-0 side tank with a bunker behind the cab."""
	box(p + 'running_plate', COLL, (-3.75, -1.72, 1.8), (3.6, 1.72, 1.95), 'black')
	for s in (1, -1):
		box(p + f'frame{s}', COLL, (-3.7, s * 1.05 - 0.08, 0.95), (3.55, s * 1.05 + 0.08, 1.8), 'black')
	boiler(p, -1.4, 3.45, 2.65, 0.95, 3.35, 2.95, 0.9, (0.0, 1.4))
	for s in (1, -1):  # side tanks with a top lip and a filler
		box(p + f'tank{s}', COLL, (-1.4, min(s * 0.85, s * 1.7), 1.95), (2.4, max(s * 0.85, s * 1.7), 3.9), 'cc1')
		box(p + f'tank_lip{s}', COLL, (-1.42, min(s * 0.83, s * 1.72), 3.85), (2.42, max(s * 0.83, s * 1.72), 3.95), 'black')
		box(p + f'tank_lining{s}', COLL, (-1.2, min(s * 1.7, s * 1.72), 2.15), (2.2, max(s * 1.7, s * 1.72), 2.22), 'cc2')
		cyl_z(p + f'filler{s}', COLL, 1.9, s * 1.25, 0.18, 0.18, 3.9, 4.05, 8, 'black')
	cab(p, -3.0, -1.4, 5.3)
	# Bunker with coal behind the cab.
	box(p + 'bunker', COLL, (-3.75, -1.6, 1.95), (-3.0, 1.6, 3.9), 'cc1')
	bulk_load(p + 'bunker_coal', COLL, -3.7, -3.05, 1.5, 3.85, 0.35, 'coal', nx=4, ny=4, seed=0)
	drivers(p, (-1.75, -0.2, 1.35), 0.68, 12, 2.4)
	beams(p, -3.9, 3.72)


def tender_engine(p):
	"""Jubilee: 4-6-0 with a short coal tender behind the cab."""
	box(p + 'running_plate', COLL, (-2.5, -1.72, 1.95), (3.6, 1.72, 2.08), 'black')
	for s in (1, -1):
		box(p + f'frame{s}', COLL, (-2.5, s * 1.05 - 0.08, 0.95), (3.6, s * 1.05 + 0.08, 1.95), 'black')
		box(p + f'valance{s}', COLL, (-2.5, min(s * 1.6, s * 1.72), 1.75), (3.6, max(s * 1.6, s * 1.72), 2.08), 'black')
	boiler(p, -1.35, 3.6, 2.8, 1.0, 3.25, 3.15, 1.3, (-0.4, 0.6, 1.6))
	# Firebox shoulders between the boiler and the cab.
	box(p + 'firebox', COLL, (-1.35, -1.1, 2.08), (-0.6, 1.1, 4.0), 'cc1')
	cab(p, -2.4, -1.35, 5.35)
	# Tender: sides, coal space, axleboxes.
	box(p + 'tender', COLL, (-3.85, -1.62, 1.6), (-2.5, 1.62, 3.95), 'cc1')
	bulk_load(p + 'tender_coal', COLL, -3.8, -2.55, 1.5, 3.9, 0.45, 'coal', nx=4, ny=5, seed=8)
	box(p + 'tender_lining', COLL, (-3.8, -1.63, 2.0), (-2.55, 1.63, 2.07), 'cc2')
	for i, x in enumerate((-3.45, -2.85)):
		for s in (1, -1):
			wheel(p + f'tender_wheel{i}{s}', COLL, x, 0.42, s, seg=12)
			box(p + f'tender_axlebox{i}{s}', COLL, (x - 0.15, min(s * 1.82, s * 1.95), 0.9), (x + 0.15, max(s * 1.82, s * 1.95), 1.3), 'black')
	for s in (1, -1):
		for i, x in enumerate((2.35, 3.1)):
			wheel(p + f'bogie_wheel{i}{s}', COLL, x, 0.38, s, seg=12)
		for i, x in enumerate((-1.45, -0.1, 1.25)):  # splashers over the drivers
			box(p + f'splasher{i}{s}', COLL, (x - 0.72, min(s * 1.45, s * 1.72), 2.08), (x + 0.72, max(s * 1.45, s * 1.72), 2.35), 'cc1')
	drivers(p, (-1.45, -0.1, 1.25), 0.64, 14, 2.3, cyl_y=1.95)  # outside cylinders clear of the bogie wheels
	box(p + 'beam_front', COLL, (3.48, -1.55, 1.15), (3.6, 1.55, 2.0), 'signal_red')
	buffers(p + 'buffers_front', COLL, 3.6, 1, z=1.5, y=1.1, length=0.3, r=0.2)
	box(p + 'beam_back', COLL, (-3.95, -1.55, 1.15), (-3.85, 1.55, 1.6), 'black')
	buffers(p + 'buffers_back', COLL, -3.95, -1, z=1.4, y=1.1, length=0.2, r=0.18)
	for s in (1, -1):
		cyl_z(p + f'lamp{s}', COLL, 3.5, s * 1.0, 0.12, 0.12, 2.08, 2.38, 8, 'black')
		box(p + f'lamp_lens{s}', COLL, (3.62, s * 1.0 - 0.08, 2.15), (3.66, s * 1.0 + 0.08, 2.31), 'lamp_yellow')


# ---- members ------------------------------------------------------------------------------------------------

def hst_back(p, spec):
	box(p + 'gangway', COLL, (-X - 0.2, -0.6, ZB + 0.3), (-X, 0.6, 4.6), 'black')


def maglev_grilles(p, spec):
	for s in (1, -1):
		for k in range(4):
			x = -1.9 + 1.25 * k
			side(s, x - 0.45, x + 0.45, 2.7, 3.4, 'black', out=0.025)
			for z in (2.85, 3.1):
				side(s, x - 0.4, x + 0.4, z, z + 0.08, 'steel', out=0.04)


def cyclops_windows(p, spec):
	for s in (1, -1):
		for k in range(4):
			x = -1.65 + 1.1 * k
			side(s, x - 0.4, x + 0.4, 3.6, 4.4, 'glass_dark')


SPECS = {
	11: dict(side_windows='saloon', bands=[(3.8, 4.6, 'wagon_grey')], roof_kit=None, end_z=3.8),  # DMU
	12: dict(side_windows='saloon', bands=[(1.4, 2.0, 'wagon_grey')], roof_kit=None, end_z=3.8),  # 'Dash'
	13: dict(bands=[(4.3, 4.6, 'hazard_yellow')]),  # '25'
	14: dict(front=Nose('hood', 1.0), back=Nose('hood', 1.0), axles=3, bands=[(4.3, 4.6, 'hazard_yellow')], end_full=True),  # '37'
	22: dict(front=Nose('wedge', 2.3, drop=0.5, pinch=0.25, power=1.5), back=Nose('flat', 0.2, drop=0.02, pinch=0.04, power=2), side_windows='cab',
		bands=[(1.4, 2.0, 'wagon_grey')], end_z=3.8, glass=(0.2, 0.75, 3.8, 5.3), extra=hst_back, rear_mat='plaster_white'),  # '125'
	23: dict(roof_kit='electric', pans=(-1.9, 1.9), bands=[(4.3, 4.6, 'hazard_yellow'), (1.4, 2.0, 'wagon_grey')], end_full=True),  # '30'
	25: dict(front=Nose('wedge', 2.0, drop=0.42, pinch=0.2, power=1.4), back=FLAT, body='concrete_dark', bands=[(3.8, 4.3, 'cc1')], end_mat='cc1', end_z=4.3,
		roof='steel', roof_kit='electric', pans=(-1.5,), glass=(0.3, 0.75, 4.3, 5.4)),  # T.I.M.
	26: dict(front=Nose('bullet', 2.6, drop=0.6, pinch=0.4, power=1.8), back=FLAT, skirt=(2.6, 'wagon_grey'), end_mat=None, roof='cc1',
		roof_kit='electric', pans=(-1.6,), glass=(0.2, 0.6, 4.3, 5.5)),  # AsiaStar
	54: dict(under='mono', end_full=True, roof_kit='sleek', side_windows='saloon', bands=[(4.6, 4.85, 'hazard_yellow')]),  # X2001
	55: dict(under='mono', front=Nose('bullet', 2.4, drop=0.55, pinch=0.35, power=1.7), back=FLAT, end_mat=None, roof='cc1', rear_mat='plaster_white',
		bands=[(2.0, 2.6, 'hazard_yellow')], roof_kit='sleek', glass=(0.2, 0.65, 3.8, 5.5)),  # Millennium Z1
	84: dict(under='maglev', front=Nose('bullet', 0.9, drop=0.25, pinch=0.3, power=1.6), back=Nose('bullet', 0.9, drop=0.25, pinch=0.3, power=1.6),
		end_full=True, glass=(0.45, 0.8, 3.8, 4.85), roof_kit='sleek', side_windows=None, extra=maglev_grilles),  # Leviathan
	85: dict(under='maglev', front=Nose('bullet', 1.2, drop=0.4, pinch=0.3, power=1.5), back=Nose('bullet', 1.2, drop=0.4, pinch=0.3, power=1.5),
		end_full=True, roof='cc1', glass=(0.35, 0.8, 3.2, 4.85), side_windows=None, bands=[(4.6, 4.85, 'hazard_yellow'), (2.0, 2.6, 'hazard_yellow')],
		roof_kit='sleek', extra=cyclops_windows),  # Cyclops
	86: dict(under='maglev', front=Nose('bullet', 2.8, drop=0.62, pinch=0.42, power=1.8), back=FLAT, end_mat='hazard_yellow', end_z=2.6, roof='cc1',
		bands=[(4.6, 4.85, 'hazard_yellow'), (2.0, 2.6, 'hazard_yellow')], glass=(0.25, 0.6, 3.8, 5.5), roof_kit='sleek'),  # Pegasus
	87: dict(under='maglev', front=Nose('wedge', 2.2, drop=0.5, pinch=0.3, power=1.5), back=FLAT, end_full=True, roof='cc1', rear_mat='plaster_white',
		bands=[(1.4, 2.0, 'hazard_yellow')], glass=(0.3, 0.8, 4.3, 5.5), roof_kit='sleek'),  # Chimaera
}

COLL = bpy.data.collections['default']
clear(COLL)
p = 'default_'
if N == 0:
	tank_engine(p)
elif N == 8:
	tender_engine(p)
else:
	spec = Spec(extra=None)
	spec.__dict__.update(SPECS[N])
	modern(p, spec)
result = {'default': triangles(COLL)}
