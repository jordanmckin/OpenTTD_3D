# Phase 7: performance and release readiness

Latest (2026-10-19): retained static instance streams and variable model slots are implemented; final Release and **118/118 tests pass**. Broad visual checks passed before the final duplicate-write cleanup. Preliminary four-window fleet drawing improves **7.08 to 5.58 ms**, with instance uploads **1649 to 130 KiB/pass**. Final post-cleanup visual/timing reruns were stopped at the user's request to finish the session. See [phase7-streams.md](phase7-streams.md) for verified evidence and exact resume commands. General release acceptance remains open.

## Second performance pass (recorded 2026-10-18)

The user reopened Phase 7 before closing Phase 8 because frame rate is still poor in a running game. Every earlier benchmark used Phase 5 placeholder art; Phase 8 added ~4,000-triangle vehicles, textured ground, animated effects and about 450 library models. A code review found that `RefreshTrains3D` and `RefreshEffects3D` (`src/video/rail3d_impl.h`) clear the whole image cache and mark the whole screen dirty whenever any vehicle or effect changes anywhere on the map, so every viewport, including every vehicle window, re-renders and reads back each frame while anything moves.

New priorities, continuing the numbering of [the earlier roadmap](phase7-tiles.md#next-performance-priorities-recorded-2026-10-16), in execution order:

**Priority 6 result (2026-10-18):** see [phase7-rebaseline.md](phase7-rebaseline.md). At the user's 3840×2160 display, the cost is per-pixel CPU readback, compositing and upload, repeated for every view on each game tick. Triangle and GPU time are small. The execution order is now **8, 7**, then 12, 9, 10, 11, re-measured after each.

**Priority 8 result (2026-10-18):** see [phase7-direct.md](phase7-direct.md). On-screen views now render into GPU textures composited beneath the 2D UI; vehicle movement re-renders them on the GPU without redrawing the UI. At 3840×2160 with the 60 Hz cap, CPU work per frame falls 12.3 → 5.4 ms with no windows and 18.0 → 6.6 ms with four, which now hold 60 FPS (from 52.5). Uncapped, four windows rise from 58 to 242 FPS. The remaining capped spikes are whole-chunk re-uploads after animated-tile changes (priorities 12 and 3). Next: priority 7.

**Priority 12 result (2026-10-18):** see [phase7-p12.md](phase7-p12.md). The tile changes are real (grass density, tree growth, industry animation frames), so none are skipped; instead a changed tile now rewrites only its own slot in the chunk's GPU buffer and is patched in place on the CPU. In the 4K fleet, chunk uploads fall from 12.2 to 0.7 MB per drawing pass, the 3D drawing pass from 8.8 to 3.4 ms, and frames over 10 ms of CPU work from 60% to 11%. This covers the chunk re-upload part of priority 3. Next: priority 7.

**Priority 7 result (2026-10-18):** see [phase7-p7.md](phase7-p7.md). Vehicle, effect and tile changes now re-render only the views whose camera can see them; images kept through a change match fresh renders exactly in all three correctness scenes. With four vehicle windows, views are re-rendered 13–29% less often and the 3D drawing pass is 0.4–0.6 ms shorter, but frame times are unchanged within noise, because in a running game every open view sees a change on almost every tick. Next: priority 9.

**Priority 9 result (2026-10-18):** Priority 9 is implemented and measured: [instanced vehicles and effects](phase7-p9.md), cached shader locations and a separate model program. The Release build, 115 tests, three live correctness scenes, a 4K direct-layer check and ten final/reference benchmark cases pass. Fleet model draw calls fall 76–82%; timing gains are smaller, and capped FPS stays at 60 in the final runs. General release gates remain open. Next: priority 10 (LOD), with static library instancing (11) still targeting the large retained geometry footprint.

**Priority 10 result (2026-10-18):** see [phase7-p10.md](phase7-p10.md). The converter generates reduced meshes for vehicles, effects and moving industry parts. Each viewport selects them using a half-pixel projected vertex-displacement limit and retains full detail close up. Runtime switching, the uniform fallback, independent CPU references, cached images and reloads are verified. The fleet uses 20-23% fewer model triangles, but four-window timing regresses in the original and reverse-order pairs and model storage increases 20 MiB. Keep full detail as the default; visual approval alone is not a performance benefit. Static library instancing is next, as priority 11.

**Priority 11 result (2026-10-19):** Priority 11 shares static library models and uses 36-byte model vertices. In the 512-square fleet, GPU chunk allocation falls about 962 to 239 MiB and CPU mesh/list storage 425 to 122 MiB. All 16 final cases hold 60 FPS; fleet CPU work increases modestly, so this is a memory optimisation rather than a general FPS gain. Release, 117 tests, live scene references and the final 4K layer check pass. See [phase7-p11.md](phase7-p11.md). Full detail remains the default and LOD stays opt-in; general release gates remain open.

6. **Re-baseline with the Phase 8 art (measured).** Re-run the benchmark cases on the current build. Add an end-to-end frame-time measurement (present-to-present interval, not only draw-pass CPU time) and a large map with an operating fleet, as the existing 512/1024-square cases have no vehicles. Break down where the frame goes: snapshots, chunk rebuilds, uploads, draw submission, GPU time, readback and compositing. The results confirm or reorder priorities 7–12.
7. **Scope vehicle and effect invalidation to the views that see it (done, [phase7-p7.md](phase7-p7.md)).** Compare old and new instance bounds against each viewport's camera and invalidate only the views (and, where practical, the screen regions) they touch. Moving objects off-screen must not redraw views. This takes over the moving-object part of priority 5.
8. **Remove the synchronous readback from the frame (done, [phase7-direct.md](phase7-direct.md)).** First step: double-buffered pixel-buffer readback so `glReadPixels` no longer stalls. The target is drawing the 3D view directly into the backend's framebuffer beneath the 2D UI. Window ordering, clipping, screenshots, cursor and classic fallback are preserved, and images are never stale. This is the concrete form of priority 4.
9. **Instanced draws for vehicles, effects and industry parts (done, [phase7-p9.md](phase7-p9.md)).** Consecutive visible instances sharing a model draw from a streamed instance buffer with `glDrawArraysInstanced`, preserving scene order. Shader locations are cached when each program links.
10. **Vehicle and model LOD (evaluated as an opt-in candidate; measured default remains full detail, [phase7-p10.md](phase7-p10.md)).** Generate reduced meshes in the converter and select them by zoom and projected size, keeping silhouettes and company colours. This is the "LOD before cutting detail" step from Phase 8.5; the user approves the reduced models.
11. **Share static library art (done, [phase7-p11.md](phase7-p11.md)).** Affine houses, trees, industry pieces, objects and station/depot art draw from shared models through per-chunk placement lists. Deformed and rail library geometry stays baked. Compact 36-byte model vertices are implemented; lossless indexing is evaluated as a further 4.5 MiB saving, without adding an indexed draw path.
12. **Animated-tile churn (done, [phase7-p12.md](phase7-p12.md)).** `MarkTileDirtyByTile` (`src/viewport.cpp`) feeds 3D dirty tracking and is called constantly for animated tiles (industries, houses, crossings, water). Use priority 6's measurements to confirm whether these calls cause snapshot reads, chunk rebuilds or full redraws without a visible change, and skip them where nothing in 3D changed.

Priorities 3 and 5 stay open. After priority 11, re-profile remaining chunk/list rebuilding and per-view instance grouping/uploads before narrowing more updates; partial screen redraws remain priority 5. Each priority is recorded as its own passing checkpoint, with live reference comparisons and before/after timings. Simulation, saves, commands and network behaviour stay unchanged.

## Earlier checkpoints

Status: recorded priorities 1 and 2 are now implemented and verified: dirty-chunk tracking and retained GPU geometry. See [the follow-up report](phase7-retained.md) for 106 passing tests, live correctness comparisons and all 14 before/after benchmarks. Large-map mesh rebuilding remains expensive; this is not general release acceptance. The first-pass report below is retained as historical evidence.

## Changes

The old two-image FIFO could evict the main view between clipped draw calls when several vehicle windows were open. The cache now retains up to 32 images with a 128 MiB pixel-data budget. Terrain and vehicle snapshots refresh once per `UpdateWindows` drawing pass, rather than once per clipped viewport rectangle. Game state is locked during drawing; diagnostic and inspection calls retain their explicit refreshes. No tick, vehicle movement, command, save or network behavior changes.

The optimized framebuffer grows to accommodate the largest viewport seen instead of reallocating its color and depth storage whenever rendering switches between the main view and vehicle views. It is released with the OpenGL context. The existing synchronous readback/compositing path preserves original window ordering and CPU screenshots.

`renderer_3d performance baseline|optimized` compares the old cache, scan and framebuffer allocation policies in the same instrumented binary. Optimized is the default. `renderer_3d vehiclewindows 0..16` opens primary-vehicle management windows using the original UI. These presentation controls are not saved.

## Reproduce

Run from the workspace root, with other game and compiler jobs stopped:

```powershell
.\tools\phase7-benchmark.ps1
.\tools\phase7-benchmark.ps1 -MapBits 7,9,10 -Windows 0
.\tools\phase7-benchmark.ps1 -Stress -Windows 4
python tools/verify-phase7.py
.\tools\phase6-demo.ps1 -SmokeTest
```

The 64-square fixture reloads the identical operating railway save for each zero/one/four-window case. Larger cases generate deterministic flat maps with high town density and industries, at 128, 512 and 1024 square. They do not contain a large operating vehicle fleet. Profiles are isolated under `.runtime/phase7-*`. Small cases sample 15 seconds after their first draw; 512/1024-square cases use at least 45 seconds. The verifier drops the first five draw samples and requires at least 15 remaining samples. Timed benchmark processes are intentionally terminated without saving. The launcher uses the existing base-data installation.

`driver=2` emits per-draw-pass CPU wall times: snapshot scan, render (including readback), readback alone, and total dirty-block drawing. OpenGL 3.3+ timer queries measure GPU triangle submission/execution separately; `gpu_timer=false` means unavailable, not zero GPU cost. GPU timing excludes framebuffer clear, uploads, readback and final UI presentation. The synchronous readback already waits for rendering; timer results are collected afterward. None of these values is an end-to-end FPS measurement. Debug logging affects absolute timings in both modes. Working set is sampled every 500 ms and includes driver allocations.

## Measured results (2026-10-16)

Windows x64 Release, RTX 3090 / NVIDIA 610.74, 1280x900, 32-bit optimized blitter, 16-tile chunks. Same instrumented executable in both modes; each case is one sequential trial, not a statistical confidence interval. Large-map samples include ongoing town/terrain updates and chunk rebuilding. All generated maps use high town density; the fleet stress remains a separate small-map fixture.

| Fixture | Baseline mean draw ms | Optimized mean draw ms | Baseline / optimized p95 ms | Samples baseline / optimized |
|---|---:|---:|---:|---:|
| Railway, no vehicle windows | 13.61 | 12.54 | 17.24 / 16.26 | 481 / 461 |
| Railway, one vehicle window | 18.30 | 13.85 | 26.23 / 21.48 | 578 / 606 |
| Railway, four vehicle windows | 71.42 | 25.34 | 91.47 / 35.38 | 212 / 541 |
| 200 additional trucks, four windows, fast-forward | 71.11 | 33.96 | 86.08 / 41.63 | 210 / 426 |
| 128x128 generated map | 12.56 | 9.53 | 15.41 / 13.26 | 31 / 32 |
| 512x512 generated map | 111.38 | 54.80 | 158.98 / 105.50 | 26 / 26 |
| 1024x1024 generated map | 529.34 | 249.71 | 802.05 / 422.04 | 19 / 25 |

Four-window drawing time improved about 65%; the fleet stress improved about 52%. The optimized four-window run averaged 4.3 image renders per pass versus 9.2 in baseline mode. Process working set stayed approximately 195 MiB for the railway and 199 MiB for fleet stress. The 512/1024-square runs reached approximately 377/1039 MiB. The 1024-square optimized scan/rebuild component still averaged 243 ms: this is not acceptable large-map performance.

See [complete timing summary](evidence/phase7/results.json), [retained per-pass samples](evidence/phase7/samples.csv), and [environment / binary provenance](evidence/phase7/environment.txt). GPU query values cover triangles only; the CPU render/readback and scan costs dominate these measured scenes. Initial short large-map trials failed the sample-count gate and were replaced by the longer runs above.

## Costs and limits after the first pass (historical)

Snapshot scanning still visits the entire map once per drawing pass. Mesh rebuilding remains chunk-based and authoritative; changing tiles can invalidate the image cache and mark the whole screen dirty. CPU projection and vertex uploads repeat per viewport; assets are compiled into the executable and have no runtime disk-load phase. No instancing or LOD is claimed. Synchronous GPU readback remains, and switching to deferred readback or GPU UI compositing needs separate clipping, cursor and screenshot validation. These are measured follow-up targets, not grounds for changing simulation timing.

The stress fixture clones and starts 200 additional trucks through the normal AI API on the existing small route; congestion and vehicles still emerging from the depot are expected. It runs with the standard fast-forward control capped at 1000%, and measures only after the AI confirms all 200 clones. This is a fleet-count stress case, not 200 independent productive routes on a large map. Long-running memory stability, cross-machine performance and final-art budgets remain unverified. See [release-readiness.md](release-readiness.md) for packaging and compatibility limitations.

## Validation and handoff

### Recorded next priorities (user request, 2026-10-16)

1. **Replace whole-map scanning with dirty-chunk tracking.** Refresh only chunks affected by construction, terrain edits, signals, scenery or climate changes. Include neighboring chunks for shared terrain corners and invalidate correctly on map generation/reload. The optimized 1024x1024 scan/rebuild component averaged 243 ms, making this the first large-map priority. Retain the full-scan mode as a correctness reference and compare visual updates and before/after timings against it.
2. **Keep static geometry on the GPU.** Retain terrain, infrastructure and building chunk meshes in GPU buffers, and apply each viewport's camera transform in the shader instead of projecting and uploading those vertices again on the CPU. Rebuild/upload changed chunks; handle moving vehicles separately. Preserve selection, transparency, depth ordering, screenshots and classic fallback. Validate zero/one/several vehicle windows and measure CPU projection/upload time, GPU time and retained memory.

Both priorities are implemented and verified in [phase7-retained.md](phase7-retained.md), including the full-scan correctness reference, same-state CPU/GPU image comparisons, reloads, selection/visibility checks, and measured zero/one/four-window results.

### Completed checkpoint

The capped Release build succeeds and CTest passes 105/105 tests. The benchmark verifier accepts all 14 cases with sufficient samples and no detected renderer or AI failures. GPU queries are enabled only at driver debug level 2 or higher in the final build; normal play avoids query collection. Classic rendering bypasses the frame timer.

The actual Release launcher also completed the visibility/secondary-viewport smoke fixture, saved and exited normally. The fresh [restored screenshot](evidence/phase7/restored.png) was visually inspected: both differently sized views render correctly, with original toolbar, status bar and window borders. This is scripted visual evidence, not native mouse/DPI acceptance. Build and CTest logs are retained beside the timing data.

Changed engine files: `src/video/proof3d.h`, `src/video/proof3d_impl.h`, `src/window.cpp`, and `src/console_cmds.cpp`. New tools: `tools/phase7-benchmark.ps1`, `tools/verify-phase7.py`, and `tools/phase7-demo.ps1`. Evidence, phase plans and release inventory accompany this checkpoint.

The subsequent CPU tile-mesh and dirty-tile checkpoints are complete; see [the current roadmap](phase7-tiles.md#next-performance-priorities-recorded-2026-10-16). Priority 2, offscreen rebuilding and bounded retention, is implemented and verified in [phase7-offscreen.md](phase7-offscreen.md). Priorities 3–5 remain planned: narrower geometry patches, readback/compositing and smaller screen invalidation. Keep the full-scan reference. This checkpoint does not close Phase 7's large-map/release readiness gate.

