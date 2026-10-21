# Phase 7: retained static instance streams

Implemented 2026-10-19. Final long reruns were stopped at the user's request to finish the session. Phase 7 release acceptance remains open.

## Change

Static placements are retained by visible chunk set, with exact per-model comparisons when a chunk changes. Only affected model groups are gathered and uploaded. Variable model counts use bounded GPU slots, so tree growth no longer requires grouping and uploading the entire view. Model order, full detail, selection, transparency and each viewport's camera are preserved.

The cache owns CPU placement copies and GPU buffers, bounded to 16 entries and 32 MiB including slot capacity and metadata. Reload, eviction, chunk-size changes and context destruction are handled. `renderer_3d instancestreams off` retains the old diagnostic path; benchmark mode `streamed` selects it.

The benchmark verifier exposed duplicate write requests when a slot outgrew its allocation after earlier partial writes had been queued. `TileSlots::WriteAll` now replaces that queue. A new regression test covers the sequence. This also avoids duplicate terrain uploads through the same allocator.

## Verified and unfinished

The model-slot implementation passed all three broad railway, construction and temperate roaming/reload fixtures before the final duplicate-write cleanup:

- 22,967 mesh and 47,242 bounds comparisons: zero failures.
- 3,817 instanced/uniform image comparisons: zero differing pixels.
- 3,664 kept-image comparisons: zero stale pixels.
- 18,200 partial stream updates; all retention checks pass.
- The 4K direct-layer test passed 306 comparisons over 1,231,532,008 pixels with zero differences or OpenGL errors.

The final Release build contains the duplicate-write fix and its regression test. **118/118 final CTest tests pass**, including the new regression. The result is recorded in [tests.log](evidence/phase7/streams/tests.log). The final post-cleanup roaming fixture was interrupted, and the queued final timing/reverse-order/large-map runs were cancelled at the user's request. No final timing or post-cleanup full visual acceptance is claimed.

## Preliminary timings

Same-binary transient/retained pairs, RTX 3090, 3840 x 2160, full model detail and a 60 Hz cap; fleet is 512 square at zoom 4. These timings precede the duplicate-write fix. The fleet verifier rejected redundant uploads in some relayout frames; these are diagnostic measurements, not a passed final benchmark gate.

| Fleet windows | Drawing ms, transient / retained | Grouping ms, transient / retained | Instance uploads KiB/pass, transient / retained |
|---|---:|---:|---:|
| 0 | 4.06 / 2.96 | 1.049 / 0.188 | 2191.9 / 176.8 |
| 1 | 4.86 / 3.53 | 0.997 / 0.180 | 1746.9 / 140.3 |
| 4 | 7.08 / 5.58 | 0.964 / 0.213 | 1649.3 / 130.3 |

The six small-map cases passed their verifier before the cleanup and held 60 FPS. The four-window pair reduced uploads from 179.5 to 3.2 KiB/pass and drawing time from 2.45 to 2.39 ms. Larger fleet cases show the intended grouping and upload reduction, pending the clean final rerun.

Evidence: [preliminary fleet](evidence/phase7/streams/preliminary-fleet.json), [small map](evidence/phase7/streams/preliminary-demo.json), [layer](evidence/phase7/streams/layer-result.json), [current binary/source hashes](evidence/phase7/streams/environment.json), and raw broad-check and fleet logs alongside them.

## Resume here

Run the final Release CTest suite if needed, then repeat the focused visual gate and final timing pairs, with compiler/correctness processes stopped during timing:

```powershell
.\tools\phase7-checks.ps1 -Scene temperate -RunTag streams-final -StaticOnly -InstanceStreams -Roam
.\tools\verify-3d-layer.ps1 -RunTag streams-layer -Windows 4 -FastForward -Rotate -Blitter 40bpp-anim -Resolution '3840,2160' -Seconds 60
.\tools\phase7-benchmark.ps1 -MapBits 6 -Windows 0,1,4 -Modes streamed,optimized -RunTag streams-demo -Resolution '3840,2160' -Capped
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 0,1,4 -Fleet -Zoom 4 -Modes streamed,optimized -RunTag streams-fleet -Resolution '3840,2160' -Capped
.\tools\phase7-benchmark.ps1 -MapBits 9 -Windows 4 -Fleet -Zoom 4 -Modes optimized,streamed -RunTag streams-repeat -Resolution '3840,2160' -Capped
.\tools\phase7-benchmark.ps1 -MapBits 7,10 -Windows 0 -Modes streamed,optimized -RunTag streams-maps -Capped
```

Smaller screen updates, native interaction, long-session/cross-GPU checks and release packaging remain open. Existing user changes are preserved; no commit was made.
