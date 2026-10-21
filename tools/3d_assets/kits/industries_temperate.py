"""Temperate industries (Phase 8.6). Exec after house_kit.py and industry_kit.py with KEY set and the industry's .blend open.

One function per tile graphic: fn(coll, tag, stage) -> parts, in local tile coordinates. Stages are 0..3
(construction_0..2, complete). Multi-tile buildings (factory, steel mill, bank) are cut on the tile seams.
The coal mine and power station (8.4 pilot) were built with the earlier scratch script and are not rebuilt here.
"""
import json
import math
import random


def staged(blocks, extra=None, low=0.3, extra_from=2):
    """Usual building stages: low open walls, full-height open walls, the building, the building; extra(coll, tag, s) from extra_from on."""
    def fn(coll, tag, s):
        if s == 0:
            p = shell(coll, tag, blocks, low, cap=2.5)
        elif s == 1:
            p = shell(coll, tag, blocks, 1.0)
        else:
            p = building(coll, tag, blocks)
        if extra and s >= extra_from:
            p += extra(coll, tag, s)
        return p or dirt(coll, tag)
    return fn


def ground_until(n, fn):
    """Bare ground for stages below n, then fn."""
    return lambda coll, tag, s: fn(coll, tag, s) if s >= n else dirt(coll, tag)


# ---------------------------------------------------------------- 02 sawmill
def shed(r, h, axis, rise):
    return dict(r=r, h=h, wall="wood", roof=('gable', axis, rise, "roof_dark", 0.4))


def planks(coll, tag):
    return [box(f"{tag}_planks{i}", coll, x, y, 0, x + 2.6, y + 4.5, 2.2, "sand") for i, (x, y) in enumerate([(9.4, 2.8), (12.4, 2.8), (9.4, 8.6), (12.4, 8.6)])]


SAWMILL = {
    11: staged([shed((1.5, 1.5, 14.5, 13.5), 10, 'x', 6)], lambda coll, tag, s: [quad(f"{tag}_door", coll, '+x', 14.5, 4.5, 10.5, 0, 6.5, "black")], extra_from=1),
    12: staged([shed((1.5, 2, 8, 14), 10, 'y', 5.5)], lambda coll, tag, s: [quad(f"{tag}_door", coll, '+y', 14, 2.8, 6.7, 0, 5, "black")] + (planks(coll, tag) if s >= 2 else []), extra_from=1),
    13: staged([shed((1.5, 1.5, 12.5, 14.5), 9, 'y', 5.5)], lambda coll, tag, s: [quad(f"{tag}_door", coll, '+y', 14.5, 4, 10, 0, 6, "black")], extra_from=1),
    14: ground_until(3, lambda coll, tag, s: logpile(coll, tag, 'y', [5, 4, 3, 2], 1.45, 1.5, 14.5, 1.0, 15.0, "roof_dark", "paint_orange")),
    15: ground_until(3, lambda coll, tag, s: logpile(coll, tag, 'x', [5, 4, 3, 2, 1], 1.45, 1.5, 14.5, 1.0, 15.0, "leaf_orange", "sand")),
}


# ---------------------------------------------------------------- 03 forest
def forest(coll, tag, s):
    H = (14, 26, 34, 44)[s]
    rnd = random.Random(16)
    p = []
    for i in range(3):
        for j in range(3):
            h = H * rnd.uniform(0.82, 1.05)
            r = min(3.0, 0.2 * h)
            x, y = 3 + 5 * i + rnd.uniform(-0.4, 0.4), 3 + 5 * j + rnd.uniform(-0.4, 0.4)
            conifer(p, coll, f"{tag}_{i}{j}", x, y, h, r, tiers=3, n=5)
    return p


# ---------------------------------------------------------------- 04 oil refinery
GREY, BLUE = "plaster_white", "tank_blue"


def g18(coll, tag, s):
    if s == 0:
        return [prism(f"{tag}_base", coll, 8, 8, 6.8, 0, 0.5, 14, "concrete_dark")]
    if s == 1:
        return [lathe(f"{tag}_tank", coll, 8, 8, [(0, 6.6), (5.5, 6.6), (9, 6.6)], 14, [BLUE, GREY], inner=(8, "stone_dark"))]
    return [lathe(f"{tag}_tank", coll, 8, 8, [(0, 6.6), (7, 6.6), (19, 6.6), (20, 6.2), (21.5, 3.5), (22, 0)], 14, [BLUE, GREY, GREY, GREY, GREY]),
            lathe(f"{tag}_rail", coll, 8, 8, [(19, 6.75), (19.8, 6.75)], 14, "steel"),
            box(f"{tag}_sign", coll, 14.45, 7.4, 6.8, 14.7, 8.6, 8.0, "hazard_yellow")]


