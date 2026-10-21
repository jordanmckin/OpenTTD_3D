# Rotated-view alpha checks, 2026-10-20

All four automated runs passed. No rotated picking or construction defect was
found in this coverage. Native mouse input and Windows monitor DPI transitions
remain unverified. The user's successful rotated-view playtest is recorded in
[the 9.5e report](phase95e-management.md).

## Packaged alpha recheck

The existing `OpenTTD-3d-alpha1-preview-m7a0aca3877-windows-x64` executable was
copied for console logging, with only its PE subsystem changed by `editbin`.
The packaged executable and release ZIP were left unchanged. This exercises the
packaged game code, using isolated profiles and the infrastructure save; it is
not another clean-machine portability test.

| Configuration | Ground checks | Vehicle actions | Label actions | Rail results | Captures | GPU comparisons |
|---|---:|---:|---:|---:|---:|---:|
| 100%, 32bpp-optimized | 11,264 | 27 | 129 | 21 | 31 | 0 |
| 200%, 40bpp-anim | 11,288 | 23 | 134 | 21 | 31 | 7 |

There were zero ground-picking failures. These reruns cover eight yaw angles,
tilts from 40% to 180%, slopes/foundations/bridge surroundings, six rail pieces,
preview/build/remove/cancel, rectangle/diagonal highlights, tool retention through
orbit/Home, cursor zoom, additional viewports, internal window overlap,
application resolution changes, map edges, classic/2D return, and rejection of
ground/vehicle targets in cab/chase views. The original verifier also checks
that rail preview pixels appear and disappear.

## Expanded construction checks

An updated diagnostic build adds explicitly invoked `renderer_3d managetool`
and `managestate` console helpers. Projected tile anchors pass through the actual
viewport inverse before the ordinary toolbar placement/drag/release callbacks
run. Those callbacks issue the existing game commands. A later diagnostic reads
authoritative tile state to verify the result. Rendering and gameplay algorithms
were not changed.

This build is distinct from the packaged alpha. Its construction and renderer
paths are unchanged; the added entry points make the additional checks possible.
Both executable hashes are retained in the environment files.

| Configuration | Tool callbacks | Map-state checks | Ground checks | Cursor zoom checks | Captures | GPU comparisons |
|---|---:|---:|---:|---:|---:|---:|
| 100%, 32bpp-optimized | 225 | 233 | 6,530 | 16 | 88 | 0 |
| 200%, 40bpp-anim | 225 | 233 | 6,530 | 16 | 88 | 11 |

Each run covers yaw 0/45/90/135/180/225/270/315 at tilt 100:

- Preview, Escape cancellation, build and remove roads in both map directions.
- Build rail and road depots; reject an incompatible depot on the occupied tile
  without replacing it; demolish the original depot.
- Drag-build and demolish a rail station; build and remove a signal on rail.
- Drag-build a rail bridge through its ordinary bridge picker and verify both
  endpoints; demolish it.
- Reject a tunnel on flat ground; build a rail tunnel through the fixture's real
  hill, verify both portals, then demolish it.
- Raise, lower and level terrain, checking corner heights and picking after the
  height change; preserve the cursor zoom anchor at every angle.
- Reset a road preview separately from the Escape key-handler check.

The expanded runs have zero picking failures. Across all four runs, **35,612
ground checks**, **450 additional tool callbacks**, and **466 additional map-state
checks** pass. All **18 GPU/reference comparisons** pass the existing 0.05%
pixel-difference limit; the largest difference is **0.007379%**. Representative
captures at both GUI scales were visually reviewed. Highlighted construction
areas in those captures are intentional active selections.

The Release rebuild succeeded and **126/126 CTest tests passed**, including both
savegame regressions. Correctness runs use GPU readback and are not performance
measurements. LOD remains off.

## Evidence and reproduction

[Summary](evidence/phase9/p5e-alpha/summary.json),
[capture gallery](evidence/phase9/p5e-alpha/gallery.html),
[source hashes](evidence/phase9/p5e-alpha/source-sha256.json),
[build log](evidence/phase9/p5e-alpha/rotated-checks-build.log), and
[test log](evidence/phase9/p5e-alpha/rotated-checks-tests.log).
Per-run result JSON, environment records, executed scripts and compressed logs
are in the same directory. Full temporary captures remain in the corresponding
workspace `.runtime` directories.

From the workspace root, use fresh run tags:

```powershell
$alphaExe = 'build/releases/OpenTTD-3d-alpha1-preview-m7a0aca3877-windows-x64/openttd.exe'
.\tools\phase95e-management.ps1 -RunTag alpha-rotated100 -Executable $alphaExe
.\tools\phase95e-management.ps1 -RunTag alpha-rotated200 -Scale 200 -Blitter 40bpp-anim -VerifyGPU -Executable $alphaExe
# Rebuild the development executable first to include the new diagnostic helpers.
.\tools\phase95e-management.ps1 -RunTag construction100 -Construction
.\tools\phase95e-management.ps1 -RunTag construction200 -Scale 200 -Blitter 40bpp-anim -VerifyGPU -Construction
```

## Native checks still open

The computer-use skill requires `node_repl`, which is not exposed in this
session. The checks above dispatch application callbacks and scoped internal
cursor state; they do not inject native mouse input. GUI scale 200% is not a
Windows monitor DPI transition. No scripted result is marked as native acceptance.

For a hands-on review, run `.\tools\phase95e-demo.ps1 -Show`. It uses an isolated
profile and starts paused with construction allowed. At classic, 45 and 90
degrees, check the following with the physical mouse:

- Click vehicle/wagon bodies and labels, including where labels overlap models.
- Drag rail and roads, and place stations, depots, signals, bridges and tunnels;
  inspect the hover measurement tooltip and cancel drags with Escape/right-click.
- Rotate/tilt with a tool active; switch Home/2D; pan and cursor-zoom to map edges.
  Confirm cancellation/transitions never submit an unintended build.
- Put an internal window over the target and confirm the click acts on that
  window. Check additional map and vehicle views; cab/chase remain spectator-only.
- Resize the native window border, maximize/restore, minimize/restore and Alt+Tab
  while paused and running. Move between monitors with different Windows DPI
  settings if available.

The callbacks bypass native pointer event routing and widget hit-testing, so
these physical-input checks remain useful even though the command results pass.
Clean-PC startup and smaller-GPU/long-play tests remain separate alpha checks.
