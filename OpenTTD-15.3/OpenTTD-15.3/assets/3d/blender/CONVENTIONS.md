# Phase 8 Blender conventions

Every base-game identity in `assets/3d/inventory.json` is modelled in its own `.blend`, named after its inventory key: `assets/3d/blender/<category>/<key>.blend` (for example `house/house_003.blend`, `vehicle/road_007.blend`). The `.blend` is the editable source of truth. Exports, previews and the generated runtime table are derived from it and can always be rebuilt.

## Workflow

All commands run from the workspace root (`D:\G ttd`). Blender is found through `$BLENDER`, then `D:\Blender\blender.exe`, then `PATH`.

1. `python tools/3d_assets/art.py new <key>` creates the `.blend` from the template: units, palette materials, the identity's state collections, the reference image and a game-angle camera.
2. Model it, in the Blender UI or through the Blender MCP. Open the reference image (`assets/3d/reference/<climate>/<key>_*.png`) beside the viewport. It is also loaded as an image empty in the `reference` collection, which is never exported.
3. `python tools/3d_assets/art.py build <key>` exports each state collection to `assets/3d/export/<key>/<state>.glb`, renders previews to `assets/3d/previews/<key>_<state>.png`, converts all exports into `src/video/asset3d_art.h` and validates them. Then rebuild the game.
4. The user reviews previews and the in-game result. Approval is recorded by setting the inventory status to `approved`. The next convert moves approved entries to `in_game`.

`python tools/3d_assets/art.py convert` reruns only the conversion, for example after pulling someone else's exports.

## Units and axes

- 1 Blender unit = 1 engine world pixel. A tile is 16 × 16 units; one terrain height step is 8 units. Z is up.
- Blender +X is engine X (towards the bottom-left of the classic screen); Blender +Y is engine Y (towards the bottom-right). The classic view looks from +X+Y+Z towards the origin; the template camera shows this angle.
- Export keeps Blender's axes (no glTF Y-up conversion). Apply rotation and scale to objects before export, or leave them; the exporter bakes transforms either way.

## Origins and footprints

- **Tiles (houses, industries, stations, depots, objects):** the north corner of the north tile is the origin `(0, 0, 0)`. Geometry stays within the footprint: `[0, 16·w] × [0, 16·h]`, Z ≥ 0. Z = 0 is the flat tile surface; foundations are drawn by the game.
- **Multi-tile houses (2×1, 1×2, 2×2):** one whole model. 2×1 extends along +X, 1×2 along +Y. The game draws it from the north tile; the other tiles draw only their ground.
- **Industries:** model the whole industry as one scene using layout 0 from the reference (left-most image). Tile `(tx, ty)` of the layout occupies `[16·tx, 16·tx+16] × [16·ty, 16·ty+16]`. Keep each tile's geometry in its own object(s) and inside its tile square; the converter assigns each object to the tile under its centre and moves it to that tile's origin. Tiles whose graphic is not in layout 0 go in an extra state collection with an `@layout<n>` suffix (for example `complete@layout2`). A graphic that appears on several tiles of a layout (three cooling towers, two coal heaps) is taken from its first tile in layout order; the copies on the other tiles are only for the preview and may differ. Animation frames that draw another graphic's model are listed in `INDUSTRY_GFX_ALIAS` in `convert_gltf.py` (the coal mine headframe, gfx 1 → 0). Moving parts (headframe wheel, power station sparks, gas flares, oil well pumps) are not in the tile's model: each step is a `part_<n>` state holding only the moving geometry, on the graphic's first tile like the static model, and the game draws the step chosen from the tile's animation frame over the static tile.
- **Vehicles:** centred on the simulation position, +X forward, Z = 0 at the wheel/rail contact. A standard 8-unit vehicle body spans X −3.6…+3.6 and Y within ±2; shorter vehicles are scaled along X by the game. Ships and aircraft are authored at world size and not scaled. Do not model wheels touching Z = 0 exactly; start them at 0.3 to avoid fighting the ground.
- **Trees:** centred on the trunk base at the origin. Each growth state is authored at its own size (the game no longer scales trees for Phase 8 models).
- **Signals:** origin at the foot of the post, +X the direction of travel, so lamps and arms face −X towards the approaching train; the track centre is 4.2 units away on the −Y side. Stay within ±4 in X and Y.
- **Catenary:** the game places each piece where the classic `elrail.cpp` draws its sprite. A pylon has its origin at the foot of the mast, and its cantilever reaches along +X to the track centre: 4 units in `pylon`, 2.83 in `pylon_diagonal`. A wire span runs along X from 0 to 16 at track height; the game stretches it between two pylon control points and shears it on slopes. `wire_both` hangs between pylons at both ends; `wire_half` has its pylon at x = 0 and ends at the middle of a two-tile span. The contact wire sits just above the raised pantographs, at 7.3.
- **Effects (smoke, sparks, explosions, the roadworks bulldozer):** the origin is the effect vehicle's position. Smoke rises by moving its vehicle, so a puff is modelled round its origin; plumes that stay put (chimney and breakdown smoke) rise from it and lean towards −X, as the classic sprites lean up and to the right on screen. The bulldozer drives along +X and is turned by the game.
- **Level crossing:** a whole tile with the origin at the north corner, authored with the road along X and the rails along Y; the game turns it 90° for a road along Y. Only the furniture (posts, lights, barriers): road and rails are drawn by the game.

