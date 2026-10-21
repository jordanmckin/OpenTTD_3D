"""Temperate houses (Phase 8.6). Exec after house_kit.py with KEY set to the house's inventory key and its .blend open.

Each member rebuilds the four state collections and sets `result` to the triangles per state. Proportions come from
the reference sprites (1 unit = 1 sprite pixel vertically; the classic view shows the +X and +Y faces).
"""
import math

C = bpy.data.collections


def floors(n, first=2.0, step=4.4):
    return [first + i * step for i in range(n)]


def pave(coll, w=16, h=16, mat="concrete"):
    return [slab("pave", coll, 0.2, 0.2, w - 0.2, h - 0.2, mat, 0.08)]


def ground(mat):
    return lambda coll: pave(coll, mat=mat)


def grid(z0, z1, n, ww, spacing, band_t=1.8):
    """Window strips from z0 to z1 split into n storeys by bands: individual windows for the cost of one quad per bay."""
    step = (z1 - z0) / n
    return dict(sills=[z0], wh=z1 - z0, ww=ww, spacing=spacing, band_t=band_t,
                bands=[z0 + step * (k + 1) - band_t for k in range(n)])


# 000 tall office block: ten-storey red brick block, grey +Y face, flat roof at the front and a red barrel roof at the back
def house_000():
    main = dict(r=(1, 1, 15, 15), h=40, wall="brick_red", band_mat="brick_red", clad={'+y': 'concrete'},
                band_over={'+y': 'concrete'}, pilasters=7, pil_mat="brick", pil_faces='+x-x', **grid(1.0, 39.0, 9, 1.0, 2.0, 2.2))
    return make([main,
                 dict(r=(1.5, 1.5, 7.5, 14.5), z0=40, h=40.05, wall="brick_red", roof=('vault', 'y', 5, "brick_red")),
                 dict(r=(7.5, 1, 15, 15), z0=40, h=40.05, wall="brick_red", roof=('flat', "concrete", "brick_red"))],
                 ground("concrete"))


# 001 office block: ten-storey cream tower with a dark mansard roof at the back, three-storey brick building with two gables in front
def house_001():
    return make([
        dict(r=(1, 1, 15, 8), h=44, wall="cream", band_mat="cream", roof=('mansard', 6, "roof_dark", 1.8, "concrete"), **grid(1.5, 43, 10, 1.0, 2.4, 2.0)),
        dict(r=(1, 8, 15, 15), h=15, wall="brick_red", sills=[1.2, 6.0, 10.8], ww=1.0, wh=2.4, spacing=2.4, bands=[5.0, 9.8, 14.6], band_t=0.4, band_mat="stone"),
        dict(r=(1, 8, 15, 11.5), z0=15, h=15.05, wall="brick_red", roof=('gable', 'x', 6, "roof_dark", 0.2)),
        dict(r=(1, 11.5, 15, 15), z0=15, h=15.05, wall="brick_red", roof=('gable', 'x', 6, "roof_dark", 0.2))],
        ground("concrete"), cap1=24)


# 002 small block of flats: three-storey brick block with a brown hipped roof, garden walls on the back edges
def house_002():
    def garden(coll):
        p = [box("wallx", coll, 0.3, 0.3, 0, 0.8, 15.7, 1.6, "brick_red"), box("wally", coll, 0.8, 0.3, 0, 15.7, 0.8, 1.6, "brick_red"),
             slab("path", coll, 12.5, 7, 15.9, 9, "concrete")]
        flowers(p, coll, "f", [(14, 3), (14.8, 12.5), (2.5, 14.5), (5, 14.8), (14, 14.5)])
        return p
    return make([dict(r=(3.5, 3.5, 12.5, 12.5), h=12, wall="brick_red", roof=('hip', 5, "roof_thatch", 3.0),
                      sills=[1.2, 5.0, 8.8], ww=1.1, wh=2.4, spacing=2.2, doors=[('+x', 8, 0)], skip=(('+x', 1, 0), ('+x', 2, 0)),
                      bands=[11.4], band_t=0.6, band_mat="brick_dark")], garden)


