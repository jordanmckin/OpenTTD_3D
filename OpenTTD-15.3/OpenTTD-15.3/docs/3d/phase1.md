# Phase 1: optional depth-rendered viewport proof

Historical milestone: Phase 2 replaces this synthetic scene with real terrain. The current demo is `tools/phase2-demo.ps1`; this document and its screenshots describe the earlier proof.

## Scope

This is a synthetic presentation test inside the real OpenTTD session. It replaces world sprites with a fixed 32x32 flat tile patch and two coloured cubes, centred on the map's midpoint. Blue tiles mark the axes. It does not render real terrain, infrastructure, buildings or vehicles. Existing viewport labels remain visible. A persistent viewport label identifies the test scene. Use classic mode for actual construction until real terrain/picking are implemented.

No simulation, game commands, tick rates, networking packets, save fields or asset files are changed. The opt-in flag is process-local and is not serialized. Godot is not involved.

## Build and run

Use the toolchain and dependency setup in build_and_test.md. The current working build directory is reused to avoid another full duplicate build. Its executable now represents the experimental source rather than the historical Phase 0 binary.

```powershell
$cmake = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
& $cmake -S OpenTTD-15.3/OpenTTD-15.3 -B build/baseline -DOPTION_3D_PROOF=ON
& $cmake --build build/baseline --config Release --parallel 1 -- /p:CL_MPCount=2 /p:MultiProcMaxCount=2 /nodeReuse:false
```

The build option defaults to OFF. An enabled build still starts in ordinary 2D. The proof currently requires the `win32-opengl` backend, OpenGL 3.2+, and `40bpp-anim` or `32bpp-optimized`. It rejects unsupported blitters/drivers without altering the simulation. Missing GPU capabilities or framebuffer/shader failure logs an error and returns to 2D.

In the game console:

```text
scrollto instant 32 32
zoomto 2
renderer_3d on
renderer_3d viewport
renderer_3d off
```

The scroll coordinates above target the centre of the 64x64 fixture. `viewport` opens the game's existing additional-viewport window when the proof is enabled. Each viewport retains its own camera/zoom. The normal console toggle key and existing GUI controls are unchanged.

For a local demo from the workspace root, run `./tools/phase1-demo.ps1` in PowerShell. It launches the real game with the tested 32bpp-optimized blitter, uses the saved Phase 0 map, enables the proof, and pauses. It creates only an isolated `.runtime/phase1-demo` profile. It requires the local build and base-data copy from Phase 0; it does not build, download, or modify the normal user profile. Its syntax was checked with the PowerShell parser. The underlying launch arguments and startup commands were exercised by the graphics smoke runs; the launcher itself was not used to start another visible session.

## Implementation

- `video/proof3d.h`: narrow API with no-op fallback for builds without the option.
- `video/proof3d_impl.h`: private implementation included only in `opengl.cpp`, sharing the existing dynamic GL loader and shader diagnostics. No independent GL context or second engine.
- `opengl.cpp`: owns proof teardown with its context. No render work survives the current draw call.
- `viewport.cpp`: replaces the landscape/vehicle draw collection only if proof rendering succeeds. It retains label/effect handling and the existing clipped DrawPixelInfo. Windows and toolbars use their original paint path.
- `console_cmds.cpp`: local console opt-in, opt-out and additional-view command. No saved settings or game commands.
- CMake: disabled-by-default `OPTION_3D_PROOF`, limited to Windows GUI/OpenGL builds.

The renderer generates GPU triangles with per-face colours. It uses the classic affine projection `(2*(y-x), x+y-z)*ZOOM_BASE`, viewport offsets and integer zoom. Depth runs along the view direction. Ground triangles are submitted after cube triangles, intentionally exercising the depth buffer rather than relying on submission order.

An offscreen RGBA8 colour target and 24-bit depth attachment render one complete viewport. Synchronous BGRA readback supplies the original CPU framebuffer. Only each visible dirty rectangle is copied; top/bottom readback orientation is corrected. The 40bpp animation mask is zeroed over those copied pixels so old palette remaps cannot overwrite the 3D colours. Original windows keep their masks and colour data.

The pass saves/restores framebuffer bindings, renderbuffer, shader, VAO/VBO, pack/unpack buffers, texture unit/binding, viewport, readback packing, depth state, clear values, blending, culling and scissor state. Framebuffer attachments resize on demand. Context teardown releases all resources. CPU images are keyed by viewport size, camera, zoom and map dimensions; at most two images are cached. Static synthetic scene data does not depend on a live simulation pointer after the call. Oversized views (over 4096 in either dimension or 8 million pixels) fall back to classic rendering; giant screenshots therefore are not a supported 3D proof target.

