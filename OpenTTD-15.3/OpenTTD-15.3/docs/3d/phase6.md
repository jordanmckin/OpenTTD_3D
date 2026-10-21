# Phase 6: usability and explicit base-content coverage

Status: implementation and scripted checks complete; native interaction acceptance pending. Native Windows checks are delegated to the user through [the manual checklist](phase6-manual-tests.md); they are not recorded as passes.

## Implemented

Fixed-camera construction now uses the original engine ground inverse, including the caller's map-edge clamping flag. Building roofs and bridge decks cannot redirect a construction cursor to an adjacent tile. Inspection-camera picking considers terrain faces only; general rotated-camera management remains out of scope.

The existing transparency and invisibility flags now control trees, houses, industries, company structures and elevated bridge decks. Transparency uses a screen-door pattern: discarded fragments expose the geometry behind them without incorrectly sorting overlapping alpha surfaces. Rails, road surfaces and ground remain solid. Visibility changes invalidate cached viewport images even while paused. The native toolbar/hotkeys remain authoritative; `renderer_3d visibility <1..8> solid|transparent|hidden` makes the same presentation settings scriptable.

Ships and primary aircraft now have simple category geometry at authoritative x/y/z and heading. Aircraft shadows/rotor child objects are excluded as separate bodies; hidden/depot vehicles stay hidden. Airports, hangars, docks, buoys, rail waypoints, water depots and locks have basic geometry. These are shared prototypes, not final Phase 8 art. Snow/desert/rock/field materials follow clear-tile state; snowy/desert tree ground follows tree state.

`renderer_3d coverage` enumerates every station category (including zero counts), clear-ground materials, slope/steep counts, water structures, primary vehicles and missing assets. The new fixture constructs air and water routes with ordinary AI commands, saves its vehicle IDs and resumes monitoring on reload. It locates vacant airport sites, verifies terrain corners, and plants trees to restore town ratings after terraforming; no simulation rules are bypassed.

## Commands

From the workspace root:

```powershell
.\tools\phase6-demo.ps1
.\tools\phase6-demo.ps1 -Scene AirWater
.\tools\phase6-demo.ps1 -SmokeTest
.\tools\phase6-checks.ps1 -Mode Coverage
.\tools\phase6-checks.ps1 -Mode Climates
.\tools\phase6-checks.ps1 -Mode Reload
.\tools\phase6-network.ps1
python tools/verify-phase6.py
```

The checks runners automatically prepare a separate console-subsystem copy of the current Release executable for each mode using the installed MSVC editbin. This matches the technique in [build_and_test.md](build_and_test.md). Do not start two copies of the same check mode concurrently. All profiles, logs and saves stay under `.runtime/phase6-*`. The demo uses the existing infrastructure save and starts paused. The AI routes belong to company 2.

## Evidence

- Visibility captures reviewed: solid, patterned transparent, fully hidden, restored with a secondary viewport. Ground and roads remain readable; original windows composite over the world.
- Town fixture: 5,120 height samples and 281 interior classic-picking comparisons per audit, zero failures with visibility solid/hidden. These are scripted coordinate checks, not mouse tests.
- Temperate, arctic, tropical and toyland mountainous maps: each reports 5,120 height checks and zero failures. Respectively 231/246/231/230 interior picking checks pass. Steep-tile counts are 16/60/21/14.
- Air/water fixture: both airports, aircraft, canal, ship depot and buoys built; primary aircraft and ship repeatedly move. Save and separate reload work; the AI reports `PHASE6 RELOADED`. Reload reports two rendered vehicles and zero missing assets on this fixture.
- Localhost multiplayer: a dedicated server runs the existing AI train/truck route while a graphical client switches 3D ? classic ? 3D. 68 synchronization packets and continuing client acknowledgements pass without a seed mismatch; the client observes normal server shutdown. This verifies a finite operating interval, not all possible multiplayer games. Exact network revision is `norev0000-uunknown`; successful same-binary testing does not establish compatibility with an upstream release or another fork build.

## Coverage matrix