# 004 large office block: grey concrete block with a window grid and corner pilasters, glass lobby, flat roof with a stair drum
def house_004():
    b = dict(r=(1, 1, 15, 15), h=44, wall="concrete", band_mat="concrete", pilasters=4, pil_mat="stone",
             roof=('flat', "concrete_dark", "stone"), **grid(7.0, 43.0, 9, 0.9, 1.6, 1.6))
    def top(coll):
        return [prism("stair", coll, 4.2, 4.2, 1.8, 44, 47, 8, "concrete", cap="roof_dark"),
                quad("lobbyx", coll, '+x', 15, 3, 7, 0, 5.4, "glass_dark"), quad("lobbyy", coll, '+y', 15, 9, 13, 0, 5.4, "glass_dark")]
    def piles(coll):
        return [prism(f"pile{i}{j}", coll, 3 + 5 * i, 3 + 5 * j, 1.3, 0, 4.5 if (i + j) % 2 else 3.0, 6, "concrete")
                for i in range(3) for j in range(3)]
    def cage(coll):
        p = []
        frame(p, coll, "c1", (1, 1, 15, 15), 0, 44, floors(10, 4.4, 4.4), "concrete", 0.4)
        return p
    return make([b], lambda coll: top(coll) + pave(coll), stages={
        "construction_0": piles, "construction_1": cage,
        "construction_2": lambda coll: building(coll, "c2", [b]) + top(coll)})


# 007 hotel (1x2): five-storey brick hotel in a grey frame, two wings round a recessed entrance with flags, roof pool and stair tower
def house_007():
    w = dict(wall="brick_red", h=30, sills=floors(5, 2.0, 5.6), ww=1.4, wh=2.6, spacing=2.6, bands=[5.2, 10.8, 16.4, 22.0, 27.6], band_t=0.6,
             band_mat="concrete", pilasters=2, roof=('flat', "concrete_dark", "concrete"))
    blocks = [dict(r=(2, 2, 14, 13), **w), dict(r=(2, 19, 14, 30), **w),
              dict(r=(2, 13, 10, 19), **dict(w, pilasters=0, doors=[('+x', 16, 0)], door="glass_dark"))]
    def extra(coll):
        p = [box("stair", coll, 3, 3, 30, 8, 8, 35, "brick_red"), box("stair_roof", coll, 2.8, 2.8, 35, 8.2, 8.2, 35.6, "concrete"),
             quad("stair_win", coll, '+x', 8, 4.5, 6.5, 31, 33.5, "window_blue"),
             box("pool_rim", coll, 5, 21, 30, 11, 28, 30.7, "concrete"), slab("pool", coll, 5.4, 21.4, 10.6, 27.6, "water", 30.72)]
        for k, r in enumerate([(2, 2, 14, 13), (2, 19, 14, 30), (2, 13, 10, 19)]):
            railing(p, coll, f"r{k}", r, 30.8, posts=0)
        for k, y in enumerate((14, 16, 18)):
            p += [prism(f"pole{k}", coll, 12.5, y, 0.15, 0, 16, 4, "steel_light"),
                  box(f"flag{k}", coll, 12.45, y + 0.15, 13.2, 12.55, y + 1.6, 15.6, "window_blue")]
        return p
    return make(blocks, lambda coll: extra(coll) + pave(coll, 16, 32), c1=0.85,
                stages={"construction_2": lambda coll: building(coll, "c2", blocks) + extra(coll)})


