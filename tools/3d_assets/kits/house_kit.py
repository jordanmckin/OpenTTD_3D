"""House kit: primitives and building helpers for the static house models (Phase 8.4 pilot, 8.6 production).

Run inside Blender with the house's .blend open; member scripts (houses_temperate.py) call make() to rebuild
the four state collections. Units: 1 = one world pixel, a tile is 16 x 16, origin at the north corner, +X towards
the bottom-left and +Y towards the bottom-right of the classic view.
"""
import json
import math
import random

import bpy
from mathutils import Vector

STATES = ("construction_0", "construction_1", "construction_2", "complete")
OFF = 0.06


# --- primitives ---

def _obj(name, coll, verts, faces, mats):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    order = list(dict.fromkeys(mats))
    for m in order:
        me.materials.append(bpy.data.materials[m])
    idx = {m: i for i, m in enumerate(order)}
    for p, m in zip(me.polygons, mats):
        p.material_index = idx[m]
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def box(name, coll, x0, y0, z0, x1, y1, z1, mat, bottom=False):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)] + ([(3, 2, 1, 0)] if bottom else [])
    return _obj(name, coll, v, f, [mat] * len(f))


def gable(name, coll, x0, y0, x1, y1, z0, z1, mat, along='y', over=0.0, gable_mat=None):
    """Gable roof over [x0,x1]x[y0,y1], eaves z0, ridge z1, ridge along the given axis; gable ends in gable_mat."""
    gm = gable_mat or mat
    if along == 'y':
        x0 -= over; x1 += over; xm = (x0 + x1) / 2
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (xm, y0, z1), (xm, y1, z1)]
        f = [(0, 4, 5, 3), (1, 2, 5, 4), (0, 1, 4), (2, 3, 5)]
    else:
        y0 -= over; y1 += over; ym = (y0 + y1) / 2
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, ym, z1), (x1, ym, z1)]
        f = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)]
    return _obj(name, coll, v, f, [mat, mat, gm, gm])


def hip(name, coll, x0, y0, x1, y1, z0, z1, mat, inset):
    """Hipped roof; ridge along the longer axis, inset from the ends."""
    if (x1 - x0) >= (y1 - y0):
        ym = (y0 + y1) / 2
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0 + inset, ym, z1), (x1 - inset, ym, z1)]
        f = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)]
    else:
        xm = (x0 + x1) / 2
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (xm, y0 + inset, z1), (xm, y1 - inset, z1)]
        f = [(0, 1, 4), (2, 3, 5), (1, 2, 5, 4), (3, 0, 4, 5)]
    return _obj(name, coll, v, f, [mat] * 4)


def pyramid(name, coll, x0, y0, x1, y1, z0, z1, mat):
    c = ((x0 + x1) / 2, (y0 + y1) / 2, z1)
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), c]
    return _obj(name, coll, v, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], [mat] * 4)


def mansard(name, coll, x0, y0, x1, y1, z0, z1, inset, mat, top):
    a, b, c, d = x0 + inset, y0 + inset, x1 - inset, y1 - inset
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (a, b, z1), (c, b, z1), (c, d, z1), (a, d, z1)]
    return _obj(name, coll, v, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], [mat] * 4 + [top])


