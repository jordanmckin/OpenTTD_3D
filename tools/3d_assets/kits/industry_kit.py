"""Industry kit: layout placement and shared parts for industry models (Phase 8.4 pilot, 8.6 production).

Exec after house_kit.py with the industry's .blend open. Members define one function per tile graphic,
fn(coll, tag, stage) -> parts, in local tile coordinates (0..16); build_industry() places a copy on every tile of
layout 0 (the converter keeps the first), plus `<state>@layout<n>` collections for graphics only found in later layouts.
"""
import math
import random

import bpy


def state_coll(name):
    C = bpy.data.collections
    if name in C:
        return C[name]
    c = C.new(name)
    bpy.data.scenes["model"].collection.children.link(c)
    return c


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def build_industry(layouts, GFX):
    """Rebuild every state collection from the layouts. Returns the largest triangle count per 'gfx/state'."""
    lay0 = [t for t in layouts[0] if t[2] in GFX]
    seen = {g for _, _, g in lay0}
    extra = {}
    for li, lay in enumerate(layouts[1:], 1):
        for tx, ty, g in lay:
            if g in GFX and g not in seen:
                extra.setdefault(li, []).append((tx, ty, g)); seen.add(g)
    out = {}
    for s, st in enumerate(STATES):
        for li, tiles in [(0, lay0)] + sorted(extra.items()):
            coll = state_coll(st if li == 0 else f"{st}@layout{li}")
            clear(coll)
            for tx, ty, g in tiles:
                tag = f"t{tx}{ty}_g{g}"
                ob = join(tag, GFX[g](coll, tag, s))
                ob.location = (16 * tx, 16 * ty, 0)
                k = f"{g}/{st}"
                out[k] = max(out.get(k, 0), tris(ob))
    return out


def build_parts(layouts, PARTS):
    """Moving parts (Phase 8.7): PARTS = {gfx: (steps, fn(coll, tag, step))}. Each step goes in a `part_<n>` state
    collection on the graphic's first tile in layout order (`part_<n>@layout<k>` if it is only in a later layout).
    The renderer draws them over the static tile. Returns the triangle count per 'gfx/part_n'."""
    first = {}
    for li, lay in enumerate(layouts):
        for tx, ty, g in lay:
            if g in PARTS and g not in first:
                first[g] = (li, tx, ty)
    out = {}
    for c in [c for c in bpy.data.collections if c.name.startswith("part_")]:
        clear(c)
    for g, (steps, fn) in PARTS.items():
        li, tx, ty = first[g]
        for n in range(steps):
            coll = state_coll(f"part_{n}" if li == 0 else f"part_{n}@layout{li}")
            tag = f"t{tx}{ty}_g{g}_p{n}"
            ob = join(tag, fn(coll, tag, n))
            ob.location = (16 * tx, 16 * ty, 0)
            out[f"{g}/part_{n}"] = tris(ob)
    return out


def flame(name, coll, base, h, step, lean=(0.0, 0.0), r=1.0):
    """Gas flare flame: a lumpy six-sided tongue from base, yellow at the burner, orange, then a red tip.
    step picks the flicker: height, lean and lumps change between steps."""
    rnd = random.Random(step * 7919 + 17)
    h *= (0.85, 1.0, 1.15, 0.95, 1.05, 0.9)[step % 6]
    lx, ly = lean[0] + rnd.uniform(-0.6, 0.6), lean[1] + rnd.uniform(-0.6, 0.6)
    rings = [(0.0, 0.7 * r), (0.3, 1.25 * r), (0.6, 0.9 * r), (0.82, 0.45 * r)]
    n = 6
    v = []
    for k, (t, rr) in enumerate(rings):
        a0 = rnd.uniform(0, math.pi / 3)
        for i in range(n):
            a = a0 + 2 * math.pi * i / n
            q = rr * rnd.uniform(0.8, 1.2)
            v.append((base[0] + lx * t * t + q * math.cos(a), base[1] + ly * t * t + q * math.sin(a), base[2] + h * t))
    v.append((base[0] + lx, base[1] + ly, base[2] + h))
    f, m = [], []
    bands = ("flame_yellow", "flame_orange", "flame_orange")
    for k in range(len(rings) - 1):
        for i in range(n):
            a, b = k * n + i, k * n + (i + 1) % n
            f.append((a, b, b + n, a + n)); m.append(bands[k])
    top = len(v) - 1
    for i in range(n):
        f.append(((len(rings) - 1) * n + i, (len(rings) - 1) * n + (i + 1) % n, top)); m.append("flame_red")
    return _obj(name, coll, v, f, m)


