"""Temperate map objects, field fences and rock props (Phase 8.6).

Exec after house_kit.py with KEY set and the identity's .blend open. Each builder returns the parts of the one
`default` state; they are joined into a single object.
- Objects stand on the tile (company HQs on 2x2, origin at the north tile); `cc1` is the owner's colour.
- Fences are one tile edge: along local X on the y = 0 side, inside the tile. The renderer turns the model for each side
  and keeps every vertex at its height above the sloped field.
- Rocks are one cluster for the whole tile, also laid on the slope; the renderer turns it by the tile hash.
"""
import math
import random

import bpy
from mathutils import Vector


def dish(name, coll, c, normal, r, depth, mat, n=8):
    """Shallow dish: a rim disc facing `normal` with a cone behind it."""
    nrm = Vector(normal).normalized()
    a = nrm.cross(Vector((0, 0, 1)))
    if a.length < 1e-6:
        a = Vector((1, 0, 0))
    a.normalize(); b = nrm.cross(a)
    C = Vector(c)
    v = [tuple(C + (a * math.cos(2 * math.pi * i / n) + b * math.sin(2 * math.pi * i / n)) * r) for i in range(n)]
    v.append(tuple(C - nrm * depth))
    f = [tuple(range(n))] + [((i + 1) % n, i, n) for i in range(n)]
    return _obj(name, coll, v, f, [mat] * len(f))


def rock(name, coll, x, y, r, h, mat, n=5, phase=0.0):
    return lathe(name, coll, x, y, [(0, r), (h * 0.6, r * 0.85), (h, r * 0.45)], n, mat, cap=mat, phase=phase)


def flag(parts, coll, tag, x, y, h, length=3.0, drop=2.0):
    """Flag pole with a company-coloured flag flying towards +Y."""
    parts.append(box(f"{tag}_pole", coll, x - 0.15, y - 0.15, 0, x + 0.15, y + 0.15, h, "steel_light"))
    parts.append(box(f"{tag}_flag", coll, x - 0.06, y + 0.15, h - drop - 0.3, x + 0.06, y + 0.15 + length, h - 0.3, "cc1"))


def walls(parts, coll, tag, r, h, mat, t=0.6, gaps=()):
    """Low boundary wall round a rectangle; gaps are (side, a0, a1) openings along '+x', '-x', '+y' or '-y'."""
    x0, y0, x1, y1 = r
    sides = {'-y': (x0, y0, x1, y0 + t, 'x'), '+y': (x0, y1 - t, x1, y1, 'x'), '-x': (x0, y0 + t, x0 + t, y1 - t, 'y'), '+x': (x1 - t, y0 + t, x1, y1 - t, 'y')}
    for name, (a, b, c, d, ax) in sides.items():
        cuts = sorted((g[1], g[2]) for g in gaps if g[0] == name)
        lo, hi = (a, c) if ax == 'x' else (b, d)
        spans, cur = [], lo
        for g0, g1 in cuts:
            spans.append((cur, g0)); cur = g1
        spans.append((cur, hi))
        for k, (s0, s1) in enumerate(spans):
            if s1 - s0 < 0.1:
                continue
            if ax == 'x':
                parts.append(box(f"{tag}_wall{name}{k}", coll, s0, b, 0, s1, d, h, mat))
            else:
                parts.append(box(f"{tag}_wall{name}{k}", coll, a, s0, 0, c, s1, h, mat))


