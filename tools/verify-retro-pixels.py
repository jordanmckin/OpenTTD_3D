"""Integration assertions for optional 3D pixel treatment and its button panel."""
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

run = Path(sys.argv[1])
logs = {p.stem: p.read_text(errors="replace") for p in run.glob("*.log")}
for name, log in logs.items():
    assert not re.search(r"(3D .*OpenGL error|3D proof failed|Assertion failed|command not found|ERROR:|Error:.*script)", log, re.I), name
references = re.findall(r"layer-reference valid=(\w+) differing=(\d+) pixels=(\d+)", logs["controls"])
assert len(references) > 10, len(references)
assert "action=status panel=false enabled=true size=3 colours=false dither=false" in logs["controls"], "fresh graphics defaults"
assert all(valid in ("true", "1") and int(differing) == 0 for valid, differing, pixels in references), references
assert "panel=false enabled=false size=2 colours=true dither=true" in logs["controls"]
assert "panel=true enabled=true size=2 colours=true dither=true" in logs["controls"]
assert "action=status panel=false enabled=true size=2 colours=true dither=true" in logs["restart"]
for name in ("controls", "restart"):
    config = (run / f"{name}.cfg").read_text(encoding="utf-8-sig")
    for key, value in (("retro", "true"), ("pixel_size", "2"), ("retro_colours", "true"), ("retro_dither", "true")):
        assert re.search(rf"^renderer_3d_{key} = {value}$", config, re.M), (name, key)

paths = {p.stem: p for p in (run / "screenshot").glob("*")}
required = ["original", "panel", "colour-1x", "retro-2x", "retro-3x", "nodither-4x", "pixels-4x", "passthrough-1x", "restored", "dither-2x", "nodither-2x", "windows-direct", "windows-readback", "chase", "cab-moving", "panel-restart", "classic-2d", "animated", "panel-scaled"]
assert all(name in paths for name in required), paths.keys()
def picture(name):
    return np.asarray(Image.open(paths[name]).convert("RGB"), dtype=np.int16)

# Away from UI, labels, and screenshot notifications. The fixture is paused.
region = np.s_[120:700, 40:1200]
original = picture("original")
assert np.array_equal(original[region], picture("restored")[region]), "disabled effect did not restore original pixels"
assert np.array_equal(original[region], picture("passthrough-1x")[region]), "1x without colour reduction was not an identity"
assert np.any(picture("dither-2x")[region] != picture("nodither-2x")[region]), "dither toggle had no visual effect"
assert np.array_equal(original[:30, 40:1200], picture("retro-2x")[:30, 40:1200]), "toolbar was filtered"
changed = np.any(original[region] != picture("retro-2x")[region], axis=2).mean()
assert changed > 0.3, changed

# Palette values: eight levels per channel. Labels are rendered afterwards, so
# tolerate their small footprint in the world crop.
palette = np.rint(np.arange(8) * 255 / 7).astype(np.int16)
quantized = picture("nodither-4x")[region]
in_palette = np.min(np.abs(quantized[..., None] - palette), axis=-1) <= 1
assert in_palette.all(axis=2).mean() > 0.98, in_palette.all(axis=2).mean()

# The viewport begins at y=30 at this scale. Search grid phase so this remains
# valid if the toolbar height changes. Every block should be flat except labels.
block_scores = {}
for size, name in ((2, "retro-2x"), (3, "retro-3x"), (4, "pixels-4x")):
    pixels = picture(name)
    scores = []
    for dy in range(size):
        for dx in range(size):
            crop = pixels[120 + dy:680 + dy, 40 + dx:1160 + dx]
            h, w = crop.shape[:2]
            blocks = crop[:h // size * size, :w // size * size].reshape(h // size, size, w // size, size, 3)
            scores.append((blocks.max(axis=(1, 3)) == blocks.min(axis=(1, 3))).all(axis=2).mean())
    block_scores[size] = float(max(scores))
    assert max(scores) > 0.97, (name, max(scores))

# Direct layer shader and CPU readback path must agree, including overlapping
# vehicle windows. Exclude notification text at the top right and the status bar.
a, b = picture("windows-direct"), picture("windows-readback")
delta = np.abs(a[80:-30, :1100] - b[80:-30, :1100])
parity = float(np.any(delta > 2, axis=2).mean())
assert parity < 0.001, parity
result = {"passed": True, "gpu_reference_checks": len(references), "world_changed_fraction": float(changed), "flat_block_fraction": block_scores, "readback_difference_fraction": parity, "screenshots": required, "native_input": "not tested; application handlers dispatched by script"}
(run / "check-results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
