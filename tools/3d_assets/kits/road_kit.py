"""Phase 8.5 road vehicle kit: lorry cabs (three styles), chassis, wheels and rear fittings.
Run inside Blender after vehicle_kit.py, in the same namespace. Units as in vehicle_kit.py; +X forward.
Cab styles follow the three generations each lorry cargo has in the base set:
  0 - raked windscreen and a low crown (the approved Balogh coal truck),
  1 - taller cab with a rounded roof, an upright windscreen under a visor,
  2 - wedge cab with a long sloped dark windscreen."""
import bpy

FRONT_AXLE, REAR_AXLE, WHEEL_R = 2.55, -2.2, 0.72
CAB_X0, CAB_X1, WIDTH = 1.45, 3.7, 1.55
BED_X0, BED_X1, BED_Z0 = -3.6, 1.2, 1.75

# Glasshouse cross-section, half profile from the waist up to the roof crown.
UPPER = [(1.55, 3.0), (1.55, 4.15), (1.42, 4.45), (1.1, 4.62), (0.55, 4.7), (0.0, 4.72)]
UPPER_ROUND = [(1.55, 3.0), (1.55, 4.25), (1.5, 4.6), (1.3, 4.86), (0.85, 5.02), (0.0, 5.08)]


def upper(scale_z, prof=UPPER):
	return mirror_y([(y * (1 - 0.06 * (1 - scale_z)), 3.0 + (z - 3.0) * scale_z) for y, z in prof])


def cab_lower(p, coll):
	"""Lower cab: body boxes either side of the front wheel arch."""
	arch = WHEEL_R + 0.12
	box(p + 'cab_back', coll, (CAB_X0, -WIDTH, 1.25), (FRONT_AXLE - arch, WIDTH, 3.0), 'cc1')
	box(p + 'cab_arch', coll, (FRONT_AXLE - arch, -WIDTH, ROAD_LIFT + 2 * WHEEL_R + 0.12), (FRONT_AXLE + arch, WIDTH, 3.0), 'cc1')
	box(p + 'cab_front', coll, (FRONT_AXLE + arch, -WIDTH, 1.25), (CAB_X1, WIDTH, 3.0), 'cc1')


def cab_style0(p, coll):
	# The raked front: a short roof edge, then the windscreen between the corner pillars.
	windscreen = lambda x0, x1, z, i: 'glass_dark' if x0 >= 3.3 and 1 < i < 8 else 'cc1'
	loft(p + 'cab_upper', coll, [(CAB_X0, upper(1.0)), (3.2, upper(1.0)), (3.3, upper(0.9)), (3.62, upper(0.12))], 'cc1', cap_back='cc1', mat_fn=windscreen)
	box(p + 'wiper', coll, (3.5, -0.6, 3.25), (3.6, 0.1, 3.3), 'black')
	for s in (1, -1):
		y = s * WIDTH
		box(p + f'side_window{s}', coll, (2.35, min(y, y + s * 0.02), 3.2), (3.1, max(y, y + s * 0.02), 4.15), 'glass_dark')
		box(p + f'rear_window{s}', coll, (1.6, min(y, y + s * 0.02), 3.35), (2.15, max(y, y + s * 0.02), 4.1), 'glass_dark')
		box(p + f'mirror_arm{s}', coll, (3.35, min(y, y + s * 0.35), 3.7), (3.4, max(y, y + s * 0.35), 3.75), 'black')
		box(p + f'mirror{s}', coll, (3.3, min(y + s * 0.3, y + s * 0.4), 3.35), (3.4, max(y + s * 0.3, y + s * 0.4), 3.95), 'black')
	box(p + 'roof_marker', coll, (3.0, -0.5, 4.66), (3.2, 0.5, 4.76), 'leaf_orange')
	box(p + 'grille', coll, (CAB_X1, -0.85, 1.55), (CAB_X1 + 0.04, 0.85, 2.75), 'steel_light')
	for k in range(5):
		z = 1.7 + 0.22 * k
		box(p + f'grille_slat{k}', coll, (CAB_X1 + 0.04, -0.8, z), (CAB_X1 + 0.07, 0.8, z + 0.08), 'black')


