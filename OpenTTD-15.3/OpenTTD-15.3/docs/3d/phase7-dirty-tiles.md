# Phase 7 priority 1: dirty tiles inside chunks

Latest follow-up: [phase7-offscreen.md](phase7-offscreen.md) completes priority 2. The measurements and remaining costs below describe the earlier priority 1 checkpoint.

Status: priority 1 implemented and verified. The capped Release build, 108 tests, five live reference-checked scenarios and all 14 benchmark cases pass. This checkpoint covers the first of the five follow-ups in [phase7-tiles.md](phase7-tiles.md#next-performance-priorities-recorded-2026-10-16); priorities 2-5 and general Phase 7 release acceptance remain open.

## Implementation

Each terrain chunk now retains a coalesced set of dirty tile indices. Tile redraw notifications mark the affected tile and its surrounding 3x3 neighborhood, clipped at map boundaries and mapped into the actual chunk row width. This preserves shared-corner dependencies across 16/32-tile chunk boundaries. Repeated notifications read each affected snapshot once per refresh. Snapshot equality still controls geometry regeneration, so no-op notifications do not rebuild or upload unchanged geometry.

First appearance, map allocation/generation, same-sized reloads, enabling 3D, chunk-size changes and diagnostic mode changes still force complete initialization. Snapshot arrays are updated in place. The mask reserves 128 bytes per chunk, or 512 KiB for the masks on a 1024-square map with 16-tile chunks. All viewport, picking, visibility, CPU tile-mesh reuse and retained GPU behavior remains in place. No simulation, game command, authoritative tile, save or network behavior changes.

The new `renderer_3d performance tilecached` reference retains the previous policy of reading every snapshot in each dirty chunk while reusing unchanged tile geometry. The default `optimized` mode reads only marked snapshots. Both modes use the same final executable, snapshot storage, masks, mesh layout and GPU path; this isolates the snapshot refresh policy rather than replaying the preceding commit's exact binary. Existing `baseline`, `cached` and `chunked` controls remain available.

`renderer_3d verifydirty on` continues to independently read every authoritative tile after incremental refresh and compare snapshots, even in clean chunks. Any detected mismatch is a failure, although the diagnostic scan repairs it. Changed meshes are also independently regenerated and compared exactly, including ordered faces, tile/category metadata and bounds. `renderer_3d verifygpu on` retains the sampled same-state CPU/GPU image comparison. Both diagnostics are disabled for measurements.

## Regression coverage

The capped Release build and **108/108 CTest tests pass**. The new regression checks derived snapshots against an independent map reference after repeated, distant and no-op notifications; shared chunk corners; map edges; partial edge chunks; same-sized reloads; and 16/32/16-tile chunk resets. It requires exactly one snapshot read for each expected tile and no reads outside that set. It also deliberately omits a notification and requires the full-scan reference to detect the stale snapshots. The existing packed-mesh regression remains in place.

The final railway, construction, Arctic, Tropic and Toyland scenarios pass, including construction/removal, signals, climate/scenery updates, shared-corner raise/lower, selection/previews, visibility modes, camera/zoom changes, 16/32-tile chunks, multiple viewports, classic switching and same-process reloads. **18,766 full-map comparisons found zero missed chunks; 18,919 exact chunk-mesh comparisons found zero mismatches.** All **2,518 sampled CPU/GPU images** meet the existing tolerance; the largest difference is one pixel in a 1280x900 image. The construction AI reached `PHASE4 ROUTE_READY`. The restored multi-viewport, classic and reloaded captures were visually inspected. This is scripted evidence, not native mouse/DPI acceptance.

Evidence: [correctness totals](evidence/phase7-dirty-tiles/correctness.json), [build](evidence/phase7-dirty-tiles/build.txt), [tests](evidence/phase7-dirty-tiles/tests.txt), [environment/binary provenance](evidence/phase7-dirty-tiles/environment.json), and [source hashes](evidence/phase7-dirty-tiles/source-sha256.json). Full logs are compressed in the same directory. Actual captures: [restored](evidence/phase7-dirty-tiles/restored.png), [classic](evidence/phase7-dirty-tiles/classic.png), [reloaded](evidence/phase7-dirty-tiles/reloaded.png).

## Reproduce

Build using the capped command in [build_and_test.md](build_and_test.md), then run from the workspace root:

```powershell
foreach ($scene in @('railway','construction','arctic','tropic','toyland')) {
    .\tools\phase7-checks.ps1 -Scene $scene -RunTag phase7dirty
}
.\tools\phase7-benchmark.ps1 -RunTag phase7dirty -Modes tilecached,optimized -Windows 0,1,4
.\tools\phase7-benchmark.ps1 -RunTag phase7dirty -Modes tilecached,optimized -MapBits 7,9,10 -Windows 0
.\tools\phase7-benchmark.ps1 -RunTag phase7dirty -Modes tilecached,optimized -Windows 4 -Stress
```

`tiles_scanned` counts authoritative snapshot reads; `tiles_scan_candidates` counts all tiles in the visited chunks before filtering by the dirty tile set. The benchmark verifier requires equal counts in `tilecached`, fewer reads in `optimized`, and actual tile geometry reuse in both. `scan_us` still includes snapshot refresh, packed-mesh copying/rebuilding and moving-vehicle extraction; it is not snapshot extraction alone. Timing definitions, warm-up exclusion and fixture limits otherwise follow [phase7-tiles.md](phase7-tiles.md).

## Measured results (2026-10-16)

Windows x64 Release, RTX 3090 / NVIDIA 610.74, 1280x900, 32-bit optimized blitter, 16-tile chunks. Each pair is one sequential trial in the same final executable, with no compiler or correctness games running alongside it. Both verification diagnostics were off. The first five samples are discarded; each case retains at least 15. These are CPU drawing-pass wall times, not end-to-end FPS or confidence intervals. Large generated maps contain dense towns and industries; the operating fleet stress is a separate small-map fixture.

| Fixture | Tilecached mean ms | Dirty tiles mean ms | Before / after p95 ms | Samples before / after | Peak working set MiB before / after |
|---|---:|---:|---:|---:|---:|
| Railway, no vehicle windows | 9.04 | 6.50 | 16.92 / 15.15 | 450 / 451 | 182.6 / 182.6 |
| Railway, one window | 12.40 | 13.73 | 22.48 / 27.38 | 556 / 547 | 184.9 / 183.9 |
| Railway, four windows | 35.32 | 36.92 | 48.57 / 50.03 | 343 / 324 | 184.0 / 184.3 |
| 200 extra trucks, four windows | 32.96 | 34.11 | 48.03 / 48.52 | 370 / 363 | 189.5 / 188.1 |
| 128x128 generated | 7.13 | 6.31 | 10.55 / 10.06 | 31 / 31 | 179.0 / 195.7 |
| 512x512 generated | 20.20 | 19.10 | 36.41 / 32.81 | 26 / 26 | 388.0 / 388.3 |
| 1024x1024 generated | 68.63 | 48.83 | 128.03 / 90.11 | 31 / 31 | 1063.7 / 1064.8 |

At 512 square, authoritative snapshot reads fall **80,384 to 4,588.8 per pass (94.3%)**, and CPU snapshot/rebuild time falls **13.308 to 9.969 ms (25.1%)**. At 1024 square, reads fall **362,768.5 to 19,798.9 (94.5%)**, and CPU snapshot/rebuild time falls **61.099 to 42.543 ms (30.4%)**. Total mean drawing improves **5.4%** and **28.9%**, respectively. Optimized 1024-square chunks still contain an average 362,768.5 candidate tiles per pass; only their marked indices are read.

Small-map results remain mixed. One-window, four-window and stress mean drawing times worsen **1.331 ms (10.7%)**, **1.603 ms (4.5%)** and **1.153 ms (3.5%)** in these trials. Their CPU snapshot/rebuild times are **0.452 / 0.434**, **0.575 / 0.625** and **1.118 / 1.047 ms** before/after. Readback is **8.245 / 9.803**, **27.572 / 28.794** and **22.196 / 23.609 ms**. These measurements do not isolate the cause of the differences or establish a consistent multi-window improvement/regression. Components overlap total drawing and must not be added together. Reducing snapshot reads does not address synchronous readback.

The 128-square optimized process peaks **16.7 MiB higher** in this pair; the 512/1024-square differences are **0.3/1.1 MiB**. Both modes allocate the same masks and snapshot arrays. Working set includes CPU geometry, images, game state and driver allocations; these short sequential runs do not establish a stable memory reduction or long-session behavior. Whole-map CPU geometry remains retained; total process working set reaches about **1065 MiB** for 1024 square.

The remaining **42.54 ms** CPU snapshot/rebuild component at 1024 square is substantial. Offscreen rebuilding, packed-mesh copying and full changed-chunk uploads remain measured follow-up targets; this checkpoint does not isolate their individual costs or close the large-map/release gate. Performance results are a diagnostic policy comparison against `tilecached`, not an absolute comparison with earlier checkpoint timings.

See [all metrics](evidence/phase7-dirty-tiles/results.json), [retained per-pass samples](evidence/phase7-dirty-tiles/samples.csv), and compressed benchmark logs beside them.

## Remaining scope

Chunks whose snapshots change still copy their unchanged packed geometry; visible changed meshes upload in full. Whole-map CPU geometry storage, offscreen rebuilding, synchronous readback/compositing, broad screen invalidation and per-chunk draw submission remain. Priorities 2-5 are separate follow-ups. Native interaction acceptance, long-session memory stability, cross-machine performance, release packaging and final art remain separate gates.
