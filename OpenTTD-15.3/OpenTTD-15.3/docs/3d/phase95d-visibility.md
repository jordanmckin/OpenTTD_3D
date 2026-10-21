# Phase 9.5d: automatic visibility and selection outlines

Status: implemented 2026-10-19; scripted verification completed 2026-10-20. **Approved by the user on 2026-10-20.** [Off/on review gallery](evidence/phase9/p5d/gallery.html).

**User approval (2026-10-20):** "perfect approved and i like it". Accepted following visual review; the verification coverage documented below remains unchanged.

The 3D toolbar menu has a saved **Automatic visibility and selection outlines** preference. It is enabled by default inside the opt-in 3D renderer and is a client setting, excluded from saves and network synchronization.

Ordinary map views focus on the construction target while a tool is active, then on their followed vehicle or the frontmost open vehicle window. Each vehicle viewport follows its own vehicle. Cab views clear a small area ahead of the eye without drawing an outline of the hidden cab vehicle. Fixed diagnostic cameras have no automatic focus. Hidden, crashed, depot and deleted vehicles do not keep an active focus.

Obstructing fragments of trees, houses, industries, station/depot buildings and other structures fade inside a bounded screen-space circle, only when they are nearer than the focus. The border is feathered, using a stable ordered screen pattern consistent with the existing manual transparency presentation. Ground, running rails, signals, catenary, vehicles and text remain intact. Bridges retain manual visibility: their current structure geometry includes the running deck and rails, so automatic bridge fading is deliberately excluded.

Manual transparency and invisibility still apply first. A locked category also retains its manually chosen solid or transparent presentation. The setting never changes the transparency masks, locks, selection state or commands.

An outline traces the selected vehicle's actual model silhouette or the target tile's ground boundary. Its interior is stencil-masked; the outline remains visible through obstructions. It uses nine small draws and the viewport's packed depth/stencil attachment, with no additional viewport-sized texture or GPU readback. Focus and preference changes are part of cached image identity, including while paused. Offscreen focus is discarded so a distant selected vehicle does not repeatedly invalidate unrelated map views.

## Verification

- Capped Release build passes. **123/123 CTest tests pass**, including regression replays. The Release directory has matching language and base data for double-click startup.
- **59 paused comparison groups / 182 captures / 348 viewport states pass** across the infrastructure fixture, dense town, four vehicle views, 100% and 200% UI scaling, both supported blitters, and a GPU-reference run.
- **3,132 ground-picking samples are unchanged** between off/on/restored states. Manual transparency, invisibility and lock masks are unchanged. Every off/restored image comparison has **zero changed viewport pixels**; unfocused views also remain identical.
- Dense-town checks distinguish manual hidden, transparent, locked solid and unlocked presentation. Locking houses removes the automatic cutaway while retaining the target outline; unlocking restores it.
- **37 GPU-reference comparisons pass** across the instanced, uniform and CPU-expanded paths. The largest difference is seven pixels out of 1,152,000 (under 0.0007%), consistent with edge rounding. There are no OpenGL failures or 2D fallbacks in these runs.
- Keyboard selection of the actual menu entry, saving the preference, restart with the saved disabled preference, and re-enabling through the menu pass in all five runs. The 200% menu fits the viewport.
- An additional five off/contact/sun comparison views pass the existing shadow verifier after the packed depth/stencil attachment change. [Shadow regression results](evidence/phase9/p5d/shadow-compatibility-results.json).
- Inspected captures cover tall town buildings, trees, rail previews, slopes, stations, bridges, selected vehicles, independent ordinary/cab/chase views, and closing all vehicle windows. Ride views remain non-interactive; their picking samples remain invalid as before.

Evidence: [summary](evidence/phase9/p5d/results.json), [CTest](evidence/phase9/p5d/tests.log), [build](evidence/phase9/p5d/build.log), and per-run settings, diagnostics and comparison results alongside the [gallery](evidence/phase9/p5d/gallery.html).

## Performance

Two short A/B passes use the same executable and 512-square fleet save, uncapped at 1920×1080, full models, contact shadows, four 510×228 vehicle views where applicable, five seconds of warm-up and eight seconds measured per case. The second pass runs without gallery generation alongside it:

| View setup | Mean draw, off → on | Mean total work, off → on |
| --- | --- | --- |
| Main view only, no focus | 1.60 → 2.35 ms | 0.93 → 1.06 ms |
| Four normal vehicle views | 3.26 → 3.87 ms | 1.35 → 2.05 ms |
| One cab and three chase views | 5.19 → 6.10 ms | 9.57 → 10.92 ms |

The two samples show roughly 0.6–0.7 ms more drawing with four normal vehicle views and 0.9–1.1 ms with mixed ride views. These are approximate busy-machine measurements: the no-focus control varied by 0.75 ms in the repeat despite identical presentation, while its first pass was effectively unchanged (1.67 → 1.66 ms). They do not isolate the full cost from background variation. All measured cases retain direct presentation with zero readback and zero LOD instances. [Results and both passes](evidence/phase9/p5d/performance-results.json); per-case metadata records the executable hash, settings, sample interval and fixture.

```powershell
.\tools\phase9-performance.ps1 -RunTag p95d-timing-off -Seconds 8 -Cases closed,normal4,mixed4 -Shadows contact -AutoVisibility off
.\tools\phase9-performance.ps1 -RunTag p95d-timing-on -Seconds 8 -Cases closed,normal4,mixed4 -Shadows contact -AutoVisibility on
```

Reusable scripts:

```powershell
.\tools\phase95d-visibility.ps1 -RunTag p95d-infra
.\tools\phase95d-visibility.ps1 -RunTag p95d-town -Scene town -FixtureSave '.runtime/p96-town-final/save/p96-dense-town.sav'
.\tools\phase95d-visibility.ps1 -RunTag p95d-fleet -Scene fleet
.\tools\phase95d-visibility.ps1 -RunTag p95d-infra200 -Scale 200 -Blitter 40bpp-anim
.\tools\phase95d-visibility.ps1 -RunTag p95d-gpu -VerifyGPU
```

Each comparison is paused and captures off/on/off in the same session. `renderer_3d focusstats <tag>` logs focus identity, manual masks/locks and nine independent ground-picking samples per viewport. The verifier compares these samples and checks restoration against the original off capture. Additional `-Scale`, `-Blitter` and `-VerifyGPU` controls exercise existing presentation paths.

Native interaction is unverified: the computer-use skill requires `node_repl`, which is not exposed in this session. Scripted input and application screenshots do not establish native mouse, tooltip or cross-monitor DPI acceptance.

LOD remains off. Rotated orthographic management/construction remains Phase 9.5e; the rotated views tested here are inspection views. Simulation, commands, saves and networking are unchanged.
