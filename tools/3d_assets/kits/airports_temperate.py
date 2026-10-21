"""Temperate airports (Phase 8.6): one model per base airport tile graphic (AirportTiles, airporttile_ids.h).

Exec after house_kit.py and industry_kit.py with KEY set (airport_<name>) and the airport's .blend open. The airport's
layout comes from the inventory; every tile gets a copy of its graphic's model, as for industries, and the converter
keeps the first copy of each graphic. A graphic used by several airports is converted from the first airport in
inventory order; all copies come from the functions here, so they agree.

States: `default` holds every tile; `frame_<n>` holds only the animated tiles at animation frame n (the radar turns
through 12 frames, the wind sock through 4).

Ground: the terrain draws apron concrete, or grass for the tiles in GRASS (the same list is in terrain3d_impl.h).
Taxiway pieces cut the tile along screen-aligned lines (constant u = x + y or v = y - x, measured from the sprites);
the minority ground is a flat overlay. Fences stand on the tile edges in the owner's colour, as the sprites' do.
"""
import json
import math

import bpy

INVENTORY = r"D:\G ttd\OpenTTD-15.3\OpenTTD-15.3\assets\3d\inventory.json"
STATES = ["default"] + [f"frame_{n}" for n in range(1, 12)]
RADAR = (31, 51, 52)
FLAG = (39, 73)
FRAMES = {**{g: 12 for g in RADAR}, **{g: 4 for g in FLAG}}

GRASS = {4, 5, 10, 11, 13, 20, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 73}
G = 0.06  # ground overlay height
M = 0.1   # paint markings

# Taxiway lines. Lines 16 apart continue across tile edges: v = VW in one tile is v = VE in its neighbour.
UN, US = 4.25, 20.25  # constant u = x + y
VW, VE = -7.25, 8.75  # constant v = y - x
U, V = (1, 1), (-1, 1)  # (a, b) with a*x + b*y
# gfx: (overlay material, [region, ...]); a region is a list of half-planes (a, b, c, keep a*x + b*y <= c if
# sign > 0, >= c if sign < 0).
TAXI = {
	4: ("apron", [[(V, VW, 1)]]),
	5: ("apron", [[(U, US, -1)]]),
	6: ("turf", [[(V, VW, 1), (U, US, 1)], [(V, VE, -1), (U, US, 1)]]),
	7: ("turf", [[(U, UN, 1)], [(U, US, -1), (V, VW, -1)]]),
	8: ("turf", [[(V, VW, 1)], [(V, VE, -1)]]),
	9: ("turf", [[(U, UN, 1)], [(U, US, -1), (V, VE, 1)]]),
	10: ("apron", [[(V, VE, -1)]]),
	11: ("apron", [[(U, UN, 1)]]),
	12: ("turf", [[(U, UN, 1)], [(U, US, -1)]]),
	13: ("apron", [[(U, UN, 1)]]),
	71: ("turf", [[(V, 0.0, 1)]]),
	72: ("turf", [[(V, 0.0, -1)]]),
}

FENCES = {
	1: "nw", 2: "sw", 13: "sw", 14: "se", 15: "se", 16: "se", 17: "se", 18: "se", 20: "sw", 25: "nw", 30: "ne",
	31: "sw", 32: "ne", 36: "sw", 39: "ne", 40: "se", 41: "se", 42: "se", 48: "ne", 49: "nw", 50: "nw", 51: "sw",
	52: "ne", 53: "sw", 54: "nw", 56: "ne sw", 57: "nw sw", 58: "se sw", 59: "ne nw", 60: "ne se", 61: "ne se",
	62: "se sw", 63: "ne nw", 64: "nw", 65: "se", 66: "se sw", 67: "nw sw", 68: "nw", 70: "ne se", 73: "ne",
}


# ---------------------------------------------------------------- ground and paint

def clip_halfplane(poly, a, b, c, sign):
	f = lambda p: sign * (c - (a * p[0] + b * p[1]))  # >= 0 keeps
	out = []
	for i, p in enumerate(poly):
		q = poly[(i + 1) % len(poly)]
		fp, fq = f(p), f(q)
		if fp >= 0:
			out.append(p)
		if (fp >= 0) != (fq >= 0):
			t = fp / (fp - fq)
			out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
	return out


def region(p, coll, tag, planes, mat, z=G):
	poly = [(0, 0), (16, 0), (16, 16), (0, 16)]
	for (a, b), c, sign in planes:
		poly = clip_halfplane(poly, a, b, c, sign)
		if len(poly) < 3:
			return
	poly = [(x, y) for x, y in poly]
	area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
	if abs(area) < 0.1:
		return
	if area < 0:
		poly = poly[::-1]
	p.append(_obj(tag, coll, [(x, y, z) for x, y in poly], [tuple(range(len(poly)))], [mat]))


def taxiway(p, coll, tag, gfx):
	mat, regions = TAXI[gfx]
	for k, planes in enumerate(regions):
		region(p, coll, f"{tag}_{mat}{k}", planes, mat)


