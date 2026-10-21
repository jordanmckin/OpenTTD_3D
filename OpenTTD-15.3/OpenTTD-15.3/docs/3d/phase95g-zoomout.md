# Phase 9.5g: zoomed-out map performance

Accepted by the user on 2026-10-20 after the local test-release handoff. Completed: baseline, idea 3, ideas 1+4, idea 2. Idea 5 (parallel cold chunk building) is deferred unless playtesting demonstrates a remaining need. LOD stays off and every scenery item is drawn at full detail. No setting removes scenery, and simulation and gameplay are unchanged.

Acceptance applies to 9.5g; it does not establish general alpha readiness or individually close older native interaction checks. The accepted local test package is `build/releases/OpenTTD-3D-9.5g-test-20261020-7a0aca3`, built from `7a0aca3`. Its executable matches the measured idea-2 binary. All 126 CTest cases passed (124 unit cases and two savegame regressions); the staged executable also generated a map, rendered a visually checked 3D screenshot, saved, and exited normally.

## Measurement

`tools/phase95g-zoomout.ps1` loads fresh, seeded, vehicle-free maps (512x512 `sq512`, 2048x512 `wide`, 512x2048 `tall`; the new-map regression seed 20261020) at 3840x2160 with refresh requested at 1000 Hz, `win32-opengl`, `32bpp-optimized`, shadows off. It covers zoom 2 (normal) to 5 (maximum zoom-out), classic and 45-degree rotated orthographic cameras, and still or panning views. The pan case visits a 4x4 grid across the map, moving every 10 drawn frames, and loops, so it covers both cold views and revisits. Each case is a new process. Five seconds of warm-up and the cold start are excluded from the 15-second timed interval, and readback is off. `tools/verify-phase95g-zoomout.py` reports presented frame intervals (median/p95), CPU work, 3D draw time, GPU time per render, renders per second, preparation, uploads, residency and evictions. Run it with `--compare <tag>` to compare against a baseline.

The baseline binary is the current Release build before 9.5g changes, frozen in `build/phase95g-before` (SHA-256 `CE54A99C…B5E910`, the same binary as the new-map startup fix).

## Baseline (tag `p95g-before`, 48 cases, all pass)

[Full results](evidence/phase9/p5g/baseline-results.json). Selected cases, FPS / median frame / p95 frame:

| Map | Zoom 2 still | Zoom 4 still | Zoom 5 still | Zoom 4 pan | Zoom 5 pan |
|---|---|---|---|---|---|
| 512x512 classic | 293 / 3.1 / 5.6 ms | 204 / 3.3 / 11.5 ms | 183 / 3.3 / 14.0 ms | 36 / 4.1 / 204 ms | 52 / 4.3 / 108 ms |
| 512x2048 classic | 292 / 3.1 / 5.8 ms | 202 / 3.1 / 11.9 ms | 71 / 19.4 / 27.9 ms | 27 / 5.6 / 270 ms | 15 / 22.9 / 260 ms |
| 2048x512 classic | 282 / 3.1 / 6.1 ms | 178 / 3.3 / 15.2 ms | **18.6 / 53.5 / 58.3 ms** | 13 / 6.3 / 707 ms | **6.8 / 33.4 / 1217 ms** |
| 2048x512 rotated | 280 / 3.1 / 6.4 ms | 176 / 3.3 / 15.5 ms | 24.0 / 41.8 / 49.6 ms | 13 / 10.5 / 690 ms | 6.4 / 27.4 / 1353 ms |

- Normal zoom is fine everywhere (about 280–290 FPS).
- Panning at zoom 3–5 is poor on every map. Evictions run at 6,000–10,000 per 15 seconds, so chunks are evicted and rebuilt continuously against the 128 MB mesh budget.
- Still views fall off a cliff rather than a slope: 512x512 zoom 5 (1,024 visible chunks) runs at 183 FPS, but 2048x512 zoom 5 (1,607 chunks) runs at 18.6 FPS, with GPU time per render rising from 9 to 45 ms. This fits crossing the fixed budgets more than raw geometry.

## First findings (2026-10-20, before any change)

Diagnostic runs, 2048x512, classic camera, zoom 5, still view:

| Run | FPS | Median frame | GPU per render | Renders/s |
|---|---:|---:|---:|---:|
| Running | 18.3 | 54.0 ms | 45.6 ms | 18.3 |
| Running, trees hidden | 18.7 | 53.3 ms | 44.7 ms | 18.7 |
| Running, trees/houses/industries/buildings/structures hidden | 17.6 | 55.6 ms | 47.9 ms | 17.6 |
| Paused | 301.5 | 3.2 ms | n/a | 0 |

