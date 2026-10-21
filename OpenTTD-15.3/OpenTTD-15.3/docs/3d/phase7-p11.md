# Phase 7 priority 11: shared static library models

Status (2026-10-19): implemented, checked against independent expanded geometry, and measured. General Phase 7 release acceptance remains open. Full-detail models remain the default; priority 10's LOD candidate stays opt-in.

## Changes

`BuildAsset3D` now records affine placements of houses, trees, static industry pieces, objects and station/depot models in per-chunk instance lists. Each list retains the model identity, transform, company colours, tile identity, transparency option and exact transformed bounds. The full-detail model library is uploaded once. Opaque placements are grouped by model in linear time for each view and drawn with instancing; the uniform draw fallback remains available. Placement order within a model stays stable. The independent CPU image reference expands the original scene in tile order, rather than consuming the grouped instance stream.

Terrain, procedural infrastructure, rail library pieces and models deformed over a sloped surface remain in tile slots. In particular, fences, rocks and dock land pieces keep their existing per-vertex terrain following. No model, material, simulation, command, save or network state changes.

The existing packed-span updater patches the geometry and instance lists from the same dirty-tile mask. Growth, construction and animation can replace or remove variable-length placement spans. Both streams contribute to chunk bounds. CPU retention accounting includes the placement lists and their spans; eviction releases them, and a cold view regenerates them. Runtime `renderer_3d staticinstances on|off` resets terrain residency and cached views. Selection and transparency are evaluated per instance from its owning tile, and close secondary/vehicle views use their own culling.

The shared model vertex format now stores only position, colour and local face normal: **36 bytes instead of 44**, without quantisation. Its full-detail library falls from **39.443 to 32.272 MiB**. This format is active in both timing modes, so the A/B comparison isolates sharing static placements.

`audit_vertex_storage.py` evaluates lossless indexing of that compact library, preserving position, colour and the unnormalised face normal in every key. With 32-bit indices it would save a further **4.522 MiB** (14% of the compact library). This is a storage estimate, not an implemented or timed indexed draw path. The report is [vertex-storage.json](evidence/phase7/p11/vertex-storage.json).

## Correctness

The capped Release build succeeds, and CTest passes **117/117**, including both savegame regression fixtures. The broad operating railway, construction and temperate roaming fixtures all passed before the final culling adjustment:

- **28,162** comparisons of cached geometry plus expanded placements against freshly built chunks: zero mismatches.
- **63,411** chunk-bounds comparisons: zero failures; dirty snapshot references find zero missed chunks.
- **4,433** instanced/uniform image comparisons: zero differing pixels.
- **4,499** independent CPU/GPU image comparisons: maximum differing fraction **0.00684%**, within the unchanged 0.5% edge/colour threshold. These references include the original tile submission order; CPU/GPU images are bounded comparisons, not pixel-identical claims.
- **4,116** kept-image comparisons: zero stale-image differences.

The fixtures include runtime baked/shared switching, an explicit uniform screenshot, construction/removal, highlight and preview state, transparent and hidden structures, rotated cameras, chunk sizes 16/32, secondary and vehicle windows, classic switching and separate save/reload. Temperate additionally leaves and re-enters edited areas. Representative restored and shared screenshots were visually inspected. The broad-check summaries and raw logs are retained alongside the final checks.

The final build removes redundant per-placement visibility tests and uses the original per-chunk culling, with partial chunks clipped by the GPU. After that adjustment, CTest passes again and the focused railway and temperate roaming fixtures repeat the rendering transitions and reloads. They add 13,115 mesh comparisons, 2,321 exact instanced/uniform comparisons and 2,107 kept-image comparisons, with zero failures. See [final railway](evidence/phase7/p11/final-check-railway.json) and [final temperate](evidence/phase7/p11/final-check-temperate.json).

The 3840 x 2160 direct-layer test with four vehicle windows, rotating cameras, fast forward and the 40bpp animated blitter passes **104** comparisons over **411,207,972** pixels, with zero stale pixels or OpenGL errors. Native mouse/DPI acceptance and a separate OpenGL 3.2 driver remain outside this scripted checkpoint.

## Measurements

Windows x64 Release, RTX 3090 / NVIDIA 610.74, direct presentation, 60 Hz cap. Demo and fleet cases use 3840 x 2160; the generated 128-square map uses 1280 x 900. The fleet is 512 square at zoom 4. Each case reloads the same fixture or generation seed. Small cases sample 15 seconds and fleet cases at least 45 seconds after readiness; initial samples are excluded by the existing verifier. Correctness processes and compiler jobs have exited before timing.

`baked` and `optimized` run the same executable, with static sharing off and on respectively. Instancing of moving models, compact vertices, all other optimisations and full model detail stay the same. Each row is one sequential pair, not a confidence interval. The four-window fleet is repeated in reverse order.

