"""Bridges and tunnel portals (Phase 8.6); bridge sprites are the same in every climate.

Exec after house_kit.py and industry_kit.py with KEY set and the identity's .blend open.

Bridges are built per tile piece, in one canonical turn the renderer rotates:
- Middle pieces run along local X with the bridge's north end at x = 0. The deck top is z = 0 (the bridge height);
  the renderer still draws the track or road on it. States follow CalcBridgePiece: `north`, `south`, `inner_north`,
  `inner_south`, `middle_odd`, `middle_even`; `middle` stands for every piece a type does not draw differently.
- Pillars are one 8-high segment (z -8..0) that the renderer stacks from the deck down to the ground: `pillar_<piece>`,
  or `pillar` for the pieces `middle` covers. Pieces whose sprites draw no pillars get none.
- Ramps are the northern head of an X bridge, rising along local +X towards the span: `ramp` on a flat tile (deck from
  z = 0 to 8), `ramp_flat` on a foundation (deck level at z = 8).
Tunnel portals face local -X: the entrance is the x = 0 edge, the track runs in at z = 0 and the hill rises to z = 8
at x = 16.
"""
import math

import bpy
from mathutils import Vector

W0, W1 = 1.2, 14.8  # deck width across local Y
SIDES = (1.6, 14.4)  # structure lines on both sides of the deck
T = 1.6  # deck thickness


# ---------------------------------------------------------------- shared parts

def slope_slab(name, coll, x0, x1, y0, y1, z0, z1, t, top, side, taper=False):
    """Deck slab whose top runs from z0 at x0 to z1 at x1. taper: no thickness at x0 (a ramp meeting the ground)."""
    b0 = z0 if taper else z0 - t
    v = [(x0, y0, z0), (x1, y0, z1), (x1, y1, z1), (x0, y1, z0),
         (x0, y0, b0), (x1, y0, z1 - t), (x1, y1, z1 - t), (x0, y1, b0)]
    f = [(0, 1, 2, 3), (7, 6, 5, 4), (4, 5, 1, 0), (6, 7, 3, 2), (5, 6, 2, 1)] + ([] if taper else [(7, 4, 0, 3)])
    return _obj(name, coll, v, f, [top] + [side] * (len(f) - 1))


def deck(p, coll, tag, side, top="wood_dark", z0=0.0, z1=0.0, t=T):
    p.append(slope_slab(f"{tag}_deck", coll, 0, 16, W0, W1, z0, z1, t, top, side))


def parapets(p, coll, tag, mat, z0=0.0, z1=0.0, h=0.9, w=0.4):
    for k, y in enumerate((W0 + w / 2, W1 - w / 2)):
        p.append(beam(f"{tag}_par{k}", coll, (0, y, z0 + h / 2), (16, y, z1 + h / 2), w, h, mat))


def railing(p, coll, tag, mat, z0=0.0, z1=0.0, h=2.0, posts=(2, 6, 10, 14)):
    for k, y in enumerate(SIDES):
        p.append(beam(f"{tag}_rail{k}", coll, (0, y, z0 + h), (16, y, z1 + h), 0.3, 0.3, mat))
        for j, x in enumerate(posts):
            z = z0 + (z1 - z0) * x / 16
            p.append(box(f"{tag}_post{k}{j}", coll, x - 0.15, y - 0.15, z, x + 0.15, y + 0.15, z + h, mat))


def columns(p, coll, tag, mat, x=8.0, r=0.7, ys=(2.6, 13.4)):
    """Pillar segment: one column per side, z -8..0."""
    for k, y in enumerate(ys):
        p.append(box(f"{tag}_col{k}", coll, x - r, y - r, -8, x + r, y + r, 0, mat))


def heads(coll, side, top="wood_dark", pier=None, extra=None):
    """Sloped ramp and ramp on a foundation. extra(p, tag, z0, z1) adds the family's parapet or railing."""
    out = {}
    for state, z0, z1 in (("ramp", 0.0, 8.0), ("ramp_flat", 8.0, 8.0)):
        p, tag = [], state
        p.append(slope_slab(f"{tag}_deck", coll, 0, 16, W0, W1, z0, z1, T, top, side, taper=state == "ramp"))
        if extra:
            extra(p, tag, z0, z1)
        if state == "ramp":
            # Abutment under the high end, as the short post in the head sprites.
            p.append(box(f"{tag}_pier", coll, 11.6, 3.0, 0, 13.6, 13.0, 6.8 - T + 0.1, pier or side))
            p.append(box(f"{tag}_cap", coll, 11.2, 2.4, 6.8 - T - 0.6, 14.0, 13.6, 6.8 - T + 0.1, pier or side))
        out[state] = p
    return out


