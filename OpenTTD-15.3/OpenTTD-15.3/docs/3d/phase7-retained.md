# Phase 7 priorities 1 and 2: incremental terrain and retained geometry

Status: recorded priorities 1 and 2 implemented and verified. This checkpoint does not close the remaining Phase 7 release, Phase 6 native-interaction, or Phase 8 art gates.

## Implementation

The renderer now tracks dirty chunks from `MarkTileDirtyByTile`, including the neighboring tiles that share terrain corners. Random tree creation has an additional presentation-only notification because that path does not immediately request a classic sprite redraw. Map allocation, including same-sized reloads, resets the snapshots. Enabling 3D and changing chunk size also reset them. Invalidation clears the drawing-pass snapshot flag so screenshots requested outside the regular window drawing pass cannot reuse an empty or stale snapshot.

Only dirty chunks read authoritative tile snapshots. Snapshot equality still decides whether a mesh actually changes. The chunk list is traversed for dirty flags and view culling; this is not a spatial-index implementation. Game commands, tile contents, simulation timing, random numbers, saves and network messages remain unchanged.

Visible static chunk meshes are uploaded lazily into OpenGL buffers and retained across viewports and frames. Monotonic mesh revisions trigger replacement uploads. Reloads and chunk-size changes discard the old GPU generation; context destruction deletes all buffers. Camera projection, tile highlighting, rectangular selection, transparency and invisibility use shader uniforms and per-face tile/category metadata. Rail previews and moving vehicles remain a separate compact CPU-projected stream. All geometry uses the same depth buffer, and synchronous readback preserves existing CPU screenshots and UI compositing.

## References and diagnostic controls

- `renderer_3d performance baseline`: original small image cache, repeated scans and framebuffer resizing, with CPU projection.
- `renderer_3d performance cached`: the previous Phase 7 optimization (larger image cache, one full scan per drawing pass, reusable framebuffer), with CPU projection. This is the before-reference for these two priorities.
- `renderer_3d performance optimized`: dirty-chunk refresh and retained GPU geometry; the default.
- `renderer_3d verifydirty on`: after incremental refresh, independently scan every tile and report any missed changed chunk. A mismatch is a failure even though the diagnostic reference scan repairs it.
- `renderer_3d verifygpu on`: on every sixteenth drawing pass, render sampled views again using CPU projection and compare the readback pixels at identical simulation state. These verification runs are excluded from performance measurements.

Use `-d driver=1` for correctness logs and `-d driver=2` for performance logs. Both verifiers must be off when benchmarking.

## Reproduction

From the workspace root:

```powershell
foreach ($scene in @('railway','construction','arctic','tropic','toyland')) {
    .\tools\phase7-checks.ps1 -Scene $scene
}
.\tools\phase7-benchmark.ps1 -RunTag phase7retained -Modes cached,optimized -Windows 0,1,4
.\tools\phase7-benchmark.ps1 -RunTag phase7retained -Modes cached,optimized -MapBits 7,9,10 -Windows 0
.\tools\phase7-benchmark.ps1 -RunTag phase7retained -Modes cached,optimized -Windows 4 -Stress
```

The correctness scripts exercise shared-corner terrain raise/lower, rail previews, highlights, solid/transparent/hidden structures, camera yaw/tilt/zoom, 16/32-tile chunks, multiple viewports, classic switching and same-process save/reload. The construction case builds the existing infrastructure AI fixture through normal commands. The climate cases use generated hilly maps. The verifier requires fresh screenshots with visible world geometry, in addition to snapshot and same-state pixel comparisons. CPU/GPU rasterization may differ at floating-point edges; the automated limit is less than 0.5% of pixels differing by more than two colour levels.

## Correctness results (2026-10-16)

The final capped Release build succeeds and **106/106 CTest tests pass**. Five live scenarios completed, including same-process reloads: **14,222 full-map reference comparisons found zero missed chunks**, and **2,145 sampled images matched the CPU reference within the stated tolerance**. The largest difference was one pixel in a 1280x900 image; the other four scenarios had no differing pixels. The construction AI reached `PHASE4 ROUTE_READY` and reported no fixture failures. Shared-corner raise/lower succeeded at tile (32,32), including the expected authoritative height changes.

The initial reference run exposed spontaneous tree creation without a redraw notification; the added notification fixes it. Visual inspection also exposed a screenshot taken immediately after chunk-cache reset; resetting the drawing-pass refresh flag fixes that path. Failed exploratory runs are not included in the passing results. The final verifier additionally checks that fresh captures contain world geometry.