# 010 fountain: paved square, round stone basin, tall jet with a spray bowl
def house_010():
    def fountain(coll):
        p = pave(coll)
        p.append(lathe("rim", coll, 8, 8, [(0.1, 5.4), (1.3, 5.4), (1.3, 4.8), (0.9, 4.8)], 14, "stone"))
        p.append(prism("water", coll, 8, 8, 4.85, 0.1, 0.85, 14, "water", cap="water"))
        p.append(prism("column", coll, 8, 8, 0.6, 0.8, 6.0, 6, "stone"))
        p.append(lathe("bowl", coll, 8, 8, [(5.6, 0.5), (6.4, 2.0), (6.8, 2.0)], 8, "stone", cap="water"))
        p.append(lathe("jet", coll, 8, 8, [(6.8, 0.7), (10, 0.45), (24, 0.2), (25, 0)], 6, "window_blue"))
        for k in range(6):
            a = 2 * math.pi * k / 6
            x, y = 8 + 3.4 * math.cos(a), 8 + 3.4 * math.sin(a)
            p.append(beam(f"spray{k}", coll, (8 + 1.8 * math.cos(a), 8 + 1.8 * math.sin(a), 6.8), (x, y, 1.0), 0.25, 0.25, "plaster_white"))
        return p
    return make([], stages={"construction_0": ground("dirt"), "construction_1": ground("concrete"),
                            "construction_2": fountain, "complete": fountain})


# 011 park: tall conifer at the back, birch on the left, pond, paths along the two front edges, dark shrubs
def house_011():
    def park(coll):
        p = [_obj("pond", coll, [(5, 4.5, 0.15), (11, 3.5, 0.15), (14.3, 6.5, 0.15), (14, 12.5, 0.15), (9.5, 14, 0.15), (5.5, 11.5, 0.15)],
                  [(0, 1, 2, 3, 4, 5)], ["water"]),
             slab("pathx", coll, 14.5, 0.2, 15.8, 6.5, "concrete"), slab("pathy", coll, 8.5, 14.5, 15.8, 15.8, "concrete"),
             box("bench", coll, 15.0, 9.5, 0.6, 15.6, 11.5, 1.1, "wood")]
        conifer(p, coll, "fir", 4.8, 10.5, 58, 4.6, tiers=5)
        blob_tree(p, coll, "birch", 11, 4.6, 12, 3.4, 22, "leaf_light", "bark_white", lobes=3, trunk_r=0.4, seed=11)
        p += [heap("shrub0", coll, 12, 13.5, 2.0, 1.6, 2.8, "leaf_dark", seed=1), heap("shrub1", coll, 3.2, 3.2, 1.8, 1.8, 2.5, "leaf_dark", seed=2)]
        return p
    return make([], stages={"construction_0": ground("dirt"), "construction_1": park, "construction_2": park, "complete": park})


# 012 park: big deciduous tree at the back, small red tree on the left, a clipped hedge mound, path across the front
def house_012():
    def park(coll):
        p = [_obj("path", coll, [(15.8, 8.5, 0.12), (15.8, 10.3, 0.12), (10.3, 15.8, 0.12), (8.5, 15.8, 0.12)], [(0, 1, 2, 3)], ["concrete"]),
             lathe("hedge", coll, 9, 9, [(0.1, 5.2), (3.5, 4.8), (6.5, 3.0), (8, 0)], 9, "leaf_dark")]
        blob_tree(p, coll, "oak", 6, 9.5, 18, 5.0, 27, "leaf", "bark", lobes=3, trunk_r=0.7, seed=3)
        blob_tree(p, coll, "red", 12.5, 3.8, 6, 2.4, 11, "leaf_red", "bark_grey", lobes=2, trunk_r=0.3, seed=4)
        return p
    return make([], stages={"construction_0": ground("dirt"), "construction_1": park, "construction_2": park, "complete": park})


# 013 office block: three storeys of brick panels in a grey concrete frame, flat roof
def house_013():
    b = dict(r=(1, 1, 15, 15), h=30, wall="brick_red", sills=[3.0, 11.5, 20.0], ww=1.0, wh=3.6, spacing=2.3,
             bands=[0, 8.6, 17.1, 25.6], band_t=1.6, band_mat="concrete", pilasters=4, roof=('flat', "concrete_dark", "concrete"))
    return make([b], ground("concrete"))


