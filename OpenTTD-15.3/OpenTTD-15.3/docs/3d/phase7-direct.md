# Phase 7 priority 8: draw the 3D view beneath the 2D UI

Status (2026-10-18): implemented and measured. On-screen 3D views no longer go through the CPU. Each view is rendered into a texture that stays on the GPU. That texture is composited beneath the 2D UI when the frame is presented. Vehicle and effect movement re-renders the views on the GPU without redrawing or re-uploading the 2D screen.

At the user's 3840×2160 display with the 60 Hz cap, CPU work per frame falls from 12.3 to 5.4 ms with no vehicle windows open. With four windows it falls from 18.0 to 6.6 ms, and the frame rate rises from 52.5 to a steady 60 FPS.

## How it works

- **Views stay on the GPU.** `RenderProofImage` renders a view into its own retained texture instead of reading it back with `glReadPixels`. The image cache keeps these textures under the same 32-view / 128 MiB budget. Textures that are released are reused for later renders of the same size.
- **A screen layer sits beneath the UI.** For each clip of a view drawn into the 2D buffer, `DrawProof3D` writes transparent pixels (alpha 0) and queues a draw of that clip into a screen-sized layer. `OpenGLBackend::Paint` draws the layer first, then blends the 2D buffer over it, so the holes show the 3D views. Everything else in the UI is opaque, as before.
- **The stencil records which view owns each pixel.** A drawn clip writes its view's number into the layer's stencil. When only 3D content changes (vehicles, effects, terrain, selection, visibility or the camera), `InvalidateProof3DImages` marks the layer stale instead of calling `MarkWholeScreenDirty`. At the end of the drawing pass, each open view is re-rendered and redrawn only where the stencil says it owns the pixel. This also keeps window stacking correct: a vehicle window above the main view keeps its own pixels.
- **The layer and the UI present the same frame.** The backend uploads the 2D buffer when it is released after `Paint`, so the buffer on screen is always one tick old. Layer draws are therefore queued while drawing and run in `OpenGLBackend::ReleaseVideoBuffer`, together with that upload. Without this, a dragged window would show the wrong view for one frame. A released texture is not reused until the queue has run.
- **Screenshots and fallbacks.** Screen screenshots replace the transparent pixels with the layer (`ResolveProof3DScreenshot`). Giant/world screenshots draw into their own buffer and keep the read-back path. `renderer_3d verifygpu` also keeps read-back, because its reference comparison needs CPU pixels. If rendering fails, the renderer reverts to classic 2D, as before. The 40bpp-anim blitter keeps working: its animation buffer is cleared under the holes as before.
- **Timer queries no longer stall.** In direct mode, GPU times are collected from a ring of eight queries a few renders later, instead of waiting for the GPU after every render. This only affects driver debug level 2.

`renderer_3d performance readback` is the optimized policy with the previous read-back and CPU compositing; `optimized` (the default) uses direct presentation. Both are in the same executable for A/B measurement. Simulation, saves, commands and network behaviour are unchanged.

## Results (2026-10-18)

Windows x64 Release, RTX 3090 / NVIDIA 610.74, 32bpp-optimized, the 64² demo railway. One sequential trial per case, with the same executable in both modes. CPU work is `work_us` from `PHASE7 present`: input, window drawing including 3D, painting and presentation.

### 3840×2160, 60 Hz cap (what the player sees)

| Case | FPS | p50 / p95 frame ms | CPU work ms | 3D draw pass ms | Readback ms | Paint ms |
|---|---:|---:|---:|---:|---:|---:|
| 0 windows, readback | 60.0 | 18.65 / 31.19 | 12.28 | 13.65 | 3.87 | 3.23 |
| **0 windows, direct** | **60.0** | **16.62 / 23.69** | **5.45** | **1.78** | 0 | 4.24 |
| 4 windows, readback | 52.5 | 24.49 / 34.19 | 18.03 | 17.43 | 4.42 | 2.97 |
| **4 windows, direct** | **60.0** | **16.68 / 24.13** | **6.60** | **3.33** | 0 | 3.47 |

### 3840×2160, uncapped (headroom)

| Case | Readback FPS | Direct FPS | Readback p95 ms | Direct p95 ms | CPU work ms (readback → direct) |
|---|---:|---:|---:|---:|---:|
| 0 windows | 158.9 | **290.8** | 18.25 | **4.51** | 6.16 → 3.29 |
| 1 window | 108.6 | **280.0** | 24.91 | **5.16** | 9.06 → 3.43 |
| 4 windows | 57.7 | **242.0** | 33.25 | **7.14** | 17.10 → 4.00 |

### 512² fleet (348 vehicles), zoom 4, 3840×2160, 60 Hz cap

