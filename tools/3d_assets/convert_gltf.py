"""Convert Phase 8 glTF exports into the embedded runtime table (standard library only).

Usage: python tools/3d_assets/convert_gltf.py [--check]

Reads OpenTTD-15.3/OpenTTD-15.3/assets/3d/export/<key>/<state>.glb for every inventory
entry, validates them against CONVENTIONS.md, and writes src/video/asset3d_art.h.
Inventory statuses advance: not_started -> modelled when an export exists,
approved -> in_game once converted. --check validates without writing anything.
"""
import json
import math
import struct
import sys
from pathlib import Path
from lod import reduce_faces

ROOT = Path(__file__).resolve().parents[2] / 'OpenTTD-15.3' / 'OpenTTD-15.3'
ASSETS = ROOT / 'assets' / '3d'
EXPORT = ASSETS / 'export'
INVENTORY = ASSETS / 'inventory.json'
OUT = ROOT / 'src' / 'video' / 'asset3d_art.h'
LOD_OUT = ROOT / 'src' / 'video' / 'asset3d_lod.h'

STAGES = {'construction_0': 0, 'construction_1': 1, 'construction_2': 2, 'complete': 3}
VEHICLE_STATES = {'default': 0, 'empty': 0, 'loaded': 1}
# Base industry tile graphics that are animation frames of another graphic and draw its model.
INDUSTRY_GFX_ALIAS = {1: 0, 30: 29, 31: 29, 32: 29}  # coal mine headframe and oil well pump while they animate
TREE_STATES = {'growth_0': 0, 'growth_1': 1, 'growth_2': 2, 'grown': 3, 'dying_0': 4, 'dying_1': 5, 'dead': 6}
FURNITURE_STATES = {'red': 0, 'green': 1, 'open': 0, 'closed': 1}
# Rail furniture identities: signals are variant * 8 + SignalType (SIG_ELECTRIC/SIG_SEMAPHORE; block, entry, exit, combo, path, path_oneway).
SIGNAL_TYPES = ('block', 'entry', 'exit', 'combo', 'path', 'path_oneway')
FURNITURE_CROSSING = 16
# Catenary pieces (pylon at the straight or diagonal position, a wire span with pylons at both ends or the near end only).
FURNITURE_CATENARY = 17
CATENARY_STATES = {'pylon': 0, 'pylon_diagonal': 1, 'wire_both': 2, 'wire_half': 3}
# Map objects: ObjectType for the original objects; the company HQ is OBJECT_HQ (4) plus its size.
OBJECT_IDS = {'transmitter': 0, 'lighthouse': 1, 'statue': 2, 'owned_land': 3,
	'hq_tiny': 4, 'hq_small': 5, 'hq_medium': 6, 'hq_large': 7, 'hq_huge': 8}
# Landscape props: field fences use their fence type (1-6, as GetFence); rocks follow.
LANDSCAPE_ROCKS = 16
# Stations, stops, depots and the canal lock, one tile each. Models are authored in a canonical turn (track or road
# along local X; entrances, exits and the dock's water side towards local +Y; the lock rising towards +Y) and turned
# by the renderer. Multi-tile pieces are split per tile: dock land/water, ship depot north/south (DepotPart) and
# lock middle/lower/upper (LockPart).
STATION_IDS = {'station_rail_platform': 0, 'station_rail_building': 1, 'station_rail_roof_a': 2, 'station_rail_roof_b': 3,
	'waypoint_rail': 4, 'stop_truck_bay': 5, 'stop_truck_drive': 6, 'stop_bus_bay': 7, 'stop_bus_drive': 8, 'waypoint_road': 9,
	'dock': 10, 'buoy': 11, 'depot_rail': 12, 'depot_road': 13, 'depot_ship': 14, 'lock': 15}