| Case | 3D drawing ms, baked / shared | CPU work ms/frame, baked / shared | p95 frame ms, baked / shared | FPS, baked / shared |
|---|---:|---:|---:|---:|
| Demo, 0 windows | 1.08 / 1.03 | 1.14 / 1.10 | 18.37 / 18.49 | 60.00 / 60.00 |
| Demo, 1 windows | 1.38 / 1.41 | 1.45 / 1.52 | 18.58 / 18.77 | 60.00 / 60.00 |
| Demo, 4 windows | 2.34 / 2.46 | 2.59 / 2.68 | 19.58 / 19.29 | 60.01 / 60.00 |
| Fleet, 0 windows | 3.23 / 3.58 | 2.65 / 2.82 | 22.49 / 21.25 | 60.01 / 60.00 |
| Fleet, 1 windows | 3.53 / 3.84 | 3.41 / 3.64 | 22.43 / 21.93 | 60.00 / 60.01 |
| Fleet, 4 windows | 5.76 / 6.50 | 5.77 / 6.39 | 24.46 / 25.11 | 60.00 / 60.00 |
| Repeat, 4 windows | 6.02 / 6.21 | 6.01 / 6.11 | 24.84 / 24.87 | 60.00 / 60.00 |
| Map128, 0 windows | 1.56 / 1.02 | 0.46 / 0.35 | 17.61 / 17.65 | 60.01 / 60.00 |

Retained chunk vertex allocation and CPU mesh/list storage are reported separately from the shared model library. The working set is sampled every 500 ms during the measured interval. It also includes snapshots, streamed instance data, framebuffer storage and driver allocations; it is not a measurement of total GPU memory.

| Fleet vehicle windows | GPU chunk MiB, baked / shared | CPU mesh/list MiB, baked / shared | Sampled working set MiB, baked / shared | Shared static instances/pass | Shared static draws/pass |
|---|---:|---:|---:|---:|---:|
| 0 | 962.3 / 239.0 | 424.7 / 121.7 | 2523.0 / 939.6 | 34489 | 168 |
| 1 | 962.8 / 239.0 | 424.7 / 121.7 | 2581.5 / 954.9 | 27831 | 175 |
| 4 | 962.4 / 239.0 | 424.7 / 121.7 | 2551.8 / 954.9 | 25962 | 280 |

Keep sharing enabled by default in 3D mode as a memory optimisation. Fleet chunk allocation falls about **75%**, CPU mesh/list storage about **71%**, and sampled process working set from about **2.5 GiB to 0.93 GiB**. All 16 final cases hold 60 FPS with the cap.

The memory saving has a CPU cost. Mean fleet CPU work increases by 0.17-0.62 ms/frame in the first pairs and 0.10 ms in the four-window reverse-order pair. Four-window p95 frame time increases by 0.65 ms in the first pair and 0.03 ms in the repeat. Small-map times are mixed; the generated 128-square case improves. These runs support the storage benefit, without establishing a general frame-rate improvement. `renderer_3d staticinstances off` retains the baked diagnostic path.

The next smallest performance task is to profile per-view instance grouping and streaming and evaluate retaining or patching those streams, with bounded memory and moving-camera reference checks. This revisits priority 3 after the large duplicated model payload has been removed. Priority 5's smaller screen updates, native interaction acceptance, long-session/cross-GPU checks and release packaging remain open.

Evidence: [demo](evidence/phase7/p11/demo-results.json), [fleet](evidence/phase7/p11/fleet-results.json), [reverse order](evidence/phase7/p11/repeat-results.json), [128-square map](evidence/phase7/p11/map128-results.json), [binary/source hashes](evidence/phase7/p11/environment.json), [Release build](evidence/phase7/p11/build.log), [tests](evidence/phase7/p11/tests.log). Per-pass CSVs and raw renderer logs are retained as gzip files beside the summaries.

## Reproduce

From the workspace root, with other task-owned game and compiler jobs stopped during timing:

```powershell
.\tools\phase7-checks.ps1 -Scene railway -RunTag p11 -StaticModels
.\tools\phase7-checks.ps1 -Scene construction -RunTag p11 -StaticModels
.\tools\phase7-checks.ps1 -Scene temperate -RunTag p11 -StaticModels -Roam
.\tools\phase7-checks.ps1 -Scene railway -RunTag p11final -StaticOnly
.\tools\phase7-checks.ps1 -Scene temperate -RunTag p11final -StaticOnly -Roam
.\tools\verify-3d-layer.ps1 -RunTag p11finallayer -Windows 4 -FastForward -Rotate -Blitter 40bpp-anim -Resolution '3840,2160' -Seconds 20
.\tools\phase7-benchmark.ps1 -MapBits 6 -Windows 0,1,4 -Modes baked,optimized -RunTag p11finaldemo -Resolution '3840,2160' -Capped
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 0,1,4 -Fleet -Zoom 4 -Modes baked,optimized -RunTag p11finalfleet -Resolution '3840,2160' -Capped
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 4 -Fleet -Zoom 4 -Modes optimized,baked -RunTag p11finalrepeat -Resolution '3840,2160' -Capped
.\tools\phase7-benchmark.ps1 -MapBits 7 -Windows 0 -Modes baked,optimized -RunTag p11finalmap128 -Capped
python tools/3d_assets/audit_vertex_storage.py --output .tmp/p11-vertex-storage.json
```

Changed engine files: `src/video/terrain3d_impl.h`, `src/video/asset3d_impl.h`, `src/video/proof3d_impl.h`, `src/video/proof3d.h`, `src/console_cmds.cpp`. Benchmark and correctness launchers/verifiers expose the diagnostic switch and retain the new evidence.