def parking(parts, coll, tag, x0, x1, y0, y1, step=3.0, along='y'):
    """White bay lines painted on a car park."""
    n = int((y1 - y0 if along == 'y' else x1 - x0) // step) + 1
    for i in range(n):
        if along == 'y':
            y = y0 + i * step
            parts.append(slab(f"{tag}_bay{i}", coll, x0, y - 0.15, x1, y + 0.15, "plaster_white", 0.14))
        else:
            x = x0 + i * step
            parts.append(slab(f"{tag}_bay{i}", coll, x - 0.15, y0, x + 0.15, y1, "plaster_white", 0.14))


def planter(parts, coll, tag, r, seed):
    x0, y0, x1, y1 = r
    parts.append(box(f"{tag}_kerb", coll, x0, y0, 0, x1, y1, 0.6, "concrete"))
    parts.append(box(f"{tag}_bed", coll, x0 + 0.4, y0 + 0.4, 0, x1 - 0.4, y1 - 0.4, 0.75, "grass"))
    rnd = random.Random(seed)
    flowers(parts, coll, tag, [(rnd.uniform(x0 + 0.8, x1 - 0.8), rnd.uniform(y0 + 0.8, y1 - 0.8)) for _ in range(6)])
    for p in parts[-6:]:
        p.location.z += 0.6


# ---------------------------------------------------------------- map objects

def object_transmitter(coll):
    p, c, w, top = [], 8.0, 1.3, 54
    corners = [(c - w, c - w), (c + w, c - w), (c + w, c + w), (c - w, c + w)]
    p += [beam(f"post{k}", coll, (x, y, 0), (x, y, top), 0.35, 0.35, "steel_light") for k, (x, y) in enumerate(corners)]
    levels = [0.5 + 10.7 * k for k in range(6)]
    for f in range(4):  # one zigzag per face
        (ax, ay), (bx, by) = corners[f], corners[(f + 1) % 4]
        for k, (z0, z1) in enumerate(zip(levels, levels[1:])):
            s, e = ((ax, ay), (bx, by)) if k % 2 == 0 else ((bx, by), (ax, ay))
            p.append(beam(f"brace{f}_{k}", coll, (*s, z0), (*e, z1), 0.2, 0.2, "steel_light"))
    p.append(box("platform", coll, c - 2.2, c - 2.2, top, c + 2.2, c + 2.2, top + 0.6, "steel"))
    for k in range(3):  # dishes facing out over the platform
        a = math.radians(45 + 120 * k)
        d = (math.cos(a), math.sin(a), 0.15)
        p.append(dish(f"dish{k}", coll, (c + 3.0 * d[0], c + 3.0 * d[1], top + 4.0), d, 3.6, 1.5, "stone_dark"))
    p.append(beam("mast", coll, (c, c, top + 0.6), (c, c, top + 10), 0.3, 0.3, "steel_light"))
    p += [box(f"light{k}", coll, c + w - 0.3, c + w - 0.3, z, c + w + 0.4, c + w + 0.4, z + 0.6, "signal_red") for k, z in enumerate((22, 40))]
    p.append(box("toplight", coll, c - 0.3, c - 0.3, top + 10, c + 0.3, c + 0.3, top + 10.6, "signal_red"))
    p += [beam(f"guy{k}", coll, (x, y, 44), (0.6 + 14.8 * (x > c), 0.6 + 14.8 * (y > c), 0), 0.1, 0.1, "steel_light") for k, (x, y) in enumerate(corners)]
    p.append(box("base", coll, c - 2, c - 2, 0, c + 2, c + 2, 0.5, "concrete"))
    return p


def object_lighthouse(coll):
    p, tx, ty = [], 5.6, 11.0
    p.append(lathe("tower", coll, tx, ty, [(0, 3.0), (11, 2.85), (19, 2.7), (29, 2.55), (34, 2.45)], 10,
                   ["plaster_white", "stone_dark", "plaster_white", "stone_dark"]))
    p.append(lathe("gallery", coll, tx, ty, [(34, 2.45), (34, 3.2), (34.6, 3.2), (35.6, 3.2)], 10, ["black", "black", "steel"]))
    p.append(lathe("lantern", coll, tx, ty, [(34.6, 1.9), (37.4, 1.9), (38.4, 1.9)], 8, ["lamp_yellow", "glass_dark"]))
    p.append(lathe("dome", coll, tx, ty, [(38.4, 2.3), (39.6, 1.8), (41.2, 0.5), (41.2, 0)], 8, "stone_dark"))
    p.append(beam("vent", coll, (tx, ty, 41), (tx, ty, 42.6), 0.3, 0.3, "black"))
    p += [quad(f"slit{k}", coll, '+x', tx + 2.75 - 0.2 * k, ty - 0.5, ty + 0.5, z, z + 1.8, "glass_dark") for k, z in enumerate((14, 24))]
    cottage = dict(r=(6.5, 2.5, 14.5, 8.0), h=6.0, wall="plaster_white", roof=('gable', 'x', 3.2, "roof_slate", 0.4),
                   sills=[2.4], faces='+x+y', ww=1.1, wh=1.6, spacing=2.6, win="window_blue", doors=[('+y', 11.6, 0)], door="wood", chimneys=[(8.5, 5.2, 10.5)],
                   skip=[('+y', 2, 0)])
    p += building(coll, "cottage", [cottage])
    p.append(slab("path", coll, 10.9, 8.0, 12.3, 15.8, "sand", 0.06))
    return p


def object_statue(coll):
    p = [slab("paving", coll, 0.3, 0.3, 15.7, 15.7, "concrete", 0.08)]
    for k, (inset, z0, z1) in enumerate([(3.6, 0, 1.6), (4.6, 1.6, 3.2), (5.6, 3.2, 4.8)]):
        p.append(box(f"step{k}", coll, inset, inset, z0, 16 - inset, 16 - inset, z1, "stone"))
    p.append(loft("plinth", coll, 6.4, 6.4, 9.6, 9.6, [(4.8, 0), (13, 0.6), (14, 0.4)], "copper_green", top="stone"))
    p += [box("legs", coll, 7.5, 7.6, 14, 8.5, 8.4, 17, "cc1"),
          box("body", coll, 7.4, 7.5, 17, 8.6, 8.5, 20.5, "cc1"),
          prism("head", coll, 8.0, 8.0, 0.55, 20.5, 21.7, 6, "cc1"),
          beam("arm", coll, (8.0, 8.4, 20.0), (8.0, 9.6, 23.0), 0.4, 0.4, "cc1")]
    return p


def object_owned_land(coll):
    p = [box("post", coll, 7.6, 7.6, 0, 8.1, 8.1, 9.0, "steel_light")]
    p.append(box("flag", coll, 7.75, 8.1, 5.0, 7.95, 12.6, 8.6, "cc1"))
    return p


# ---------------------------------------------------------------- company HQs (2x2, 32 x 32)

def bungalow(coll, tag, r):
    return building(coll, tag, [dict(r=r, h=5.5, wall="brick", roof=('gable', 'y', 3.0, "cc1", 0.4), sills=[2.0], faces='+x+y-x-y',
                                     ww=1.2, wh=1.6, spacing=2.8, win="glass_dark", doors=[('+y', (r[0] + r[2]) / 2, 0)], door="wood_dark",
                                     skip=[('+y', 1, 0)])])


def object_hq_tiny(coll):
    p = [slab("yard", coll, 3, 3, 29, 29, "dirt", 0.05)]
    p += bungalow(coll, "house", (11, 13, 17.5, 24))
    p.append(slab("path", coll, 13.6, 24, 15.0, 31.8, "concrete", 0.09))
    return p


def object_hq_small(coll):
    p = object_hq_tiny(coll)
    shed = dict(r=(20, 5, 26, 11), h=3.4, wall="stone_dark", roof=('gable', 'x', 1.8, "roof_dark", 0.3))
    p += building(coll, "shed", [shed])
    fence(p, coll, "paddock", [(4, 4, 28, 4.2), (4, 27.8, 13.4, 28), (15.2, 27.8, 28, 28), (4, 4.2, 4.2, 27.8), (27.8, 4.2, 28, 27.8)], "plaster_white", "plaster_white", 1.8, 6)
    return p


def object_hq_medium(coll):
    p = [slab("paving", coll, 0.3, 0.3, 31.7, 31.7, "concrete_dark", 0.06), slab("lawn", coll, 13, 13, 29, 29, "grass", 0.09)]
    walls(p, coll, "edge", (0.3, 0.3, 31.7, 31.7), 1.6, "brick", gaps=[('+y', 4, 11), ('+x', 4, 11)])
    blocks = [dict(r=(3, 3, 9, 22), h=6.5, wall="brick", roof=('flat', "cc1", "brick"), sills=[2.2], faces='+x+y-x-y', ww=1.2, wh=1.8, spacing=2.6, win="glass_dark",
                   doors=[('+x', 12, 0)], door="glass_dark"),
              dict(r=(9, 3, 17, 9), h=6.5, wall="brick", roof=('flat', "cc1", "brick"), sills=[2.2], faces='+x+y-y', ww=1.2, wh=1.8, spacing=2.6, win="glass_dark")]
    p += building(coll, "office", blocks)
    for k, y in enumerate((14, 19)):
        p += building(coll, f"shed{k}", [dict(r=(21, y - 12, 29, y - 7.5), h=2.6, wall="stone_dark", roof=('gable', 'x', 1.4, "roof_dark", 0.2))])
    flag(p, coll, "flag", 12, 12, 16)
    return p


def object_hq_large(coll):
    p = [slab("paving", coll, 0.3, 0.3, 31.7, 31.7, "concrete_dark", 0.06)]
    walls(p, coll, "edge", (0.3, 0.3, 31.7, 31.7), 2.2, "brick", gaps=[('+y', 20, 27), ('+x', 22, 28)])
    H = 16
    office = dict(r=(3, 3, 19, 19), h=H, wall="brick", roof=('flat', "cc1", "brick"), sills=[2.0, 7.0, 12.0], faces='+x+y-x-y',
                  ww=1.1, wh=2.4, spacing=2.0, win="glass_dark", doors=[('+x', 11, 0), ('+y', 11, 0)], door="glass_dark",
                  skip=[('+x', 4, 0), ('+y', 4, 0)], bands=[5.6, 10.6], band_mat="brick_dark", band_t=0.4)
    p += building(coll, "office", [office])
    p.append(box("lightwell", coll, 8.5, 8.5, H, 13.5, 13.5, H + 0.3, "concrete_dark"))
    p += [box(f"well{k}", coll, *r, "brick") for k, r in enumerate([(7.8, 7.8, H, 14.2, 8.5, H + 0.9), (7.8, 13.5, H, 14.2, 14.2, H + 0.9),
                                                                    (7.8, 8.5, H, 8.5, 13.5, H + 0.9), (13.5, 8.5, H, 14.2, 13.5, H + 0.9)])]
    planter(p, coll, "bed", (22, 3, 29, 9), 7)
    parking(p, coll, "park", 13, 30, 22, 29, along='x')
    flag(p, coll, "flag0", 21, 13, 18)
    flag(p, coll, "flag1", 15, 21, 18)
    return p


def object_hq_huge(coll):
    p = [slab("paving", coll, 0.3, 0.3, 31.7, 31.7, "concrete", 0.06)]
    walls(p, coll, "edge", (0.3, 0.3, 31.7, 31.7), 2.0, "plaster_white", gaps=[('+y', 4, 10), ('+x', 22, 28)])
    r, H = (7, 3, 21, 17), 56
    tower = dict(r=r, h=H, wall="brick", roof=('flat', "cc1", "cc1"), sills=[2.4 + 4.6 * k for k in range(12)], faces='+x+y-x-y',
                 ww=1.3, wh=2.6, spacing=2.4, win="glass_dark", doors=[('+x', 10, 0), ('+y', 14, 0)], door="glass_dark",
                 skip=[('+x', 3, 0), ('+y', 3, 0)], pilasters=5, pil_mat="cc1")
    p += building(coll, "tower", [tower])
    x0, y0, x1, y1 = r  # crenellated parapet corners
    p += [box(f"cren{k}", coll, x - 0.6, y - 0.6, H, x + 0.6, y + 0.6, H + 1.8, "cc1") for k, (x, y) in
          enumerate([(x0, y0), (x1, y0), (x1, y1), (x0, y1), ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1), (x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)])]
    planter(p, coll, "bed0", (4, 20, 10, 27), 3)
    planter(p, coll, "bed1", (19, 22, 26, 28), 5)
    parking(p, coll, "park", 24, 30, 3, 15)
    flag(p, coll, "flag", 16, 21, 18)
    return p