def g19(coll, tag, s):
    if s == 0:
        return [lathe(f"{tag}_ring", coll, 8, 8, [(0, 3.4), (1.5, 3.4)], 10, GREY, inner=(1.2, "stone_dark"))]
    zs = [0, 9, 13.5, 19, 23.5, 29, 33.5, 39, 43.5, 49, 52]
    p = [lathe(f"{tag}_col", coll, 8, 8, [(z, 3.4) for z in zs], 10, [GREY, BLUE] * 5, cap=BLUE),
         box(f"{tag}_sign", coll, 11.3, 7.4, 2, 11.5, 8.6, 3.2, "hazard_yellow")]
    if s >= 2:
        p += striped(coll, f"{tag}_pipe", (8, 11.9, 0.5), (8, 11.9, 44), 0.6, 7)
        p.append(beam(f"{tag}_bend", coll, (8, 11.9, 44), (8, 10.8, 46), 0.6, 0.6, "signal_red"))
    return p


def g20(coll, tag, s):
    if s == 0:
        return [lathe(f"{tag}_ring", coll, 8.5, 8.5, [(0, 2.4), (1.5, 2.4)], 8, GREY, inner=(1.2, "stone_dark"))]
    levels = (26, 33, 40, 47) if s == 3 else (26, 33)
    p = [prism(f"{tag}_tower", coll, 8.5, 8.5, 2.2, 0, 52, 8, GREY, cap="stone_dark")]
    for k, z in enumerate(levels):  # balconies on the +X+Y side with a short rail
        p += [box(f"{tag}_deck{k}", coll, 10.0, 9.0, z, 12.6, 12.6, z + 0.5, "steel"),
              box(f"{tag}_rail{k}", coll, 12.4, 9.0, z + 0.5, 12.6, 12.6, z + 1.8, "steel"),
              box(f"{tag}_railb{k}", coll, 10.0, 12.4, z + 0.5, 12.6, 12.6, z + 1.8, "steel")]
    top = 70 if s == 3 else 36
    p += polyline(coll, f"{tag}_pipe", [(5, 7, 0), (5, 7, min(top, 56))] + ([(8.5, 8.5, 56), (8.5, 8.5, 70)] if s == 3 else []), 0.6, GREY)
    return p  # the flare flame is a part (flare_refinery)


def flare_refinery(coll, tag, step):
    return [flame(f"{tag}_flame", coll, (8.5, 8.5, 70), 9, step, lean=(-1.5, 0.0), r=1.0)]


def rack(coll, tag, y, x0=2, x1=14, zs=(0.8, 1.8)):
    return [beam(f"{tag}_rack{k}", coll, (x0, y, z), (x1, y, z), 0.4, 0.4, GREY) for k, z in enumerate(zs)]


def posts_frame(coll, tag, r, h, levels, w=0.9, mat="rust"):
    """Heavy steel frame: square posts at the corners and box beams round each level."""
    x0, y0, x1, y1 = r
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    p = [box(f"{tag}_post{k}", coll, x - w / 2, y - w / 2, 0, x + w / 2, y + w / 2, h, mat) for k, (x, y) in enumerate(c)]
    for lv, z in enumerate(levels):
        p += [beam(f"{tag}_beam{lv}_{k}", coll, (*c[k], z), (*c[(k + 1) % 4], z), w * 0.8, w * 0.8, mat) for k in range(4)]
    return p


def g21(coll, tag, s):
    p = posts_frame(coll, tag, (2, 2, 14, 14), 40, [14, 27, 39.5])
    if s >= 1:
        p += [log(f"{tag}_v0", coll, 'x', 3.5, 12.5, 6, 18, 2.4, BLUE, BLUE, 8), log(f"{tag}_v1", coll, 'x', 3.5, 12.5, 10.5, 18, 2.4, GREY, GREY, 8),
              prism(f"{tag}_v2", coll, 6, 10.5, 2.2, 0, 13, 8, BLUE), prism(f"{tag}_v3", coll, 10.5, 6, 2.2, 0, 13, 8, GREY)]
    if s >= 2:
        p += striped(coll, f"{tag}_p0", (12.8, 8, 0), (12.8, 8, 30), 0.6, 5) + striped(coll, f"{tag}_p1", (3.4, 12.5, 0), (3.4, 12.5, 26), 0.6, 4)
        p += rack(coll, tag, 14.6) + [beam(f"{tag}_top{k}", coll, (2.5, y, 30), (13.5, y, 30), 0.5, 0.5, GREY) for k, y in enumerate((6, 10))]
    return p


def g22(coll, tag, s):
    p = posts_frame(coll, tag, (5, 5, 11, 11), 18 if s else 10, [9, 17.5] if s else [9], 0.8)
    if s >= 1:
        p += [lathe(f"{tag}_tank", coll, 8, 8, [(18, 4.0), (22, 4.0), (26, 4.0)], 10, [GREY, BLUE], cap=BLUE),
              prism(f"{tag}_t0", coll, 3.0, 11.5, 2.0, 0, 9, 8, GREY), prism(f"{tag}_t1", coll, 6.5, 13.5, 2.0, 0, 8, 8, BLUE),
              prism(f"{tag}_t2", coll, 12.6, 12, 2.4, 0, 8, 8, GREY)]
    if s >= 2:
        p += striped(coll, f"{tag}_p0", (12.4, 7.5, 0), (12.4, 7.5, 30), 0.6, 5)
        p += polyline(coll, f"{tag}_arch", [(6, 2.6, 0), (6, 2.6, 31), (10, 2.6, 31), (10, 2.6, 0)], 0.6, GREY)
        p += rack(coll, tag, 15, 9, 15.5)
    return p


