"""Ginzu 'A4' (engine 9, shared with toyland engine 4): streamlined 4-6-2 in company colour.
Run in Blender with train_009.blend open, after vehicle_kit.py has been executed in the same namespace."""
import math
import bpy

coll = bpy.data.collections['default']
clear(coll)

# Casing cross-section, half profile from the valance foot up to the crown (y, z).
CASING = [(1.72, 1.95), (1.74, 2.4), (1.74, 3.6), (1.68, 4.4), (1.52, 5.05), (1.26, 5.6), (0.92, 6.0), (0.48, 6.24), (0.0, 6.32)]
SKIRT_TOP = 2.4  # below this the casing is the black valance edge


def casing_at(x):
	"""The A4 wedge: from x=1.0 the crown drops and the upper sides pull in to the beak at the front."""
	t = max(0.0, min(1.0, (x - 1.0) / 2.85))
	drop = t ** 1.6  # crown falls faster towards the front
	pinch = t ** 1.3
	prof = []
	for y, z in CASING:
		h = (z - 1.95) / (6.32 - 1.95)  # 0 at the valance foot, 1 at the crown
		zz = 1.95 + (z - 1.95) * (1 - 0.48 * drop * (0.4 + 0.6 * h))
		yy = y * (1 - pinch * (0.18 + 0.72 * h * h))
		if h < 0.15:  # the valance foot curves in at the very front
			yy = y * (1 - 0.35 * t ** 4)
		prof.append((yy, zz))
	return mirror_y(prof)


def casing_mat(x0, x1, zmid, i):
	if zmid < 2.2:
		return 'black'  # valance lower edge
	if x0 >= 2.95 and zmid < 3.5:
		return 'black'  # the smokebox mouth under the beak
	return 'cc1'


stations = [(x, casing_at(x)) for x in (-2.0, -1.0, 0.0, 1.0, 1.5, 2.0, 2.45, 2.85, 3.2, 3.5, 3.72, 3.85)]
loft('casing', coll, stations, 'cc1', cap_front=lambda za, zb: 'black' if (za + zb) / 2 < 3.5 else 'cc1', mat_fn=casing_mat)

# Garter-style lining: a thin cc2 stripe along the valance top, and the chime of the wedge.
for s in (1, -1):
	box(f'lining_{s}', coll, (-2.0, s * 1.745 - 0.01, 2.38), (2.3, s * 1.745 + 0.01, 2.5), 'cc2')
	box(f'nameplate_{s}', coll, (-0.35, s * 1.75 - 0.015, 3.05), (0.75, s * 1.75 + 0.015, 3.4), 'steel_light')
	box(f'handrail_{s}', coll, (-1.95, s * 1.72 - 0.03, 4.45), (1.4, s * 1.72 + 0.03, 4.52), 'steel_light')

# Cab: flat sides, raked front windows, curved roof; the rear meets the (implied) tender.
CAB = [(1.76, 1.95), (1.76, 5.4), (1.62, 5.85), (1.28, 6.2), (0.7, 6.4), (0.0, 6.45)]
cab_prof = mirror_y(CAB)
loft('cab', coll, [(-3.8, cab_prof), (-2.0, cab_prof)], 'cc1', cap_back='cc1', cap_front='cc1',
	mat_fn=lambda x0, x1, z, i: 'black' if z < 2.2 else 'cc1')
# Cab front above the casing crown, with the A4's angled spectacle windows.
for s in (1, -1):
	box(f'cab_spectacle_{s}', coll, (-2.03, s * 0.75 - 0.35, 5.55), (-1.98, s * 0.75 + 0.35, 6.05), 'glass_dark')
for s in (1, -1):
	box(f'cab_window_{s}', coll, (-3.4, s * 1.76 - 0.02, 4.35), (-2.3, s * 1.76 + 0.02, 5.3), 'glass_dark')
	box(f'cab_window_frame_{s}', coll, (-2.9, s * 1.76 - 0.03, 4.35), (-2.8, s * 1.76 + 0.03, 5.3), 'cc1')
	box(f'cab_step_{s}', coll, (-3.6, s * 1.55, 1.2), (-3.1, s * 1.85, 1.3), 'black')
	box(f'cab_grab_{s}', coll, (-3.72, s * 1.77 - 0.02, 2.6), (-3.66, s * 1.77 + 0.02, 4.8), 'steel_light')
# Cab rear: the fall plate opening towards the tender.
box('cab_door', coll, (-3.83, -0.85, 1.95), (-3.79, 0.85, 5.4), 'black')
box('roof_vent', coll, (-3.3, -0.3, 6.42), (-2.6, 0.3, 6.52), 'roof_dark')

