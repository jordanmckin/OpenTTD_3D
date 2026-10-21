# 3D development milestones

Approved scope: custom OpenGL renderer inside OpenTTD; base-game content only; original simulation and 2D fallback preserved. Godot is optional for separate visual experiments, not a runtime dependency. No NewGRF compatibility work in this iteration. Retain base-set loading and the original 2D mod support.

## 0. Baseline and architecture
Record supplied source provenance; establish Git; build unchanged source; run tests and a small map with base graphics; document integration seams and limitations. No renderer implementation or asset generation. See architecture_audit.md and build_and_test.md for actual evidence and gate status.

## 1. GPU viewport and original windows
Status (2026-10-16): rendering proof implemented; Release build and 96 tests pass. Scripted captures verify depth, GUI overlap, secondary viewport, live pan/zoom, two resolutions/blitters, 200% UI scaling, mode switching, save/reload, unsupported-driver fallback and normal quit. Live mouse/resize/cursor/tooltip checks remain unverified because native UI automation is unavailable. See phase1.md for evidence and exact limits; no real terrain yet.

Build/runtime opt-in; depth-tested cube and flat colored patch; original GUI and cursor; resize and DPI; overlapping windows and a secondary viewport; context cleanup; 2D switch and fallback. Start with Windows OpenGL and explicitly reject unsupported drivers. Gate: a real session displays the test surface without covering windows or breaking input. Prove compositing before assets.

## 2. Terrain, camera, and early picking

Status (2026-10-16): implemented and small-map scripted gate verified. Real terrain/foundations/water, shared-corner chunk invalidation, culling, wireframe, tile highlights, height-aware picking and camera views work. Release build and 100 tests pass; scripted screen picks raise sea and hillside tiles through existing commands; edited height survives save/reload. Four-angle screenshots and exact evidence are in phase2.md. Live native mouse/resize/cursor checks remain the Phase 1 manual follow-up. Optional yaw/tilt inspection controls were brought forward for the requested multi-angle captures.
Match classic projection first. Read real tile corners and foundations; slopes, water, map edges; pan/zoom; tile highlights and height-aware picking; coordinate tests. Measure 16x16 versus 32x32 chunks; invalidate neighbors for shared corners. Gate: correct clicked tile and terrain edits on a small map, including slopes and coastline.

## 3. First playable railway
Status (2026-10-16): implemented; scripted cargo-route gate verified. Release build and 102 tests pass. Base railway geometry, live signals, stations/depot, industry placeholders, authoritative engine/wagon positions and original autorail previews render. A reproducible fixture builds/removes rail and delivers 90 coal; a separate reload continues delivery. Screen-coordinate build/remove, pause, normal/fast speed and 2D switching are exercised. See phase3.md and tools/phase3-demo.ps1. Native mouse/resize/DPI checks remain the explicitly carried Phase 1 manual follow-up.

Base rail, junctions, signals, depot, station platforms, simple industry placeholders; original construction commands and drag previews. Add a placeholder train and wagons using authoritative coordinates/consist state. Gate: construct and operate one cargo route, save/reload, pause, speed changes, and 2D switching. Accept angular turns; never alter movement rules for appearance.

## 4. Infrastructure coverage
Status (2026-10-16): implemented; scripted gate verified. Release build and 103 tests pass. Rail/road bridges and tunnels, inclined bridge-head foundations, slopes, crossings, road depots/stops and moving road vehicles render from authoritative state. The fixture builds/removes/rebuilds infrastructure, delivers 90 coal, and runs three trucks above/below bridges and through tunnels on both axes. All 3,072 live ramp/portal height checks pass; tunnel hiding, depot round trips, reload, speed controls and classic/3D switching are verified. The actual Release launcher passes its screenshot/exit smoke test. Run tools/phase4-demo.ps1; see [phase4.md](phase4.md) and the [gallery](evidence/phase4/gallery.html). Native mouse/resize/DPI checks remain the carried Phase 1 manual follow-up; art is placeholder and exhaustive content coverage is not claimed.