G23 = [dict(r=(3, 3, 13, 13), h=8, wall="plaster_white", roof=('flat', "concrete_dark", "stone"), sills=[2.6], ww=1.6, wh=2.4, spacing=2.0,
            win="glass_dark", bands=[6.2], band_t=0.5, band_mat="stone")]


def g23_top(coll, tag, s):
    return [box(f"{tag}_ac0", coll, 4.5, 4.5, 8.1, 7.5, 7.5, 9.6, "steel_light"), box(f"{tag}_ac1", coll, 4.5, 8.5, 8.1, 7.5, 11.5, 9.6, "steel_light"),
            box(f"{tag}_sky", coll, 8.8, 8.8, 8.1, 11.5, 11.5, 9.0, BLUE)]


REFINERY = {18: g18, 19: g19, 20: g20, 21: g21, 22: g22, 23: staged(G23, g23_top)}


# ---------------------------------------------------------------- 05 oil rig (sea level is z = 0)
RZ = 12  # deck lift over the first draft, from the sprite heights


def leg(coll, tag, x, y):
    return [prism(f"{tag}_leg", coll, x, y, 2.0, 0, 22 + RZ, 8, "concrete"), prism(f"{tag}_foot", coll, x, y, 2.4, 0, 1.2, 8, "concrete_dark")]


def deck(coll, tag, upper=True):
    p = [box(f"{tag}_truss", coll, 0, 0, 20 + RZ, 16, 16, 24 + RZ, "hazard_yellow")]
    if upper:
        p.append(box(f"{tag}_deck", coll, 0, 0, 24 + RZ, 16, 16, 25 + RZ, "concrete"))
    return p


def rig(legs, top=None, mid=None):
    def fn(coll, tag, s):
        p = []
        for k, (x, y) in enumerate(legs):
            p += leg(coll, f"{tag}{k}", x, y)
        if s >= 1:
            p += deck(coll, tag)
            if mid:
                p += mid(coll, tag)
        if s == 3 and top:
            p += top(coll, tag)
        return p
    return fn


def rig24(coll, tag):
    return [box(f"{tag}_mod0", coll, 2, 2, 25 + RZ, 9, 14, 31 + RZ, GREY), box(f"{tag}_mod1", coll, 10, 3, 25 + RZ, 14, 8, 29 + RZ, "stone_dark"),
            box(f"{tag}_mod2", coll, 10, 9.5, 25 + RZ, 14.5, 14, 30 + RZ, "signal_red")] + \
        [beam(f"{tag}_pipe{k}", coll, (1, y, 31.6 + RZ), (15, y, 31.6 + RZ), 0.5, 0.5, "steel") for k, y in enumerate((4, 8, 12))]


def rig25(coll, tag):
    base = [(5, 5), (11, 5), (11, 11), (5, 11)]
    p = [beam(f"{tag}_dleg{k}", coll, (x, y, 25 + RZ), (7 + (x > 8) * 2, 7 + (y > 8) * 2, 58 + RZ), 0.6, 0.6, "paint_orange") for k, (x, y) in enumerate(base)]
    for lv, z in enumerate((34 + RZ, 44 + RZ, 52 + RZ)):
        t = (z - (25 + RZ)) / 33
        c = [(x + ((7 + (x > 8) * 2) - x) * t, y + ((7 + (y > 8) * 2) - y) * t, z) for x, y in base]
        p += [beam(f"{tag}_ring{lv}_{k}", coll, c[k], c[(k + 1) % 4], 0.4, 0.4, "paint_orange") for k in range(4)]
    p += [box(f"{tag}_cab", coll, 6.5, 6.5, 58 + RZ, 9.5, 9.5, 60 + RZ, "steel_light"), beam(f"{tag}_mast", coll, (8, 8, 60 + RZ), (8, 8, 68 + RZ), 0.4, 0.4, "signal_red"),
          box(f"{tag}_floor", coll, 3, 3, 25 + RZ, 13, 13, 27 + RZ, "stone_dark")]
    return p


def rig26(coll, tag):
    p = [box(f"{tag}_quarters", coll, 2, 2, 25 + RZ, 14, 14, 33 + RZ, "plaster_white")]
    for f, at in (('+x', 14), ('+y', 14), ('-x', 2), ('-y', 2)):
        p += [quad(f"{tag}_win{f}{k}", coll, f, at, 2.5, 13.5, z, z + 1.2, "glass_dark") for k, z in enumerate((27 + RZ, 30 + RZ))]
    p += [prism(f"{tag}_pad", coll, 9, 7.5, 6.0, 33.4 + RZ, 34.0 + RZ, 8, "stone_dark", phase=math.pi / 8),
          lathe(f"{tag}_rim", coll, 9, 7.5, [(34.0 + RZ, 6.0), (34.5 + RZ, 6.0)], 8, "signal_red", phase=math.pi / 8),
          lathe(f"{tag}_circle", coll, 9, 7.5, [(34.05 + RZ, 3.6), (34.05 + RZ, 2.9)], 12, "hazard_yellow")]
    return p


