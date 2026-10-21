# Phase 7 priority 12: animated-tile churn

Status (2026-10-18): implemented and measured. A tile change now rewrites only that tile's geometry on the GPU, instead of re-uploading its whole 16×16 chunk (about 6 MB). In the 512² fleet at the user's 3840×2160 display with the 60 Hz cap, chunk uploads fall 94% per drawing pass. The 3D drawing pass falls from 8.8 to 3.4 ms with no vehicle windows, and frames with more than 10 ms of CPU work fall from 60% to 11%.

## What the tile changes were

`MarkTileDirtyByTile` marks tiles for 3D, but a marked tile is only rebuilt when its snapshot differs (`DirtyTileSet::Refresh`), so redundant marks already cost only a snapshot read. A diagnostic run of the fleet (45 s, `-Zoom 4`) logged every snapshot that changed and which fields differed:

| Change | Tiles | Share |
|---|---:|---:|
| Clear land: ground density only (grass growing) | 4,392 | 47% |
| Trees: growth stage or count | 3,985 | 43% |
| Industry tiles: animation frame (model 321 → 322 → 323) | 773 | 8% |
| Other (houses, stations, roads) | 123 | 1% |

Every one is a visible change, so none can be skipped. The waste was in what followed: each change, however small, rebuilt the chunk's CPU face list by copying the whole chunk twice, then converted and uploaded the whole chunk to the GPU.

## Changes

- **Per-tile slots in each chunk buffer** (`src/video/terrain3d_slots.h`). Each tile owns a vertex range in its chunk's buffer, and the chunk is drawn with one `glMultiDrawArrays` over those ranges. A changed tile is converted and written with `glBufferSubData` into its own slot. A tile that outgrows its slot moves to free space at the end of the buffer with 25% extra room. When that space runs out, the buffer is laid out again, keeping the grown slots, so cycling animation frames and growth stages settle. A buffer that never changes has no spare room; one that has changed gets 1/32 of its size plus 1,024 vertices.
- **Tiles rebuilt since the last upload are tracked per chunk** (`TerrainChunk::gpu_changes`), because a chunk can be rebuilt several times before a view next draws it.
- **In-place mesh patching** (`PatchTileMesh`, `src/video/terrain3d_mesh.h`). Only changed tiles are built into scratch storage. When each keeps its face count (ground density, most animation frames), the new faces overwrite the old ones in place. Otherwise the chunk is reassembled with one copy instead of two.
- `renderer_3d performance baseline` keeps whole-buffer uploads for A/B comparison. `PHASE7 frame` reports `slot_writes` and `slot_relayouts`.

## Results (2026-10-18)

Windows x64 Release, RTX 3090, 3840×2160, 60 Hz cap, direct presentation. Before is commit 811e7c7, after is this change; one sequential trial per case. "Upload" is retained chunk geometry uploaded per drawing pass. "Over 10 ms" is the share of presented frames with more than 10 ms of CPU work.

| Case | Upload MB/pass | 3D draw pass ms | Mesh ms | p95 frame ms | Over 10 ms | GPU retained MB |
|---|---:|---:|---:|---:|---:|---:|
| Demo, 0 windows, before | 1.09 | 2.04 | 0.13 | 24.4 | 8.2% | 50 |
| **Demo, 0 windows, after** | **0.09** | **1.05** | **0.08** | **19.3** | **1.5%** | 52 |
| Demo, 4 windows, before | 0.69 | 3.45 | 0.09 | 23.8 | 9.0% | 50 |
| **Demo, 4 windows, after** | **0.06** | **2.84** | **0.05** | **20.1** | **3.2%** | 52 |
| Fleet, 0 windows, before | 12.18 | 8.84 | 1.42 | 29.9 | 60.4% | 953 |
| **Fleet, 0 windows, after** | **0.74** | **3.37** | **0.58** | **24.1** | **10.6%** | 1,010 |
| Fleet, 4 windows, before | 8.90 | 9.86 | 1.26 | 29.7 | 65.4% | 953 |
| **Fleet, 4 windows, after** | **0.54** | **6.06** | **0.68** | **24.4** | **36.0%** | 1,010 |

All cases hold 60 FPS before and after; the gains are in frame-time spikes and headroom. The largest single upload in a pass falls from 37 to 11 MB. In the fleet, about 6% of slot updates lay a buffer out again, mostly the first time a chunk changes. A first version with 1/8 of spare room used 16% more GPU memory for almost no further gain, so the room was reduced. Summaries: [before](evidence/phase7/p12/before-4k-capped-results.json), [after](evidence/phase7/p12/after-4k-capped-results.json), [slots without in-place patching](evidence/phase7/p12/slots-only-4k-capped-results.json).

## What is left

- **The fleet's retained geometry is about 1 GB of GPU memory and 590 MB of CPU memory at zoom 4**, where the whole 512² map is visible. This was already the case before this change (953 MB). Most of it is library art copied into every chunk, which priority 11 targets.
- **Snapshot scanning and preparation take about 2 ms per pass in the fleet**, and four vehicle windows still re-render every view when anything moves (priority 7).

## Correctness

- `tools/phase7-checks.ps1` passes the railway, construction and temperate (roaming) scenes. Each compares mesh and image references: 0 mesh mismatches in 24,437 comparisons, 0 missed chunks and 0 bounds failures. The image check renders sampled frames from the retained slot buffers and again from freshly projected CPU geometry; the largest difference is 0.007% of pixels (railway: 2,805 comparisons).
- New unit test `3D tile slots rewrite only changed tiles and keep the drawn buffer exact` simulates the buffer through 400 frames of cycling and growing tiles, checking for stale, overlapping or missing slots. `3D packed tile meshes match full regeneration` now also covers in-place edits.
- CTest is 113/115 (the two known savegame regressions).

## Reproduce

```powershell
.\tools\phase7-benchmark.ps1 -MapBits 6 -Windows 0,4 -Modes optimized -RunTag p12 -Resolution 3840,2160 -Capped
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 0,4 -Fleet -Zoom 4 -Modes optimized -RunTag p12 -Resolution 3840,2160 -Capped
.\tools\phase7-checks.ps1 -Scene railway
.\tools\phase7-checks.ps1 -Scene construction
.\tools\phase7-checks.ps1 -Scene temperate -Roam
```

Changed engine files: `src/video/terrain3d_slots.h` (new), `src/video/terrain3d_mesh.h`, `src/video/terrain3d_impl.h`, `src/video/proof3d_impl.h`; tests in `src/tests/terrain3d.cpp`.