def fences(p, coll, tag, gfx, h=3.2):
	"""Airport fence on tile edges: posts in the owner's colour, two pale rails."""
	for edge in FENCES.get(gfx, "").split():
		along_x = edge in ("nw", "se")
		c = {"nw": 0.25, "se": 15.75, "ne": 0.25, "sw": 15.75}[edge]
		t = 0.08
		for k, z in enumerate((1.3, h - 0.3)):
			if along_x:
				p.append(box(f"{tag}_{edge}_rail{k}", coll, 0, c - t, z, 16, c + t, z + 0.25, "plaster_white"))
			else:
				p.append(box(f"{tag}_{edge}_rail{k}", coll, c - t, 0, z, c + t, 16, z + 0.25, "plaster_white"))
		for i in range(8):
			a = 1.0 + 2.0 * i
			x, y = (a, c) if along_x else (c, a)
			p.append(box(f"{tag}_{edge}_post{i}", coll, x - 0.17, y - 0.17, 0, x + 0.17, y + 0.17, h, "cc1"))


def paint(p, coll, tag, x0, y0, x1, y1, mat="pitch_line"):
	p.append(slab(tag, coll, x0, y0, x1, y1, mat, M))


def light(p, coll, tag, x, y, mat="lamp_yellow", s=0.3, h=0.5):
	p.append(box(tag, coll, x - s, y - s, 0, x + s, y + s, h, mat))


def stand_marks(p, coll, tag):
	"""Aircraft stand: a broken white box with a yellow lead-in line."""
	w = 0.45
	for k, (a0, a1) in enumerate([(1.2, 7.6), (8.6, 14.8)]):
		paint(p, coll, f"{tag}_n{k}", 1.2, a0, 1.2 + w, a1)
		paint(p, coll, f"{tag}_s{k}", 14.8 - w, a0, 14.8, a1)
		paint(p, coll, f"{tag}_w{k}", a0, 1.2, a1, 1.2 + w)
		paint(p, coll, f"{tag}_e{k}", a0, 14.8 - w, a1, 14.8)
	paint(p, coll, f"{tag}_lead", 7.8, 3.0, 8.2, 13.0, "hazard_yellow")
	paint(p, coll, f"{tag}_stop", 3.0, 12.6, 13.0, 13.0, "hazard_yellow")


def runway(p, coll, tag, end=False, lights=(0.5, 15.5)):
	"""Runway along local X: centre-line dashes, or threshold bars at an end; edge lights once per tile."""
	if end:
		for k, (a, b) in enumerate([(2.0, 3.5), (5.0, 6.5), (9.5, 11.0), (12.5, 14.0)]):
			paint(p, coll, f"{tag}_key{k}", 4.0, a, 11.5, b)
	else:
		for k, (a, b) in enumerate([(1.0, 6.0), (9.0, 14.0)]):
			paint(p, coll, f"{tag}_dash{k}", a, 7.6, b, 8.4)
	for k, y in enumerate(lights):
		light(p, coll, f"{tag}_light{k}", 14.0, y)
		light(p, coll, f"{tag}_light{k}b", 6.0, y, "plaster_white", 0.2, 0.35)


def helipad(p, coll, tag, cx=8.0, cy=8.0, z=0.0, r=4.6, letter=False):
	"""Round pad: white ring, yellow edge lights, and an H when asked."""
	p.append(lathe(f"{tag}_ring", coll, cx, cy, [(z + M, r - 0.6), (z + M, r)], 16, "pitch_line"))
	for i in range(8):
		a = 2 * math.pi * (i + 0.5) / 8
		light(p, coll, f"{tag}_l{i}", cx + (r + 0.9) * math.cos(a), cy + (r + 0.9) * math.sin(a), s=0.25, h=0.4)
		p[-1].location.z = z
	if letter:
		paint(p, coll, f"{tag}_h0", cx - 2.0, cy - 1.6, cx + 2.0, cy - 0.9)
		paint(p, coll, f"{tag}_h1", cx - 2.0, cy + 0.9, cx + 2.0, cy + 1.6)
		paint(p, coll, f"{tag}_h2", cx - 0.35, cy - 0.9, cx + 0.35, cy + 0.9)
		for o in p[-3:]:
			o.location.z = z


# ---------------------------------------------------------------- buildings

def office(p, coll, tag, r, h, floors, base=0.0, wall="plaster_white", band="grain", glass="window_blue", faces="+x-x+y-y"):
	"""Modern block: pale walls, a glazed ribbon per floor, gold floor bands, a flat roof with a parapet."""
	x0, y0, x1, y1 = r
	p.append(box(f"{tag}_body", coll, x0, y0, base, x1, y1, h, wall))
	fh = (h - base - 1.0) / floors
	for i in range(floors):
		z = base + 0.6 + i * fh
		for f, (at, a0, a1) in faces_of(r).items():
			if f in faces:
				p.append(quad(f"{tag}_rib{i}{f}", coll, f, at, a0 + 0.5, a1 - 0.5, z + 0.9, z + fh - 0.5, glass))
		if i:
			p.append(box(f"{tag}_band{i}", coll, x0 - 0.12, y0 - 0.12, z - 0.1, x1 + 0.12, y1 + 0.12, z + 0.35, band))
	p.append(box(f"{tag}_parapet", coll, x0 - 0.15, y0 - 0.15, h - 0.6, x1 + 0.15, y1 + 0.15, h + 0.5, "concrete"))
	p.append(slab(f"{tag}_roof", coll, x0 + 0.3, y0 + 0.3, x1 - 0.3, y1 - 0.3, "concrete_dark", h + 0.1))


