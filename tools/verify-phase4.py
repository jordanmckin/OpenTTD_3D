"""Check Phase 4 runtime evidence; does not launch or modify the game."""
import argparse
import json
import re
import statistics
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("log", type=Path)
parser.add_argument("--reload", action="store_true")
args = parser.parse_args()
log = args.log.read_text(encoding="utf-8", errors="replace")


def require(ok, message):
    if not ok:
        raise SystemExit("FAIL: " + message)


require("Script died" not in log and "script died" not in log and "Fixture failed" not in log, "fixture script failed")
require("PHASE4 RELOADED" in log if args.reload else "PHASE4 ROUTE_READY" in log, "route ready/reload marker missing")
audits = re.findall(r"PHASE4 AUDIT roads=(\d+) crossings=(\d+) portals=(\d+) ramps=(\d+) deck_tiles=(\d+) height_checks=(\d+) failures=(\d+)", log)
require(audits, "infrastructure height audit missing")
roads, crossings, portals, ramps, decks, checks, failures = map(int, audits[-1])
require(roads >= 50 and crossings >= 1 and portals == 6 and ramps == 6 and decks == 9 and checks == 3072 and failures == 0, "infrastructure counts or height audit failed")
if not args.reload:
    labels = ["rail bridge", "remove rail bridge", "rebuild rail bridge", "rail tunnel", "remove rail tunnel", "rebuild rail tunnel", "road bridge", "remove road bridge", "rebuild road bridge", "road tunnel", "remove road tunnel", "rebuild road tunnel", "remove road segment", "rebuild road segment", "live level crossing", "north bridge foundation corner", "south bridge foundation corner", "perpendicular road bridge", "perpendicular road tunnel"]
    for label in labels:
        require(f"PHASE4 {label}=true" in log, label)

events = [tuple(map(int, row[:-1])) + (row[-1] == "true",) for row in re.findall(r"PHASE4 VEHICLE id=(\d+) type=(\d+) event=(\d+) tile=\((\d+), (\d+)\) z=(-?\d+) deck=(-?\d+) rendered=(true|false)", log)]


def event(kind, category, x=None, y=None):
    return any(t == kind and c == category and (x is None or tx == x) and (y is None or ty == y) for _, t, c, tx, ty, z, deck, rendered in events)


for kind in (0, 1):
    for category in (2, 4, 16, 32, 128):
        require(event(kind, category), f"vehicle type {kind} missing event {category}")
if args.reload:
    for kind, name in ((0, "train"), (1, "truck")):
        require(event(kind, 1), f"{name} depot hiding not observed")
        require(f"PHASE4 {name.upper()}_DEPOT_CONFIRMED" in log and f"PHASE4 restart {name} after depot=true" in log, f"{name} depot round trip incomplete")
require(event(1, 8, 20, 29) and event(1, 8, 20, 38), "truck did not traverse both underpasses")
require(event(1, 4, 54) and event(1, 2, 54), "perpendicular bridge/tunnel movement missing")
require(all(z == deck and rendered for _, _, c, _, _, z, deck, rendered in events if c == 4), "deck vehicle height/visibility mismatch")
require(all(not rendered for _, _, c, _, _, _, _, rendered in events if c in (1, 2)), "hidden/depot vehicle included")
require(all(z < deck and rendered for _, _, c, _, _, z, deck, rendered in events if c == 8), "underpass vehicle height/visibility mismatch")
require("PHASE4 CROSSING tile=(39, 29) barred=true" in log and "PHASE4 CROSSING tile=(39, 29) barred=false" in log, "crossing did not open and close")
deliveries = [tuple(map(int, row)) for row in re.findall(r"PHASE4 RUN tile=(\d+) load=(\d+) profit=(-?\d+)", log)]
require(any(load == 90 for _, load, _ in deliveries), "train never fully loaded")
require(any(load == 0 and profit > prior_profit for (_, prior_load, prior_profit), (_, load, profit) in zip(deliveries, deliveries[1:]) if prior_load > 0), "no observed unloading/income transition")
road = [tuple(map(int, row)) for row in re.findall(r"PHASE4 ROAD tile=(\d+) speed=(\d+)", log)]
require(len({tile for tile, speed in road if speed > 0}) > 10, "road vehicle not moving along route")
samples = sorted(map(int, re.findall(r"3D proof 1280x900 render/readback: (\d+) us", log)))
print(json.dumps({"result": "PASS", "reload": args.reload, "height_checks": checks, "height_failures": failures, "vehicle_events": len(events), "road_tiles_visited": len({tile for tile, _ in road}), "render_readback_us": {"samples": len(samples), "median": statistics.median(samples), "p95": samples[min(len(samples)-1, int(len(samples)*0.95))], "max": max(samples)} if samples else None}, indent=2))
