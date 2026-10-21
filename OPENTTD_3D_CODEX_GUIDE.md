# OpenTTD 3D — Codex Implementation Guide

## Mission

### Approved scope update (2026-10-16)
- Use a small custom renderer within OpenTTD, initially targeting its Windows OpenGL backend. Godot is not a runtime dependency.
- Support base-game content only for this iteration. NewGRF model mapping, billboard compatibility, and mod testing are deferred; preserve the existing 2D behavior. Base graphics such as OpenGFX remain necessary and are distinct from gameplay NewGRFs.
- Move basic height-aware picking, tile highlights, and coordinate tests into Phase 2. Test overlapping windows, additional viewports, DPI, and resize behavior in Phase 1.
- Prioritize a readable, playable miniature railway. Discrete vehicle turns and imperfect early graphics are acceptable; simulation changes to disguise them are not.
- Bring the placeholder locomotive and wagons into Phase 3's first playable railway. Roads, crossings, bridges, tunnels, and road vehicles belong to Phase 4.
- The phase sequence below matches [milestones.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/milestones.md). Keep both documents aligned when scope or milestone status changes. NewGRF compatibility work remains deferred.

### Current progress (updated 2026-10-20)

- **Phase 0:** baseline established; architecture and build evidence recorded in [architecture_audit.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/architecture_audit.md) and [build_and_test.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/build_and_test.md).
- **Phase 1:** rendering proof implemented; Release build and 96 tests passed. Scripted compositing, viewports, scaling, mode switching, and fallback checks passed. Native mouse, window resize, cursor/tooltip, and DPI-transition checks remain manual follow-up. See [phase1.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase1.md).
- **Phase 2:** terrain, foundations, water, chunk invalidation, camera inspection, and height-aware picking implemented; small-map scripted gate verified with 100 tests passing. See [phase2.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase2.md).
- **Phase 3:** approved scripted cargo-route gate complete; Release build and **102/102 tests passed**. Rail construction/removal, live signals, trains delivering 90 coal, save/reload, pause, speed controls, and 2D/3D switching verified. The Release launcher smoke test also passed after its data-lookup fix. Run `.\tools\phase3-demo.ps1`; see [phase3.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase3.md) for evidence and limitations.
- **Phase 4:** scripted infrastructure gate complete. Rail/road bridges, tunnels, inclined foundations, slopes, crossings and three moving trucks are verified alongside the coal train. Release build and **103/103 tests passed**; **3,072 live height checks found zero failures**. Construction/removal, traffic above and below bridges, tunnel hiding, depot round trips, reload and classic/3D switching passed. Run `.\tools\phase4-demo.ps1` or open the [screenshot gallery](OpenTTD-15.3/OpenTTD-15.3/docs/3d/evidence/phase4/gallery.html). See [phase4.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase4.md) for evidence and limits.
- **Phase 5:** scripted coherent-asset gate complete. A deterministic Python generator produces **26 models**, a 110-entry house registry, compiled meshes, JSON, previews and license metadata. Towns, mine/power tiles, trees, platforms and mapped train/truck assets render coherently; fixture audits report zero missing map assets. Release build, **104/104 tests**, launcher captures, classic switching and a separate saved-game reload pass. Run `.\tools\phase5-demo.ps1`; see [phase5.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase5.md) and the [gallery](OpenTTD-15.3/OpenTTD-15.3/docs/3d/evidence/phase5/gallery.html).
- **Phase 6:** implementation and scripted checks complete; **native interaction acceptance pending**. Fixed-camera ground picking, transparency/invisibility, basic air/water rendering, four-climate audits, air/water AI save/reload and same-binary localhost synchronization checks are implemented and tested. Release build and **104/104 tests** pass. Run `.\tools\phase6-demo.ps1` (or `-Scene AirWater`); see [phase6.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase6.md), its explicit coverage matrix, and [manual Windows checklist](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase6-manual-tests.md). Existing art remains shared/placeholders; Phase 7 performance and Phase 8 final art remain separate. The Phase 6 rotated-camera restriction is superseded by [9.5e rotated management](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase95e-management.md).

