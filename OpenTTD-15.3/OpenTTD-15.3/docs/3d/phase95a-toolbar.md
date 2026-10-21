# Phase 9.5a: toolbar access and client preferences

User approval: **approved 2026-10-19**; proceed to 9.5b. The native-input limitations below remain the historical verification record.

The main game toolbar has a **3D** text button in the complete layout and in both rows of every collapsed layout. Its dropdown shows the current display state, a checked Enable 3D option, textured terrain and camera hint preferences, building/orbit camera controls, and camera help. **Ctrl+Alt+3** opens it by default (`maintoolbar.3d_menu` in `hotkeys.cfg`). Up/Down skip disabled rows and separators, Enter chooses, and Escape dismisses without selecting.

Enable 3D, textured terrain and camera hints are client settings (`gui.renderer_3d`, `gui.renderer_3d_ground_textures`, `gui.renderer_3d_camera_hints`). They use OpenTTD's existing configuration save lifecycle. They are excluded from saves and network synchronization. The first defaults to false; the other two default to true. Ordinary configuration writes must be enabled; the existing `-x` option deliberately prevents persistence. Camera angles and individual vehicle ride modes remain session state. LOD stays off; the menu exposes no LOD switch.

Full config loading applies the preferences after driver startup. Windows OpenGL with `32bpp-optimized` or `40bpp-anim` supports the renderer. Other drivers/builds keep classic 2D and show an unavailable status with Enable 3D disabled. The stored preference survives fallback for the next supported launch. Rendering failures retain the existing classic fallback. Temporary development console renderer commands remain diagnostic overrides; using the toolbar restores agreement with the saved enable preference.

The development banner is removed. Optional orbit and ride hints remain; help describes map controls, vehicle camera controls, current interaction limits, configuration persistence and compatibility. Existing construction tools still return the management camera to its building angle; rotated construction is a later slice.

## Verification

Run from the workspace root with a fresh tag:

```powershell
.\tools\phase95a-toolbar.ps1 -RunTag phase95a-toolbar
```

The isolated fixture dispatches actual application toolbar and keyboard events, takes app-generated screenshots, and restarts the executable with config writes enabled. It covers fresh opt-in, escape cancellation, enable/disable, help over the map, preference changes, orbit and return, supported restarts, 800x600 and 1280x900 resize, both collapsed toolbar rows, software driver fallback, restoration, the animated blitter, persistence of disabling, and 200% UI scaling. The verifier checks live states, on-screen button bounds, saved configuration and large-area image changes. It does not inject native mouse events.

Native mouse and DPI-transition acceptance remains pending: this session has no computer-use JavaScript tool. The skill's required `@oai/sky` entry point cannot be invoked; no substitute OS input automation is used.

Release build and **123/123 CTest cases pass**. The scripted run verifies **19 named states and 18 screenshots** across seven launches. Its first launch uses automatic driver/blitter selection (Windows OpenGL selects `40bpp-anim` on this machine); subsequent cases explicitly exercise `32bpp-optimized`, `40bpp-anim` and software `win32`. Both collapsed rows are checked at 200% scaling, including a pixel comparison proving that the displayed toolbar row changes. Help is captured over two 3D vehicle windows. Captures of the menu, help, both collapsed rows and unsupported/scaled configurations were visually inspected.

Evidence: [results](evidence/phase9/p5a/check-results.json), [gallery](evidence/phase9/p5a/gallery.html), [build](evidence/phase9/p5a/build.log), [tests](evidence/phase9/p5a/tests.log), [environment and executable hash](evidence/phase9/p5a/environment.json). The existing window-definition test caught an invalid colour on the help text container during development; the corrected definition passes and opens normally. Fixture config edits use UTF-8 without a BOM to preserve INI parsing.

No new performance result is claimed. Rendering algorithms, draw distance, simulation timing and LOD are unchanged; the original 9.6 measurements remain the baseline.

## Native acceptance checklist

- Open/close the 3D dropdown by click and press/drag/release. Enable and disable 3D, then exit normally and relaunch.
- Hover the 3D button to check its tooltip. Open camera help, move it across the map and open other windows above it; check clipping and stacking.
- Resize the app with a native window border; check the full toolbar and both collapsed rows, including at 200% GUI scaling.
- Open the menu using the rebindable shortcut while a vehicle window overlaps the map; navigate arrows, Enter and Escape. Verify no unintended camera pan or other hotkey action.
- Move the app between monitors with different DPI. Verify button bounds, cursor alignment, tooltip, dropdown and help remain readable and clickable.
- Use an ordinary build tool, cancel a drag, pan and zoom in the building angle, and switch between 2D/3D with vehicle windows open. Ride viewports remain non-interactive.
