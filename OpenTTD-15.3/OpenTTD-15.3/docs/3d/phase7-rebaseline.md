# Phase 7 priority 6: re-baseline with the Phase 8 art

Status (2026-10-18): measured. The renderer is not limited by triangles or GPU time. A frame's cost is set by screen resolution: the 3D image is read back from the GPU, copied into the 2D screen buffer, the whole screen is redrawn, and then the whole screen is uploaded back to the GPU. Any vehicle movement repeats this for every open view on every game tick. At the user's 3840×2160 display, the simple demo scene can't hold an even 60 Hz with one view and drops further with four.

## New measurements

- `PHASE7 present` (driver debug level 2) times each completed draw tick from `VideoDriver::Tick`:
  - `work_us`: input, window drawing including 3D, painting and presentation.
  - `paint_us`: the backend's `Paint` and the buffer swap.
  - `interval_us`: time between presented frames.
  - `game_us` / `game_ticks`: game-loop time spent since the previous frame.
- `tools/verify-phase7.py` reports, per case:
  - FPS (1e6 / mean interval) and p50/p95/p99 frame times.
  - The share of frames that redraw any 3D view.
  - Game-tick cost per frame.
- Benchmarks run with `refresh_rate = 1000` by default, so frame cost is not hidden below the 60 Hz draw interval. `-Capped` keeps the normal 60 Hz rate, which is what a player sees.
- New options: `-Resolution W,H` and `-Zoom N`. `-Fleet` reloads `fixtures/phase7/fleet/fleet-9.sav`.
- `tools/phase7-fleet.ps1` generates the fleet save. It is a 512² map with 184 towns, and its fixture AI builds through ordinary commands:
  - 288 buses in the 12 towns nearest the centre;
  - 12 shuttle trains of 5 vehicles each: 348 vehicles in all.
- When the whole 64² map is visible, the verifier no longer requires pending offscreen chunks.

## Results (2026-10-18)

Windows x64 Release, RTX 3090 / NVIDIA 610.74, optimized mode, OpenGL, 32bpp-optimized. One sequential trial per case. 3D times are means over the draw passes that drew a 3D view.

| Case | FPS | p50 frame ms | p95 frame ms | Frames redrawing 3D | Renders per pass | Draw pass ms | Readback ms | GPU ms | Paint ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Demo railway 64², 1280×900, 0 windows | 953 | 0.71 | 2.58 | 3% | 0.89 | 3.41 | 0.76 | 0.48 | 0.62 |
| Demo, 1280×900, 4 windows | 784 | 0.73 | 2.98 | 8% | 3.24 | 4.14 | 0.89 | 0.48 | 0.64 |
| Demo, 3840×2160, 0 windows | 162 | 3.19 | 17.24 | 22% | 0.90 | 12.18 | 3.45 | 1.11 | 2.90 |
| Demo, 3840×2160, 1 window | 126 | 4.22 | 21.31 | 36% | 1.50 | 11.47 | 2.97 | 0.90 | 2.89 |
| Demo, 3840×2160, 4 windows | 71 | 9.37 | 30.18 | 60% | 4.16 | 16.18 | 4.08 | 1.09 | 2.91 |
| **Demo, 3840×2160, 0 windows, 60 Hz cap** | 60.0 | 18.81 | 31.58 | 56% | 0.95 | 14.26 | 4.11 | 1.33 | 3.29 |
| **Demo, 3840×2160, 4 windows, 60 Hz cap** | 52.1 | 24.82 | 35.18 | 75% | 4.36 | 17.91 | 4.58 | 1.24 | 2.94 |
| Fleet 512², 1280×900, zoom 2, 0 windows | 985 | 0.71 | 2.60 | 5% | 0.75 | 2.36 | 0.58 | 0.17 | 0.62 |
| Fleet, zoom 5 (farthest), 4 windows | 421 | 0.76 | 15.32 | 15% | 3.93 | 9.53 | 2.25 | 2.60 | 0.67 |
| Fleet, 2560×1440, zoom 4, 0 windows | 229 | 1.63 | 16.95 | 16% | 0.92 | 14.88 | 3.98 | 3.78 | 1.53 |
| Fleet, 2560×1440, zoom 4, 4 windows | 135 | 2.03 | 20.64 | 41% | 4.06 | 13.17 | 2.85 | 2.35 | 1.50 |

The complete summaries are in [evidence/phase7/second-pass](evidence/phase7/second-pass/).

## Findings

1. **The cost grows with the number of pixels, not triangles.**
   - At 3840×2160, a 3D draw pass takes 14–18 ms, but GPU triangle time is only 1.1–1.3 ms.
   - The remaining CPU-side cost is about 12–16 ms, made up of:
     - `glReadPixels` (about 4 ms);
     - allocating and zero-filling a new 33 MB image for each render, because the cache was just cleared;
     - copying the image into the screen buffer and redrawing the whole UI;
     - the backend's full-screen texture upload in `Paint` (about 3 ms).
   - The 348-vehicle fleet with Phase 8 art costs less than the 64² demo at the same resolution.
2. **3D redraws happen on every game tick while anything moves.**
   - `RefreshTrains3D` and `RefreshEffects3D` clear every cached view and call `MarkWholeScreenDirty()` whenever any vehicle or effect changes. Vehicle windows also follow moving vehicles.
   - With the 60 Hz cap at 4K, 56% of frames redraw 3D with no windows open and 75% with four. Each of those frames takes about one full 16.7 ms budget.
   - This gives the judder the user reports: p50 18.8 ms and p95 31.6 ms, rising to p50 24.8 ms / p95 35.2 ms with four windows (an average of 52 FPS).
3. **The other suspects are cheap.**
   - Snapshot scanning averages 0.4 ms. Animated tiles trigger snapshot re-reads but almost no rebuilds (priority 12).
   - Chunk rebuilds and uploads are near zero in steady state.
   - Game ticks cost 0.01 ms per frame.
   - Zoomed-out views at 1280×900 stay under 10 ms per pass even with 356 resident chunks.

## Consequence for the roadmap

Priority 8 (remove readback and draw the 3D view directly beneath the 2D UI) goes first: it removes the readback, the image allocation, the copy and most of the per-pixel CPU work. Priority 7 (limit invalidation to the views a change touches) follows. Priorities 9–11 (instancing, LOD, static instancing) target GPU and triangle costs, which these measurements show are not the current bottleneck. They stay planned and will be re-measured after 8 and 7.

## Reproduce

```powershell
.\tools\phase7-fleet.ps1 -MapBits 9
.\tools\phase7-benchmark.ps1 -MapBits 6 -Windows 0,1,4 -Modes optimized -RunTag p7demo -Resolution 3840,2160
.\tools\phase7-benchmark.ps1 -MapBits 6 -Windows 0,4 -Modes optimized -RunTag p7cap -Resolution 3840,2160 -Capped
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 0,4 -Fleet -Zoom 4 -Modes optimized -RunTag p7b -Resolution 2560,1440
```

Benchmark windows are hidden, so the window is set to its configured size. The draw-pass breakdown fields are those of [phase7.md](phase7.md#reproduce). The changed engine files are `src/video/video_driver.cpp` (two timing calls), `src/video/proof3d.h`, `src/video/proof3d_impl.h` and `src/video/opengl.cpp`. Simulation, saves, commands and network behaviour are unchanged.