def rig27(coll, tag):
    p = [box(f"{tag}_quarters", coll, 0.5, 0.5, 25 + RZ, 15.5, 15.5, 38 + RZ, "plaster_white"), box(f"{tag}_roof", coll, 0.5, 0.5, 38 + RZ, 15.5, 15.5, 38.5 + RZ, "stone_dark")]
    for f, at in (('+x', 15.5), ('+y', 15.5), ('-x', 0.5), ('-y', 0.5)):
        p += [quad(f"{tag}_win{f}{k}", coll, f, at, 1, 15, z, z + 1.2, "glass_dark") for k, z in enumerate((27 + RZ, 30.5 + RZ, 34 + RZ))]
    p += [box(f"{tag}_boat{k}", coll, 15.5, y, 26 + RZ, 16, y + 3, 27.6 + RZ, "paint_orange") for k, y in enumerate((3, 9))]
    p.append(beam(f"{tag}_boom", coll, (11, 5, 38.5 + RZ), (14, 2, 56 + RZ), 1.0, 1.0, "signal_red"))  # flame: flare_rig
    return p


def flare_rig(coll, tag, step):
    return [flame(f"{tag}_flame", coll, (14, 2, 56 + RZ), 11, step, lean=(0.2, -0.2), r=0.75)]


def rig27_mid(coll, tag):
    return [box(f"{tag}_deck2", coll, 1, 1, 31 + RZ, 15, 15, 32.5 + RZ, "hazard_yellow")] + \
        [box(f"{tag}_post{k}", coll, x, y, 25 + RZ, x + 0.6, y + 0.6, 31 + RZ, "signal_red") for k, (x, y) in enumerate([(1, 1), (14.4, 1), (1, 14.4), (14.4, 14.4)])]


def rig28(coll, tag):
    return [box(f"{tag}_mod0", coll, 8, 2, 25 + RZ, 15, 9, 32 + RZ, GREY), box(f"{tag}_mod1", coll, 2, 2, 25 + RZ, 7, 7, 30 + RZ, "signal_red"),
            box(f"{tag}_mod2", coll, 9, 10, 25 + RZ, 14.5, 14.5, 29 + RZ, "hazard_yellow")]


def rig28_mid(coll, tag):
    return [prism(f"{tag}_crane", coll, 5, 11, 1.0, 25 + RZ, 40 + RZ, 6, "signal_red"),
            beam(f"{tag}_jib", coll, (5, 11, 40 + RZ), (14.5, 15, 46 + RZ), 0.8, 0.8, "signal_red"),
            beam(f"{tag}_hook", coll, (14.3, 14.8, 46 + RZ), (14.3, 14.8, 32 + RZ), 0.15, 0.15, "black")]


OIL_RIG = {24: rig([(4, 4)], rig24), 25: rig([(4, 12)], rig25), 26: rig([(12, 4)], rig26),
           27: rig([(8, 8)], rig27, rig27_mid), 28: rig([(12, 12)], rig28, rig28_mid)}


# ---------------------------------------------------------------- 06 factory (2x2 groups: 39 back, 40 right, 41 left, 42 front)
def hall(r, axis, faces):
    return dict(r=r, h=15, wall="brick", roof=('gable', axis, 4.5, "tank_blue", 0.3), sills=[1.6, 6.4, 11.0], ww=1.4, wh=2.4,
                spacing=2.4, win="glass_dark", faces=faces)


def chimneys(coll, tag):
    return [lathe(f"{tag}_ch{k}", coll, x, y, [(0, 1.0), (h, 1.0)], 8, "brick", inner=(1.5, "black"))
            for k, (x, y, h) in enumerate([(4.0, 2.0, 40), (7.5, 1.6, 34), (11, 2.0, 42)])]


def coils(coll, tag, x0, y0, n=3):
    return [log(f"{tag}_coil{k}", coll, 'x', x0, x0 + 2.2, y0 + 2.4 * k, 1.1, 1.1, "sand", "stone_dark", 8) for k in range(n)]


def plates(coll, tag, x, y):
    return [box(f"{tag}_plate{k}", coll, x, y + 0.2 * k, 0.5 * k, x + 4, y + 2.4, 0.5 * k + 0.5, GREY if k % 2 else "stone_dark") for k in range(3)]


def factory_hall(blocks, extra=None):
    def fn(coll, tag, s):
        if s == 0:
            return shell(coll, tag, blocks, 0.2, cap=2.5)
        p = shell(coll, tag, blocks, 1.0) if s < 3 else building(coll, tag, blocks)
        return p + (extra(coll, tag, s) if extra else [])
    return fn


def f42(coll, tag, s):
    if s == 0:
        return dirt(coll, tag, "concrete")
    if s < 3:
        return [box(f"{tag}_truck", coll, 3, 5, 0.6, 8, 8.5, 2.6, "hazard_yellow"), box(f"{tag}_cab", coll, 6.5, 5.2, 2.6, 8, 8.3, 4.4, "glass_dark")] + \
            [log(f"{tag}_w{k}", coll, 'y', 4.9, 8.6, x, 0.7, 0.7, "rubber", "steel", 6) for k, x in enumerate((3.8, 7.2))] + \
            [beam(f"{tag}_boom", coll, (5, 6.7, 3), (12.5, 12.5, 58), 0.9, 0.9, "hazard_yellow"),
             beam(f"{tag}_cable", coll, (12.5, 12.5, 58), (12.5, 12.5, 30), 0.15, 0.15, "black"),
             box(f"{tag}_load", coll, 11.6, 11.6, 16, 13.4, 13.4, 30, "hazard_yellow")]
    return coils(coll, tag, 10, 8) + plates(coll, tag, 3, 9)


