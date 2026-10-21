# Phase 9.5e: rotated management and construction

Implemented and scripted verification passed on 2026-10-20. User visual/native acceptance is pending. [Review gallery](evidence/phase9/p5e/gallery.html).

Native feedback (2026-10-20): the user reports that rotated views worked in their playtest. This is positive native feedback, not a report of an unresolved picking or polling defect. The exact tools, drag/cancel cases and DPI/window transitions exercised were not specified, so the individual remaining checks below are not all marked passed.

Alpha follow-up (2026-10-20): both original management matrices were rerun against the packaged alpha executable and passed. Additional application-callback checks now cover roads, depots, stations, signals, bridges, tunnels, terrain edits, invalid placement and Escape cancellation. See [the alpha check report](rotated-alpha-checks.md) for results, executable hashes and the remaining native checks.

## Result

Construction no longer returns the orthographic camera to classic. Tools stay selected during orbit and Home transitions. Ground picking follows the current yaw/tilt; structures and bridge decks do not redirect ground construction onto adjacent tiles. The existing height-aware classic inverse remains the classic path.

Vehicle clicks use the actual transformed model triangles, ordered by projected depth, including wagon IDs and the fallback geometry. Hidden/unclickable vehicles are excluded. Labels keep their established displayed-pixel priority. A vehicle-body click opens its vehicle window without also opening the structure beneath it. Cab, chase and fixed perspective views reject both vehicle and ground targets.

Rotated cursor zoom retains the picked ground anchor. Rectangle and signed diagonal area highlights use the original tile-selection extents in the retained shader and CPU reference. Track-piece drag previews keep the original direction/parity rules. Existing rail tools, measurement tooltips and build/remove callbacks issue the original commands. Menu/help text now describes building at rotated angles.

Simulation algorithms, commands, saves and network formats are unchanged. LOD remains off. No 9.5f work is included.

## Verified evidence

Release builds successfully; **124/124 tests pass**. The added unit test exercises sloped triangle hits and conservative pointer bounds at 24 rotations, five tilts and three zoom scales. [Build](evidence/phase9/p5e/build.log), [tests](evidence/phase9/p5e/tests.log), [source hashes](evidence/phase9/p5e/source-sha256.json).

| Run | Ground checks | Slopes / foundations / bridge surroundings | Vehicle actions | Label actions | Command results | Captures |
|---|---:|---:|---:|---:|---:|---:|
| 100%, 32bpp-optimized | 11,264 | 1,136 / 2 / 187 | 27 | 129 | 21 | 31 |
| 200%, 40bpp-anim | 11,288 | 1,136 / 2 / 187 | 23 | 134 | 21 | 31 |

There are **zero ground-picking failures**. Both runs exercise yaw 0/45/90/135/180/225/270/315 and tilts from 40% to 180%; all six rail pieces are confirmed in authoritative track bits. Previews are checked before any construction, then building, removing and cancelling are checked separately. Gold preview pixels must appear and disappear after clearing the preview. Rectangle and diagonal selection captures were visually inspected.

Orbit and Home retain the active tool; returning Home restores the previous rotated angle. Cursor zoom in/out retains the target tile. Additional map and vehicle viewports, internal window overlap, 800x600 resize, map edges and returning to classic/2D are exercised. Cab/chase windows each reject nine sampled ground/vehicle targets, even with clamping requested.

The 200% run passes **7 GPU/reference comparisons**, maximum difference **0.000955%**. Geometry and instance reference paths agree within edge rasterisation rounding. Correctness runs use readback; timing runs disable it.

The vehicle checker samples exposed vehicle bodies, excluding displayed label pixels and covered internal windows. Labels are tested separately through their actual application click actions. Measurement tooltip creation is tested with scoped application cursor state in a hidden fixture; this does not inject OS mouse input or establish native hover behavior.

Results: [100%](evidence/phase9/p5e/results-100.json), [200%](evidence/phase9/p5e/results-200.json). Compressed application logs, environment records and captures are alongside these summaries. Historical exploratory runs with an incomplete preview/label-overlap checker are excluded.

## Performance

The same 512x512 fleet save is loaded before and after, at yaw 90 / tilt 80, 1920x1080, contact shadows and automatic visibility on. Each case has five seconds of warm-up and eight seconds of measurements. LOD stays off, reference readback is disabled, and compiler/functional fixtures have finished. The earlier binary is the preserved 9.5d console executable; both binary hashes and measurement offsets are retained.

Draw is 3D work per active drawing tick; work is CPU work per presented frame. These local measurements vary with machine activity; no renderer speedup is claimed. In particular, the older binary's mixed-window p95 was 22.91 ms in this run, so its large difference must not be presented as a 9.5e optimisation.

| Case | Before draw / work ms | Final draw / work ms | Before / final p95 frame ms |
|---|---:|---:|---:|
| closed | 2.15 / 0.43 | 2.06 / 0.40 | 3.71 / 3.52 |
| mixed4 | 9.49 / 10.84 | 5.91 / 7.06 | 22.91 / 10.75 |
| normal4 | 4.64 / 0.92 | 4.67 / 0.88 | 6.41 / 6.44 |

All final p95 intervals are below 16.7 ms. Normal map-window costs remain close to the earlier binary; simulation runs at approximately 37 ticks/s. [Before measurements](evidence/phase9/p5e/performance-before.json), [final measurements](evidence/phase9/p5e/performance-after.json). Pointer checks also record elapsed microseconds per batch in the ground diagnostics; these are correctness batches, not steady-state frame measurements.

## Reproduce and review

Run from the workspace root with fresh tags:

```powershell
.\tools\phase95e-management.ps1 -RunTag p95e-check
.\tools\phase95e-management.ps1 -RunTag p95e-check200 -Scale 200 -Blitter 40bpp-anim -VerifyGPU
.\tools\phase9-performance.ps1 -RunTag p95e-timing -Cases closed,normal4,mixed4 -Seconds 8 -Yaw 90 -Tilt 80 -Shadows contact -AutoVisibility on
.\tools\phase95e-demo.ps1 -Show
```

The demo uses an isolated profile and the infrastructure fixture, starts paused at yaw 45 / tilt 80, and allows construction while paused. Use comma/period to rotate, Page Up/Down to tilt, Ctrl+drag to orbit, and Home to switch to/from classic. Build using the ordinary toolbar. Rail tool orientations remain map directions as they do in the original game.

## Acceptance still requiring native input

The Windows automation skill requires `node_repl`, which is not exposed in this session. Application callbacks, screenshots and 200% GUI scaling do not establish native mouse/monitor DPI behavior.

- Click exposed vehicles, wagon bodies and station/town/sign labels at several angles; verify the expected window and label priority.
- Build/remove rail in each toolbar orientation, then exercise roads, stations, depots, bridges/tunnels and terrain tools around slopes. Confirm actual mouse drag previews and measurement tooltip placement.
- Cancel a drag with Escape/right-click, rotate while a tool is active, and switch Home/2D during management. Verify no accidental command.
- Pan and cursor-zoom in main/additional views, including map edges; confirm covered internal windows block clicks.
- Resize using the native border, and move the window between monitors with different DPI settings.
- Confirm cab/chase clicks remain spectator-only.

The original matrix specifically covered rail build/remove. The [alpha follow-up](rotated-alpha-checks.md) adds scripted construction results for the other tools listed above. Native mouse coverage, multiplayer, arbitrary NewGRFs and other hardware are not claimed. User visual approval remains pending.