def vault(name, coll, x0, y0, x1, y1, z0, rise, mat, along='x', segs=6, end_mat=None):
    """Barrel vault over the rectangle, springing at z0, axis along X or Y; closed ends in end_mat."""
    em = end_mat or mat
    if along == 'x':
        w0, w1, a0, a1 = y0, y1, x0, x1
        P = lambda a, w, z: (a, w, z)
    else:
        w0, w1, a0, a1 = x0, x1, y0, y1
        P = lambda a, w, z: (w, a, z)
    arc = [(w0 + (w1 - w0) * (1 - math.cos(math.pi * i / segs)) / 2, z0 + rise * math.sin(math.pi * i / segs)) for i in range(segs + 1)]
    v = [P(a0, w, z) for w, z in arc] + [P(a1, w, z) for w, z in arc]
    n = segs + 1
    f = [(i, i + 1, n + i + 1, n + i) for i in range(segs)]
    m = [mat] * segs
    f += [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    m += [em, em]
    ob = _obj(name, coll, v, f, m)
    if along == 'y':  # P swaps the axes, so the winding flips
        ob.data.flip_normals()
    return ob


def loft(name, coll, x0, y0, x1, y1, rings, mat, top=None):
    """Four-sided walls through rings [(z, inset), ...] bottom to top (insets may be negative to bulge); optional top cap."""
    v, f, m = [], [], []
    for z, d in rings:
        v += [(x0 + d, y0 + d, z), (x1 - d, y0 + d, z), (x1 - d, y1 - d, z), (x0 + d, y1 - d, z)]
    for k in range(len(rings) - 1):
        a, b = 4 * k, 4 * (k + 1)
        for i in range(4):
            j = (i + 1) % 4
            f.append((a + i, a + j, b + j, b + i)); m.append(mat)
    if top:
        t = 4 * (len(rings) - 1)
        f.append((t, t + 1, t + 2, t + 3)); m.append(top)
    return _obj(name, coll, v, f, m)


def lathe(name, coll, cx, cy, profile, n, mat, cap=None, inner=None, phase=0.0):
    """Surface of revolution about a vertical axis. profile: [(z, r), ...] bottom to top.
    mat: one material, or a list with one per profile segment. cap: material for a disc closing the top;
    inner: (depth, mat) for a dark inner wall below the open top. phase: start angle in radians."""
    mats = mat if isinstance(mat, list) else [mat] * (len(profile) - 1)
    ang = lambda i: phase + 2 * math.pi * i / n
    v, f, m = [], [], []
    rings = []
    for z, r in profile:
        rings.append(len(v))
        if r == 0:  # a point: the faces meeting it are triangles
            v.append((cx, cy, z))
        else:
            v += [(cx + r * math.cos(ang(i)), cy + r * math.sin(ang(i)), z) for i in range(n)]
    for k, (a, b) in enumerate(zip(rings, rings[1:])):
        pa, pb = profile[k][1] == 0, profile[k + 1][1] == 0
        for i in range(n):
            j = (i + 1) % n
            if pb:
                f.append((a + i, a + j, b))
            elif pa:
                f.append((a, b + j, b + i))
            else:
                f.append((a + i, a + j, b + j, b + i))
            m.append(mats[k])
    top = rings[-1]; zt, rt = profile[-1]
    if cap and rt > 0:
        f.append(tuple(top + i for i in range(n))); m.append(cap)
    if inner:
        depth, imat = inner
        b = len(v); r2 = rt * 0.92
        v += [(cx + r2 * math.cos(ang(i)), cy + r2 * math.sin(ang(i)), zt - depth) for i in range(n)]
        for i in range(n):
            j = (i + 1) % n
            f.append((top + j, top + i, b + i, b + j)); m.append(imat)
        f.append(tuple(b + i for i in range(n))); m.append(imat)
    return _obj(name, coll, v, f, m)


def prism(name, coll, cx, cy, r, z0, z1, n, mat, cap=None, phase=0.0):
    return lathe(name, coll, cx, cy, [(z0, r), (z1, r)], n, mat, cap=cap or mat, phase=phase)


def beam(name, coll, p0, p1, w, h, mat):
    """Box from p0 to p1 with a w-wide horizontal and h-high vertical cross-section."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0).normalized()
    side = d.cross(Vector((0, 0, 1)))
    if side.length < 1e-6:
        side = Vector((1, 0, 0))
    side.normalize(); up = side.cross(d).normalized()
    s, u = side * (w / 2), up * (h / 2)
    corners = [-s - u, s - u, s + u, -s + u]
    v = [tuple(p0 + c) for c in corners] + [tuple(p1 + c) for c in corners]
    f = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (3, 2, 1, 0), (4, 5, 6, 7)]
    return _obj(name, coll, v, f, [mat] * 6)


def heap(name, coll, cx, cy, rx, ry, h, mat, n=7, seed=0):
    """Low irregular cone: a coal or spoil heap, or a hedge mound."""
    rnd = random.Random(seed)
    v = [(cx + rx * (0.8 + 0.3 * rnd.random()) * math.cos(2 * math.pi * i / n), cy + ry * (0.8 + 0.3 * rnd.random()) * math.sin(2 * math.pi * i / n), 0.1) for i in range(n)]
    v.append((cx + rnd.uniform(-0.3, 0.3) * rx, cy + rnd.uniform(-0.3, 0.3) * ry, h))
    return _obj(name, coll, v, [(i, (i + 1) % n, n) for i in range(n)], [mat] * n)


def join(name, objs):
    ctx = bpy.context
    with ctx.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
        bpy.ops.object.join()
    objs[0].name = name; objs[0].data.name = name
    return objs[0]


def clear(coll):
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def sync_palette():
    """Add palette colours created after this .blend was made, exactly as new_blend.py makes them."""
    pal = json.load(open(r"D:\G ttd\OpenTTD-15.3\OpenTTD-15.3\assets\3d\blender\palette.json", encoding="utf-8"))["colours"]
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    added = []
    for name, rgb in pal.items():
        if name in bpy.data.materials:
            continue
        mat = bpy.data.materials.new(name)
        linear = [lin(c) for c in rgb] + [1.0]
        mat.diffuse_color = linear
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = linear
            bsdf.inputs['Roughness'].default_value = 1.0
        mat.use_fake_user = True
        added.append(name)
    return added


# --- building helpers ---

def quad(name, coll, face, at, a0, a1, z0, z1, mat, off=OFF):
    """Flat panel just proud of a wall. face: '+x','-x','+y','-y'; at = wall coordinate; a0..a1 along the wall."""
    d = off if face[0] == '+' else -off
    if face[1] == 'x':
        X = at + d
        v = [(X, a0, z0), (X, a1, z0), (X, a1, z1), (X, a0, z1)]
    else:
        Y = at + d
        v = [(a1, Y, z0), (a0, Y, z0), (a0, Y, z1), (a1, Y, z1)]
    if face[0] == '-':
        v = v[::-1]
    return _obj(name, coll, v, [(0, 1, 2, 3)], [mat])


def slab(name, coll, x0, y0, x1, y1, mat, z=0.12):
    return _obj(name, coll, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [(0, 1, 2, 3)], [mat])


def faces_of(r):
    x0, y0, x1, y1 = r
    return {'+x': (x1, y0, y1), '-x': (x0, y0, y1), '+y': (y1, x0, x1), '-y': (y0, x0, x1)}


def windows(parts, coll, tag, r, sills, faces='+x-x+y-y', ww=1.2, wh=2.0, spacing=3.2, mat="window_blue", skip=()):
    for f, (at, a0, a1) in faces_of(r).items():
        if f not in faces:
            continue
        n = max(1, int((a1 - a0) // spacing))
        step = (a1 - a0) / n
        for i in range(n):
            c = a0 + step * (i + 0.5)
            for j, s in enumerate(sills):
                if (f, i, j) in skip:
                    continue
                parts.append(quad(f"{tag}_w{f}{i}_{j}", coll, f, at, c - ww / 2, c + ww / 2, s, s + wh, mat))


def bands(parts, coll, tag, r, zs, mat, t=0.5, out=0.15, over=None):
    """Horizontal bands (floor lines, cornices) wrapped round a block: one thin box per height.
    over: {face: mat} overlays a differently coloured strip on those faces."""
    x0, y0, x1, y1 = r
    for k, z in enumerate(zs):
        parts.append(box(f"{tag}_band{k}", coll, x0 - out, y0 - out, z, x1 + out, y1 + out, z + t, mat))
        for f, m in (over or {}).items():
            o, e = out, out + 0.05
            rect = {'+x': (x1 + o, y0 - o, x1 + e, y1 + o), '-x': (x0 - e, y0 - o, x0 - o, y1 + o),
                    '+y': (x0 - o, y1 + o, x1 + o, y1 + e), '-y': (x0 - o, y0 - e, x1 + o, y0 - o)}[f]
            parts.append(box(f"{tag}_band{k}{f}", coll, rect[0], rect[1], z, rect[2], rect[3], z + t, m))


def pilasters(parts, coll, tag, r, z0, z1, n, mat, faces='+x+y-x-y', w=0.6, out=0.2):
    """n vertical strips per face, including the corners."""
    for f, (at, a0, a1) in faces_of(r).items():
        if f not in faces:
            continue
        for i in range(n):
            a = a0 + (a1 - a0) * i / (n - 1)
            lo, hi = max(a0, a - w / 2), min(a1, a + w / 2)
            d = out if f[0] == '+' else -out
            if f[1] == 'x':
                xa, xb = sorted((at, at + d))
                parts.append(box(f"{tag}_pil{f}{i}", coll, xa, lo, z0, xb, hi, z1, mat))
            else:
                ya, yb = sorted((at, at + d))
                parts.append(box(f"{tag}_pil{f}{i}", coll, lo, ya, z0, hi, yb, z1, mat))


def railing(parts, coll, tag, r, z, mat="steel_light", h=1.2, posts=4):
    """Rooftop guard rail round a rectangle: top rail plus a few posts per side."""
    x0, y0, x1, y1 = r; t = 0.15
    for n, (a, b, c, d) in enumerate([(x0, y0, x1, y0 + t), (x0, y1 - t, x1, y1), (x0, y0, x0 + t, y1), (x1 - t, y0, x1, y1)]):
        parts.append(box(f"{tag}_rail{n}", coll, a, b, z + h - 0.2, c, d, z + h, mat))
        for i in range(posts):
            u = i / (posts - 1)
            px, py = a + (c - a) * u, b + (d - b) * u
            parts.append(box(f"{tag}_rp{n}_{i}", coll, px - 0.08, py - 0.08, z, px + 0.08, py + 0.08, z + h, mat))


def roof(parts, coll, tag, b):
    x0, y0, x1, y1 = b['r']; h = b['h']; rf = b.get('roof')
    if not rf:
        return
    kind = rf[0]
    if kind == 'gable':   # ('gable', axis, rise, mat, overhang)
        parts.append(gable(f"{tag}_roof", coll, x0, y0, x1, y1, h, h + rf[2], rf[3], rf[1], rf[4] if len(rf) > 4 else 0.4, b.get('gable_mat', b['wall'])))
    elif kind == 'hip':   # ('hip', rise, mat, inset)
        parts.append(hip(f"{tag}_roof", coll, x0 - 0.3, y0 - 0.3, x1 + 0.3, y1 + 0.3, h, h + rf[1], rf[2], rf[3]))
    elif kind == 'pyr':
        parts.append(pyramid(f"{tag}_roof", coll, x0 - 0.3, y0 - 0.3, x1 + 0.3, y1 + 0.3, h, h + rf[1], rf[2]))
    elif kind == 'mansard':  # ('mansard', rise, mat, inset, top_mat)
        parts.append(mansard(f"{tag}_roof", coll, x0 - 0.3, y0 - 0.3, x1 + 0.3, y1 + 0.3, h, h + rf[1], rf[3], rf[2], rf[4]))
    elif kind == 'vault':  # ('vault', axis, rise, mat)
        parts.append(vault(f"{tag}_roof", coll, x0 - 0.2, y0 - 0.2, x1 + 0.2, y1 + 0.2, h, rf[2], rf[3], rf[1], 4, b['wall']))
    elif kind == 'flat':  # ('flat', roof_mat, parapet_mat)
        parts.append(box(f"{tag}_roofslab", coll, x0 + 0.5, y0 + 0.5, h, x1 - 0.5, y1 - 0.5, h + 0.15, rf[1]))
        t = 0.5
        for n, (a, bb, c, d) in enumerate([(x0, y0, x1, y0 + t), (x0, y1 - t, x1, y1), (x0, y0 + t, x0 + t, y1 - t), (x1 - t, y0 + t, x1, y1 - t)]):
            parts.append(box(f"{tag}_parapet{n}", coll, a, bb, h, c, d, h + 0.8, rf[2]))


def building(coll, tag, blocks):
    parts = []
    for n, b in enumerate(blocks):
        x0, y0, x1, y1 = b['r']
        parts.append(box(f"{tag}_b{n}", coll, x0, y0, b.get('z0', 0), x1, y1, b['h'], b['wall']))
        roof(parts, coll, f"{tag}_b{n}", b)
        for f, mat in b.get('clad', {}).items():
            at, a0, a1 = faces_of(b['r'])[f]
            parts.append(quad(f"{tag}_b{n}_clad{f}", coll, f, at, a0, a1, b.get('z0', 0), b['h'], mat, 0.03))
        for k, (f, a, z) in enumerate(b.get('doors', ())):
            at = faces_of(b['r'])[f][0]
            parts.append(quad(f"{tag}_b{n}_door{k}", coll, f, at, a - 0.7, a + 0.7, z, z + 2.6, b.get('door', 'wood_dark')))
        if b.get('sills'):
            windows(parts, coll, f"{tag}_b{n}", b['r'], b['sills'], b.get('faces', '+x-x+y-y'), b.get('ww', 1.2), b.get('wh', 2.0), b.get('spacing', 3.2), b.get('win', 'window_blue'), b.get('skip', ()))
        if b.get('bands'):
            bands(parts, coll, f"{tag}_b{n}", b['r'], b['bands'], b.get('band_mat', 'concrete'), b.get('band_t', 0.5), over=b.get('band_over'))
        if b.get('pilasters'):
            pilasters(parts, coll, f"{tag}_b{n}", b['r'], b.get('z0', 0), b['h'], b['pilasters'], b.get('pil_mat', b.get('band_mat', 'concrete')), b.get('pil_faces', '+x+y-x-y'))
        for k, ch in enumerate(b.get('chimneys', ())):
            cx, cy, top = ch
            parts.append(box(f"{tag}_b{n}_ch{k}", coll, cx - 0.6, cy - 0.6, b['h'], cx + 0.6, cy + 0.6, top, b.get('chimney', 'brick_dark')))
    return parts


def shell(coll, tag, blocks, frac, t=0.6, cap=None):
    """Open walls with gaps for the construction stages: each side split around a central opening."""
    parts = []
    for n, b in enumerate(blocks):
        x0, y0, x1, y1 = b['r']; z0 = b.get('z0', 0)
        if z0 > 0:
            continue  # roof-level blocks have no shell of their own
        h = min(b['h'] * frac, cap) if cap else b['h'] * frac
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2; g = 0.9
        segs = [(x0, y0, mx - g, y0 + t), (mx + g, y0, x1, y0 + t), (x0, y1 - t, mx - g, y1), (mx + g, y1 - t, x1, y1),
                (x0, y0 + t, x0 + t, my - g), (x0, my + g, x0 + t, y1 - t), (x1 - t, y0 + t, x1, my - g), (x1 - t, my + g, x1, y1 - t)]
        for k, (a, bb, c, d) in enumerate(segs):
            if c - a > 0.05 and d - bb > 0.05:
                parts.append(box(f"{tag}_s{n}_{k}", coll, a, bb, 0, c, d, h, b.get('shell', b['wall'])))
    return parts


def frame(parts, coll, tag, r, z0, z1, floors, mat="steel", w=0.3):
    """Open steel frame: corner posts and a ring of beams at each floor height (construction stages)."""
    x0, y0, x1, y1 = r
    for k, (x, y) in enumerate([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]):
        parts.append(box(f"{tag}_post{k}", coll, x - w, y - w, z0, x + w, y + w, z1, mat))
    for k, z in enumerate(floors):
        parts.append(loft(f"{tag}_ring{k}", coll, x0, y0, x1, y1, [(z, 0), (z + w * 1.5, 0)], mat))


def fence(parts, coll, tag, edges, mat="wood_dark", post="wood", h=2.0, posts=5):
    """Picket/rail fence along tile edges: list of (x0, y0, x1, y1) thin rectangles."""
    for n, (x0, y0, x1, y1) in enumerate(edges):
        parts.append(box(f"{tag}_rail{n}", coll, x0, y0, h - 0.4, x1, y1, h, mat))
        parts.append(box(f"{tag}_raillow{n}", coll, x0, y0, 0.6, x1, y1, 0.9, mat))
        for i in range(posts):
            t = i / (posts - 1)
            if x1 - x0 > y1 - y0:
                x, y = x0 + t * (x1 - x0), (y0 + y1) / 2
            else:
                x, y = (x0 + x1) / 2, y0 + t * (y1 - y0)
            parts.append(box(f"{tag}_post{n}_{i}", coll, x - 0.15, y - 0.15, 0, x + 0.15, y + 0.15, h + 0.3, post))


def flowers(parts, coll, tag, pts):
    cols = ["signal_red", "lamp_yellow", "window_blue", "plaster_white"]
    for n, (x, y) in enumerate(pts):
        parts.append(box(f"{tag}_fl{n}", coll, x - 0.25, y - 0.25, 0.1, x + 0.25, y + 0.25, 0.5, cols[n % 4]))


def blob_tree(parts, coll, tag, x, y, trunk_h, crown_r, crown_h, leaf="leaf", bark="bark", n=7, trunk_r=0.5, lobes=1, seed=0):
    """Deciduous tree: trunk plus one or more low-poly ellipsoid crown lobes."""
    parts.append(prism(f"{tag}_trunk", coll, x, y, trunk_r, 0, trunk_h + crown_h * 0.3, 5, bark))
    rnd = random.Random(seed)
    for k in range(lobes):
        cx, cy = x, y
        r, h, z = crown_r, crown_h, trunk_h
        if k:
            a = rnd.uniform(0, 2 * math.pi)
            cx += math.cos(a) * crown_r * 0.45; cy += math.sin(a) * crown_r * 0.45
            r *= 0.7; h *= 0.6; z += crown_h * rnd.uniform(0.25, 0.5)
        prof = [(z, r * 0.45), (z + h * 0.25, r * 0.95), (z + h * 0.55, r), (z + h * 0.85, r * 0.65), (z + h, 0)]
        parts.append(lathe(f"{tag}_crown{k}", coll, cx, cy, prof, n, leaf, phase=rnd.uniform(0, 1)))


def conifer(parts, coll, tag, x, y, h, r, leaf="leaf_dark", bark="bark", tiers=4, n=7):
    """Stacked cones on a short trunk."""
    parts.append(prism(f"{tag}_trunk", coll, x, y, r * 0.12, 0, h * 0.2, 5, bark))
    for k in range(tiers):
        z0 = h * (0.12 + 0.2 * k)
        rr = r * (1 - 0.2 * k)
        top = h if k == tiers - 1 else z0 + h * 0.36
        parts.append(lathe(f"{tag}_tier{k}", coll, x, y, [(z0, rr * 0.55), (z0 + (top - z0) * 0.12, rr), (top, 0)], n, leaf, phase=0.4 * k))


# --- assembly ---

def make(blocks, garden=None, c0=0.25, c1=0.6, cap1=None, stages=None):
    """Rebuild the four state collections. Default stages: low open shell, taller shell, building, building plus garden.
    stages maps a state name to fn(coll) -> parts, replacing that default. Returns triangles per state."""
    C = bpy.data.collections
    build = {
        "construction_0": lambda coll: shell(coll, "c0", blocks, c0, cap=1.8),
        "construction_1": lambda coll: shell(coll, "c1", blocks, c1, cap=cap1),
        "construction_2": lambda coll: building(coll, "c2", blocks),
        "complete": lambda coll: building(coll, "done", blocks) + (garden(coll) if garden else []),
    }
    build.update(stages or {})
    out = {}
    for s in STATES:
        clear(C[s])
        out[s] = join(s, build[s](C[s]))
    return {s: sum(len(p.vertices) - 2 for p in o.data.polygons) for s, o in out.items()}