- **Phase 7:** Latest (2026-10-19): retained static instance streams and variable model slots are implemented; final Release and **118/118 tests pass**. Broad visual checks passed before the final duplicate-write cleanup. Preliminary four-window fleet drawing improves **7.08 to 5.58 ms**, with instance uploads **1649 to 130 KiB/pass**. Final post-cleanup visual/timing reruns were stopped at the user's request to finish the session. See [phase7-streams.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-streams.md) for verified evidence and exact resume commands. General release acceptance remains open.

Build an optional low-poly 3D presentation mode **inside a fork of OpenTTD**, preserving the original simulation, commands, economy, routing, signalling, saves, multiplayer determinism, and GUI behavior. The visual target is an early-2000s miniature railway tycoon: colorful, clean low-poly shapes, readable silhouettes, modest texture detail, and convincing miniature terrain. This is **not** a new simulation or a Godot remake.

## Instructions to Codex
You are working in a user-supplied clone of https://github.com/OpenTTD/OpenTTD. First inspect the checked-out commit and actual source before naming integration points or changing code. Treat this document as a design brief, not as proof that a particular internal API exists. Work incrementally, compile and test each milestone, and summarize changed files, results, and limitations. Never rewrite simulation systems to accommodate rendering. Do not delete or replace the existing 2D renderer. Keep new code behind a build/runtime option where practical. Do not begin bulk asset generation until a real map renders successfully.

### Non-negotiable rules
1. The game simulation remains authoritative; 3D scene objects are disposable projections of game state.
2. Do not change game tick rates, deterministic logic, map data, save format, networking messages, or game commands merely for graphics.
3. Do not mutate simulation state from rendering callbacks. Construction and interaction must call existing game commands.
4. Preserve the original GUI; determine a technically sound 2D UI-over-3D compositing path and maintain DPI, clipping, cursors, text, and window ordering.
5. A fixed classic isometric camera comes first. Camera rotation and free tilt are later features requiring picking and occlusion redesign.
6. Use a reversible, opt-in 3D mode with a working 2D fallback.
7. Treat arbitrary NewGRF content as a compatibility challenge. Do not claim full compatibility until tested. A sprite billboard fallback is a goal, not an assumed trivial solution.
8. Keep OpenTTD copyright and GPL requirements; track licensing for models, textures, shaders, and generated assets.

## Visual direction
- Low-poly early-2000s 3D transport simulation; clean silhouettes, restrained polygon counts, colorful terrain, bright railway infrastructure.
- Buildings: stylized industrial architecture, simple roofs, readable windows and chimneys; small variants rather than unique handcrafted meshes for every object.
- Vehicles: recognizable locomotives, trucks, ships, aircraft; simple wheel animation and consistent scales.
- Terrain: tiled or chunked geometry, height and slope faithful to game data; stylized flat or lightly shaded materials.
- Default camera: orthographic/isometric to match gameplay readability. Keep track geometry and signals legible at normal zoom.
- Do not introduce photorealism, complex PBR textures, or high-poly models in the MVP.

## Phase 0 — Repository reconnaissance and baseline (mandatory)
**Tasks**
- Record git revision, build platform, toolchain, installed dependencies, and licensing requirements.
- Read `README.md`, `COMPILING.md`, `CMakeLists.txt`, `CODINGSTYLE.md`, and relevant source directories.
- Build unmodified OpenTTD in a separate build directory. Run the application with base graphics installed; load or create a small test map.
- Identify and document: game loop, video backends, OpenGL implementation, viewport projection, sprite draw pipeline, UI compositor, terrain/tile access, vehicle coordinates and orientations, bridge/tunnel representation, sprite/NewGRF rendering, dirty-region updates, and mouse picking.
- Write `docs/3d/architecture_audit.md` with exact files/functions, diagrams, risks, and a proposed integration seam.
- Write `docs/3d/build_and_test.md` with verified commands for this checkout.

**Gate:** Existing game builds and runs unchanged. No speculative engine-wide rewrite. Stop and report blockers if baseline cannot be established.

## Phase 1 — Minimal 3D rendering proof
**Tasks**
- Prototype an opt-in 3D world viewport while preserving the existing menus and toolbars.
- Choose the simplest sustainable rendering integration after auditing the source. Existing OpenGL support may be useful but must not be assumed to be a ready 3D renderer.
- Render a test triangle/cube with a depth buffer, resize handling, and correct compositing with the original UI.
- Render a flat patch of world tiles with distinct colors and known world-to-screen coordinates.
- Verify overlapping windows, a secondary viewport, resize, DPI scaling, cursors, and tooltips; distinguish scripted captures from native interaction checks.
- Keep game speed, pause, menu interaction, save/load, and input unaffected.