# 017 modern office building: arcaded plinth, two very tall chimney towers with red bands, a cluster of white and red window pods
TOWERS = [(10.5, 4.0, 86), (4.5, 5.0, 100)]
PODS = [(15.5, [(8, 8), (11, 8), (8, 11), (11, 11), (3, 9.5), (5, 11)]), (19.5, [(9, 9), (5, 10), (11, 10.5), (8.5, 11), (12, 6.5)]),
        (23.5, [(8, 7.5), (11, 11), (6, 11), (3.5, 8), (11.5, 7)]), (27.5, [(9, 9), (11, 7.5), (6.5, 9.5), (8, 11.5)]),
        (31.5, [(10, 10), (7, 8.5), (11, 6.8), (5.5, 11)]), (35.5, [(8.5, 11), (11, 7.8), (6.5, 7.5)]),
        (39.5, [(9.5, 9), (7, 11), (11, 11)]), (43.5, [(8, 9.5), (10.5, 7.5)]), (47.5, [(9.5, 10)])]
RED = {(43.5, 0), (47.5, 0), (39.5, 2), (35.5, 1), (31.5, 0)}


def house_017():
    def base(coll):
        p = [box("plinth", coll, 1, 1, 0, 15, 15, 10, "plaster_white"), box("deck", coll, 0.6, 0.6, 10, 15.4, 15.4, 12.5, "plaster_white"),
             box("deckband", coll, 0.8, 0.8, 12.5, 15.2, 15.2, 13.0, "stone_dark"), box("deck2", coll, 1, 1, 13, 15, 15, 15.5, "plaster_white")]
        for f in ('+x', '-x', '+y', '-y'):
            at = 15 if f[0] == '+' else 1
            p.append(quad(f"arch{f}", coll, f, at, 3.0, 13.0, 0, 7.5, "glass_dark"))
        for k, (x, y, top) in enumerate(TOWERS):
            prof = [(15.5, 2.2), (top - 9, 2.2), (top - 7, 2.2), (top - 5.5, 2.2), (top - 3.5, 2.2), (top, 2.2)]
            p.append(lathe(f"tower{k}", coll, x, y, prof, 7, ["plaster_white", "signal_red", "plaster_white", "signal_red", "plaster_white"],
                           cap="concrete", phase=math.pi / 8))
        return p
    def pods(coll, layers, red):
        p = []
        for z, spots in layers:
            for i, (x, y) in enumerate(spots):
                x, y = min(x, 11), min(y, 11)
                m = "signal_red" if red and (z, i) in RED else "plaster_white"
                p.append(box(f"pod{z}_{i}", coll, x, y, z, x + 4, y + 4, z + 4, m))
                if (i + int(z)) % 2:  # one round window per pod, alternating sides
                    p.append(quad(f"podw{z}_{i}", coll, '+x', x + 4, y + 1.2, y + 2.8, z + 1.2, z + 2.8, "glass_dark"))
                else:
                    p.append(quad(f"podw{z}_{i}", coll, '+y', y + 4, x + 1.2, x + 2.8, z + 1.2, z + 2.8, "glass_dark"))
        return p
    return make([], stages={"construction_0": base,
                            "construction_1": lambda coll: base(coll) + pods(coll, PODS[:3], False),
                            "construction_2": lambda coll: base(coll) + pods(coll, PODS, True),
                            "complete": lambda coll: base(coll) + pods(coll, PODS, True) + pave(coll)})


