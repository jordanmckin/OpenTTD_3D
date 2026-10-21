"""Moving parts for the pilot industries (Phase 8.7): the coal mine headframe wheel and the power station sparks.
Exec after house_kit.py and industry_kit.py with KEY set and the industry's .blend open.

The coal mine and power station static models came from the 8.4 pilot script and stay as they are in their .blend,
except that the headframe wheel (its steel_light faces) moves out of the complete state into the parts.
"""
import json

import bmesh

WHEEL = dict(c=(11.5, 4.5, 29.5), r=3.7, t=0.6, n=12, mat="steel_light", axis="x")  # as built in the pilot


def headframe_wheel(coll, tag, step):
    """The wheel turns a third of the spokes' quarter turn per animation frame (three frames, as the sprites)."""
    return wheel(f"{tag}_wheel", coll, phase=step * math.pi / 6, **WHEEL)


def plant_sparks(coll, tag, step):
    """The classic sprite climbs the transformer over six frames: an arc from an insulator to the wire above, then
    a flash running along the wire. Two of the four lines spark, half a cycle apart."""
    p = []
    for k, (x, y0, lag) in enumerate(((6.5, 5.0, 0), (9.5, 10.0, 3))):
        s = (step + lag) % 6
        if s < 3:
            top = 3.9 + (10.3 - 3.9) * (s + 1) / 3
            p += bolt(coll, f"{tag}_arc{k}", (x, y0, 3.9), (x, y0, top), 3 + s, step + 7 * k)
        else:
            y = y0 + (2.2 if y0 < 8 else -2.2) * (s - 2)
            p += bolt(coll, f"{tag}_run{k}", (x, y - 1.2, 10.35), (x, y + 1.2, 10.35), 3, step + 7 * k, mat="flame_yellow")
    return p


def strip_wheel():
    """Remove the wheel faces from the static headframe (idempotent)."""
    for c in ("complete", "complete@layout1"):
        for o in bpy.data.collections[c].objects:
            if "_g0" not in o.name or "steel_light" not in [s.name for s in o.material_slots]:
                continue
            i = [s.name for s in o.material_slots].index("steel_light")
            bm = bmesh.new(); bm.from_mesh(o.data)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == i], context="FACES")
            bm.to_mesh(o.data); bm.free()


PARTS = {"industry_00": {0: (3, headframe_wheel)}, "industry_01": {10: (6, plant_sparks)}}

_inv = json.load(open(r"D:\G ttd\OpenTTD-15.3\OpenTTD-15.3\assets\3d\inventory.json", encoding="utf-8"))
_entry = next(e for e in _inv["entries"] if e["key"] == KEY)
sync_palette()
if KEY == "industry_00":
    strip_wheel()
result = build_parts([[tuple(t) for t in lay] for lay in _entry["layouts"]], PARTS[KEY])