# ---------------------------------------------------------------- field fences (one edge, along X at y = 0)

Y0, Y1 = 0.3, 2.1


def hedge(p, coll, tag, x0, x1, h=2.8, mat="grass", bump="leaf_light", seed=1):
    p.append(box(f"{tag}_body", coll, x0, Y0, 0, x1, Y1, h, mat))
    rnd = random.Random(seed)
    n = max(1, int((x1 - x0) // 2.2))
    for i in range(n):
        x = x0 + (x1 - x0) * (i + 0.5) / n + rnd.uniform(-0.4, 0.4)
        p.append(lathe(f"{tag}_bump{i}", coll, x, (Y0 + Y1) / 2, [(h - 0.2, 1.0), (h + 0.5, 0.8), (h + 0.9, 0)], 5, bump, phase=rnd.random()))


def blossoms(p, coll, tag, mat, seed, n=12):
    rnd = random.Random(seed)
    for i in range(n):
        x, z = 0.6 + 14.8 * (i + rnd.random()) / n, rnd.uniform(1.2, 3.2)
        y = Y1 if i % 2 == 0 else Y0
        side = 0.02 if i % 2 == 0 else -0.42
        p.append(box(f"{tag}_bl{i}", coll, x - 0.3, y + side, z, x + 0.3, y + side + 0.4, z + 0.5, mat))


def fence_1(coll):
    p = []
    hedge(p, coll, "hedge", 0.2, 15.8)
    return p


def fence_2(coll):
    p = []
    hedge(p, coll, "left", 0.2, 5.6, seed=2)
    hedge(p, coll, "right", 10.4, 15.8, seed=3)
    for k, z in enumerate((0.8, 1.6, 2.4)):
        p.append(box(f"gate{k}", coll, 5.6, 1.0, z, 10.4, 1.4, z + 0.35, "wood"))
    p.append(beam("brace", coll, (5.8, 1.2, 0.9), (10.2, 1.2, 2.6), 0.3, 0.3, "wood"))
    return p


def fence_3(coll):
    p = []
    fence(p, coll, "rail", [(0.2, 1.0, 15.8, 1.35)], "wood", "wood_dark", 2.6, 5)
    return p


def fence_4(coll):
    p = []
    hedge(p, coll, "hedge", 0.2, 15.8, seed=4)
    blossoms(p, coll, "yellow", "lamp_yellow", 4)
    return p


def fence_5(coll):
    p = []
    hedge(p, coll, "hedge", 0.2, 15.8, seed=5)
    blossoms(p, coll, "red", "signal_red", 5)
    return p


def fence_6(coll):
    p = [box("wall", coll, 0.2, 0.5, 0, 15.8, 1.9, 1.9, "stone")]
    rnd = random.Random(6)
    x = 0.2
    while x < 15.6:  # rough coping stones
        w = rnd.uniform(1.0, 2.0)
        p.append(box(f"cope{x:.1f}", coll, x, 0.4, 1.9, min(15.8, x + w), 2.0, 1.9 + rnd.uniform(0.25, 0.6), rnd.choice(["stone", "stone_dark", "concrete"])))
        x += w
    return p


# ---------------------------------------------------------------- rocks

def prop_rocks(coll):
    rnd = random.Random(16)
    spots = [(4.0, 4.5, 1.0, 0.9), (11.5, 5.0, 0.7, 0.6), (6.0, 11.5, 1.2, 1.1), (12.0, 12.0, 0.6, 0.5),
             (9.0, 8.0, 0.5, 0.4), (2.8, 9.0, 0.45, 0.35), (13.8, 8.8, 0.45, 0.4), (8.5, 14.0, 0.4, 0.35)]
    return [rock(f"rock{k}", coll, x, y, r, h, rnd.choice(["stone", "stone_dark", "concrete_dark"]), 5, rnd.random())
            for k, (x, y, r, h) in enumerate(spots)]


sync_palette()
coll = bpy.data.collections["default"]
clear(coll)
ob = join(KEY, globals()[KEY](coll))
result = sum(len(p.vertices) - 2 for p in ob.data.polygons)
