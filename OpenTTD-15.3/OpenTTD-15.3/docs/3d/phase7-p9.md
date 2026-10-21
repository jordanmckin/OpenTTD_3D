# Phase 7 priority 9: instanced vehicles and effects

Status (2026-10-18): implemented, correctness-checked and measured.

Vehicles, effects and moving industry parts share the model library and now draw consecutive visible instances of the same model with `glDrawArraysInstanced`. The original scene order is preserved, including the order within each batch: the depth test keeps the first surface at equal depth, so sorting every instance by model could change overlapping vehicles or effects.

## Changes

- Each viewport culls instances with the existing model bounds, then packs placement, direction, length, company colours and stippling into 64-byte instance records. One streamed buffer upload serves the view. Consecutive instances sharing a model draw together; different models start another batch. The buffer is orphaned for each view so earlier GPU draws retain their data.
- A dedicated instance program uses the same placement, normals, lighting, company colours and stippling as the previous uniform path. The terrain program keeps its original vertex inputs and branches; model fragments do not run the ground-texture code. If the instance program fails to compile, the renderer retains uniform draws. Instance attributes are disabled and their divisors reset after drawing, before the shared VAO is used for terrain or previews again.
- Uniform and vertex-attribute locations are cached when each program links, including the direct compositor's uniforms. Context recreation recreates the locations and buffers.
- `renderer_3d instancing on|off` selects the instanced or uniform path without changing simulation or saved settings. OpenGL 3.2 retains uniform draws; instancing requires OpenGL 3.3 and both entry points. The benchmark's `uninstanced` mode otherwise uses the same optimized renderer, including cached locations and the rotation/layer fix.
- `PHASE7 frame` now reports `vehicle_instances`, `vehicle_draws`, `instance_upload_bytes` and `instanced`. The benchmark summary includes their averages and checks that upload sizes and draw counts agree.
- With `renderer_3d verifygpu on`, sampled views additionally render the same state with instancing disabled. `PHASE7 instance-reference` compares those images before the independent CPU-geometry reference. The correctness verifier requires more than 20 valid comparisons and zero pixels differing by more than two RGB levels.

## Measurements (2026-10-18)

Windows x64 Release, RTX 3090 / NVIDIA 610.74, 3840 by 2160, 60 Hz cap, direct presentation. The preserved before build includes the rotation/layer fix and predates this priority. Each case is one sequential trial; the small demo samples 15 seconds and each fleet case at least 45 seconds. All diagnostic rendering, compiler jobs and other task-owned game processes are stopped during timing. These are measured averages, not confidence intervals.

The complete change, including cached locations and the dedicated instance program:

| Case | 3D drawing ms, before / after | CPU work ms/frame, before / after | p95 frame ms, before / after | FPS, before / after |
|---|---:|---:|---:|---:|
| Demo, four windows | 2.45 / 2.39 | 2.72 / 2.64 | 19.5 / 19.6 | 60.0 / 60.0 |
| 512-square fleet, no windows | 3.60 / 3.31 | 2.87 / 2.70 | 22.8 / 22.7 | 60.0 / 60.0 |
| 512-square fleet, four windows | 5.68 / 5.61 | 5.63 / 5.61 | 24.4 / 24.4 | 60.0 / 60.0 |

All final cases hold 60 FPS with the cap, before and after; this change adds headroom rather than raising capped FPS.

The same final binary with `instancing off`, then on, isolates batching; both modes cache shader locations. Counts are means per drawing pass, including vehicles, effects and moving industry parts; visible instance counts vary with the running scene and scoped view rendering.

| Case | Draws, off / on | Visible instances, off / on | 3D drawing ms, off / on | Instance stream KiB/pass, on |
|---|---:|---:|---:|---:|
| Fleet, 0 windows | 431.7 / 78.1 | 431.7 / 432.8 | 3.35 / 3.31 | 27.1 |
| Fleet, 4 windows | 360.2 / 85.0 | 360.2 / 359.4 | 5.69 / 5.61 | 22.5 |

