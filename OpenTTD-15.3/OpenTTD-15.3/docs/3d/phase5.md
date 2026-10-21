# Phase 5: coherent procedural base assets

Status (2026-10-16): scripted asset-library gate complete. Release build, all 104 tests, live coverage audit, actual Release launcher, screenshot review and a separate saved-game reload pass. The scope is a coherent town and coal industry chain, not complete base-game or NewGRF model coverage.

## What changed

A dependency-free Python generator builds 26 original low-poly models from reusable box, roof, window and cone modules. The library contains three houses, an office, church, park, monument, theater, four stadium quadrants, construction site, factory, mine hall/headframe, power hall/chimney, coal yard, live/dead trees, station platform, locomotive, wagon, truck and an obvious missing-model marker. The counted library includes the marker and the separate stadium quadrants. Shared colors and proportions give the fixture a consistent miniature style.

The renderer uses generated immutable triangle tables, with matching JSON, SVG contact sheet and license/hash manifest. This is a justified alternative to a glTF loader for the existing colored-triangle renderer. No Blender runtime, external model packages or bitmap textures are required. See [asset_spec.md](asset_spec.md) for coordinates, materials, LOD policy, identity sources, exact coverage and licensing; see [preview.svg](../../assets/3d/preview.svg) for the authoring contact sheet.

House IDs resolve through an enumerated 110-entry registry; the mine and power station use their actual industry type and tile graphics. Houses/industries under construction render scaffolding/footings. Trees read authoritative count and growth, and their trunks follow terrain height. Static state changes invalidate existing chunk meshes. Vehicles retain their simulation positions, headings, cached length, hidden/depot flags, and per-part movement. Coal appears in loaded wagons and disappears when empty. No simulation, save-format, command, network or pathfinding code changed.

## Demo and reproduction

From workspace root:

```powershell
python tools/3d_assets/generate.py --check
python tools/3d_assets/verify.py
.\tools\phase5-demo.ps1
.\tools\phase5-demo.ps1 -SmokeTest
```

The normal launcher starts paused with the existing Phase 4 coal-route save, using the new assets and an isolated `.runtime/phase5-demo` profile. Use the original pause button to run. The routes belong to company 2; the offline cheat window allows changing company. Console `renderer_3d off` / `on` preserves the classic fallback. `renderer_3d assets` prints a read-only live coverage audit. The original Phase 4 generator remains the reproducible construction fixture; Phase 5 reuses its save and AI, with its own view/capture scripts.

Useful views: town `(10,16)`, mine `(9,27)`, power station `(43,27)`, all at `zoomto 1`; railway `(29,33)` at `zoomto 2`. `renderer_3d camera 0 100` is the supported construction camera. The 90-degree view is for inspection. The smoke test schedules camera changes and captures separately, switches to classic and back, saves, pauses and exits. It allows ten minutes on slower machines and checks fresh screenshot output plus normal process exit.

Build/test commands are the established capped Release build and CTest from [build_and_test.md](build_and_test.md): one MSBuild project, at most two compiler workers. The generated header is checked in; Python is not needed to build or run the game.

## Verification

- Release build passes; **104/104 CTest tests pass**, including existing savegame regressions. The asset test checks known/unknown identity mapping, finite positions, valid material colors, nondegenerate triangles and the per-model triangle budget.
- Generator and verifier reproduce checked-in exports byte-for-byte and enumerate all 110 original house IDs. The generator verifies their sequence against this checkout's table.
- Six read-only live audits during the console capture run report **121 house tiles, 12 industry tiles, over 2,300 trees and zero missing assets** on this fixture. Construction counts and tree counts change during ordinary simulation, with chunk rebuilds recorded.
- Engine IDs 9, 29 and 123 resolve to the locomotive, wagon and truck. The original fixture AI continues reporting movement and both 90-coal and empty-train observations.
- Town, mine, power, whole railway, rotated and classic/restored views were captured and visually inspected. The initial art review found stadium/theater placeholders; those now have curated geometry. Stadium quadrants match the original house tile ordering.

- The actual Release `-SmokeTest` launcher exits zero with fresh screenshots and a new save. A separate console-subsystem run loads that new `phase5-preview.sav`, advances the simulation, captures it, saves again and exits zero. It reports 122 house tiles, 12 industry tiles, over 2,400 trees and zero missing assets; all 3,072 infrastructure height checks still pass. Its scripts are in `fixtures/phase5/reload`; it uses a separate `.runtime/phase5-reload` profile with the same copied base/language/AI files. The console-subsystem preparation follows the documented Phase 0 procedure.

See the [screenshot gallery](evidence/phase5/gallery.html), [runtime audit](evidence/phase5/runtime.log), [reload log](evidence/phase5/reload.log), [build log](evidence/phase5/build.log), and [test log](evidence/phase5/tests.log). Captures are application framebuffer evidence, not native-input automation.

Changed engine files: `video/asset3d_impl.h`, `video/asset3d_generated.h`, `video/terrain3d_impl.h`, `video/rail3d_impl.h`, `video/opengl.cpp`, `video/proof3d.h`, `console_cmds.cpp`, and `tests/terrain3d.cpp`. Generator/verifier, exported library, launcher, capture/reload scripts, specification and evidence accompany them.

Runtime evidence can be rechecked with `python tools/3d_assets/verify.py <runtime-log>`. The verifier requires multiple live audits, the mine/power submodels, the expected vehicle mappings, full and empty coal observations, zero missing assets in this map, and no reported fatal/assertion/fixture errors.

## Performance and limits

The console capture run records 4,737 cache-miss render/readback samples at 1280x900: median **10,751 microseconds**, p95 **12,629 microseconds**, maximum **29,597 microseconds**. These are CPU projection/upload/render/synchronous-readback measurements, not isolated GPU timing or FPS. CTest overlapped the beginning of the run; the changing viewpoints and visible geometry differ from Phase 4, so this is not a controlled performance comparison. Extra scenery increases CPU geometry cost. Full-map snapshots, per-frame vehicle triangle rebuilding and synchronous readback remain known costs; large-map profiling belongs to Phase 7.

The art is intentionally stylized and shared by category. Factory geometry is export/geometry-tested but not exercised by this coal fixture. Most multi-tile offices/hotels use one module per tile; exact silhouettes, seasonal/species art, wheel animation, company colors, the remaining industries, ships and aircraft remain follow-up. Three original non-temperate house IDs and unknown IDs have magenta markers; unsupported vehicles retain the Phase 4 generic box models. Existing bridge/depot/road-stop assets remain generic. No complete base-content coverage claim is made.

Native mouse/drag, resize, cursor and DPI-transition tests remain the explicitly carried Phase 1 follow-up. Rotated-camera picking/occlusion, exhaustive climates and content, and multiplayer determinism remain Phase 6 work. The next smallest task is a targeted construction/picking and building-occlusion usability fixture in the fixed camera.