## States

Each state is a top-level collection whose name is the state name, exactly as listed in the inventory entry's `states`. Only objects inside state collections are exported. A missing state falls back to the Phase 5 model for that state.

| Category | State collections |
|---|---|
| house, industry | `construction_0`, `construction_1`, `construction_2`, `complete` |
| vehicle | `default`, or `empty` and `loaded` |
| tree | `growth_0`, `growth_1`, `growth_2`, `grown`, `dying_0`, `dying_1`, `dead` |
| signal | `red`, `green` |
| level crossing | `open`, `closed` |
| catenary | `pylon`, `pylon_diagonal`, `wire_both`, `wire_half` |
| industry moving part | `part_0`, `part_1`, … one per step (with `@layout<n>` like the other industry states) |
| effect | `frame_0`, `frame_1`, … one per sprite of the classic sequence; the bulldozer has only `default` |
| others | as listed in the inventory entry; otherwise `default` |

## Families

Family scripts live in `tools/3d_assets/families/` (`trees_temperate.py`, `signals.py`, `catenary.py`, `effects.py`). Each one rebuilds the state collections of its members' `.blend` files from a parameter table; run it in Blender (through the MCP, or `blender -b -P <script> -- [keys]`), then `art.py build` the members. Hand edits to a member are lost when its family script is rerun.

## Materials

- Flat base colours only: no textures or UVs (the renderer is untextured). Lighting is applied by the game per face.
- Use the shared palette (`palette.json`); the template creates every palette colour as a material with the same name. New colours go into the palette, not into one-off materials.
- `cc1` and `cc2` are reserved: faces using them are drawn in the owning company's primary and secondary colour (vehicles, and later stations, depots and HQs).
- `flame_yellow`, `flame_orange`, `flame_red` and `spark_blue` glow: the game draws them unlit, at full colour whatever the light (the converter marks them by adding 2 to the colour).
- Vertex colours are allowed; a face's colour is the average of its vertex colours multiplied by the material colour.
- Every face needs a material. A face with no material is a conversion error.

## Budgets

- 600 triangles per tile of footprint for buildings, industry pieces and the level crossing (a 2×2 house may use 2,400), 600 per vehicle (to be raised in step 8.5), 200 per tree state, 300 per signal or small prop.
- Only faces seen from above and the sides matter: the game never shows the underside, so bottom faces may be omitted.
- Low-poly, readable silhouettes matching the reference sprite: recognisable roofline, chimneys, towers and colours. Detail that would be under one pixel at the closest in-game zoom is wasted.

## Files

| Path | Committed | Content |
|---|---|---|
| `assets/3d/blender/<category>/<key>.blend` | yes | source model |
| `assets/3d/export/<key>/<state>.glb` | yes | exported mesh per state |
| `assets/3d/previews/<key>_<state>.png` | yes | game-angle preview for review |
| `src/video/asset3d_art.h` | yes | generated runtime table, do not edit |
| `assets/3d/reference/` | no | regenerate with `tools/3d_assets/build_references.py` |
