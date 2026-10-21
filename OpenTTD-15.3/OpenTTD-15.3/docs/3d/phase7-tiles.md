# Phase 7: reuse unchanged tile geometry inside dirty chunks

Latest follow-up: [offscreen mesh rebuilding and retention](phase7-offscreen.md) completes priority 2, following [dirty tiles inside chunks](phase7-dirty-tiles.md) for priority 1. The measurements on this page describe the earlier CPU tile-geometry checkpoint.

Status: implementation and verification complete for this CPU tile-geometry follow-up. The capped Release build, 107 tests, five live correctness scenarios and all 14 benchmark cases pass their verifiers. General Phase 7 release acceptance remains open.

## Scope and implementation

The previous checkpoint (`9b63bad`) completed dirty-chunk notifications and retained GPU geometry. It still regenerated **every tile's geometry** when one snapshot changed within a chunk. This follow-up caches the face range and bounds of each tile in the packed CPU chunk mesh. Snapshot equality determines which tiles need regeneration. Unchanged face ranges are copied in their original order; changed ranges are regenerated, allowing their face counts to grow, shrink or become empty. Chunk bounds are combined from the tile bounds, including tightening after removal. A shared scratch vector is used across chunks within a refresh, rather than allocating one face vector per map tile. Each chunk retains its own backing allocation; the scratch buffer is copied back, preventing dense-chunk capacity from propagating into sparse chunks. The regression also covers this allocation behavior.

Dirty notifications, shared-corner coverage, map reloads, chunk-size resets, retained GPU buffers, camera transforms and moving vehicles retain their existing behavior. A changed chunk still uploads its complete packed mesh. Dirty chunks still read all of their authoritative tile snapshots. Simulation timing, commands, authoritative map contents, saves and network messages are unaffected.

`renderer_3d performance chunked` retains static GPU buffers but regenerates every tile in each changed chunk. `optimized` is the default and reuses unchanged tile geometry. Both use the same executable, packed mesh layout and per-tile metadata, isolating the regeneration policy. Older `baseline` and `cached` diagnostic modes remain available.

## Correctness validation

The new packed-mesh regression repeatedly changes adjacent and separated tile spans, including empty geometry, different vertices with equal face counts, growth, removal and shrinking bounds. It compares the complete ordered mesh against full regeneration and checks that unchanged tiles do not call the builder.

With `renderer_3d verifydirty on`, every changed chunk is also independently regenerated in full and compared exactly, including vertices, colours, face order, tile/category metadata and bounds. This catches cache errors that a CPU/GPU image comparison would share. The existing full-map authoritative snapshot reference and sampled CPU/GPU image comparison remain enabled in live checks and disabled in timing runs.

The capped Release build succeeds and **107/107 CTest tests pass**. Railway, construction, Arctic, Tropic and Toyland scenarios completed, including same-process reloads, 16/32-tile chunks, camera changes, selection/previews and structure visibility modes. Across them, **18,976 exact chunk-mesh comparisons** and **19,058 full-map snapshot comparisons** found zero mesh mismatches or missed chunks. **2,641 sampled images** matched the CPU reference within the existing tolerance; the largest difference was one pixel in a 1280x900 image. The construction AI reached `PHASE4 ROUTE_READY`. Actual restored multi-viewport, classic fallback and reloaded-map screenshots were visually inspected. These scripted checks do not establish native mouse/DPI acceptance.

Evidence: [correctness totals](evidence/phase7-tiles/correctness.json), [build](evidence/phase7-tiles/build.txt), [tests](evidence/phase7-tiles/tests.txt), [binary/environment provenance](evidence/phase7-tiles/environment.json), and [changed source hashes](evidence/phase7-tiles/source-sha256.json). The full correctness logs are compressed beside them. Actual captures: [restored viewports](evidence/phase7-tiles/restored.png), [classic fallback](evidence/phase7-tiles/classic.png), [reloaded map](evidence/phase7-tiles/reloaded.png).

## Reproduce

Use the capped Release build command in [build_and_test.md](build_and_test.md), then run from the workspace root:

```powershell
foreach ($scene in @('railway','construction','arctic','tropic','toyland')) {
    .\tools\phase7-checks.ps1 -Scene $scene -RunTag phase7tiles
}
.\tools\phase7-benchmark.ps1 -RunTag phase7tiles -Modes chunked,optimized -Windows 0,1,4
.\tools\phase7-benchmark.ps1 -RunTag phase7tiles -Modes chunked,optimized -MapBits 7,9,10 -Windows 0
.\tools\phase7-benchmark.ps1 -RunTag phase7tiles -Modes chunked,optimized -Windows 4 -Stress
```

Benchmark definitions, warm-up exclusion and fixture limits follow [phase7-retained.md](phase7-retained.md). `tiles_rebuilt` counts tile geometry builders; `tiles_reused` counts unchanged tile spans copied inside changed chunks. Neither includes chunks whose snapshots are entirely unchanged. Times are drawing-pass wall times, not end-to-end FPS. Each pair is a sequential trial on this workstation, not a statistical confidence interval.

## Measured results (2026-10-16)

All 14 cases pass the benchmark verifier, including checks that the reference rebuilds all changed-chunk tiles and the optimized path actually reuses tile spans. Each pair uses the same final Release executable. The `chunked` reference uses the same per-tile metadata and scratch/copy-back layout as `optimized`, with every tile marked for regeneration; it is a diagnostic policy comparison rather than the previous commit's identical implementation. No compiler or correctness games ran alongside the benchmarks. The first five drawing samples were discarded, with at least 15 retained per case. Early exploratory timings from before the allocation fix were discarded; the final five correctness scenarios and all benchmarks use the corrected build.

| Fixture | Chunked mean ms | Tile reuse mean ms | Chunked / reuse p95 ms | Samples chunked / reuse |
|---|---:|---:|---:|---:|
| Railway, no vehicle windows | 4.59 | 4.49 | 6.88 / 6.69 | 447 / 455 |
| Railway, one window | 5.24 | 4.86 | 9.06 / 8.55 | 614 / 611 |
| Railway, four windows | 5.78 | 6.21 | 11.17 / 11.83 | 790 / 795 |
| 200 extra trucks, four windows | 9.43 | 9.92 | 13.05 / 13.03 | 933 / 929 |
| 128x128 generated | 5.36 | 4.70 | 7.17 / 6.02 | 31 / 31 |
| 512x512 generated | 46.39 | 15.94 | 106.88 / 30.07 | 26 / 26 |
| 1024x1024 generated | 215.17 | 57.28 | 414.50 / 111.39 | 25 / 31 |

Mean drawing time improved **66% at 512 square** and **73% at 1024 square**. Snapshot/rebuild time fell **41.029 to 10.781 ms** and **209.140 to 51.600 ms**, respectively. At 512 square, the optimized path regenerated an average **266.8 tile meshes** and reused **46,246.5 tile spans** per pass. At 1024 square it regenerated **1,122.9** and reused **205,097.5**. About **99.4% of tile spans inside changed chunks** were reused in these cases.

Small-map results are mixed: the four-window and stress means worsened **0.437 ms (7.6%)** and **0.488 ms (5.2%)** in these sequential trials. CPU snapshot/rebuild time still fell **0.265 to 0.246 ms** and **1.114 to 0.756 ms**. Readback increased **2.963 to 3.379 ms** and **2.893 to 3.875 ms**; these components overlap total drawing and do not by themselves prove the cause. This single trial does not establish a consistent small-map/window improvement or distinguish a reproducible regression from run-to-run timing variation.

Peak working set was **387.4 / 387.0 MiB** at 512 square and **1053.3 / 1058.6 MiB** at 1024 square. The x64 tile-span metadata costs 32 bytes per tile (32 MiB for a 1024-square map), present in both comparison modes; these short runs do not establish long-session memory stability. Static uploads remain essentially unchanged: whole changed chunks still upload, even when most CPU tile geometry is reused.

