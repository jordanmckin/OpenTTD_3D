"""Temperate stations, stops, depots, docks, buoy and canal lock (Phase 8.6).

Exec after house_kit.py and industry_kit.py with KEY set and the identity's .blend open. Every piece is one tile,
in a canonical turn that the renderer rotates:
- Rail station tiles and waypoints: track along local X through y = 8, platforms on both sides. The renderer still
  draws the track; the models leave the track bed clear. Large-building roof A is the north tile of a two-tile shed
  (rising from pillars at y = 0), roof B the south tile (falling to a brick arcade at y = 16).
- Drive-through stops and road waypoints: road along local X. Bay stops and depots: the entrance faces +Y.
- Dock: land tile (sloping down towards +Y; the renderer lays it on the slope) and the water tile beyond it.
- Ship depot: two tiles along local X, north part first. Canal lock: three tiles rising towards +Y, lower, middle
  and upper, each piece relative to its own tile's base height (the upper water is 8 above the lower).
Station glass is left open (frames and glazing bars only) so trains stay visible under the roofs, as the
transparent roof sprites do. `cc1` marks the owner's colour, as the sprites' company-colour remap does.
"""
import math
import random

import bmesh
import bpy

PLAT = 1.8  # platform height
FRONT, REAR = (11.4, 15.8), (0.2, 4.6)  # platform strips across the track


# ---------------------------------------------------------------- shared parts

def platform(p, coll, tag, y0, y1, x0=0.0, x1=16.0):
    """Platform block with a pale edge line on the track side."""
    p.append(box(f"{tag}_body", coll, x0, y0, 0, x1, y1, PLAT, "concrete"))
    edge = y1 - 0.5 if y0 < 8 else y0 + 0.1
    p.append(slab(f"{tag}_edge", coll, x0, edge, x1, edge + 0.4, "hazard_yellow", PLAT + 0.03))
    face = '+y' if y0 < 8 else '-y'
    p.append(quad(f"{tag}_face", coll, face, y1 if y0 < 8 else y0, x0, x1, 0, PLAT - 0.3, "concrete_dark"))


def bench(p, coll, tag, x, y, z=PLAT, along='x'):
    w, d = (1.8, 0.6) if along == 'x' else (0.6, 1.8)
    p.append(box(f"{tag}_seat", coll, x - w / 2, y - d / 2, z + 0.7, x + w / 2, y + d / 2, z + 0.95, "wood"))
    for k, s in enumerate((-0.7, 0.7)):
        lx, ly = (x + s, y) if along == 'x' else (x, y + s)
        p.append(box(f"{tag}_leg{k}", coll, lx - 0.12, ly - 0.12, z, lx + 0.12, ly + 0.12, z + 0.7, "wood_dark"))


def sign(p, coll, tag, x, y, z=PLAT, along='x', w=2.2, h=4.2):
    """Station name board on two posts, in the owner's colour."""
    for k, s in enumerate((-w / 2 + 0.2, w / 2 - 0.2)):
        lx, ly = (x + s, y) if along == 'x' else (x, y + s)
        p.append(box(f"{tag}_post{k}", coll, lx - 0.1, ly - 0.1, z, lx + 0.1, ly + 0.1, z + h, "steel_light"))
    if along == 'x':
        p.append(box(f"{tag}_board", coll, x - w / 2, y - 0.12, z + h - 1.3, x + w / 2, y + 0.12, z + h, "cc1"))
    else:
        p.append(box(f"{tag}_board", coll, x - 0.12, y - w / 2, z + h - 1.3, x + 0.12, y + w / 2, z + h, "cc1"))


def lamp(p, coll, tag, x, y, z=0.0, h=5.5, head="lamp_yellow"):
    p.append(box(f"{tag}_pole", coll, x - 0.12, y - 0.12, z, x + 0.12, y + 0.12, z + h, "steel"))
    p.append(box(f"{tag}_head", coll, x - 0.35, y - 0.35, z + h, x + 0.35, y + 0.35, z + h + 0.5, head))


def bollards(p, coll, tag, x0, y0, x1, y1, n, mat="cc1", h=1.0):
    for i in range(n):
        t = i / (n - 1)
        x, y = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        p.append(box(f"{tag}_{i}", coll, x - 0.18, y - 0.18, 0, x + 0.18, y + 0.18, h, mat))


def crates(p, coll, tag, x, y, seed, n=3, mat=("wood", "wood_dark", "cream")):
    rnd = random.Random(seed)
    for i in range(n):
        s = rnd.uniform(1.0, 1.5)
        cx, cy = x + rnd.uniform(-1.2, 1.2), y + rnd.uniform(-1.2, 1.2)
        z = 0 if i < 2 else s * 0.9
        p.append(box(f"{tag}_{i}", coll, cx - s / 2, cy - s / 2, z, cx + s / 2, cy + s / 2, z + s * 0.9, rnd.choice(mat)))