def cab_style1(p, coll):
	# Tall rounded cab: near-upright windscreen with rounded top corners, a sun visor and three roof lamps.
	windscreen = lambda x0, x1, z, i: 'glass_dark' if x0 >= 3.45 and 0 < i < 9 and z < 4.75 else 'cc1'
	stations = [(CAB_X0, upper(1.0, UPPER_ROUND)), (3.3, upper(1.0, UPPER_ROUND)), (3.48, upper(0.96, UPPER_ROUND)), (3.66, upper(0.86, UPPER_ROUND)), (3.72, upper(0.7, UPPER_ROUND))]
	loft(p + 'cab_upper', coll, stations, 'cc1', cap_back='cc1', cap_front='cc1', mat_fn=windscreen)
	box(p + 'visor', coll, (3.55, -1.35, 4.6), (3.95, 1.35, 4.68), 'cc1')
	box(p + 'wiper_l', coll, (3.73, -1.0, 3.2), (3.76, -0.2, 3.25), 'black')
	box(p + 'wiper_r', coll, (3.73, 0.2, 3.2), (3.76, 1.0, 3.25), 'black')
	box(p + 'pillar', coll, (3.72, -0.04, 3.05), (3.75, 0.04, 4.45), 'cc1')  # split windscreen
	for k in (-1, 0, 1):
		box(p + f'roof_lamp{k}', coll, (3.25, k * 0.45 - 0.1, 5.02), (3.45, k * 0.45 + 0.1, 5.12), 'leaf_orange')
	for s in (1, -1):
		y = s * WIDTH
		box(p + f'side_window{s}', coll, (2.4, min(y, y + s * 0.02), 3.15), (3.3, max(y, y + s * 0.02), 4.3), 'glass_dark')
		box(p + f'quarter_window{s}', coll, (1.65, min(y, y + s * 0.02), 3.6), (2.15, max(y, y + s * 0.02), 4.3), 'glass_dark')
		box(p + f'mirror_arm{s}', coll, (3.4, min(y, y + s * 0.4), 3.9), (3.45, max(y, y + s * 0.4), 3.95), 'black')
		box(p + f'mirror{s}', coll, (3.35, min(y + s * 0.32, y + s * 0.44), 3.3), (3.45, max(y + s * 0.32, y + s * 0.44), 4.05), 'black')
		box(p + f'kick_panel{s}', coll, (2.35, min(y, y + s * 0.03), 1.25), (3.35, max(y, y + s * 0.03), 1.45), 'black')
	# Vertical-bar grille with a surround.
	box(p + 'grille', coll, (CAB_X1, -0.95, 1.6), (CAB_X1 + 0.04, 0.95, 2.8), 'black')
	for k in range(9):
		y = -0.85 + 0.2125 * k
		box(p + f'grille_bar{k}', coll, (CAB_X1 + 0.04, y - 0.04, 1.65), (CAB_X1 + 0.08, y + 0.04, 2.75), 'steel_light')


def cab_style2(p, coll):
	# Wedge cab: the windscreen runs from the roof at x 2.75 down to the waist at the nose; a wide black grille band.
	windscreen = lambda x0, x1, z, i: 'glass_dark' if x0 >= 2.75 and 0 < i < 9 else 'cc1'
	loft(p + 'cab_upper', coll, [(CAB_X0, upper(1.0)), (2.75, upper(1.0)), (3.66, upper(0.06))], 'cc1', cap_back='cc1', cap_front='cc1', mat_fn=windscreen)
	box(p + 'air_dam', coll, (CAB_X0 + 0.1, -1.2, 4.7), (2.6, 1.2, 4.95), 'cc1')  # roof deflector
	box(p + 'air_dam_top', coll, (CAB_X0 + 0.1, -1.0, 4.95), (2.2, 1.0, 5.15), 'cc1')
	box(p + 'wiper', coll, (3.2, -0.8, 3.75), (3.3, 0.6, 3.8), 'black')
	for s in (1, -1):
		y = s * WIDTH
		box(p + f'side_window{s}', coll, (2.3, min(y, y + s * 0.02), 3.15), (2.95, max(y, y + s * 0.02), 4.2), 'glass_dark')
		box(p + f'mirror_arm{s}', coll, (3.1, min(y, y + s * 0.35), 3.7), (3.15, max(y, y + s * 0.35), 3.75), 'black')
		box(p + f'mirror{s}', coll, (3.05, min(y + s * 0.28, y + s * 0.4), 3.25), (3.15, max(y + s * 0.28, y + s * 0.4), 3.95), 'black')
		box(p + f'side_skirt{s}', coll, (3.0, min(y, y + s * 0.03), 1.25), (CAB_X1, max(y, y + s * 0.03), 1.6), 'black')
	box(p + 'grille', coll, (CAB_X1, -1.35, 2.05), (CAB_X1 + 0.04, 1.35, 2.75), 'black')
	for k in range(3):
		z = 2.15 + 0.2 * k
		box(p + f'grille_slat{k}', coll, (CAB_X1 + 0.04, -1.25, z), (CAB_X1 + 0.07, 1.25, z + 0.07), 'steel')


