# Phase 3: first playable railway

Status (2026-10-16): Phase 3's approved scripted gate is complete. Build, cargo operation, construction/removal, reload, pause, speed controls, mode switching and presentation evidence are recorded below.

The approved sequence in `milestones.md` moves vehicles into Phase 3 and roads, crossings, bridges and tunnels into Phase 4. This milestone implements base rail, junctions, signals, depots, station platforms, industry placeholders and a locomotive/wagon presentation. It retains the original simulation and construction commands. Native mouse, OS resize and DPI-transition checks remain the explicit Phase 1 manual follow-up; scripted construction is not a claim of physical mouse automation.

## Implementation

`video/rail3d_impl.h` reads guarded rail/station map accessors. The six engine track pieces combine into junctions. Ballast and two rails follow the actual triangulated foundation surface, including inclined and half-tile surfaces. Platforms flank the station axis; a depot has three walls and an entrance facing its stored direction. Signal heads use the presence and red/green state of each track direction. Industry tiles receive simple solid building placeholders. These are original procedural primitives under GPL-2.0, with no external models or generated bitmap assets.

The terrain chunk snapshot now includes rail bits, depot orientation, station state, signal presence and signal state. Construction, removal and signal changes invalidate the affected chunk and cached view. Train snapshots are separate from static chunks: each visible engine and wagon uses its own authoritative position, heading and cached length. Hidden/depot vehicles are excluded. Vehicle movement invalidates the view without rebuilding static meshes. No interpolation, movement, signalling, pathfinding, economy, command, save-format or networking implementation has changed.

The fixed camera retains the original viewport picking integration. The original autorail selection computes the direction and alternating pieces of a drag; the 3D pass draws those pieces in yellow, or red when the original UI requests it. Station/depot rectangles retain terrain highlighting. `IsPartOfAutoLine` is shared with the classic renderer rather than reimplementing its line membership rules. Original windows still composite above the world.

## Demo

From the workspace root, run:

```powershell
.\tools\phase3-demo.ps1
```

This launches the opt-in Release executable with the saved coal railway and an isolated profile. It starts paused. Use the original pause button to run it. The train serves the mine at one end and the power plant at the other, with three coal wagons and two station orders. The construction fixture belongs to company 2; use the original offline cheat window, **Ctrl+Alt+C > Change company**, to manage that company. The fixture AI only observes the completed route. You can also construct your own railway as company 1 using the normal toolbar.

Launcher correction: with `-c` and `-X`, OpenTTD searches the config directory and executable directory, not the shell's working directory. The launcher copies the matching build's `lang` and `baseset` files into the isolated profile. This fixes the missing-language error when launching `Release/openttd.exe`; earlier renderer tests used a console executable located beside the build data and did not expose that launcher defect. `tools/phase3-demo.ps1 -SmokeTest` now exercises the actual Release executable, loads the fixture, captures a rendered screenshot and checks normal exit. This smoke test passed after the correction on 2026-10-16.

Use `renderer_3d off` / `on` in the console for classic/3D switching. `renderer_3d camera 0 100` restores the fixed classic camera; `camera 90 80` is an inspection view. `renderer_3d fastforward on|off` calls the same speed control as the original toolbar. Normal toolbar speed and pause controls remain available.

`tools/phase3-demo.ps1 -Generate` reproduces the fixture from seed 20261016. It installs the checked-in fixture AI into the isolated profile, builds through the public AI command API, and saves/pauses on April 1, 1950. It borrows an explicitly configured large loan to fund the two industries; it does not write map arrays or fabricate cargo. The AI checks coal production and acceptance within station catchment before starting the train, and saves/restores its monitoring state. The funding loan means company-wide profit is not a profitability benchmark.

The launcher requires the Phase 0 OpenGFX installation, the opt-in build and the fixture save. OpenGFX is external, not bundled. Build with the documented Phase 0 dependencies and Phase 1 `OPTION_3D_PROOF=ON`; keep the existing one-project/two-compiler-worker limit:

```powershell
& $cmake --build build/baseline --config Release --parallel 1 -- /p:CL_MPCount=2 /p:MultiProcMaxCount=2 /nodeReuse:false
& $ctest --test-dir build/baseline -C Release --output-on-failure
```

## Verification