def chainlink(p, coll, tag, x0, y0, x1, y1, h=3.0, posts=5):
    """Wire fence: thin dark mesh panel on steel posts."""
    along_x = abs(x1 - x0) > abs(y1 - y0)
    if along_x:
        p.append(box(f"{tag}_mesh", coll, x0, y0 - 0.04, 0.2, x1, y0 + 0.04, h, "steel"))
    else:
        p.append(box(f"{tag}_mesh", coll, x0 - 0.04, y0, 0.2, x0 + 0.04, y1, h, "steel"))
    for i in range(posts):
        t = i / (posts - 1)
        x, y = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        p.append(box(f"{tag}_post{i}", coll, x - 0.12, y - 0.12, 0, x + 0.12, y + 0.12, h + 0.2, "wood_dark"))


def shelter(p, coll, tag, r, h=4.2, back='-y'):
    """Bus shelter: glass back wall, roof in the owner's colour, posts and a bench."""
    x0, y0, x1, y1 = r
    along_x = (x1 - x0) >= (y1 - y0)
    for k, (x, y) in enumerate([(x0 + 0.3, y0 + 0.3), (x1 - 0.3, y0 + 0.3), (x1 - 0.3, y1 - 0.3), (x0 + 0.3, y1 - 0.3)]):
        p.append(box(f"{tag}_post{k}", coll, x - 0.12, y - 0.12, 0, x + 0.12, y + 0.12, h, "steel_light"))
    p.append(box(f"{tag}_roof", coll, x0 - 0.2, y0 - 0.2, h, x1 + 0.2, y1 + 0.2, h + 0.35, "cc1"))
    wall = {'-y': (x0 + 0.3, y0 + 0.2, x1 - 0.3, y0 + 0.4), '+y': (x0 + 0.3, y1 - 0.4, x1 - 0.3, y1 - 0.2),
            '-x': (x0 + 0.2, y0 + 0.3, x0 + 0.4, y1 - 0.3), '+x': (x1 - 0.4, y0 + 0.3, x1 - 0.2, y1 - 0.3)}[back]
    p.append(box(f"{tag}_glass", coll, wall[0], wall[1], 0.6, wall[2], wall[3], h - 0.3, "glass"))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    off = {'-y': (0, -0.5), '+y': (0, 0.5), '-x': (-0.5, 0), '+x': (0.5, 0)}[back]
    bench(p, coll, f"{tag}_bench", cx + off[0] * (x1 - x0) * 0.5, cy + off[1] * (y1 - y0) * 0.5, 0, 'x' if along_x else 'y')


def open_roof(p, coll, tag, x0, x1, prof, ribs=5, bars=7, rib_mat="steel_light", bar_mat="cc1"):
    """Open glazed roof along X: steel ribs across at `ribs` stations, glazing bars along X following the
    profile [(y, z), ...] at `bars` points spread over it."""
    for i in range(ribs):
        x = x0 + (x1 - x0) * i / (ribs - 1)
        x = min(max(x, x0 + 0.2), x1 - 0.2)
        for k, ((ya, za), (yb, zb)) in enumerate(zip(prof, prof[1:])):
            p.append(beam(f"{tag}_rib{i}_{k}", coll, (x, ya, za), (x, yb, zb), 0.3, 0.45, rib_mat))
    # glazing bars: sample the profile evenly by length
    seg = [math.hypot(yb - ya, zb - za) for (ya, za), (yb, zb) in zip(prof, prof[1:])]
    total = sum(seg)
    for j in range(bars):
        d = total * j / (bars - 1)
        for k, L in enumerate(seg):
            if d <= L + 1e-6 or k == len(seg) - 1:
                t = min(1.0, d / L)
                (ya, za), (yb, zb) = prof[k], prof[k + 1]
                y, z = ya + t * (yb - ya), za + t * (zb - za)
                break
            d -= L
        p.append(box(f"{tag}_bar{j}", coll, x0, y - 0.13, z + 0.15, x1, y + 0.13, z + 0.4, bar_mat))
        if j not in (0, bars - 1):  # a narrow pane of glass beside every inner bar
            p.append(slab(f"{tag}_pane{j}", coll, x0 + 0.3, y + 0.13, x1 - 0.3, y + 0.7, "glass", z + 0.3))


def arc_profile(y0, y1, z0, z1, n=6, rising=True):
    """Quarter-circle profile from (y0, z0) to (y1, z1): steep at the low end, level at the high end."""
    pts = []
    for i in range(n + 1):
        a = (math.pi / 2) * i / n
        if rising:
            pts.append((y0 + (y1 - y0) * (1 - math.cos(a)), z0 + (z1 - z0) * math.sin(a)))
        else:
            pts.append((y0 + (y1 - y0) * math.sin(a), z1 + (z0 - z1) * (1 - math.cos(a))))
    return pts


# ---------------------------------------------------------------- rail station tiles

def platform_furniture(p, coll, rear=True, front=True):
    if rear:
        bench(p, coll, "rbench0", 3.5, 2.2); bench(p, coll, "rbench1", 12.5, 2.2)
        sign(p, coll, "rsign", 8, 1.6)
        lamp(p, coll, "rlamp", 0.8, 1.0, PLAT, 4.8)
    if front:
        bench(p, coll, "fbench0", 4.5, 13.8); bench(p, coll, "fbench1", 11.5, 13.8)
        sign(p, coll, "fsign", 8, 14.4)
        lamp(p, coll, "flamp", 15.2, 15.0, PLAT, 4.8)