FACTORY = {
    39: factory_hall([hall((3, 3, 16, 12), 'x', '-x-y'), hall((3, 12, 12, 16), 'y', '-x+x')], lambda coll, tag, s: chimneys(coll, tag)),
    40: factory_hall([hall((3, 0, 12, 9), 'y', '-x+x'),
                      dict(r=(4, 9, 13, 15.5), h=32, wall="brick", roof=('flat', "concrete_dark", "brick"), sills=[2, 7.5, 13, 18.5, 24],
                           ww=1.4, wh=2.6, spacing=3.0, win="glass_dark")],
                     lambda coll, tag, s: coils(coll, tag, 13.4, 1.6) if s == 3 else []),
    41: factory_hall([hall((0, 3, 13, 12), 'x', '+x+y-y')]),
    42: f42,
}


# ---------------------------------------------------------------- 08 steel mill (2x2: 52 back, 53 right, 54 left, 55 front; 2x1: 56 back, 57 front)
def markings(coll, tag, x0, y0, x1, y1, t=0.4):
    return [slab(f"{tag}_mk{k}", coll, a, b, c, d, "hazard_yellow", 0.1) for k, (a, b, c, d) in
            enumerate([(x0, y0, x1, y0 + t), (x0, y1 - t, x1, y1), (x0, y0, x0 + t, y1), (x1 - t, y0, x1, y1)])]


def stubs(coll, tag, pts, h=2.0):
    return [box(f"{tag}_stub{k}", coll, x, y, 0, x + 0.8, y + 0.8, h, "brick") for k, (x, y) in enumerate(pts)]


def sm52(coll, tag, s):
    if s == 0:
        return stubs(coll, tag, [(2, 2), (8, 2), (2, 8), (14, 2)])
    if s < 3:
        return [box(f"{tag}_wall", coll, 1, 1, 0, 2, 15, 13, "brick"), box(f"{tag}_lintel", coll, 2, 1, 11, 15, 2, 13, "brick"),
                box(f"{tag}_pier", coll, 13, 1, 0, 15, 2, 11, "brick")]
    return [box(f"{tag}_hall", coll, 0.5, 0.5, 0, 16, 16, 10, "brick"), sawtooth(f"{tag}_roof", coll, 0.5, 0.5, 16, 16, 10, 4, 3, along='x')] + \
        banded_chimney(coll, f"{tag}_ch", 2, 2, 1.1, 20)


def sm53(coll, tag, s):
    if s == 0:
        return stubs(coll, tag, [(2, 4), (2, 12), (13, 12)])
    cols = [box(f"{tag}_col{k}", coll, x, y, 0, x + 1.2, y + 1.2, 11, "brick") for k, (x, y) in enumerate([(1, 14.3), (14.3, 14.3), (1, 7), (14.3, 7)])]
    if s < 3:
        return cols + [box(f"{tag}_beam", coll, 1, 14.3, 11, 15.5, 15.5, 13, "brick"), box(f"{tag}_wall", coll, 0, 0, 0, 1.2, 14.3, 18, "brick")]
    return cols + [sawtooth(f"{tag}_roof", coll, 0, 0, 16, 15.5, 11, 4, 2.5, along='x')] + markings(coll, tag, 3, 2, 13, 13)


def sm54(coll, tag, s):
    blocks = [dict(r=(2, 1, 16, 9), h=6, wall="brick")]
    if s == 0:
        return shell(coll, tag, blocks, 0.3, cap=2)
    if s < 3:
        return shell(coll, tag, blocks, 1.0) + [box(f"{tag}_portal", coll, 3, 11, 0, 4, 15, 12, "brick")]
    return building(coll, tag, blocks) + [sawtooth(f"{tag}_roof", coll, 2, 1, 16, 9, 6, 3, 2.2, along='x')] + \
        banded_chimney(coll, f"{tag}_ch", 5, 12, 1.1, 30) + markings(coll, tag, 8, 10, 15, 15)


def sm55(coll, tag, s):
    return markings(coll, tag, 3, 3, 13, 13) + ([box(f"{tag}_kerb", coll, 0.5, 0.5, 0, 15.5, 1.2, 0.8, "brick")] if s < 3 else [])


def sm56(coll, tag, s):
    blocks = [dict(r=(0.5, 1, 12, 15), h=18, wall="brick")]
    if s == 0:
        return shell(coll, tag, blocks, 0.1, cap=2)
    if s < 3:
        return shell(coll, tag, blocks, 1.0)
    return building(coll, tag, blocks) + [sawtooth(f"{tag}_roof", coll, 0.5, 1, 12, 15, 18, 4, 3, along='x')] + [
        lathe(f"{tag}_furnace", coll, 13.4, 5.5, [(0, 2.2), (5, 2.4), (8, 2.0), (10, 1.2), (14, 0.8)], 8, "black"),
        box(f"{tag}_glow", coll, 15.5, 4.9, 1.5, 15.9, 6.1, 4.0, "paint_orange"),
        quad(f"{tag}_band", coll, '+y', 15, 1, 12, 3, 5, "tank_blue")]