- Release build passes; **102/102 CTest tests pass**. Two new tests compare all six mesh track endpoint pairs with the engine's track-direction exits and all eight train headings with its world-direction offsets. The existing savegame regressions remain green.
- The fixture constructs the entire route through ordinary commands, removes a middle track section, waits, and rebuilds it successfully. A junction, vertical branch and corner siding also construct successfully. The renderer updates affected chunks as these commands execute.
- A train loads **90 coal**, travels to the destination, unloads and earns income: the construction log records load `90`, then `0`, with train profit rising from `-251` to `1658`. Subsequent trips repeat. This is an operating cargo route, not a stationary vehicle mockup.
- A separate process reloads the save and logs `PHASE3 RELOADED train=0`. The train continues loading, moving and earning income after reload; its orders, wagons and railway persist.
- The screen-coordinate construction test picks **(640,450) -> tile (40,36)** through `TranslateXYToTileCoord`. The ordinary build command succeeds and reports track bits `1`; the ordinary removal command at the same screen point succeeds and reports `0`. Both changes are captured.
- Construction previews use `VpStartPlaceSizing`, `VpSelectTilesWithMethod` and `UpdateTileSelection`, the same selection path as the rail toolbar. The diagonal preview reports style `13`, origin `(560,560)`, size `(96,96)`. The original finance window correctly occludes the earlier preview capture. The final preview capture checks the track-piece overlay without filling whole tiles.
- The live cargo route runs at normal speed and the existing 500% fast-forward setting, switches to classic 2D and back, and renders at a second camera angle. A separate run pauses and saves; train log updates cease while the process remains live. The final review reloads that paused fixture, unpauses, continues cargo operation, clears the preview and exits normally with status zero.

The fixture scripts are in `fixtures/phase3/generate`, `input`, and `reload`. Copy the desired script set into the isolated profile's `scripts` directory, and the AI files into `ai/railway3d`. Launch from `build/baseline` using `-c <isolated config> -x -X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null -g <save>`; generation instead uses `-g -G 20261016`. For captured diagnostics use the console-subsystem executable technique from Phase 0 with `-d script=4,driver=1`.

Additional opt-in diagnostic commands:

- `renderer_3d clickrail <screen x> <screen y>` and `clickremove`: pick through the real viewport path, then post the ordinary single X-track build/remove command for the local company. These edit the current game and obey normal ownership, cost and terrain restrictions.
- `renderer_3d preview <tile x1> <tile y1> <tile x2> <tile y2>`: freeze an original autorail selection for capture; no construction command is sent. `renderer_3d previewclear` releases it and restores normal selection handling.
- `renderer_3d highlight off`: clear the diagnostic tile highlight.

## Evidence and performance

See `evidence/phase3/build.log`, `tests.log`, `construction.log`, `generate.log`, `reload.log`, `review.log` and `input.log`. [The image gallery](evidence/phase3/gallery.html) links the overview, rotated railway, classic fallback, build/remove, paused view and construction preview. Screenshots are app-generated framebuffer captures, not proof of native cursor or OS-window behaviour. `generate.log` verifies a fresh run of the final fixture, including its branch, through the first delivery; the checked-in save is that run's paused April 1 result.

On the small 64x64 live-route reload, **1,483 cache-miss viewport render/readback samples** measured **4,419 microseconds median**, **4,814 microseconds p95**, and **9,627 microseconds maximum**, at 1280x900. This includes CPU projection/upload/render/synchronous readback, not isolated GPU time. Moving trains cause new readbacks; these results do not establish large-map or many-train performance. Full-map snapshot scanning and synchronous readback remain known performance costs.

The final-build fresh-generation run records 750 samples: median 4,225.5 microseconds, p95 4,560 microseconds, maximum 8,308 microseconds. These include construction and moving-train frames; the test suite ran during the initial part of this session, so this is an observed workload, not an isolated benchmark.

## Limits and next step

This is deliberately placeholder art. Industry identity-specific buildings, town buildings, scenery, detailed engines and wheel animation are later asset work. All train bodies use a simple engine/wagon palette. Electric rail, monorail and maglev still have the same placeholder rail appearance; no complete base-content coverage is claimed. Terrain slopes use the Phase 2 foundation representation, but the operating cargo fixture is level; exhaustive sloped railway gameplay remains follow-up coverage.

Roads, rail-road crossings, bridges, tunnels and road vehicles belong to the approved Phase 4. They are not drawn as complete infrastructure here. Alternate camera angles remain inspection controls; vehicle-label/click alignment, tooltips and navigation at rotated angles are not claimed complete. The normal fixed camera is the supported construction view. Multiplayer determinism testing and the archive build's existing network-version limitation remain separate from this renderer milestone.

Changed implementation files: `rail3d_impl.h`, `rail3d_geometry.h`, `terrain3d_impl.h`, `proof3d_impl.h`, `opengl.cpp`, `video/CMakeLists.txt`, `console_cmds.cpp`, `viewport.cpp`, `tilehighlight_func.h`, and `tests/terrain3d.cpp`. The launcher, fixture AI/config/save/scripts and evidence accompany them. The next implementation milestone is authoritative bridge/tunnel/crossing/road geometry and deck/hidden-vehicle validation.

The milestone commit also checkpoints the terrain/compositor prerequisites and earlier evidence that were still uncommitted at the start of Phase 3. Historical Phase 1/2 reports describe the Git permission limitation at that time; staging the complete milestone is now permitted through the managed approval path.