def station_rail_platform(coll):
    p = []
    platform(p, coll, "rear", *REAR)
    platform(p, coll, "front", *FRONT)
    platform_furniture(p, coll)
    return {"default": p}


def station_rail_building(coll):
    p = []
    platform(p, coll, "front", *FRONT)
    platform_furniture(p, coll, rear=False)
    # station building on the rear strip, with a canopy over the platform edge
    p.append(box("plinth", coll, 0.2, 0.2, 0, 15.8, 4.6, PLAT, "concrete"))
    b = dict(r=(1.0, 0.3, 15.0, 3.6), z0=PLAT, h=PLAT + 8.5, wall="brick", roof=('gable', 'x', 3.0, "roof_slate", 0.4),
             sills=[PLAT + 1.0, PLAT + 5.2], faces='+y-x+x', ww=1.1, wh=2.2, spacing=2.2, win="window_blue",
             doors=[('+y', 8.0, PLAT)], door="wood_dark", chimneys=[(13.0, 2.0, PLAT + 13.6)], skip=[('+y', 2, 0), ('+y', 3, 0)])
    p += building(coll, "bldg", [b])
    p.append(box("band", coll, 0.9, 3.6, PLAT + 3.6, 15.1, 3.75, PLAT + 4.6, "cc1"))  # company-colour fascia
    p.append(box("canopy", coll, 1.0, 3.6, PLAT + 4.6, 15.0, 5.0, PLAT + 4.9, "cc1"))
    for k, x in enumerate((2.0, 8.0, 14.0)):
        p.append(box(f"cpost{k}", coll, x - 0.1, 4.6, PLAT, x + 0.1, 4.8, PLAT + 4.6, "steel_light"))
    p.append(box("bend0", coll, 0.4, 0.4, PLAT, 1.0, 3.4, PLAT + 8.5, "brick_dark"))
    p.append(box("bend1", coll, 15.0, 0.4, PLAT, 15.6, 3.4, PLAT + 8.5, "brick_dark"))
    return {"default": p}


ROOF_Z, ROOF_TOP = 16.0, 24.0


def station_rail_roof_a(coll):
    """North tile of the two-tile shed: brick piers on the rear platform carry a roof rising to the shed's crown."""
    p = []
    platform(p, coll, "rear", *REAR)
    platform(p, coll, "front", *FRONT)
    platform_furniture(p, coll, rear=False)
    bench(p, coll, "rbench", 8.0, 2.4)
    for k, x in enumerate((0.3, 7.3, 14.3)):
        p.append(box(f"pier{k}", coll, x, 0.3, PLAT, x + 1.4, 1.9, ROOF_Z, "brick"))
        p.append(box(f"cap{k}", coll, x - 0.15, 0.15, ROOF_Z - 0.6, x + 1.55, 2.05, ROOF_Z, "stone"))
    p.append(box("wallplate", coll, 0.2, 0.2, ROOF_Z, 15.8, 2.0, ROOF_Z + 0.6, "brick_dark"))
    open_roof(p, coll, "roof", 0.0, 16.0, arc_profile(1.0, 16.0, ROOF_Z + 0.6, ROOF_TOP, 4), ribs=4, bars=9)
    p.append(box("crown", coll, 0.0, 15.6, ROOF_TOP, 16.0, 16.0, ROOF_TOP + 0.6, "steel_light"))
    return {"default": p}


def station_rail_roof_b(coll):
    """South tile: the roof falls from the crown to a brick arcade along the front platform."""
    p = []
    platform(p, coll, "rear", *REAR)
    platform(p, coll, "front", *FRONT)
    platform_furniture(p, coll, front=False)
    # arcade wall on the outer edge of the front platform: piers and arches as wall blocks with dark openings
    y0, y1 = 14.4, 15.8
    p.append(box("arcade_base", coll, 0.2, y0, PLAT, 15.8, y1, PLAT + 0.6, "brick"))
    for k, (a, b) in enumerate([(0.2, 2.0), (6.7, 9.3), (14.0, 15.8)]):
        p.append(box(f"apier{k}", coll, a, y0, PLAT, b, y1, ROOF_Z, "brick"))
    for k, (a, b) in enumerate([(2.0, 6.7), (9.3, 14.0)]):
        p.append(box(f"aspan{k}", coll, a, y0, PLAT + 8.5, b, y1, ROOF_Z, "brick"))
        # rounded arch head: three stepped blocks
        for j, (inset, zb) in enumerate([(1.1, PLAT + 6.7)]):
            p.append(box(f"ahead{k}_{j}", coll, a, y0, zb, a + inset, y1, PLAT + 8.5, "brick"))
            p.append(box(f"ahead{k}_{j}b", coll, b - inset, y0, zb, b, y1, PLAT + 8.5, "brick"))
    p.append(box("cornice", coll, 0.0, y0 - 0.2, ROOF_Z, 16.0, 16.0, ROOF_Z + 0.6, "stone"))
    for k, x in enumerate((0.6, 15.4)):  # steel columns carry the roof over the rear platform
        p.append(box(f"col{k}", coll, x - 0.25, 1.0, PLAT, x + 0.25, 1.5, ROOF_TOP - 0.3, "steel_light"))
    p.append(box("crown", coll, 0.0, 0.0, ROOF_TOP, 16.0, 0.4, ROOF_TOP + 0.6, "steel_light"))
    open_roof(p, coll, "roof", 0.0, 16.0, arc_profile(0.0, 15.2, ROOF_TOP, ROOF_Z + 0.6, 4, rising=False), ribs=4, bars=9)
    return {"default": p}