# 018 warehouse: brown brick shed with a twin-gabled dark roof, high window band, dark loading doors
def house_018():
    def doors(coll):
        return [quad("doory0", coll, '+y', 14, 3.5, 6.5, 0, 6, "black"), quad("doory1", coll, '+y', 14, 9.5, 12.5, 0, 6, "black"),
                quad("doorx", coll, '+x', 14, 9, 12, 0, 5, "black")]
    blocks = [dict(r=(2, 2, 14, 14), h=12, wall="brick_brown", sills=[9.4], ww=1.0, wh=1.6, spacing=1.6, pilasters=5, pil_mat="wood_dark",
                   pil_faces='+x+y'),
              dict(r=(2, 2, 14, 8), z0=12, h=12.05, wall="brick_brown", roof=('gable', 'x', 5, "roof_dark", 0.3)),
              dict(r=(2, 8, 14, 14), z0=12, h=12.05, wall="brick_brown", roof=('gable', 'x', 5, "roof_dark", 0.3))]
    return make(blocks, lambda coll: doors(coll) + pave(coll),
                stages={"construction_2": lambda coll: building(coll, "c2", blocks) + doors(coll)})


# 019 office block: tall red brick block with a red mansard roof at the back, white four-storey block with a brown mansard and dormers in front
def house_019():
    def dormers(coll):
        p = []
        for k, y in enumerate((4, 8, 12)):
            p += [box(f"dorm{k}", coll, 13.4, y - 1.1, 22, 14.8, y + 1.1, 25.2, "plaster_white"),
                  quad(f"dormw{k}", coll, '+x', 14.8, y - 0.7, y + 0.7, 22.6, 24.6, "window_blue")]
        return p
    blocks = [dict(r=(1, 1, 8, 15), h=40, wall="brick_red", band_mat="brick_red", faces='+x-x+y-y',
                   roof=('mansard', 7, "brick_red", 2.0, "roof_tile"), **grid(1.5, 39.5, 9, 1.0, 2.2, 2.0)),
              dict(r=(8, 1, 15, 15), h=22, wall="plaster_white", sills=[1.5, 6.5, 11.5, 16.5], ww=1.3, wh=3.0, spacing=2.6, faces='+x+y-y',
                   roof=('mansard', 6, "roof_thatch", 2.2, "roof_dark"), bands=[5.4, 10.4, 15.4, 21.2], band_t=0.5, band_mat="stone")]
    return make(blocks, lambda coll: dormers(coll) + pave(coll), cap1=24,
                stages={"construction_2": lambda coll: building(coll, "c2", blocks) + dormers(coll)})


# 028 tall office block: concrete podium with dark drum columns, blue glass tower, red arch with fins up the +X face
def house_028():
    tower = dict(r=(2, 5, 14, 14.5), z0=10, h=78, wall="window_blue", bands=[10 + 4.6 * k for k in range(1, 15)], band_t=0.35,
                 band_mat="concrete", pilasters=4, roof=('flat', "concrete_dark", "concrete"))
    def podium(coll):
        p = [box("podium", coll, 1, 1, 0, 15, 15, 9, "concrete"), box("podium_top", coll, 0.8, 0.8, 9, 15.2, 15.2, 10, "stone"),
             quad("door", coll, '+y', 15, 9, 12, 0, 3.5, "glass_dark")]
        for k, y in enumerate((5.5, 10.5)):
            p.append(prism(f"drum{k}", coll, 14.6, y, 1.2, 0, 9, 8, "stone_dark"))
        return p
    def arch(coll):
        p = []
        x, ya, yb, top = 15.0, 5.5, 10.5, 64
        r = (yb - ya) / 2; yc = (ya + yb) / 2
        p += [beam("legA", coll, (x, ya, 9), (x, ya, top - r), 1.0, 1.0, "brick_red"),
              beam("legB", coll, (x, yb, 9), (x, yb, top - r), 1.0, 1.0, "brick_red")]
        pts = [(x, yc - r * math.cos(math.pi * i / 6), top - r + r * math.sin(math.pi * i / 6)) for i in range(7)]
        p += [beam(f"arc{i}", coll, pts[i], pts[i + 1], 1.0, 1.0, "brick_red") for i in range(6)]
        p += [beam(f"fin{k}", coll, (x, ya - 1.6, z), (x, yb + 1.6, z), 0.8, 0.6, "brick_red") for k, z in enumerate((24, 34, 44, 54))]
        return p
    def cage(coll):
        p = podium(coll) + arch(coll)
        frame(p, coll, "cage", tower['r'], 10, 78, [10 + 8.5 * k for k in range(1, 9)], "steel", 0.25)
        return p
    return make([], stages={"construction_0": podium, "construction_1": cage,
                            "construction_2": lambda coll: podium(coll) + building(coll, "c2", [tower]) + arch(coll),
                            "complete": lambda coll: podium(coll) + building(coll, "done", [tower]) + arch(coll) + pave(coll)})