| Case | FPS | p50 / p95 frame ms | CPU work ms | 3D draw pass ms | Readback ms | GPU ms |
|---|---:|---:|---:|---:|---:|---:|
| 0 windows, readback | 31.6 | 30.96 / 39.79 | 31.48 | 25.82 | 4.58 | 9.44 |
| **0 windows, direct** | **60.0** | **16.60 / 29.49** | **10.06** | **8.44** | 0 | 5.27 |
| 4 windows, readback | 23.8 | 41.34 / 49.88 | 41.90 | 36.00 | 6.53 | 11.14 |
| **4 windows, direct** | **60.0** | **17.30 / 29.82** | **12.59** | **9.74** | 0 | 3.52 |

With the old path, every frame of the fleet redrew 3D. Now 62–87% of frames re-render a view, but only on the GPU. Most of the fleet's remaining 8–10 ms draw pass is re-uploading changed chunk meshes: an average of 8.5–11.5 MB per pass, taking 3.6–4.9 ms. Snapshot scanning adds another 1.6–1.8 ms. Both come from tile changes across the busy towns, which is what priorities 12 and 3 target.

The readback rows reproduce the [priority 6 rebaseline](phase7-rebaseline.md) (162 / 126 / 71 FPS uncapped there). Summaries: [capped](evidence/phase7/direct/capped-4k-results.json), [uncapped](evidence/phase7/direct/uncapped-4k-results.json), [fleet](evidence/phase7/direct/fleet-4k-capped-results.json).

## What is left in the frame

- **Paint is now the floor**, about 3 ms at 4K: drawing two full-screen quads and the buffer swap. Uncapped, this limits the demo to about 300 FPS.
- **Remaining capped spikes come from chunk re-uploads, not presentation.** About 9% of capped frames still take ~12 ms of CPU work. In each of them, a changed chunk is rebuilt and its whole mesh (about 6 MB) is uploaded again; mesh preparation averages 4.8 ms, against 0.2 ms in other frames. These rebuilds come from animated or growing tiles. They are the subject of priority 12 (animated-tile churn) and priority 3 (narrower geometry patches).
- **Every open view is re-rendered when anything moves.** Each re-render is a GPU draw of about 1 ms, with no CPU pixel work. Priority 7 limits it to the views a change touches.
- **Classic dirty rectangles still redraw small parts of the 2D UI** when a vehicle moves, because the original vehicle code marks its sprite bounds dirty. Each such clip now writes transparent pixels instead of copying 3D pixels.

## Correctness

- **Direct and read-back frames match except on text over a 3D view.** `tools/phase7-direct-compare.ps1` loads the railway save paused, opens three vehicle windows and takes a screenshot in each mode. Every 3D pixel matches. Differences are limited to the anti-aliased edges of the 2D text drawn over a view (the "3D TRANSPORT" banner): 0.37% of the screen with the classic camera and 0.73% with the rotated camera (`-Camera "40 70"`), which shows a second banner line. In direct mode these edge pixels blend with the transparent hole (black) instead of the terrain, giving a slightly darker one-pixel fringe ([comparison](evidence/phase7/direct/text-fringe-direct-top-readback-bottom.png), [diff mask](evidence/phase7/direct/direct-vs-readback-rotated-diff.png)). Any other partly transparent 2D drawing over a 3D view would show the same fringe.
- **The presented window was captured from the screen.** It shows the main view and two vehicle windows correctly stacked, under the original UI ([presented window](evidence/phase7/direct/presented-window.png)). An in-game screenshot of the same run contains no holes ([screenshot](evidence/phase7/direct/screenshot-direct.png)).
- **The read-back path still passes.** The railway correctness scene (`tools/phase7-checks.ps1 -Scene railway`), which uses `verifygpu` and therefore read-back, passes with 2,827 image comparisons and no bounds failures.
- **Build and tests:** the capped Release build passes, and CTest is 112/114 (the two known savegame regressions).

Not verified: interactive mouse dragging of windows over views at 4K on the user's display, and the 40bpp-anim blitter in direct mode. Both use the same code paths as the checks above.

## Reproduce

```powershell
.\tools\phase7-benchmark.ps1 -MapBits 6 -Windows 0,4 -Modes readback,optimized -RunTag p8cap -Resolution 3840,2160 -Capped
.\tools\phase7-benchmark.ps1 -MapBits 6 -Windows 0,1,4 -Modes readback,optimized -RunTag p8demo -Resolution 3840,2160
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 0,4 -Fleet -Zoom 4 -Modes readback,optimized -RunTag p8fleet -Resolution 3840,2160 -Capped
.\tools\phase7-direct-compare.ps1
.\tools\phase7-direct-compare.ps1 -Camera "40 70"
```

`tools/phase7-benchmark.ps1` now normalizes `-Resolution`: when it is called from PowerShell, `3840,2160` arrives as the text `3840 2160`, which would otherwise produce an invalid `resolution` setting. `PHASE7 present` now also reports `renders`, and the verifier reports `frames_with_3d_render`. `PHASE7 frame` reports `direct`, `layer_draws` and `layer_refreshes`.

Changed engine files: `src/video/proof3d_impl.h`, `src/video/proof3d.h`, `src/video/terrain3d_impl.h`, `src/video/rail3d_impl.h`, `src/video/opengl.cpp`, `src/screenshot.cpp` and `src/console_cmds.cpp`.