def rod(name, coll, p0, p1, w, mat):
    """Slender member without end caps (8 triangles): cables, truss bars, hoops."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0).normalized()
    side = d.cross(Vector((0, 0, 1)))
    if side.length < 1e-6:
        side = Vector((1, 0, 0))
    side.normalize(); up = side.cross(d).normalized()
    s, u = side * (w / 2), up * (w / 2)
    corners = [-s - u, s - u, s + u, -s + u]
    v = [tuple(p0 + c) for c in corners] + [tuple(p1 + c) for c in corners]
    return _obj(name, coll, v, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], [mat] * 4)


def arc(p, coll, tag, pts, w, mat):
    for k in range(len(pts) - 1):
        p.append(rod(f"{tag}_{k}", coll, pts[k], pts[k + 1], w, mat))


# ---------------------------------------------------------------- families

def wood(coll):
    def extra(p, tag, z0, z1):
        railing(p, coll, tag, "wood", z0, z1, h=2.4, posts=(1, 3, 5, 7, 9, 11, 13, 15))
        for j, x in enumerate((1.5, 5.5, 9.5, 13.5)):
            z = z0 + (z1 - z0) * x / 16
            if z - 0.9 > 0.5:  # ties stay above the ground where a ramp meets it
                p.append(box(f"{tag}_tie{j}", coll, x - 0.5, 0.2, max(z - 1.9, 0.0), x + 0.5, 15.8, z - 0.9, "wood_dark"))
    mid = []
    deck(mid, coll, "m", "wood")
    extra(mid, "m", 0, 0)
    pil = []
    for j, x in enumerate((4.0, 12.0)):
        columns(pil, coll, f"p{j}", "wood", x=x, r=0.55)
        pil.append(rod(f"p{j}_brace", coll, (x, 2.6, -7.6), (x, 13.4, -0.4), 0.45, "wood_dark"))
    out = heads(coll, "wood", pier="wood", extra=extra)
    out.update(middle=mid, pillar=pil)
    return out


def concrete(coll):
    def extra(p, tag, z0, z1):
        parapets(p, coll, tag, "signal_red", z0, z1, h=0.8, w=0.35)
    mid = []
    deck(mid, coll, "m", "concrete", t=2.0)
    extra(mid, "m", 0, 0)
    pil = []
    columns(pil, coll, "p", "concrete")
    out = heads(coll, "concrete", pier="concrete", extra=extra)
    out.update(middle=mid, pillar=pil)
    return out


def archgirder(coll):
    mid = []
    deck(mid, coll, "m", "concrete_dark")
    parapets(mid, coll, "m", "concrete", h=0.6, w=0.3)
    n = 8
    for k, y in enumerate(SIDES):
        pts = [(8 - 7.6 * math.cos(math.pi * i / n), y, 12.0 * math.sin(math.pi * i / n)) for i in range(n + 1)]
        arc(mid, coll, f"m_arch{k}", pts, 0.7, "concrete")
        for j, x in enumerate((2.6, 4.4, 6.2, 8.0, 9.8, 11.6, 13.4)):
            z = 12.0 * math.sin(math.acos((x - 8) / 7.6))
            mid.append(rod(f"m_hang{k}{j}", coll, (x, y, 0), (x, y, z), 0.25, "concrete"))
    pil = []
    columns(pil, coll, "p", "concrete", r=0.6)
    out = heads(coll, "concrete_dark", pier="concrete",
                extra=lambda p, tag, z0, z1: parapets(p, coll, tag, "concrete", z0, z1, h=0.6, w=0.3))
    out.update(middle=mid, pillar=pil)
    return out


def girder(coll, col, head):
    mid = []
    deck(mid, coll, "m", col)
    H = 9.0
    for k, y in enumerate(SIDES):
        mid.append(beam(f"m_top{k}", coll, (0, y, H), (16, y, H), 0.6, 0.8, col))
        mid.append(beam(f"m_bot{k}", coll, (0, y, 0.5), (16, y, 0.5), 0.6, 1.0, col))
        for j, x in enumerate((0.4, 8.0)):
            mid.append(box(f"m_vert{k}{j}", coll, x - 0.4, y - 0.3, 0, x + 0.4, y + 0.3, H, col))
        for j, (a, b) in enumerate(((0.4, 8.0), (8.0, 15.6))):
            mid.append(rod(f"m_x{k}{j}a", coll, (a, y, 1.0), (b, y, H - 0.4), 0.35, "steel_light"))
            mid.append(rod(f"m_x{k}{j}b", coll, (a, y, H - 0.4), (b, y, 1.0), 0.35, "steel_light"))
    pil = []
    columns(pil, coll, "p", "steel_light", r=0.6)
    out = heads(coll, head, extra=lambda p, tag, z0, z1: parapets(p, coll, tag, head, z0, z1))
    out.update(middle=mid, pillar=pil)
    return out


def suspension(coll, col, head):
    TOP, LEG = 32.0, 0.8

    def tower(p, tag, x):
        for k, y in enumerate((1.4, 14.6)):
            p.append(box(f"{tag}_leg{k}", coll, x - LEG, y - LEG, -T, x + LEG, y + LEG, TOP, col))
        for j, z in enumerate((19.0, TOP - 1.4)):
            p.append(box(f"{tag}_cross{j}", coll, x - 0.6, 2.2, z, x + 0.6, 13.8, z + 1.4, col))

    def fan(p, tag, x_top, xs):
        for k, y in enumerate(SIDES):
            for j, x in enumerate(xs):
                p.append(rod(f"{tag}_c{k}{j}", coll, (x_top, y, TOP - 2.2 - 0.6 * j), (x, y, 0.2), 0.22, "plaster_white"))

    def piece(tag, towers=(), fans=()):
        p = []
        deck(p, coll, tag, col)
        parapets(p, coll, tag, col, h=0.7, w=0.3)
        for x in towers:
            tower(p, f"{tag}_t{x:g}", x)
        for x_top, xs in fans:
            fan(p, f"{tag}_f{x_top:g}", x_top, xs)
        return p

    out = {
        # The towers stand at the outer ends of the north and south pieces; their stays reach back towards the
        # heads, the inner pieces carry the main fans from the same towers.
        "north": piece("n", towers=(15.2,), fans=((15.2, (0.5, 2.2, 3.9, 5.6, 7.3, 9.0, 10.7, 12.4)),)),
        "south": piece("s", towers=(0.8,), fans=((0.8, (15.5, 13.8, 12.1, 10.4, 8.7, 7.0, 5.3, 3.6)),)),
        "inner_north": piece("in", fans=((0.2, (15.5, 13.6, 11.7, 9.8, 7.9, 6.0, 4.1, 2.2)),)),
        "inner_south": piece("is", fans=((15.8, (0.5, 2.4, 4.3, 6.2, 8.1, 10.0, 11.9, 13.8)),)),
        "middle_odd": piece("mo", fans=((0.2, (7.4, 5.6, 3.8, 2.0)), (15.8, (8.6, 10.4, 12.2, 14.0)))),
        "middle_even": piece("me"),
    }
    for state, x in (("pillar_north", 15.2), ("pillar_south", 0.8)):
        p = []
        for k, y in enumerate((1.4, 14.6)):
            p.append(box(f"{state}_leg{k}", coll, x - LEG, y - LEG, -8, x + LEG, y + LEG, 0, col))
        out[state] = p
    out.update(heads(coll, head, extra=lambda p, tag, z0, z1: parapets(p, coll, tag, head, z0, z1, h=0.7, w=0.3)))
    return out


def cantilever(coll, col):
    def height(x, rise):
        """Truss height: 14 in the middle; the end pieces curve down to 6 at the heads."""
        if rise == 0:
            return 14.0
        u = x / 16 if rise > 0 else 1 - x / 16
        return 6.0 + 8.0 * math.sin(math.pi / 2 * u)

    def piece(tag, rise):
        p = []
        deck(p, coll, tag, col)
        xs = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0]
        for k, y in enumerate(SIDES):
            arc(p, coll, f"{tag}_top{k}", [(x, y, height(x, rise)) for x in xs[::2]], 0.8, col)
            for j in range(8):
                lo, hi = (xs[j], xs[j + 1]) if j % 2 == 0 else (xs[j + 1], xs[j])
                p.append(rod(f"{tag}_d{k}{j}", coll, (lo, y, 0.2), (hi, y, height(hi, rise) - 0.2), 0.55, col))
            for j, x in enumerate(xs[1:-1:2]):
                p.append(rod(f"{tag}_v{k}{j}", coll, (x, y, 0), (x, y, height(x, rise)), 0.5, col))
        for j, x in enumerate((0.0, 4.0, 8.0, 12.0)):
            p.append(rod(f"{tag}_tie{j}", coll, (x + 2, SIDES[0], height(x + 2, rise)), (x + 2, SIDES[1], height(x + 2, rise)), 0.5, col))
            p.append(rod(f"{tag}_x{j}", coll, (x, SIDES[0], height(x, rise)), (x + 4, SIDES[1], height(x + 4, rise)), 0.4, col))
        return p

    pil = []
    columns(pil, coll, "p", "steel_light", r=0.8)
    out = {"north": piece("n", 1), "south": piece("s", -1), "middle": piece("m", 0), "pillar": pil,
           "pillar_south": columns_list(coll, "ps", "steel_light", 0.8)}
    out.update(heads(coll, col, extra=lambda p, tag, z0, z1: parapets(p, coll, tag, col, z0, z1, h=0.7, w=0.3)))
    return out


def columns_list(coll, tag, mat, r):
    p = []
    columns(p, coll, tag, mat, r=r)
    return p


def tubular(coll, col, head):
    R = 6.6

    def hoop(p, tag, x, f):
        n = 6
        pts = [(x, 8 - R * math.cos(math.pi * i / n), 0.4 + f * 2.0 * R * math.sin(math.pi * i / n)) for i in range(n + 1)]
        arc(p, coll, tag, pts, 0.55, col)

    def piece(tag, scale):
        p = []
        deck(p, coll, tag, col)
        xs = (1.3, 4.0, 6.7, 9.3, 12.0, 14.7)
        for j, x in enumerate(xs):
            hoop(p, f"{tag}_h{j}", x, scale(x))
        for k, a in enumerate((math.pi / 6, math.pi / 3, math.pi / 2, 2 * math.pi / 3, 5 * math.pi / 6)):
            y = 8 - R * math.cos(a)
            z0, z1 = (0.4 + scale(x) * 2.0 * R * math.sin(a) for x in (0.0, 16.0))
            p.append(rod(f"{tag}_s{k}", coll, (0, y, z0), (16, y, z1), 0.45, col))
        railing(p, coll, tag, col, h=2.2, posts=(1.3, 6.7, 12.0))
        return p

    pil = []
    columns(pil, coll, "p", col, r=0.8)
    out = {"north": piece("n", lambda x: 0.45 + 0.55 * x / 16), "south": piece("s", lambda x: 1.0 - 0.55 * x / 16),
           "middle": piece("m", lambda x: 1.0), "pillar": pil, "pillar_south": columns_list(coll, "ps", col, 0.8)}
    out.update(heads(coll, head, extra=lambda p, tag, z0, z1: parapets(p, coll, tag, head, z0, z1, h=0.7, w=0.3)))
    return out


# ---------------------------------------------------------------- tunnels

def mound(p, coll, tag, x0, crown0, mat, n=6, rows=(2.0, 6.0, 10.0, 14.0, 16.0)):
    """Hill over a portal: cross-sections from the portal top (crown0 at x0) down to the slope at x = 16."""
    secs = []
    for x in rows:
        ground = x / 2
        crown = ground + (crown0 - x0 / 2) * (1 - (x - x0) / (16 - x0)) ** 1.5 + 0.3
        secs.append([(x, 0.4 + 15.2 * i / n, ground + 0.05 + (crown - ground) * math.sin(math.pi * i / n) ** 0.6) for i in range(n + 1)])
    verts = [v for s in secs for v in s]
    faces = []
    for a in range(len(secs) - 1):
        for i in range(n):
            b0, b1 = a * (n + 1), (a + 1) * (n + 1)
            faces.append((b0 + i, b1 + i, b1 + i + 1, b0 + i + 1))
    p.append(_obj(f"{tag}_mound", coll, verts, faces, [mat] * len(faces)))


def tunnel_rail(coll):
    p = []
    D, Y0, Y1, Z1 = 2.0, 0.6, 15.4, 13.0  # portal depth and outer face
    y0, y1, spring = 3.6, 12.4, 7.0  # opening
    r = (y1 - y0) / 2
    n = 8
    inner = [(8 + r * math.cos(math.pi * i / n), spring + r * math.sin(math.pi * i / n)) for i in range(n + 1)]
    for x, name in ((0.0, "front"), (D, "back")):
        verts, faces = [], []
        for i, (y, z) in enumerate(inner):
            verts += [(x, y, z), (x, y, Z1)]
        for i in range(n):
            faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) if x == 0 else (2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
        p.append(_obj(f"t_{name}", coll, verts, faces, ["stone"] * n))
    soffit = []
    for i, (y, z) in enumerate(inner):
        soffit += [(0, y, z), (D, y, z)]
    p.append(_obj("t_soffit", coll, soffit, [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(n)], ["stone_dark"] * n))
    for k, (a, b) in enumerate(((Y0, y0), (y1, Y1))):
        p.append(box(f"t_pier{k}", coll, 0, a, 0, D, b, Z1, "stone"))
    p.append(box("t_coping", coll, -0.3, Y0 - 0.3, Z1, D + 0.3, Y1 + 0.3, Z1 + 0.8, "stone_dark"))
    p.append(box("t_keystone", coll, -0.2, 7.2, spring + r - 0.6, 0.2, 8.8, spring + r + 1.0, "stone_dark"))
    # Dark interior just inside the arch.
    dark = [(D + 0.3, y, z) for y, z in inner] + [(D + 0.3, y0, 0), (D + 0.3, y1, 0)]
    p.append(_obj("t_dark", coll, dark, [tuple([n + 2] + list(range(n, -1, -1)) + [n + 1])], ["black"]))
    mound(p, coll, "t", D, Z1 + 0.8, "turf")
    return {"default": p}


def tunnel_road(coll):
    p = []
    D, Y0, Y1, Z1 = 2.0, 0.6, 15.4, 11.0
    y0, y1, top = 2.4, 13.6, 9.0
    for k, (a, b) in enumerate(((Y0, y0), (y1, Y1))):
        p.append(box(f"t_wall{k}", coll, 0, a, 0, D, b, Z1, "concrete"))
    p.append(box("t_lintel", coll, 0, y0, top, D, y1, Z1, "concrete"))
    p.append(box("t_band", coll, -0.25, Y0 - 0.25, Z1 - 1.2, D + 0.25, Y1 + 0.25, Z1, "concrete_dark"))
    for k, y in enumerate((y0 + 0.6, y1 - 0.6)):
        p.append(box(f"t_lamp{k}", coll, -0.15, y - 0.4, top - 1.2, 0.1, y + 0.4, top - 0.7, "lamp_yellow"))
    p.append(_obj("t_dark", coll, [(D + 0.3, y0, 0), (D + 0.3, y1, 0), (D + 0.3, y1, top), (D + 0.3, y0, top)], [(3, 2, 1, 0)], ["black"]))
    p.append(slope_slab("t_roof", coll, D, 16, 1.0, 15.0, Z1, 8.6, 0.8, "concrete", "concrete_dark"))
    for k, y in enumerate((1.0, 15.0)):
        sign = -1 if k == 0 else 1
        v = [(D, y, 0), (16, y, 8.0), (16, y, 8.6), (D, y, Z1)]
        p.append(_obj(f"t_side{k}", coll, v, [(0, 1, 2, 3) if sign < 0 else (3, 2, 1, 0)], ["concrete_dark"]))
    return {"default": p}


# ---------------------------------------------------------------- identities

BUILD = {
    "bridge_00": lambda c: wood(c),
    "bridge_01": lambda c: concrete(c),
    "bridge_02": lambda c: archgirder(c),
    "bridge_03": lambda c: suspension(c, "steel_blue", "steel_blue"),
    "bridge_04": lambda c: suspension(c, "oxide", "oxide_light"),
    "bridge_05": lambda c: suspension(c, "steel_yellow", "steel_yellow"),
    "bridge_06": lambda c: cantilever(c, "oxide_light"),
    "bridge_07": lambda c: cantilever(c, "steel_brown"),
    "bridge_08": lambda c: cantilever(c, "steel_red"),
    "bridge_09": lambda c: girder(c, "oxide", "oxide_light"),
    "bridge_10": lambda c: tubular(c, "oxide", "oxide_light"),
    "bridge_11": lambda c: tubular(c, "steel_yellow", "steel_yellow"),
    "bridge_12": lambda c: tubular(c, "steel_blue", "steel_blue"),
    "tunnel_rail": tunnel_rail,
    "tunnel_road": tunnel_road,
}


# ---------------------------------------------------------------- build

sync_palette()
scene_root = bpy.data.scenes["model"].collection
for c in list(scene_root.children):
    if not c.name.startswith('_') and c.name != 'reference':
        clear(c)
base = bpy.data.collections.get("default") or bpy.data.collections.new("default")
if base.name not in scene_root.children:
    scene_root.children.link(base)
states = BUILD[KEY](base)
result = {}
for state, parts in states.items():
    coll = state_coll(state)
    for o in parts:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    ob = join(f"{KEY}_{state}", parts) if len(parts) > 1 else parts[0]
    result[state] = tris(ob)
if "default" not in states:
    scene_root.children.unlink(base)
