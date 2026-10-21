# Phase 4: infrastructure coverage

Status (2026-10-16): Phase 4's scripted infrastructure gate is complete. Fresh generation, reload/depot checks, the final Release build, all 103 tests, screenshot review and the actual Release launcher smoke test pass. The main guide and milestones are aligned; Phase 5 is next.

## Implementation

The opt-in OpenGL renderer now reads authoritative road bits, road stops/depot entrances, crossing rail/road axes and barrier state, tunnel directions, bridge ramp foundations, bridge axes and deck heights. Static snapshots include this state, so construction, removal and crossing changes invalidate the affected chunks. A bridge span is a separate layer above the underlying tile: roads and rails beneath it remain visible. Piers are omitted over underlying transport infrastructure so they do not obstruct the underpass. All bridge types currently share a simple concrete deck and side-rail model.

Ramp surfaces follow the engine's foundation/ramp height rule, including inclined bridge-head foundations. Tunnel entrances use a portal frame and dark inset. Road arms follow the engine's road-bit orientations; crossings retain both road and rail geometry and use the simulation's open/closed barrier state. Road stops and depots use procedural placeholders. The existing foundation mesh is retained below infrastructure.

Road vehicles now join the moving-vehicle snapshot. Each train wagon and each road-vehicle part reads its own authoritative position, direction and cached length. Hidden and depot vehicles are excluded. Vehicles above a bridge remain at their simulation deck height; vehicles beneath it remain at ground height. No pathfinding, signalling, movement, economy, command, save-format or networking code was changed. Geometry is original procedural work under the repository's GPL-2.0 license; no external models or generated bitmap assets are used.

## Demo

From the workspace root:

```powershell
.\tools\phase4-demo.ps1
```

The saved 64x64 map comes from the validated reload/depot run and starts paused. Use the original pause button to run it. The coal train serves the mine and power station, crossing a bridge, slopes, a tunnel and a level crossing. Three trucks exercise the parallel road bridge/tunnel route, the perpendicular bridge/tunnel route, the level crossing and both underpasses. Truck orders are movement fixtures; the train is the cargo/income test.

The routes belong to company 2. In this offline fixture, **Ctrl+Alt+C > Change company** lets you manage them; company 1 remains available for your own construction. Use the normal construction tools in the fixed classic camera. Console commands `renderer_3d off` / `on` switch presentation. `renderer_3d camera 0 100` restores the supported camera; `camera 90 80` is an inspection view. `scrollto instant 20 32` with `zoomto 1` focuses the bridges and underpasses; `(36,31)` focuses the rail tunnel and crossing; `(54,28)` focuses the perpendicular road infrastructure.

The launcher copies matching build language/base files into `.runtime/phase4-demo`, keeping the normal OpenTTD profile separate. It requires the Phase 0 OpenGFX installation and the Release build with `OPTION_3D_PROOF=ON`.

```powershell
.\tools\phase4-demo.ps1 -Generate
.\tools\phase4-demo.ps1 -SmokeTest
```

`-Generate` builds from seed 20261016 using the checked-in AI and ordinary public construction commands. It saves under the isolated profile; it does not overwrite the checked-in fixture. It funds the industries with the explicitly configured loan and plants trees through normal commands to restore town ratings after construction. It also sends the train and one truck to their depots and restarts them, preserving the test-completion flag in the save. After that test, the AI only monitors traffic. `-SmokeTest` loads the checked-in save, captures settled views in a separate camera/capture sequence, switches to classic and back, saves/pauses and exits. The separate `reload` script set also exercises normal speed and depot round trips; the `capture` set uses fast-forward for repeatable visual review. Launcher exit/screenshot checks are startup evidence; the runtime verifier below checks actual operation.

## Verification and evidence