- **The whole view re-renders every frame with no vehicles.** Tile-loop growth (grass and trees) changes about 40 tiles per tick, and at this zoom every change falls inside the view. When paused, the same view is free.
- **GPU time per render is about 45 ms, and hiding static scenery does not reduce it.** The cost is in the terrain pass. It draws 1,607 visible chunks, each as a `glMultiDrawArrays` of 256 per-tile ranges, about 411,000 sub-draws.
- **The static instance cache never engages.** About 228,000 static placements exceed the fixed 32 MB `PROOF_STREAM_BUDGET`. Each render builds the stream, discards it, then regroups and uploads 14.6 MB again (`static_group_us` about 28 ms).
- **The mesh cache is well over its 128 MB budget**: 405 MB retained GPU plus 235 MB CPU faces, all visible and therefore pinned. Some eviction churn occurs even in a still view.

## Ideas and agreed order

The user agreed this order on 2026-10-20:

1. **Idea 3 – fewer terrain draw calls (first).** Merge back-to-back per-tile slots into runs, kept in tile order and cached per chunk revision, so a packed chunk is one draw instead of 256 and drawing order is unchanged. If needed, follow up by reducing per-chunk vertex-attribute rebinding (one VAO per chunk, or one arena buffer with a single multi-draw across chunks).
2. **Ideas 1 + 4 – budgets and vertex size (second).** The user is fine with raising the budgets. Scale the mesh budget and the static stream budget with the map/visible set, and check the budget only when meshes change. Pack the 44-byte terrain vertex (half floats or packed tile coordinates, RGBA8 colour, byte-sized transparency/layer) to about 20 bytes, and drop the CPU face copy for uploaded, unchanged chunks where picking does not need it.
3. **Idea 2 – partial re-render (third).** Keep a cached colour and depth image of the static scene. Re-render only the scoped dirty rectangles with a scissor, then draw dynamic vehicles, effects and contact shadows over the cached depth. The first findings show this also matters with no vehicles, because tile growth invalidates the whole view every tick.
4. **Idea 5 – parallel cold chunk building.** Only at the very end, if needed.

Not planned: **idea 7** (sun shadow pass cost), because the slowdown reproduces with shadows off. **Idea 6** (hierarchical chunk culling) is unproven; revisit only if visibility loops show up in the measurements.

## Progress

### Idea 3: merged terrain draws (done, measured)

`TileSlots::Runs` (`src/video/terrain3d_slots.h`) merges back-to-back tile slots in tile order. `ProofChunkBuffer` caches the runs whenever the chunk's buffer is written, and terrain chunks draw their runs instead of one range per tile. A packed chunk is a single draw. Drawing contiguous ranges in the same order is equivalent to the per-tile multi-draw. The `PHASE7 frame` log reports `terrain_runs`. The tile-slot unit test checks that the runs cover exactly the tiles' vertices, in order, and that a packed buffer is one run.

Verification: Release builds. The `openttd_test` unit tests pass, 122/122 under CTest. The two savegame regressions fail only when CTest launches them through the relative copied executable in this environment; run through `Regression.cmake` with an absolute path, both pass against their expected output. Paused 3840x2160 screenshots of 2048x512 at zoom 5, classic and rotated, are **pixel-identical** (0 differing pixels) between the baseline and idea 3 binaries ([capture](evidence/phase9/p5g/wide-z5-classic.png)).

Measured (tag `p95g-p3` against `p95g-before`, same saves and settings; [results](evidence/phase9/p5g/idea3-results.json), [comparison](evidence/phase9/p5g/idea3-compare.log)):

| Case | Terrain draws per render | GPU per render | Median frame | FPS |
|---|---:|---:|---:|---:|
| 2048x512 classic z5 still | ~411,000 → 1,607 | 44.7 → **15.3 ms** | 53.5 → 53.8 ms | 18.6 → 18.5 |
| 2048x512 rotated z5 still | | 32.7 → 21.8 ms | 41.8 → 41.2 ms | 24.0 → 24.3 |
| 512x2048 classic z5 still | | 16.8 → 11.8 ms | 19.4 → **5.2 ms** | 70.9 → 81.3 |
| 2048x512 classic z5 pan | | 36.9 → 28.6 ms | 33.4 → 25.1 ms | 6.8 → 7.1 |
| 512x512 classic z5 still (repeated twice) | | 8.7 → 6.9 ms | 3.0 → 3.0 ms | 199–201 → 195–196 |