def sm57(coll, tag, s):
    blocks = [dict(r=(1, 1, 15, 15), h=7, wall="brick")]
    if s == 0:
        return shell(coll, tag, blocks, 0.3, cap=2)
    if s < 3:
        return shell(coll, tag, blocks, 1.0)
    return building(coll, tag, blocks) + [sawtooth(f"{tag}_roof", coll, 1, 1, 15, 15, 7, 3, 2.5, along='x')] + banded_chimney(coll, f"{tag}_ch", 3.5, 8, 1.1, 30)


STEEL = {52: sm52, 53: sm53, 54: sm54, 55: sm55, 56: sm56, 57: sm57}


# ---------------------------------------------------------------- 09 farm
def farmhouse(r, axis, h=7):
    return dict(r=r, h=h, wall="concrete", roof=('gable', axis, 5, "roof_dark", 0.4), sills=[1.2, 4.2], ww=1.0, wh=1.6, spacing=2.4, chimneys=[(r[0] + 1, r[1] + 1, 13.5)])


def fa33(coll, tag, s):
    p = building(coll, tag, [farmhouse((6, 4, 13, 12), 'y')]) + [quad(f"{tag}_door", coll, '+x', 13, 7.3, 8.7, 0, 2.6, "wood_dark"),
                                                                  slab(f"{tag}_path", coll, 13, 7.2, 16, 8.8, "concrete")]
    blob_tree(p, coll, f"{tag}_tree", 4.6, 4.6, 14, 4.0, 22, "leaf", "bark", trunk_r=0.6, lobes=2, seed=33)
    flowers(p, coll, f"{tag}_f", [(14.5, 4), (14.8, 12), (14, 13.5)])
    return p


def tractor(coll, tag, x, y):
    return [box(f"{tag}_body", coll, x, y, 0.8, x + 3.2, y + 1.8, 2.4, "hazard_yellow"), box(f"{tag}_cab", coll, x + 0.2, y + 0.1, 2.4, x + 1.5, y + 1.7, 4.0, "glass_dark")] + \
        [log(f"{tag}_w{k}", coll, 'y', y - 0.3, y + 2.1, x + dx, rr, rr, "rubber", "hazard_yellow", 6) for k, (dx, rr) in enumerate(((0.7, 0.9), (2.7, 0.55)))]


def fa34(coll, tag, s):
    return building(coll, tag, [dict(farmhouse((2, 1.5, 9, 8.5), 'y', 10), sills=[1.5, 6.0])]) + tractor(coll, f"{tag}_tr", 10.5, 9.5) + \
        [quad(f"{tag}_door", coll, '+x', 9, 4.3, 5.7, 0, 2.6, "wood_dark")]


def pole_barn(coll, tag, r, axis="x"):
    x0, y0, x1, y1 = r
    p = [gable(f"{tag}_roof", coll, x0, y0, x1, y1, 6, 9, "roof_dark", axis, 0.3)]
    for k, (x, y) in enumerate([(x0, y0), (x1 - 0.4, y0), (x0, y1 - 0.4), (x1 - 0.4, y1 - 0.4), ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1 - 0.4)]):
        p.append(box(f"{tag}_post{k}", coll, x, y, 0, x + 0.4, y + 0.4, 6, "wood_dark"))
    p.append(box(f"{tag}_hay", coll, x0 + 0.8, y0 + 0.8, 0, x1 - 0.8, y1 - 0.8, 4, "grain"))
    return p


def fa36(coll, tag, s):
    return building(coll, tag, [dict(r=(2, 3, 13, 13), h=7, wall="concrete", roof=('gable', 'y', 4.5, "roof_dark", 0.4))]) + \
        [quad(f"{tag}_door", coll, '+y', 13, 4, 11, 0, 5, "black"),
         box(f"{tag}_mach0", coll, 4.5, 13.2, 0, 7.5, 15.2, 2.0, "tank_blue"), box(f"{tag}_mach1", coll, 8.5, 13.2, 0, 11.5, 15.6, 1.6, "tank_blue")]


def fa37(coll, tag, s):
    return [lathe(f"{tag}_silo0", coll, 4.5, 4.5, [(0, 2.4), (36, 2.4), (37.5, 1.4), (38, 0)], 10, [GREY, "tank_blue", "tank_blue"]),
            lathe(f"{tag}_silo1", coll, 7.5, 11, [(0, 2.4), (32, 2.4), (33.5, 1.4), (34, 0)], 10, [GREY, "tank_blue", "tank_blue"]),
            heap(f"{tag}_spill", coll, 9.5, 7.5, 1.6, 1.4, 0.8, "grain", seed=37)] + \
        polyline(coll, f"{tag}_pipe", [(4.5, 4.5, 38), (4.5, 4.5, 39.5), (7.5, 11, 39.5), (7.5, 11, 34)], 0.5, GREY)


