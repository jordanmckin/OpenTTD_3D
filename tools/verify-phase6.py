"""Verify the recorded Phase 6 scripted evidence; native checks remain a user checklist."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "OpenTTD-15.3/OpenTTD-15.3/docs/3d/evidence/phase6"


def require(condition, message):
    if not condition:
        raise SystemExit("FAIL: " + message)


def read(name):
    raw = (EVIDENCE / name).read_bytes()
    text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8", errors="replace")
    require(not re.search(r"PHASE6 FAILED|Your script made an error|Assertion failed|3D proof failed|3D proof OpenGL error|failures=[1-9]", text), name + " contains a failure")
    return text


for climate, name in enumerate(("temperate", "arctic", "tropic", "toyland")):
    log = read(name + ".log")
    require(f"PHASE6 COVERAGE climate={climate}" in log, name + " climate identity")
    samples = re.search(r"3D CHECK: heights=(\d+) failures=0; interior classic picks=(\d+) failures=0", log)
    require(samples and int(samples[1]) >= 5120 and int(samples[2]) >= 200, name + " insufficient coordinate checks")
    slopes = re.search(r"PHASE6 COVERAGE.* slopes=(\d+) steep=(\d+)", log)
    require(slopes and int(slopes[1]) > 0 and int(slopes[2]) > 0, name + " lacks non-flat and steep terrain")
    require((EVIDENCE / (name + ".png")).is_file(), name + " capture")

visibility = read("usability.log")
for option in range(1, 6):
    for mode in ("solid", "transparent", "hidden"):
        require(f"PHASE6 VISIBILITY option={option} mode={mode}" in visibility, f"visibility {option}/{mode}")
for mode in ("solid", "transparent", "hidden", "restored"):
    require((EVIDENCE / f"phase6-{mode}.png").is_file(), mode + " capture")

for name, marker in (("coverage.log", "PHASE6 READY"), ("reload.log", "PHASE6 RELOADED")):
    log = read(name)
    require(marker in log, name + " fixture completion")
    for kind in (2, 3):
        samples = re.findall(rf"PHASE6 MOVEMENT vehicle=\d+ type={kind} tile=(\d+) speed=(\d+)", log)
        require(len({tile for tile, speed in samples if int(speed) > 0}) >= 3, name + f" type {kind} did not move across three tiles")
    require("PHASE6 STATION type=1 tiles=24" in log, name + " two small airport footprints")
    require("PHASE6 STATION type=6 tiles=2" in log, name + " two buoys")
    require("ship_depots=2" in log, name + " two-tile ship depot")

client = read("network-client.log")
server = read("network-server.log")
require(not re.search(r"Sync error detected|Missed frame for sync-test", client), "network synchronization failure")
frames = [int(n) for n in re.findall(r"Receive_SERVER_SYNC\(\): sync_frame=(\d+)", client)]
require(len(frames) >= 30 and max(frames) - min(frames) >= 3000, "insufficient multiplayer synchronization interval")
require("Receive_SERVER_SHUTDOWN" in client, "normal server shutdown not observed")
require("PHASE6 COVERAGE" in client, "3D restoration audit missing")
require("PHASE4 RELOADED" in server and "load=90" in server and "load=0" in server, "server AI and cargo activity missing")
require("100% tests passed, 0 tests failed out of 105" in read("tests.log"), "CTest suite")
for capture in ("ship.png", "aircraft.png"):
    require((EVIDENCE / capture).is_file(), capture + " missing")

print(f"PASS: four climates, coordinates, visibility, air/water movement and reload, {len(frames)} network sync packets, and 105 tests.")
print("Native Windows input/resize/DPI are not verified by this script; use phase6-manual-tests.md.")