def canopy(p, coll, tag, r, z):
	x0, y0, x1, y1 = r
	p.append(box(f"{tag}", coll, x0, y0, z, x1, y1, z + 0.35, "cc1"))
	for k, (x, y) in enumerate([(x0 + 0.3, y0 + 0.3), (x1 - 0.3, y0 + 0.3), (x1 - 0.3, y1 - 0.3), (x0 + 0.3, y1 - 0.3)]):
		p.append(box(f"{tag}_post{k}", coll, x - 0.1, y - 0.1, 0, x + 0.1, y + 0.1, z, "steel_light"))


def skylight(p, coll, tag, x, y, z, s=2.0):
	p.append(box(f"{tag}", coll, x - s, y - s, z, x + s, y + s, z + 1.0, "concrete"))
	p.append(slab(f"{tag}_glass", coll, x - s + 0.4, y - s + 0.4, x + s - 0.4, y + s - 0.4, "cc1", z + 1.05))


def beacons(p, coll, tag, pts, z, h=1.6):
	for k, (x, y) in enumerate(pts):
		p.append(box(f"{tag}{k}", coll, x - 0.1, y - 0.1, z, x + 0.1, y + 0.1, z + h, "steel"))
		p.append(box(f"{tag}{k}_lamp", coll, x - 0.22, y - 0.22, z + h, x + 0.22, y + 0.22, z + h + 0.4, "signal_red"))


CORRIDOR = (6.6, 10.4)  # passenger corridors and jetways


def corridor(p, coll, tag, a, b, z0=CORRIDOR[0], z1=CORRIDOR[1], w=2.4):
	"""Glazed passenger corridor from a to b (x, y): pale body, a blue window band, a roof in the owner's colour."""
	h = z1 - z0
	p.append(beam(f"{tag}_body", coll, (*a, z0 + h / 2), (*b, z0 + h / 2), w, h, "plaster_white"))
	p.append(beam(f"{tag}_win", coll, (*a, z0 + h * 0.55), (*b, z0 + h * 0.55), w + 0.12, h * 0.42, "window_blue"))
	p.append(beam(f"{tag}_roof", coll, (*a, z1 + 0.15), (*b, z1 + 0.15), w + 0.2, 0.3, "cc1"))


def pillar(p, coll, tag, x, y, z, s=0.45, wheels=False):
	p.append(box(f"{tag}", coll, x - s, y - s, 0, x + s, y + s, z, "steel_light"))
	if wheels:
		p.append(box(f"{tag}_bogie", coll, x - 1.0, y - 0.6, 0.2, x + 1.0, y + 0.6, 1.0, "rubber"))


def jetway(p, coll, tag, pts):
	"""Jetway: corridor along pts, a rotunda at the bend on a pillar, a drive bogie under the cab end."""
	for k, (a, b) in enumerate(zip(pts, pts[1:])):
		corridor(p, coll, f"{tag}_seg{k}", a, b, w=2.0)
	bx, by = pts[1]
	p.append(box(f"{tag}_rot", coll, bx - 1.4, by - 1.4, CORRIDOR[0] - 0.2, bx + 1.4, by + 1.4, CORRIDOR[1] + 0.3, "plaster_white"))
	pillar(p, coll, f"{tag}_pil", bx, by, CORRIDOR[0] - 0.2, 0.6)
	ex, ey = pts[-1]
	pillar(p, coll, f"{tag}_leg", ex, ey, CORRIDOR[0], 0.3, wheels=True)


def control_tower(p, coll, tag, ground):
	"""Base block, round shaft, glazed octagonal cab with an overhanging roof and antennas."""
	office(p, coll, f"{tag}_base", (3.0, 3.0, 13.0, 13.0), 8.0, 1)
	canopy(p, coll, f"{tag}_porch", (12.8, 9.0, 14.6, 12.6), 3.0)
	p.append(prism(f"{tag}_shaft", coll, 8, 8, 2.2, 8.6, 43.0, 10, "plaster_white"))
	p.append(lathe(f"{tag}_cab", coll, 8, 8, [(43.0, 2.4), (44.0, 5.8), (45.0, 6.2), (49.5, 6.6), (50.2, 6.0), (51.4, 5.0)], 8,
	               ["concrete", "plaster_white", "window_blue", "cc1", "concrete"], cap="concrete_dark", phase=math.pi / 8))
	p.append(lathe(f"{tag}_band", coll, 8, 8, [(45.6, 6.32), (46.0, 6.32)], 8, "grain", phase=math.pi / 8))
	beacons(p, coll, f"{tag}_ant", [(6.8, 7.2), (9.2, 8.8), (8.0, 9.6)], 51.4, 4.5)
	p.append(box(f"{tag}_radome", coll, 7.2, 6.6, 51.4, 8.6, 8.0, 52.6, "plaster_white"))


