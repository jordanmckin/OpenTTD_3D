# Orbit camera

Date: 2026-10-17. Presentation only: no simulation, save or network state changes.

## Controls (3D renderer on)

| Input | Action |
|---|---|
| `,` / `.` | Rotate 45° left/right (animated; hold to keep turning) |
| Page Up / Page Down | Tilt toward top-down / toward the horizon (40–180%) |
| Ctrl + right-drag | Free orbit: horizontal turns, vertical tilts |
| Hold middle mouse + drag | Free orbit over the main map, without Ctrl; release to stop |
| Home | Toggle between the classic camera and the last orbit angle |

The keys are ordinary global hotkeys (`3d_rotate_left`, `3d_rotate_right`, `3d_tilt_up`, `3d_tilt_down`, `3d_camera_toggle`) and can be rebound in `hotkeys.cfg`. Console: `renderer_3d orbit <+yaw> <+tilt>` and `renderer_3d home`; `renderer_3d camera <yaw> <tilt>` still sets an angle instantly.

## Snap-back rule

Construction, vehicle clicks and labels assume the classic projection. Instead of rotating them all, the camera returns to classic (yaw 0, tilt 100) whenever a placement tool is active (`_thd.place_mode != HT_NONE`). The orbit angle is remembered; Home goes back to it. Rotating while a tool is open closes the tool.

While rotated:
- Panning (right-drag, arrow keys, edge scroll, extra viewports) is converted so screen directions stay screen directions (`Terrain3D::ClassicScrollDelta`).
- The mouse wheel zooms about the view centre, not the cursor.
- Left clicks pick ground tiles only (e.g. opening a station or depot); vehicle and sign hit boxes are skipped.
- Signs and text effects are not drawn in 3D (unchanged).

## Pivot

The camera turns about the ground under the screen centre, not about height zero. When a gesture starts, the centre ground point is picked, the classic scroll position is moved onto that point's classic centre ray, and its height becomes the pivot (`Camera::pz`). At yaw 0 and tilt 100 any pivot on that ray produces the identical classic picture, so the switch is invisible.

## Verification

- Unit tests: classic picture independent of pivot height; pivot stays at screen centre for all yaw/tilt; scroll inverse moves the rotated view by the requested screen delta. 111/111 test cases pass.
- Scripted run (railway fixture, 1280x900): the centre pick is tile 29,33 before and after `orbit 135 -30`; the rail preview tool snaps the camera to 0/100; `home` restores 135/70; a second `home` returns to 0/100 along the short way.
- Not automated: physical key presses, Ctrl+right-drag feel and rotated panning direction in a live window.

2026-10-20: added held middle-button orbit in the Windows backend. It starts only
over the main 3D map, uses a captured pointer, and ends on release, lost capture
or lost focus. It works independently of the configured panning button. Release
build and 126/126 automated tests pass; physical middle-drag verification remains
manual. The in-game English camera help includes the new gesture.
