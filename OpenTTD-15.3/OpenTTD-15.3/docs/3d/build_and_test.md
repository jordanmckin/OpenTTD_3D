# Phase 0 build and test record

Date: 2026-10-16. Run commands from `D:\G ttd` unless stated otherwise. Source is the supplied 15.3 archive; workspace baseline commit `b850d81`. No game source was modified for Phase 0. Exact upstream commit is unknown; see architecture_audit.md for the archive/version-metadata limitation.

## Machine and toolchain

- Windows 10 build 19045, x64 target.
- Visual Studio Build Tools 2022 17.14; MSVC compiler 19.44.35209, toolset directory 14.44.35207.
- Windows SDK 10.0.26100.0 selected by CMake.
- CMake 3.31.6-msvc6 bundled with Build Tools (not on the ordinary shell PATH).
- Git 2.38.1.windows.1. Repository initialized on `main` at workspace root.
- Existing Miniconda installation supplies `Library/include/lzma.h`, `zlib.h`, `Library/lib/lzma.lib`, `zlib.lib`, and runtime DLLs `liblzma.dll`, `zlib.dll`. This is a local baseline dependency route, not a reproducible release dependency pin. Prefer the source's vcpkg manifest for future release builds.
- OpenGL found as the Windows system library. PNG, LZO, breakpad and optional Opus/Ogg libraries were not found. Missing PNG means BMP screenshots for this baseline. Missing LZO limits legacy saves; sound/music are disabled in the smoke launch.

## Configure and build

```powershell
$cmake = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
& $cmake -S OpenTTD-15.3/OpenTTD-15.3 -B build/baseline `
  -G 'Visual Studio 17 2022' -A x64 `
  '-DCMAKE_GENERATOR_INSTANCE=C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools' `
  '-DLIBLZMA_INCLUDE_DIR=C:/Users/8bits/miniconda3/Library/include' `
  '-DLIBLZMA_LIBRARY=C:/Users/8bits/miniconda3/Library/lib/lzma.lib' `
  '-DZLIB_INCLUDE_DIR=C:/Users/8bits/miniconda3/Library/include' `
  '-DZLIB_LIBRARY=C:/Users/8bits/miniconda3/Library/lib/zlib.lib'
& $cmake --build build/baseline --config Release --parallel 1 -- /p:CL_MPCount=2 /p:MultiProcMaxCount=2 /nodeReuse:false
```

Output executables are `build/baseline/Release/openttd.exe` and `openttd_test.exe`; base descriptors and language data are in `build/baseline/baseset` and `lang`. Run the game with working directory `build/baseline`, not `Release` or the isolated config folder, so its data can be found.

CPU budget: one MSBuild project at a time and at most two parallel compiler workers. `--parallel 1` alone does not cap MSVC's `/MP` setting; the initial builds caused excessive CPU use and were stopped on user feedback. `Microsoft.Cl.Common.props` maps `CL_MPCount` to the compiler's ProcessorNumber. Use the capped command above for future builds.

Copy the dynamic dependencies beside the executables and into the build root (regression tests copy the game there):

```powershell
$runtimeDlls = @(
  'C:\Users\8bits\miniconda3\Library\bin\liblzma.dll',
  'C:\Users\8bits\miniconda3\Library\bin\zlib.dll'
)
Copy-Item -LiteralPath $runtimeDlls -Destination build/baseline/Release/
Copy-Item -LiteralPath $runtimeDlls -Destination build/baseline/
```

Initial configuration without explicit dependency paths succeeded but omitted LZMA/zlib. Its single-worker Release build succeeded with 0 errors and 10 warnings in 4m36s. Existing warnings included unused parameters in network/survey code and potential divide-by-zero warnings in widget.cpp. Earlier `--parallel 6` and `--parallel 2` attempts exited 1 with no useful diagnostic; `--parallel 1` succeeded. The single-worker diagnostic log is `build/baseline-diagnostic.log`; corrected configure/build logs are `build/baseline-configure.log` and `build/baseline-build.log`.

## Existing tests

```powershell
& 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\ctest.exe' `
  --test-dir build/baseline -C Release --output-on-failure
