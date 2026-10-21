# Vehicle window stutter (2026-10-20)

The normal vehicle window could show its vehicle jumping ahead and recentering
on the next frame. The stationary main map did not have this camera mismatch.

`UpdateWindows` rendered current vehicle snapshots in `DrawDirtyBlocks` and
`EndProof3DFrame`, then called `UpdateViewportPosition`. Thus a following view
rendered a new vehicle position with the previous frame's camera. The direct
layer can update even when the 2D UI has no dirty blocks, making the mismatch
visible between UI redraws.

In 3D mode, viewport positions and cab/chase cameras now update before drawing.
Classic 2D retains its existing pixel-scroll and dirty-block order. Simulation
positions, game ticks, networking and saves are unchanged.

## Regression check

Run from the workspace root after building Release:

```powershell
.\tools\vehicle-follow-check.ps1 -RunTag follow-check
```

This runs the railway and air/water fixtures with shared camera yaw 0 and 90.
It checks the normal following view every frame, including cache reuse, and
requires moving vehicles of all four types. Each run also pauses before exit.
At `driver=3`, `3D FOLLOW` logs the difference between a following viewport's
actual virtual origin and the origin for its vehicle's current position. Both
components must be zero. Logs and result JSON stay under `.runtime`.

The same instrumented renderer was tested before and after changing frame order:

| Vehicle | Lagging samples before | Lagging samples after |
|---|---:|---:|
| Train | 350 / 760 | 0 / 757 |
| Road vehicle | 430 / 2280 | 0 / 2271 |
| Ship | 86 / 753 | 0 / 760 |
| Aircraft | 344 / 753 | 0 / 760 |
| Total | 1210 / 4546 | 0 / 4548 |

The Release build succeeds and CTest passes **126/126** tests. Paused railway
output was visually inspected with all four vehicle windows open.

`tools/phase9-checks.ps1 -RunTag vehicle-follow-compat` also passes: normal/cab/
chase transitions, shared-camera isolation, moving views and classic 2D/3D
switching. All 606 GPU comparisons remain within the existing tolerance; all
513 retained-image comparisons are exact.
