# Phase 9: first-person and chase views

Status (2026-10-20): original slices 9.1 through 9.6 complete, including the measured performance gate. **9.5a toolbar access was approved by the user on 2026-10-19. 9.5b labels were approved by the user on 2026-10-19; scripted verification passes. 9.5c shadows were approved by the user on 2026-10-19 (contact shadows default, sun shadows optional).** **9.5d was approved by the user on 2026-10-20; scripted checks pass.** **9.5e is implemented and scripted verification passes; user review is pending.** **9.5g zoomed-out performance was accepted by the user on 2026-10-20 after the local test-release handoff.** Parallel cold-chunk building is deferred unless needed; 9.5f spectator expansion remains optional. LOD stays off by explicit user instruction. Presentation and client settings only; simulation rules, game commands, save formats and networking remain unchanged.

**New-map startup correction (2026-10-20):** reproduced missing terrain on a generated 2048x512 map; the renderer now waits for generation to finish and rebuilds its snapshots at completion. Release and 124 tests pass; new-map reset/full-snapshot references pass on large rectangular maps and both blitters. See [report and reproduction](newmap-startup-fix.md). Zoomed-out performance was subsequently implemented and accepted in 9.5g.

## Direction

The vehicle window's own viewport (`WID_VV_VIEWPORT` in `src/vehicle_gui.cpp`) can switch from the normal view to a **cab view** (at the front of the vehicle, looking forward) or a **chase view** (behind and above it). The main view, the toolbar and every other window are unaffected. Dragging the vehicle window bigger gives a bigger first-person view, and several vehicle windows can each ride along with a different vehicle at the same time.

Agreed with the user (2026-10-19):

- **Scope:** only the vehicle window's viewport changes. The rest of the UI keeps working normally.
- **No picking** inside a cab or chase viewport. Clicks in it do nothing beyond the normal window focus. Picking, construction and labels stay on the classic camera, as they do now (see [camera-orbit.md](camera-orbit.md)).
- **Toggle:** a new small button in the vehicle window cycles normal → cab → chase → normal, plus a hotkey next to the existing `honk` one in the `vehicleview` list (`src/vehicle_gui.cpp`), rebindable in `hotkeys.cfg`. Since 9.4 the button and the `camera` hotkey (`V`) cycle normal → cab → chase → normal.
- **Snap back:** returning to normal is instant. A small window doesn't need a fly-out animation.
- **Tunnels:** fade to black while the vehicle is underground, then fade back in.

## What already exists

- **Per-viewport 3D rendering.** Every window viewport gets its own 3D camera and image, built from that viewport's size, scroll position and zoom (`proof3d_impl.h:535`, `:614`, `ProofViewKey` at `:1278`, layer ids at `:1381`). Phase 7 measured and optimised four vehicle windows open at once.
- **Following.** The vehicle window's viewport already follows its vehicle (`follow_vehicle`). Its size comes from `VV_INITIAL_VIEWPORT_WIDTH/HEIGHT` and grows with the window.
- **Vehicle state.** `x_pos`, `y_pos`, `z_pos`, `direction` and the consist chain give the position and heading. Hidden or underground state (`VS_HIDDEN`, tunnel tiles) drives the fade.
- **LOD.** The existing Phase 7 diagnostic remains off by default. Perspective LOD is outside the accepted 9.6 scope, at the user's request.

## What has to change

- **The camera is global.** `TerrainCamera()` (`terrain3d_impl.h:103`) takes yaw, tilt and pivot from the shared `_terrain_yaw`/`_terrain_tilt`/`_terrain_pivot_z`. A viewport needs its own optional camera mode: none, cab or chase, plus a vehicle ID.
- **The camera is orthographic.** `Terrain3D::Camera` (`terrain3d_math.h`) is a scaled orthographic projection, and the shaders take it as the `cameraA/B/C` uniforms. First person needs a perspective camera with eye position, look direction, field of view and near/far planes, for both the chunk program and the instance program.
- **Culling.** `Terrain3D::Visible` is an orthographic screen-bounds test. Perspective needs a frustum test with a distance limit.
- **The image cache.** `ProofViewKey` identifies a view by viewport size, scroll and zoom. A cab or chase view moves every frame, so the key must include the camera mode, or the cache is skipped for these views.
- **Exits.** The view returns to normal by itself when the vehicle is sold or crashes, enters a depot or hangar, or when the window closes.

## Slices

### 9.1 Per-viewport camera override
Add an optional per-viewport camera mode (none / cab / chase + vehicle ID), stored outside the simulation. When it is unset, `TerrainCamera()` behaves exactly as today. Extend `ProofViewKey` (or bypass the cache) for overridden views. Picking returns nothing in overridden viewports. A temporary console command (`renderer_3d cab <vehicle>`) drives it before the button exists.

Gate: an overridden viewport can show a different orthographic angle from the main view, independently of it, with no change to the main view, other windows, picking or screenshots. The existing camera tests still pass.

**Done (2026-10-19).**

- `Viewport` gains `camera_3d` (`ViewportCamera3D::Normal/Cab/Chase`) and `camera_vehicle` (`viewport_type.h`). They are presentation only and go away with the window.
- `TerrainCamera()` takes the view's angle explicitly (`TerrainAngle`: yaw, tilt, pivot height). `SharedTerrainAngle()` is the orbit camera used by every normal view; `ViewTerrainAngle(vp)` returns a view's own camera; `ViewportTerrainCamera(vp)` builds a live viewport's camera (`terrain3d_impl.h`).
- The image key grows from 8 to 11 ints: the yaw, tilt and pivot floats are stored bit for bit, so normal views render exactly as before, and views with their own cameras never share images. Scoped invalidation, mesh trimming, rendering and the GPU references rebuild the camera from the key (`KeyTerrainCamera`) or from the live viewport.
- **Stand-in camera:** until 9.2 adds perspective, cab and chase are orthographic about the vehicle, turned so it heads up the screen (`Terrain3D::HeadingYaw`, a unit test checks all 8 directions). Tilt is 45 for cab and 70 for chase, and the pivot is at the vehicle's height.
- **No picking:** `PickTerrain3D` returns nothing, so there is no hover highlight or tool target, and `HandleViewportClicked` ignores clicks in these views while 3D is on. In classic 2D the setting is ignored and kept.
- The view's second 2D banner line reads "Cab view" or "Chase view".
- Console: `renderer_3d view <vehicle id|all> normal|cab|chase` opens the vehicle window if needed. It logs `PHASE9 VIEW` with the viewport rectangle and a pick at its centre.
- Console (test scripts): `renderer_3d queued <command>`. Console screenshots are queued to the main thread and taken after the whole script step, so this runs a `renderer_3d` command after the screenshots already requested. That lets one step capture several states in the same game tick.