# 030 shops and offices: glass block bulging at mid height, wrapped in tan timber fins, flat roof
RINGS = [(0, 1.2), (16, 1.2), (24, 0.2), (36, 0.2), (46, 1.2), (54, 1.2)]


def house_030():
    def fins(coll, rings, n=7):
        p = []
        for f in ('+x', '-x', '+y', '-y'):
            for i in range(n):
                v, fc = [], []
                for z, d in rings:
                    lo, hi = 1 + d, 15 - d
                    a = lo + (hi - lo) * (i + 0.5) / n
                    if f[1] == 'x':
                        X = (15 - d + 0.12) if f[0] == '+' else (1 + d - 0.12)
                        v += [(X, a - 0.35, z), (X, a + 0.35, z)]
                    else:
                        Y = (15 - d + 0.12) if f[0] == '+' else (1 + d - 0.12)
                        v += [(a + 0.35, Y, z), (a - 0.35, Y, z)]
                for k in range(len(rings) - 1):
                    q = (2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2)
                    fc.append(q if f[0] == '+' else q[::-1])
                p.append(_obj(f"fin{f}{i}", coll, v, fc, ["sand"] * len(fc)))
        return p
    def body(coll):
        return [loft("glass", coll, 1, 1, 15, 15, RINGS, "window_blue", top="concrete"),
                loft("rim", coll, 1, 1, 15, 15, [(54, 1.0), (55, 1.0)], "sand")] + fins(coll, RINGS)
    def c0(coll):
        return fins(coll, [(0, 1.2), (6, 1.2)])
    def c1(coll):
        return fins(coll, RINGS) + [loft("rim", coll, 1, 1, 15, 15, [(54, 1.0), (55, 1.0)], "sand")]
    return make([], stages={"construction_0": c0, "construction_1": c1, "construction_2": body,
                            "complete": lambda coll: body(coll) + pave(coll)})


# 031 theatre: stepped red brick hall with flat roofs, lit marquee round the front corner and a vertical sign
def house_031():
    blocks = [dict(r=(2, 2, 9, 14), h=20, wall="brick_red", roof=('flat', "roof_dark", "brick_red"), sills=[15], ww=1.0, wh=2.0, spacing=2.4),
              dict(r=(9, 1, 15, 14), h=13, wall="brick_red", roof=('flat', "roof_dark", "brick_red"), sills=[9.5], ww=1.0, wh=1.8, spacing=2.4,
                   faces='+y-y', doors=[('+x', 12, 0)], door="glass_dark")]
    def front(coll):
        p = [box("marquee", coll, 15, 1, 4.2, 15.8, 9, 5.8, "concrete"), box("marquee_y", coll, 9, 0.2, 4.2, 15.8, 1, 5.8, "concrete"),
             box("canopy", coll, 14.6, 0.2, 5.8, 15.9, 9.2, 6.3, "roof_dark"), quad("foyer", coll, '+x', 15, 2, 8, 0, 4.0, "glass_dark"),
             box("sign", coll, 9, 3.6, 7.5, 9.8, 4.8, 19, "concrete")]
        for k in range(6):
            p.append(box(f"bulb{k}", coll, 15.8, 1.6 + 1.3 * k, 4.8, 15.95, 2.0 + 1.3 * k, 5.2, "lamp_yellow"))
        for k in range(4):
            p.append(box(f"sbulb{k}", coll, 9.8, 4.0, 9 + 2.6 * k, 9.95, 4.4, 9.4 + 2.6 * k, "lamp_yellow"))
        return p
    hall = lambda coll, tag: building(coll, tag, blocks) + front(coll)
    return make(blocks, stages={"construction_0": ground("dirt"), "construction_1": lambda coll: hall(coll, "c1"),
                                "construction_2": lambda coll: hall(coll, "c2"), "complete": lambda coll: hall(coll, "done") + pave(coll)})