```

The first run passed 94/96 tests in 12.68s. Both failures were existing regression fixtures (`regression_regression`, `regression_stationlist`). Direct replay confirmed: `Internal error: Loader for 'lzma' is not available.` This also affects the title-screen save. An executable exit code of zero alone is insufficient: the null-video replay exited zero despite printing load failures. Reconfigure with the dependencies above and rerun all tests; final result is recorded below.

## Isolated baseline map

The checked-in fixtures contain a 64x64 temperate map configuration and game-start scripts that wait until the next calendar month, save the map, request a screenshot, then pause. Seed is 20261016, start year 1950. Waiting avoids capturing the generation-progress window. The screenshot script requires a real graphical backend (the null driver forces the null blitter). Base models are still 2D; no 3D exists yet.

```powershell
New-Item -ItemType Directory -Force .runtime/baseline/baseset,.runtime/baseline/scripts | Out-Null
Copy-Item OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures/baseline.cfg .runtime/baseline/openttd.cfg
Copy-Item OpenTTD-15.3/OpenTTD-15.3/docs/3d/fixtures/*.scr .runtime/baseline/scripts/
Copy-Item -LiteralPath 'C:\Users\8bits\Documents\OpenTTD\content_download\baseset\4f474658-OpenGFX-7.1.tar' -Destination .runtime/baseline/baseset/
Push-Location build/baseline
try {
  & .\Release\openttd.exe -c 'D:\G ttd\.runtime\baseline\openttd.cfg' `
    -x -X -QQ -I OpenGFX -v win32-opengl -s null -m null -g -G 20261016
} finally { Pop-Location }
```

`-c` isolates config/personal paths, `-x` disables configuration writes, `-X` excludes global search paths, and `-QQ` disables gameplay NewGRF scanning/loading. Original user saves/configuration are not copied. Only OpenGFX 7.1 was copied into the workspace. Keep its included license notices; it is not committed as part of the source. Saves and screenshots go under `.runtime/baseline/`.

The Windows computer-use helper returned `Computer Use native pipe is unavailable ... The system cannot find the file specified (os error 2)` on both attempts. Consequently no interactive GUI smoke result can be claimed from that tool. A CLI launch and app-generated screenshot can verify startup/rendering, but not mouse interaction, window overlap, resizing or DPI behavior.

The successful graphical smoke used a console-subsystem copy of the built executable, matching the existing regression harness technique, so startup diagnostics were captured. No game source or logic was changed. The initial direct GUI launches did not yield useful diagnostics and were stopped. Exact successful preparation/launch from workspace root:

```powershell
Copy-Item build/baseline/Release/openttd.exe build/baseline/openttd-console.exe
& 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\editbin.exe' /nologo /subsystem:console build/baseline/openttd-console.exe
& .\build\baseline\openttd-console.exe -c '.runtime/baseline/openttd.cfg' `
  -x -X -QQ -I OpenGFX -v win32-opengl -s null -m null `
  -g '.runtime/baseline/save/phase0-baseline.sav' -d driver=1,misc=1
```

To replay the saved fixture, first copy `docs/3d/fixtures/phase0-baseline.sav` from the source root into `.runtime/baseline/save/`. The original fixture was saved immediately after generation; the scheduled capture waits until February 1, 1950, then writes `phase0-reloaded.sav` and `phase0-reloaded.bmp` in the isolated save/screenshot folders and pauses. The screenshot is a CPU framebuffer capture produced by the game; the log separately confirms the active OpenGL driver. It is not a GPU frame-time measurement or proof of GPU presentation/cursor correctness.

## Final results and gate

- Corrected capped Release build: **PASS**, exit 0. Log: `evidence/build.txt`.
- CTest: **96/96 PASS**, 11.33 seconds, exit 0. Log: `evidence/ctest.txt`. Both LZMA-related failures are resolved.
- Graphics startup: **PASS** in the console-subsystem copy; log reports `win32-opengl`, NVIDIA GeForce RTX 3090, OpenGL 4.5. The backend automatically selected `40bpp-anim`; Phase 1 must explicitly account for its separate animation buffer or restrict the prototype blitter.
- New map and save: **PASS**, seed 20261016, 64x64 temperate, original simulation. Reusable save: `fixtures/phase0-baseline.sav` (uncompressed as configured).
- Reload and time advancement: **PASS**; February 1, 1950 capture after one in-game month, with pause requested by script. See `evidence/phase0-reloaded.bmp`, visually inspected for normal world rendering and original toolbar/status bar.
- Interactive mouse/keyboard, resize, DPI, window overlap, audio, multiplayer and performance profiling: **NOT TESTED**. The native automation helper is unavailable; these are explicit follow-up checks, not claimed passes.
- Initial screenshot caught the generation-progress window; the delayed capture replaced it as the useful visual evidence. Missing original commercial base-data warnings are expected while scanning descriptors; OpenGFX is installed and renders successfully.
- All task-owned game/compiler processes were stopped after verification. The corrected build was interrupted once on CPU feedback, then resumed successfully with the two-worker limit.

**Phase 0 baseline gate is met:** unchanged game source builds, all existing tests pass, and a real OpenGL-backed session generates, saves and reloads a small map. Interactive GUI verification remains outstanding for Phase 1's compositor work. No renderer, simulation, command, save format, or asset changes were made. No FPS/GPU measurements are available. Stop here for review; next smallest task is the opt-in depth-tested viewport proof in architecture_audit.md.
