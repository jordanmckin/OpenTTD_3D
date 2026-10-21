# Phase 6 Windows interaction checks

Status: partial user feedback received (2026-10-16). The user reports that management and clicking worked. Reported diagonal rail gaps have been corrected with boundary-intersected strip endpoints and regression coverage; user retest is pending. Overall performance is poor and worsens with multiple vehicle windows open; the user explicitly deferred performance to Phase 7. Drag/cancel, resize and DPI checks were not individually reported, so remain unverified. Scripted console calls and screenshots do not prove native input behavior.

Run `./tools/phase6-demo.ps1` from the workspace root. The isolated profile starts the railway fixture paused. Open the console with the key above Tab and enter `renderer_3d camera 0 100` if needed. Construction is supported in this fixed view. Use Ctrl+Alt+C and Change company to select company 2 for the existing routes; switch back to your own company for independent construction. Save only into the isolated demo profile.

Record PASS/FAIL for each row. For a failure include the tool, tile/location, zoom, display scaling, and whether the same operation works after `renderer_3d off`.

| Check | Actions | Expected result |
|---|---|---|
| Ground picking | Open rail construction. Move the cursor across flat ground, hillside, a foundation, coastline, and behind a tall town building. Compare with classic mode. | Highlight and commanded tile agree with classic; roofs do not shift construction to another tile. |
| Rail drag | Drag straight and diagonal autorail in both directions, cancel with Escape, then build and remove a short section. | Preview follows the intended pieces; cancellation changes nothing; built/removed rail matches preview. |
| Other tools | Build/remove a road, station, depot and signal; raise/lower one terrain corner. Try an invalid placement. | Footprint and orientation match the command; invalid placement shows normal errors without changing unrelated tiles. |
| Occlusion | Press X; use Ctrl+X to open transparency controls. Toggle houses, industries, trees, company buildings and bridges separately, including invisibility. Repeat while paused. | Transparent structures retain a faint pattern while exposing the ground. Hidden structures disappear. Restoring visibility immediately restores them; tracks remain visible. |
| Management | Click a moving train/truck, a station and an industry; open orders, depot and vehicle windows. | Correct object/window opens; controls operate normally and match classic behavior. |
| Tooltips and cursor | Hover toolbar buttons and window controls; move over buildings and open windows. | Tooltip text, cursor shape and click position remain aligned. |
| Window overlap | Drag a depot or vehicle window over the map. Click controls and empty areas in that window. | World does not paint over the window; clicking its controls does not construct underneath it. |
| Secondary view | Run `renderer_3d viewport`; pan/zoom the extra viewport, move and resize its window. | Both views render correctly and interactions use the viewport under the mouse. |
| Pan, zoom, edges | Pan to each map edge, zoom around the pointer, and drag a construction preview toward an edge. | No displaced cursor, invalid tile, stuck drag, crash or unexpected jump. |
| Resize | Resize the main window smaller/larger, maximize/restore, and minimize/restore while paused and running. | UI and world refill correctly and picking stays aligned. |
| DPI | If available, move the game between monitors with different Windows scaling. Also test the game's UI scale setting. | Text, cursors, window hit boxes and tile selection agree after each transition. |
| Simulation and persistence | Unpause, use fast-forward, return to normal, save and reload, switch `renderer_3d off` / `on`. | Vehicles, orders, money and construction persist; the original GUI and classic renderer remain usable. |

For ships and aircraft, run `./tools/phase6-demo.ps1 -Scene AirWater`. It starts paused at the canal; unpause to see the ship. In the console, `scrollto instant 33 8` shows the airport/aircraft route; `scrollto instant 23 44` returns to the ship. Repeat the management, tooltip, orders, depot, pause, save/reload and graphics-switch checks for both transport types. The AI owns these vehicles (company 2). Do not interpret an untested row as a pass.
