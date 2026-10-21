# Optional retro pixel display

Open **3D → Retro pixel settings**. The small floating panel stays open while
you compare settings. Pressed buttons indicate enabled options and the selected
pixel size. Close it with its close button or Escape.

- **Enable retro pixels** switches the whole treatment on or off. It defaults on.
- **1x / 2x / 3x / 4x** chooses the block size in physical viewport pixels. The
  initial choice is 3x. At 1x, only the enabled colour effects are applied.
- **Reduced colours** limits each RGB channel to eight levels (512 colours).
- **Subtle dithering** uses a restrained 4×4 Bayer pattern to transition between
  those colours. It requires reduced colours. Its saved preference is retained
  while disabled.

The default is 3x pixels with reduced colours and dithering off. Supported fresh
launches enable 3D for the title-screen world and new games. Existing saved
graphics choices take precedence; starting a new game does not reset them.
The colour and dithering effects remain optional. Preferences are client config
settings, excluded from saves and network synchronization. Classic 2D rendering
does not use them. Menus, text, map labels and other existing 2D overlays keep
their original resolution and colours.

## Implementation

`proof3d_impl.h` applies the effect while each 3D viewport texture is composited
into the existing layer. It samples the centre of each pixel block, clamps
incomplete edge blocks to the viewport, optionally quantizes colour, and dithers
per block. The grid is anchored to the viewport's top left, independently of
dirty clips, window positions, clipping and viewport height. Geometry, depth,
simulation and picking remain unchanged. There is no additional GPU render pass;
the world is still rendered at its original resolution, so pixelation does not
claim a rendering speedup.

Changing a preference repaints the screen, including paused and overlapping
views, while reusing the original source textures and meshes. The CPU readback
path applies the same treatment for offscreen screenshots and the diagnostic
readback compositor. The GPU layer verification compares actual compositing
against CPU sampling of the unfiltered source texture.

This is a filter of the current 3D art. Small rails and signals can lose detail
at larger block sizes, and moving fine details can shimmer. Use 1x or 2x for
management views. It does not generate handcrafted sprite art or lower the
simulation or animation frame rate.

## Validation

Build with the capped Release command from `build_and_test.md`, then run:

```powershell
.\tools\retro-pixels-check.ps1 -RunTag retro-pixels
```

The isolated fixture dispatches the real toolbar keyboard handlers and panel
button handlers. It captures all block sizes, independent colour/dither toggles,
off/on round trips, overlapping vehicle windows, cab/chase views, a configuration
restart using the 40bpp-anim blitter, and an 800×600 panel layout at 200% GUI scale.
It checks unfiltered restoration, 1x identity, palette values, flat pixel blocks,
unfiltered toolbar pixels, GPU/CPU compositing parity and saved preferences.
Native mouse input and OS DPI transitions are separate manual checks.

Results and captures are written to `.runtime/<RunTag>/`.

### Verified 2026-10-21

- Capped Release build passed. Existing shared-widget and terrain-math compiler
  warnings remain.
- CTest: **126/126 passed** in 15.65 seconds.
- Integration run: `.runtime/retro-pixels-final/check-results.json`; **180 GPU layer
  comparisons**, all valid with zero differing world pixels. All four block sizes,
  colour/dither toggles, original-image restoration, 1x identity, saved preferences,
  cab/chase views and both supported blitters passed.
- The panel was visually inspected at normal scale and at 200% in an 800×600
  window. Its controls and explanatory text fit. Native input was not exercised.

### Default update, 2026-10-21

Fresh profiles now enable 3D and 3x pixels, with reduced colours and dithering
off. The packaged launcher config explicitly matches these defaults. Saved
preferences remain authoritative across title screens, loads and new games.

The title screen and a newly generated 64x64 map were captured without any
renderer settings in the config. Both reported the intended defaults; every
sampled title-background block was a flat 3x3 block, and toggling the effect
off/on restored the new-game image exactly. Evidence:
`.runtime/retro-defaults-smoke/check-results.json`. The complete controls and
restart check also passed in `.runtime/retro-defaults-controls/`. CTest passed
**126/126** in 15.31 seconds.

The running original executable was locked by Windows, so the updated game
was linked alongside it as `build/baseline/Release/openttd-pixels3.exe` using
the same Release objects. No running game was interrupted.
