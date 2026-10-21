"""Build Phase 8 reference images and the art inventory from the game tables.

Usage: python tools/3d_assets/build_references.py [--sprites sprites_pulled/sliced]

Reads the base-game drawing tables in OpenTTD-15.3/OpenTTD-15.3/src/table, looks
up each identity's sprites in the sliced OpenGFX export (slice_sprites.py),
composites multi-sprite and multi-tile objects the way the classic viewport
places them, and writes:

  OpenTTD-15.3/OpenTTD-15.3/assets/3d/reference/<climate>/<key>_<label>.png  (4x, transparent)
  OpenTTD-15.3/OpenTTD-15.3/assets/3d/inventory.json                        (tracking sheet)

Re-running keeps the status, approach and notes of existing inventory entries.
Reference images are authoring material only and never shipped with the game.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'OpenTTD-15.3' / 'OpenTTD-15.3' / 'src'
TABLE = SRC / 'table'
ASSETS = ROOT / 'OpenTTD-15.3' / 'OpenTTD-15.3' / 'assets' / '3d'
OUT_REF = ASSETS / 'reference'
OUT_INV = ASSETS / 'inventory.json'

CLIMATES = ('temperate', 'arctic', 'tropic', 'toyland')
CLIMATE_GRF = {'arctic': 'ogfxc_arctic', 'tropic': 'ogfxh_tropical', 'toyland': 'ogfxt_toyland'}
SCALE = 4
SPRITE_MASK = (1 << 24) - 1
RECOLOUR_FLAG = 1 << 30
COMPANY_RECOLOUR = 775  # PALETTE_RECOLOUR_START, company colour dark blue
TRANSPARENT_FLAG = 1 << 31
PALETTE_TO_TRANSPARENT = 802
GLASS = 'glass'  # transparent-palette sprites (station roof glass) drawn as a translucent tint


def strip_comments(text):
	text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
	return re.sub(r'//[^\n]*', '', text)


# ---------------------------------------------------------------------------
# Symbols and strings

class Symbols:
	"""Integer constants from the headers, evaluated lazily."""

	ASSIGN = re.compile(r'^\s*(?:static\s+)?(?:const|constexpr)\s+[\w:<>]+\s+(\w+)\s*=\s*([^;]+);', re.M)
	ENUM_ITEM = re.compile(r'^\s*(\w+)\s*=\s*([^,\n/]+),', re.M)

	def __init__(self, files):
		self.raw = {}
		for f in files:
			text = strip_comments(f.read_text(encoding='utf-8', errors='replace'))
			for rx in (self.ASSIGN, self.ENUM_ITEM):
				for name, expr in rx.findall(text):
					self.raw.setdefault(name, expr.strip())
		self.raw.update({'PAL_NONE': '0', 'PALETTE_MODIFIER_COLOUR': '30', 'PALETTE_MODIFIER_TRANSPARENT': '31'})
		self.cache = {}

	def value(self, expr, depth=0):
		expr = expr.strip()
		if depth > 40:
			raise ValueError(expr)
		expr = re.sub(r'\b(?:static_cast|SpriteID|PaletteID|u?int\d*_t|uint)\s*<[^>]*>|\(\s*(?:SpriteID|PaletteID|u?int\d*_t|uint)\s*\)', '', expr)
		expr = re.sub(r'\b(0x[0-9A-Fa-f]+|\d+)[uUlL]+\b', r'\1', expr)

		def sub(m):
			name = m.group(0)
			if name in self.cache:
				return str(self.cache[name])
			if name not in self.raw:
				raise KeyError(name)
			v = self.value(self.raw[name], depth + 1)
			self.cache[name] = v
			return str(v)

		expr = re.sub(r'\b[A-Za-z_]\w*\b', sub, expr)
		return int(eval(expr, {'__builtins__': {}}))

	def get(self, expr):
		try:
			return self.value(expr)
		except (KeyError, ValueError, SyntaxError, TypeError, NameError):
			return None


def load_strings():
	strings = {}
	for line in (SRC / 'lang' / 'english.txt').read_text(encoding='utf-8').splitlines():
		m = re.match(r'^(STR_\w+)\s*:(.*)$', line)
		if m:
			strings[m.group(1)] = re.sub(r'\{[^}]*\}', '', m.group(2)).strip()
	return strings


def slug(text):
	return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def split_args(text):
	"""Split a macro argument list on top-level commas."""
	out, depth, cur = [], 0, ''
	for ch in text:
		if ch in '({[':
			depth += 1
		elif ch in ')}]':
			depth -= 1
		if ch == ',' and depth == 0:
			out.append(cur.strip())
			cur = ''
		else:
			cur += ch
	if cur.strip():
		out.append(cur.strip())
	return out


def macro_calls(text, name):
	"""Yield the argument lists of every NAME(...) call in text."""
	for m in re.finditer(r'\b' + name + r'\s*\(', text):
		i, depth = m.end(), 1
		while depth:
			depth += {'(': 1, ')': -1}.get(text[i], 0)
			i += 1
		yield split_args(text[m.end():i - 1])


def block(text, start_pattern):
	"""Return the brace-enclosed body following start_pattern."""
	m = re.search(start_pattern, text)
	if not m:
		raise ValueError(start_pattern)
	i = text.index('{', m.end() - 1)
	depth, j = 0, i
	while True:
		depth += {'{': 1, '}': -1}.get(text[j], 0)
		j += 1
		if depth == 0:
			return text[i + 1:j - 1]


# ---------------------------------------------------------------------------
# Sprites

def parse_recolours(nfo):
	"""Recolour pseudo-sprites ('* 257') from a grfcodec .nfo, keyed by sprite number."""
	maps, cur, data = {}, None, []

	def finish():
		if cur is not None and len(data) >= 257:
			maps[cur] = data[1:257]

	for line in nfo.read_text(encoding='latin-1').splitlines():
		m = re.match(r'^\s*(\d+)\s+\*\s+(\d+)\s*(.*)$', line)
		if m:
			finish()
			cur, data = (int(m.group(1)), []) if m.group(2) == '257' else (None, [])
			rest = m.group(3)
		elif re.match(r'^\s*(\d+|\|)\s+\S+\.png\s', line):
			finish()
			cur, data = None, []
			continue
		elif cur is not None:
			rest = line
		else:
			continue
		for tok in re.finditer(r'"((?:[^"\\]|\\.)*)"|([0-9A-Fa-f]{2})', rest):
			if tok.group(1) is not None:
				data.extend(ord(c) for c in re.sub(r'\\(.)', r'\1', tok.group(1)))
			else:
				data.append(int(tok.group(2), 16))
	finish()
	return maps


class SpriteStore:
	"""Map game SpriteIDs to sliced images for one climate."""

	def __init__(self, sliced, climate, landscape_tables, extra):
		self.entries = {}
		self.cache = {}
		self.missing = set()
		self._add(sliced / 'ogfx1_base', 0)
		self._add(sliced / 'ogfxi_logos', 4793)
		folder = sliced / 'ogfxe_extra'
		rows = {int(r['sprite']): r for r in self._rows(folder)}
		for sprite_id, number in extra.items():
			if number in rows:
				r = rows[number]
				self.entries[sprite_id] = (folder / r['file'], int(r['xrel']), int(r['yrel']))
		if climate in CLIMATE_GRF:
			ids = [i for a, b in landscape_tables[climate] for i in range(a, b + 1)]
			folder = sliced / CLIMATE_GRF[climate]
			for row in self._rows(folder):
				n = int(row['sprite'])
				if n < len(ids):
					self.entries[ids[n]] = (folder / row['file'], int(row['xrel']), int(row['yrel']))

	@staticmethod
	def _rows(folder):
		with open(folder / 'index.csv', newline='') as f:
			return [r for r in csv.DictReader(f) if r['zoom'] == 'normal']

	def _add(self, folder, base):
		for row in self._rows(folder):
			self.entries[base + int(row['sprite'])] = (folder / row['file'], int(row['xrel']), int(row['yrel']))

	def get(self, sprite, recolour=None):
		"""Return (RGBA image, xrel, yrel) or None."""
		key = (sprite, tuple(recolour) if isinstance(recolour, list) else recolour)
		if key in self.cache:
			return self.cache[key]
		entry = self.entries.get(sprite)
		result = None
		if entry is None:
			self.missing.add(sprite)
		else:
			path, xrel, yrel = entry
			img = Image.open(path)
			if img.mode == 'P' and recolour == GLASS:
				alpha = Image.frombytes('L', img.size, bytes(0 if b == 0 else 110 for b in img.tobytes()))
				img = Image.new('RGBA', img.size, (150, 190, 220, 0))
				img.putalpha(alpha)
			elif img.mode == 'P':
				if recolour:
					img = img.point(lambda i: recolour[i])
				alpha = Image.frombytes('L', img.size, bytes(0 if b == 0 else 255 for b in img.tobytes()))
				img = img.convert('RGBA')
				img.putalpha(alpha)
			else:
				img = img.convert('RGBA')
			result = (img, xrel, yrel)
		self.cache[key] = result
		return result


class Canvas:
	"""Collects sprites at world positions and paints them in viewport order."""

	def __init__(self, store, recolours):
		self.store = store
		self.recolours = recolours
		self.items = []

	def add(self, sprite, pal, x, y, z, layer=1, order=None):
		"""layer 0 = ground, 1 = sortable; x/y/z in world pixels."""
		if not sprite:
			return
		sid = sprite & SPRITE_MASK
		recolour = self.palette(sprite, pal)
		key = (layer, x + y if order is None else order, z, len(self.items))
		self.items.append((key, sid, recolour, (y - x) * 2, y + x - z, None))
		self.parent = (key, sid, (y - x) * 2, y + x - z)

	def palette(self, sprite, pal):
		if (pal & SPRITE_MASK) == PALETTE_TO_TRANSPARENT or sprite & TRANSPARENT_FLAG:
			return GLASS
		if pal:
			return self.recolours.get(pal & SPRITE_MASK)
		if sprite & RECOLOUR_FLAG:
			return self.recolours.get(COMPANY_RECOLOUR)
		return None

	def add_child(self, sprite, pal, dx, dy):
		"""Child sprite: screen offset from the last parent sprite's top-left corner (viewport.cpp), drawn just after it."""
		if not sprite:
			return
		key, parent_sid, sx, sy = self.parent
		self.items.append((key[:3] + (key[3] + 0.5,), sprite & SPRITE_MASK, self.palette(sprite, pal), sx + dx, sy + dy, parent_sid))

	def add_ground_child(self, sprite, pal, x, y, z, dx, dy):
		"""Child before any parent in a tile layout: a ground sprite with a screen offset."""
		if not sprite:
			return
		self.items.append(((0, x + y, z, len(self.items)), sprite & SPRITE_MASK, self.palette(sprite, pal), (y - x) * 2 + dx, y + x - z + dy, None))

	def render(self, pad=2):
		drawn = []
		for key, sid, recolour, sx, sy, parent in sorted(self.items, key=lambda i: i[0]):
			got = self.store.get(sid, recolour)
			if parent is not None:
				p = self.store.get(parent)
				if p:
					sx, sy = sx + p[1], sy + p[2]
			if got:
				img, xrel, yrel = got
				drawn.append((img, sx + xrel, sy + yrel))
		if not drawn:
			return None
		x0 = min(x for _, x, _ in drawn) - pad
		y0 = min(y for _, _, y in drawn) - pad
		x1 = max(x + i.width for i, x, _ in drawn) + pad
		y1 = max(y + i.height for i, _, y in drawn) + pad
		out = Image.new('RGBA', (x1 - x0, y1 - y0))
		for img, x, y in drawn:
			out.alpha_composite(img, (x - x0, y - y0))
		return out