def bolt(coll, tag, p0, p1, kinks, step, w=0.18, mat="spark_blue"):
    """A jagged electric spark from p0 to p1."""
    rnd = random.Random(step * 31 + kinks)
    pts = [p0]
    for k in range(1, kinks):
        t = k / kinks
        pts.append(tuple(p0[j] + (p1[j] - p0[j]) * t + rnd.uniform(-0.7, 0.7) * (j < 2) for j in range(3)))
    pts.append(p1)
    return [beam(f"{tag}_{i}", coll, a, b, w, w, mat if i % 2 else "plaster_white") for i, (a, b) in enumerate(zip(pts, pts[1:]))]


def dirt(coll, tag, mat="dirt"):
    """Placeholder for a stage with nothing built yet, so the state never falls back to the old model."""
    return [slab(f"{tag}_dirt", coll, 3, 3, 13, 13, mat, 0.05)]


def log(name, coll, axis, a0, a1, c, z, r, body, end, n=6):
    """Horizontal cylinder along X or Y from a0 to a1, centre c across, height z; end discs in `end`."""
    ring = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    P = (lambda a, u, w: (a, c + u, z + w)) if axis == 'x' else (lambda a, u, w: (c + u, a, z + w))
    v = [P(a0, u, w) for u, w in ring] + [P(a1, u, w) for u, w in ring]
    f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    m = [body] * n
    f += [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    m += [end, end]
    ob = _obj(name, coll, v, f, m)
    if axis == 'y':
        ob.data.flip_normals()
    return ob


def logpile(coll, tag, axis, rows, r, a0, a1, c0, c1, body, end):
    """Pyramid of logs: rows = logs per layer, bottom first, centred between c0 and c1."""
    p = []
    for k, n in enumerate(rows):
        z = r + k * r * 1.72
        start = (c0 + c1) / 2 - r * (n - 1)
        for i in range(n):
            p.append(log(f"{tag}_log{k}_{i}", coll, axis, a0, a1, start + 2 * r * i, z, r, body, end))
    return p


def polyline(coll, tag, pts, w, mat):
    return [beam(f"{tag}_{i}", coll, a, b, w, w, mat) for i, (a, b) in enumerate(zip(pts, pts[1:]))]


def striped(coll, tag, p0, p1, w, n, mats=("signal_red", "hazard_yellow")):
    """Pipe from p0 to p1 painted in alternating bands."""
    pts = [tuple(p0[j] + (p1[j] - p0[j]) * i / n for j in range(3)) for i in range(n + 1)]
    return [beam(f"{tag}_{i}", coll, a, b, w, w, mats[i % len(mats)]) for i, (a, b) in enumerate(zip(pts, pts[1:]))]


def banded_chimney(coll, tag, x, y, r, h, mat="brick", band="tank_blue", n=8):
    prof = [(0, r), (h - 8, r), (h - 6.5, r), (h - 5, r), (h - 3.5, r), (h, r)]
    return [lathe(f"{tag}", coll, x, y, prof, n, [mat, band, mat, band, mat], inner=(2.0, "black"))]


def sawtooth(name, coll, x0, y0, x1, y1, z, n, h, roof="brick", glass="glass_dark", end=None, along='y'):
    """North-light roof: n teeth with ridges along `along`; glazing on the viewer (+X or +Y) side of each tooth."""
    if along == 'x':  # build it with the axes swapped, then swap back (which mirrors the winding)
        ob = sawtooth(name, coll, y0, x0, y1, x1, z, n, h, roof, glass, end)
        for v in ob.data.vertices:
            v.co.x, v.co.y = v.co.y, v.co.x
        ob.data.flip_normals()
        return ob
    em = end or roof
    w = (x1 - x0) / n
    v, f, m = [], [], []
    for i in range(n):
        a = x0 + w * i; b = a + w
        k = len(v)
        v += [(a, y0, z), (a, y1, z), (b, y1, z + h), (b, y0, z + h), (b, y0, z), (b, y1, z)]
        f += [(k, k + 3, k + 2, k + 1), (k + 4, k + 5, k + 2, k + 3), (k, k + 4, k + 3), (k + 1, k + 2, k + 5)]
        m += [roof, glass, em, em]
    return _obj(name, coll, v, f, m)


# --- pilot parts (coal mine), also used by the iron ore mine ---

def wheel(name, coll, c, r, t, n, mat, axis='x', rim=0.5, phase=0.0):
    """Spoked winding wheel: a ring in the plane normal to axis plus two crossed spokes, turned by phase radians."""
    cx, cy, cz = c
    def P(a, rr, off):
        a += phase
        u, w = rr * math.cos(a), rr * math.sin(a)
        return (cx + off, cy + u, cz + w) if axis == 'x' else (cx + u, cy + off, cz + w)
    v, f = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        v += [P(a, r, -t / 2), P(a, r - rim, -t / 2), P(a, r, t / 2), P(a, r - rim, t / 2)]
    for i in range(n):
        a, b = 4 * i, 4 * ((i + 1) % n)
        f += [(a, b, b + 1, a + 1), (a + 2, a + 3, b + 3, b + 2), (a, a + 2, b + 2, b), (a + 1, b + 1, b + 3, a + 3)]
    ob = _obj(name, coll, v, f, [mat] * len(f))
    spokes = []
    for k in range(2):
        a = math.pi / 4 + k * math.pi / 2
        spokes.append(beam(f"{name}_sp{k}", coll, P(a, r - rim, 0), P(a + math.pi, r - rim, 0), t * 0.6, 0.3, mat))
    return [ob] + spokes


def stilts(coll, tag, x0, y0, x1, y1, z):
    p = [box(f"{tag}_deck", coll, x0, y0, z - 0.5, x1, y1, z, "concrete_dark")]
    xs = [x0 + 0.3, (x0 + x1) / 2, x1 - 0.7]; ys = [y0 + 0.3, y1 - 0.7]
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            p.append(box(f"{tag}_leg{i}{j}", coll, x, y, 0, x + 0.4, y + 0.4, z - 0.5, "steel"))
    for j, y in enumerate(ys):
        p.append(beam(f"{tag}_brace{j}", coll, (xs[0] + 0.2, y + 0.2, 0.3), (xs[-1] + 0.2, y + 0.2, z - 0.6), 0.25, 0.25, "steel"))
    return p


def mine_building(coll, tag, stage, r, axis, sill_faces, wall="cream", roof="roof_dark"):
    """Cream mine building on steel stilts: stilts, then low walls, then the gabled building."""
    x0, y0, x1, y1 = r; Z = 4.0; H = 12.0
    p = stilts(coll, tag, x0, y0, x1, y1, Z)
    if stage == 0:
        return p
    if stage == 1:
        return p + [box(f"{tag}_walls", coll, x0, y0, Z, x1, y1, Z + 4.5, wall)]
    p.append(box(f"{tag}_walls", coll, x0, y0, Z, x1, y1, H, wall))
    p.append(gable(f"{tag}_roof", coll, x0, y0, x1, y1, H, H + 4.5, roof, axis, 0.4, wall))
    windows(p, coll, tag, r, [Z + 2.6], sill_faces, ww=1.1, wh=1.8, spacing=2.6)
    return p