GPU time drops in every zoomed-out case. The worst still case does not gain FPS yet: with the GPU at 15 ms, the frame is now bounded by about 28 ms of CPU static-instance regrouping and the 14.6 MB re-upload caused by the 32 MB stream budget, which is next (ideas 1+4). In the first full matrix, 512x512 classic z5 still read 183 → 151 FPS. Two repeated pairs gave the same 3.0 ms median frame for both binaries, with lower draw and GPU time, so that reading was run-to-run noise. Pan p95 frames remain dominated by eviction and rebuild. No normal-zoom regression was measured (zoom 2 cases are within noise).

Committed in b499d6b.

### Ideas 1 + 4: budgets and a smaller terrain vertex (done, measured)

- **Static stream budget** (`PROOF_STREAM_BUDGET`) raised from 32 MB to 256 MB. The 2048x512 maximum zoom-out stream is about 38 MB, so it is now retained and patched instead of rebuilt and discarded every render. `static_group_us` drops from about 28 ms to about 2 ms, and instance uploads from 14.6 MB to the changed tree models only.
- **Mesh budget** (`Terrain3D::MeshBudget`, `src/video/terrain3d_cache.h`) replaces the fixed 128 MB. It is three times the bytes pinned by visible chunks, with a 1.5 GB floor and a 2 GB cap. The floor holds all of a 2048x512 map (about 1.25 GB of CPU and GPU mesh after packing), so panning revisits chunks instead of evicting and rebuilding them. An earlier attempt (twice the pinned bytes, 256 MB floor) still evicted about 10,000 chunks per pan run at zoom 4 and 5. Memory is only used when the map has that much geometry; 512x512 maps stay below 330 MB of mesh.
- **Retained terrain vertex** packed from 44 to 32 bytes. Position and colour stay float; the tile origin, transparency option and layer are 16-bit integers that the GPU converts exactly, and the always-zero `transparent` attribute is no longer stored. A 28-byte version with 16-bit colour changed 0.1-0.7% of pixels by 1/255, so it was rejected. Retained GPU memory for 2048x512 zoom 5 drops from 386 MB to 280 MB.

Verification: Release builds; `openttd_test` passes (123 test cases, including a new `MeshBudget` case). Paused 3840x2160 screenshots of 2048x512 at zoom 2 and 5, classic and rotated, from the packed-vertex build are **pixel-identical** to the idea 3 binary (the later budget floor does not change what is drawn). Binary frozen in `build/phase95g-p5` (SHA-256 `8343E659…21FAE3`).

Full matrix, tag `p95g-p5full` against the original baseline `p95g-before`, 48 cases, all pass ([results](evidence/phase9/p5g/idea14-results.json), [comparison](evidence/phase9/p5g/idea14-compare.log); step-by-step: [budgets](evidence/phase9/p5g/idea1-budgets-compare.log), [packing](evidence/phase9/p5g/idea4-packed-compare.log), [1.5 GB floor](evidence/phase9/p5g/idea1-floor-compare.log)):

| Case (classic unless noted) | Baseline FPS / median / p95 | Ideas 3+1+4 FPS / median / p95 | Evictions |
|---|---|---|---|
| 2048x512 z5 still | 18.6 / 53.5 / 58.3 ms | **53.2 / 23.0 / 29.9 ms** | 0 |
| 2048x512 rotated z5 still | 24.0 / 41.8 / 49.6 ms | 47.5 / 24.4 / 30.5 ms | 0 |
| 2048x512 z5 pan | 6.8 / 33.4 / 1217 ms | **49.6 / 21.7 / 43.0 ms** | 10,000+ → 0 |
| 2048x512 z4 pan | 13.0 / 6.3 / 707 ms | **124 / 4.1 / 22.0 ms** | 10,000+ → 0 |
| 512x2048 z5 still | 70.9 / 19.4 / 27.9 ms | 89.1 / 5.1 / 25.1 ms | 0 |
| 512x2048 z5 pan | 15.0 / 22.9 / 260 ms | 61.5 / 17.8 / 37.8 ms | 0 |
| 512x512 z5 still | 183 / 3.3 / 14.0 ms | 194 / 3.0 / 13.3 ms | 0 |
| 2048x512 z2 (normal) pan | 90 / 3.6 ms | 226 / 3.1 / 9.9 ms | 0 |
| 2048x512 z2 (normal) still | 282 / 3.1 ms | 291 / 3.0 ms | 0 |

