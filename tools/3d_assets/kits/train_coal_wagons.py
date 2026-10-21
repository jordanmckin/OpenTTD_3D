"""Coal trucks: engine 29 (rail, diamond bogies in company colour) and engine 59 (monorail, shared by maglev 91:
the same body on a skirted base with a hazard stripe). Run in Blender with the member's .blend open, after
vehicle_kit.py has been executed in the same namespace, with KEY set to 'train_029' or 'train_059'."""
import bpy

sync_palette()
RAIL = KEY == 'train_029'
BODY_X, BODY_W, BODY_Z0, BODY_Z1 = 3.3, 1.55, 2.0, 4.3


def build(state):
	coll = bpy.data.collections[state]
	clear(coll)
	p = state + '_'
	open_wagon(p + 'body', coll, -BODY_X, BODY_X, BODY_W, BODY_Z0, BODY_Z1, 'wagon_grey', ribs=6, floor_mat='concrete_dark')
	for s in (1, -1):
		# Side door (centre drop door) with hinges and a lever, and the number panel.
		y = s * (BODY_W + 0.075)
		box(p + f'door{s}', coll, (-0.75, min(y, y + s * 0.03), BODY_Z0 + 0.35), (0.75, max(y, y + s * 0.03), BODY_Z1 - 0.3), 'wagon_grey')
		for z in (BODY_Z0 + 0.6, BODY_Z1 - 0.6):
			box(p + f'hinge{s}{z}', coll, (-0.7, min(y, y + s * 0.06), z - 0.05), (0.7, max(y, y + s * 0.06), z + 0.05), 'black')
		box(p + f'panel{s}', coll, (-2.55, min(y, y + s * 0.03), BODY_Z0 + 0.3), (-1.75, max(y, y + s * 0.03), BODY_Z0 + 0.8), 'black')
		box(p + f'panel_text{s}', coll, (-2.45, min(y, y + s * 0.04), BODY_Z0 + 0.5), (-1.85, max(y, y + s * 0.04), BODY_Z0 + 0.6), 'plaster_white')
	if state == 'loaded':
		bulk_load(p + 'coal', coll, -BODY_X + 0.12, BODY_X - 0.12, BODY_W - 0.12, BODY_Z1 - 0.3, 1.05, 'coal', nx=12, ny=6, seed=29)

	if RAIL:
		rail_underframe(p, coll, BODY_Z0)
	else:
		mono_base(p, coll, BODY_Z0)
	return triangles(coll)


result = {state: build(state) for state in ('empty', 'loaded')}