- Capped Release build passes; **103/103 CTest tests pass**, including existing savegame regressions. The new ramp test checks all four directions, three foundation elevations, every integer tile position, inclined-head height, and continuous tile-edge joins against the engine's slope calculations.
- Fresh generation builds/removes/rebuilds rail and road bridges, rail and road tunnels, a road segment and a rail segment through ordinary commands. It constructs a level crossing and road junctions. Both transport types traverse slopes. The perpendicular bridge uses single-corner terrain requiring inclined foundations.
- The live audit finds **six portals, six bridge heads, nine span tiles and one crossing**, with **3,072 ramp/portal height comparisons and zero failures** against `GetSlopePixelZ(..., true)`.
- Runtime observations record the train and trucks on bridge decks at `z=16`; the underpass truck is at `z=8` below those decks. Both road bridge axes are exercised. Trains and trucks are omitted inside tunnels and reappear on exit. Crossing barriers open and close while the train passes.
- The separate reload run preserves all routes and orders, continues delivery, verifies a train and truck depot round trip (hidden in depot, restarted successfully), and exercises normal/fast speed and classic/3D switching. The final-build generation repeats the depot checks.
- The final `tools/phase4-demo.ps1 -SmokeTest` run uses the actual Release executable, loads the checked-in paused save, captures six settled views, saves/pauses and exits with status zero. Captures were visually reviewed after the road-stop orientation correction; camera setup and capture occur in separate scheduled steps, and annual finance popups are disabled in this isolated profile.
- The actual Release `-Generate` launcher also passes, producing a fresh save and screenshot before normal exit. Generation schedules quitting in a separate step so the screenshot request finishes before shutdown; see `generator-launcher.log`.
- The coal train loads **90 coal**, unloads and earns income. Road monitoring records movement across more than ten distinct tiles, with independent vehicle-state observations of the perpendicular route and underpasses.

The read-only console command `renderer_3d infrastructure` reports infrastructure counts and height checks, then enables diagnostic vehicle/crossing observations at `-d driver=1`. Vehicle event codes are: `1` depot, `2` hidden, `4` on deck, `8` below deck, `16` visible at a portal, `32` crossing, `128` reappeared after hiding. Records are limited to one per vehicle/category/tile. This is diagnostic logging, not simulation control.

See the [screenshot gallery](evidence/phase4/gallery.html). Logs and app-generated captures are in [evidence/phase4](evidence/phase4/). The fixture AI, generation scripts, reload scripts, config and save are in [fixtures/phase4](fixtures/phase4/). To verify the recorded runtime evidence from the workspace root:

```powershell
python tools/verify-phase4.py OpenTTD-15.3/OpenTTD-15.3/docs/3d/evidence/phase4/generate.log
python tools/verify-phase4.py OpenTTD-15.3/OpenTTD-15.3/docs/3d/evidence/phase4/reload.log --reload
```

For detailed runtime logging, copy the Release executable to a console-subsystem executable using the Phase 0 `editbin /subsystem:console` procedure and launch with the same isolated profile and `-d script=4,driver=1`. Build with the established **one-project/two-compiler-worker** cap; see [phase3.md](phase3.md) for build and CTest commands.

## Performance and limits

The fresh-generation run recorded 5,651 cache-miss viewport render/readback samples at 1280x900: median **3,485 microseconds**, p95 **5,467 microseconds**, maximum **16,521 microseconds**. These are observed CPU projection/upload/render/synchronous-readback times, not isolated GPU timings. CTest overlapped the start of generation, and a separate Release screenshot run was also active; this is not an isolated benchmark. This small map with one train and three trucks is not evidence of large-map performance. Full-map snapshot scanning and synchronous readback remain known costs.

Bridge style variants, electrification, tram-specific art, road signs/one-way markings, detailed stops, town buildings and vehicle-specific models remain placeholder/asset work. Ships, aircraft and aqueduct rendering remain follow-up coverage; an aqueduct is not represented as railway track. Exhaustive steep/half-tile combinations, intersecting elevated structures and every base-content variation are not claimed tested. This phase verifies ordinary rail/road construction and traffic across the documented layered fixture.

Native mouse/drag, OS resize, cursor/tooltip and DPI-transition checks remain the explicit Phase 1 manual follow-up. These screenshots are application framebuffer captures, not native-input evidence. Rotated views remain inspection controls; layer-selective picking, full rotated-camera click fidelity and occlusion controls remain usability work. Multiplayer determinism and the supplied archive's network-version limitation remain separate tests.

Changed engine files: `video/rail3d_impl.h`, `video/rail3d_geometry.h`, `video/terrain3d_impl.h`, `video/proof3d_impl.h`, `video/proof3d.h`, `video/opengl.cpp`, `console_cmds.cpp`, `viewport.cpp`, and `tests/terrain3d.cpp`. The launcher, evidence verifier, fixture and captures accompany them. The next planned milestone is Phase 5's coherent base-game assets.