Evidence: [correctness totals](evidence/phase7-retained/correctness.json), [build](evidence/phase7-retained/build.txt), [tests](evidence/phase7-retained/tests.txt), and [binary/environment provenance](evidence/phase7-retained/environment.txt). Compressed full correctness logs are retained in the same directory. The [restored multi-viewport scene](evidence/phase7-retained/restored.png), [classic fallback](evidence/phase7-retained/classic.png), and [reloaded scene](evidence/phase7-retained/reloaded.png) are actual game captures. The restored and classic captures were visually inspected; this is scripted evidence, not native mouse/DPI acceptance.

## Measurement definitions

All before/after cases use the same final instrumented Release executable, machine, resolution and fixture. `cached` and `optimized` share the compact CPU-stream vertex format. Static retained vertices additionally carry tile/category metadata. First five drawing samples are discarded; at least fifteen remaining samples are required. Runs are sequential, with other test games and builds stopped.

`scan_us` includes terrain snapshot comparison/rebuild and moving-vehicle extraction. `projection_us` covers CPU vertex preparation and chunk culling. `upload_us` covers packing changed static vertices and buffer uploads. `prepare_us` includes preparation and submission, and overlaps these components; do not sum overlapping fields. `gpu_ns` now spans the geometry submission interval, including intervening changed-buffer uploads/driver gaps, and excludes clear/readback/UI presentation. It is not directly comparable to the older triangles-only GPU figures in phase7.md. `retained_bytes` counts static GPU vertex-buffer payloads; process working set also includes CPU snapshots, images, driver allocations and other game memory. None of these values is an end-to-end FPS measurement.

## Measured results (2026-10-16)

All 14 cases pass the benchmark verifier. Each pair is one sequential trial, not a statistical confidence interval. Times are drawing-pass wall times, not FPS.

| Fixture | Cached mean ms | Retained mean ms | Cached / retained p95 ms | Samples cached / retained |
|---|---:|---:|---:|---:|
| Railway, no vehicle windows | 13.09 | 5.31 | 15.96 / 7.63 | 449 / 457 |
| Railway, one window | 15.58 | 5.31 | 22.99 / 9.27 | 576 / 602 |
| Railway, four windows | 28.81 | 5.92 | 37.07 / 12.07 | 494 / 831 |
| 200 extra trucks, four windows | 34.43 | 9.95 | 41.02 / 12.57 | 422 / 933 |
| 128x128 generated | 9.67 | 5.14 | 12.03 / 6.61 | 31 / 31 |
| 512x512 generated | 56.25 | 43.98 | 107.62 / 101.00 | 26 / 26 |
| 1024x1024 generated | 254.34 | 203.70 | 423.14 / 400.78 | 26 / 27 |

Four-window mean drawing time improved **79%**, and the 200-truck stress improved **71%**. In the four-window case, CPU projection fell from **14.981 to 0.492 ms**, upload preparation/upload from **2.240 to 0.085 ms**, and GPU submission-interval time from **6.019 to 0.925 ms**. Total uploads fell from **16.69 to 0.265 MiB per pass**; the retained static payload peaked at **12.256 MiB**. Working set was **195.5 / 185.3 MiB** before/after. The stress case retained 12.412 MiB and used 190.1 MiB working set.

On 512x512, average tiles read dropped from **262,144 to 80,571** per pass; snapshot/rebuild time fell from **48.503 to 38.804 ms**. On 1024x1024, snapshot/rebuild still averaged **198.597 ms** and total drawing **203.704 ms**, versus **248.218 / 254.343 ms** in the cached reference. Working set reached **1044 MiB**, including whole-map CPU geometry; retained GPU payload was only **7.693 MiB** in that view. Distributed scenery changes still dirty many chunks and rebuilding their geometry dominates these large generated scenes. **This is not acceptable general large-map performance**, despite eliminating unconditional full-map polling and repeated static projection/uploads.

The next measured optimization target is CPU rebuilding of frequently changing chunks (for example, avoiding rebuilding unaffected tile geometry inside a dirty chunk). Readback remains material in the railway cases. Neither observation changes simulation timing or expands this checkpoint into final release acceptance.

See [complete metrics](evidence/phase7-retained/results.json), [per-pass samples](evidence/phase7-retained/samples.csv), and compressed benchmark logs beside them.

## Remaining Phase 7 limits

Synchronous readback, whole-screen invalidation on actual terrain changes, CPU storage for whole-map meshes, and per-chunk draw submission remain. The large generated benchmarks have towns and industries but no operating vehicle fleet; the 200-truck fleet stress is a separate small-map case. Native mouse/DPI acceptance, long-running memory stability, cross-machine results, final art and general release readiness remain separate work.