STATION_STATES = {'default': 0, 'land': 0, 'water': 1, 'north': 0, 'south': 1, 'middle': 0, 'lower': 1, 'upper': 2}
# Bridges: one identity per original BridgeType. Middle pieces use CalcBridgePiece's BridgePieces order; `middle` stands
# for every piece without its own state, and `pillar` for those pieces' pillar segment (state 8 + piece).
BRIDGE_PIECES = ('north', 'south', 'inner_north', 'inner_south', 'middle_odd', 'middle_even')
BRIDGE_RAMP, BRIDGE_RAMP_FLAT, BRIDGE_PILLAR = 6, 7, 8
TUNNEL_IDS = {'tunnel_rail': 0, 'tunnel_road': 1}
# Effect vehicles by sprite sequence (Phase 8.7); Art3D::Effect ids, mirrored by Effect3D in rail3d_impl.h.
EFFECT_IDS = {'effect_chimney_smoke': 0, 'effect_steam_smoke': 1, 'effect_diesel_smoke': 2, 'effect_electric_spark': 3,
	'effect_smoke': 4, 'effect_explosion_large': 5, 'effect_breakdown_smoke': 6, 'effect_explosion_small': 7, 'effect_bulldozer': 8}
CC = {'cc1': -1.0, 'cc2': -2.0}
# Glowing materials (flames, sparks): the renderer draws them unlit. Written as colour + EMISSIVE_OFFSET.
EMISSIVE = ('flame_yellow', 'flame_orange', 'flame_red', 'spark_blue')
EMISSIVE_OFFSET = 2.0
TOLERANCE = 0.51


# ---------------------------------------------------------------------------
# glTF

COMPONENT = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}
WIDTH = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
NORMALISE = {5121: 255.0, 5123: 65535.0, 5120: 127.0, 5122: 32767.0}


def read_glb(path):
	data = path.read_bytes()
	magic, version, _ = struct.unpack_from('<4sII', data, 0)
	if magic != b'glTF' or version != 2:
		raise ValueError(f'{path}: not a glTF 2 binary')
	offset, doc, binary = 12, None, b''
	while offset < len(data):
		length, kind = struct.unpack_from('<II', data, offset)
		chunk = data[offset + 8:offset + 8 + length]
		if kind == 0x4E4F534A:
			doc = json.loads(chunk)
		elif kind == 0x004E4942:
			binary = chunk
		offset += 8 + length
	return doc, binary


def accessor(doc, binary, index):
	acc = doc['accessors'][index]
	view = doc['bufferViews'][acc['bufferView']]
	fmt = COMPONENT[acc['componentType']]
	width = WIDTH[acc['type']]
	size = struct.calcsize(fmt)
	stride = view.get('byteStride') or size * width
	base = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
	out = []
	for i in range(acc['count']):
		vals = struct.unpack_from('<' + fmt * width, binary, base + i * stride)
		if acc.get('normalized') and acc['componentType'] in NORMALISE:
			vals = tuple(v / NORMALISE[acc['componentType']] for v in vals)
		out.append(vals if width > 1 else vals[0])
	return out