def waypoint_rail(coll):
    """Signal box beside the line, with a relay cabinet, lamp and marker posts."""
    p = []
    x0, y0, x1, y1 = 9.0, 0.6, 15.0, 4.6
    p.append(box("box_low", coll, x0, y0, 0, x1, y1, 5.0, "plaster_white"))
    p += [quad(f"low_w{k}", coll, '+y', y1, a, a + 1.0, 1.4, 3.4, "glass_dark") for k, a in enumerate((9.8, 11.4, 13.0))]
    p.append(box("box_up", coll, x0 - 0.3, y0 - 0.3, 5.0, x1 + 0.3, y1 + 0.3, 9.0, "brick_red"))
    p.append(quad("up_glass_y", coll, '+y', y1 + 0.3, x0 + 0.3, x1 - 0.3, 6.0, 8.3, "window_blue"))
    p.append(quad("up_glass_x", coll, '+x', x1 + 0.3, y0 + 0.3, y1 - 0.3, 6.0, 8.3, "window_blue"))
    p += [quad(f"mull{k}", coll, '+y', y1 + 0.36, a - 0.12, a + 0.12, 6.0, 8.3, "cc1") for k, a in enumerate((10.5, 12.0, 13.5))]
    p.append(hip("box_roof", coll, x0 - 0.8, y0 - 0.8, x1 + 0.8, y1 + 0.8, 9.0, 11.5, "roof_tile", 1.6))
    p.append(beam("stair", coll, (8.6, y1 - 0.2, 0.3), (8.6, y0 + 0.6, 5.0), 0.7, 0.3, "wood_dark"))
    p.append(box("cabinet", coll, 4.0, 12.6, 0, 5.8, 14.0, 2.2, "plaster_white"))
    p.append(box("cab_top", coll, 3.9, 12.5, 2.2, 5.9, 14.1, 2.5, "concrete_dark"))
    bollards(p, coll, "marker", 1.0, 1.2, 7.5, 1.2, 4, "cc1", 1.3)
    lamp(p, coll, "lamp", 14.0, 13.6, 0, 5.0, "plaster_white")
    return {"default": p}


# ---------------------------------------------------------------- road stops

def stop_bus_bay(coll):
    p = []
    shelter(p, coll, "back", (1.5, 0.3, 12.5, 3.0), back='-y')
    shelter(p, coll, "side", (13.0, 3.8, 15.7, 12.5), back='+x')
    bollards(p, coll, "bol", 0.5, 1.0, 0.5, 15.0, 8)
    sign(p, coll, "sign", 14.6, 14.6, 0, 'x', 1.3, 4.6)
    for k, x in enumerate((5.0, 9.0)):  # bay markings
        p.append(slab(f"mark{k}", coll, x - 0.3, 4.0, x + 0.3, 9.0, "plaster_white", 0.45))
    p.append(slab("markx", coll, 3.0, 9.0, 11.0, 9.6, "plaster_white", 0.45))
    return {"default": p}


def stop_bus_drive(coll):
    p = []
    shelter(p, coll, "rear", (1.5, 0.3, 9.5, 2.8), back='-y')
    shelter(p, coll, "front", (6.5, 13.2, 14.5, 15.7), back='+y')
    sign(p, coll, "rsign", 12.0, 1.4, 0, 'x', 1.3, 4.6)
    sign(p, coll, "fsign", 3.6, 14.6, 0, 'x', 1.3, 4.6)
    p.append(box("bin", coll, 14.3, 1.0, 0, 15.0, 1.7, 1.2, "cc1"))
    return {"default": p}