Bridges, tunnels, foundations, crossings, roads and road vehicles; verify hidden vehicles and deck heights. Ship and aircraft coverage follows. Gate: clear construction and movement across terrain and layered infrastructure, with unsupported cases documented.

## 5. Coherent base-game assets
Status (2026-10-16): scripted gate complete. A deterministic Python generator exports 26 original low-poly models, JSON, compiled triangle tables, a contact sheet and license manifest. All 110 base-house IDs are enumerated, with explicit category substitutes and missing markers. Live town/mine/power/vehicle assets, growth/construction snapshots, coal loading, classic switching and a separate reload pass. Release build and 104/104 tests pass; the fixture has zero missing map assets. See [phase5.md](phase5.md), [asset specification](asset_spec.md), and [gallery](evidence/phase5/gallery.html). Run tools/phase5-demo.ps1. Full base-content and native-input coverage remain follow-up.

Only after working map/route: procedural buildings, industries, trees, vehicle variants; asset units/origins/material conventions and provenance manifest; deterministic generator scripts. Gate: one coherent town and industry chain. Use obvious placeholders for unfinished base models; no claim of complete base coverage until enumerated and tested.

## 6. Usability and base-content coverage
Status (2026-10-16): implementation and scripted checks complete; native interaction acceptance pending. Fixed-camera ground picking, existing transparency controls, basic air/water presentation, four-climate height/picking audits, air/water AI save/reload and same-binary localhost synchronization are verified. Release build and 104/104 tests pass. See [phase6.md](phase6.md) for the explicit coverage matrix and [manual checklist](phase6-manual-tests.md). The user accepted a native-test handoff; no mouse/resize/DPI pass is claimed.

Improve occlusion, tooltip/click fidelity, secondary views, climates and transport types. Test AI and multiplayer determinism separately from network version-handshake compatibility. Expand fixture suite. Gate: reliable ordinary management and construction with an explicit coverage matrix.

## 7. Performance and packaging

Latest (2026-10-19): retained static instance streams and variable model slots are implemented; final Release and **118/118 tests pass**. Broad visual checks passed before the final duplicate-write cleanup. Preliminary four-window fleet drawing improves **7.08 to 5.58 ms**, with instance uploads **1649 to 130 KiB/pass**. Final post-cleanup visual/timing reruns were stopped at the user's request to finish the session. See [phase7-streams.md](phase7-streams.md) for verified evidence and exact resume commands. General release acceptance remains open.

Status: priorities 1–2 of the current roadmap are implemented and verified. Dirty-tile snapshots are followed by deferred offscreen mesh rebuilding, coalesced changes and bounded CPU/GPU retention. Release build, **110 tests**, six live correctness scenarios and 16 benchmark cases pass. At 1024 square, mean drawing falls 40.41 to 9.32 ms and sampled working set 1057.8 to 289.1 MiB in the diagnostic pair. Small-map/window results are mixed; cold pan/zoom costs are recorded. See [phase7-offscreen.md](phase7-offscreen.md), [dirty-tile checkpoint](phase7-dirty-tiles.md), [remaining roadmap](phase7-tiles.md) and [release-readiness.md](release-readiness.md). General release, native interaction and final art remain separate gates.

User feedback (2026-10-16): 3D performance is poor overall and worsens with multiple vehicle windows open. Explicitly deferred by the user to Phase 7. Reproduce and measure zero/one/several vehicle windows on the same running map before optimizing viewport caching, repeated scans, redraws and GPU readback.

Measure CPU/GPU time, allocations, rebuilds, and memory on 128x128 and 512x512 maps before larger cases; add batching, instancing and LOD where needed. Packaging and licensing inventory; reproducible builds. Camera rotation, tilt, lighting polish, and any NewGRF work remain separately scoped follow-ups.

Completed priorities from the earlier user request (2026-10-16):

1. Replace whole-map polling with dirty-chunk tracking; preserve shared-corner/reload correctness and retain the full-scan reference.
2. Keep static chunk meshes on the GPU, apply camera transforms in shaders, and upload only changed chunks; handle moving vehicles separately.

