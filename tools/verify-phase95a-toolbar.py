"""Verify real application toolbar/keyboard dispatch and isolated client config restarts."""
import json
import re
import sys
from pathlib import Path
from PIL import Image, ImageChops

run = Path(sys.argv[1])
states = {}
for log in run.glob("*.log"):
    text = log.read_text(errors="replace")
    assert not re.search(r"(3D proof failed|Assertion failed|Error:.*script|command not found|outside of group)", text, re.I), log
    for line in text.splitlines():
        if "PHASE95A " not in line:
            continue
        fields = dict(re.findall(r"(\w+)=([^ ]+)", line.split("PHASE95A ", 1)[1]))
        if fields["action"] == "status" and fields["tag"] != "-":
            states[fields["tag"]] = fields

def check(tag, **expected):
    assert tag in states, f"missing state {tag}"
    state = states[tag]
    for key, value in expected.items():
        actual = state[key]
        if isinstance(value, bool):
            actual = actual in ("true", "1")
        assert actual == value, f"{tag}: {key}: {actual} != {value}"
    x, y, w, h = map(int, state["button"].split(","))
    sw, sh = map(int, state["screen"].split(","))
    assert w > 0 and h > 0 and 0 <= x < x + w <= sw and 0 <= y < y + h <= sh, (tag, state)

check("fresh", supported=True, enabled=False, preference=False, ground=True, hints=True)
check("escape", enabled=False, menu=False)
check("enabled", enabled=True, preference=True)
check("help", help=True, menu=False, enabled=True)
check("prefs", ground=False, hints=False, enabled=True)
check("orbit", classic=False, enabled=True)
check("classic", classic=True, enabled=True)
check("disabled", enabled=False, preference=False)
check("restart", enabled=True, preference=True, ground=False, hints=False)
check("narrow", enabled=True, screen="800,600")
check("lower", enabled=True, screen="800,600")
check("resized", enabled=True, screen="1280,900")
check("fallback", supported=False, enabled=False, preference=True)
check("fallback-help", supported=False, enabled=False, preference=True, help=True)
check("restored", supported=True, enabled=True, preference=True, ground=False, hints=False)
check("animated", supported=True, enabled=True)
check("off-saved", enabled=False, preference=False)
check("off-restart", enabled=False, preference=False)
check("scaled", supported=True, enabled=False)

for case, enabled in (("controls", True), ("fallback", True), ("animated", False), ("off-restart", False)):
    config = (run / f"{case}.cfg").read_text(encoding="utf-8-sig")
    assert re.search(rf"^renderer_3d = {'true' if enabled else 'false'}$", config, re.M), case
    assert re.search(r"^renderer_3d_ground_textures = false$", config, re.M), case
    assert re.search(r"^renderer_3d_camera_hints = false$", config, re.M), case

pictures = {p.stem: p for p in (run / "screenshot").glob("*")}
required = ["fresh", "menu-2d", "enabled", "help", "flat", "orbit", "classic", "disabled", "restart", "narrow-upper", "narrow-lower", "resized", "fallback", "fallback-help", "restored", "animated", "scaled-menu", "scaled-help"]
assert all(name in pictures for name in required), sorted(pictures)
# A large central region must change when 3D is enabled, independent of toolbar / screenshot notifications.
def changed(a, b):
    a = Image.open(pictures[a]).convert("RGB").crop((160, 180, 1100, 760))
    b = Image.open(pictures[b]).convert("RGB").crop((160, 180, 1100, 760))
    return sum(max(pixel) > 4 for pixel in ImageChops.difference(a, b).getdata()) / (a.width * a.height)
fractions = {"2d_to_3d": changed("fresh", "enabled"), "3d_to_2d": changed("classic", "disabled"), "ground_texture": changed("enabled", "flat"), "orbit": changed("flat", "orbit")}
assert fractions["2d_to_3d"] > .3, fractions
assert fractions["3d_to_2d"] > .3, fractions
assert fractions["ground_texture"] > .01, fractions
assert fractions["orbit"] > .3, fractions
upper = Image.open(pictures["narrow-upper"]).convert("RGB").crop((0, 0, 800, 70))
lower = Image.open(pictures["narrow-lower"]).convert("RGB").crop((0, 0, 800, 70))
assert sum(max(p) > 4 for p in ImageChops.difference(upper, lower).getdata()) > 500, "toolbar did not switch rows"
result = {"states": states, "image_changed_fraction": fractions, "screenshots": required, "native_mouse_dpi": "not tested: computer-use JavaScript tool unavailable"}
(run / "check-results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"passed": True, "states": len(states), "images": len(required), "image_changed_fraction": fractions}, indent=2))