**Gate:** A real OpenTTD session displays a 3D world surface behind its functional original UI, and can switch back to 2D.

## Phase 2 — Terrain geometry and camera
**Tasks**
- Read actual tile corner elevations and slope rules. Match OpenTTD's terrain and foundations; do not infer terrain heights from sprite appearances.
- Generate chunk meshes (e.g. 16×16 or 32×32 tiles, benchmark both). Rebuild only affected chunks on terrain changes.
- Implement water, coastline, terrain materials, foundation edges, and a fixed isometric orthographic camera.
- Implement zoom, pan, map-edge handling, clipping, frustum culling, and a debug wireframe/grid mode.
- Define a stable coordinate conversion with tests for tile corners, height, slopes, and screen positions.
- Implement early height-aware picking and tile highlights; verify terrain edits through existing commands and persistence after reload. Yaw/tilt controls may be used for inspection captures; general rotated-camera interaction remains later work.

**Gate:** Real generated maps, including slopes and water, render correctly; terrain modifications update visually; frame time is measured.

## Phase 3 — First playable railway
**Tasks**
- Read authoritative tile infrastructure state; build base rail and junction meshes based on actual orientations, combinations, elevations, and foundations.
- Render depots, station platforms, live signals, and simple industry placeholders.
- Extract per-frame presentation state from authoritative vehicle positions, directions, elevation, and consist structure; render a placeholder locomotive and wagons. Accept discrete turns without changing movement rules.
- Implement construction/removal and autorail drag previews using the original game commands and UI.
- Never replace rail pathfinding or signalling logic.

**Gate:** Construct and operate one cargo route with correct 3D visual updates; verify save/reload, pause, speed changes, and 2D switching. The scripted gate is complete; native mouse/drag checks remain explicitly outstanding.

## Phase 4 — Infrastructure coverage
**Status:** Scripted gate complete (2026-10-16); demo, screenshots and validation are linked in Current progress above.

**Tasks**
- Extend authoritative infrastructure geometry to bridges, tunnel portals, foundations, rail-road crossings, and roads.
- Add road vehicles; ship and aircraft coverage follows.
- Validate vehicle deck heights, tunnel hiding, depot entry, turns, and slopes using original simulation state.
- Exercise construction and movement across terrain and layered infrastructure; document unsupported cases.
- Add interpolation only if purely visual and without altering deterministic simulation or networking.

**Gate:** Clear construction and movement across terrain and layered infrastructure, including correct vehicle heights and visibility, with unsupported cases documented.

## Phase 5 — Buildings, industries, scenery and asset tools
**Tasks**
- Define an asset specification: glTF/GLB or another justified runtime format, units, origin, orientation, LOD policy, materials, naming, metadata, and license manifest.
- Establish a model registry keyed by verified base-game identities, with obvious placeholders for missing models. NewGRF mapping is deferred.
- Create a Python/Blender procedural generator for a small curated library: house variants, office, factory, coal mine, power station, station platform, trees, locomotive, wagon, truck.
- Produce deterministic seeds, palettes, reusable roof/window/chimney modules, and previews. Keep source scripts alongside exported assets.
- Track base-content coverage explicitly; do not claim complete coverage until enumerated and tested. Sprite billboard compatibility remains a separately scoped follow-up.

**Gate:** One town and one industry chain are visually coherent without requiring manual creation of every object.

## Phase 6 — Usability and base-content coverage
**Tasks**
- Implement robust world-space mouse picking, height-aware selection, construction previews, tooltips, window overlap, and occlusion/transparency for structures blocking tracks.
- Expand save/load, game speed, AI, and graphics-switching fixtures. Test multiplayer determinism separately from network version-handshake compatibility.
- Test multiple landscapes, climate types, station types, base transport types, and unusual slopes. Maintain an explicit coverage matrix; NewGRF testing is deferred.
- Improve occlusion, tooltip/click fidelity, and secondary views. General camera rotation/tilt usability, day/night lighting, shadows, and visual polish remain separately scoped follow-ups.

