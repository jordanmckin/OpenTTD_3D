"""Check a paused new map against a renderer reset or full-snapshot reference."""
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops


def verify(run):
    environment = json.loads((run / "environment.json").read_text(encoding="utf-8-sig"))
    log = (run / "stderr.log").read_text(encoding="utf-8", errors="replace")
    initial = Image.open(run / "screenshot/initial.bmp").convert("RGB")
    refreshed = Image.open(run / "screenshot/refreshed.bmp").convert("RGB")
    assert initial.size == refreshed.size, "Capture sizes differ"
    changed = sum(pixel != (0, 0, 0) for pixel in ImageChops.difference(initial, refreshed).getdata())
    missed_tiles = len(re.findall(r"PHASE7 missed tile=", log))
    missed_chunks = [int(value) for value in re.findall(r"PHASE7 dirty-reference missed_chunks=(\d+)", log)]
    width, height = 1 << environment["map_x"], 1 << environment["map_y"]
    allocated = f"Allocating map of size {width}x{height}" in log
    valid_reference = not environment["verify_dirty"] or (bool(missed_chunks) and not any(missed_chunks))
    result = {
        "passed": allocated and changed == 0 and missed_tiles == 0 and valid_reference,
        "map": [width, height],
        "changed_pixels_after_reference": changed,
        "missed_tile_snapshots": missed_tiles,
        "missed_chunks": missed_chunks,
        "expected_map_allocated": allocated,
        "environment": environment,
    }
    (run / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return result["passed"]


if __name__ == "__main__":
    sys.exit(0 if verify(Path(sys.argv[1])) else 1)