def fa38(coll, tag, s):
    p = [box(f"{tag}_w{k}", coll, a, b, 0, c, d, 1.2, "concrete") for k, (a, b, c, d) in
         enumerate([(1, 1, 15, 1.5), (1, 14.5, 15, 15), (1, 1.5, 1.5, 14.5), (14.5, 1.5, 15, 14.5)])]
    p += building(coll, f"{tag}_shed", [dict(r=(2, 11, 14, 14.4), h=2.6, wall="concrete", roof=('gable', 'x', 1.5, "roof_dark", 0.3))])
    p.append(box(f"{tag}_trough", coll, 3, 4.5, 0, 11, 5.3, 0.5, "lamp_yellow"))
    rnd = random.Random(38)
    for k in range(6):
        x, y = rnd.uniform(3, 12), rnd.uniform(6.5, 9.5)
        p.append(box(f"{tag}_pig{k}", coll, x, y, 0, x + 1.4, y + 0.8, 0.8, "pig_pink"))
    return p


FARM = {33: fa33, 34: fa34, 35: ground_until(1, lambda coll, tag, s: pole_barn(coll, f"{tag}a", (2, 1, 14, 7.5)) + pole_barn(coll, f"{tag}b", (2, 8.5, 14, 15))),
        36: ground_until(1, fa36), 37: ground_until(1, fa37), 38: ground_until(1, fa38)}


# ---------------------------------------------------------------- 11 oil wells
WELL_PIVOT = (8.5, 7.5, 26.5)    # top of the Samson post
WELL_DIR = (0.7071, -0.7071)      # walking beam, rear end to the horsehead over the casing
WELL_CRANK = (5.5, 11.4, 6.0)     # crank shaft on the gearbox


def well(coll, tag, s):
    """Static oil well: pad, Samson post, gearbox with its crank bearings, casing. The beam is a part (well_pump)."""
    top = WELL_PIVOT
    p = [box(f"{tag}_pad", coll, 3, 3, 0, 13, 13, 0.5, "concrete")]
    p += [beam(f"{tag}_leg{k}", coll, b, top, 0.7, 0.7, "rust") for k, b in enumerate([(6.5, 5.5, 0.5), (10.5, 9.5, 0.5), (10.5, 5.5, 0.5)])]
    p += [box(f"{tag}_motor", coll, 3.5, 9.6, 0.5, 7.5, 13.4, 4.0, "stone_dark")]
    p += [beam(f"{tag}_bearing{k}", coll, (WELL_CRANK[0] + o, WELL_CRANK[1] - o, 4.0), (WELL_CRANK[0] + o, WELL_CRANK[1] - o, WELL_CRANK[2] + 0.4), 0.6, 0.6, "rust")
          for k, o in enumerate((-1.0, 1.0))]
    p.append(prism(f"{tag}_casing", coll, 12.7, 3.5, 0.6, 0.5, 1.6, 6, "steel"))
    return p


def well_pump(coll, tag, step):
    """Walking beam, horsehead, polished rod, crank and counterweight at one of 12 steps of a stroke."""
    phi = 2 * math.pi * step / 12
    th = 0.2 * math.sin(phi)
    ux, uy = WELL_DIR
    px, py, pz = WELL_PIVOT
    b = (ux * math.cos(th), uy * math.cos(th), math.sin(th))  # along the beam
    dn = (ux * math.sin(th), uy * math.sin(th), -math.cos(th))  # down, square to the beam
    at = lambda d, e=0.0: (px + b[0] * d + dn[0] * e, py + b[1] * d + dn[1] * e, pz + b[2] * d + dn[2] * e)
    head, rear = 5.7, -5.7
    p = [beam(f"{tag}_walk", coll, at(rear), at(head), 0.8, 1.0, "rust"),
         beam(f"{tag}_head", coll, at(head - 0.4, -2.5), at(head + 0.9, 3.0), 1.8, 1.6, "stone")]
    hx, hy, hz = at(head + 0.9, 4.0)
    p.append(beam(f"{tag}_rod", coll, (12.7, 3.5, 0.5), (12.7, 3.5, hz), 0.25, 0.25, "black"))
    p.append(beam(f"{tag}_bridle", coll, (12.7, 3.5, hz), (hx, hy, hz + 0.6), 0.2, 0.2, "black"))
    cx, cy, cz = WELL_CRANK
    pin = (cx + ux * 3.2 * math.cos(phi), cy + uy * 3.2 * math.cos(phi), cz + 3.2 * math.sin(phi))
    p.append(beam(f"{tag}_crank", coll, (cx - ux * 1.6 * math.cos(phi), cy - uy * 1.6 * math.cos(phi), cz - 1.6 * math.sin(phi)), pin, 0.5, 0.9, "rust"))
    w = (cx - ux * 1.4 * math.cos(phi), cy - uy * 1.4 * math.cos(phi), cz - 1.4 * math.sin(phi))
    p.append(beam(f"{tag}_weight", coll, (w[0] - ux * 0.9, w[1] - uy * 0.9, w[2]), (w[0] + ux * 0.9, w[1] + uy * 0.9, w[2]), 2.6, 2.4, "stone_dark"))
    p.append(beam(f"{tag}_pitman", coll, pin, at(rear + 0.5, 0.5), 0.35, 0.35, "rust"))
    return p