**Gate:** Standard construction and management tasks are as precise as in classic OpenTTD.

## Phase 7 — Performance and release readiness
**User-reported priority (2026-10-16):** 3D performance is poor overall and worsens with multiple vehicle windows open. The user explicitly deferred this issue to Phase 7. Profile zero, one and several vehicle windows on the same running map, investigating viewport cache churn, repeated scans, full-screen invalidation and synchronous GPU readback. Record measured before/after results.

**Tasks**
- Profile CPU/GPU frame times, mesh rebuilding, asset loads, memory use, and viewport redraws.
- Benchmark 128×128, 512×512, and larger maps as feasible, with dense towns and hundreds of vehicles. Report actual results, not estimated FPS.
- Use chunking, mesh/material batching, instancing, view culling, and asset LOD where measurements justify them.
- Document GPL obligations, third-party asset provenance, build instructions, known compatibility limitations, and release packaging.

**Completed priorities from the earlier request (2026-10-16):**
1. Replace whole-map polling with dirty-chunk tracking, including shared corners and reload invalidation; retain full scanning as a correctness reference.
2. Retain static chunk geometry in GPU buffers and transform it per viewport in the shader; upload changed chunks and handle moving vehicles separately.
Both priorities are implemented and verified. See [phase7-retained.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-retained.md) for implementation, correctness evidence, before/after timings and remaining costs.

The CPU follow-up also reuses unchanged tile geometry inside dirty chunks, with independent full-mesh comparisons and a `chunked`/`optimized` diagnostic benchmark. See [phase7-tiles.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-tiles.md). The subsequent [dirty-tile checkpoint](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-dirty-tiles.md) reads only affected snapshots. Visible changed chunks still copy/upload their packed geometry; whole-map snapshots and synchronous readback remain. Priority 2 now defers offscreen rebuilding and bounds retained geometry; see [phase7-offscreen.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-offscreen.md).

**Performance follow-ups (recorded 2026-10-16): priorities 1–2 complete; priorities 3–5 planned, in order:**

1. **Complete:** track dirty tiles within chunks to avoid reading unchanged authoritative snapshots; retain shared-corner/reload correctness and the full-scan reference. See [phase7-dirty-tiles.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-dirty-tiles.md).
2. **Complete:** defer offscreen mesh rebuilding, coalesce changes and bound retained CPU/GPU geometry while preserving every viewport and picking. See [phase7-offscreen.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-offscreen.md).
3. Patch geometry more narrowly in CPU meshes and GPU buffers, handling variable face counts and bounded allocation without whole-chunk copying/uploads.
4. Reduce GPU readback and compositing costs, especially with multiple vehicle windows; preserve window ordering, clipping, screenshots and current-state presentation.
5. Invalidate smaller screen regions for localized changes, covering old/new bounds and every active viewport without stale pixels.