def strip(images, gap=6):
	images = [i for i in images if i is not None]
	if not images:
		return None
	w = sum(i.width for i in images) + gap * (len(images) - 1)
	h = max(i.height for i in images)
	out = Image.new('RGBA', (w, h))
	x = 0
	for i in images:
		out.alpha_composite(i, (x, h - i.height))
		x += i.width + gap
	return out


def save(img, path):
	if img is None:
		return False
	path.parent.mkdir(parents=True, exist_ok=True)
	img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST).save(path)
	return True


# ---------------------------------------------------------------------------
# Table parsers

def parse_landscape_tables():
	text = strip_comments((TABLE / 'landscape_sprite.h').read_text())
	tables = {}
	for climate, name in (('arctic', 'arctic'), ('tropic', 'tropic'), ('toyland', 'toyland')):
		body = block(text, r'_landscape_spriteindexes_' + name + r'\[\]\s*=')
		tables[climate] = [(int(a, 0), int(b, 0)) for a, b in re.findall(r'\{\s*(0x[0-9A-Fa-f]+|\d+)\s*,\s*(0x[0-9A-Fa-f]+|\d+)\s*\}', body)]
	return tables


def parse_draw_buildings(text, array_name, sym):
	"""M(s1, p1, s2, p2, dx, dy, sx, sy, sz, p) rows of a DrawBuildingsTileStruct table."""
	rows = []
	for args in macro_calls(block(text, array_name + r'\s*\[[^\]]*\]\s*='), 'M'):
		s1, p1, s2, p2, dx, dy = (sym.get(a) or 0 for a in args[:6])
		rows.append({'ground': (s1, p1), 'building': (s2, p2), 'dx': dx, 'dy': dy})
	return rows


HOUSE_CLIMATES = {
	'ClimateTemperate': 'temperate', 'ClimateSubarcticBelowSnow': 'arctic', 'ClimateSubarcticAboveSnow': 'arctic',
	'ClimateSubtropic': 'tropic', 'ClimateToyland': 'toyland',
}


def parse_houses(sym, strings):
	text = strip_comments((TABLE / 'town_land.h').read_text())
	draw = parse_draw_buildings(text, '_town_draw_tile_data', sym)
	specs = list(macro_calls(block(text, r'_original_house_specs\[\]\s*='), 'MS'))
	houses = []
	for hid, args in enumerate(specs):
		flags, zones = args[10], args[11]
		size = next((s for s in ('Size2x2', 'Size2x1', 'Size1x2', 'Size1x1') if s in flags), None)
		houses.append({
			'id': hid, 'name_str': args[4], 'size': size, 'flags': flags,
			'church': 'IsChurch' in flags, 'stadium': 'IsStadium' in flags,
			'climates': sorted({c for k, c in HOUSE_CLIMATES.items() if k in zones}, key=CLIMATES.index),
			'above_snow': 'ClimateSubarcticAboveSnow' in zones,
			'years': (int(args[0]), args[1].replace('CalendarTime::MAX_YEAR', 'max')),
		})
	for h in houses:
		h['label'] = strings.get(h['name_str'], h['name_str'])
	return houses, draw