# 032 stadium (2x2): striped pitch along Y, covered crowd stand on the back (-X) side, long low brick stand on the front (+X) side, rugby posts
def house_032():
    def pitch(coll):
        p = [slab("pitch", coll, 1, 1, 31, 31, "grass", 0.1)]
        for k in range(10):
            y = 3 + 2.9 * k
            p.append(slab(f"line{k}", coll, 9, y, 25, y + 0.3, "pitch_line", 0.14))
        p += [slab("side0", coll, 9, 3, 9.3, 29.4, "pitch_line", 0.14), slab("side1", coll, 24.7, 3, 25, 29.4, "pitch_line", 0.14)]
        return p
    def stands(coll):
        p = [_obj("crowd", coll, [(8, 30, 1), (8, 2, 1), (2.5, 2, 9), (2.5, 30, 9)], [(0, 1, 2, 3)], ["crowd"]),
             box("front", coll, 7.6, 2, 0, 8.2, 30, 1.4, "plaster_white"),
             box("back", coll, 1, 1.5, 0, 2.5, 30.5, 13.5, "brick_red"),
             box("canopy", coll, 1, 1.5, 13.5, 4.2, 30.5, 14.0, "plaster_white"),
             box("end0", coll, 1, 1.5, 0, 8.2, 2.0, 12, "brick_red"), box("end1", coll, 1, 30, 0, 8.2, 30.5, 12, "brick_red"),
             box("lstand", coll, 29.5, 3, 0, 31, 29, 6, "brick_red"),
             _obj("lroof", coll, [(31, 3, 7.5), (31, 29, 7.5), (26, 29, 5.5), (26, 3, 5.5)], [(0, 1, 2, 3)], ["brick_red"]),
             box("lroof_edge", coll, 25.8, 3, 4.9, 26.2, 29, 5.6, "brick_dark"),
             _obj("lseats", coll, [(26.5, 29, 0.8), (26.5, 3, 0.8), (29.5, 3, 4), (29.5, 29, 4)], [(0, 1, 2, 3)], ["roof_dark"])]
        for k in range(8):
            y = 3.5 + 3.6 * k
            p.append(box(f"post{k}", coll, 26.1, y, 0, 26.4, y + 0.3, 5.5, "stone_dark"))
            p.append(box(f"cpost{k}", coll, 3.9, y, 9, 4.2, y + 0.3, 13.5, "steel_light"))
        for n, y in enumerate((3.2, 29.2)):
            p += [box(f"goal{n}a", coll, 15.2, y - 0.15, 0, 15.5, y + 0.15, 8, "pitch_line"),
                  box(f"goal{n}b", coll, 18.5, y - 0.15, 0, 18.8, y + 0.15, 8, "pitch_line"),
                  box(f"goal{n}c", coll, 15.2, y - 0.15, 2.8, 18.8, y + 0.15, 3.1, "pitch_line")]
        return p
    full = lambda coll: pitch(coll) + stands(coll)
    return make([], stages={"construction_0": pitch, "construction_1": full, "construction_2": full, "complete": full})


# 036 offices: round glass tower with concrete floor rings and a dark crown, slung between two tall telescopic yellow masts
MASTS = [(9.5, 1.2, (44, 78, 104, 116)), (9.6, 14.8, (36, 70, 98, 114))]


