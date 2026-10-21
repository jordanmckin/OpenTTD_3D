# Phase 2: real terrain, camera and picking

Status (2026-10-16): Phase 2 implemented and its small-map scripted gate verified. Release build and 100 tests pass; terrain edits, saved height, picking, camera views, culling and wireframe are verified. The previously documented live Windows mouse/resize/cursor checks remain manual follow-up items.

## Implementation

The optional OpenGL viewport now reads the actual map. Each tile has four triangular sectors, preserving both possible diagonal ridges, saddles and steep slopes. Foundation surfaces come from OpenTTD's existing foundation query, including half-tile platforms and vertical skirts. Water, sloping coastlines and exposed map edges are coloured separately. Directional lighting and restrained tile colour variation make elevation visible. No generated assets or Godot runtime are involved.

The default camera uses the original affine projection and zoom. `renderer_3d camera <yaw degrees> <tilt 40..180>` provides additional inspection angles; `camera 0 100` restores the classic orientation. Rotation/tilt are presentation-only, shared by viewports. Each viewport retains its independent position and zoom. The classic pixel-scroll optimisation is disabled in 3D because its displacement does not describe a rotated camera. Picking uses the same aligned camera and triangles as drawing, resolves depth, and returns world coordinates through `TranslateXYToTileCoord`, the existing construction input path.

Chunk bounds are conservatively projected against the orthographic viewport; fully off-screen chunks are omitted before vertex upload. The GPU clips intersecting triangles. `renderer_3d wireframe on|off` exposes the actual triangle mesh; polygon rasterisation state is restored before the original GUI is drawn.

Original rectangular tile selections tint the selected terrain yellow (red for rejected selections). A diagnostic `highlight x y` can select a known tile for capture. Town labels and floating text are suppressed in terrain mode until their placement can follow the camera. Construction commands, simulation, save fields and networking remain the existing OpenTTD implementations. Buildings, trees, tracks, roads and vehicles are not drawn in this phase; use `renderer_3d off` to see them.

CPU chunk meshes compare authoritative tile type, ground slope, foundation slope and heights. Corner changes therefore invalidate the tiles on both sides of a chunk boundary. A revision invalidates cached viewport images and requests repaint, including for rotated views. This correctness-first small-map implementation scans tile snapshots on redraw/pick; it is not a large-map performance claim. The existing synchronous GPU readback remains.

## Controls and diagnostic commands

Run `tools/phase2-demo.ps1` from the workspace root. Optional PowerShell parameters: `-Yaw 90 -Tilt 65`. This uses an isolated profile and the checked-in 64x64 coastal fixture, starts paused, and does not compile. Unpause for construction.

```text
renderer_3d on
renderer_3d camera 0 100
renderer_3d camera 90 65
renderer_3d camera 180 100
renderer_3d camera 270 145
renderer_3d viewport
renderer_3d wireframe on
renderer_3d wireframe off
renderer_3d off
```

Testing commands (only in a build with `OPTION_3D_PROOF`):

- `renderer_3d check`: compare slope meshes with engine height queries; compare interior classic-view picks with the original height-aware inverse; check map-edge ownership; measure 16/32 chunk rebuilds and unchanged scans. No map edits.
- `renderer_3d chunks 16` / `32`: choose CPU chunk size and rebuild.
- `renderer_3d pick <screen x> <screen y>`: use the main viewport's real input translation and highlight its result.
- `renderer_3d clickraise <screen x> <screen y>`: pick through that input path, then post the ordinary raise-land command. **Edits the current game.**
- `renderer_3d raise <tile x> <tile y>` / `lower`: post ordinary terraform commands at a known tile. **Edits the current game.**
- `renderer_3d highlight <tile x> <tile y>`: highlight only.
- `renderer_3d inspect <tile x> <tile y>`: log authoritative north-corner height and slope without edits.

Map-edge side-wall picking intentionally differs from the old inverse: the visible wall belongs to its last valid terrain tile, whereas the classic inverse can return void/off-map coordinates behind it.

## Build and validation

Use the Phase 0 dependency setup and Phase 1 opt-in build configuration. Continue limiting builds to one project and two compiler workers:

```powershell
& $cmake --build build/baseline --config Release --parallel 1 -- /p:CL_MPCount=2 /p:MultiProcMaxCount=2 /nodeReuse:false
& $ctest --test-dir build/baseline -C Release --output-on-failure
```

The local demo executable `build/baseline/openttd-3d.exe` is a console-subsystem copy of the built Release executable, produced using MSVC `editbin /subsystem:console`, as in earlier scripted runs. Runtime dependency DLLs remain next to it. The source renderer is identical.

New unit tests cover classic projection, sloped triangle picking across rotations/tilts/zooms, rejected outside/degenerate hits, and conservative chunk culling (intersection, height and rotation). Runtime geometry diagnostics additionally cover 5,120 samples across basic/steep/saddle slopes and half-platform corner variants.

## Limits carried forward

Native Windows automation is unavailable. Scripted screen-coordinate picks exercise construction translation but do not prove physical mouse injection, tooltips, cursor appearance, live OS resizing or DPI transitions. Those Phase 1 manual checks remain open. Alternate camera orientations are inspection controls; scroll targeting and navigation still use the original world navigation conventions. Rail/road drag previews and rotated labels belong to later infrastructure work.