def hangar(p, coll, tag):
	"""Large aircraft hangar: corrugated walls, a barrel roof with skylights along it, the door open towards +Y."""
	x0, x1, y0, y1, h, rise = 0.4, 15.6, 0.4, 15.4, 15.0, 12.0
	p.append(box(f"{tag}_wall_l", coll, x0, y0, 0, x0 + 1.0, y1, h, "steel_light"))
	p.append(box(f"{tag}_wall_r", coll, x1 - 1.0, y0, 0, x1, y1, h, "steel_light"))
	p.append(box(f"{tag}_wall_back", coll, x0 + 1.0, y0, 0, x1 - 1.0, y0 + 0.8, h, "steel_light"))
	p.append(box(f"{tag}_lintel", coll, x0 + 1.0, y1 - 0.8, h - 2.0, x1 - 1.0, y1, h, "steel_light"))
	p.append(vault(f"{tag}_roof", coll, x0, y0, x1, y1, h, rise, "steel_light", 'y', 8, "steel_light"))
	for f, at in (("+x", x1), ("-x", x0)):
		for k in range(9):
			a = y0 + 0.6 + (y1 - y0 - 1.2) * k / 8
			p.append(quad(f"{tag}_rib{f}{k}", coll, f, at, a - 0.15, a + 0.15, 0, h, "steel", 0.1))
		p.append(quad(f"{tag}_win{f}", coll, f, at, y0 + 2.0, y1 - 2.0, 9.5, 11.5, "window_blue", 0.12))
	for k, frac in enumerate((0.3, 0.5, 0.7)):  # skylights along the barrel
		a = math.pi * frac
		x = x0 + (x1 - x0) * (1 - math.cos(a)) / 2
		z = h + rise * math.sin(a)
		p.append(beam(f"{tag}_sky{k}", coll, (x, y0 + 0.6, z + 0.1), (x, y1 - 0.6, z + 0.1), 2.2, 0.2, "cc1"))
	p.append(slab(f"{tag}_floor", coll, x0 + 1.0, y0 + 0.8, x1 - 1.0, y1, "concrete_dark", 0.05))
	p.append(box(f"{tag}_door_l", coll, x0 + 1.0, y1 - 0.6, 0, x0 + 2.4, y1, h - 2.0, "cc1"))
	p.append(box(f"{tag}_door_r", coll, x1 - 2.4, y1 - 0.6, 0, x1 - 1.0, y1, h - 2.0, "cc1"))


def small_hangar(p, coll, tag):
	"""Airfield hangar: brick walls with windows, a dark gable roof, the door open towards +Y."""
	x0, x1, y0, y1, h = 0.8, 15.2, 0.6, 15.4, 11.0
	p.append(box(f"{tag}_wall_l", coll, x0, y0, 0, x0 + 0.9, y1, h, "brick"))
	p.append(box(f"{tag}_wall_r", coll, x1 - 0.9, y0, 0, x1, y1, h, "brick"))
	p.append(box(f"{tag}_wall_back", coll, x0 + 0.9, y0, 0, x1 - 0.9, y0 + 0.9, h, "brick"))
	p.append(box(f"{tag}_lintel", coll, x0 + 0.9, y1 - 0.9, h - 1.5, x1 - 0.9, y1, h, "brick"))
	p.append(gable(f"{tag}_roof", coll, x0, y0, x1, y1, h, h + 10.0, "roof_dark", 'y', 0.5, "brick"))
	p.append(slab(f"{tag}_floor", coll, x0 + 0.9, y0 + 0.9, x1 - 0.9, y1, "concrete_dark", 0.05))
	for f, at in (("+x", x1), ("-x", x0)):
		for k, a in enumerate((3.0, 6.5, 10.0, 13.0)):
			p.append(quad(f"{tag}_win{f}{k}", coll, f, at, a - 0.7, a + 0.7, 3.0, 6.0, "window_blue"))
	p.append(box(f"{tag}_door", coll, x0 + 0.9, y1 - 0.5, h - 4.0, x1 - 0.9, y1 - 0.2, h - 1.5, "cc1"))  # door rolled up


# ---------------------------------------------------------------- tiles

def t_none(coll, tag, f):
	return []


def t_fenced(coll, tag, f, gfx):
	p = []
	fences(p, coll, tag, gfx)
	return p


def t_stand(coll, tag, f, gfx):
	p = []
	stand_marks(p, coll, tag)
	fences(p, coll, tag, gfx)
	if gfx == 25:
		jetway(p, coll, f"{tag}_jet", [(8.6, 16.0), (8.6, 12.4), (11.6, 11.2)])
	if gfx == 26:
		jetway(p, coll, f"{tag}_jet", [(0.0, 8.6), (4.2, 8.6), (6.2, 5.6)])
	return p


def t_pier_nw_ne(coll, tag, f):
	p = []
	jetway(p, coll, f"{tag}_jet", [(4.6, 0.0), (4.6, 4.2), (2.4, 7.2)])
	return p


def t_pier(coll, tag, f):
	p = []
	corridor(p, coll, f"{tag}_tunnel", (0.0, 9.5), (16.0, 9.5))
	for k, x in enumerate((4.0, 12.0)):
		pillar(p, coll, f"{tag}_pil{k}", x, 9.5, CORRIDOR[0], 0.5)
	return p