**Verification:** Release build and **119/119 tests** pass. Run `.\tools\phase9-checks.ps1`, which uses the Phase 4 railway save, four vehicle windows and GPU references ([results](evidence/phase9/p1/check-results.json), [screenshots](evidence/phase9/p1/chase-cab.png)). Same-tick comparisons; the screenshot message box is masked:

| Check | Result |
|---|---|
| Normal → chase → cab → normal, whole screen | 0 differing pixels |
| Chase / cab, outside the vehicle viewports | 0 differing pixels |
| Chase vs normal, inside | 76% differ |
| Cab vs chase, inside | 61% differ |
| Shared camera turned to 90/60: cab views / main view | 0% / 70% differ |
| Centre pick in cab/chase views (20 logged) | none; normal views pick a tile |
| GPU references while cab/chase follow moving vehicles | 541, max 0.03% differing |
| Kept images through scoped invalidation | 411, 0 differing |

Notes:
- The ctest regression replays launch a copied executable by relative name; in this shell CMake could not find it until `build/baseline` was put on `PATH`. This is an environment issue, unrelated to the change.
- The "3D TRANSPORT" banner covers the centre of small vehicle windows, where the vehicle is. Move or drop it for cab and chase views in 9.3.

### 9.2 Perspective projection and culling
Add a perspective camera path: view-projection uniforms in both shader programs, a frustum and distance cull for chunks and instances, a depth range that suits ground level, and distance fog matching the existing palette to hide the draw limit. Orthographic views keep their current code path.

Gate: a fixed perspective camera placed by console command renders terrain, track, buildings, trees and vehicles correctly with no gaps at the cull distance. Frame time is measured with one and four perspective windows on the Phase 7 benchmark map.

**Done (2026-10-19).**

