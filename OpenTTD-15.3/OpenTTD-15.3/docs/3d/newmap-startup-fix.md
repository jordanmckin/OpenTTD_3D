# New-map startup: stale terrain snapshots

Fixed and verified on 2026-10-20. This is a correctness fix before the planned 9.5g zoomed-out performance work.

## Defect and cause

The user reported dark, unfilled terrain patches on a newly generated large rectangular map, repaired by switching to classic and back to 3D. The defect reproduces with 3D enabled before creating a 2048x512 temperate map through the main-menu/new-game path. Terrain generation itself completes; the renderer retains snapshots captured before the terrain was finished.

Generation yields to progress-window drawing, which could enter `DrawProof3D` and snapshot intermediate tile heights and types. Generation does not issue ordinary dirty-tile notifications for every subsequent change. The separate direct-layer refresh checked `_generating_world`, but that flag is cleared during the tile-loop warm-up while the generation progress is still active. Toggling 3D repaired the view because enabling it resets the snapshots.

Both 3D draw paths now wait until modal generation progress ends. `CleanupGeneration` also resets CPU terrain snapshots so the next view reads the completed world, including a replacement map of the same dimensions. The reset sets flags only; it does not run GL operations in generation. Simulation, map data, commands, saves, detail and LOD settings are unchanged.

Changed engine files: `src/genworld.cpp`, `src/video/opengl.cpp`, and the generation guards in `src/video/proof3d_impl.h`. Regression tools: workspace `tools/newmap-3d-check.ps1` and `tools/verify-newmap-3d.py`.

## Verification

Release builds successfully and **124/124 CTest cases pass**. The rebuilt executable and matching data have been staged in `build/baseline/Release` using `tools/prepare-release.ps1`.

Each new-map regression starts with 3D already enabled, generates a seeded map, pauses, captures it, and compares it against either an off/on renderer reset or the independent full-snapshot reference. Screenshot notifications are disabled to keep the images comparable. The verifier also checks the actual allocated map dimensions and rejects missed dirty snapshots. The fixed first frame was visually inspected for the reported holes.

| Case | Path / reference | Result |
|---|---|---|
| Earlier binary, 2048x512, 32bpp | Main menu / off-on reset | Expected failure: 94,274 changed pixels; visible holes before reset |
| Fixed, 2048x512, 32bpp | Main menu / off-on reset | Images identical; first image visually inspected |
| Fixed, 2048x512, 40bpp | Main menu / off-on reset | Pass: zero changed pixels |
| Fixed, 512x2048, 32bpp | Main menu / off-on reset | Pass: zero changed pixels |
| Fixed, 2048x512, 32bpp | Main menu / full-snapshot reference | Pass: zero changed pixels, zero missed chunks/tiles |
| Fixed, 512x512, 32bpp | Direct new-game launch / full-snapshot reference | Pass: zero changed pixels, zero missed chunks/tiles |

An exploratory pre-fix full-snapshot run also found 259,475 stale tiles across 4,025 chunks, then zero on its second scan after the reference corrected them. Its large diagnostic log remains in `.runtime/newmap-before-dirty`; the table's repeatable pre-fix pixel comparison is preserved below.

Evidence: [before image](evidence/newmap-startup/before.png), [fixed image](evidence/newmap-startup/fixed.png), [expected pre-fix failure](evidence/newmap-startup/newmap-regression-before-results.json), [40bpp reset comparison](evidence/newmap-startup/newmap-fixed-2048x512-results.json), [reverse rectangle](evidence/newmap-startup/newmap-fixed-512x2048-results.json), [full-snapshot reference](evidence/newmap-startup/newmap-fixed-dirty-results.json), [direct startup](evidence/newmap-startup/newmap-fixed-direct-results.json), [build](evidence/newmap-startup/build.log), [tests](evidence/newmap-startup/tests.log). Compressed application logs and binary hashes accompany the results.

Reproduce from the workspace root with fresh run tags:

```powershell
.\tools\newmap-3d-check.ps1 -RunTag newmap-check
.\tools\newmap-3d-check.ps1 -RunTag newmap-check40 -Blitter 40bpp-anim
.\tools\newmap-3d-check.ps1 -RunTag newmap-check-tall -MapX 9 -MapY 11
.\tools\newmap-3d-check.ps1 -RunTag newmap-check-reference -VerifyDirty
.\tools\newmap-3d-check.ps1 -RunTag newmap-check-direct -MapX 9 -MapY 9 -DirectStart -VerifyDirty
```

These checks exercise application startup and rendering, not native mouse or monitor-DPI acceptance. No zoomed-out performance improvement is claimed; 9.5g must establish its own baseline and measured gate with LOD off.