def cab(p, coll, style):
	"""Cab with doors, steps, lights, bumper and plate; the style picks the glasshouse and grille."""
	cab_lower(p, coll)
	(cab_style0, cab_style1, cab_style2)[style](p, coll)
	for s in (1, -1):
		y = s * WIDTH
		box(p + f'door_line{s}', coll, (2.25, min(y, y + s * 0.025), 1.95), (2.3, max(y, y + s * 0.025), 4.3), 'black')
		box(p + f'door_handle{s}', coll, (2.4, min(y, y + s * 0.05), 2.75), (2.65, max(y, y + s * 0.05), 2.82), 'steel_light')
		box(p + f'step{s}', coll, (2.35, min(s * 1.3, s * 1.62), 1.05), (2.95, max(s * 1.3, s * 1.62), 1.15), 'black')
		if style == 2:  # rectangular lamp clusters in the grille band
			box(p + f'headlight{s}', coll, (CAB_X1, s * 1.05 - 0.25, 2.1), (CAB_X1 + 0.06, s * 1.05 + 0.25, 2.4), 'lamp_yellow')
		else:
			cyl_x(p + f'headlight{s}', coll, s * (1.15 if style == 0 else 1.22), 2.2, 0.24, 3.65, 3.8, 10, 'steel_light', cap_mat='lamp_yellow')
		box(p + f'indicator{s}', coll, (3.7, s * 1.42 - 0.08, 2.6), (3.74, s * 1.42 + 0.08, 2.75), 'leaf_orange')
	box(p + 'bumper', coll, (CAB_X1, -WIDTH, 1.0), (CAB_X1 + 0.18, WIDTH, 1.35), 'steel_light' if style < 2 else 'black')
	box(p + 'plate', coll, (CAB_X1 + 0.18, -0.35, 1.08), (CAB_X1 + 0.2, 0.35, 1.27), 'plaster_white')


def chassis(p, coll, tank=True, ram=False):
	"""Chassis rails and crossmembers, fuel tank, battery box, exhaust stack; optional tipper ram."""
	for s in (1, -1):
		box(p + f'chassis{s}', coll, (-3.55, s * 0.85 - 0.12, 0.95), (CAB_X1 - 0.1, s * 0.85 + 0.12, 1.3), 'black')
	for x in (-3.4, -1.0, 0.9):
		box(p + f'crossmember{x}', coll, (x - 0.1, -0.85, 1.0), (x + 0.1, 0.85, 1.25), 'black')
	if tank:
		cyl_x(p + 'fuel_tank', coll, -1.2, 1.0, 0.36, -0.6, 0.6, 12, 'steel_light')
	box(p + 'battery_box', coll, (-0.5, 0.95, 0.75), (0.4, 1.45, 1.3), 'black')
	cyl_z(p + 'exhaust', coll, CAB_X0 - 0.12, 1.25, 0.1, 0.1, 1.3, 4.95, 8, 'black')
	cyl_z(p + 'exhaust_cap', coll, CAB_X0 - 0.12, 1.25, 0.13, 0.13, 4.95, 5.05, 8, 'black')
	if ram:
		cyl_z(p + 'tipper_ram', coll, BED_X1 + 0.1, 0.0, 0.16, 0.16, 1.3, 2.4, 8, 'steel_light')


def rear(p, coll):
	"""Rear mudguards over the duals, mudflaps and tail lights."""
	for s in (1, -1):
		y = s * WIDTH
		box(p + f'rear_guard{s}', coll, (REAR_AXLE - 0.95, min(s * 0.7, y), ROAD_LIFT + 2 * WHEEL_R + 0.08), (REAR_AXLE + 0.95, max(s * 0.7, y), ROAD_LIFT + 2 * WHEEL_R + 0.16), 'black')
		box(p + f'mudflap{s}', coll, (REAR_AXLE - 0.98, min(s * 0.75, y), 0.45), (REAR_AXLE - 0.94, max(s * 0.75, y), ROAD_LIFT + 2 * WHEEL_R + 0.1), 'black')
		box(p + f'tail_light{s}', coll, (-3.66, s * 1.3 - 0.12, 1.35), (-3.6, s * 1.3 + 0.12, 1.55), 'signal_red')


def truck_wheels(p, coll):
	"""Single front wheels and dual rear wheels."""
	for s in (1, -1):
		road_wheel(p + f'front{s}', coll, FRONT_AXLE, WHEEL_R, s, 1.5, width=0.42)
		road_wheel(p + f'rear_out{s}', coll, REAR_AXLE, WHEEL_R, s, 1.5, width=0.4)
		road_wheel(p + f'rear_in{s}', coll, REAR_AXLE, WHEEL_R, s, 1.06, width=0.38, inner=True)