- `Terrain3D::Camera` gains an optional perspective part: a column-major view-projection matrix, the eye and a draw distance (`terrain3d_math.h`). `PerspectiveCamera()` builds it from an eye, a heading (degrees clockwise from north, the same convention as `HeadingYaw`), a pitch and a vertical field of view, with the near plane at one unit. `Project()` and `Visible()` branch on it; orthographic cameras take exactly the old code path.
- **Culling:** `Visible()` tests a box against the six frustum planes taken from the matrix. The far plane is the draw distance (64 tiles, `TERRAIN_DRAW_DISTANCE`), so the same test culls by distance for chunks, retained static streams, vehicles, effects, mesh preparation, trimming and scoped invalidation.
- **Shaders:** both programs take `viewProjection`, `eye` (xyz, w = draw distance; 0 keeps the orthographic projection) and `fog` (colour, w = start distance). Perspective vertices fade to the fog colour from 60% of the draw distance to 98% of it, and perspective images are cleared to the fog colour, so the far plane never shows an edge. CPU reference vertices of a perspective view stay in world space and the shader projects them.
- **Fixed camera:** `ViewportCamera3D::Fixed` with `Viewport::camera_eye` (x, y, z, heading, pitch, field of view). The image key grows from 11 to 17 ints with the eye, heading, pitch and field of view bits; a perspective key ignores the scroll position, so the window following its vehicle alone does not re-render it.
- Library LOD is off in perspective views until distance LOD in 9.6, because its bounds assume an orthographic scale.
- Cab and chase keep their 9.1 orthographic stand-ins until 9.3 and 9.4 place perspective cameras on the vehicle.
- Console: `renderer_3d eye <vehicle id|all> <+x tiles> <+y tiles> <height> <heading|ahead> <pitch> [field of view]` places a still camera relative to where each vehicle is now (height above the ground; `ahead` uses the vehicle's heading). `renderer_3d windowsize <vehicle id|all> <width> <height>` resizes vehicle windows as if dragged, for test scripts. The view banner reads "Fixed view".
- The PHASE7 GPU, kept and instance reference log lines end with `perspective=true|false`.

**Verification:** Release build and **120/120 tests** pass (new unit test: heading, screen right and up, depth order, and culling behind the eye and past the draw distance, for all 8 directions). `.\tools\phase9-perspective.ps1` runs on the Phase 4 railway save and `.\tools\phase9-perspective.ps1 -Fleet` on the 512×512 Phase 7 fleet map ([results](evidence/phase9/p2/check-results.json), [views](evidence/phase9/p2/perspective-views.png), [four windows](evidence/phase9/p2/four-windows.png), [log](evidence/phase9/p2/views.log)). `.\tools\phase9-checks.ps1` (9.1) still passes.

| Check | Result |
|---|---|
| Four fixed windows, same tick: outside the windows / inside | 0 differing pixels / 90% differ |
| Back to normal, whole screen | 0 differing pixels |
| Centre pick in fixed views | none |
| GPU references, perspective views (railway / fleet map) | 81, 0 differing / 38, max 1 pixel in 940k |
| Kept-image and instance references, perspective views | 0 differing |
| Ground below the horizon showing sky (holes), 6 near views | none |
| Fog: mean colour distance from the fog near the horizon vs. near the eye (fleet, from 400 up) | 73 vs 293 |
| Main view vs. the 9.1 build, same script | identical apart from moving vehicles and the date |

The GPU reference regenerates the whole scene without culling, so matching it shows the frustum and distance cull leave no gaps. Terrain, track, roads, tunnels, stations, buildings, trees and vehicles all render in the captures; the low eye in the railway set sits inside its own truck, which 9.4 deals with.

**Frame time** ([benchmark](evidence/phase9/p2/benchmark.json)): `tools/phase7-benchmark.ps1 -MapBits 9 -Fleet -Windows 1,4 -Modes optimized`, with and without `-Camera "eye all 0 0 32 ahead -4"`, 1280×900, uncapped:

| Vehicle windows | CPU per render | GPU per render | Model triangles | Resident chunks / mesh MiB | Mean / p99 frame |
|---|---|---|---|---|---|
| 1 orthographic | 0.57 ms | 0.14 ms | 77k | 21 / 11.5 | 1.00 / 3.9 ms |
| 1 perspective | 0.61 ms | 0.47 ms | 175k | 51 / 28.2 | 1.00 / 4.3 ms |
| 4 orthographic | 1.32 ms | 0.31 ms | 116k | 23 / 11.8 | 1.15 / 5.7 ms |
| 4 perspective | 1.30 ms | 0.79 ms | 380k | 96 / 56.1 | 1.10 / 6.4 ms |

A perspective window sees up to 64 tiles away instead of the few tiles under an orthographic one, so GPU time, triangles and resident meshes grow, while CPU time per render stays the same. Frame rate is unchanged at this size. 9.6 revisits LOD and the draw distance with large windows and dense towns.

Notes:
- The fixed camera is a test tool for this slice. The player-facing chase and cab cameras come in 9.3 and 9.4.
- The "3D TRANSPORT" banner still covers the top of the view; 9.3 moves or drops it for these views.

### 9.3 Chase view
Place the camera behind and above the lead vehicle, looking ahead along its heading. Smooth the position and turn the heading gradually between game ticks, because vehicles move in steps along each tile and face one of only 8 directions. Smoothing affects presentation only. Add the vehicle-window button and hotkey (normal → cab → chase cycle; cab can map to chase until 9.4 lands).

Gate: chase view follows a train, a truck, a ship and an aircraft through curves, slopes, bridges and stations without visible snapping. The button and hotkey work, and save/reload and pause behave normally.

**Done (2026-10-19).**

- **Camera:** a perspective camera `CHASE_BACK` (56, 3.5 tiles) behind and `CHASE_UP` (24) above the followed vehicle, looking at a point one tile ahead of it, with a 60° field of view (`Terrain3D::ChaseEye`, `terrain3d_math.h`). It stays at least 8 above the ground under it, so hills behind the vehicle don't swallow it. Chase views reuse the 9.2 perspective path: the eye is stored in `Viewport::camera_eye` like a fixed camera.
- **Smoothing** (`Terrain3D::FollowChase`), presentation only and updated once per frame from `UpdateViewportPosition` with the frame time:
  - Position eases over 0.12 s and trails by at most 24 units, so fast vehicles stay in view.
  - Heading turns the short way, easing over 0.8 s or one and a half tiles travelled, whichever is shorter, and at most 240° a second.
  - A vehicle moving further than 8 units per elapsed game tick has jumped, as when a train reverses and its lead vehicle moves to the other end. The camera eases the jump out over 0.3 s instead of moving with it. A jump of more than 16 tiles starts again at the vehicle.
  - Values settle exactly, so a view whose vehicle has stopped stops redrawing. The state lives in `Viewport::camera_follow` and goes away with the window.
- **Button and hotkey:** a camera button in the vehicle window's button column (`WID_VV_CAMERA`) and the `camera` hotkey in the `vehicleview` list (default `V`, rebindable in `hotkeys.cfg`) switch the view between normal and chase. The button shows pressed while the view has its own camera, and is disabled in classic 2D. Cab stays out of the cycle until 9.4 makes it a real view; `renderer_3d view <id> cab` still shows the orthographic stand-in.
- **Banner:** cab, chase and fixed views drop the "3D TRANSPORT" banner and show only a small label ("Chase view") in their bottom-left corner. The main view keeps the banner.
- Console (test scripts):
  - `renderer_3d view` also takes `train|road|ship|aircraft`, meaning the first vehicle of that type.
  - `renderer_3d press <id|all> button|hotkey` clicks the camera button, or sends its key through the normal key dispatch.
  - `renderer_3d views` logs every vehicle window's camera.
  - `renderer_3d chaselog on|off` logs every chase update (`PHASE9 CHASE`).
  - `renderer_3d after <frames> <command>` runs any console command after that many drawn frames, also while paused or across a load.

**Verification:** Release build and **121/121 tests** pass. The new unit test covers all 8 directions (vehicle centred below the middle of the screen, distance behind, ground clearance), a 45° turn across north (under 2° a frame), the turn-rate cap, the lag limit, exact settling, a train reversal (the eye moves under 8 units a frame), and a restart after a long jump. `.\tools\phase9-chase.ps1` runs on the Phase 4 railway save (train and trucks), and `.\tools\phase9-chase.ps1 -Save AirWater` on the Phase 6 coverage save (aircraft and ship) ([railway results](evidence/phase9/p3/check-results-railway.json), [air and water results](evidence/phase9/p3/check-results-airwater.json), [chase views](evidence/phase9/p3/chase-views.png), [button](evidence/phase9/p3/button.png), logs: [railway](evidence/phase9/p3/views-railway.log), [air and water](evidence/phase9/p3/views-airwater.log)). The 9.1 and 9.2 scripts still pass. Their checks now leave out each vehicle window's button column, because the camera button shows pressed.

| Check (same game tick unless noted) | Result |
|---|---|
| Button press, outside the vehicle viewports and their button column / inside | 0 differing pixels / 90% (railway), 82% (air and water) differ |
| Button chase vs `renderer_3d view all chase` | 0 differing pixels |
| Hotkey off vs normal, hotkey on vs button, whole screen | 0 / 0 differing pixels |
| Paused 10 s, then 1 s later, whole screen | 0 differing pixels |
| Save and reload with a chase view open | loads; reopened windows are all normal |
| GPU references, chase views (railway / air and water) | 1612, max 0.009% / 868, max 0.17% differing |
| Ground below the horizon showing sky, large train, truck and ship views | none |

Smoothness was measured over a month at normal speed, from every chase camera update (about 60 a second). "Excess" is how much further the eye moved in one frame than the vehicle did nearby; the unsmoothed column is a camera held straight behind the vehicle.

| Vehicle | Updates | Heading changes | Covered | Largest turn per frame | Excess per frame, chase / unsmoothed |
|---|---|---|---|---|---|
| Train | 3,309 | 2 (reversals) | station, bridge, tunnel, slopes | 4.1° | 3.3 / 64 |
| Trucks (3) | 9,927 | 33 | stations, bridge, tunnel, slopes | 4.1° | 2.7 / 43 |
| Ship | 3,020 | 11 | canal, buoys | 4.1° | 2.9 / 78 |
| Aircraft | 3,020 | 48 | airports, climbing and descending | 4.3° | 2.9 / 43 |

The first run without jump handling turned the camera 113° in one frame when the train reversed at a station. That run motivated the turn-rate cap and the jump easing.

Notes:
- The large aircraft capture looks out past the edge of the small coverage map, where there is no ground, so the hole check skips it.
- In a tunnel the chase camera still follows the vehicle underground; the fade to black is 9.5.
- Chase in fast-forward keeps the vehicle in view through the lag limit, but the vehicle moves many tiles per frame, so it cannot look smooth.

### 9.4 Cab view
Place the camera at the front of the lead vehicle at about driver height, looking forward. Hide or clip the lead vehicle so the camera doesn't see its own model, while the rest of the consist stays visible on curves. Ships use the bow and aircraft the nose.

Gate: cab view rides a train along a full route, including junctions, stations, bridges and slopes, with no self-clipping or near-plane holes in nearby track and platforms.

**Done (2026-10-19).** The user tried it in game and confirmed it works.

- **Camera:** a perspective eye on the front tip of the vehicle's own 3D model, at 80% of the height of the model's front 30%, so trains and trucks see from the cab end, ships from the bow and aircraft from the nose (`CabMount3D`, `terrain3d_impl.h`, cached per model). It looks along the heading 6° below the grade with a 70° field of view (`Terrain3D::CabEye`, `CAB_PITCH`, `CAB_FOV`). The fallback boxes use half the vehicle length and a height of 5.
- **Slopes:** road and rail vehicles going up or down a slope (`GVF_GOINGUP_BIT`/`GVF_GOINGDOWN_BIT`) give a grade of one tile height over one tile (26.6°). The eye rises with the front of the vehicle and pitches along the slope. The grade is now part of `ChaseTarget` and the follow state (`Viewport::camera_follow` grows from 11 to 13 floats); chase views ease it but don't use it.
- **Smoothing:** `FollowChase` takes a `FollowTiming`. Chase keeps `CHASE_TIMING` unchanged. `CAB_TIMING` stays on the vehicle: position eases over 0.05 s and trails at most 4 units, heading and grade turn over 0.35 s or 12 units travelled at up to 240° a second, and a jump such as a train reversing cuts straight to the other end instead of sliding through the train. Changing the camera clears the follow state.
- **Own vehicle left out:** a cab camera carries its vehicle's position (`Camera::hidden`/`hides`), and the library instance drawn exactly there is skipped in the GPU path and the CPU reference (`HiddenVehicle3D`). The rest of the consist is still drawn. The image key grows from 17 to 21 ints with that position. Vehicles drawn as fallback boxes are not left out; every temperate vehicle has a model.
- **Button and hotkey:** `WID_VV_CAMERA` and `V` cycle normal → cab → chase → normal; the tooltip says so. The 9.1 orthographic cab stand-in is gone.
- Console (test scripts): `renderer_3d chaselog on` also logs cab updates (`camera=cab`, with target and smoothed grade) and, per cab render, how many vehicles it left out (`PHASE9 CABDRAW hidden=`). `PHASE9 VIEW` lines end with the camera's pitch and whether the vehicle is underground.

**Verification:** Release build and **122/122 tests** pass. The new unit test covers all 8 directions (eye ahead of the vehicle at the given height, the vehicle's own position culled, track half a tile and two tiles ahead centred on screen), the eye and pitch on a slope, heading and grade easing within the turn rate, position lag and the reversal cut. `.\tools\phase9-cab.ps1` runs on the Phase 4 railway save (train and trucks) and `.\tools\phase9-cab.ps1 -Save AirWater` on the Phase 6 coverage save (ship and aircraft) ([railway results](evidence/phase9/p4/check-results-railway.json), [air and water results](evidence/phase9/p4/check-results-airwater.json), [cab views](evidence/phase9/p4/cab-views.png), logs: [railway](evidence/phase9/p4/views-railway.log), [air and water](evidence/phase9/p4/views-airwater.log)). The 9.1, 9.2 and 9.3 scripts still pass; the 9.3 script now presses twice to reach chase.

| Check (same game tick unless noted) | Result |
|---|---|
| Button cab, outside the vehicle viewports and their button column / inside | 0 differing pixels / 93% (railway), 81% (air and water) differ |
| Button cab vs `view all cab`, button chase vs `view all chase`, third press vs normal, hotkey vs button | 0 differing pixels each |
| Cab vs chase, inside | 88% / 64% differ |
| Cab renders leaving out exactly one vehicle (railway / air and water) | 90% of 12,015 / 100% of 5,171; never more than one. The rest had the vehicle underground, so not drawn |
| Ground below the horizon showing sky, 6 large captures per type | none for train, trucks and ship (one truck capture in a tunnel left out until the 9.5 fade) |
| GPU references, cab views (railway / air and water) | 1105, max 0.0001% / 704, max 0.002% differing |

The ride was logged over a month at normal speed. "Excess" is how much further the eye moved in one frame than the vehicle did nearby.

| Vehicle | Updates | Heading changes | Covered | Turn rate over the cap | Excess per frame |
|---|---|---|---|---|---|
| Train | 3,329 | 2 (reversals) | station, bridge, tunnel, slopes | 0 | 0.35 |
| Trucks (3) | 9,987 | 33 | stations, bridges, tunnels, slopes | 0 | 0.23 |
| Ship | 2,539 | 11 | canal, buoys | 0 | 0.91 |
| Aircraft | 2,539 | 46 | airports, climbing and descending | 0 | 0.42 |

Notes:
- The railway save's train runs a single line with no junction; curves were covered by the trucks. Junctions were checked by the user in game rather than by a fixture.
- The aircraft cab mostly sees sky when it flies off the edge of the small coverage map, so the hole check skips it, as in 9.3.
- In a tunnel the cab looks at the hill from below; the fade to black is 9.5.

### 9.5 Exits and edge cases
- **Tunnels:** fade to black when entering and fade in on exit, from authoritative tunnel and hidden state.
- **Snap back** to normal when the vehicle is sold, crashes, enters a depot or hangar, or the window closes.
- **Aircraft:** altitude changes, holding patterns, helicopters, landing and take-off.
- **Road vehicles:** overtaking and turning around at road ends.
- **Trains:** reversing, where the lead vehicle changes.

Gate: every listed case is exercised on a fixture with screenshots, and no stale camera survives a vehicle being removed.

**Done (2026-10-19).**

- **Tunnel fade:** a cab or chase view goes black on the way into a tunnel and fades back in after it, from the game's own state: the vehicle is hidden on a tunnel tile (`VehicleInTunnel3D`), and on the way in, how far the eye still is from the frame where the game hides the vehicle (`TunnelToGo3D`, `_tunnel_visibility_frame`). The view darkens over the last 8 units before the eye gets there, so the fade follows the vehicle at any speed, and it fades in over 0.4 s after the vehicle comes out (`Terrain3D::TunnelDark`, `TUNNEL_FADE_*`). A vehicle that hides on a curve fades out over 0.2 s instead. A cab stays black until its eye is out of the exit portal (`TunnelPortalAhead3D`). Without that, the truck cab faded in while looking at the inside of the portal. A long frame fades at most a quarter of the way, so a stall can't skip the fade.
- **Rendering the fade:** the darkness is stored per view (`Viewport::camera_dark`), carried by the camera (`Camera::dark`) and is part of the image key (21 → 22 ints). A partly dark view gets a full-view pass that scales its colours (`DrawProofFade`, alpha kept), in both the GPU path and the reference, so GPU references still compare like with like. A fully black view clears to black and draws nothing. A black view keeps following its vehicle, so the ground around it stays loaded for when it comes out. An early version parked the black camera at a fixed spot so its image could be reused, but the meshes along the real route went cold and the first frame out of the tunnel stalled for about 450 ms.
- **Snap back:** a cab or chase view returns to normal when its vehicle crashes or is in a depot or hangar (`RideEnded3D`, checked every frame), so pressing the button there does nothing. When a vehicle is deleted (sold, or a crashed vehicle cleared away), every view that names it is reset (`StopGlobalFollowVehicle`), so no camera can latch onto a later vehicle with the same ID. Closing the window takes its camera with it.
- **Trains reversing** hand the cab to the other end with the 9.4 cut. **Road vehicles turning round and overtaking**, and **aircraft** taking off, climbing, holding and landing (planes and helicopters), needed no changes and stay within the 9.4 smoothing limits.
- Console (test scripts, single player only): `renderer_3d ride <vehicle> depot|stop|start|turn|reverse|sell|crash|extra` runs the vehicle's own commands for its owner, as an AI's would be, crashes it, or opens an extra viewport chasing it. `renderer_3d onride <vehicle|any> <event> <command>` runs a command the first time a view sees an event (`entering`, `black`, `leaving`, `clear`, `snapback`, `takeoff`, `landing`, `helitakeoff`, `helilanding`, `holding`, `overtaking`, `turning`); the scripts use it to take their screenshots at the right moment. `renderer_3d views` also lists other views that still name a vehicle (`PHASE9 OTHERVIEW`). `PHASE9 CHASE` lines now carry the darkness, the tunnel state and the vehicle's own movement state, and GPU reference lines carry the eye.

**Fixtures:**
- *Railway:* the Phase 4 save. On reload its fixture AI also runs `fixtures/phase9/edges/ai/edges.nut`, which builds a straight dead-end road with a stop near each end and two trucks (12 and 15). They turn round at the road ends, and once the first stops halfway along, the second overtakes it. Ordinary AI commands only.
- *Air:* the Phase 8.6 generated map (seed 20261016) in 2005. `fixtures/phase9/air/ai` builds a city airport, a small country airfield and a heliport, three small planes between the city and the airfield (too many for it, so they hold), and two helicopters between the heliport and the city.

**Verification:** Release build and **123/123 tests** pass. The new unit test covers the distance fade at any speed, staying black inside, the timed fade-out and fade-in, and a stalled frame. `.\tools\phase9-exits.ps1` (railway) and `.\tools\phase9-exits.ps1 -Save Air` ([railway results](evidence/phase9/p5/check-results-railway.json), [air results](evidence/phase9/p5/check-results-air.json), [event screenshots](evidence/phase9/p5/exits.png), event logs: [railway](evidence/phase9/p5/events-railway.log), [air](evidence/phase9/p5/events-air.log)). The 9.3 and 9.4 scripts still pass after two fixes to their checkers, neither caused by 9.5: the 9.4 hole check now skips captures pitched upwards (a truck cresting a ramp showed real sky past the crest, 0.1% of the view), and the 9.3 turn-step check now leaves out frames of exactly 100 ms as stalled (8.1° in 100 ms is well within 240°/s).

| Case | Result |
|---|---|
| Tunnels: train cab, truck cab, truck chase | 8, 3 and 2 passages; black when the vehicle hides (a chase view is within a step of it), black throughout, fade-in 0.41–0.46 s every time, clear everywhere else |
| Fade screenshots (entering / black / leaving / clear) | black frames 99.7–100% black; sky at "entering" is exactly the fog colour × 0.5 |
| Train reversing | 5 cuts to the other end (1 commanded, the rest at the line ends); before/after differ 89% |
| Trucks turning round (road ends and on command) / overtaking | 330 / 68 updates; turn rate never over the cap, eye at most 0.7 units beyond the vehicle per frame |
| Depot | truck sent to its depot snaps back (and once more passing through one on its own route); another truck snapped back driving through a depot |
| Crash | the truck's window and an extra viewport chasing it both snap back in the same tick |
| Sold / cleared away | windows closed; afterwards no view names either vehicle |
| Planes / helicopters | take-off, landing and holding for planes, take-off and landing for helicopters; altitude 9–242; turn rate never over the cap; eye at most 2.8 units beyond the vehicle per frame (chase) |
| Hangar | plane sent to its hangar snaps back |
| GPU references (railway / air) | 2822, max 0.003% / 1362, max 2.5% (see notes) |

Notes:
- On the air map, 272 of 1362 GPU references differ by more than 0.05%, all with the eye low at the city airport. Dumped image pairs show the difference is one-pixel slivers along the edges of thin airport models close to the eye (radar and lattice towers, light poles), between the retained GPU path and the reference path. These views are never faded, the orthographic 8.6 airport checks match, and the railway views match, so this is existing airport geometry rasterising a pixel apart in close perspective, not a 9.5 change. The air check allows up to 3% and reports the count.
- In a station with a roof, the cab can see the inside of the building just ahead (railway, before the commanded reversal). It is not a hole and is left for review.
- Event screenshots are taken a frame or so after the event, so their darkness is close to, but not exactly, the logged value.

#### 9.5a Toolbar access and 3D settings - approved 2026-10-19

Add a discoverable **3D button to the main toolbar (hotbar)**. The preferred design is a dropdown with a checked **Enable 3D** entry, access to 3D preferences, and camera controls/help. Final menu layout can follow the existing toolbar conventions. Players must be able to enable and disable 3D without opening the console.

- Remember the enable preference and applicable 3D preferences in client configuration, independently of game saves and multiplayer state. Keep LOD off.
- Show supported/unsupported and enabled/disabled states clearly, retaining the working classic fallback.
- Replace the development banner with the normal controls; retain useful camera hints where needed. Add later slices' settings to this menu as they become available.
- Verify the button/dropdown with overlapping windows, UI scaling, resizing, keyboard navigation and mode switching; complete the outstanding native interaction checks alongside this work.

Gate: a fresh launch can enter and leave 3D from the toolbar, retain the chosen preference after restart, and expose camera help without console commands. Unsupported configurations have a clear disabled state or fallback; the original toolbar and 2D mode remain usable.

**Implementation and scripted verification (2026-10-19):** the main toolbar has a 3D dropdown in its complete layout and both collapsed rows. It exposes Enable 3D, saved client preferences for textured terrain and camera hints, building/orbit controls and persistent help. Ctrl+Alt+3 opens the menu; Up/Down, Enter and Escape work without a console. The development banner is removed. Unsupported drivers retain classic 2D and the saved preference. LOD remains off. Release build and **123/123 tests pass**; `tools/phase95a-toolbar.ps1` verifies 19 states and 18 captures across seven fresh/restart/driver/scaling cases, including default driver selection, two overlapping vehicle windows, 800x600/1280x900 resize, both collapsed rows at 200%, software fallback, both supported blitters, and persistence of disabling. [Implementation and native checklist](phase95a-toolbar.md), [results](evidence/phase9/p5a/check-results.json), [gallery](evidence/phase9/p5a/gallery.html).

**User approval (2026-10-19):** the user approved 9.5a and requested 9.5b. The historical scripted checks did not exercise native mouse, tooltip, border dragging or cross-monitor DPI input; no new native pass is claimed.

#### 9.5b Station names, town names and signs in 3D - approved 2026-10-19

Restore map information in 3D, starting with **station names**, then town names, user signs and floating text effects. Respect the existing label visibility, size, colour and zoom preferences.

- Project labels from their authoritative world positions for classic and rotated orthographic 3D views; keep text legible and its click target aligned with the displayed label.
- Preserve station/town/sign actions and window clipping. Keep ride views uncluttered; labels must not introduce picking or construction into cab/chase views.
- Exercise dense towns, long station names, slopes, multiple viewports, zoom and UI scaling. Use the toolbar/preferences from 9.5a for any additional controls.

Gate: station/town names and signs are readable and open the correct existing windows from their displayed positions, including after pan/zoom/rotation and in secondary views. Label settings and classic rendering continue to work.

**Implementation (2026-10-19):** station, waypoint, town and sign labels use authoritative world anchors and the same camera projection for drawing and clicks. Original styles, display/facility/competitor preferences and zoom fonts remain in use. Floating text retains its world anchor and existing rise/lifetime; ride views stay clear. Camera changes repaint the text layer so direct GPU presentation cannot leave stale labels. Release and **123/123 tests pass**; 100% and 200% runs plus the dense-town fixture verify **343 application label actions and 52 projected raster checks**. Native input remains unverified. [Report, reproduction and limits](phase95b-labels.md), [gallery](evidence/phase9/p5b/gallery.html).

**User approval (2026-10-19):** "approved / looks good". 9.5b is accepted following visual review. The documented automated/native-input coverage remains unchanged.

#### 9.5c Lighting and grounding experiment — approved 2026-10-19

Test a modest lighting improvement, such as contact shadows or a simple shadow system, to ground vehicles and buildings on the terrain. **Measure and review the experiment before adopting it**; choose the technique from actual visual results and cost.

- Compare the current lighting with the candidate on the same saved scenes, including slopes, bridges, dense towns and cab/chase views. Keep signals, track and company colours readable.
- Measure end-to-end frame work, GPU cost and memory with no vehicle windows, several ride windows and enlarged views, using the 9.6 fixtures. Keep LOD off and preserve draw distance and simulation timing.
- Provide an off switch through the 9.5a controls and retain the current lighting when the effect is disabled or unsupported.

Gate: record visual comparisons and before/after costs, then document whether the effect is accepted, optional or rejected. A completed experiment does not require enabling a slower or visually unsuitable effect by default.

**Result (2026-10-19):** 3D menu preference No shadows / Contact shadows / Contact and sun shadows Contact shadows (depth-reconstructed footprint decals, darkest overlap kept, 22% maximum) are accepted as the default; sun shadows (one 4096² map, soft PCF, 448-unit range in cab/chase views) are a menu option. User approval 2026-10-19. 12 views pass the visual check; 123/123 tests pass. Costs were measured on a busy machine, so they are approximate: contact adds about 0.1–0.5 ms draw in ordinary views and up to about 1 ms with four cab/chase windows; sun adds 1–2 ms with several cab/chase windows and 64 MiB of GPU memory. See the [report](phase95c-shadows.md).

#### 9.5d Automatic visibility and selection outlines — approved 2026-10-20

Make dense scenes easier to work in by fading obstructing buildings or trees around the construction cursor or selected vehicle, with a clear selection outline. Include station roofs obstructing ride views where appropriate.

- Build on the existing manual transparency/invisibility settings; expose an automatic-visibility preference through 9.5a and honour manual choices.
- Keep tracks and signals readable, avoid flicker as the cursor/camera moves, and preserve authoritative picking and construction targets regardless of visual fading.
- Check pause, multiple viewports, tall buildings, roofed stations and bridges. Keep all effects local to presentation.

Gate: a selected vehicle or build target remains easy to find in a dense scene; automatic fading restores correctly when focus moves, and toggling it off returns to the normal/manual presentation without changing selection or commands.

**Result (2026-10-19):** saved menu preference, per-view obstruction cutaways and stencil selection outlines are implemented. Manual transparency/invisibility and locks are preserved; ground, rails, signals, catenary and bridge decks remain readable. Release and **123/123 tests pass**; **59 comparison groups, 3,132 ground-picking samples and 37 GPU references pass** at 100%/200% with both supported blitters. Off restores every comparison exactly. Native mouse/DPI checks remain unverified. [Report](phase95d-visibility.md) and [off/on gallery](evidence/phase9/p5d/gallery.html).

**User approval (2026-10-20):** "perfect approved and i like it". 9.5d is accepted following visual review. The documented scripted/native-input coverage remains unchanged.

#### 9.5e Management and construction from rotated views — implemented; user review pending

Extend the **rotated orthographic management camera** so building and selection work at the chosen angle, replacing the current requirement to snap back to classic for construction. Cab/chase perspective views remain spectator views without picking.

- Support terrain, vehicle and sign selection, tooltips, tile highlights, drag previews, and construction/removal through the original game commands at rotated angles and supported tilts.
- Keep pan/zoom behaviour consistent and use the projected label positions from 9.5b. Preserve the classic camera and its existing interactions.
- Verify all construction orientations, slopes, bridge/tunnel surroundings, map edges, drag cancellation, overlapping windows, secondary views, resize and DPI.

Gate: a representative build/manage session can stay at a rotated angle with accurate targets and previews, correct command results and no forced snap-back. Returning to classic or 2D preserves ordinary management behaviour.

**Implementation and scripted verification (2026-10-20):** construction tools retain the rotated camera; orbit and Home retain the tool. Orthographic vehicle selection follows the drawn model triangles, while terrain tools retain ground targets beneath roofs/decks. Cursor zoom keeps its ground anchor. Rectangle and signed diagonal previews draw consistently in the retained and reference paths; cab/chase/fixed views still reject picking. Release and **124/124 tests pass**. At 100%/200%, both supported blitters pass **22,552 ground checks, 50 vehicle-window actions, 263 label actions, 42 command-result checks and 7 GPU references**. Native mouse/cross-monitor DPI acceptance remains unverified; user review is pending. [Report, reproduction, performance and limits](phase95e-management.md), [gallery](evidence/phase9/p5e/gallery.html).

#### 9.5f Expanded spectator and ride view — planned, last priority

After the earlier follow-ups and 9.5g, optionally add a larger, maximized cab/chase presentation with minimal window furniture. Provide easy vehicle selection/switching and cab/chase controls without repeatedly opening and closing vehicle windows.

- Provide an obvious way to restore the ordinary vehicle window or leave the ride view, including a keyboard exit.
- Preserve tunnel fades, pause behaviour, camera smoothing and the established crash/depot/deletion exits. The rest of the game UI must remain accessible.
- Measure the expanded view with the 9.6 fixtures; keep LOD off and keep picking/construction outside ride views.

Gate: players can enter an expanded ride view, switch vehicle and camera, and return to ordinary management reliably; lifecycle exits and performance remain verified. **This is the final slice in the follow-up sequence.**

#### 9.5g Zoomed-out map performance - accepted by user 2026-10-20 ([report](phase95g-zoomout.md)), before optional 9.5f

User request (2026-10-20): zooming out causes an FPS crawl, particularly on a large rectangular map (reported as approximately 1500x500). This is a management-view performance gate, separate from 9.6's cab/chase multi-view measurements. Fix the newly reported missing-terrain startup defect before measuring improvements.

- Establish repeatable before/after runs on identical saved 512x512 and 2048x512 worlds (plus 512x2048 for rectangular traversal), covering normal through maximum supported zoom-out, classic and rotated orthographic angles, paused and running, and zero/four vehicle windows.
- Measure presented frame intervals (median/p95), end-to-end CPU work, GPU time, snapshot/mesh preparation, visible geometry and model counts, uploads, retained memory and cache churn. Include cold zoom/pan and revisiting the same view; keep reference readback out of performance measurements.
- Profile first, then optimize the measured bottleneck: visibility traversal, geometry/model submission and grouping, cache reuse/retention, redundant uploads or pixel/shadow work as evidence warrants. Keep full detail and LOD off unless the user explicitly changes that instruction. Do not silently remove scenery, reduce simulation speed or change gameplay.
- Preserve terrain coverage, labels, cursor-anchored zoom, selection, construction previews and 2D fallback. Compare correctness references at the widest views and around map edges; include fresh map startup, restart and save/reload.

Gate: record a measured improvement in the failing zoomed-out cases against the same binary/save/settings baseline, explain remaining limits, and show no material normal-zoom regression or new terrain gaps. Set an absolute frame-time target after the baseline is measured; no performance improvement is claimed by adding this plan.

The follow-up order is **9.5a → 9.5b → 9.5c → 9.5d → 9.5e → 9.5g → optional 9.5f**. The user fixed the first three priorities and placed spectator view last; visibility precedes rotated management as the working order for the middle pair. Original 9.5 exit/fade checks and the completed 9.6 measurements remain valid baseline evidence. Re-run relevant interaction and performance checks as these additions land; 9.5d has user approval (2026-10-20); 9.5e is implemented and verified, awaiting user review; 9.5g has user acceptance (2026-10-20), with parallel cold-chunk building deferred; 9.5f remains optional; 9.5a and 9.5b have user approval (2026-10-19); 9.5c has user approval (2026-10-19).

### 9.6 Performance
**Done (2026-10-19).** This is a measured performance gate. **LOD stays off by the user's explicit instruction.** The renderer, 64-tile draw distance, fog and camera update rate remain unchanged; no speedup is claimed.

`tools/phase9-performance.ps1` reloads the same 512×512 fleet save for each case, at 1920×1080 using `win32-opengl`, `32bpp-optimized` and the RTX 3090 (driver 610.74). It excludes 5 seconds of warm-up and measures 15 seconds with refresh requested at 1000 Hz, normal simulation speed and reference readback disabled. Compiler jobs and other fixtures finish before measurement. These are local instrumented results, not a hardware-independent FPS guarantee.

"Draw" is mean 3D work per active drawing tick, including all views drawn in that tick. "Work" is mean end-to-end CPU work over every presented frame, including frames that reuse images. The p95 frame column measures intervals between presentations. Ordinary views redraw less often than smoothed cab/chase views, so draw cost alone is not overall frame cost.

| Case | Before draw / work | Final draw / work | Final p95 frame |
|---|---:|---:|---:|
| No vehicle windows | 0.93 / 0.33 ms | 0.97 / 0.33 ms | 2.43 ms |
| 4 ordinary windows | 2.39 / 0.52 ms | 2.45 / 0.52 ms | 4.39 ms |
| 4 mixed cab/chase windows | 3.85 / 5.13 ms | 4.38 / 5.78 ms | 9.54 ms |
| 4 enlarged mixed windows | 3.88 / 5.24 ms | 4.53 / 6.00 ms | 9.74 ms |
| 1 large cab window | 1.67 / 2.93 ms | 1.82 / 3.15 ms | 4.95 ms |
| 1 large chase window | 1.66 / 2.93 ms | 1.76 / 3.09 ms | 4.86 ms |
| Long view, grown town | 1.44 / 0.41 ms | 1.47 / 0.41 ms | 2.86 ms |

These are separate measurements with the same renderer; no speedup is claimed. With cab/chase closed, end-to-end work is effectively unchanged (hundredths of a millisecond). Several perspective views increase cost, but all tested p95 frame intervals remain below 16.7 ms. Full detail meets this local gate without reducing the draw distance or update rate. The simulation remains at approximately 37 ticks/s in timing runs. Working sets, GPU timings, uploads, triangle counts, sample counts and exact viewport sizes are in the linked JSON files.

**Coverage:** individual small cab/chase windows were measured in the baseline matrix; final runs cover four mixed windows, four resized/overlapping windows (roughly 798×374 viewports), and large cab/chase views (1748×884). A separate dense-town fixture grows the nearest town to (256,256), at (258,276), from 21 to 713 houses through the existing `CMD_EXPAND_TOWN`, then runs twelve calendar months so construction completes. Both dense-town binaries load the exact same saved state. Its large still camera gives a long view over the buildings and fog; moving cameras are covered by the other cases.

**Verification:** final Release build and **123/123 tests pass**. Separate reference runs (not timing evidence) compare retained geometry and instanced drawing against their CPU/uninstanced references, with LOD off throughout:

| Reference scene | GPU comparisons | Max GPU differing | Max instance differing |
|---|---:|---:|---:|
| cablarge | 2 | 0.0000% | 0.0000% |
| mixedlarge | 4 | 0.0004% | 0.0000% |
| town | 3 | 0.0008% | 0.0000% |

All reported references are valid; retained static streams remain within their 16-entry/32 MiB bounds; timed passes have zero GPU readback. Captures were visually inspected for all enlarged views and the dense town. Resizing here uses `ResizeWindow` through the test console; this gate does not add a native mouse/drag/DPI claim. The previously documented close-airport edge rasterisation difference remains outside this railway/town gate.

The only C++ addition in this slice is the explicitly invoked, single-player-only `renderer_3d fixturetown <x> <y> <1..2000 growth attempts>` fixture helper. It uses the existing town command with a scoped deity company, restores the company automatically, and is never called by rendering. Simulation algorithms, game commands, saves and networking are unchanged.

Evidence: [baseline matrix](evidence/phase9/p6/p96a-before-results.json), [final matrix](evidence/phase9/p6/p96-final-results.json), dense town [before](evidence/phase9/p6/p96-dense-before-results.json) / [after](evidence/phase9/p6/p96-dense-after-results.json), references [railway](evidence/phase9/p6/p96-gpu-results.json) / [town](evidence/phase9/p6/p96-dense-gpu-results.json), [gallery](evidence/phase9/p6/gallery.html), [environment and hashes](evidence/phase9/p6/environment.json), [build](evidence/phase9/p6/build.log), [tests](evidence/phase9/p6/tests.log). Complete compressed logs and measurement offsets are alongside the summaries. Early exploratory LOD results are excluded from the accepted gate.

Reproduce from the workspace root (use fresh run tags):

```powershell
.\tools\phase9-performance.ps1 -RunTag p96-check
.\tools\phase9-town.ps1 -RunTag p96-town
$town = 'D:/G ttd/.runtime/p96-town/save/p96-dense-town.sav'
.\tools\phase9-performance.ps1 -RunTag p96-town-check -Cases town -FixtureSave $town
.\tools\phase9-performance.ps1 -RunTag p96-reference -Cases mixedlarge,cablarge -Seconds 10 -VerifyGPU
.\tools\phase9-performance.ps1 -RunTag p96-town-reference -Cases town -FixtureSave $town -Seconds 10 -VerifyGPU
```
For before/after comparisons, add `-Executable <path>` to select the baseline binary; keep the save and parameters identical. `-VerifyGPU` deliberately enables synchronous reference readback and must be kept out of performance comparisons.

## Out of scope

- Free-look with the mouse. Expanded/maximized ride presentation is planned in 9.5f.
- Cab interiors or dashboards.
- Picking or construction from a perspective view.
- Sound changes.
- NewGRF vehicles beyond the existing fallback.
