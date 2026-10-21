# Phase 7 priority 10: distant model LOD

Status (2026-10-18): evaluated as an opt-in candidate; **do not enable it by default on these measurements**. It reduces triangles but regresses the measured four-window frame cost and increases model storage. Reduced-model visual approval is also outstanding. Full detail remains the default. This does not close Phase 7's general release gate.

The [review gallery](evidence/phase7/p10/review/index.html) contains **all 167 generated variants**, with two camera directions, company colours, close-ups and actual distant game pixels enlarged without smoothing. It renders the embedded triangles offline using the classic projection and lighting. It is separate from the live renderer reference checks. Representative train, bus, ship and aircraft comparisons were visually inspected.

## Geometry and selection

The existing glTF converter now also writes `src/video/asset3d_lod.h` and [lod-report.json](../../assets/3d/lod-report.json). It clusters vertices within connected components, retains each component's axis bounds and material colours, and rejects reductions that reverse a surviving triangle or lose a component or material. Company-colour markers and emissive colours remain intact. The source `.blend`, exports and full-detail runtime table are unchanged. Reduced faces inherit the source geometry's GPL-2.0-only licence.

Two clustering scales, 0.4 and 0.8 world units, are tried. A candidate must remove at least 10% of the previous level's triangles; a coarser clustering that produces more triangles is skipped. The converter records the maximum displacement of every source vertex, including vertices in collapsed triangles, with an allowance for embedding precision. `--check` now also verifies reproducibility of both generated headers and the report.

The retained GPU path and independent CPU expansion select the same model per viewport. Close views retain full detail. A reduced mesh is eligible only when the camera scale is below 1, its conservative projected diameter is at most 64 pixels, and its projected vertex displacement is at most **0.5 pixels**. The bound accounts for camera tilt, yaw, vehicle direction and stretched vehicle length. Rotations preserve displacement length; the largest singular value of the orthographic screen projection bounds its screen displacement. This is a geometric vertex bound, not a guarantee that raster colours or shading are identical to full detail.

Vehicles, effects and moving industry parts can use these variants. Houses, trees, static industry geometry and other baked chunk art retain full detail; sharing those models is priority 11. Culling and invalidation retain the original bounds. Both instanced and uniform GPU paths use the selected range and preserve scene order. Changing `renderer_3d lod on|off` invalidates every cached view; the model buffer is recreated during rendering when the selected library changes. Context recreation follows the existing buffer lifecycle. The LOD flag is client presentation state and is not saved. Simulation, commands and network behaviour are unchanged.

Across the generated variants, **204,636 source triangles become 158,589**, a 22.50% reduction. This sum counts the source again when it has two reduced variants; it is not a whole-scene reduction. Some examples:

| Model | Full triangles | Reduced triangles |
|---|---:|---:|
| `train_000`, medium | 2,348 | 1,741 |
| `road_000`, far | 1,062 | 801 |
| `ship_000`, far | 1,972 | 1,546 |
| `aircraft_001`, medium | 1,270 | 816 |

## Correctness

The capped Windows x64 Release build succeeds, and CTest passes **117/117**, including both savegame regression fixtures. New tests validate generated model references, nondegenerate faces, finite coordinates, matching bounds and material colours, and the projected displacement bound under rotation, tilt and vehicle stretching. Converter reproducibility and Python/PowerShell syntax checks pass.

Two focused live fixtures exercise distant and close views, runtime LOD switching, the uniform fallback, rotated cameras, a secondary viewport, classic switching, terrain edits and save/reload. They use `-LODOnly`; they are not a repeat of every visibility/construction step in the broader fixture. The latter remains available with `-LOD`. At zoom 4, the 64-square map occupies the centre of the screen, so the focused screenshot occupancy check inspects the main view beside the secondary window rather than the empty bottom strip; it retains the existing 20% occupancy threshold.

| Scene | Instanced/uniform comparisons | Differing pixels | Independent CPU/GPU maximum differing pixel fraction | Kept-image comparisons | Reduced-mesh view renders |
|---|---:|---:|---:|---:|---:|
| Operating railway, four vehicle windows | 1,443 | 0 | 0.00513% | 1,400 | 4,720 |
| Construction | 356 | 0 | 0.000434% | 419 | 4,217 |

Both scenes report zero missed chunks, mesh mismatches, bounds failures and kept-image differences. Close views with zero reduced instances are present alongside distant views with reduced instances. These counts include diagnostic renders. See [railway](evidence/phase7/p10/check-railway.json) and [construction](evidence/phase7/p10/check-construction.json).

The 3840×2160 direct-layer regression with four vehicle windows, fast forward, rotating cameras, the 40bpp animated blitter and LOD enabled passes **105 comparisons**, checking **396,697,651 pixels**, with zero stale pixels or OpenGL errors. See [layer results](evidence/phase7/p10/check-layer-4k.json). Native mouse/DPI acceptance and a separate OpenGL 3.2 driver remain untested; the uniform fallback was explicitly exercised on the available OpenGL 4.5 driver.