def t_taxi(coll, tag, f, gfx):
	p = []
	taxiway(p, coll, tag, gfx)
	fences(p, coll, tag, gfx)
	return p


def t_runway(coll, tag, f, gfx):
	p = []
	end = gfx in (18, 45, 49, 57, 58, 59, 60)
	runway(p, coll, tag, end)
	fences(p, coll, tag, gfx)
	return p


def t_building_2(coll, tag, f):
	"""Terminal A: a four-storey block with a taller operations tower at its north-east end."""
	p = []
	office(p, coll, f"{tag}_main", (1.6, 0.6, 15.0, 15.4), 24.0, 4)
	office(p, coll, f"{tag}_tower", (2.4, 9.6, 8.4, 15.0), 39.0, 3, base=24.0)
	beacons(p, coll, f"{tag}_lamp", [(2.6, 9.8), (8.2, 9.8), (8.2, 14.8), (2.6, 14.8)], 39.5, 0.8)
	for k in range(4):  # roof plant grilles
		x = 3.6 + 2.6 * k
		p.append(box(f"{tag}_vent{k}", coll, x, 2.0, 24.6, x + 1.6, 7.6, 25.8, "steel"))
	canopy(p, coll, f"{tag}_canopy", (15.0, 3.0, 16.0, 13.0), 4.0)
	return p


def t_round_terminal(coll, tag, f):
	"""Concourse: a square three-storey hub carrying a round drum with lights and antennas."""
	p = []
	office(p, coll, f"{tag}_hub", (0.6, 0.6, 15.4, 15.4), 18.0, 3)
	p.append(lathe(f"{tag}_drum", coll, 8, 8, [(18.6, 5.0), (22.0, 5.0), (22.4, 5.4), (24.0, 5.4), (24.4, 4.4)], 12,
	               ["window_blue", "grain", "plaster_white", "concrete"], cap="concrete_dark"))
	beacons(p, coll, f"{tag}_ant", [(7.0, 7.2), (9.0, 8.8), (8.0, 9.6), (9.6, 7.0)], 24.4, 3.0)
	return p


def t_building_3(coll, tag, f):
	p = []
	office(p, coll, f"{tag}_main", (3.0, 3.0, 13.0, 14.0), 26.0, 4)
	skylight(p, coll, f"{tag}_sky", 8.0, 8.5, 26.5)
	canopy(p, coll, f"{tag}_canopy", (13.0, 9.0, 14.8, 13.4), 4.0)
	return p


def t_building_1(coll, tag, f):
	p = []
	office(p, coll, f"{tag}_main", (0.6, 3.0, 15.4, 14.0), 21.0, 3)
	skylight(p, coll, f"{tag}_sky", 6.0, 8.5, 21.5, 2.4)
	canopy(p, coll, f"{tag}_canopy", (15.4, 4.0, 16.0, 9.0), 4.0)
	return p


def t_depot(coll, tag, f):
	p = []
	hangar(p, coll, tag)
	return p


def t_small_depot(coll, tag, f):
	p = []
	small_hangar(p, coll, tag)
	return p


def t_tower(coll, tag, f, gfx):
	p = []
	control_tower(p, coll, tag, gfx == 20)
	fences(p, coll, tag, gfx)
	return p


def t_radar(coll, tag, f, gfx):
	"""Surveillance radar: striped mast, a turning antenna (30 degrees per animation frame)."""
	p = []
	p.append(box(f"{tag}_base", coll, 6.6, 6.6, 0, 9.4, 9.4, 1.6, "concrete"))
	for k in range(6):
		p.append(prism(f"{tag}_mast{k}", coll, 8, 8, 0.6, 1.6 + 2.6 * k, 4.2 + 2.6 * k, 6,
		               "signal_red" if k % 2 == 0 else "plaster_white"))
	p.append(prism(f"{tag}_head", coll, 8, 8, 0.9, 17.2, 18.4, 6, "steel"))
	a = 2 * math.pi * f / 12
	ca, sa = math.cos(a), math.sin(a)
	p.append(beam(f"{tag}_dish", coll, (8 - 3.6 * ca, 8 - 3.6 * sa, 19.6), (8 + 3.6 * ca, 8 + 3.6 * sa, 19.6), 0.5, 2.4, "plaster_white"))
	p.append(beam(f"{tag}_feed", coll, (8, 8, 18.6), (8 - 1.6 * sa, 8 + 1.6 * ca, 19.2), 0.3, 0.3, "steel"))
	fences(p, coll, tag, gfx)
	return p