def truck_office(p, coll, tag, r, h=5.0):
    x0, y0, x1, y1 = r
    p += building(coll, tag, [dict(r=r, h=h, wall="brick", roof=('flat', "concrete_dark", "brick_dark"), sills=[1.6], faces='+y+x',
                                   ww=1.2, wh=1.6, spacing=3.0, win="window_blue", doors=[('+y', x0 + 1.4, 0)], door="wood_dark")])
    # sloping roof panels in the owner's colour along the front edge
    for k in range(int((x1 - x0) // 2.2)):
        a = x0 + 0.4 + 2.2 * k
        p.append(beam(f"{tag}_panel{k}", coll, (a + 0.9, y0 + 0.8, h + 0.9), (a + 0.9, y1 - 0.2, h + 0.15), 1.9, 0.15, "cc1"))


def stop_truck_bay(coll):
    p = []
    truck_office(p, coll, "office", (1.0, 0.4, 11.5, 3.6))
    crates(p, coll, "crates", 13.6, 2.4, 7)
    chainlink(p, coll, "fence_r", 15.6, 0.4, 15.6, 15.6)
    chainlink(p, coll, "fence_l", 0.4, 4.2, 0.4, 15.6)
    lamp(p, coll, "lamp0", 0.9, 15.0, 0, 6.0)
    lamp(p, coll, "lamp1", 15.0, 15.0, 0, 6.0)
    sign(p, coll, "sign", 13.2, 0.8, 0, 'x', 1.6, 5.0)
    for k, x in enumerate((5.5, 10.5)):
        p.append(slab(f"mark{k}", coll, x - 0.3, 5.0, x + 0.3, 10.0, "plaster_white", 0.45))
    return {"default": p}


def stop_truck_drive(coll):
    p = []
    truck_office(p, coll, "office", (7.5, 11.8, 14.5, 15.4), 4.6)
    crates(p, coll, "crates", 4.0, 2.4, 9)
    chainlink(p, coll, "fence", 1.0, 0.4, 13.0, 0.4)
    lamp(p, coll, "lamp0", 0.9, 1.2, 0, 6.0)
    lamp(p, coll, "lamp1", 15.0, 14.8, 0, 6.0)
    for k, x in enumerate((13.6, 14.2, 14.8)):
        p.append(box(f"rack{k}", coll, x - 0.12, 1.0, 0, x + 0.12, 3.0, 2.0, "cc1"))
    p.append(box("rack_top", coll, 13.4, 1.0, 2.0, 15.0, 3.0, 2.2, "cc1"))
    return {"default": p}


def waypoint_road(coll):
    p = []
    bollards(p, coll, "rear", 1.0, 0.8, 15.0, 0.8, 10)
    bollards(p, coll, "front", 1.0, 15.2, 15.0, 15.2, 10)
    for k, (x, y) in enumerate([(1.0, 0.8), (15.0, 15.2)]):
        p.append(box(f"marker{k}", coll, x - 0.35, y - 0.35, 0, x + 0.35, y + 0.35, 2.6, "cc1"))
        p.append(box(f"marker{k}_cap", coll, x - 0.45, y - 0.45, 2.6, x + 0.45, y + 0.45, 3.0, "plaster_white"))
    return {"default": p}


# ---------------------------------------------------------------- depots

def depot_rail(coll):
    """Brick engine shed, ridge along the track (local Y), open arch towards +Y."""
    p = []
    x0, y0, x1, y1, h = 1.0, 1.0, 15.0, 15.4, 9.0
    p.append(box("wall_l", coll, x0, y0, 0, x0 + 1.0, y1, h, "brick"))
    p.append(box("wall_r", coll, x1 - 1.0, y0, 0, x1, y1, h, "brick"))
    p.append(box("wall_back", coll, x0 + 1.0, y0, 0, x1 - 1.0, y0 + 1.0, h, "brick"))
    p.append(box("door_l", coll, x0 + 1.0, y1 - 1.0, 0, 4.4, y1, h, "brick"))
    p.append(box("door_r", coll, 11.6, y1 - 1.0, 0, x1 - 1.0, y1, h, "brick"))
    p.append(box("lintel", coll, 4.4, y1 - 1.0, 7.0, 11.6, y1, h, "brick"))
    for k, (a, zb) in enumerate([(0.7, 6.2), (0.3, 6.7)]):
        p.append(box(f"arch{k}a", coll, 4.4, y1 - 1.0, zb, 4.4 + a, y1, 7.0, "brick"))
        p.append(box(f"arch{k}b", coll, 11.6 - a, y1 - 1.0, zb, 11.6, y1, 7.0, "brick"))
    p.append(slab("floor", coll, x0 + 1.0, y0 + 1.0, x1 - 1.0, y1 - 1.0, "concrete_dark", 0.05))
    p.append(gable("roof", coll, x0, y0, x1, y1, h, h + 5.0, "roof_dark", 'y', 0.5, "brick"))
    p.append(box("ridge", coll, 7.7, y0, h + 4.9, 8.3, y1, h + 5.3, "brick_dark"))
    for f, at in (('+x', x1), ('-x', x0)):
        for k, a in enumerate((4.0, 8.2, 12.4)):
            p.append(quad(f"win{f}{k}", coll, f, at, a - 0.8, a + 0.8, 2.5, 6.0, "glass_dark"))
            p.append(quad(f"winhead{f}{k}", coll, f, at, a - 0.5, a + 0.5, 6.0, 6.6, "glass_dark"))
    p.append(box("vent", coll, 7.4, 6.0, h + 4.6, 8.6, 9.0, h + 6.2, "brick_dark"))
    return {"default": p}


def depot_road(coll):
    """Brick garage with a sawtooth roof and a glazed band; open front towards +Y."""
    p = []
    x0, y0, x1, y1, h = 0.8, 0.8, 15.2, 15.2, 8.0
    p.append(box("wall_l", coll, x0, y0, 0, x0 + 0.8, y1, h, "brick"))
    p.append(box("wall_r", coll, x1 - 0.8, y0, 0, x1, y1, h, "brick"))
    p.append(box("wall_back", coll, x0 + 0.8, y0, 0, x1 - 0.8, y0 + 0.8, h, "brick"))
    p.append(box("front_l", coll, x0 + 0.8, y1 - 0.8, 0, 2.6, y1, h, "brick"))
    p.append(box("front_r", coll, 13.4, y1 - 0.8, 0, x1 - 0.8, y1, h, "brick"))
    p.append(box("lintel", coll, 2.6, y1 - 0.8, 5.6, 13.4, y1, h, "brick"))
    p.append(slab("floor", coll, x0 + 0.8, y0 + 0.8, x1 - 0.8, y1 - 0.8, "concrete_dark", 0.05))
    p.append(box("glazing", coll, x0, y0, h, x1, y1, h + 1.8, "window_blue"))
    for k in range(13):
        x = x0 + 0.2 + (x1 - x0 - 0.4) * k / 12
        p.append(box(f"mullx{k}", coll, x - 0.18, y1 - 0.1, h, x + 0.18, y1 + 0.08, h + 1.8, "concrete_dark"))
        y = y0 + 0.2 + (y1 - y0 - 0.4) * k / 12
        p.append(box(f"mully{k}", coll, x1 - 0.1, y - 0.18, h, x1 + 0.08, y + 0.18, h + 1.8, "concrete_dark"))
    p.append(box("eaves", coll, x0 - 0.2, y0 - 0.2, h + 1.8, x1 + 0.2, y1 + 0.2, h + 2.2, "concrete"))
    p.append(sawtooth("roof", coll, x0, y0, x1, y1, h + 2.2, 4, 2.6, "roof_slate", "glass", "roof_dark", along='x'))
    return {"default": p}


def depot_ship(coll):
    """Two-tile boat shed over the water, along local X; the north part is x 0..16. Big doors at both ends."""
    p = []
    x0, x1, y0, y1, h = 0.4, 31.6, 1.6, 14.4, 9.0
    p.append(box("hull_l", coll, x0, y0, -1.0, x1, y0 + 0.6, 1.2, "stone_dark"))
    p.append(box("hull_r", coll, x0, y1 - 0.6, -1.0, x1, y1, 1.2, "stone_dark"))
    p.append(box("wall_l", coll, x0, y0, 1.2, x1, y0 + 0.6, h, "plaster_white"))
    p.append(box("wall_r", coll, x0, y1 - 0.6, 1.2, x1, y1, h, "plaster_white"))
    for f, at in (('+y', y1), ('-y', y0)):
        for k in range(10):
            a = 2.2 + 3.0 * k
            p.append(quad(f"win{f}{k}", coll, f, at, a, a + 1.6, 4.4, 5.8, "window_blue"))
        for k in range(16):  # corrugation ribs
            a = x0 + 0.3 + (x1 - x0 - 0.6) * k / 15
            p.append(quad(f"rib{f}{k}", coll, f, at, a - 0.12, a + 0.12, 1.2, h, "steel_light", 0.1))
    for k, x in enumerate((x0, x1 - 0.8)):  # end frames with tall doors in the owner's colour
        p.append(box(f"frame{k}a", coll, x, y0, -1.0, x + 0.8, y0 + 2.0, h, "steel_light"))
        p.append(box(f"frame{k}b", coll, x, y1 - 2.0, -1.0, x + 0.8, y1, h, "steel_light"))
        p.append(box(f"door{k}", coll, x + 0.2, y0 + 2.0, 5.5, x + 0.6, y1 - 2.0, h, "cc1"))
        p.append(box(f"door{k}_band", coll, x + 0.1, y0 + 2.0, 4.6, x + 0.7, y1 - 2.0, 5.5, "steel"))
    p.append(gable("roof", coll, x0, y0, x1, y1, h, h + 5.5, "roof_dark", 'x', 0.6, "plaster_white"))
    for k in range(4):  # skylights
        a = 4.0 + 7.0 * k
        for side, (ya, yb) in enumerate([(4.0, 7.2), (8.8, 12.0)]):
            za = h + 5.5 * (ya - y0) / 6.4 if ya < 8 else h + 5.5 * (y1 - yb) / 6.4
            zb = h + 5.5 * (yb - y0) / 6.4 if yb <= 8 else h + 5.5 * (y1 - ya) / 6.4
            p.append(beam(f"sky{k}_{side}", coll, (a + 1.5, ya, za + 0.25), (a + 1.5, yb, zb + 0.25), 3.0, 0.2, "glass"))
    for k, x in enumerate((1.0, 31.0)):
        p.append(box(f"flagpole{k}", coll, x - 0.12, 7.88, h + 5.0, x + 0.12, 8.12, h + 9.5, "steel_light"))
        p.append(box(f"flag{k}", coll, x - 0.06, 8.12, h + 7.6, x + 0.06, 10.6, h + 9.2, "cc1"))
    full = join("depot_ship_full", p)
    return split(full, 'x', {"north": 0, "south": 1})


# ---------------------------------------------------------------- water

def dock(coll):
    """Land tile: a paved quay laid on the shore slope. Water tile: a timber-faced pier with a crane and containers."""
    land = []
    land.append(slab("paving", coll, 0.4, 0.0, 15.6, 16.0, "concrete_dark", 0.15))
    land.append(box("kerb_l", coll, 0.0, 0.0, 0, 0.6, 16.0, 0.6, "concrete"))
    land.append(box("kerb_r", coll, 15.4, 0.0, 0, 16.0, 16.0, 0.6, "concrete"))
    land.append(slab("line", coll, 7.85, 1.0, 8.15, 15.0, "hazard_yellow", 0.2))
    lamp(land, coll, "lamp", 14.6, 12.0, 0, 6.0)
    crates(land, coll, "crates", 3.2, 4.0, 3)
    water = []
    deck = 3.0
    water.append(box("deck", coll, 0.0, 0.0, deck - 0.6, 16.0, 15.0, deck, "concrete_dark"))
    water.append(box("edge", coll, 0.0, 14.6, deck - 0.6, 16.0, 15.2, deck + 0.4, "hazard_yellow"))
    for k in range(9):  # piles along the open sides
        a = 0.6 + 1.85 * k
        water.append(box(f"pile_f{k}", coll, a - 0.3, 14.7, -1.5, a + 0.3, 15.3, deck - 0.6, "wood_dark"))
        b = 0.6 + 1.7 * k
        if b < 15:
            water.append(box(f"pile_l{k}", coll, -0.0, b - 0.3, -1.5, 0.6, b + 0.3, deck - 0.6, "wood_dark"))
            water.append(box(f"pile_r{k}", coll, 15.4, b - 0.3, -1.5, 16.0, b + 0.3, deck - 0.6, "wood_dark"))
    for k in range(5):
        x = 1.5 + 3.2 * k
        water.append(box(f"bollard{k}", coll, x - 0.3, 13.8, deck, x + 0.3, 14.4, deck + 0.8, "black"))
    # crane rails and a level-luffing crane on a portal
    for y in (8.5, 13.0):
        water.append(box(f"rail{y}", coll, 0.5, y - 0.15, deck, 15.5, y + 0.15, deck + 0.2, "steel"))
    cx, cy = 10.0, 10.75
    for k, (dx, dy) in enumerate([(-1.6, -2.25), (1.6, -2.25), (1.6, 2.25), (-1.6, 2.25)]):
        water.append(beam(f"leg{k}", coll, (cx + dx, cy + dy, deck + 0.2), (cx + dx * 0.4, cy + dy * 0.4, deck + 6.0), 0.5, 0.5, "leaf_olive"))
    water.append(box("portal", coll, cx - 1.3, cy - 1.3, deck + 6.0, cx + 1.3, cy + 1.3, deck + 7.0, "leaf_olive"))
    water.append(box("cab", coll, cx - 1.2, cy - 1.0, deck + 7.0, cx + 1.4, cy + 1.2, deck + 9.6, "leaf_olive"))
    water.append(quad("cabwin", coll, '+y', cy + 1.2, cx - 0.8, cx + 1.0, deck + 8.0, deck + 9.2, "glass_dark"))
    water.append(beam("jib", coll, (cx, cy, deck + 9.0), (cx - 0.5, cy + 5.0, deck + 22.0), 0.6, 0.7, "leaf_olive"))
    water.append(beam("jib2", coll, (cx - 0.5, cy + 5.0, deck + 22.0), (cx - 0.5, cy + 5.0, deck + 15.5), 0.2, 0.2, "steel"))
    water.append(box("counter", coll, cx - 1.0, cy - 3.0, deck + 8.4, cx + 1.0, cy - 1.0, deck + 10.2, "concrete_dark"))
    water.append(box("hook", coll, cx - 0.8, cy + 4.7, deck + 14.8, cx - 0.2, cy + 5.3, deck + 15.6, "hazard_yellow"))
    # containers
    for k, (x, y, z, mat) in enumerate([(1.0, 1.0, 0, "signal_red"), (1.0, 1.0, 2.4, "tank_blue"), (4.4, 1.0, 0, "copper_green"),
                                        (1.0, 4.6, 0, "paint_orange")]):
        water.append(box(f"cont{k}", coll, x, y, deck + z, x + 3.0, y + 3.2, deck + z + 2.4, mat))
        water.append(quad(f"cont{k}_door", coll, '+x', x + 3.0, y + 0.3, y + 2.9, deck + z + 0.2, deck + z + 2.2, "steel"))
    crates(water, coll, "crates", 5.6, 5.6, 11)
    for o in water[-3:]:
        o.location.z += deck
    return {"land": land, "water": water}


def buoy(coll):
    p = []
    p.append(lathe("float", coll, 8, 8, [(-0.6, 1.8), (0.6, 2.0), (1.4, 1.7), (2.2, 0.9), (2.6, 0.4)], 10,
                   ["signal_red", "plaster_white", "signal_red", "signal_red"]))
    p.append(box("mast", coll, 7.8, 7.8, 2.5, 8.2, 8.2, 6.0, "steel"))
    p.append(box("cage", coll, 7.5, 7.5, 5.0, 8.5, 8.5, 5.3, "signal_red"))
    p.append(box("light", coll, 7.6, 7.6, 6.0, 8.4, 8.4, 6.8, "lamp_yellow"))
    p.append(lathe("ring", coll, 8, 8, [(-0.05, 2.6), (0.05, 2.6)], 12, "plaster_white"))
    return {"default": p}


def lock(coll):
    """Three tiles along local Y rising towards +Y: lower y 0..16 (water 0), middle 16..32, upper 32..48 (water 8)."""
    p = []
    TOP = 10.0
    for side, (a, b) in enumerate([(0.0, 2.6), (13.4, 16.0)]):
        p.append(box(f"wall{side}_lo", coll, a, 0.0, -1.0, b, 32.0, TOP, "stone_dark"))
        p.append(box(f"wall{side}_up", coll, a, 32.0, 7.0, b, 48.0, TOP, "stone_dark"))
        p.append(box(f"coping{side}", coll, a - 0.1, 0.0, TOP, b + 0.1, 48.0, TOP + 0.4, "concrete"))
        inner = '+x' if side == 0 else '-x'
        at = b if side == 0 else a
        for k in range(8):  # vertical stone courses facing the chamber
            y = 1.0 + 3.8 * k
            p.append(quad(f"course{side}_{k}", coll, inner, at, y, y + 0.5, -0.5, TOP, "stone", 0.05))
        for k, y in enumerate((4.0, 14.0, 24.0, 36.0, 44.0)):
            lamp(p, coll, f"lamp{side}_{k}", (a + b) / 2, y, TOP + 0.4, 4.0, "lamp_yellow")
    for k, (y, z0) in enumerate([(16.0, -0.5), (32.0, 7.5)]):  # mitre gates
        p.append(box(f"gate{k}", coll, 2.6, y - 0.5, z0, 13.4, y + 0.5, TOP - 0.3, "wood_dark"))
        for j in range(5):
            x = 3.4 + 2.3 * j
            p.append(quad(f"gate{k}_plank{j}", coll, '+y', y + 0.5, x, x + 0.6, z0 + 0.3, TOP - 0.6, "cream"))
        p.append(box(f"walk{k}", coll, 2.6, y - 0.6, TOP - 0.3, 13.4, y + 0.6, TOP, "steel"))
        p.append(box(f"rail{k}", coll, 2.6, y - 0.05, TOP + 1.0, 13.4, y + 0.05, TOP + 1.2, "plaster_white"))
        for j, (x0, x1) in enumerate([(0.6, 2.0), (14.0, 15.4)]):  # balance beams and winches
            p.append(box(f"winch{k}_{j}", coll, x0, y + 1.0, TOP + 0.4, x1, y + 2.4, TOP + 1.8, "hazard_yellow"))
    p.append(box("hut", coll, 13.6, 5.0, TOP + 0.4, 16.0, 10.0, TOP + 3.8, "plaster_white"))
    p.append(gable("hut_roof", coll, 13.4, 4.8, 16.2, 10.2, TOP + 3.8, TOP + 5.0, "roof_dark", 'y', 0.2, "plaster_white"))
    p.append(quad("hut_win", coll, '-x', 13.6, 6.2, 8.8, TOP + 1.6, TOP + 3.0, "glass_dark"))
    p.append(beam("crane", coll, (1.3, 20.0, TOP + 0.4), (1.3, 20.0, TOP + 7.5), 0.8, 0.8, "hazard_yellow"))
    p.append(beam("crane_jib", coll, (1.3, 20.0, TOP + 7.2), (4.0, 20.0, TOP + 7.2), 0.5, 0.5, "hazard_yellow"))
    full = join("lock_full", p)
    return split(full, 'y', {"lower": 0, "middle": 1, "upper": 2}, z_shift={"upper": -8.0})


# ---------------------------------------------------------------- tile splitting

def split(ob, axis, parts, z_shift=None):
    """Cut a joined multi-tile model into one object per tile, each moved to local 0..16. Returns {state: [obj]}."""
    k = 0 if axis == 'x' else 1
    out = {}
    for state, n in parts.items():
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        no = [0, 0, 0]; no[k] = 1
        for co, keep_above in ((16 * n, True), (16 * (n + 1), False)):
            c = [0, 0, 0]; c[k] = co
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=c, plane_no=no, clear_inner=keep_above, clear_outer=not keep_above)
        d = [0, 0, 0]; d[k] = -16 * n; d[2] = (z_shift or {}).get(state, 0.0)
        bmesh.ops.translate(bm, verts=bm.verts[:], vec=d)
        me = bpy.data.meshes.new(f"{KEY}_{state}")
        bm.to_mesh(me); bm.free()
        for m in ob.data.materials:
            me.materials.append(m)
        part = bpy.data.objects.new(f"{KEY}_{state}", me)
        out[state] = [part]
    bpy.data.objects.remove(ob, do_unlink=True)
    return out


# ---------------------------------------------------------------- build

sync_palette()
scene_root = bpy.data.scenes["model"].collection
for c in list(scene_root.children):
    if not c.name.startswith('_') and c.name != 'reference':
        clear(c)
base = bpy.data.collections.get("default") or bpy.data.collections.new("default")
if base.name not in scene_root.children:
    scene_root.children.link(base)
states = globals()[KEY](base)
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