| Area | Scripted evidence | Remaining validation / limits |
|---|---|---|
| Fixed ground picking, flat/sloped/foundation/coast | Classic ground inverse; town and four-climate audits | Native cursor, drag, corner selection and zoom/edge interaction checklist |
| Rail, roads, crossings, bridges, tunnels | Phase 4 construction/movement fixture; Phase 6 visibility integration | Native construction and bridge visibility checklist; bridge ramp structures remain solid |
| Town, industries, trees | Solid/transparent/hidden/restored captures | Exact art coverage remains the Phase 5 registry; many industries use explicit magenta missing markers |
| Rail and road vehicles | Existing operational coal train and trucks; AI in network session | Native management clicks, orders and depots |
| Aircraft | Two small airports, moving aircraft, reload | Simple shared silhouette; other airport layouts and helicopters not yet exercised |
| Ships | Moving ship, canal, two buoys and two-tile ship depot; reload | Dock service, locks, aqueducts and loading/cargo routes not yet exercised |
| Stations | Rail, road truck stops, airports and buoys exercised across fixtures | Bus/bay stops, docks/oil rigs, waypoints, other airports require expansion or manual checks |
| Landscapes | All four climates, non-flat and steep tiles, snow/desert | Category art stays shared; no exhaustive every-identity art claim |
| UI and viewports | Secondary viewport and overlapping window screenshot | Native tooltip, click routing, cursor, resize and DPI checks pending user |
| Save/load and speed | Coverage save/reload; original AI persists; fast-forward capture fixtures | Manual normal/fast/pause interaction checklist |
| Multiplayer | Same-binary localhost synchronization, renderer switching, active AI/cargo and normal shutdown | Archive version provenance and cross-build compatibility unresolved |

The generated climate maps deliberately reveal missing model coverage: 93/83/119/107 missing asset tiles in the temperate/arctic/tropical/toyland audits. These are explicit placeholders, not missing simulation objects. Full model refinement is Phase 8. No Phase 7 large-map performance claim is made.

## User feedback (2026-10-16)

Management and clicking passed the user's manual trial. The user reported gaps between diagonal rails; the strip endpoints now intersect their tile boundaries instead of being clamped, preserving continuous rail and ballast edges. A regression covers both diagonal orientations and all six track pieces. The Release fixture builds 24 pieces through ordinary commands and captures continuous joins in [orientation A](evidence/phase6/phase6-diagonal-a.png) and [orientation B](evidence/phase6/phase6-diagonal-b.png). Reproduce with `./tools/phase6-checks.ps1 -Mode Rail`. The user also reported poor performance, worse with multiple vehicle windows open, and explicitly deferred that work to Phase 7. This deferral is recorded in both planning documents. Unreported native checks remain unverified.

## Acceptance handoff

The [gallery](evidence/phase6/gallery.html), fixture sources, saved air/water route, coverage matrix, evidence verifier and manual checklist accompany the changes. Release build and 105/105 CTest tests pass; the actual Release railway launcher produces fresh captures/save and exits normally. All automated profiles use the unmodified simulation, commands, save format and network protocol.

The user explicitly allowed a list of native tests because Windows controls are unavailable to this agent. Complete [the checklist](phase6-manual-tests.md) before treating the ordinary-construction/management acceptance gate as fully verified. No native test is silently assumed passed. Full art refinement stays in Phase 8; large-map performance stays in Phase 7.

Performance: no controlled CPU/GPU or FPS benchmark was performed for Phase 6. Logs contain per-viewport render/readback times; these include CPU work and synchronous readback and overlap other fixture runs. They must not be used as an FPS claim.

Changed engine files: `console_cmds.cpp`, `viewport.cpp`, `video/proof3d.h`, `video/proof3d_impl.h`, `video/terrain3d_impl.h`, `video/rail3d_impl.h`, `video/asset3d_impl.h`, and `video/opengl.cpp`. Phase 6 launchers, AI/scripts/save, manual checks, matrix, captures and verifier are new. Next smallest task: native ground selection/rail dragging and transparency checks in the fixed camera; fix any reported mismatch before closing the acceptance gate.