**Second performance pass (recorded 2026-10-18, before closing Phase 8):** priorities 6–12 are tracked in [phase7.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7.md#second-performance-pass-recorded-2026-10-18). They are: (6) re-baseline with the Phase 8 art, an end-to-end frame-time measurement and a large map with a fleet; (7) limit vehicle and effect invalidation to the views that see the change; (8) remove the synchronous readback; (9) instanced draws; (10) vehicle/model LOD; (11) draw static library art as instances instead of baking it into chunk meshes; (12) animated-tile churn. Priorities 6, 7, 8, 9 and 12 are done ([rebaseline](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-rebaseline.md), [direct presentation](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-direct.md), [per-tile chunk updates](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-p12.md)); see [scoped invalidation](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-p7.md) and [instancing](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-p9.md). Priority 10 is evaluated as an opt-in candidate; full detail remains the default after a measured four-window regression ([LOD report](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-p10.md)); priority 11 is implemented as a measured memory optimisation ([static library sharing](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-p11.md)).

Detailed scope, measurement targets and correctness requirements are in [the Phase 7 roadmap](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase7-tiles.md#next-performance-priorities-recorded-2026-10-16). Priorities 1–2 are implemented and verified; items 3–5 remain planned. Preserve simulation behavior and record each passing implementation checkpoint separately.

## Phase 8 — Hand-modelled base-game art
**Status:** Replanned by user request (2026-10-16). Detailed plan: [phase8.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase8.md). Keep Phase 5 art as the fallback until each identity is replaced; Phase 7 continues independently.

**Direction:** every base-game visual identity (about 450–500 models) gets its own low-poly model in Blender, built through the user's Blender MCP and approved by the user, using the original game sprite as reference. Do not use third-party asset packs. Each `.blend` is the editable source of truth.

**Build approaches (agreed with the user):** `bespoke`: one individually modelled `.blend` per identity for houses, industries, landmarks and stations. `kit`: vehicles assembled from a user-approved shared Blender parts library, each still its own model. `family`: one parametric Blender Python script per family (trees, fences/hedges, signal variants, bridge spans, ground props) producing every member from a parameter table, approved as a family. Record `approach` per identity in `inventory.json`.

**Multi-tile objects:** houses are one whole model drawn from the north tile; other tiles draw ground only; culling uses full model bounds. Industries are modelled as one scene and cut on the 16-unit grid into per-tile-graphic pieces that fit every base layout. Stations, depots, stops and bridges are per tile.

**Tasks**
- **8.1 Reference sprites:** primary source is the user's grfcodec export in `sprites_pulled/`, sliced by `tools/3d_assets/slice_sprites.py`; base sprite numbers equal game SpriteIDs. Map identities to sprites via the game tables and composite multi-sprite/multi-tile objects with `.nfo` offsets and table recolour palettes, one reference per identity. Fallback/verification: a presentation-only console command that draws each house, engine, depot and station with the existing classic GUI drawing code (`DrawHouseInGUI`, `DrawVehicleEngine`, depot/station build-menu drawing) to PNG at 2×/4× zoom, one file per identity per climate; capture industries, bridges, tunnel portals, trees and other map-only objects from a fixture map. Write `assets/3d/inventory.json` listing every identity, its states and status, including landscape objects: all 41 tree species with growth/dying states, transmitter, lighthouse, statue, owned-land flag, five HQ sizes, field fences/hedges, optional rock/bush props, buoys, locks, ship depots, docks, signals, level crossings and catenary.
- **8.2 Pipeline:** conventions file and template `.blend` matching `asset_spec.md` units/origins; shared flat-colour palette; `cc1`/`cc2` company-colour materials; named state collections; Blender export to glTF with preview renders; a standard-library converter that validates and emits embedded runtime data (no runtime glTF parser); per-identity fallback to Phase 5, then magenta.
- **8.3 Ground textures:** before the pilot set. Replace flat ground colours with a texture array sampled from world-position coordinates, multiplied by the existing per-triangle light and blended across tile edges; use grass density, rough, rocky, field type (`GetFieldType`), snow/desert density and shore state, adding new state to snapshot comparison. Textures are authored in Blender, approved by the user and embedded at build time; flat colours remain the fallback. Terrain slope geometry and lighting are unchanged; shadows and AO are out of scope by user decision. Record the measured Phase 7 cost.
- **8.4 Pilot set:** model the static identities in the current temperate town capture into the game: houses, coal mine and power station, signals and crossing, plus the temperate tree family script. The approved church (`house_003`) is the static style reference.
- **8.5 Vehicles (high detail):** separate step at the user's request. Trains and other vehicles get the most detail, with an expanded triangle budget agreed with the user and checked against the Phase 7 vehicle stress benchmark (LOD before cutting detail). The vehicle kit is approved first, then the pilot locomotive, coal wagons and coal truck, then the remaining vehicles.
- **8.6 Production:** one identity per task for `bespoke`, kit then members for `kit`, family script then member review for `family`, from the inventory, category by category, temperate only. Everything specific to the other climates is deferred to Phase 10. Each task delivers `.blend`, export, previews, converted asset and inventory update.
- **8.7 States and polish:** construction/load/growth states, company colours and user-requested presentation-only animations from authoritative state.
- **8.8 Final checks:** re-run Phase 7 performance/packaging and Phase 4–6 live fixtures; add LOD or reduce budgets only where measured.

**Review loop per model:** reference PNG → Blender model → preview beside reference → corrections → user approval → export/convert → in-game check → inventory update.

**Gate:** every inventory identity used in the temperate climate, including landscape objects and ground textures, is in game or intentionally shared with a reason; identities only found in other climates are Phase 10; textured ground works in every viewport; no Phase 5 fallbacks or magenta placeholders remain in temperate; user approval recorded; footprints, picking, occlusion, simulation behavior and performance preserved. NewGRF models remain separately scoped.


##phase 8.5 smoke from trains? exhaust from trucks?

## Phase 9 — First-person and chase views
**Status:** Original 9.1 through 9.6 done (2026-10-19). **9.5a toolbar access was approved by the user on 2026-10-19. 9.5b labels were approved by the user on 2026-10-19; scripted verification passes. 9.5c shadows were approved by the user on 2026-10-19 (contact shadows default, sun shadows optional).** **9.5d was approved by the user on 2026-10-20; scripted verification passes.** **9.5e is implemented and scripted verification passes; user review is pending.** **9.5g zoomed-out performance was accepted by the user on 2026-10-20 after the local test-release handoff.** Parallel cold-chunk building is deferred unless needed; 9.5f spectator expansion remains optional. LOD remains off by explicit user instruction. Detailed plan and evidence: [phase9.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase9.md). Presentation and client settings only; no simulation rules, save-format or network changes.

**Direction:** the vehicle window's own viewport switches between normal, cab view (front of the vehicle, looking forward) and chase view (behind and above it). The main view and the rest of the UI are unaffected; dragging the window bigger enlarges the view. No picking inside these viewports. A small vehicle-window button and a `vehicleview` hotkey cycle normal → cab → chase. Returning to normal is an instant snap back. Tunnels fade to black.

**Slices**
- **9.1 Per-viewport camera override — done:** `Viewport::camera_3d`/`camera_vehicle`; `TerrainCamera()` takes each view's angle and the image key carries it exactly; no picking or clicks in these views; `renderer_3d view <id|all> normal|cab|chase`. Orthographic heading-up stand-in until 9.2. 119/119 tests; `tools/phase9-checks.ps1` shows other views pixel-identical and exact restore.
- **9.2 Perspective projection and culling — done:** `Terrain3D::PerspectiveCamera` (eye, heading, pitch, field of view, near plane 1, 64-tile draw distance); `viewProjection`/`eye`/`fog` uniforms in both shader programs; `Visible()` tests the frustum planes, whose far plane is the draw distance; fog from 60% of it into a matching sky clear colour. Orthographic views take the old path unchanged. Test camera: `renderer_3d eye <id|all> <+x> <+y> <height> <heading|ahead> <pitch> [fov]` and `renderer_3d windowsize`. 120/120 tests; `tools/phase9-perspective.ps1` (plus `-Fleet`) matches the unculled reference with no gaps. On the 512 map, CPU per render stays the same, and GPU per render rises from 0.14 to 0.47 ms (one window) and from 0.31 to 0.79 ms (four).
- **9.3 Chase view — done:** perspective eye 3.5 tiles behind and 1.5 tiles up, kept above the ground (`Terrain3D::ChaseEye`). `Terrain3D::FollowChase` eases position (0.12 s, at most 24 units behind) and heading (0.8 s or 1.5 tiles travelled, at most 240°/s), and eases out jumps such as a train reversing, once per frame from `UpdateViewportPosition`. Vehicle-window camera button (`WID_VV_CAMERA`) and `camera` hotkey `V` in the `vehicleview` list switch normal ↔ chase (cab joins in 9.4). These views drop the "3D TRANSPORT" banner for a small corner label. 121/121 tests; `tools/phase9-chase.ps1` (railway, plus `-Save AirWater`): at most 4.3° of turn and 3.3 units of excess eye movement per frame for train, trucks, ship and aircraft, against 43–78 unsmoothed; button and hotkey are same-tick exact; pause and reload are clean.
- **9.4 Cab view — done:** perspective eye on the front tip of the vehicle's own model at 80% of its front height (bow for ships, nose for aircraft), 6° down along the heading, 70° field of view, tipping with slopes (`Terrain3D::CabEye`, `CabMount3D`). `FollowChase` takes a `FollowTiming`; `CAB_TIMING` stays on the vehicle and cuts on a train reversal. The cab's own vehicle instance is left out (`Camera::hidden`, image key 21 ints). Button and `V` cycle normal → cab → chase → normal. 122/122 tests; `tools/phase9-cab.ps1` (plus `-Save AirWater`): button and hotkey same-tick exact, own vehicle never drawn, no holes below the horizon, turn rate within the cap for train, trucks, ship and aircraft. Confirmed in game by the user.
- **9.5 Exits and edge cases — done:** cab and chase views go black into tunnels and fade back in, from the game's tunnel and hidden state (darkening over the last 8 units before the vehicle hides, 0.4 s fade-in, a cab stays black until its eye is out of the portal; `Terrain3D::TunnelDark`, `Viewport::camera_dark`, `DrawProofFade`, image key 22 ints). Views snap back to normal on a crash or in a depot or hangar, and no view keeps a deleted vehicle's ID. Test-only console `renderer_3d ride` and `renderer_3d onride`; fixture AIs for a dead-end road with overtaking and turning (railway save) and for planes and helicopters on a 2005 map. 123/123 tests; `tools/phase9-exits.ps1` (plus `-Save Air`): every case exercised with screenshots. One finding: thin airport towers differ from the reference by single-pixel edges up close (up to 2.5%); that is existing geometry, not the fade.
- **9.5a Toolbar access and 3D settings - approved 2026-10-19:** main-toolbar 3D dropdown in the complete and both collapsed layouts, saved enable/terrain-texture/camera-hint preferences, camera controls and help, and Ctrl+Alt+3 with keyboard menu navigation. Development banner removed; unsupported drivers fall back to classic and retain the preference. Release and 123/123 tests pass; 19 scripted states and 18 captures verify launch/restart, fallback, overlap, resize, 200% scaling and both supported blitters. Native mouse/tooltip/DPI checks remain open because the computer-use tool is unavailable. See [report and checklist](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase95a-toolbar.md).
- **9.5b Station names, town names and signs - approved 2026-10-19:** projected station/town/sign labels and floating text, shared draw/click positions, original visibility/colour/zoom preferences and viewport clipping. Release and 123/123 tests pass; 343 application label actions and 52 raster checks pass at 100%/200% and in the dense-town fixture. [Report](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase95b-labels.md).
- **9.5c Lighting and grounding experiment — approved 2026-10-19:** 3D menu preference No shadows / Contact shadows / Contact and sun shadows. Subtle contact shadows are the default; the ranged sun shadow map is optional; 12 views pass the visual check, 123/123 tests pass, costs measured approximately on a busy machine. [Report](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase95c-shadows.md).
- **9.5d Automatic visibility and selection outlines — approved 2026-10-20:** saved automatic-visibility preference, per-view obstruction cutaways and target/vehicle outlines, manual visibility and lock precedence. Release and 123/123 tests pass; 59 comparison groups, 3,132 ground-picking samples and 37 GPU references pass. [Report](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase95d-visibility.md) and [review gallery](OpenTTD-15.3/OpenTTD-15.3/docs/3d/evidence/phase9/p5d/gallery.html).
- **9.5e Rotated management and construction — implemented; review pending:** accurate selection, labels, measurement tooltips, rectangular/diagonal highlights and rail build/remove drag previews work at rotated orthographic angles through existing commands, without forcing a return to classic. Release and 124 tests pass; [report and gallery](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase95e-management.md). Cab/chase views remain non-interactive spectator views.
- **9.5g Zoomed-out map performance - accepted by the user 2026-10-20 (baseline, ideas 3, 1+4 and 2 complete; parallel cold-chunk building deferred), before optional 9.5f:** profile normal through maximum zoom-out on identical large square/rectangular saves; measure end-to-end CPU/GPU frame costs, geometry, uploads, memory and cold pan/zoom; optimize measured bottlenecks with LOD off and full detail preserved. Verify terrain coverage, labels, picking, construction and normal-zoom performance. See the detailed gate in [phase9.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase9.md).
- **9.5f Expanded spectator/ride view — optional, last:** a larger/maximized cab/chase view with minimal furniture, easy vehicle/camera switching and clear restore/exit controls; preserve tunnel/lifecycle behaviour and measure performance.
- **9.6 Performance — done:** repeatable 512×512 fleet benchmarks cover several mixed cab/chase windows, enlarged windows and a separate grown-town long view; before/final timing and reference images recorded. Final Release and 123/123 tests pass. LOD stays off; renderer, draw distance and update rate remain unchanged. See the [9.6 report](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase9.md#96-performance) and [gallery](OpenTTD-15.3/OpenTTD-15.3/docs/3d/evidence/phase9/p6/gallery.html).

**Original gate (met):** cab and chase views follow trains, road vehicles, ships and aircraft through curves, slopes, bridges, tunnels and stations without snapping or self-clipping; every exit case returns to normal; the main view, picking, screenshots and other windows are unchanged; timings recorded with several views open.

**Follow-up priority:** 9.5a → 9.5b → 9.5c → 9.5d → 9.5e → 9.5g → optional 9.5f. The first three and spectator-last order are user priorities; visibility precedes rotated management as the working order for the middle pair. Each slice has its own gate in [phase9.md](OpenTTD-15.3/OpenTTD-15.3/docs/3d/phase9.md). Recheck relevant native interactions and performance as changes land; the original gate does not mark these additions complete.


## Phase 10 — Other climates
**Status:** Planned. The user moved the other climates' vehicles out of Phase 8 on 2026-10-17 because they are not a priority, and later the same day everything else specific to the other climates.

Phase 8 finishes the temperate climate. This phase covers the sub-arctic, sub-tropical and toyland content, using the same kits, family scripts, budgets and review loop as Phase 8. At the move these identities were left:
- **Vehicles:** 38 owner identities (11 arctic/tropic, 12 tropic-only, 15 toyland) of trains, road vehicles, ships and aircraft. Some are filed `shared_with` a temperate owner because their base sprites coincide (for example toyland `train_004`, and aircraft 33–37 and 40). Until they are re-owned and modelled, they show the temperate model.
- **Houses:** 63.
- **Industries:** 25.
- **Trees:** 37, the sub-arctic (with snowy variants), rainforest, cactus, sub-tropical and toyland species.
- **Ground:** the review of the snow and desert texture layers, which are still first-pass placeholders, and any toyland ground look.
- Shared identities that already exist in temperate (bridges, tunnels, stations, signals, catenary and so on) are done in Phase 8 and only checked here in their climate.
- Gate: every identity in the other climates is in game or intentionally shared with a reason and approved by the user; no Phase 5 fallbacks or magenta placeholders remain in any climate; textured ground works in every climate.


## Test strategy
Create a small reproducible save/map fixture and smoke-test: (1) flat and sloped terrain, (2) coastlines, (3) track curves/junctions, (4) moving train on a bridge, (5) tunnel entry/exit, (6) terrain edits, (7) station placement, (8) save/reload, (9) GUI overlays and tooltips, (10) switching between render modes. For every milestone run the existing project tests where available, plus targeted new tests. Record screenshots and frame timings.

## Suggested directory structure (adapt after audit)
```
docs/3d/architecture_audit.md
docs/3d/build_and_test.md
docs/3d/milestones.md
src/3d/                 # optional; only if consistent with actual build architecture
assets/3d/              # generated models and metadata, location subject to packaging audit
tools/3d_assets/        # Blender/Python generators
```

## Original Phase 0 assignment — historical reference (completed)
> Inspect this OpenTTD checkout and read `OPENTTD_3D_CODEX_GUIDE.md`. Execute **Phase 0 only**. Build and run the original game on this Windows machine following the checked-out `COMPILING.md`. Audit the rendering, viewport, GUI compositing, terrain data, vehicle positions, input/picking, and NewGRF paths. Produce `docs/3d/architecture_audit.md` and `docs/3d/build_and_test.md` with exact source references, a proposed minimal 3D integration point, and an ordered Phase 1 implementation plan. Do not implement the 3D renderer or generate assets yet. If dependencies or environment issues prevent building, document precisely what is missing and what command failed. Do not modify simulation logic. Report the build/test results and stop for review.

## Development cadence
At the end of each phase, Codex must deliver: changed files, technical decisions, working demo instructions, tests executed, performance observations, outstanding defects, and the next smallest task. Keep changes reviewable and commit each passing milestone separately.

## References
- Source: https://github.com/OpenTTD/OpenTTD
- Build: https://github.com/OpenTTD/OpenTTD/blob/master/COMPILING.md
- License: https://github.com/OpenTTD/OpenTTD/blob/master/COPYING.md