def house_036():
    def masts(coll):
        p = []
        for k, (x, y, (a, b, c, top)) in enumerate(MASTS):
            prof = [(0, 0.9), (a, 0.9), (a, 0.7), (b, 0.7), (b, 0.5), (c, 0.5), (c, 0.32), (top, 0.32)]
            p.append(lathe(f"mast{k}", coll, x, y, prof, 5, "hazard_yellow", cap="hazard_yellow"))
        return p
    def tower(coll):
        r, prof, mats = 5.0, [], []
        for k in range(10):
            prof += [(10 * k, r), (10 * k + 0.9, r)]
            mats += ["concrete", "window_blue"]
        prof.append((100, r))
        p = [lathe("tower", coll, 7.2, 8, prof, 9, mats[:len(prof) - 1]),
             lathe("crown", coll, 7.2, 8, [(100, r), (101.2, r + 0.3), (103, r * 0.75), (104, r * 0.4)], 9, "roof_dark", cap="roof_dark")]
        for k, (x, y, (_, _, _, top)) in enumerate(MASTS):
            p.append(beam(f"cable{k}", coll, (7.2, 8, 103), (x, y, top - 1.5), 0.3, 0.3, "black"))
        return p
    site = lambda coll: pave(coll) + masts(coll)
    return make([], stages={"construction_0": ground("dirt"), "construction_1": site, "construction_2": site,
                            "complete": lambda coll: site(coll) + tower(coll)})


# 040 shopping centre (2x2): paved site with four brick-walled planting squares while building; then a brick arcade under twin glass vaults
SQUARES = [(7, 7), (25, 7), (7, 25), (25, 25)]


def house_040():
    def site(coll):
        p = pave(coll, 32, 32)
        for k, (cx, cy) in enumerate(SQUARES):
            x0, y0, x1, y1 = cx - 4, cy - 4, cx + 4, cy + 4
            for n, (a, b, c, d) in enumerate([(x0, y0, x1, y0 + 0.5), (x0, y1 - 0.5, x1, y1), (x0, y0 + 0.5, x0 + 0.5, y1 - 0.5), (x1 - 0.5, y0 + 0.5, x1, y1 - 0.5)]):
                p.append(box(f"sq{k}_{n}", coll, a, b, 0, c, d, 1.5, "brick_red"))
            for n, (x, y) in enumerate([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]):
                p.append(box(f"sqp{k}_{n}", coll, x - 0.4 if x == x0 else x - 0.4, y - 0.4, 0, x + 0.4, y + 0.4, 2.4, "brick_dark"))
        return p
    def mall(coll):
        p = pave(coll, 32, 32) + [box("arcade", coll, 1.5, 1.5, 0, 30.5, 30.5, 4, "brick_red")]
        for f, at in (('+x', 30.5), ('+y', 30.5), ('-x', 1.5), ('-y', 1.5)):
            for k in range(6):
                a = 3.5 + 4.6 * k
                p.append(quad(f"shop{f}{k}", coll, f, at, a, a + 3.2, 0, 3.2, "glass_dark"))
        for k, (x0, x1) in enumerate(((1.5, 16), (16, 30.5))):
            p.append(vault(f"vault{k}", coll, x0, 1.2, x1, 30.8, 4, 7, "window_blue", 'y', 6, "glass"))
            for i, y in enumerate((1.4, 9, 16, 23, 30.6)):
                pts = [(x0 + (x1 - x0) * (1 - math.cos(math.pi * j / 6)) / 2, y, 4 + 7 * math.sin(math.pi * j / 6) + 0.1) for j in range(7)]
                p += [beam(f"rib{k}_{i}_{j}", coll, pts[j], pts[j + 1], 0.3, 0.3, "plaster_white") for j in range(6)]
        return p
    return make([], stages={"construction_0": site, "construction_1": site, "construction_2": mall, "complete": mall})


result = globals()[f"house_{KEY.split('_')[1]}"]()