def t_radio(coll, tag, f, gfx):
	"""Lattice radio mast with guy wires and microwave dishes at the top."""
	p = []
	H = 68.0
	legs = [(6.4, 6.4), (9.6, 6.4), (9.6, 9.6), (6.4, 9.6)]
	top = [(7.4, 7.4), (8.6, 7.4), (8.6, 8.6), (7.4, 8.6)]
	for k, (b, t) in enumerate(zip(legs, top)):
		p.append(beam(f"{tag}_leg{k}", coll, (*b, 0), (*t, H), 0.35, 0.35, "steel_light"))
	for j in range(1, 7):  # braces round the mast every few metres
		z = H * j / 7
		s = 1.6 - 1.0 * j / 7
		p.append(lathe(f"{tag}_ring{j}", coll, 8, 8, [(z, s * 1.41), (z + 0.3, s * 1.41)], 4, "steel_light", phase=math.pi / 4))
	for k, (x, y) in enumerate([(1.0, 1.0), (15.0, 15.0), (15.0, 1.0)]):
		p.append(beam(f"{tag}_guy{k}", coll, (x, y, 0.2), (8, 8, H * 0.7), 0.1, 0.1, "steel"))
		p.append(box(f"{tag}_anchor{k}", coll, x - 0.4, y - 0.4, 0, x + 0.4, y + 0.4, 0.4, "concrete"))
	for k, (dx, dy) in enumerate([(1, 0), (0, 1), (-0.7, -0.7)]):
		cx, cy = 8 + 2.0 * dx, 8 + 2.0 * dy
		ob = lathe(f"{tag}_dish{k}", coll, 0, 0, [(0.0, 0.0), (1.0, 2.6), (1.5, 3.2)], 10, "steel", cap="concrete_dark")
		ob.rotation_euler = (0, math.pi / 2, math.atan2(dy, dx))
		ob.location = (cx, cy, H - 4.0 - k * 2.0)
		p.append(ob)
	beacons(p, coll, f"{tag}_tip", [(8.0, 8.0)], H, 3.0)
	fences(p, coll, tag, gfx)
	return p


def t_brick_house(coll, tag, f):
	"""Airfield office: a brick cottage with a hipped roof."""
	p = []
	p.append(box(f"{tag}_body", coll, 4.0, 4.0, 0, 11.6, 11.0, 7.0, "brick"))
	p.append(hip(f"{tag}_roof", coll, 3.6, 3.6, 12.0, 11.4, 7.0, 11.0, "roof_slate", 2.5))
	windows(p, coll, f"{tag}_w", (4.0, 4.0, 11.6, 11.0), [2.6], "+x+y-x-y", 1.2, 2.0, 3.4)
	p.append(quad(f"{tag}_door", coll, "+x", 11.6, 6.6, 7.8, 0, 3.6, "wood_dark"))
	p.append(box(f"{tag}_chimney", coll, 9.0, 5.0, 8.0, 10.0, 6.0, 12.4, "brick_dark"))
	return p


def t_brick_sheds(coll, tag, f):
	"""Airfield workshop: a round-roofed hut and a brick store."""
	p = []
	p.append(box(f"{tag}_hut", coll, 7.6, 1.0, 0, 14.6, 8.4, 3.5, "steel_light"))
	p.append(vault(f"{tag}_hut_roof", coll, 7.6, 1.0, 14.6, 8.4, 3.5, 3.4, "steel_light", 'y', 6, "concrete"))
	p.append(quad(f"{tag}_hut_door", coll, "+y", 8.4, 9.6, 12.6, 0, 3.0, "wood_dark"))
	p.append(box(f"{tag}_store", coll, 2.0, 7.4, 0, 9.0, 14.6, 7.0, "brick"))
	p.append(gable(f"{tag}_store_roof", coll, 2.0, 7.4, 9.0, 14.6, 7.0, 10.0, "roof_slate", 'x', 0.4, "brick"))
	windows(p, coll, f"{tag}_w", (2.0, 7.4, 9.0, 14.6), [2.6], "+x+y-x-y", 1.2, 2.0, 3.4)
	return p


def t_airfield_office(coll, tag, f):
	"""Airfield control: a brick tower with a glazed top and masts, a low wing, and a checkered water tank."""
	p = []
	p.append(slab(f"{tag}_yard", coll, 1.0, 1.0, 14.6, 8.4, "apron", G))
	p.append(box(f"{tag}_tower", coll, 1.4, 1.4, 0, 7.0, 7.0, 13.0, "brick"))
	windows(p, coll, f"{tag}_tw", (1.4, 1.4, 7.0, 7.0), [3.0, 7.0], "+x+y-x-y", 1.0, 2.0, 2.6)
	p.append(box(f"{tag}_cab", coll, 1.2, 1.2, 13.0, 7.2, 7.2, 15.6, "window_blue"))
	p.append(box(f"{tag}_cab_roof", coll, 0.9, 0.9, 15.6, 7.5, 7.5, 16.3, "concrete"))
	beacons(p, coll, f"{tag}_mast", [(2.0, 2.4), (4.2, 2.0), (6.4, 2.4)], 16.3, 3.6)
	p.append(box(f"{tag}_wing", coll, 7.0, 2.0, 0, 12.4, 9.0, 7.0, "brick"))
	p.append(slab(f"{tag}_wing_roof", coll, 7.0, 2.0, 12.4, 9.0, "concrete_dark", 7.1))
	windows(p, coll, f"{tag}_ww", (7.0, 2.0, 12.4, 9.0), [2.6], "+x+y", 1.2, 2.0, 2.8)
	for k, (x, y) in enumerate([(9.8, 10.2), (13.2, 10.2), (13.2, 13.6), (9.8, 13.6)]):
		p.append(box(f"{tag}_tleg{k}", coll, x - 0.2, y - 0.2, 0, x + 0.2, y + 0.2, 4.4, "steel"))
	p.append(lathe(f"{tag}_tank", coll, 11.5, 11.9, [(4.4, 2.6), (6.6, 2.6), (8.8, 2.6), (11.0, 2.6), (11.8, 1.6)], 8,
	               ["cc1", "plaster_white", "cc1", "concrete"], cap="concrete"))
	return p


