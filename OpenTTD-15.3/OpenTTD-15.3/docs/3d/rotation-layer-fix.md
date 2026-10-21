# Rotation and delayed vehicle refresh diagnosis

The Phase 7 priority 7 layer-refresh optimization in `8abfd1b` could leave large areas of a viewport displaying old frames. Ctrl + right drag made the failure obvious; fast forward made stale vehicle positions look like delayed animation.

`DrawProof3D` renders a complete image even when the 2D drawing pass requests only a small dirty rectangle, then queues only that rectangle into the direct layer. At the end of the pass, `RefreshProof3DLayer` used a change in the render counter to decide whether to refresh the whole view. If the dirty rectangle had already caused that frame's render, the counter did not change during the refresh lookup, so the rest of the view was skipped. Only future dirty rectangles or a later full refresh repaired those pixels. This is a presentation failure; there is no queue of vehicle animation being replayed.

The fix assigns each rendered image a monotonically increasing revision and records the last fully queued revision separately for each viewport's layer ownership ID. A new image refreshes all pixels owned by that viewport, even if a small clip rendered it first. Shared cached images and recycled texture names cannot hide a pending refresh. Unchanged views keep their image and skip the layer draw. Layer ownership still protects overlapping windows.

## Verification

`renderer_3d verifylayer on` reads back the actual layer, its stencil ownership, and current viewport textures every 16th drawing frame. It compares visible transparent UI holes owned by each view with the corresponding current texture pixels. RGB differences greater than two are failures. It is disabled by default and does not disable direct presentation. The existing `verifygpu` checks select the readback path and consequently did not test this compositing failure.

On the unfixed renderer with this diagnostic added, an eight-second rotating fast-forward run failed 19 of 31 comparisons, with up to 1,008,263 stale pixels in a 1280 by 900 view. The repaired renderer produced:

| Scenario | Comparisons | Pixels compared | Failures |
|---|---:|---:|---:|
| Rotation, fast forward, no vehicle windows, 32bpp | 39 | 41,899,572 | 0 |
| Rotation, fast forward, four vehicle windows, 32bpp | 56 | 28,879,525 | 0 |
| Normal speed, rotated camera, four vehicle windows, 32bpp | 126 | 27,205,875 | 0 |
| Rotation, fast forward, four vehicle windows, 40bpp, 3840 by 2160 | 52 | 203,173,442 | 0 |

All runs reported zero OpenGL errors. The capped Release build succeeded and CTest passed **115/115**, including both savegame regression fixtures. Build/test logs are `.tmp/rotation-fix-build.log` and `.tmp/rotation-tests.log`. Comparison logs and JSON summaries are in `.runtime/rotation-before`, `rotation-after`, `rotation-after-windows`, `rotation-after-normal`, and `rotation-after-4k`.

With verification disabled, a ten-second normal-speed 4K run with four vehicle windows and a 90-degree camera measured 59.99 FPS, a 3.224 ms mean 3D draw pass, and a 20.259 ms p95 frame interval. GPU readback remained zero. This is a small fixture timing check, not a new fleet benchmark or a before/after performance comparison. Results: `.runtime/rotationperf-results.json`. The benchmark validator initially misparsed the hyphenated run tag as a map size; renaming the runtime folder to the supported single-word tag allowed all existing assertions to pass without changing the validator.

The regression script uses immediate console camera changes, which share the camera invalidation path with Ctrl + right drag. Native mouse gestures and the user's particular save have not been retested. The reported twenty-second recovery duration was not measured; the confirmed fault permits pixels to stay stale until another redraw reaches them.

```powershell
.\tools\verify-3d-layer.ps1 -RunTag rotation-check -FastForward -Rotate
.\tools\verify-3d-layer.ps1 -RunTag rotation-windows -Windows 4 -FastForward -Rotate
.\tools\verify-3d-layer.ps1 -RunTag rotation-normal -Windows 4
.\tools\verify-3d-layer.ps1 -RunTag rotation-4k -Windows 4 -FastForward -Rotate -Blitter 40bpp-anim -Resolution '3840,2160'
```

The script launches an isolated fixture with a unique configuration, samples the diagnostic, stops only its own process, and fails on stale pixels or GL errors. Disable the diagnostic when measuring performance because it deliberately synchronizes GPU readbacks.

## Starting the Release executable from Explorer

The multi-configuration build places matching language files and base data in `build/baseline`, while the executable is in `build/baseline/Release`. Double-clicking that executable initially failed with "No available language packs (invalid versions?)". Run `.\tools\prepare-release.ps1` after rebuilding to stage the matching data and the existing OpenGFX archive alongside the executable. The repaired layout was verified by starting the actual Release executable with Release as its working directory and no language or graphics folders in its isolated configuration directory; it generated `.runtime/release-startup-check/screenshot/release-startup.bmp` and exited normally.