def mat_mul(a, b):
	return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def node_matrix(node):
	if 'matrix' in node:
		m = node['matrix']
		return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
	tx, ty, tz = node.get('translation', (0, 0, 0))
	qx, qy, qz, qw = node.get('rotation', (0, 0, 0, 1))
	sx, sy, sz = node.get('scale', (1, 1, 1))
	r = [[1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
		[2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
		[2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)]]
	return [[r[0][0] * sx, r[0][1] * sy, r[0][2] * sz, tx], [r[1][0] * sx, r[1][1] * sy, r[1][2] * sz, ty],
		[r[2][0] * sx, r[2][1] * sy, r[2][2] * sz, tz], [0, 0, 0, 1]]


def transform(m, p):
	return tuple(m[i][0] * p[0] + m[i][1] * p[1] + m[i][2] * p[2] + m[i][3] for i in range(3))


def linear_to_srgb(c):
	c = max(0.0, min(1.0, c))
	return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def load_objects(path):
	"""Return [(object name, [(p0, p1, p2, colour)])] in world space; colour is sRGB or a cc sentinel."""
	doc, binary = read_glb(path)
	materials = doc.get('materials', [])
	objects, errors = [], []

	def visit(index, parent):
		node = doc['nodes'][index]
		m = mat_mul(parent, node_matrix(node))
		if 'mesh' in node:
			faces = []
			for prim in doc['meshes'][node['mesh']]['primitives']:
				if prim.get('mode', 4) != 4:
					errors.append(f'{path.name}: {node.get("name")} has non-triangle primitives')
					continue
				pos = [transform(m, p) for p in accessor(doc, binary, prim['attributes']['POSITION'])]
				idx = accessor(doc, binary, prim['indices']) if 'indices' in prim else list(range(len(pos)))
				vcol = accessor(doc, binary, prim['attributes']['COLOR_0']) if 'COLOR_0' in prim['attributes'] else None
				if 'material' not in prim:
					errors.append(f'{path.name}: {node.get("name")} has faces without a material')
					continue
				mat = materials[prim['material']]
				name = mat.get('name', '')
				base = mat.get('pbrMetallicRoughness', {}).get('baseColorFactor', [1, 1, 1, 1])
				for t in range(0, len(idx) - 2, 3):
					a, b, c = idx[t:t + 3]
					if name in CC:
						colour = (CC[name],) * 3
					else:
						lin = list(base[:3])
						if vcol:
							lin = [base[k] * (vcol[a][k] + vcol[b][k] + vcol[c][k]) / 3 for k in range(3)]
						colour = tuple(linear_to_srgb(v) + (EMISSIVE_OFFSET if name in EMISSIVE else 0) for v in lin)
					u = [pos[b][k] - pos[a][k] for k in range(3)]
					v = [pos[c][k] - pos[a][k] for k in range(3)]
					n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
					if math.sqrt(sum(x * x for x in n)) < 1e-4:
						continue  # degenerate; the renderer would drop it anyway
					faces.append((pos[a], pos[b], pos[c], colour))
			objects.append((node.get('name', f'node{index}'), faces))
		for child in node.get('children', []):
			visit(child, m)

	identity = [[1 if i == j else 0 for j in range(4)] for i in range(4)]
	scene = doc['scenes'][doc.get('scene', 0)]
	for n in scene['nodes']:
		visit(n, identity)
	return objects, errors


# ---------------------------------------------------------------------------
# Conversion

def bounds(faces):
	pts = [p for f in faces for p in f[:3]]
	return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def check_bounds(key, state, faces, lo_ok, hi_ok, problems):
	if not faces:
		return
	lo, hi = bounds(faces)
	for i, axis in enumerate('xyz'):
		if lo_ok[i] is not None and lo[i] < lo_ok[i] - TOLERANCE:
			problems.append(f'{key}/{state}: {axis} min {lo[i]:.2f} is outside {lo_ok[i]}')
		if hi_ok[i] is not None and hi[i] > hi_ok[i] + TOLERANCE:
			problems.append(f'{key}/{state}: {axis} max {hi[i]:.2f} is outside {hi_ok[i]}')


def budget(entry):
	cat = entry['category']
	if entry['key'] == 'crossing_rail_road':
		return 600  # a whole tile, like buildings
	if cat in ('house', 'object', 'station', 'depot', 'water'):
		w, h = (int(v) for v in entry.get('footprint', '1x1').split('x'))
		return 600 * w * h
	if cat == 'vehicle':
		return 2500 if entry.get('type') == 'wagon' else 4000  # Phase 8.5: the user asked for the most detail on vehicles
	return {'industry': 600, 'vehicle': 600, 'tree': 200, 'rail_furniture': 300, 'landscape': 300}.get(cat, 600)


def convert(entry, exports, problems):
	"""Return [(table, id, state, faces)] for one inventory entry."""
	key, cat = entry['key'], entry['category']
	out = []
	limit = budget(entry)
	for state_file in sorted(exports.glob('*.glb')):
		state = state_file.stem
		objects, errors = load_objects(state_file)
		problems.extend(f'{key}: {e}' for e in errors)
		layout_index = 0
		if '@layout' in state:
			state, layout = state.split('@layout')
			layout_index = int(layout)
		if key.startswith('airport_'):
			# Airports: one model per base airport tile graphic, cut from the assembled layout like industries.
			# `default` is animation frame 0, `frame_<n>` holds the animated tiles at frame n.
			if state != 'default' and not (state.startswith('frame_') and state[6:].isdigit()):
				problems.append(f'{key}: unknown state {state}')
				continue
			frame = 0 if state == 'default' else int(state[6:])
			layout = entry['layout']
			source, pieces = {}, {}
			for x, y, g in layout:
				source.setdefault(g, (x, y))
			for name, faces in objects:
				if not faces:
					continue
				lo, hi = bounds(faces)
				tx, ty = int(((lo[0] + hi[0]) / 2) // 16), int(((lo[1] + hi[1]) / 2) // 16)
				gfx = next((g for x, y, g in layout if (x, y) == (tx, ty)), None)
				if gfx is None:
					problems.append(f'{key}/{state}: object {name} centre is on tile ({tx},{ty}), outside the layout')
					continue
				if source[gfx] != (tx, ty):
					continue
				pieces.setdefault(gfx, []).extend(tuple((p[0] - 16 * tx, p[1] - 16 * ty, p[2]) for p in f[:3]) + (f[3],) for f in faces)
			for gfx, faces in pieces.items():
				check_bounds(key, f'{state} gfx {gfx}', faces, (0, 0, 0), (16, 16, None), problems)
				if len(faces) > limit:
					problems.append(f'{key}/{state}: gfx {gfx} has {len(faces)} triangles (budget {limit})')
				out.append(('airport_tiles', gfx, frame, faces))
			continue
		if cat == 'industry':
			# Moving parts (part_<n>) are cut per tile like the stages and drawn over the static tile.
			part = int(state[5:]) if state.startswith('part_') and state[5:].isdigit() else None
			if state not in STAGES and part is None:
				problems.append(f'{key}: unknown state {state}')
				continue
			layout = entry['layouts'][layout_index] if layout_index < len(entry['layouts']) else []
			pieces = {}
			source = {}  # gfx -> first tile showing it; repeated gfx in a layout are copies
			for x, y, g in layout:
				source.setdefault(g, (x, y))
			for name, faces in objects:
				if not faces:
					continue
				lo, hi = bounds(faces)
				tx, ty = int(((lo[0] + hi[0]) / 2) // 16), int(((lo[1] + hi[1]) / 2) // 16)
				gfx = next((g for x, y, g in layout if (x, y) == (tx, ty)), None)
				if gfx is None:
					problems.append(f'{key}/{state}: object {name} centre is on tile ({tx},{ty}), not in layout {layout_index}')
					continue
				if source[gfx] != (tx, ty):
					continue
				moved = [tuple((p[0] - 16 * tx, p[1] - 16 * ty, p[2]) for p in f[:3]) + (f[3],) for f in faces]
				pieces.setdefault(gfx, []).extend(moved)
			for gfx, faces in pieces.items():
				check_bounds(key, f'{state} gfx {gfx}', faces, (0, 0, 0), (16, 16, None), problems)
				if len(faces) > limit:
					problems.append(f'{key}/{state}: gfx {gfx} has {len(faces)} triangles (budget {limit})')
				table, st = ('industry_tiles', STAGES[state]) if part is None else ('industry_parts', part)
				out.append((table, gfx, st, faces))
				out.extend((table, alias, st, faces) for alias, base in INDUSTRY_GFX_ALIAS.items() if base == gfx)
			continue

		faces = [f for _, fs in objects for f in fs]
		if not faces:
			continue
		if len(faces) > limit:
			problems.append(f'{key}/{state}: {len(faces)} triangles (budget {limit})')
		if cat == 'house':
			if state not in STAGES:
				problems.append(f'{key}: unknown state {state}')
				continue
			w, h = (int(v) for v in entry['footprint'].split('x'))
			check_bounds(key, state, faces, (0, 0, 0), (16 * w, 16 * h, None), problems)
			out.append(('houses', entry['house_id'], STAGES[state], faces))
		elif cat == 'vehicle':
			if state not in VEHICLE_STATES:
				problems.append(f'{key}: unknown state {state}')
				continue
			kind = key.split('_')[0]
			if kind in ('train', 'road'):
				check_bounds(key, state, faces, (-4.5, -2.5, 0), (4.5, 2.5, None), problems)
			out.append(('engines', entry['engine_id'], VEHICLE_STATES[state], faces))
		elif cat == 'tree':
			if state not in TREE_STATES:
				problems.append(f'{key}: unknown state {state}')
				continue
			if 'variant_of' in entry:
				problems.append(f'{key}: snowy tree variants are not drawn yet; export skipped')
				continue
			out.append(('trees', entry['tree_type'], TREE_STATES[state], faces))
		elif cat == 'rail_furniture' and (key.startswith('signal_') or key == 'crossing_rail_road'):
			if state not in FURNITURE_STATES:
				problems.append(f'{key}: unknown state {state}')
				continue
			if key == 'crossing_rail_road':
				ident = FURNITURE_CROSSING
				check_bounds(key, state, faces, (0, 0, 0), (16, 16, None), problems)
			else:
				variant, kind = key[len('signal_'):].split('_', 1)
				ident = (variant == 'semaphore') * 8 + SIGNAL_TYPES.index(kind)
				check_bounds(key, state, faces, (-4, -4, 0), (4, 4, None), problems)  # the track centre is 4.2 away
			out.append(('furniture', ident, FURNITURE_STATES[state], faces))
		elif key == 'catenary_rail':
			if state not in CATENARY_STATES:
				problems.append(f'{key}: unknown state {state}')
				continue
			if state.startswith('pylon'):
				check_bounds(key, state, faces, (-1, -1, 0), (5, 1, None), problems)  # the cantilever reaches +X over the track
			else:
				check_bounds(key, state, faces, (0, -0.5, 0), (16, 0.5, None), problems)
			out.append(('furniture', FURNITURE_CATENARY, CATENARY_STATES[state], faces))
		elif cat == 'object':
			if state != 'default':
				problems.append(f'{key}: unknown state {state}')
				continue
			w, h = (int(v) for v in entry.get('footprint', '1x1').split('x'))
			check_bounds(key, state, faces, (0, 0, 0), (16 * w, 16 * h, None), problems)
			out.append(('objects', OBJECT_IDS[key[len('object_'):]], 0, faces))
		elif cat == 'landscape':
			if state != 'default':
				problems.append(f'{key}: unknown state {state}')
				continue
			if key.startswith('fence_'):
				# One edge: along local X on the tile's y = 0 side, inside the tile; the renderer turns it for each side.
				check_bounds(key, state, faces, (0, 0, 0), (16, 3, None), problems)
				ident = int(key[len('fence_'):])
			else:
				check_bounds(key, state, faces, (0, 0, 0), (16, 16, None), problems)
				ident = LANDSCAPE_ROCKS
			out.append(('landscape', ident, 0, faces))
		elif cat == 'bridge':
			# Middle pieces and ramps stay inside the tile across; pillar segments are 8 high below their top.
			names = {f.stem for f in exports.glob('*.glb')}
			generic = tuple(i for i, n in enumerate(BRIDGE_PIECES) if n not in names)
			if state in BRIDGE_PIECES or state == 'middle':
				states = (BRIDGE_PIECES.index(state),) if state != 'middle' else generic
				check_bounds(key, state, faces, (0, 0, None), (16, 16, None), problems)
			elif state in ('ramp', 'ramp_flat'):
				states = (BRIDGE_RAMP if state == 'ramp' else BRIDGE_RAMP_FLAT,)
				check_bounds(key, state, faces, (0, 0, -0.5), (16, 16, None), problems)
			elif state == 'pillar' or (state.startswith('pillar_') and state[7:] in BRIDGE_PIECES):
				states = tuple(BRIDGE_PILLAR + i for i in (generic if state == 'pillar' else (BRIDGE_PIECES.index(state[7:]),)))
				check_bounds(key, state, faces, (0, 0, -8), (16, 16, 0), problems)
			else:
				problems.append(f'{key}: unknown state {state}')
				continue
			out.append(('bridges', int(key[len('bridge_'):]), states, faces))
		elif cat == 'tunnel':
			if state != 'default':
				problems.append(f'{key}: unknown state {state}')
				continue
			check_bounds(key, state, faces, (0, 0, 0), (16, 16, None), problems)
			out.append(('tunnels', TUNNEL_IDS[key], 0, faces))
		elif cat == 'effect':
			frame = 0 if state == 'default' else int(state[6:]) if state.startswith('frame_') and state[6:].isdigit() else None
			if frame is None or key not in EFFECT_IDS:
				problems.append(f'{key}: unknown state {state}')
				continue
			check_bounds(key, state, faces, (-24, -16, -8), (16, 16, 40), problems)  # plumes lean towards -X
			out.append(('effects', EFFECT_IDS[key], frame, faces))
		elif key in STATION_IDS:
			if state not in STATION_STATES:
				problems.append(f'{key}: unknown state {state}')
				continue
			check_bounds(key, state, faces, (0, 0, None), (16, 16, None), problems)
			out.append(('stations', STATION_IDS[key], STATION_STATES[state], faces))
		else:
			problems.append(f'{key}: category {cat} has no runtime hook yet; export kept, not converted')
	return out


def fmt(v):
	# Round before choosing the form: 12.99999 must become '13.f', not the invalid literal '13f'.
	text = f'{v:.4f}'.rstrip('0')
	return text + 'f' if text != '-0.' else '0.f'


def write_header(models, tables):
	lines = [
		'/* Generated by tools/3d_assets/convert_gltf.py from assets/3d/export; GPL-2.0-only. Do not edit. */',
		'/** @file asset3d_art.h Phase 8 Blender models and their game identity lookups. */',
		'#ifndef ASSET3D_ART_H',
		'#define ASSET3D_ART_H',
		'#include "asset3d_generated.h"',
		'namespace Art3D {',
		'using Asset3D::Face;',
		'using Asset3D::Model;',
		'/** Faces whose colour is negative use company colour 1 (-1) or 2 (-2); colours above 1.5 glow: drawn unlit, less 2. */',
		'struct Entry { uint16_t id; uint8_t state; uint16_t model; };',
	]
	for name, faces in models:
		lines.append(f'inline constexpr Face {name}[] = {{')
		for a, b, c, col in faces:
			pts = ','.join('{' + ','.join(fmt(v) for v in p) + '}' for p in (a, b, c))
			lines.append('{{' + pts + '},{' + ','.join(fmt(v) for v in col) + '}},')
		lines.append('};')
	if models:
		lines.append('inline constexpr Model models[] = {' + ','.join(f'{{{n}, std::size({n})}}' for n, _ in models) + '};')
	else:
		lines.append('inline constexpr Face none[] = {{{{0.f,0.f,0.f},{0.f,0.f,0.f},{0.f,0.f,0.f}},{0.f,0.f,0.f}}};')
		lines.append('inline constexpr Model models[] = {{none, 0}};')
	for table in ('houses', 'industry_tiles', 'industry_parts', 'effects', 'engines', 'trees', 'furniture', 'objects', 'landscape', 'stations', 'airport_tiles',
			'bridges', 'tunnels'):
		rows = sorted(tables.get(table, []))
		body = ','.join(f'{{{i},{s},{m}}}' for i, s, m in rows) or '{0xFFFF,0xFF,0}'
		lines.append(f'inline constexpr Entry {table}[] = {{{body}}};')
	lines += [
		'/** Model index for an identity and state, or -1 when it has no Phase 8 model yet. */',
		'template <size_t N> constexpr int Find(const Entry (&table)[N], unsigned id, unsigned state)',
		'{',
		'\tfor (const Entry &e : table) if (e.id == id && e.state == state) return e.model;',
		'\treturn -1;',
		'}',
		'/** Whether any state of this identity has a Phase 8 model. */',
		'template <size_t N> constexpr bool Has(const Entry (&table)[N], unsigned id)',
		'{',
		'\tfor (const Entry &e : table) if (e.id == id) return true;',
		'\treturn false;',
		'}',
		'constexpr int House(unsigned house, unsigned stage) { return Find(houses, house, stage); }',
		'constexpr bool HasHouse(unsigned house) { return Has(houses, house); }',
		'constexpr int IndustryTile(unsigned gfx, unsigned stage) { return Find(industry_tiles, gfx, stage); }',
		'/** Moving part of a base industry tile graphic at an animation step, drawn over the static tile; -1 if none. */',
		'constexpr int IndustryPart(unsigned gfx, unsigned step) { return Find(industry_parts, gfx, step); }',
		'/** Animation steps of the moving part of a base industry tile graphic (0 when it has none). */',
		'constexpr unsigned IndustryPartSteps(unsigned gfx) { unsigned n = 0; while (Find(industry_parts, gfx, n) >= 0) ++n; return n; }',
		'/** Effect vehicle model by sprite sequence (EFFECT_IDS in the converter) and frame; -1 if none. */',
		'constexpr int Effect(unsigned id, unsigned frame) { return Find(effects, id, frame); }',
		'/** Loaded falls back to the empty/default model. */',
		'constexpr int Engine(unsigned engine, bool loaded) { int m = loaded ? Find(engines, engine, 1) : -1; return m >= 0 ? m : Find(engines, engine, 0); }',
		'constexpr int Tree(unsigned type, unsigned growth) { return Find(trees, type, growth); }',
		'/** Signal by variant (0 electric, 1 semaphore), SignalType and aspect; no fallback between aspects. */',
		'constexpr int Signal(unsigned variant, unsigned type, bool green) { return Find(furniture, variant * 8 + type, green ? 1 : 0); }',
		f'constexpr int Crossing(bool closed) {{ return Find(furniture, {FURNITURE_CROSSING}, closed ? 1 : 0); }}',
		'/** Catenary piece: 0 pylon, 1 pylon at a diagonal position, 2 wire with pylons at both ends, 3 wire with a pylon at its start. */',
		f'constexpr int Catenary(unsigned piece) {{ return Find(furniture, {FURNITURE_CATENARY}, piece); }}',
		'/** Original map object by ObjectType; the company HQ is OBJECT_HQ plus its size. */',
		'constexpr int Object(unsigned id) { return Find(objects, id, 0); }',
		'/** Field fence by type (1-6), one tile edge. */',
		'constexpr int Fence(unsigned type) { return Find(landscape, type, 0); }',
		f'constexpr int Rocks() {{ return Find(landscape, {LANDSCAPE_ROCKS}, 0); }}',
		'/** Station, stop, depot or lock tile piece by identity (see STATION_IDS in the converter) and part. */',
		'constexpr int Station(unsigned id, unsigned part = 0) { return Find(stations, id, part); }',
		'/** Base airport tile graphic (AirportTiles) at an animation frame; frames without a model show frame 0. */',
		'constexpr int AirportTile(unsigned gfx, unsigned frame) { int m = frame ? Find(airport_tiles, gfx, frame) : -1; return m >= 0 ? m : Find(airport_tiles, gfx, 0); }',
		'/** Whether airports have Phase 8 models; base tiles without one (plain apron, plain grass) then draw only their ground. */',
		'constexpr bool HasAirportTiles() { return airport_tiles[0].id != 0xFFFF; }',
		'/** Original bridge type: middle piece (BridgePieces), its pillar segment (none for pieces drawn without), or ramp. */',
		'constexpr int BridgePiece(unsigned type, unsigned piece) { return Find(bridges, type, piece); }',
		f'constexpr int BridgePillar(unsigned type, unsigned piece) {{ return Find(bridges, type, {BRIDGE_PILLAR} + piece); }}',
		f'constexpr int BridgeRamp(unsigned type, bool sloped) {{ return Find(bridges, type, sloped ? {BRIDGE_RAMP} : {BRIDGE_RAMP_FLAT}); }}',
		'/** Tunnel portal: 0 rail, 1 road. */',
		'constexpr int Tunnel(unsigned id) { return Find(tunnels, id, 0); }',
		'}',
		'#endif',
		'',
	]
	return '\n'.join(lines)


def write_lod_header(models, entries, originals):
	lines = ['/* Generated by tools/3d_assets/convert_gltf.py; GPL-2.0-only. Do not edit. */',
		'#ifndef ASSET3D_LOD_H', '#define ASSET3D_LOD_H', '#include "asset3d_generated.h"',
		'namespace ArtLOD3D {', 'using Asset3D::Face;', 'using Asset3D::Model;']
	for name, faces in models:
		lines.append(f'inline constexpr Face {name}[] = {{')
		for a, b, c, col in faces:
			pts = ','.join('{' + ','.join(fmt(v) for v in p) + '}' for p in (a, b, c))
			lines.append('{{' + pts + '},{' + ','.join(fmt(v) for v in col) + '}},')
		lines.append('};')
	lines.append('inline constexpr Model models[] = {' + ','.join(f'{{{n}, std::size({n})}}' for n, _ in models) + '};' if models else
		'inline constexpr Model models[] = {{nullptr, 0}};')
	lines += ['struct Entry { uint16_t model; float error; };',
		'struct Levels { Entry level[2]; float radius, height; };', 'inline constexpr Levels levels[] = {']
	for original, (_, faces) in enumerate(originals):
		levels = {l: (i, e) for m, l, i, e in entries if m == original}
		body = ','.join(f'{{{levels[l][0]},{fmt(levels[l][1])}}}' if l in levels else '{0xFFFF,0.f}' for l in (1, 2))
		lo, hi = bounds(faces)
		radius = max(math.hypot(p[0], p[1]) for f in faces for p in f[:3]) + 0.0002
		lines.append('{{' + body + '},' + fmt(radius) + ',' + fmt(hi[2] - lo[2] + 0.0002) + '},')
	lines += ['};', '}', '#endif', '']
	return '\n'.join(lines)


def main():
	check = '--check' in sys.argv
	inv = json.loads(INVENTORY.read_text(encoding='utf-8'))
	entries = {e['key']: e for e in inv['entries']}
	problems, models, tables, converted = [], [], {}, []
	lod_models, lod_entries, lod_report = [], [], []
	for key, entry in entries.items():
		folder = EXPORT / key
		if not folder.is_dir() or not any(folder.glob('*.glb')):
			continue
		results = convert(entry, folder, problems)
		for table, ident, state, faces in results:
			if table == 'airport_tiles' and any(i == ident and st == state for i, st, _ in tables.get(table, [])):
				continue  # a tile graphic shared by several airports comes from the first one in inventory order
			# One model can serve several states (a bridge's `middle` covers each piece without its own).
			states = state if isinstance(state, tuple) else (state,)
			index = len(models)
			models.append((f'{key}_{table}_{ident}_{states[0]}', faces))
			if table in ('engines', 'effects', 'industry_parts'):
				previous_count = len(faces)
				for level, cell in enumerate((0.4, 0.8), 1):
					reduced, error = reduce_faces(faces, cell)
					if len(reduced) >= previous_count * 0.9:
						continue
					previous_count = len(reduced)
					lod_entries.append((index, level, len(lod_models), error + 0.0002))
					lod_models.append((f'{models[-1][0]}_lod{level}', reduced))
					lod_report.append(dict(key=key, model=index, level=level, full=len(faces), reduced=len(reduced), error=error + 0.0002))
			tables.setdefault(table, []).extend((ident, st, index) for st in states)
			if table == 'engines':
				# Engines sharing this base sprite share the model.
				for other in entries.values():
					if other.get('shared_with') == key and other.get('status') == 'shared':
						tables[table].append((other['engine_id'], state, index))
		if results:
			converted.append(key)
			if entry['status'] == 'not_started':
				entry['status'] = 'modelled'
			elif entry['status'] == 'approved':
				entry['status'] = 'in_game'
	for p in problems:
		print('WARNING' if 'no runtime hook' in p or 'not drawn yet' in p else 'ERROR', p)
	errors = [p for p in problems if 'no runtime hook' not in p and 'not drawn yet' not in p]
	print(f'{len(converted)} identities, {len(models)} models, {sum(len(f) for _, f in models)} triangles')
	print(f'LOD: {len(lod_models)} reduced models; {sum(r["full"] for r in lod_report)} -> {sum(r["reduced"] for r in lod_report)} triangles')
	if check:
		if not errors:
			for path, text in ((OUT, write_header(models, tables)), (LOD_OUT, write_lod_header(lod_models, lod_entries, models)),
					(ASSETS / 'lod-report.json', json.dumps(lod_report, indent='\t') + '\n')):
				if not path.exists() or path.read_text(encoding='utf-8') != text:
					print(f'ERROR stale generated artifact: {path}')
					errors.append(str(path))
		return 1 if errors else 0
	if errors:
		print('Not writing the runtime table until the errors above are fixed.')
		return 1
	text = write_header(models, tables)
	if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
		with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
			f.write(text)
		print(f'wrote {OUT}')
	lod_text = write_lod_header(lod_models, lod_entries, models)
	if not LOD_OUT.exists() or LOD_OUT.read_text(encoding='utf-8') != lod_text:
		with open(LOD_OUT, 'w', encoding='utf-8', newline='\n') as f:
			f.write(lod_text)
		print(f'wrote {LOD_OUT}')
	(ASSETS / 'lod-report.json').write_text(json.dumps(lod_report, indent='\t') + '\n', encoding='utf-8')
	INVENTORY.write_text(json.dumps(inv, indent='\t') + '\n', encoding='utf-8')
	return 0


if __name__ == '__main__':
	sys.exit(main())