HOUSE_TILES = {
	'Size1x1': [(0, 0)],
	'Size1x2': [(0, 0), (0, 1)],
	'Size2x1': [(0, 0), (1, 0)],
	'Size2x2': [(0, 0), (0, 1), (1, 0), (1, 1)],
}


def house_image(house, draw, store, recolours, stage=3, variant=0):
	canvas = Canvas(store, recolours)
	for i, (tx, ty) in enumerate(HOUSE_TILES[house['size']]):
		d = draw[(house['id'] + i) << 4 | variant << 2 | stage]
		x, y = tx * 16, ty * 16
		canvas.add(*d['ground'], x, y, 0, layer=0)
		canvas.add(*d['building'], x + d['dx'], y + d['dy'], 0)
	return canvas.render()


LANDSCAPE_NAMES = {'Temperate': 'temperate', 'Arctic': 'arctic', 'Tropic': 'tropic', 'Toyland': 'toyland'}


def parse_industries(sym, strings):
	bi = strip_comments((TABLE / 'build_industry.h').read_text())
	il = strip_comments((TABLE / 'industry_land.h').read_text())
	draw = parse_draw_buildings(il, '_industry_draw_tile_data', sym)

	layouts = {}
	for m in re.finditer(r'static const IndustryTileLayout (\w+)\s*\{', bi):
		body = block(bi, r'IndustryTileLayout ' + m.group(1) + r'\s*\{')
		tiles = []
		for args in macro_calls(body, 'MK'):
			x, y, gfx = sym.get(args[0]), sym.get(args[1]), sym.get(args[2])
			if None not in (x, y, gfx):
				tiles.append((x, y, gfx))
		layouts[m.group(1)] = tiles
	tables = {}
	for m in re.finditer(r'static const std::vector<IndustryTileLayout> (\w+)\s*\{([^}]*)\}', bi):
		tables[m.group(1)] = [n.strip() for n in m.group(2).split(',') if n.strip()]

	industries = []
	for iid, args in enumerate(macro_calls(block(bi, r'_origin_industry_specs\[[^\]]*\]\s*='), 'MI')):
		name_str = next(a for a in args if a.startswith('STR_INDUSTRY_NAME_'))
		clim_arg = next(a for a in args if a.startswith('LandscapeType'))
		climates = [c for k, c in LANDSCAPE_NAMES.items() if 'LandscapeType::' + k in clim_arg]
		names = tables.get(args[0], [])
		industries.append({
			'id': iid, 'name_str': name_str, 'label': strings.get(name_str, name_str), 'climates': climates,
			'layouts': [layouts[n] for n in names if n in layouts],
		})
	return industries, draw


def industry_image(layout, draw, store, recolours, stage=3):
	canvas = Canvas(store, recolours)
	for tx, ty, gfx in layout:
		if (gfx << 2 | stage) >= len(draw):
			continue
		d = draw[gfx << 2 | stage]
		x, y = tx * 16, ty * 16
		canvas.add(*d['ground'], x, y, 0, layer=0)
		canvas.add(*d['building'], x + d['dx'], y + d['dy'], 0)
	return canvas.render()


TREE_GROUPS = [
	# (first type, count, climate, group)
	(0x00, 12, 'temperate', 'temperate'),
	(0x0C, 8, 'arctic', 'sub_arctic'),
	(0x14, 7, 'tropic', 'rainforest'),
	(0x1B, 1, 'tropic', 'cactus'),
	(0x1C, 4, 'tropic', 'sub_tropical'),
	(0x20, 9, 'toyland', 'toyland'),
]


def parse_trees(sym):
	text = strip_comments((TABLE / 'tree_land.h').read_text())
	body = block(text, r'_tree_layout_sprite\[[^\]]*\]\[4\]\s*=')
	rows = re.findall(r'\{\s*\{\s*([^,]+),', body)
	return [sym.get(r) for r in rows]


def tree_image(base, store, recolours):
	frames = []
	for growth in range(7):
		canvas = Canvas(store, recolours)
		canvas.add(base + growth, 0, 8, 8, 0)
		frames.append(canvas.render())
	return strip(frames)


VEHICLE_TABLES = {
	'train': ('_orig_rail_vehicle_info', 'RVI', 'STR_VEHICLE_NAME_TRAIN_ENGINE_RAIL_KIRBY_PAUL_TANK_STEAM'),
	'road': ('_orig_road_vehicle_info', 'ROV', 'STR_VEHICLE_NAME_ROAD_VEHICLE_MPS_REGAL_BUS'),
	'ship': ('_orig_ship_vehicle_info', 'SVI', 'STR_VEHICLE_NAME_SHIP_MPS_OIL_TANKER'),
	'aircraft': ('_orig_aircraft_vehicle_info', 'AVI', 'STR_VEHICLE_NAME_AIRCRAFT_SAMPSON_U52'),
}


def parse_vehicles(strings):
	raw = (TABLE / 'engines.h').read_text()
	text = strip_comments(raw)
	info_body = block(text, r'_orig_engine_info\[\]\s*=')
	engine_climates = []
	for macro in re.finditer(r'\b(MT|MW|MM|MR|MA)\s*\(([^)]*)\)', info_body):
		args = split_args(macro.group(2))
		clim = args[-1]
		engine_climates.append([c for c, k in (('temperate', 'T'), ('arctic', 'A'), ('tropic', 'S'), ('toyland', 'Y')) if re.search(r'\b' + k + r'\b', clim)])

	# English string order gives the names; table row comments are a fallback.
	str_names = list(strings)

	vehicles = []
	offset = 0
	for kind, (array, macro, first_str) in VEHICLE_TABLES.items():
		rows = list(macro_calls(block(text, array + r'\[\]\s*='), macro))
		start = str_names.index(first_str)
		for i, args in enumerate(rows):
			label = strings[str_names[start + i]]
			v = {'kind': kind, 'local_id': i, 'engine_id': offset + i, 'image_index': int(args[0]), 'label': label,
				'climates': engine_climates[offset + i] if offset + i < len(engine_climates) else []}
			if kind == 'train':
				v['type'] = {'M': 'multihead', 'W': 'wagon', 'G': 'engine'}.get(args[1], args[1])
			vehicles.append(v)
		offset += len(rows)
	return vehicles


def parse_u16_array(path, name):
	text = strip_comments(path.read_text())
	body = block(text, name + r'\[\]\s*=')
	return [int(v, 0) for v in re.findall(r'0x[0-9A-Fa-f]+|\b\d+\b', body)]


def vehicle_sprites(v, tables):
	"""Return (sprites for 8 directions, loaded-sprite offset or 0)."""
	idx = v['image_index']
	if v['kind'] == 'train':
		base, mask, add, full = (tables[k][idx] for k in ('_engine_sprite_base', '_engine_sprite_and', '_engine_sprite_add', '_wagon_full_adder'))
		return [((d + add) & mask) + base for d in range(8)], full
	if v['kind'] == 'road':
		return [tables['_roadveh_images'][idx] + d for d in range(8)], tables['_roadveh_full_adder'][idx]
	if v['kind'] == 'ship':
		return [tables['_ship_sprites'][idx] + d for d in range(8)], 0
	return [tables['_aircraft_sprite'][idx] + d for d in range(8)], 0