The 1024-square optimized pass still averages **57.28 ms**, including **51.60 ms** of CPU snapshot/rebuild work. Dirty chunks read an average **362,768.5 authoritative tile snapshots** per pass there. Further large-map work should profile dirty-tile snapshot extraction and packed-mesh copying, rather than assuming the remaining cost is GPU rendering. Readback/compositing remains a separate small-map/window target. No general large-map or release-readiness gate is closed by this checkpoint.

See [all metrics](evidence/phase7-tiles/results.json), [per-pass samples](evidence/phase7-tiles/samples.csv), and the compressed benchmark logs in the same directory.

## Remaining limits

Whole-map CPU geometry storage, snapshots of every tile in a dirty chunk, copying unchanged face ranges inside a changed chunk, complete changed-chunk uploads, synchronous GPU readback, screen invalidation and per-chunk draw submission remain. Native interaction acceptance, long-session memory stability, cross-machine validation, packaging and final art remain separate gates.

## Next performance priorities (recorded 2026-10-16)

Status: priorities 1–2 are implemented and verified in [phase7-dirty-tiles.md](phase7-dirty-tiles.md) and [phase7-offscreen.md](phase7-offscreen.md). Priorities 3–5 remain planned, in the order below. They build on the completed GPU-retention and CPU tile-geometry reuse checkpoints above.

1. **Track dirty tiles within chunks (complete).** Refresh authoritative snapshots only for affected tiles, including all shared-corner neighbors, instead of scanning every tile in a dirty chunk. The earlier 1024-square benchmark read about 362,769 snapshots per pass to regenerate about 1,123 tile meshes, with CPU snapshot/rebuild work accounting for 51.60 of 57.28 ms. Map generation/reload and chunk-size invalidation, independent full-map snapshots and full-mesh references are preserved. See [the implementation and measured results](phase7-dirty-tiles.md).

2. **Defer offscreen mesh rebuilding (complete).** Coalesce changed tile geometry outside active views and build the latest state when a viewport or rotated pick needs it. Conservative bounds cover raised terrain and enlarged structures. A 128 MiB combined CPU/GPU mesh budget evicts unused chunks while protecting every active viewport. Six live scenarios and 16 benchmark cases pass, including large maps, multiple windows, re-entry, reload and actual eviction. Working set and cold pan/zoom costs are recorded in [phase7-offscreen.md](phase7-offscreen.md); snapshots remain whole-map and active views may exceed the soft geometry budget.

3. **Patch geometry more narrowly.** Replace changed tile ranges in CPU meshes and GPU buffers rather than copying and uploading an entire changed chunk. Profile the CPU copying and GPU upload components separately. Evaluate a bounded allocation/range strategy for geometry whose face counts grow, shrink or become empty; preserve face order where needed, bounds, selection/visibility metadata and depth behavior. Avoid transferring dense-chunk allocation capacity into sparse chunks, and measure fragmentation and memory growth over longer sessions.

4. **Reduce GPU readback and compositing costs.** Profile synchronous readback and CPU/UI compositing with zero, one and four vehicle windows and the 200-truck stress fixture. Evaluate asynchronous readback or more direct GPU compositing where the measurements justify it. Preserve original window ordering, clipping, screenshots, cursor/tooltip presentation and classic fallback; do not trade accurate current-state captures for stale viewport images. The latest small-map/window results are mixed, so compare repeated trials before claiming a consistent gain.

5. **Invalidate smaller screen regions.** Replace broad screen invalidation after a localized world change with affected regions in each active viewport where practical. Cover old and new projected bounds for removed, raised or enlarged structures, overlapping windows, zoom/camera changes and visibility changes. Verify that distant/offscreen scenery changes avoid unnecessary redraws while terrain edits, selections and moving objects leave no stale pixels.

For each implemented follow-up, record a separate passing checkpoint with appropriate regression coverage, live reference comparisons, before/after timings and memory measurements. Reuse the established large-map and multi-window fixtures and record regressions as well as improvements. Preserve authoritative simulation timing, map contents, game commands, saves and network behavior throughout.
