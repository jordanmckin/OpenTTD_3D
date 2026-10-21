# Phase 7 priority 7: scoped vehicle and effect invalidation

Follow-up: [rotation and delayed vehicle refresh fix](rotation-layer-fix.md). The direct layer refresh skipped parts of newly rendered views when a small dirty clip rendered them first. The historical performance figures below predate that correctness fix; repeat them before relying on the reported savings. A new opt-in layer pixel reference covers direct compositing.

Status (2026-10-18): implemented and measured. A moving vehicle, effect or changed tile now re-renders only the views whose camera can see it, instead of every cached view. All correctness scenes pass, and every image kept through a change matches a fresh render exactly. In a running game the gain is small: with vehicle windows open, views are re-rendered 13–29% less often and the 3D drawing pass is 0.4–0.6 ms shorter, but frame times stay the same within run-to-run noise. Every open view usually does see a change on every tick: vehicle windows follow moving vehicles, and the 4K main view covers hundreds of tiles of traffic, growing grass and trees.

## Changes

- **Changes are described as world boxes** (`InvalidateProof3DRegions`, `src/video/proof3d_impl.h`). Each cached image, and each on-screen view, is tested against the boxes with its own camera (`Terrain3D::Visible`, the same conservative test used for culling). Only images that can see a box are dropped. In direct presentation the layer is marked stale only when an on-screen view sees one. In read-back presentation only those views' screen rectangles are marked dirty. On-screen views are tested as well as cached images, so a view whose image was evicted is still redrawn.
- **Vehicles and effects** (`src/video/rail3d_impl.h`). The old and new instance lists are compared as sorted sets, so a vehicle entering a depot does not shift every later vehicle. Each moved, added, removed or restyled instance contributes its old and new boxes, from the model's horizontal reach, scaled by its length, and its height range, as at draw time. Placeholder faces are compared by position.
- **Tiles** (`src/video/terrain3d_impl.h`). A changed tile contributes one box covering its old and new extents (`TerrainTileBounds`, factored out of `ExpandTerrainBounds`). The first read of a chunk, camera, visibility, selection and settings changes still invalidate everything.
- **The layer only redraws views that were re-rendered.** Before, a stale layer re-queued every view; a view that kept its image still shows it in the layer.
- More than 8,192 boxes in one change invalidates everything, because testing them would cost more than re-rendering.
- `renderer_3d scoped on|off` is the A/B control; off is the pre-priority-7 behaviour. The benchmark accepts `-Modes unscoped`. `PHASE7 frame` reports `scoped_boxes`, `scoped_drops` and `scoped_kept`.

## Results (2026-10-18)

Windows x64 Release, RTX 3090, 3840×2160, 60 Hz cap, direct presentation. The same executable, with scoped invalidation off, then on; one sequential trial per case. "Renders" are view images rendered per drawing pass. "Layer" is views re-queued into the layer per pass outside the 2D drawing. "Over 10 ms" is the share of presented frames with more than 10 ms of CPU work.

| Case | Renders | Layer | 3D draw pass ms | Render ms | p95 frame ms | Over 10 ms |
|---|---:|---:|---:|---:|---:|---:|
| Demo, 4 windows, off | 3.63 | 0.99 | 2.65 | 1.34 | 19.9 | 2.7% |
| **Demo, 4 windows, on** | **2.58** | **0.03** | 2.69 | **1.20** | 20.2 | 5.2% |
| Fleet zoom 4, 4 windows, off | 4.24 | 0.37 | 6.72 | 3.90 | 25.0 | 52.3% |
| **Fleet zoom 4, 4 windows, on** | **3.70** | **0.01** | **6.07** | **3.51** | 26.5 | **43.6%** |
| Fleet zoom 2, 4 windows, off | 4.00 | 0.19 | 4.68 | 2.43 | 22.4 | 16.4% |
| **Fleet zoom 2, 4 windows, on** | **3.48** | **0.01** | **4.30** | **2.15** | 24.3 | 19.6% |

All cases hold 60 FPS in both modes. Without vehicle windows, both modes render the same number of images (0.75–0.96 per pass): the main view sees some change on almost every tick, at zoom 2 as well as zoom 4. The p95 and over-10 ms figures move in both directions by about as much as they vary between repeated runs; an earlier pair of fleet runs without windows, taken while other applications were busy, fell to 33–42 FPS in both modes and was repeated. The cost of the box tests is not measurable: 170–320 boxes per pass in the fleet.

Summaries: [demo and fleet at zoom 4](evidence/phase7/p7/4k-capped-zoom4-results.json), [fleet without windows, repeated](evidence/phase7/p7/4k-capped-fleet0-rerun-results.json), [fleet at zoom 2](evidence/phase7/p7/4k-capped-fleet-zoom2-results.json).

## Correctness

- **New kept-image reference.** With `renderer_3d verifygpu on`, an image kept through a change is re-rendered from scratch every 16th frame and compared with the cached pixels (`PHASE7 kept-reference`). `tools/verify-phase7-checks.py` now requires these comparisons, with almost no differing pixels allowed.
- `tools/phase7-checks.ps1` passes the railway, construction and temperate (roaming) scenes. Kept images: 1,151, 437 and 454 comparisons, all identical to the fresh render. Mesh mismatches 0, missed chunks 0, bounds failures 0, and the existing retained-against-CPU image check is unchanged (at most 0.005% of pixels). See [railway](evidence/phase7/p7/check-railway.json), [construction](evidence/phase7/p7/check-construction.json), [temperate](evidence/phase7/p7/check-temperate.json).
- CTest is 113/115 (the two known savegame regressions).

## What is left

- When every view really changes on every tick, scoping cannot reduce the work. The remaining per-render cost is drawing itself: in the 4-window fleet, about 6 ms of the 9.4 ms of CPU work per frame is the 3D drawing pass, and each library instance is still one draw call with four uniform updates (priority 9).
- p95 frame intervals of 20–26 ms with 6–9 ms of mean CPU work mean some frames miss the 60 Hz deadline even when the work is well under it. Frame pacing has not been examined yet.

## Reproduce

```powershell
.\tools\phase7-benchmark.ps1 -MapBits 6 -Windows 0,4 -Modes unscoped,optimized -RunTag p7s -Resolution 3840,2160 -Capped
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 0,4 -Fleet -Zoom 4 -Modes unscoped,optimized -RunTag p7s -Resolution 3840,2160 -Capped
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 0,4 -Fleet -Zoom 2 -Modes unscoped,optimized -RunTag p7z -Resolution 3840,2160 -Capped
.\tools\phase7-checks.ps1 -Scene railway
.\tools\phase7-checks.ps1 -Scene construction
.\tools\phase7-checks.ps1 -Scene temperate -Roam
```

Changed engine files: `src/video/proof3d_impl.h`, `src/video/proof3d.h`, `src/video/rail3d_impl.h`, `src/video/terrain3d_impl.h`, `src/console_cmds.cpp`. Tools: `tools/phase7-benchmark.ps1`, `tools/verify-phase7.py`, `tools/verify-phase7-checks.py`.
