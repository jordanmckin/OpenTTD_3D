# Phase 7 priority 2: defer offscreen mesh rebuilding and bound retention

Status: priority 2 implemented and verified. Release build, 110 tests, six live correctness scenarios and all 16 benchmark cases pass. This checkpoint covers priority 2 of the [current roadmap](phase7-tiles.md#next-performance-priorities-recorded-2026-10-16). Priorities 3–5, native interaction acceptance and general release readiness remain separate.

## Implementation

Authoritative dirty-tile snapshots continue to refresh independently of visibility. Geometry changes accumulate in a separate per-chunk mask across refreshes. A viewport requests its current mesh only when it needs an uncached image. Changed tiles are regenerated from their latest snapshots; repeated offscreen changes coalesce. First appearance and re-entry after eviction regenerate all tile spans. Classic picking still uses the authoritative height inverse; rotated inspection picking prepares the requested camera's ground geometry before testing triangles.

Every request uses its own camera, including vehicle windows, secondary viewports and screenshots. Visibility uses the previous geometry bounds expanded by each changed snapshot's conservative footprint and elevation, including terrain slopes, foundations, bridge decks, infrastructure and compiled asset extents. Rebuilding tightens the bounds again. This preserves newly raised or enlarged content that extends into a viewport. Map allocation, same-sized reload, chunk-size changes and diagnostic policy changes reset the cache generation.

The default combined budget for CPU face/span allocations and retained static GPU vertices is **128 MiB**. Oldest unused chunks are evicted first; their CPU allocations and GPU buffers are released together on the GL context thread. Every active window viewport, including one not redrawn in the current clip, and every view requested in the current drawing pass is protected. Active views can exceed the budget: it is a soft bound rather than a reason to repeatedly rebuild visible chunks. Snapshot arrays, dirty masks, pending masks, readback images, scratch storage, game state and driver overhead are outside this geometry budget. Whole-map authoritative snapshots are deliberately retained, so this does not bound total process memory.

`renderer_3d performance eager` uses the preceding policy: dirty-tile snapshot reads and unchanged CPU tile reuse, but meshes for every changed chunk are rebuilt immediately and retained. `optimized` defers rebuilding and bounds retention. Both policies use the same executable and mesh layout; this is a diagnostic policy comparison rather than replaying the previous executable. Older performance modes remain available. No simulation, authoritative map, command, save or network behavior changes.

## Correctness checks

New regressions exercise accumulated changes across repeated/no-op refreshes, variable geometry growth/removal, eviction with unchanged snapshots, same-sized reload, oldest-first eviction and protection of several active views. Existing shared-corner, map-edge, 16/32-tile chunk and packed-mesh regressions remain.

`verifydirty` still compares every authoritative snapshot independently, including clean and deferred chunks. It also regenerates pending chunks transiently and checks that every vertex lies inside the conservative bounds, and compares every rebuilt packed mesh and its exact bounds against full regeneration. `verifygpu` now regenerates the entire scene for its sampled CPU reference, bypassing residency, pending masks and cached culling bounds. Both diagnostics are disabled in timing runs.

The capped Release build succeeds and **110/110 CTest tests pass**. Railway, construction, Arctic, Tropic, Toyland and the larger 128-square Arctic traversal pass their verifiers. **26,503 full-map snapshot comparisons, 28,757 exact mesh comparisons and 318,610 conservative-bound comparisons found zero errors.** All **2,879 sampled full-scene image comparisons** meet tolerance; the maximum difference is one pixel in a 1280x900 image. The construction AI reached `PHASE4 ROUTE_READY`. All four distant raise/lower commands at (104,104) succeeded, and the rotated re-entry screen pick returned real ground at (104,103). The restored multi-viewport, classic, reload and re-entry screenshots were visually inspected. These scripted checks do not establish native mouse/DPI acceptance.

## Reproduce

Use the capped Release build and CTest commands in [build_and_test.md](build_and_test.md). From the workspace root:

```powershell
foreach ($scene in @('railway','construction','arctic','tropic','toyland')) {
    .\tools\phase7-checks.ps1 -Scene $scene -RunTag phase7deferred
}
.\tools\phase7-checks.ps1 -Scene arctic -RunTag phase7deferred128 -MapBits 7 -Roam
.\tools\phase7-benchmark.ps1 -RunTag phase7deferred -Modes eager,optimized -Windows 0,1,4
.\tools\phase7-benchmark.ps1 -RunTag phase7deferred -Modes eager,optimized -MapBits 7,9,10 -Windows 0
.\tools\phase7-benchmark.ps1 -RunTag phase7deferred -Modes eager,optimized -Windows 4 -Stress
.\tools\phase7-benchmark.ps1 -RunTag phase7deferredpan -Modes eager,optimized -MapBits 9 -Windows 0 -Seconds 90 -Pan
```

The larger correctness fixture edits a distant chunk repeatedly, returns to it with a rotated camera, picks ground, changes zoom, preserves the secondary view and reloads. The pan measurement traverses sixteen positions distributed across the map and loops, alternating zoom 2/3 through ordinary user controls. It uses the existing fast-forward control equally in both policies. Standard timing definitions, warm-up exclusion and fixture limits follow [phase7-dirty-tiles.md](phase7-dirty-tiles.md).

## Measured results (2026-10-16)

Windows x64 Release, RTX 3090 / NVIDIA 610.74, 1280x900, 32-bit optimized blitter and 16-tile chunks. All 14 standard cases and both traversal cases pass their verifier. Each pair is one sequential trial in the same final executable, with no compiler or correctness game running alongside it. Verification diagnostics are off. The first five drawing samples are discarded, with at least 15 retained per case. These are drawing-pass wall times, not end-to-end FPS or statistical confidence intervals. Large generated maps contain dense towns and industries; the 200-truck operating stress is a separate small-map fixture. Simulation continues during the trials.

| Fixture | Eager mean ms | Deferred mean ms | Before / after p95 ms | Samples before / after | Peak working set MiB before / after |
|---|---:|---:|---:|---:|---:|
| Railway, no vehicle windows | 4.176 | 4.105 | 6.651 / 6.179 | 468 / 476 | 182.9 / 183.0 |
| Railway, one window | 4.013 | 4.657 | 7.601 / 8.440 | 632 / 623 | 184.8 / 184.8 |
| Railway, four windows | 5.514 | 6.920 | 13.827 / 12.835 | 833 / 831 | 183.9 / 184.4 |
| 200 extra trucks, four windows | 11.444 | 10.808 | 15.343 / 14.708 | 937 / 929 | 194.1 / 188.7 |
| 128×128 generated | 5.667 | 4.808 | 8.367 / 5.943 | 31 / 31 | 188.5 / 192.1 |
| 512×512 generated | 12.661 | 6.713 | 23.951 / 8.962 | 26 / 26 | 385.8 / 218.1 |
| 1024×1024 generated | 40.406 | 9.315 | 74.356 / 14.494 | 31 / 31 | 1057.8 / 289.1 |

At 512 square, mean drawing improves **47.0%** and mesh preparation falls **5.742 to 0.160 ms**. CPU face/span storage falls **168.745 to 5.382 MiB**, with **1024 / 28** resident chunks at their recorded maxima. At 1024 square, mean drawing improves **76.9%**, mesh preparation falls **30.332 to 0.354 ms**, and CPU face/span storage falls **758.443 to 5.403 MiB**. Resident chunk maxima are **4096 / 30**. Sampled process working set falls **72.7%** at 1024 square.

Authoritative snapshot reads remain essentially identical: about **19,797.8 per pass** at 1024 square. The snapshot/mesh/vehicle component falls **33.851 to 3.842 ms**. Mesh patches fall **805.5 to 2.2 per pass**; static uploads remain **711.056 / 711.056 KiB**. This isolates the benefit of deferring CPU geometry work and allocation: existing visibility culling already avoided uploading offscreen chunks. Full changed-chunk copying and visible uploads remain.

The first measured 1024-square drawing pass falls **991.004 to 112.058 ms**, and the 512-square pass falls **245.592 to 46.954 ms**. These initialization samples include snapshot initialization, required meshes, rendering and readback, and are excluded from the steady-state table. They are not map-loading or input-latency measurements.

Small-map/window results remain mixed. The one-window mean worsens **0.644 ms (16.0%)** and the four-window mean worsens **1.406 ms (25.5%)** in this pair. Their snapshot/mesh/vehicle components are **0.235 / 0.296** and **0.240 / 0.263 ms**; readback is **1.576 / 2.067** and **2.400 / 3.244 ms**. Components overlap total drawing and must not be added together. These sequential trials do not establish a consistent window improvement or isolate the cause of the timing differences. The 128-square working set increases 3.6 MiB despite lower CPU geometry allocation; process working set also includes game, image and driver allocations. No stable small-map memory reduction is claimed.

### Pan, zoom and retention

Both policies traverse the same sixteen map positions with zoom changes for 90 seconds, looping back to earlier regions under ordinary fast-forward controls. Games continue to develop, so these wall-clock trials do not guarantee identical simulated dates at each camera transition. The optimized verifier requires at least sixteen distinct view keys, a completed traversal and return, actual eviction and cold rebuilding.

| 512-square traversal | Eager | Deferred |
|---|---:|---:|
| Retained drawing samples | 3374 | 3557 |
| Mean drawing ms | 8.681 | 5.705 |
| p95 drawing ms | 13.218 | 7.307 |
| Peak sampled working set MiB | 587.1 | 382.2 |
| Peak combined retained CPU/GPU mesh MiB | 345.600 | 127.999 |
| Released chunk allocations after warm-up | 0 | 475 |

The deferred traversal contains **30 drawing passes with cold geometry** after warm-up. Their mean drawing time is **14.406 ms**, with a maximum of **23.146 ms**. These are actual drawing-pass costs when generating first-use or evicted geometry, including rendering/readback and concurrent work in the pass; they are not native mouse-to-display latency or a clean isolation of meshing alone. A transient pan/zoom cost remains even when steady drawing improves. The recorded retained mesh maximum evaluates the 128 MiB policy on this traversal; active views remain permitted to exceed it. This short loop does not establish long-session allocator stability or a universal budget for final art.

Evidence: [all metrics](evidence/phase7-offscreen/results.json), [standard per-pass samples](evidence/phase7-offscreen/phase7deferred-samples.csv), [traversal samples](evidence/phase7-offscreen/phase7deferredpan-samples.csv), [correctness totals](evidence/phase7-offscreen/correctness.json), [build](evidence/phase7-offscreen/build.txt), [tests](evidence/phase7-offscreen/tests.txt), [binary/environment provenance](evidence/phase7-offscreen/environment.json), and [source/tool hashes](evidence/phase7-offscreen/source-sha256.json). Full logs are compressed beside them. Actual captures: [restored viewports](evidence/phase7-offscreen/restored.png), [classic fallback](evidence/phase7-offscreen/classic.png), [reload](evidence/phase7-offscreen/reloaded.png), [rotated re-entry](evidence/phase7-offscreen/reentry.png).

## Measurement definitions and remaining costs

`scan_us` includes snapshot refresh, demanded mesh preparation and moving-vehicle extraction. `mesh_us` isolates mesh preparation, including visibility traversal and packed-mesh rebuilding; it overlaps `scan_us`. `chunks_rebuilt` counts actual mesh patches, `pending_chunks` counts chunks with accumulated changes, and `cold_chunks` counts full regenerations on first use or after eviction. `cpu_mesh_bytes` uses face/span vector capacities; `retained_bytes` counts static GPU vertex storage. `evictions` counts released chunk allocations. These are per drawing pass; the existing tile read/rebuild/reuse counters remain available. Cold-frame drawing latency includes rendering/readback and other work in that pass, not just rebuilding. Drawing-pass wall time is not end-to-end FPS or input-to-display latency.

Visible changed chunks still copy packed geometry and upload their complete meshes. Dirty notifications still refresh offscreen snapshots and can invalidate screen images broadly. GPU readback remains synchronous. First-use mesh generation and uploads can cause pan/zoom spikes; steady-state improvements must be read alongside their latency and memory measurements. Native mouse/DPI acceptance, long-session stability, cross-machine validation, packaging and final art remain open.