## Measurements

Windows x64 Release, RTX 3090 / NVIDIA 610.74, 3840×2160, 60 Hz cap, direct presentation, 512-square operating fleet at zoom 4. Each case samples at least 45 seconds after readiness, dropping the verifier's initial samples. All diagnostic processes and compiler jobs have exited. The same executable runs with LOD off (`optimized`) and on (`lod`); instancing, cached locations, scoped invalidation and all other optimizations stay enabled. These are sequential trials, not confidence intervals.

| Case | Mean 3D drawing ms, full / LOD | CPU work ms/frame, full / LOD | p95 frame ms, full / LOD | FPS, full / LOD |
|---|---:|---:|---:|---:|
| Fleet, no windows | 3.44 / 3.42 | 2.84 / 2.84 | 22.61 / 22.49 | 60.01 / 60.01 |
| Fleet, four windows, first pair | 5.81 / 7.66 | 5.83 / 8.43 | 24.62 / 29.16 | 60.01 / 57.38 |
| Fleet, four windows, reverse-order repeat | 5.72 / 6.86 | 5.75 / 6.87 | 24.65 / 26.12 | 60.01 / 59.18 |

The first pair runs full detail before LOD; the repeat runs LOD before full detail. The repeat also regresses four-window drawing and frame cost. The exact cost varies between runs, so it should not be assigned solely to a particular function without further profiling. The result is sufficient to reject enabling this candidate by default. There is no demonstrated frame-time win in the measured fleet.

The LOD counters compare the selected meshes with the full meshes for the **same visible instances within each drawing pass**:

| LOD case | Full-model triangles/pass | Selected triangles/pass | Reduction | Reduced instances/pass |
|---|---:|---:|---:|---:|
| No windows | 426,876 | 328,675 | 23.00% | 338.4 |
| Four windows, first pair | 361,247 | 289,512 | 19.86% | 247.2 |
| Four windows, repeat | 364,666 | 292,112 | 19.90% | 250.0 |

These counts cover vehicles, effects and moving industry parts, not static terrain/chunk triangles. Independently timed runs have slightly different visible-instance counts, so their triangle totals should not be treated as identical snapshots.

The retained GPU model library grows from **39.443 to 59.407 MiB**, an extra **19.964 MiB**, while LOD is on. The default path uploads only the full library. Process working sets range from roughly 2.44 to 2.53 GiB in these runs and include driver allocations; they vary more than the fixed model-buffer increment. The candidate also adds embedded geometry to the executable. Reducing model triangles alone does not justify these costs for this scene.

Decision: retain the opt-in A/B path and [visual review gallery](evidence/phase7/p10/review/index.html), keep **full detail as the default**, and continue with priority 11's shared static library instances. Enabling LOD as a performance improvement requires new evidence as well as the roadmap's visual approval. Priority 10 is an evaluated candidate, not an accepted default optimization.

Evidence: [original four cases](evidence/phase7/p10/fleet-results.json), [reverse-order repeat](evidence/phase7/p10/repeat-results.json), [original per-pass samples](evidence/phase7/p10/p10fleet-samples.csv.gz), [repeat samples](evidence/phase7/p10/p10repeat-samples.csv.gz), [binary/environment](evidence/phase7/p10/environment.json), [Release build](evidence/phase7/p10/build.log), [117 tests](evidence/phase7/p10/tests.log). Compressed raw scene, layer and benchmark logs are retained beside these summaries.

## Reproduce

From the workspace root:

```powershell
python tools/3d_assets/convert_gltf.py
python tools/3d_assets/convert_gltf.py --check
python tools/3d_assets/preview_lod.py
.\tools\phase7-checks.ps1 -Scene railway -RunTag p10focused -LODOnly
.\tools\phase7-checks.ps1 -Scene construction -RunTag p10focused -LODOnly
.\tools\verify-3d-layer.ps1 -RunTag p10layer -Windows 4 -FastForward -Rotate -Blitter 40bpp-anim -Resolution '3840,2160' -Seconds 20 -LOD
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 0,4 -Fleet -Zoom 4 -Modes optimized,lod -RunTag p10fleet -Resolution '3840,2160' -Capped
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 4 -Fleet -Zoom 4 -Modes lod,optimized -RunTag p10repeat -Resolution '3840,2160' -Capped
```

Timing runs start only after all correctness processes and compiler jobs have exited. `optimized` and `lod` use the same executable and differ only in the LOD flag. Reference rendering is disabled during timing. Full detail stays the default; visual approval alone is not evidence of a performance benefit. Priority 11, static library instancing, remains separate.