The source is still uncommitted after the initial import because this session cannot write the protected Git index. No attempt is made to bypass that restriction.

## Verified results

- Release build succeeds with the two-worker limit. All **100 CTest tests pass**, including four new camera/picking/culling cases and the existing savegame regressions.
- Runtime geometry checks: **5,120 height samples, zero failures**. The coastal-map pick comparison passes **219 interior samples**, including **89 on slopes, 105 on water and two on foundations**, with **eight valid map-edge hits**. After hillside terraforming: 218 interior samples, zero failures.
- Screen `(640,450)` selects tile `(32,32)`. The ordinary terraform command raises its north corner **0 to 1**, then a known-tile command raises it **1 to 2**. A third command is rejected by the game's normal rules (the company has only about £8,686 left); the height remains 2. The renderer rebuilds **four 16x16 chunks** across that shared corner. Screen `(200,350)` selects hillside tile `(42,14)` and raises it **9 to 10**.
- The saved coastal edit loads in a separate process using the null video driver. `inspect 32 32` reports **height 2, slope 29**, matching the saved state. Exit status is zero. Rendering is not needed to load the edited save.
- The 32bpp and 40bpp OpenGL paths render terrain. Captures verify yellow highlights, the original toolbar/status windows, an additional viewport, live scripted pan/zoom, four camera angles, classic-mode fallback, and wireframe with the original GUI still filled. Normal quits are recorded by the test runs.
- Frustum diagnostics on the rotated close view submit **14 of 16 chunks**. Culling tests cover fully outside bounds, intersection, raised terrain and rotation.
- Screenshots are direct app captures. Exported PNGs are checked pixel-for-pixel against the source BMPs. [Open the four-angle gallery](evidence/phase2/gallery.html).

### Small-map measurements

On the 64x64 coastal fixture before editing (the terrain/edit run, before adding chunk-bound culling), 16x16 chunks rebuilt in **1,763 µs**, versus **1,643 µs** for 32x32; unchanged scans were **113 µs** and **101 µs**, respectively. Keep 16x16 as the default: the slight full-map rebuild advantage for 32x32 does not outweigh rebuilding larger regions for local edits. These are CPU snapshot/mesh times, not GPU timings. The final review log repeats this benchmark with culling bounds included.

The viewport log measures CPU projection/upload/render/readback together on cache misses. Typical 1280x900 captures during the test were around **3–10 ms**, with occasional larger stalls, including approximately **150 ms** while multiple test instances ran. Cached frames do not rebuild/read back terrain. The wireframe capture's original FPS window reports **60.01 graphics frames/s** and **37.07 simulation frames/s**. This is a small mostly static map, not a dense railway or large-map benchmark; it does not establish a general frame-rate guarantee.

In the final culling/wireframe build, 16x16 rebuild/scan measured **1,877/112 µs**, versus **1,716/101 µs** for 32x32. Its repeated geometry check passed 5,120 heights and 221 interior picks (89 slope, 111 water, three foundation samples), plus seven map-edge hits. The console frame sampler reported drawing **0.13/0.13/0.14 ms** and video output **0.22/0.23/0.24 ms** over its 64/128/512-sample windows, with **59.93 graphics frames/s**. These averages are dominated by cached terrain frames. The final session exited normally with status zero.

### Evidence index

- [Build log](evidence/phase2/build.log), [100-test run](evidence/phase2/tests.log).
- [Terrain edits and picking](evidence/phase2/terrain-edit.log), [save/reload height](evidence/phase2/reload.log).
- [Final culling/wireframe run](evidence/phase2/review.log), [console frame timings](evidence/phase2/review-console.log).
- [Raised tile](evidence/phase2/phase2-raised.png), [secondary viewport](evidence/phase2/phase2-secondary.png), [pan/zoom](evidence/phase2/phase2-pan-zoom.png), [classic fallback](evidence/phase2/phase2-classic-fallback.png), [wireframe](evidence/phase2/phase2-wireframe.png), [final filled view](evidence/phase2/phase2-final-filled.png).
- Reproduction config, base and edited saves, and the capture scripts are in `fixtures/phase2/`. OpenGFX remains an external base-data requirement; it is not bundled into these fixtures.

### Changed files and next step

`video/terrain3d_math.h` and `terrain3d_impl.h` provide the camera, terrain snapshots, geometry, picking and diagnostics. `proof3d_impl.h` integrates them with the existing framebuffer pass. `proof3d.h`, `opengl.cpp`, `viewport.cpp`, and `console_cmds.cpp` provide lifecycle, input, redraw and controls. Video/test CMake lists register the files; `tests/terrain3d.cpp` adds targeted coverage. `tools/phase2-demo.ps1`, the fixtures, screenshots and this report make the milestone reviewable. The launcher's PowerShell syntax parses without errors; the underlying executable, profile and launch arguments are exercised by scripted runs.

The next smallest task is Phase 3: render base rail on the real terrain, use the existing construction commands and drag previews, then add a station/depot and an authoritative-position placeholder train. Do not begin bulk asset work before that miniature route operates.