Batching reduces these draw calls by **76–82%**. The gain in CPU drawing time is much smaller than the reduction in calls: model triangle counts and static terrain geometry are unchanged. Consecutive runs preserve scene order, so interleaved models may still need separate draws. Retained static geometry and model LOD remain priorities 11 and 10; general Phase 7 release acceptance stays open.

Data: [preserved build](evidence/phase7/p9/before-results.json), [final demo, zero/one/four windows](evidence/phase7/p9/demo-results.json), [final fleet A/B](evidence/phase7/p9/fleet-results.json). The earlier shared-shader trials were superseded by the dedicated program. Their anomalous 11 FPS four-window result did not reproduce in a repeated pair (both modes held 60 FPS); final results above use the final shader only. Intermediate logs remain under `.runtime/p9fleet-*` and `.runtime/p9repeat-*`.

## Correctness

The Release build succeeds and CTest passes **115/115**, including both savegame regression fixtures. The three live scenes pass their existing independent CPU/GPU geometry, dirty-snapshot, bounds, kept-image and save/reload gates. Every sampled instanced image also matches the old uniform path within the two-level RGB rounding threshold:

| Scene | Instance comparisons | Differing pixels | Kept-image comparisons |
|---|---:|---:|---:|
| Operating railway, four vehicle windows and secondary view | 2,607 | 0 | 2,116 |
| Construction | 652 | 0 | 680 |
| Temperate, distant edits and rotated re-entry | 358 | 0 | 442 |

References: [railway](evidence/phase7/p9/check-railway.json), [construction](evidence/phase7/p9/check-construction.json), [temperate](evidence/phase7/p9/check-temperate.json). There are no missed chunks, mesh mismatches or bounds failures. The largest independent CPU/GPU difference is 0.00855% of pixels. The final railway screenshot and reloaded temperate screenshot were also visually inspected.

The existing direct-layer regression passes at 3840 by 2160, with four vehicle windows, fast forward, rotating cameras and the 40bpp animated blitter: **93 comparisons, 337,519,957 pixels checked, zero stale pixels and zero OpenGL errors**. See [layer results](evidence/phase7/p9/check-layer-4k.json). The rotation/layer fix already in the working tree is preserved. These are scripted camera changes; native mouse/DPI acceptance and a separate OpenGL 3.2 driver remain untested.

Build and test logs: [Release build](evidence/phase7/p9/build.log), [CTest](evidence/phase7/p9/tests.log), [binary and environment](evidence/phase7/p9/environment.json). Correctness scenes ran concurrently; benchmark cases run sequentially after all diagnostic processes exit.

## Reproduce

From the workspace root:

```powershell
.\tools\phase7-benchmark.ps1 -MapBits 6 -Windows 0,1,4 -Modes optimized -RunTag p9finaldemo -Resolution '3840,2160' -Capped
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 0,4 -Fleet -Zoom 4 -Modes uninstanced,optimized -RunTag p9finalfleet -Resolution '3840,2160' -Capped
.\tools\phase7-checks.ps1 -Scene railway -RunTag p9sep
.\tools\phase7-checks.ps1 -Scene construction -RunTag p9sep
.\tools\phase7-checks.ps1 -Scene temperate -Roam -RunTag p9sep
.\tools\verify-3d-layer.ps1 -RunTag p9seplayer -Windows 4 -FastForward -Rotate -Blitter 40bpp-anim -Resolution '3840,2160' -Seconds 20
```

The live comparisons deliberately synchronize readbacks. They are disabled during performance measurements. The final-binary A/B pair isolates batching. The preserved-build comparison includes cached locations; `-Executable` selects a separately preserved executable while using the same launch configuration. Its hash is in the environment record. The triangle count, model detail and retained static chunk memory are unchanged. LOD and static library instancing remain separate priorities.