def t_grass(coll, tag, f, gfx):
	p = []
	if gfx in (36, 37, 38, 39):  # worn wheel tracks across the airfield grass
		for k, (a, b) in enumerate([(5.0, 6.2), (9.8, 11.0)]):
			p.append(slab(f"{tag}_track{k}", coll, 0, a, 16, b, "dirt", G))
	fences(p, coll, tag, gfx)
	return p


def t_strip(coll, tag, f, gfx):
	"""Grass airstrip: a worn dirt strip along X with marker cones at the edges."""
	p = []
	x0, x1 = {40: (0.0, 15.0), 41: (0.0, 16.0), 42: (1.0, 16.0)}[gfx]
	p.append(slab(f"{tag}_dirt", coll, x0, 2.0, x1, 15.2, "dirt", G))
	for k, x in enumerate((4.0, 12.0)):
		for j, y in enumerate((1.4, 15.0)):
			if x0 <= x <= x1:
				p.append(lathe(f"{tag}_cone{k}{j}", coll, x, y - 0.6 if j else y, [(0.0, 0.35), (0.8, 0.0)], 5, "paint_orange"))
	if gfx in (40, 42):  # end markers across the strip
		x = x1 - 1.0 if gfx == 40 else x0 + 1.0
		paint(p, coll, f"{tag}_end", x - 0.4, 3.0, x + 0.4, 14.2)
	fences(p, coll, tag, gfx)
	return p


def t_flag(coll, tag, f, gfx):
	"""Wind sock on a pole at the east corner; it swings through the animation frames."""
	p = []
	px, py = 1.0, 14.8
	p.append(box(f"{tag}_pole", coll, px - 0.15, py - 0.15, 0, px + 0.15, py + 0.15, 20.0, "steel_light"))
	a = math.radians(20 + 15 * f)  # swings from pointing along -y towards +x, staying on the tile
	droop = (0.0, 1.2, 0.6, 1.6)[f % 4]
	n, L = 4, 6.0
	for k in range(n):
		t0, t1 = k / n, (k + 1) / n
		pa = (px + L * t0 * math.sin(a), py - L * t0 * math.cos(a), 19.0 - droop * t0 * t0)
		pb = (px + L * t1 * math.sin(a), py - L * t1 * math.cos(a), 19.0 - droop * t1 * t1)
		r = 1.0 - 0.45 * (t0 + t1) / 2
		p.append(beam(f"{tag}_sock{k}", coll, pa, pb, r * 1.6, r * 1.6, "paint_orange" if k % 2 == 0 else "plaster_white"))
	fences(p, coll, tag, gfx)
	return p


def t_heliport(coll, tag, f):
	"""City heliport: a podium and a chamfered office tower with the pad on its roof at z = 60."""
	p = []
	office(p, coll, f"{tag}_podium", (0.4, 0.4, 15.6, 15.6), 20.0, 3)
	canopy(p, coll, f"{tag}_canopy", (15.6, 5.0, 16.0, 11.0), 4.0)
	r = [(1.6, 4.0), (4.0, 1.6), (12.0, 1.6), (14.4, 4.0), (14.4, 12.0), (12.0, 14.4), (4.0, 14.4), (1.6, 12.0)]
	ring = lambda z, d: [(x + (d if x < 8 else -d), y + (d if y < 8 else -d), z) for x, y in r]
	v, fc, mats = [], [], []
	for z in (20.0, 58.0):
		v += ring(z, 0.0)
	for i in range(8):
		j = (i + 1) % 8
		fc.append((i, j, 8 + j, 8 + i)); mats.append("plaster_white")
	fc.append(tuple(range(8, 16))); mats.append("concrete_dark")
	p.append(_obj(f"{tag}_tower", coll, v, fc, mats))
	for k in range(6):
		z = 21.0 + 6.0 * k
		gv = ring(z + 0.8, -0.06) + ring(z + 4.6, -0.06)
		gf = [(i, (i + 1) % 8, 8 + (i + 1) % 8, 8 + i) for i in range(8)]
		p.append(_obj(f"{tag}_glass{k}", coll, gv, gf, ["window_blue"] * 8))
	p.append(_obj(f"{tag}_deck", coll, ring(58.0, -0.3) + ring(60.0, -0.3),
	              [(i, (i + 1) % 8, 8 + (i + 1) % 8, 8 + i) for i in range(8)] + [tuple(range(8, 16))], ["concrete"] * 8 + ["concrete_dark"]))
	helipad(p, coll, f"{tag}_pad", z=60.0, r=4.4, letter=True)
	return p