Both are implemented and verified; evidence and measured limitations are recorded in [phase7-retained.md](phase7-retained.md).

The subsequent CPU tile-geometry follow-up is recorded in [phase7-tiles.md](phase7-tiles.md). It distinguishes the earlier GPU retention priority from reusing unchanged CPU tile geometry within a dirty chunk. The latest [dirty-tile checkpoint](phase7-dirty-tiles.md) refreshes only affected authoritative snapshots, preserving the independent full-map and full-mesh references.

Performance follow-ups (recorded 2026-10-16): priorities 1–2 complete; priorities 3–5 planned, in order:

1. **Complete:** track dirty tiles within chunks to avoid reading unchanged authoritative snapshots. See [phase7-dirty-tiles.md](phase7-dirty-tiles.md).
2. **Complete:** defer offscreen mesh rebuilding and bound CPU/GPU mesh retention. See [phase7-offscreen.md](phase7-offscreen.md).
3. Patch changed geometry ranges in CPU meshes and GPU buffers.
4. Reduce GPU readback and compositing costs, particularly with multiple vehicle windows.
5. Invalidate smaller screen regions for localized world changes.

Second performance pass (recorded 2026-10-18, before closing Phase 8): priorities 6–12 are tracked in [phase7.md](phase7.md#second-performance-pass-recorded-2026-10-18). They are: re-baseline with the Phase 8 art and an end-to-end frame-time measurement; limit vehicle and effect invalidation to the views that see the change; remove the synchronous readback; instanced draws; vehicle/model LOD; static art drawn as instances; and animated-tile churn. Priority 6 (re-baseline), priority 8 ([3D drawn beneath the UI without readback](phase7-direct.md)) and priority 12 ([tile changes rewrite only that tile's geometry](phase7-p12.md)) are done, as are priority 7 ([scoped invalidation](phase7-p7.md)) and priority 9 ([instanced model draws](phase7-p9.md)); priority 10 is evaluated as an opt-in candidate; full detail remains the default after a measured four-window regression ([LOD report](phase7-p10.md)); priority 11 is implemented as a measured memory optimisation ([static library sharing](phase7-p11.md)).

See [the detailed roadmap](phase7-tiles.md#next-performance-priorities-recorded-2026-10-16) for correctness requirements, profiling targets and validation. Keep simulation behavior unchanged and record each passing implementation checkpoint separately.

## 8. Hand-modelled base-game art
Status (2026-10-16): replanned at the user's request; see [phase8.md](phase8.md). Phase 5 art remains the fallback until each identity is replaced. Phase 7 continues independently.

Every base-game identity (about 450–500 models) gets its own low-poly Blender model, built through the user's Blender MCP by Claude or Codex and approved by the user, using the original game sprite as reference; no third-party asset packs. Three build approaches: `bespoke` individual models for houses, industries, landmarks and stations; a shared Blender parts `kit` for vehicles; parametric `family` scripts for trees, fences, signals, bridge spans and props. Houses are whole models drawn from the north tile; industries are modelled whole and cut into per-tile pieces. Steps: (1) map identities to the user's grfcodec export of OpenGFX sprites (`sprites_pulled/`, sliced by `tools/3d_assets/slice_sprites.py`) through the game tables, composite one reference per identity per climate, and write `assets/3d/inventory.json` as the tracking sheet, including all 41 tree species, map objects, field fences/hedges, water objects, signals, crossings and catenary; (2) a Blender → glTF → build-time converter pipeline with shared conventions, palette, company-colour materials, and named states, so an approved `.blend` appears in game with no runtime parser; (3) textured ground from a texture array (lighting unchanged), using grass/snow/desert density, rough, rocky, field type and shore state, with measured cost; (4) a pilot set from the current temperate town is modelled and approved on the final ground as the style reference; (5) the remaining identities are modelled category by category; (6) states, company colours and presentation-only animations; (7) Phase 7 performance/packaging and Phase 4–6 fixtures are re-run.

Scope (2026-10-17): Phase 8 finishes the temperate climate. At the user's request, everything specific to the sub-arctic, sub-tropical and toyland climates (vehicles, houses, industries, trees and the snow and desert ground textures) is Phase 10 in `OPENTTD_3D_CODEX_GUIDE.md`.

Gate: every inventory identity used in the temperate climate, including landscape objects and ground textures, is in game or intentionally shared with a reason, with no Phase 5 fallbacks or magenta placeholders in temperate. Textured ground works in every viewport. The user has approved the models; footprints, picking, occlusion, simulation behavior and measured performance are preserved. NewGRF models remain separate scope.

## 9. First-person and chase views
Status (2026-10-20): original 9.1 through 9.6 complete: per-viewport perspective cameras, smoothed chase and cab views, button/hotkey controls, tunnel fades, lifecycle exits and the measured multi-view performance gate. Final Release and **123/123 tests pass**. **9.5a toolbar access was approved by the user on 2026-10-19. 9.5b labels were approved by the user on 2026-10-19; scripted verification passes. 9.5c shadows were approved by the user on 2026-10-19 (contact shadows default, sun shadows optional).** **9.5d was approved by the user on 2026-10-20; scripted verification passes.** **9.5e is implemented and scripted verification passes; user review is pending.** **9.5g zoomed-out performance was accepted by the user on 2026-10-20 after the local test-release handoff.** Parallel cold-chunk building is deferred unless needed; 9.5f spectator expansion remains optional. LOD stays off by explicit user instruction. See [phase9.md](phase9.md) for completed evidence and each follow-up gate.

The vehicle window's viewport switches between normal, cab and chase views with a button and hotkey. The main view and the rest of the UI are unaffected, and there is no picking in these views. Slices: (9.1) per-viewport camera override; (9.2) perspective projection, culling and fog; (9.3) chase view with smoothing, plus the button and hotkey; (9.4) cab view; (9.5) exits and edge cases, including the tunnel fade-to-black and snap back on sold, crashed or depot; (9.6) performance with several views.

Original gate (met): cab and chase views follow every base vehicle type through curves, slopes, bridges, tunnels and stations without snapping or self-clipping; every exit case returns to normal; other views, picking and screenshots are unchanged; timings recorded.

Follow-ups under 9.5, in execution order:

| Slice | Feature | Priority |
|---|---|---|
| 9.5a | Main-toolbar 3D button/dropdown: Enable 3D, saved client preferences, camera controls/help, normal access without the console | Approved by user 2026-10-19 |
| 9.5b | Station names first, then town names, signs and floating text effects, with readable projected labels and aligned click targets | Approved by user 2026-10-19 |
| 9.5c | Lighting/grounding experiment: compare contact/simple shadows, measure cost and decide whether to adopt | Approved by user 2026-10-19: contact shadows default, sun shadows optional; [report](phase95c-shadows.md) |
| 9.5d | Automatic obstruction fading and selection outlines, integrated with manual transparency | [Approved by user 2026-10-20](phase95d-visibility.md) |
| 9.5e | Accurate management and construction from rotated orthographic views | [Implemented and verified; user review pending](phase95e-management.md) |
| 9.5g | Profile and improve zoomed-out map FPS on large square/rectangular maps, preserving full detail, picking and terrain coverage | [Accepted by user 2026-10-20](phase95g-zoomout.md): merged terrain draws, budgets, vertex packing and partial redraw complete; parallel cold-chunk building deferred |
| 9.5f | Expanded/maximized spectator ride view, vehicle/camera switching and clear exit/restore | Optional, last |

The first three priorities and spectator-last placement are explicit user choices; visibility precedes rotated management as the working order for the middle pair. 9.5a has [implementation and verification evidence](phase95a-toolbar.md); user approval is recorded and the remaining additions have their own gates, with per-slice acceptance gates in [phase9.md](phase9.md). Keep LOD off, preserve original commands/simulation, and re-run relevant interaction and performance checks as the slices land.

Every phase records changed files, commands/results, demo steps, defects, measured performance (or explicitly no measurements), and next smallest task. Commit passing milestones separately; do not label a blocked gate complete.