# ---------------------------------------------------------------- 12 bank (2x1 along X: 58 back, 59 front)
def bank(r_walls, r_roof, faces, front=False):
    def fn(coll, tag, s):
        x0, y0, x1, y1 = r_walls
        p = [box(f"{tag}_walls", coll, x0, y0, 0, x1, y1, 10, "cream"),
             gable(f"{tag}_roof", coll, *r_roof, 10, 14, "copper_green", 'x', 0.4, "plaster_white"),
             box(f"{tag}_cornice", coll, x0 - 0.2, y0 - 0.2, 9.3, x1 + (0 if front else 0), y1 + 0.2, 10, "plaster_white")]
        windows(p, coll, tag, r_walls, [2.0], faces, ww=1.2, wh=6.0, spacing=2.6, mat="window_blue")
        pilasters(p, coll, tag, r_walls, 0, 9.3, 5, "plaster_white", faces.replace('+x', '').replace('-x', '') or '+y')
        if front:
            p += [prism(f"{tag}_col{k}", coll, 14.2, y, 0.5, 0.6, 9.5, 6, "plaster_white") for k, y in enumerate((3.2, 5.6, 8.0, 10.4, 12.8))]
            p += [box(f"{tag}_steps", coll, x1, 2.5, 0, 15.8, 13.5, 0.6, "stone"), quad(f"{tag}_door", coll, '+x', x1, 7, 9, 0, 4.5, "wood_dark")]
        if s == 3:
            p += [heap(f"{tag}_shrub{k}", coll, x, 15.0, 1.4, 0.7, 1.4, "leaf_dark", seed=k + (5 if front else 0)) for k, x in enumerate((3.5, 7.5, 11))]
        return p
    return fn


BANK = {58: bank((3, 2, 16, 14), (3, 2, 16, 14), '-x+y-y'), 59: bank((0, 2, 12, 14), (0, 2, 15.6, 14), '+y-y', front=True)}


# ---------------------------------------------------------------- 18 iron ore mine (4x4, gfx = 100 + 4 tx + ty)
PIT = {105, 106, 109, 110, 114, 115}
ORE_BUILDINGS = {106: ((4, 2, 12, 15), 'y', '+x+y-x'), 109: ((3, 3, 12, 12), 'x', '+x+y-y'), 114: ((3, 3, 12, 13), 'y', '+x+y-x')}


def ore(g):
    tx, ty = divmod(g - 100, 4)
    def fn(coll, tag, s):
        rnd = random.Random(g)
        p = []
        if g in PIT:
            p.append(slab(f"{tag}_pit", coll, 0.5, 0.5, 15.5, 15.5, "dirt", 0.06))
        for k in range(2 if g in PIT else 4):
            x, y = rnd.uniform(4, 12), rnd.uniform(4, 12)
            p.append(heap(f"{tag}_ore{k}", coll, x, y, rnd.uniform(3.0, 4.0), rnd.uniform(3.0, 4.0), rnd.uniform(2.5, 4.5),
                          "rust" if k % 2 else "brick_brown", 7, g * 10 + k))
        posts = []
        if tx == 0:
            posts += [(1.0, 0.8 + 2 * i) for i in range(8)]
        if ty == 0:
            posts += [(0.8 + 2 * i, 1.0) for i in range(8)]
        p += [box(f"{tag}_fp{k}", coll, x - 0.18, y - 0.18, 0, x + 0.18, y + 0.18, 3.6, "plaster_white") for k, (x, y) in enumerate(dict.fromkeys(posts))]
        if g in ORE_BUILDINGS:
            r, axis, faces = ORE_BUILDINGS[g]
            p += mine_building(coll, tag, min(s, 2), r, axis, faces)
        return p
    return fn


IRON = {g: ore(g) for g in range(100, 116)}


MEMBERS = {"industry_02": SAWMILL, "industry_03": {16: forest}, "industry_04": REFINERY, "industry_05": OIL_RIG, "industry_06": FACTORY,
           "industry_08": STEEL, "industry_09": FARM, "industry_11": {29: ground_until(1, well)}, "industry_12": BANK, "industry_18": IRON}

_inv = json.load(open(r"D:\G ttd\OpenTTD-15.3\OpenTTD-15.3\assets\3d\inventory.json", encoding="utf-8"))
_entry = next(e for e in _inv["entries"] if e["key"] == KEY)
sync_palette()
# Moving parts (Phase 8.7): gfx -> (steps, fn(coll, tag, step)); the renderer picks the step from the tile state.
PARTS = {"industry_04": {20: (4, flare_refinery)}, "industry_05": {27: (4, flare_rig)}, "industry_11": {29: (12, well_pump)}}

_layouts = [[tuple(t) for t in lay] for lay in _entry["layouts"]]
result = build_industry(_layouts, MEMBERS[KEY])
if KEY in PARTS:
    result.update(build_parts(_layouts, PARTS[KEY]))
