# Phase 9.5b: projected map labels and floating text

Implemented and **approved by the user on 2026-10-19** following visual review ("approved / looks good"). Scripted verification passes. LOD remains off.

Station names, waypoint names, town names and user signs now draw over orthographic 3D. Their anchors come from the existing station/town tile and terrain height, or a sign's world coordinates. The same camera projection serves drawing and clicking. The renderer copies the existing label dimensions and offsets; it never changes the classic sign tree or the authoritative object position.

The original text, company colours, station facility icons, population preference, normal/small fonts, competitor/facility filters, transparency and invisibility settings remain in use. No additional setting is needed. Label actions open the existing station, waypoint, town and sign windows. In 3D, overlapping label clicks follow the drawing order: stations, then signs, then towns. Classic 2D retains its original priority.

Floating costs, income, transfers, loading indicators and vehicle start/stop text retain their world anchors. Rising text keeps its existing screen-space rise and lifetime. Text zoom limits, loading-indicator preferences and text transparency still apply. Cab/chase/fixed perspective views draw no map labels or floating text and retain their existing spectator-only input behavior.

Camera changes now invalidate the label layer in every ordinary viewport. This matters with direct GPU presentation: refreshing the 3D texture alone previously left old text in the UI buffer. Label changes also dirty ordinary viewports when a retained scene image can be reused. Rotated views visit the sign tree and clip projected label bounds; classic views retain spatial queries. Integer click bounds match the final text raster, including subpixel camera anchors and odd label widths.

## Verification

- Release build and **123/123 CTest tests pass**.
- At 100% UI scale with `32bpp-optimized`: **29 viewport states, 147 application label actions and 26 projected raster checks pass**.
- At 200% UI scale with `40bpp-anim`: **29 viewport states, 148 application label actions and 26 projected raster checks pass**. The test sign width changes from 114 to 226 pixels, confirming actual scaling.
- Dense 512-square fleet/town fixture: **10 viewport states and 48 application label actions pass**, including four ordinary vehicle windows and an extra viewport. The fixture is the mature Phase 9.6 town save.
- Tested yaw 0/45/90/180/270, tilt 60/80/100/140, pan, zoom 1/2/4, long station names, raised terrain, window clipping, overlapping viewports, resize to 800x600, label/facility/competitor preferences, transparency/invisibility, classic 2D switching, floating-text visibility, and cab/chase suppression.
- Boundary diagnostics check the first/last drawn pixels and the pixels immediately outside each 3D label. Screenshot checks independently sample label frame pixels at their projected positions, catching stale text after a rotation. Screenshots were visually inspected for rotated views, dense town, overlapping viewports and 200% scaling.

The click harness calls the application's existing viewport handler and verifies that the correct window class/ID opens. It deliberately bypasses OS mouse routing. Native mouse interaction, tooltips, border dragging and cross-monitor DPI transitions have not been exercised; the computer-use tool is unavailable. The user's 9.5a approval is recorded separately and is not presented as a new native test result.

Evidence: [100% results](evidence/phase9/p5b/labels-100-results.json), [200% results](evidence/phase9/p5b/labels-200-results.json), [dense-town results](evidence/phase9/p5b/dense-results.json), [gallery](evidence/phase9/p5b/gallery.html), [build](evidence/phase9/p5b/build.log), [tests](evidence/phase9/p5b/tests.log). Compressed application logs and binary/fixture hashes accompany the results.

## Performance

The pre-change executable is the approved 9.5a/9.6 working build. Both binaries load identical saves with full detail, LOD off, a 1920x1080 window, `win32-opengl`, `32bpp-optimized` and the same refresh request. Each timed case excludes five seconds of warm-up and measures fifteen seconds without GPU reference readback. Compiler jobs and other game instances are finished before these isolated measurements. Values are local instrumented CPU/presentation measurements, not a general FPS guarantee.

| Scene | Mean CPU work before / after | p95 presentation interval before / after |
|---|---:|---:|
| Fleet, main view only | 0.450 / 0.507 ms | 3.000 / 3.438 ms |
| Fleet, four ordinary windows | 0.609 / 0.694 ms | 4.024 / 4.329 ms |
| Fleet, four enlarged mixed ride windows | 5.624 / 5.634 ms | 9.081 / 9.112 ms |
| Dense town, yaw 90 / tilt 80, main view only | 0.486 / 0.536 ms | 3.133 / 3.790 ms |
| Dense town, yaw 90 / tilt 80, four ordinary windows | 0.639 / 0.748 ms | 3.962 / 5.162 ms |

Restoring text has a cost: ordinary-view mean CPU work increases by approximately 0.05-0.11 ms in these cases. The mixed ride case is effectively unchanged. All measured p95 presentation intervals remain below 16.7 ms. Rotated views perform a full sign-tree visit before clipping; large numbers of labels can cost more than these fixtures. The existing draw-tick measurements, GPU timings, memory and simulation tick rates are retained in the JSON evidence.

Evidence: [before](evidence/phase9/p5b/phase95b-perf-before-results.json), [final after](evidence/phase9/p5b/performance-after-results.json), rotated dense-town [before](evidence/phase9/p5b/phase95b-rotated-before-final-results.json) / [after](evidence/phase9/p5b/phase95b-rotated-after-final-results.json). The final mixed-window measurement uses `phase95b-mixed-final`; a preliminary mixed measurement that overlapped another launch is excluded.

A separate [GPU reference run](evidence/phase9/p5b/phase95b-gpu-final-results.json) passes: seven retained/unretained comparisons differ by at most **0.00036%**, seven cached-image references match exactly, and eight instanced/uninstanced comparisons match exactly. Its synchronous readback costs are excluded from the performance table. A five-second reference attempt completed no measured frames and was discarded; the accepted reference run uses twenty seconds.

## Reproduce

From the workspace root, using fresh run tags:

```powershell
.\tools\phase95b-labels.ps1 -RunTag labels-check-100 -Scale 100
.\tools\phase95b-labels.ps1 -RunTag labels-check-200 -Scale 200 -Blitter 40bpp-anim
.\tools\phase95b-labels.ps1 -RunTag labels-dense -Scale 100 -Dense `
  -FixtureSave 'D:/G ttd/.runtime/p96-town-final/save/p96-dense-town.sav'
.\tools\phase9-performance.ps1 -RunTag labels-perf -Cases closed,normal4,mixedlarge -Seconds 15
.\tools\phase9-performance.ps1 -RunTag labels-perf-rotated -Cases closed,normal4 `
  -FixtureSave 'D:/G ttd/.runtime/p96-town-final/save/p96-dense-town.sav' -Yaw 90 -Tilt 80 -Seconds 15
.\tools\phase9-performance.ps1 -RunTag labels-gpu -Cases mixedlarge -Seconds 20 -VerifyGPU
```

`renderer_3d labels inspect|click <tag>` is an explicitly invoked diagnostic. `fixturelabels` uses existing single-player commands to place a sign and rename a station in the isolated fixture. `labeleffects` adds presentation-only example text. Rendering does not call fixture commands. Simulation algorithms, saves and network protocols are unchanged.