def vehicle_image(sprites, store, recolours, loaded=0):
	frames = []
	for s in sprites:
		canvas = Canvas(store, recolours)
		canvas.add(s + loaded | RECOLOUR_FLAG, 0, 8, 8, 0)
		frames.append(canvas.render())
	return strip(frames)


OBJECTS = [
	# (id, label, ground, [(sprite, dx, dy)])
	('transmitter', 'Transmitter', 'SPR_FLAT_2_THIRD_GRASS_TILE', [('SPR_TRANSMITTER', 7, 7)]),
	('lighthouse', 'Lighthouse', 'SPR_FLAT_2_THIRD_GRASS_TILE', [('SPR_LIGHTHOUSE', 4, 4)]),
	('statue', 'Company statue', 'SPR_CONCRETE_GROUND', [('SPR_STATUE_COMPANY', 0, 0)]),
	('owned_land', 'Owned land', 'SPR_FLAT_BARE_LAND', [('SPR_BOUGHT_LAND', 8, 8)]),
]

HQ_SIZES = ['TINY', 'SMALL', 'MEDIUM', 'LARGE', 'HUGE']


def hq_image(size, sym, store, recolours):
	"""Company HQ: four tiles, index size<<2 | y<<1 | x (object_cmd.cpp)."""
	text = strip_comments((TABLE / 'object_land.h').read_text())
	lines = re.findall(r'TILE_SPRITE_LINE(?:_NOTHING)?\(\s*(\w+)(?:\s*,\s*(\w+))?\)', block(text, r'_object_hq\[\]\s*='))
	seqs = {m.group(1): m.group(2) for m in re.finditer(r'_object_hq_(\w+)\[\]\s*=\s*\{\s*TILE_SEQ_LINE\(\s*\d+\s*,\s*(\w+)', text)}
	canvas = Canvas(store, recolours)
	for part in range(4):
		ground, seq = lines[size * 4 + part]
		x, y = (part & 1) * 16, (part >> 1) * 16
		canvas.add(sym.get(ground) | RECOLOUR_FLAG, 0, x, y, 0, layer=0)
		if seq:
			canvas.add(sym.get(seqs[seq.replace('_object_hq_', '')]) | RECOLOUR_FLAG, 0, x, y, 0)
	return canvas.render()


def single_image(sym, store, recolours, ground, parts, company=False):
	canvas = Canvas(store, recolours)
	flag = RECOLOUR_FLAG if company else 0
	if ground:
		canvas.add(sym.get(ground), 0, 0, 0, 0, layer=0)
	for sprite, dx, dy in parts:
		canvas.add((sym.get(sprite) if isinstance(sprite, str) else sprite) | flag, 0, dx, dy, 0)
	return canvas.render()


# ---------------------------------------------------------------------------
# Extra GRF (OpenTTD's own sprites, loaded by Action 5 blocks)

ACTION5_BASES = {
	0x04: 'SPR_SIGNALS_BASE', 0x05: 'SPR_ELRAIL_BASE', 0x06: 'SPR_SLOPES_BASE', 0x08: 'SPR_CANALS_BASE',
	0x09: 'SPR_ONEWAY_BASE', 0x0B: 'SPR_TRAMWAY_BASE', 0x0D: 'SPR_SHORE_BASE', 0x0F: 'SPR_TRACKS_FOR_SLOPES_BASE',
	0x10: 'SPR_AIRPORTX_BASE', 0x11: 'SPR_ROADSTOP_BASE', 0x12: 'SPR_AQUEDUCT_BASE', 0x13: 'SPR_AUTORAIL_BASE',
	0x15: 'SPR_OPENTTD_BASE', 0x16: 'SPR_AIRPORT_PREVIEW_BASE', 0x17: 'SPR_RAILTYPE_TUNNEL_BASE',
	0x19: 'SPR_ROAD_WAYPOINTS_BASE', 0x1A: 'SPR_OVERLAY_ROCKS_BASE', 0x1B: 'SPR_BRIDGE_DECKS_BASE',
}


def parse_extra(nfo, sym):
	"""Map SpriteIDs to .nfo sprite numbers for each Action 5 block; the first block for a sprite wins."""
	mapping = {}
	for line in nfo.read_text(encoding='latin-1').splitlines():
		m = re.match(r'^\s*(\d+)\s+\*\s+\d+\s+05\s+([0-9A-Fa-f]{2})\s+(.*)$', line)
		if not m:
			continue
		number, typ = int(m.group(1)), int(m.group(2), 16)
		data = [int(b, 16) for b in m.group(3).split()]

		def ext(pos):
			return (data[pos + 1] | data[pos + 2] << 8, pos + 3) if data[pos] == 0xFF else (data[pos], pos + 1)

		count, pos = ext(0)
		offset = ext(pos)[0] if typ & 0x80 else 0
		base = sym.get(ACTION5_BASES.get(typ & 0x7F, ''))
		if base is None:
			continue
		for k in range(count):
			mapping.setdefault(base + offset + k, number + 1 + k)
	return mapping


# ---------------------------------------------------------------------------
# DrawTileSeqStruct / DrawTileSpriteSpan layouts



def expand_macros(text, macros):
	for _ in range(6):
		changed = False
		for name, (params, body) in macros.items():
			while True:
				m = re.search(r'\b' + name + r'\s*\(', text)
				if not m:
					break
				i, depth = m.end(), 1
				while depth:
					depth += {'(': 1, ')': -1}.get(text[i], 0)
					i += 1
				args = split_args(text[m.end():i - 1])
				out = body
				for p, a in zip(params, args):
					out = re.sub(r'\b' + p + r'\b', lambda _m, a=a: '(' + a + ')', out)
				text = text[:m.start()] + out + text[i:]
				changed = True
		if not changed:
			break
	return text


def load_layouts(path, sym):
	"""Return (seqs, spans): seqs[name] = [(dx,dy,dz,sx,sy,sz,img,pal)], spans[name] = [(ground, pal, seqname)]."""
	text = strip_comments(path.read_text())
	events = [(m.start(), 'def', m) for m in re.finditer(r'^#define\s+(\w+)\(([^)]*)\)[ 	]*(.*)$', text, re.M)]
	events += [(m.start(), 'undef', m) for m in re.finditer(r'^#undef\s+(\w+)', text, re.M)]
	events += [(m.start(), 'decl', m) for m in re.finditer(
		r'^\s*(?:extern\s+)?(?:static\s+)?const\s+(DrawTileSeqStruct|DrawTileSpriteSpan)\s+(\w+)((?:\[[^\]]*\])*)\s*=', text, re.M)]
	seqs, spans, macros = {}, {}, {}
	for pos, kind, m in sorted(events, key=lambda e: e[0]):
		if kind == 'def':
			macros[m.group(1)] = ([p.strip() for p in m.group(2).split(',') if p.strip()], m.group(3))
			continue
		if kind == 'undef':
			macros.pop(m.group(1), None)
			continue
		start = text.index('{', m.end())
		depth, j = 0, start
		while True:
			depth += {'{': 1, '}': -1}.get(text[j], 0)
			j += 1
			if depth == 0:
				break
		body = expand_macros(text[start + 1:j - 1], macros)
		if m.group(1) == 'DrawTileSeqStruct':
			items = []
			for e in re.finditer(r'\{([^{}]*)\{([^{}]*)\}\s*\}', body):
				nums = split_args(e.group(1))
				img = split_args(e.group(2))
				vals = [sym.get(n) for n in nums[:6]]
				if len(nums) < 6 or None in vals:
					continue
				items.append(tuple(vals) + (sym.get(img[0]) or 0, (sym.get(img[1]) or 0) if len(img) > 1 else 0))
			seqs[m.group(2)] = items
		else:
			items = []
			for e in re.finditer(r'\{\s*\{([^{}]*)\}\s*(?:,\s*\(?\s*(\w+)\s*\)?)?\s*\}', body):
				g = split_args(e.group(1))
				items.append((sym.get(g[0]) or 0, (sym.get(g[1]) or 0) if len(g) > 1 else 0, e.group(2)))
			spans[m.group(2)] = items
	return seqs, spans