Every pan case at every zoom now runs with no evictions, and pan p95 frames fall from 260-1350 ms to 10-45 ms. No case regressed. In the matrix, 512x512 rotated z4/z5 still read 32 and 90 FPS with renders per second dropping to 14 and 23, which points to outside interference. Rerun on both binaries back to back, they gave 222 vs 228 FPS and 194 vs 199 FPS with the same 3.0 ms median ([recheck](evidence/phase9/p5g/idea14-sq512-rotated-recheck.log)).

Memory: process working set for 2048x512 z5 pan rises from 2.0 GB to 2.3 GB, because the whole map's mesh is now kept (695 MB GPU plus 552 MB CPU). The still view falls from 1.46 GB to 1.30 GB.

What remains: zoom 5 on the large maps is about 23 ms per frame. GPU time per render is 14 ms, and the whole view still re-renders every frame because tile growth dirties it. That is idea 2 (re-render only the changed parts).

Committed in 8df5b14.

### Idea 2: redraw only the changed cells (done, measured)

A direct orthographic view now keeps its rendered image when something it sees changes. `InvalidateProof3DRegions` projects each changed box into the image and marks the 32-pixel cells it covers, widened by 2 pixels (`Terrain3D::DirtyCells`, `src/video/terrain3d_cache.h`). Before the image is next used, `RenderProofImage` redraws only those cells:

- It clears colour, depth and stencil in each run of stale cells, with a scissor, and sets their stencil to 1. Every pass then draws with the stencil test, so pixels outside the cells are left untouched.
- It draws only the terrain chunks and static placements whose screen bounds reach a stale cell. With contact shadows, the bounds are widened by the same 4-unit reach that `InvalidateProof3DRegions` uses. Vehicles and effects are drawn whole.
- Static placements of a partial render go to their own buffer in the retained stream's model-major order, so the contact shadow pass draws them too.

Changed boxes come from terrain tiles, vehicles and effects alike, so moving vehicles also redraw only their cells. A view renders whole as before when more than half its cells are stale, after any full invalidation (camera, selection, visibility or settings), and for views with a focus outline, perspective views, sun shadows, or the read-back path. `renderer_3d partial off` restores whole renders for A/B checks. The `PHASE7 frame` log adds `partial_renders`, `partial_pixels` and `partial_kept`; `renders` and the GPU column still count only whole renders.

Verification: `renderer_3d verifypartial on` renders the same view whole after every partial render and compares the two textures. On 2048x512 and 512x512, zooms 2-5, classic and rotated, still and pan, contact shadows on and off, all 4,800 comparisons are **exact** (0 pixels differ) ([log](evidence/phase9/p5g/idea2-verify.log)). The first run, before the contact reach was added, found 40 pixels off by at most 2 levels on rotated zoom 2: a skipped chunk's tree shadow fell into a redrawn cell. `openttd_test` passes (124 test cases, with a new `DirtyCells` case). Binary frozen in `build/phase95g-i2a` (SHA-256 `770E1381…96E27EA8`).

Full matrix, tag `p95g-i2full` against ideas 3+1+4 (`p95g-p5full`), 48 cases, all pass ([results](evidence/phase9/p5g/idea2-results.json), [comparison](evidence/phase9/p5g/idea2-compare.log)):

| Case (classic unless noted) | Baseline | Ideas 3+1+4 FPS / median | Idea 2 FPS / median / p95 |
|---|---|---|---|
| 2048x512 z5 still | 18.6 | 53.2 / 23.0 ms | **196 / 3.7 / 11.0 ms** |
| 2048x512 rotated z5 still | 24.0 | 47.5 / 24.4 ms | **200 / 3.7 / 10.7 ms** |
| 2048x512 z5 pan | 6.8 | 49.6 / 21.7 ms | **95 / 5.2 / 43.9 ms** |
| 512x2048 z5 still | 70.9 | 89.1 / 5.1 ms | 233 / 3.1 / 8.3 ms |
| 512x2048 z5 pan | 15.0 | 61.5 / 17.8 ms | 114 / 4.4 / 37.2 ms |
| 2048x512 z4 still | | 193 / 3.1 ms | 232 / 3.5 / 7.4 ms |
| 512x512 z5 still | 183 | 194 / 3.0 ms | 275 / 3.1 / 6.1 ms |

Zoomed-out still views now run near the normal-zoom frame rate. A pan still renders each new position whole; that first render is what is left in the pan p95. In the matrix, wide and tall zoom 2-3 cases read 4-10% lower. A back-to-back recheck of 2048x512 classic zoom 2 still, twice each, gave 300 FPS for ideas 3+1+4, 304-306 FPS for idea 2 and 298-300 FPS for idea 2 with `partial off`, all at a 2.98 ms median, so those readings were noise from later in the run.