# Chimney (flush, double), whistle and the beak's top cleft.
cyl_z('chimney', coll, 1.25, 0.0, 0.42, 0.24, 6.05, 6.22, 12, 'black')
cyl_z('whistle', coll, -0.9, 0.0, 0.06, 0.06, 6.3, 6.55, 6, 'steel_light')

# Frames, underfloor and footsteps hidden behind the valance.
box('floor', coll, (-3.8, -1.74, 1.9), (3.7, 1.74, 1.95), 'black')
for s in (1, -1):
	box(f'frame_{s}', coll, (-3.75, s * 1.05 - 0.08, 0.95), (3.75, s * 1.05 + 0.08, 1.95), 'black')

# Running gear: 4-6-2. Bogie and trailing wheels plain, drivers spoked with balance weights.
DRIVERS = (-1.95, -0.3, 1.35)
for s in (1, -1):
	for i, x in enumerate((2.55, 3.45)):
		wheel(f'bogie_{i}_{s}', coll, x, 0.45, s, seg=12)
	wheel(f'trailing_{s}', coll, -3.15, 0.5, s, seg=12)
	for i, x in enumerate(DRIVERS):
		w = wheel(f'driver_{i}_{s}', coll, x, 0.8, s, spokes=10, seg=20)
		# Crescent balance weight opposite the crank.
		cz = RAIL_TOP + 0.8
		pts = [(x + 0.62 * math.cos(a), cz + 0.62 * math.sin(a)) for a in [math.radians(200 + 14 * k) for k in range(10)]]
		pts += [(x + 0.4 * math.cos(a), cz + 0.4 * math.sin(a)) for a in reversed([math.radians(200 + 14 * k) for k in range(10)])]
		y = s * (RAIL_Y + 0.12)
		mesh(f'weight_{i}_{s}', coll, [(px, y, pz) for px, pz in pts], [tuple(range(len(pts)))], ['black'])
	# Coupling rod over the crank pins, connecting rod back to the crosshead, slide bars, cylinder.
	cz = RAIL_TOP + 0.8
	pin = lambda x: (x + 0.32, cz + 0.12)
	y = s * (RAIL_Y + 0.17)
	rod(f'coupling_{s}', coll, pin(DRIVERS[0]), pin(DRIVERS[2]), y, 0.14, 0.06, 'steel_light')
	rod(f'connecting_{s}', coll, pin(DRIVERS[1]), (2.6, cz + 0.2), s * (RAIL_Y + 0.23), 0.16, 0.06, 'steel_light')
	box(f'slidebar_{s}', coll, (2.2, s * (RAIL_Y + 0.2) - 0.04, cz + 0.32), (3.25, s * (RAIL_Y + 0.2) + 0.04, cz + 0.38), 'steel')
	cyl_x(f'cylinder_{s}', coll, s * (RAIL_Y + 0.05), cz + 0.25, 0.32, 3.1, 3.7, 10, 'black', cap_mat='black')
	for x in DRIVERS:
		cyl_x(f'pin_{x}_{s}', coll, s * (RAIL_Y + 0.25), cz + 0.12, 0.07, x + 0.25, x + 0.39, 6, 'steel')
	box(f'sandbox_{s}', coll, (0.4, s * 1.25 - 0.15, 1.3), (0.8, s * 1.25 + 0.15, 1.9), 'black')

# Buffer beams, buffers, lamps.
box('beam_front', coll, (3.7, -1.5, 1.2), (3.85, 1.5, 1.95), 'signal_red')
box('beam_back', coll, (-3.85, -1.5, 1.2), (-3.75, 1.5, 1.95), 'signal_red')
buffers('buffers_front', coll, 3.85, 1, z=1.55, y=1.1, length=0.3, r=0.2)
buffers('buffers_back', coll, -3.85, -1, z=1.55, y=1.1, length=0.25, r=0.2)
for s in (1, -1):
	cyl_z(f'lamp_{s}', coll, 3.78, s * 1.0, 0.12, 0.12, 1.95, 2.25, 8, 'black')
	box(f'lamp_lens_{s}', coll, (3.88, s * 1.0 - 0.08, 2.02), (3.92, s * 1.0 + 0.08, 2.18), 'lamp_yellow')
cyl_z('lamp_top', coll, 3.95, 0.0, 0.12, 0.12, 3.6, 3.9, 8, 'black')
box('lamp_lens_top', coll, (4.05, -0.08, 3.67), (4.09, 0.08, 3.83), 'lamp_yellow')

result = {'triangles': triangles(coll), 'objects': len(coll.objects)}