def draw_span(canvas, span, seqs, x=0, y=0, z=0, ground_base=0, seq_base=0, seq_offset=0, company=True):
	ground, gpal, seqname = span
	if ground:
		canvas.add((ground + ground_base if ground < 5 and ground_base else ground) | (RECOLOUR_FLAG if company and ground & RECOLOUR_FLAG else 0), gpal, x, y, z, layer=0)
	parent = False
	for dx, dy, dz, sx, sy, sz, img, pal in seqs.get(seqname, []) if seqname else []:
		sprite = (img & SPRITE_MASK) + seq_base + seq_offset | (img & (RECOLOUR_FLAG | TRANSPARENT_FLAG))
		if dz not in (128, -128):
			canvas.add(sprite, pal, x + dx, y + dy, z + dz)
			parent = True
		elif parent:
			canvas.add_child(sprite, pal, dx, dy)
		else:
			canvas.add_ground_child(sprite, pal, x, y, z, dx, dy)


def parse_enum_sequence(path, enum):
	body = block(strip_comments(path.read_text()), r'enum\s+' + enum + r'\b[^{]*\{')
	names, value = {}, 0
	for item in body.split(','):
		item = item.strip()
		if not item:
			continue
		if '=' in item:
			n, v = item.split('=', 1)
			item, value = n.strip(), int(v.strip(), 0)
		names[item] = value
		value += 1
	return names


# ---------------------------------------------------------------------------
# Inventory

# Moving parts drawn over an industry's static tiles, one `part_<n>` state per step (Phase 8.7): the coal mine
# headframe wheel, the power station sparks, the refinery and oil rig flare flames, the oil well pump.
INDUSTRY_PARTS = {0: 3, 1: 6, 4: 4, 5: 4, 11: 12}
# Effect vehicle sprite sequences: key, label, first sprite, frames. Crash smoke, aircraft breakdown smoke and
# copper mine smoke share SPR_SMOKE; the bubble generator's bubbles are toyland only (Phase 10).
EFFECTS = (
	('effect_chimney_smoke', 'Chimney smoke', 'SPR_CHIMNEY_SMOKE_0', 8),
	('effect_steam_smoke', 'Steam engine smoke', 'SPR_STEAM_SMOKE_0', 5),
	('effect_diesel_smoke', 'Diesel engine smoke', 'SPR_DIESEL_SMOKE_0', 6),
	('effect_electric_spark', 'Electric engine spark', 'SPR_ELECTRIC_SPARK_0', 6),
	('effect_smoke', 'Smoke', 'SPR_SMOKE_0', 5),
	('effect_explosion_large', 'Large explosion', 'SPR_EXPLOSION_LARGE_0', 16),
	('effect_breakdown_smoke', 'Breakdown smoke', 'SPR_BREAKDOWN_SMOKE_0', 4),
	('effect_explosion_small', 'Small explosion', 'SPR_EXPLOSION_SMALL_0', 12),
	('effect_bulldozer', 'Roadworks bulldozer', 'SPR_BULLDOZER_NE', 4),
)