The synchronous path runs within the existing drawing/game-state lock. It is intentionally a correctness proof, not the final performance solution. Cache misses log wall-clock microseconds for triangle generation, rendering and readback combined, including initialization on first use. These are not GPU-only timings or FPS claims. Labels and pixel copies still incur per-redraw work on cache hits.

## Validation record

Results on 2026-10-16:

| Check | Result / evidence |
| --- | --- |
| Release build with proof enabled | PASS; `evidence/phase1/phase1-build-final.log`. First build identified two GL pointer-name errors, corrected before the successful build. |
| Existing CTest suite | 96/96 PASS, 11.88 seconds; `evidence/phase1/phase1-tests.log`. |
| Disabled-option API | MSVC `/Zs` syntax check of the no-op header API passed. A second complete option-OFF build was not run; runtime 2D was verified in the enabled build. |
| Depth test / world projection | Cubes remain visible when the ground is submitted last. `evidence/phase1/phase1-world.bmp` shows the fixed grid, axes and cubes. This is visual proof, not an exhaustive numerical depth test. |
| Original GUI over 3D | Toolbar/status bar, frame-rate window and a second viewport render with correct clipping in `phase1-on-settled.bmp`. Initial capture was before the extra viewport camera initialized; a later frame verified its settled content. |
| 40bpp animation mask | PASS in the default OpenGL-selected 40bpp-anim mode; no residual sprite/palette pixels in the proof area. |
| 32bpp path / dimensions / GUI scaling | PASS at 1280x720, 200% GUI scale, 32bpp-optimized, and different main/secondary zooms; `phase1-large.bmp`. The 592x424 secondary viewport and the full-size main viewport exercise repeated FBO attachment resizing. |
| Switching off | PASS; `phase1-off.bmp` shows classic map rendering restored in both viewports without the proof label. Simulation progressed January through April while scripts enabled/disabled the proof. |
| Save/reload and unsupported renderer | PASS; save made while enabled reloaded under `win32` GDI + `8bpp-optimized`, rejected the 3D opt-in, advanced to March and saved again. `phase1-fallback.bmp`. |
| Live camera changes / normal shutdown | PASS; `phase1-pan.bmp` shows the main view panned/zoomed while the secondary retains its camera. The scheduled normal `exit` command completed with exit code 0 while 3D was active, exercising context/resource teardown. |

The source fixtures for the scripted checks are under `fixtures/phase1/` and `fixtures/phase1-large/`. The first run loads the Phase 0 save, enables 3D in February, captures settled secondary view in March, then disables 3D and pauses in April. Screenshots are application-generated CPU framebuffer captures, not Windows-desktop screenshots; GPU cursor appearance is therefore not proven by them. Run logs reside in `.runtime/phase1/`, `.runtime/phase1-large/`, and `.runtime/phase1-fallback/`.

The final live-camera/normal-exit script variant is in `fixtures/phase1-pan/`; use the same 1280x720 profile as the large test. All task-owned compiler and game processes were stopped after verification. Only API comments were added after the final successful executable build; no behavior changed afterward.

Measured uncached scene-generation/render/readback wall times: initial 1024x768 call 8.206 ms; subsequent main call 3.739 ms; smaller viewport calls 0.943-1.141 ms in that run. In the 1280x720 32bpp/200% run, initial main call was 6.448 ms and subsequent main call 2.517 ms; secondary calls were 4.720 and 0.712 ms. Cached frames avoid these calls. These results include CPU/driver/readback work and are specific to the tiny synthetic scene on this RTX 3090; they do not predict real-map performance.

Interactive Windows automation remains unavailable (`native pipe ... os error 2`). **Mouse-driven window resizing/movement, tooltips, cursor appearance, OS DPI transitions, context-loss recovery and direct construction interaction are not verified.** Startup at two resolutions/scales and multiple framebuffer dimensions does not substitute for a live resize test. Main camera pan/zoom is checked through the existing console commands. No free camera, real terrain, vehicle models, or NewGRF presentation is implemented.

The rendering proof is implemented and its automated/visual checks are recorded; retain the outstanding interactive checks before treating the entire Phase 1 acceptance gate as fully verified. Next development step remains real terrain and early tile picking, after reviewing this proof. Git's initial source import exists, but the environment prevents writes to `.git/index`; Phase 0/1 changes remain saved and uncommitted under that restriction.