def t_helipad(coll, tag, f, gfx):
	p = []
	if gfx in (66, 67, 68):
		helipad(p, coll, f"{tag}_pad", 8.0, 8.0, 0.0, 5.0, letter=True)
	else:
		helipad(p, coll, f"{tag}_pad", 8.0, 8.0, 0.0, 4.6)
	fences(p, coll, tag, gfx)
	return p


def t_low_building(coll, tag, f, gfx):
	"""Helidepot office: a two-storey block with a rooftop plant room."""
	p = []
	office(p, coll, f"{tag}_main", (3.0, 3.0, 13.0, 13.0), 10.0, 2)
	p.append(box(f"{tag}_plant", coll, 5.0, 6.5, 10.5, 9.5, 11.0, 12.6, "concrete"))
	p.append(slab(f"{tag}_plant_top", coll, 5.4, 6.9, 9.1, 10.6, "cc1", 12.65))
	canopy(p, coll, f"{tag}_canopy", (13.0, 6.0, 14.8, 10.0), 3.4)
	fences(p, coll, tag, gfx)
	return p


GFX = {0: t_none, 3: lambda c, t, f: t_stand(c, t, f, 3), 19: t_building_2, 21: t_round_terminal, 22: t_building_3,
       23: t_building_1, 24: t_depot, 27: t_pier_nw_ne, 28: t_pier, 29: t_none, 33: t_brick_house, 34: t_brick_sheds,
       35: t_airfield_office, 43: t_small_depot, 44: t_heliport}
for _g in (1, 2, 30, 48, 56, 62, 65, 70):
	GFX[_g] = (lambda g: lambda c, t, f: t_fenced(c, t, f, g))(_g)
for _g in TAXI:
	GFX[_g] = (lambda g: lambda c, t, f: t_taxi(c, t, f, g))(_g)
for _g in (14, 15, 16, 17, 18, 45, 46, 49, 50, 57, 58, 59, 60):
	GFX[_g] = (lambda g: lambda c, t, f: t_runway(c, t, f, g))(_g)
for _g in (25, 26):
	GFX[_g] = (lambda g: lambda c, t, f: t_stand(c, t, f, g))(_g)
for _g in (20, 47):
	GFX[_g] = (lambda g: lambda c, t, f: t_tower(c, t, f, g))(_g)
for _g in RADAR:
	GFX[_g] = (lambda g: lambda c, t, f: t_radar(c, t, f, g))(_g)
GFX[32] = lambda c, t, f: t_radio(c, t, f, 32)
for _g in (36, 37, 38):
	GFX[_g] = (lambda g: lambda c, t, f: t_grass(c, t, f, g))(_g)
for _g in (40, 41, 42):
	GFX[_g] = (lambda g: lambda c, t, f: t_strip(c, t, f, g))(_g)
for _g in FLAG:
	GFX[_g] = (lambda g: lambda c, t, f: t_flag(c, t, f, g))(_g)
for _g in (53, 54, 55, 61, 66, 67, 68):
	GFX[_g] = (lambda g: lambda c, t, f: t_helipad(c, t, f, g))(_g)
for _g in (63, 64, 69):
	GFX[_g] = (lambda g: lambda c, t, f: t_low_building(c, t, f, g))(_g)


# ---------------------------------------------------------------- build

def preview_ground(layout):
	"""Terrain stand-in for review renders (never exported): grass or apron per tile, as the game chooses."""
	coll = bpy.data.collections.get("_ground") or bpy.data.collections.new("_ground")
	if coll.name not in bpy.data.scenes["model"].collection.children:
		bpy.data.scenes["model"].collection.children.link(coll)
	clear(coll)
	for tx, ty, g in layout:
		ob = slab(f"_g{tx}_{ty}", coll, 0, 0, 16, 16, "turf" if g in GRASS else "apron", 0.0)
		ob.location = (16 * tx, 16 * ty, 0)


def build_airport(layout):
	"""Rebuild every state collection. Returns the largest triangle count per gfx."""
	out = {}
	scene_root = bpy.data.scenes["model"].collection
	for st in STATES:
		coll = state_coll(st)
		if coll.name not in scene_root.children:  # unlinked by an earlier build
			scene_root.children.link(coll)
		clear(coll)
		frame = 0 if st == "default" else int(st.split("_")[1])
		for tx, ty, g in layout:
			if frame and FRAMES.get(g, 0) <= frame:
				continue
			parts = GFX[g](coll, f"t{tx}_{ty}_g{g}", frame)
			if not parts:
				continue
			ob = join(f"t{tx}_{ty}_g{g}", parts)
			ob.location = (16 * tx, 16 * ty, 0)
			out[g] = max(out.get(g, 0), tris(ob))
	for st in STATES:  # frame states that hold nothing are not exported
		c = bpy.data.collections[st]
		if not c.objects and c.name in scene_root.children:
			scene_root.children.unlink(c)
	return out


sync_palette()
entry = next(e for e in json.load(open(INVENTORY, encoding="utf-8"))["entries"] if e["key"] == KEY)
LAYOUT = [tuple(t) for t in entry["layout"]]
preview_ground(LAYOUT)
result = build_airport(LAYOUT)
