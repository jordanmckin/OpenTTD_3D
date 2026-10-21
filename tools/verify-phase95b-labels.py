"""Check projected labels and the existing application click actions; no native input claim."""
import json
import re
import sys
from collections import Counter
from pathlib import Path
from PIL import Image, ImageChops

run = Path(sys.argv[1])
log = (run / "stdout.log").read_text(errors="replace") + (run / "stderr.log").read_text(errors="replace")
assert not re.search(r"Assertion failed|3D proof failed|command not found|outside of group|ERROR:", log, re.I), "runtime error"
dense = "--dense" in sys.argv
if not dense:
    assert "PHASE95B FIXTURE ok=true" in log, "fixture failed"
records = {kind: [] for kind in ("LABEL", "CLICK", "VIEW")}
for line in log.splitlines():
    match = re.search(r"PHASE95B (LABEL|CLICK|VIEW) (.*)", line)
    if match:
        records[match[1]].append(dict(re.findall(r"(\w+)=([^ ]+)", match[2])))
assert records["VIEW"], "missing label diagnostics"
for row in records["VIEW"]:
    assert row["failures"] == "0", row
for row in records["CLICK"]:
    assert row["ok"] == "true", row
for row in records["LABEL"]:
    assert row["edges_ok"] == "true", row

def views(tag):
    found = [r for r in records["VIEW"] if r["tag"] == tag]
    assert found, f"missing tag {tag}"
    return found

def labels(tag):
    return [r for r in records["LABEL"] if r["tag"] == tag]

if dense:
    for tag in ("dense-classic", "dense45", "dense90", "dense180", "dense-secondary"):
        assert sum(int(v["visible"]) for v in views(tag)) > 0, tag
        assert sum(int(v["clicks"]) for v in views(tag)) > 0, tag
        assert any(r["type"] == "town" for r in labels(tag)), tag
    assert len(views("dense-secondary")) == 6
    result = {"passed": True, "views": len(records["VIEW"]), "clicks": len(records["CLICK"]), "records": records}
    (run / "check-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))
    sys.exit(0)

for tag in ("classic", "yaw45", "yaw90", "yaw180", "yaw270", "small", "secondary", "classic2d", "close", "resized"):
    assert sum(int(r["visible"]) for r in views(tag)) > 0, tag
    assert sum(int(r["clicks"]) for r in views(tag)) > 0, tag
for tag in ("hidden",):
    assert sum(int(r["visible"]) for r in views(tag)) == 0, tag
for tag in ("facilities", "invisible"):
    views(tag)
    assert not any(r["type"] in ("station", "waypoint") for r in labels(tag)), tag
assert not any(r["type"] == "sign" for r in labels("invisible"))
assert len(labels("competitors")) < len(labels("small")), "competitor preference ineffective"
assert len(views("secondary")) >= 3, "missing additional viewports"
for tag, camera in (("cab", "1"), ("chase", "2")):
    ride = [v for v in views(tag) if v["camera"] != "0"]
    assert len(ride) >= 2, (tag, ride)
    assert all(v["camera"] == camera for v in ride), (tag, ride)
    assert all(v["visible"] == v["clicks"] == "0" for v in ride), tag
assert {r["type"] for r in records["CLICK"]} >= {"station", "town", "sign"}, "missing label type actions"
assert all(v["enabled"] == "false" for v in views("classic2d"))

pictures = {p.stem: p for p in (run / "screenshot").glob("*")}
required = ("classic", "classic-hidden", "yaw45", "yaw90", "yaw90-hidden", "yaw180", "yaw270", "small", "hidden", "facilities", "competitors", "invisible", "transparent", "effects", "effects-hidden", "secondary", "cab", "chase", "classic2d", "close", "resized")
assert all(name in pictures for name in required), sorted(pictures)
# A stationary screenshot must put each coloured label at its logged projection.
# This catches stale text left in the UI layer when only the 3D layer rotates.
reference = Image.open(pictures["classic"]).convert("RGB")
colours = {}
for row in labels("classic"):
    if row["type"] not in ("station", "sign"):
        continue
    left, top, right, bottom = map(int, row["rect"].split(","))
    if top < 110 or top >= reference.height - 80:
        continue
    stripe = reference.crop((max(0, left), top, min(reference.width, right), top + 1))
    colours[row["type"], row["id"]] = Counter(stripe.getdata()).most_common(1)[0][0]
aligned = 0
for tag in ("yaw45", "yaw90", "yaw180", "yaw270"):
    picture = Image.open(pictures[tag]).convert("RGB")
    for row in labels(tag):
        colour = colours.get((row["type"], row["id"]))
        if colour is None:
            continue
        left, top, right, bottom = map(int, row["rect"].split(","))
        if top < 110 or top >= picture.height - 80 or min(picture.width, right) - max(0, left) < 20:
            continue
        stripe = picture.crop((max(0, left), top, min(picture.width, right), top + 1))
        fraction = sum(pixel == colour for pixel in stripe.getdata()) / stripe.width
        assert fraction > .8, ("label pixels differ from projected bounds", tag, row, fraction)
        aligned += 1
assert aligned >= 4, ("insufficient projected raster checks", aligned)
differences = {}
for a, b in (("classic", "classic-hidden"), ("yaw90", "yaw90-hidden"), ("effects", "effects-hidden")):
    first, second = [Image.open(pictures[name]).convert("RGB") for name in (a, b)]
    diff = ImageChops.difference(first, second)
    # Ignore window furniture and screenshot notifications at the bottom.
    diff = diff.crop((0, 110, first.width, first.height - 80))
    changed = sum(max(pixel) > 4 for pixel in diff.getdata())
    assert changed > 50, (a, b, changed)
    differences[f"{a}/{b}"] = changed

result = {"passed": True, "views": len(records["VIEW"]), "clicks": len(records["CLICK"]), "projected_raster_checks": aligned, "label_types": sorted({r["type"] for r in records["CLICK"]}), "image_changed_pixels": differences, "screenshots": list(required), "records": records, "native_input": "Not exercised: application handlers and screenshots only."}
(run / "check-results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: value for key, value in result.items() if key not in ("records", "screenshots")}, indent=2))