def merge_entry(old, new):
	"""Keep user/pipeline fields from a previous run."""
	if old:
		for k in ('status', 'approach', 'kit', 'family', 'notes', 'shared_with', 'blend'):
			if k in old:
				new[k] = old[k]
	return new


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('--sprites', default=str(ROOT / 'sprites_pulled' / 'sliced'))
	args = ap.parse_args()
	sliced = Path(args.sprites)
	if not (sliced / 'ogfx1_base' / 'index.csv').exists():
		sys.exit(f'{sliced} has no slices; run tools/3d_assets/slice_sprites.py first')

	sym = Symbols([TABLE / 'sprites.h', SRC / 'gfx_type.h', SRC / 'tile_type.h', TABLE / 'water_land.h'])
	strings = load_strings()
	recolours = parse_recolours(ROOT / 'sprites_pulled' / 'ogfx1_base' / 'ogfx1_base.nfo')
	landscape = parse_landscape_tables()
	extra = parse_extra(ROOT / 'sprites_pulled' / 'ogfxe_extra' / 'ogfxe_extra.nfo', sym)
	stores = {c: SpriteStore(sliced, c, landscape, extra) for c in CLIMATES}

	old = {}
	if OUT_INV.exists():
		old = {e['key']: e for e in json.loads(OUT_INV.read_text(encoding='utf-8'))['entries']}
	entries = []

	def emit(key, category, approach, label, climates, render, extra=None, family=None):
		refs = {}
		for c in climates:
			name = f'{key}_{slug(label)}.png'
			if save(render(c), OUT_REF / c / name):
				refs[c] = f'reference/{c}/{name}'
		e = {'key': key, 'category': category, 'label': label, 'climates': climates, 'approach': approach,
			'status': 'not_started', 'reference': refs}
		if family:
			e['family' if approach == 'family' else 'kit'] = family
		e.update(extra or {})
		entries.append(merge_entry(old.get(key), e))

	# Houses: one identity per north tile.
	houses, hdraw = parse_houses(sym, strings)
	for h in houses:
		if not h['size']:
			continue
		states = ['construction_0', 'construction_1', 'construction_2', 'complete']
		emit(f'house_{h["id"]:03d}', 'house', 'bespoke', h['label'], h['climates'],
			lambda c, h=h: strip([house_image(h, hdraw, stores[c], recolours, stage=s) for s in range(4)]),
			{'house_id': h['id'], 'footprint': h['size'].replace('Size', ''), 'states': states,
				'years': list(h['years']), 'flags': re.findall(r'BuildingFlag::(\w+)', h['flags']), **({'above_snowline': True} if h['above_snow'] else {})})

	# Industries: whole layouts for reference, cut per tile graphic at modelling time.
	industries, idraw = parse_industries(sym, strings)
	for ind in industries:
		gfx = sorted({g for lay in ind['layouts'] for _, _, g in lay})
		parts = [f'part_{n}' for n in range(INDUSTRY_PARTS.get(ind['id'], 0))]
		emit(f'industry_{ind["id"]:02d}', 'industry', 'bespoke', ind['label'], ind['climates'],
			lambda c, ind=ind: strip([industry_image(l, idraw, stores[c], recolours) for l in ind['layouts']], gap=12),
			{'industry_id': ind['id'], 'layouts': [[list(t) for t in lay] for lay in ind['layouts']], 'tile_gfx': gfx,
				'states': ['construction_0', 'construction_1', 'construction_2', 'complete'] + parts})

	# Trees: growth stages 0-6 (3 = full, 4-6 dying/dead).
	tree_sprites = parse_trees(sym)
	for first, count, climate, group in TREE_GROUPS:
		for t in range(first, first + count):
			base = tree_sprites[t << 2]
			climates = [climate]
			emit(f'tree_{t:02d}', 'tree', 'family', f'{group} tree {t - first + 1}', climates,
				lambda c, base=base: tree_image(base, stores[c], recolours),
				{'tree_type': t, 'sprite_base': base, 'states': ['growth_0', 'growth_1', 'growth_2', 'grown', 'dying_0', 'dying_1', 'dead']},
				family=f'trees_{group}')
		if group == 'sub_arctic':
			for t in range(first, first + count):
				base = tree_sprites[164 + ((t - first) << 2)]
				emit(f'tree_{t:02d}_snow', 'tree', 'family', f'{group} tree {t - first + 1} (snow)', ['arctic'],
					lambda c, base=base: tree_image(base, stores[c], recolours),
					{'tree_type': t, 'sprite_base': base, 'variant_of': f'tree_{t:02d}'}, family=f'trees_{group}')

	# Vehicles: one identity per engine; engines sharing a base image share a model.
	vtables = {n: parse_u16_array(TABLE / 'train_sprites.h', n) for n in ('_engine_sprite_base', '_engine_sprite_and', '_engine_sprite_add', '_wagon_full_adder')}
	vtables['_roadveh_images'] = parse_u16_array(SRC / 'roadveh_cmd.cpp', '_roadveh_images')
	vtables['_roadveh_full_adder'] = parse_u16_array(SRC / 'roadveh_cmd.cpp', '_roadveh_full_adder')
	vtables['_ship_sprites'] = parse_u16_array(SRC / 'ship_cmd.cpp', '_ship_sprites')
	vtables['_aircraft_sprite'] = parse_u16_array(SRC / 'aircraft_cmd.cpp', '_aircraft_sprite')
	first_by_image = {}
	for v in parse_vehicles(strings):
		key = f'{v["kind"]}_{v["local_id"]:03d}'
		sprites, loaded = vehicle_sprites(v, vtables)
		ident = (v['kind'], sprites[0])
		shared = first_by_image.setdefault(ident, key)
		extra = {'engine_id': v['engine_id'], 'image_index': v['image_index'], 'sprite_base': sprites[0]}
		if 'type' in v:
			extra['type'] = v['type']
		extra['states'] = ['empty', 'loaded'] if loaded else ['default']
		if shared != key:
			extra['status'] = 'shared'
			extra['shared_with'] = shared

		def render(c, sprites=sprites, loaded=loaded):
			rows = [vehicle_image(sprites, stores[c], recolours)]
			if loaded:
				rows.append(vehicle_image(sprites, stores[c], recolours, loaded))
			return strip(rows, gap=12)

		climates = v['climates'] or ['temperate']
		emit(key, 'vehicle', 'kit', v['label'], climates if shared == key else climates[:1], render, extra, family=f'{v["kind"]}_kit')

	# Map objects.
	for oid, label, ground, parts in OBJECTS:
		emit(f'object_{oid}', 'object', 'bespoke', label, list(CLIMATES),
			lambda c, ground=ground, parts=parts, oid=oid: single_image(sym, stores[c], recolours, ground, parts, company=oid in ('statue', 'owned_land')))
	for size, name in enumerate(HQ_SIZES):
		emit(f'object_hq_{name.lower()}', 'object', 'bespoke', f'Company HQ {name.lower()}', list(CLIMATES),
			lambda c, size=size: hq_image(size, sym, stores[c], recolours), {'footprint': '2x2'})

	all_climates = list(CLIMATES)

	def frames(c, fn, items, gap=6):
		out = []
		for item in items:
			canvas = Canvas(stores[c], recolours)
			fn(canvas, item)
			out.append(canvas.render())
		return strip(out, gap)

	# Signals: 6 types x electric/semaphore, 8 track positions x red/green each (rail_cmd.cpp DrawSingleSignal).
	sig_orig, sig_base = sym.get('SPR_ORIGINAL_SIGNALS_BASE'), sym.get('SPR_SIGNALS_BASE')
	for variant, vname in ((0, 'electric'), (1, 'semaphore')):
		for stype, tname in enumerate(('block', 'entry', 'exit', 'combo', 'path', 'path_oneway')):
			first = sig_orig if stype == 0 and variant == 0 else sig_base - 16 + stype * 16 + variant * 64 + (64 if stype > 3 else 0)
			emit(f'signal_{vname}_{tname}', 'rail_furniture', 'family', f'{vname} {tname} signal', all_climates,
				lambda c, first=first: frames(c, lambda cv, i: cv.add(first + i, 0, 8, 8, 0), range(16)),
				{'states': ['red', 'green'], 'sprite_base': first}, family='signals')

	# Level crossing (rail over road, both axes, open/closed).
	emit('crossing_rail_road', 'rail_furniture', 'bespoke', 'Level crossing', all_climates,
		lambda c: frames(c, lambda cv, i: cv.add(sym.get('SPR_CROSSING_OFF_X_RAIL') + i, 0, 0, 0, 0, layer=0), range(4)),
		{'states': ['open', 'closed']})

	# Electrified rail catenary: wires and pylons (extra GRF block 0x05).
	elrail = sym.get('SPR_ELRAIL_BASE')
	emit('catenary_rail', 'rail_furniture', 'family', 'Rail catenary wires and pylons', all_climates,
		lambda c: frames(c, lambda cv, i: cv.add(elrail + i, 0, 8, 8, 0), range(40), gap=2),
		{'states': ['pylon', 'pylon_diagonal', 'wire_both', 'wire_half'], 'sprite_base': elrail}, family='catenary')

	# Stations, stops, waypoints, docks, buoys, oil rig (station_land.h).
	seqs, spans = load_layouts(TABLE / 'station_land.h', sym)

	def span_frames(c, table, indices):
		return frames(c, lambda cv, i: draw_span(cv, spans[table][i], seqs), indices)

	station_groups = [
		('station_rail_platform', 'Rail station platform', '_station_display_datas_rail', [0, 1]),
		('station_rail_building', 'Rail station building', '_station_display_datas_rail', [2, 3]),
		('station_rail_roof_a', 'Rail station roof A', '_station_display_datas_rail', [4, 5]),
		('station_rail_roof_b', 'Rail station roof B', '_station_display_datas_rail', [6, 7]),
		('waypoint_rail', 'Rail waypoint', '_station_display_datas_waypoint', range(len(spans['_station_display_datas_waypoint']))),
		('stop_truck_bay', 'Lorry loading bay', '_station_display_datas_truck', [0, 1, 2, 3]),
		('stop_truck_drive', 'Drive-through lorry stop', '_station_display_datas_truck', [4, 5]),
		('stop_bus_bay', 'Bus station', '_station_display_datas_bus', [0, 1, 2, 3]),
		('stop_bus_drive', 'Drive-through bus stop', '_station_display_datas_bus', [4, 5]),
		('waypoint_road', 'Road waypoint', '_station_display_datas_road_waypoint', range(len(spans['_station_display_datas_road_waypoint']))),
		('dock', 'Dock', '_station_display_datas_dock', range(6)),
		('buoy', 'Buoy', '_station_display_datas_buoy', [0]),
	]
	for key, label, table, idx in station_groups:
		emit(key, 'station', 'bespoke', label, all_climates, lambda c, table=table, idx=list(idx): span_frames(c, table, idx))

	# Airports: whole layouts from airport_defaults.h, tiles from the airport span.
	apt = parse_enum_sequence(TABLE / 'airporttile_ids.h', 'AirportTiles')
	ad = strip_comments((TABLE / 'airport_defaults.h').read_text())
	airport_layouts = {}
	for m in re.finditer(r'AirportTileTable> (_tile_table_(\w+?)_\d+) = \{', ad):
		body = block(ad, re.escape(m.group(1)) + r' = \{')
		tiles = [(int(a[0]), int(a[1]), apt.get(a[2].strip())) for a in macro_calls(body, 'MK')]
		airport_layouts.setdefault(m.group(2), tiles)
	airport_span = spans['_station_display_datas_airport']
	for args in macro_calls(block(ad, r'_origin_airport_specs\[\]\s*='), r'AS(?:_ND)?'):
		name, label = args[0], strings.get(args[10], args[0])

		def render_airport(c, name=name):
			canvas = Canvas(stores[c], recolours)
			for tx, ty, gfx in airport_layouts.get(name, []):
				if gfx is not None and gfx < len(airport_span):
					draw_span(canvas, airport_span[gfx], seqs, tx * 16, ty * 16)
			return canvas.render()

		gfx_used = sorted({g for _, _, g in airport_layouts.get(name, []) if g is not None})
		emit(f'airport_{name}', 'station', 'bespoke', label, all_climates, render_airport,
			{'footprint': f'{args[1]}x{args[2]}', 'note': 'model per airport tile graphic; reference shows the assembled layout',
				'tile_gfx': gfx_used, 'layout': [[tx, ty, g] for tx, ty, g in airport_layouts.get(name, []) if g is not None]})

	# One image per base airport tile graphic, for modelling the tiles (not inventory identities).
	apt_names = {v: k for k, v in apt.items()}
	for c in CLIMATES:
		for gfx, span in enumerate(airport_span[:len(apt_names)]):
			# Animated tiles draw from their own frame tables (station_cmd.cpp); frame 0 stands for them.
			anim_name = {'APT_GRASS_FENCE_NE_FLAG': 'flag_grass_fence_ne', 'APT_GRASS_FENCE_NE_FLAG_2': 'flag_grass_fence_ne_2'}.get(
				apt_names[gfx], apt_names[gfx].lower().replace('apt_', ''))
			anim = spans.get('_station_display_datas_airport_' + anim_name)
			if anim:
				span = anim[0]
			canvas = Canvas(stores[c], recolours)
			draw_span(canvas, span, seqs)
			save(canvas.render(), OUT_REF / c / 'airport_tiles' / f'{gfx:02d}_{apt_names[gfx].lower()}.png')

	# Depots.
	tseqs, tspans = load_layouts(TABLE / 'track_land.h', sym)
	emit('depot_rail', 'depot', 'bespoke', 'Train depot', all_climates,
		lambda c: frames(c, lambda cv, i: draw_span(cv, tspans['_depot_gfx_table'][i], tseqs), range(4)))
	rseqs, rspans = load_layouts(TABLE / 'road_land.h', sym)
	emit('depot_road', 'depot', 'bespoke', 'Road vehicle depot', all_climates,
		lambda c: frames(c, lambda cv, i: draw_span(cv, rspans['_road_depot'][i], rseqs), range(4)))
	wseqs, wspans = load_layouts(TABLE / 'water_land.h', sym)

	def ship_depot(cv, axis):
		for part in range(2):
			draw_span(cv, wspans['_shipdepot_display_data'][axis * 2 + part], wseqs, 16 * part * (axis == 0), 16 * part * (axis == 1))

	emit('depot_ship', 'depot', 'bespoke', 'Ship depot', all_climates, lambda c: frames(c, ship_depot, range(2)), {'footprint': '2x1'})

	canals, lock_base = sym.get('SPR_CANALS_BASE'), sym.get('SPR_LOCK_BASE')

	def lock(cv, direction):
		# Parts: middle (0), lower (1), upper (2), laid out along the lock direction.
		step = [(-1, 0), (0, 1), (1, 0), (0, -1)][direction]
		for part, k, z in ((1, -1, 0), (0, 0, 0), (2, 1, 8)):
			draw_span(cv, wspans['_lock_display_data'][part * 4 + direction], wseqs, 16 * k * step[0], 16 * k * step[1], z,
				ground_base=canals, seq_base=lock_base)

	emit('lock', 'water', 'bespoke', 'Canal lock', all_climates, lambda c: frames(c, lock, range(2), gap=12), {'footprint': '3x1'})

	# Bridges: GUI sprite plus the rail X-axis pieces of each type (bridge_land.h).
	bl = strip_comments((TABLE / 'bridge_land.h').read_text())
	bl = re.sub(r'\bM([NRWC])\(\s*([^()]+?)\s*\)', lambda m: '{%s, %s}' % (m.group(2), {'N': 'PAL_NONE', 'R': 'PALETTE_TO_STRUCT_RED',
		'W': 'PALETTE_TO_STRUCT_WHITE', 'C': 'PALETTE_TO_STRUCT_CONCRETE'}[m.group(1)]), bl)
	piece_tables = {m.group(1): [(sym.get(a) or 0, sym.get(b) or 0) for a, b in re.findall(r'\{\s*([^,{}]+),\s*([^{}]+?)\s*\}', block(bl, re.escape(m.group(1)) + r'\[\]\s*='))]
		for m in re.finditer(r'PalSpriteID (_bridge_sprite_table_\w+)\[\]', bl)}
	type_pieces = {m.group(1): re.findall(r'_bridge_sprite_table_\w+', m.group(2))
		for m in re.finditer(r'std::span<const PalSpriteID> (_bridge_sprite_table_\w+)\[\]\s*=\s*\{([^}]*)\}', bl)}
	order = re.findall(r'_bridge_sprite_table_\w+', block(bl, r'_bridge_sprite_table\[MAX_BRIDGES\]\s*='))
	for bid, args in enumerate(macro_calls(block(bl, r'_orig_bridge\[\]\s*='), 'MBR')):
		gui, gpal = sym.get(args[5]), sym.get(args[6]) or 0
		pieces = []
		for t in type_pieces.get(order[bid], []):
			for piece in piece_tables.get(t, [])[:4]:
				if piece[0] and piece not in pieces:
					pieces.append(piece)

		def bridge(c, gui=gui, gpal=gpal, pieces=pieces):
			return strip([frames(c, lambda cv, s: cv.add(s, gpal, 0, 0, 0), [gui]),
				frames(c, lambda cv, p: cv.add(p[0], p[1], 8, 8, 0), pieces, gap=2)], gap=16)

		emit(f'bridge_{bid:02d}', 'bridge', 'family', f'{strings.get(args[7], args[7])} {bid}', all_climates, bridge,
			{'states': ['ramp', 'middle', 'pillar']}, family='bridges')

		# Assembled rail spans as DrawTile_TunnelBridge/DrawBridgeMiddle place them: ramps on flat tiles at z=24,
		# middle tiles on flat ground at z=0 with stacked pillars. Lengths 3 and 5 between them use all six pieces.
		tables = [piece_tables.get(t, []) for t in type_pieces.get(order[bid], [])]

		def span(cv, axis, middles, tables=tables):
			head_z, bridge_z = 24, 32
			at = (lambda i: (16 * i, 0)) if axis == 0 else (lambda i: (0, 16 * i))
			n = len(middles) + 1
			for i, d in ((0, 2 if axis == 0 else 1), (n, 0 if axis == 0 else 3)):
				ramp = {2: 0, 1: 1, 0: 2, 3: 3}[d] + 4
				x, y = at(i)
				cv.add(*tables[6][ramp], x, y, head_z)
			for i, piece in enumerate(middles, 1):
				floor, front, pillar = tables[piece][axis * 4:axis * 4 + 3]
				x, y = at(i)
				fx, fy = (x, y + 12) if axis == 0 else (x + 12, y)
				cv.add(*floor, x, y, bridge_z - 3)
				cv.add(*front, fx, fy, bridge_z - 3)
				for z in range(bridge_z - 3, -1, -8):
					cv.add(*pillar, fx, fy, z, order=fx + fy - 0.5)
				for z in range(bridge_z - 19, -1, -8):
					cv.add(*pillar, fx - 9 * axis, fy - 9 * (1 - axis), z, order=fx + fy - 9.5)

		if tables:
			for c in CLIMATES:
				for name, axis, middles in (('x3', 0, (0, 4, 1)), ('x5', 0, (0, 2, 5, 3, 1)), ('y5', 1, (0, 2, 5, 3, 1))):
					canvas = Canvas(stores[c], recolours)
					span(canvas, axis, middles)
					save(canvas.render(), OUT_REF / c / 'bridge_spans' / f'{bid:02d}_{name}.png')
				# Each middle piece alone over a grass tile (its footprint), and both ramps (sloped and on a foundation).
				pieces = []
				for piece in range(6):
					canvas = Canvas(stores[c], recolours)
					canvas.add(sym.get('SPR_FLAT_GRASS_TILE'), 0, 0, 0, 0, layer=0)
					floor, front, pillar = tables[piece][:3]
					canvas.add(*floor, 0, 0, 29)
					canvas.add(*front, 0, 12, 29)
					for z in (29, 21, 13, 5):
						canvas.add(*pillar, 0, 12, z, order=11.5)
					for z in (13, 5):
						canvas.add(*pillar, 0, 3, z, order=2.5)
					pieces.append(canvas.render())
				for ramp in (4, 0):
					canvas = Canvas(stores[c], recolours)
					canvas.add(sym.get('SPR_FLAT_GRASS_TILE'), 0, 0, 0, 0, layer=0)
					canvas.add(*tables[6][ramp], 0, 0, 0 if ramp else 8)
					pieces.append(canvas.render())
				save(strip(pieces, 8), OUT_REF / c / 'bridge_spans' / f'{bid:02d}_pieces.png')

	# Tunnel portals: rear part is a ground sprite, front part sorts over vehicles.
	for key, label, base in (('tunnel_rail', 'Rail tunnel portal', 'SPR_TUNNEL_ENTRY_REAR_RAIL'), ('tunnel_road', 'Road tunnel portal', 'SPR_TUNNEL_ENTRY_REAR_ROAD')):
		first = sym.get(base)
		emit(key, 'tunnel', 'bespoke', label, all_climates,
			lambda c, first=first: frames(c, lambda cv, d: (cv.add(first + d * 2, 0, 0, 0, 0, layer=0), cv.add(first + d * 2 + 1, 0, 0, 0, 0)), range(4)))

	# Field hedges and fences (clear_land.h; six slope variants each).
	for k, name in enumerate(('SPR_HEDGE_BUSHES', 'SPR_HEDGE_BUSHES_WITH_GATE', 'SPR_HEDGE_FENCE', 'SPR_HEDGE_BLOOMBUSH_YELLOW', 'SPR_HEDGE_BLOOMBUSH_RED', 'SPR_HEDGE_STONE')):
		first = sym.get(name)
		emit(f'fence_{k + 1}', 'landscape', 'family', name[4:].lower().replace('_', ' '), ['temperate', 'arctic', 'tropic'],
			lambda c, first=first: frames(c, lambda cv, i: cv.add(first + i, 0, 0, 0, 0), range(6)), family='field_fences')

	# Effect vehicles (effectvehicle.cpp): one identity per sprite sequence, a model per frame; the bulldozer is turned.
	for key, label, first, count in EFFECTS:
		base = sym.get(first)
		states = ['default'] if key == 'effect_bulldozer' else [f'frame_{n}' for n in range(count)]
		emit(key, 'effect', 'family', label, all_climates,
			lambda c, base=base, count=count: frames(c, lambda cv, i: cv.add(base + i, 0, 0, 0, 0), range(count), gap=2),
			{'states': states, 'sprite_base': base}, family='effects')

	# Ground props drawn over rocky land (extra GRF overlay rocks).
	rocks = sym.get('SPR_OVERLAY_ROCKS_BASE')
	emit('prop_rocks', 'landscape', 'family', 'Rock clusters', all_climates,
		lambda c: frames(c, lambda cv, i: cv.add(rocks + i, 0, 0, 0, 0, layer=0), range(0, 95, 19)), family='ground_props')

	# Ground textures (flat tile sprites per climate).
	textures = [
		('bare', ['SPR_FLAT_BARE_LAND']),
		('grass', ['SPR_FLAT_1_THIRD_GRASS_TILE', 'SPR_FLAT_2_THIRD_GRASS_TILE', 'SPR_FLAT_GRASS_TILE']),
		('rough', ['SPR_FLAT_ROUGH_LAND', 'SPR_FLAT_ROUGH_LAND_1', 'SPR_FLAT_ROUGH_LAND_2', 'SPR_FLAT_ROUGH_LAND_3', 'SPR_FLAT_ROUGH_LAND_4']),
		('rocks', ['SPR_FLAT_ROCKY_LAND_1', 'SPR_FLAT_ROCKY_LAND_2']),
		('fields', ['SPR_FARMLAND_BARE'] + [f'SPR_FARMLAND_STATE_{i}' for i in range(1, 8)] + ['SPR_FARMLAND_HAYPACKS']),
		('snow_desert', ['SPR_FLAT_1_QUART_SNOW_DESERT_TILE', 'SPR_FLAT_2_QUART_SNOW_DESERT_TILE', 'SPR_FLAT_3_QUART_SNOW_DESERT_TILE', 'SPR_FLAT_SNOW_DESERT_TILE']),
		('water', ['SPR_FLAT_WATER_TILE']),
		('concrete', ['SPR_CONCRETE_GROUND']),
	]
	for name, sprites in textures:
		ids = [sym.get(s) for s in sprites]
		climates = ['arctic', 'tropic'] if name == 'snow_desert' else all_climates
		emit(f'texture_{name}', 'texture', 'texture', name.replace('_', '/'), climates,
			lambda c, ids=ids: frames(c, lambda cv, s: cv.add(s, 0, 0, 0, 0, layer=0), [i for i in ids if i]),
			{'states': [s.lower() for s in sprites]})

	OUT_INV.parent.mkdir(parents=True, exist_ok=True)
	summary = {}
	for e in entries:
		summary.setdefault(e['category'], 0)
		summary[e['category']] += 1
	OUT_INV.write_text(json.dumps({
		'generated_by': 'tools/3d_assets/build_references.py',
		'status_values': ['not_started', 'modelled', 'approved', 'in_game', 'shared'],
		'approaches': ['bespoke', 'kit', 'family', 'texture'],
		'entries': entries,
	}, indent='\t') + '\n', encoding='utf-8')

	missing = set().union(*(s.missing for s in stores.values()))
	for cat, n in summary.items():
		print(f'{cat}: {n}')
	print(f'{len(entries)} entries; {sum(len(e["reference"]) for e in entries)} reference images')
	if missing:
		print(f'{len(missing)} sprites not found in export: {sorted(missing)[:20]}...')


if __name__ == '__main__':
	main()
