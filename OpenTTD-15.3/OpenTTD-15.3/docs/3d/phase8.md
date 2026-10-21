# Phase 8: hand-modelled base-game art

Status (2026-10-17): 8.1 and 8.2 implemented; 8.3 implemented and approved; 8.4 pilot set implemented and approved; 8.5 (vehicles) next. Vehicles moved to their own step, 8.5, at the user's request. Replaces the earlier Phase 8 outline at the user's request. Phase 7 work continues independently. Nothing here changes simulation or picking; renderer changes are limited to the asset source and ground textures (8.3). Lighting is unchanged.

## Direction

Every base-game visual identity gets its own low-poly Blender model, built through the user's Blender MCP by Claude or Codex and approved by the user. The original game sprite for each identity is the reference. No third-party asset packs. The Phase 5 Python generator stays only as the fallback for identities not yet replaced and is retired once coverage is complete. Each `.blend` is the editable source of truth and may be adjusted by hand at any time.

The library is roughly 450–500 models, not one per sprite: most of the ~11,000 base sprites are directions, slopes, construction/animation frames, zoom levels and GUI. One 3D model replaces all rotations of an object, and terrain geometry replaces slope sprites.

The workflow is:

1. **Pull reference sprites** from the running game, one image per identity.
2. **Build the Blender → game pipeline:** conventions, export and a build-time converter, so an approved `.blend` appears in game.
3. **Add textured ground** to the renderer, so models are reviewed on the final ground.
4. **Model each identity in Blender** from its reference, review, approve, and integrate.

## Build approaches

Agreed with the user (2026-10-16): each identity is built with one of three approaches, recorded per identity in `inventory.json` as `approach`.

| Approach | Used for | Approx. count | How |
|---|---|---|---|
| `bespoke` | Houses, industries, landmarks (church, stadium, HQ, lighthouse, transmitter), stations | 150–200 | One Blender model per identity, modelled individually from its reference. Recognizable silhouettes; no shared generator. |
| `kit` | Trains (66 unique images of 116 engines), road vehicles (63 of 88), aircraft (26 of 41), ships (4 of 11) | ~160 | Assembled in Blender from a shared parts library (`assets/3d/blender/kits/`: bogies, wheels, cabs, boiler sections, wagon bodies, cargo inserts, truck/bus chassis, hulls, fuselages, wings), then given its own proportions and details. Each vehicle remains its own `.blend` and model. |
| `family` | Trees (41 species with growth/dying states), field fences/hedges, signal variants, bridge spans, ground props | 100+ | One parametric Blender Python script per family produces every member from a small parameter table (e.g. trunk/crown shape, colour and height per tree species). Members are approved as a family, with spot checks. |

Kit parts and family scripts are approved by the user before members are produced. A kit or family change regenerates its members' exports; member `.blend` files that were hand-adjusted are flagged rather than overwritten.

## Multi-tile objects

- **Houses (1×1, 2×1, 1×2, 2×2):** one whole model per building, origin at the north corner of the north tile (`GetHouseNorthPart`). The north tile draws the model; the other tiles draw only their ground. Culling uses the model's full bounds so a building spanning chunks or the screen edge is never cut off. This replaces the Phase 5 per-tile modules and stadium quadrants.
- **Industries:** layouts vary (e.g. four coal mine layouts in `table/build_industry.h`), so each industry is modelled as one Blender scene and cut on the 16-unit grid into one piece per industry tile graphic (175 base tile graphics across 37 industries). Each tile draws its own piece; pieces must fit together in every base layout. Reference previews show each layout assembled.
- **Stations, depots, stops, bridges:** per tile, as players build them tile by tile.

## Runtime format

The game does not load `.blend` files. Each approved `.blend` is exported to glTF, and a build-time converter turns glTF into the embedded runtime format. There is still no runtime parser or external resource search path, consistent with [asset_spec.md](asset_spec.md).

## 8.1 Reference sprites and inventory

**Primary source (available):** the user exported all OpenGFX 8.0 sprites with grfcodec into `sprites_pulled/` (sheets plus `.nfo` rectangles). `tools/3d_assets/slice_sprites.py` cuts them into `sprites_pulled/sliced/<grf>/<number>.png` with `index.csv` offsets (11,005 images; regenerable, not committed). Base sprite numbers equal the game's SpriteIDs (e.g. the church is `0x59c` = 1436 in `table/town_land.h`). A script maps each identity to its sprites using the game tables (`town_land.h`, `build_industry.h`/`industry_land.h`, `engines.h` image indices, tree/object/signal/station sprite constants in `table/sprites.h`), composites multi-sprite and multi-tile objects using the `.nfo` offsets, applies recolour palettes where the table specifies one (e.g. `PALETTE_CHURCH_RED`), and writes one reference image per identity. Many base sprites have only normal zoom; `zi2` versions are used where present. The game currently runs OpenGFX 7.1; the difference is irrelevant for reference use.

**Implemented:** `tools/3d_assets/build_references.py` (Python + Pillow, run from the workspace root) reads the game tables directly and composites references the way the classic viewport places sprites (`RemapCoords`, bounding-box origins, child sprites, ground-before-building order, recolour palettes including company colour and transparent station glass). It maps the climate GRFs through `table/landscape_sprite.h` and the extra GRF through its Action 5 blocks (`newgrf_act5.cpp` types), so signals, catenary, airport extras, locks and rock overlays resolve. Every identity resolves with no missing sprites. Output, regenerable in about 10 seconds and not committed:

- `assets/3d/reference/<climate>/<key>_<label>.png` at 4× nearest-neighbour, transparent background, one image per identity per climate (903 images). Each strip shows the states or directions side by side: house construction stages 0–3, all industry layouts, tree growth 0–6, vehicle 8 directions (plus a loaded row), signal positions red/green, depot directions, station axes, airport layouts assembled.
- `assets/3d/inventory.json`: 514 entries (house 94, industry 37, tree 49 including snowy sub-arctic variants, vehicle 256, object 9, station/stop/airport 21, depot 3, lock 1, bridge 13, tunnel 2, signals and crossing and catenary 14, fences and rock props 7, ground textures 8). 387 need their own model; the other 127 are vehicles with status `shared` and `shared_with`, because they use the same base sprite as an earlier engine. Re-running preserves `status`, `approach`, `kit`/`family`, `notes`, `shared_with` and `blend` of existing entries.

The console-command fallback (`dump_reference_sprites`) is not needed while the sprite export covers every identity; it remains an option for verifying against the running game or for NewGRF art later.

Each inventory entry has category, ID, label, climates, footprint/size, required states (construction stages, cargo loads, growth, open/closed) and status.

The inventory includes landscape objects, not only buildings and vehicles:

- Trees: all 41 base species (temperate 12, sub-arctic 8, rainforest 7, cactus 1, sub-tropical 4, toyland 9; `src/tree_map.h`), with growth and dying/dead states. Whether each state is a separate model or a scaled/shared one is decided per species by the user.
- Map objects (`src/object_type.h`): transmitter, lighthouse, company statue, owned-land flag, company HQ in all five sizes.
- Field edges: each hedge/fence type used on farm field borders (`GetFence`).
- Optional ground props: small rock and bush clusters placed over rocky and rough land textures.
- Water: buoys, canal locks, ship depots and docks.
- Rail/road furniture: all signal types and states, level crossings, electrified rail catenary poles and wires.

Ground surfaces themselves are textures, not models; they are listed in the inventory as texture identities (see 8.3).

Each inventory entry also records its build `approach` (`bespoke`, `kit` or `family`) and, for kit/family members, the kit or family name.

Status values: `not_started`, `modelled`, `approved`, `in_game`, `shared` (intentionally uses another identity's approved model, with a reason).

Gate: reference PNGs and inventory exist for all four climates; the user spot-checks a sample against the classic view.

## 8.2 Blender → game pipeline

- **Conventions** (`assets/3d/blender/CONVENTIONS.md` plus a template `.blend`): 1 Blender unit = 1 engine world pixel (tile 16×16, height step 8), Z up, static tiles originate at the north corner, vehicles centered with +X forward and Z=0 at wheel contact, matching [asset_spec.md](asset_spec.md). Fixed camera preview scene matching the in-game view.
- **Materials:** flat base colours (the renderer is untextured). A shared named palette so models stay consistent. Reserved material names `cc1`/`cc2` are replaced at runtime with the owning company's colours. Vertex colours are allowed. Textures/UVs are out of scope unless the renderer gains them in a separate decision.
- **States as named collections/objects** in one `.blend` per identity (e.g. `construction_0..2`, `complete`, `load_empty`, `load_full`), so each state exports with one script.
- **Export:** `tools/3d_assets/export_blend.py`, run by Blender headless or via the MCP, writes `assets/3d/export/<name>.glb` and preview renders (game-angle isometric plus front/side/top) to `assets/3d/previews/`.
- **Convert:** `tools/3d_assets/convert_gltf.py` (standard-library Python) reads the exports, validates conventions (bounds within footprint, no missing materials, triangle budget) and emits the embedded runtime asset data. Whether this remains a generated C++ table or becomes an embedded binary blob is decided by measured build time and size.
- **Runtime lookup:** per identity, use the converted model if present, else the Phase 5 model, else the magenta placeholder. Missing-identity reporting stays.
- **Verify:** `tools/3d_assets/verify.py` is extended to check inventory against converted assets and report coverage by status.

Gate: one trivial test model goes from `.blend` → export → convert → visible in a live game with correct position, orientation, picking and company colour, using one command.

Implemented (2026-10-16):

- `python tools/3d_assets/art.py new <key>` runs `new_blend.py` in headless Blender. It writes `assets/3d/blender/<category>/<key>.blend` with every `palette.json` material (fake users), one collection per inventory state, a `reference` collection (footprint outline, tile markers, packed sprite reference) and a `game_view` scene. Blender is found via `$BLENDER`, `D:/Blender/blender.exe`, or PATH.
- **Preview projection:** the game camera is axonometric with Z 1:1 in screen pixels. An orthographic camera at 60° pitch / 135° yaw matches it once Z is scaled by √2/(4·cos 30°) ≈ 0.408. `game_view` and the previews apply that scale to collection instances, so the authored geometry stays in true world units.
- `art.py build <key>|--all` runs `export_blend.py` (one GLB per non-empty state collection, `export_yup=False`, plus one framed Workbench preview per state) and then `convert_gltf.py`.
- **Converter:** `convert_gltf.py` is standard library only. It reads GLB node transforms, triangle primitives, base-colour factors (linear → sRGB) and `COLOR_0`. It drops degenerate triangles. Materials `cc1`/`cc2` are encoded as colour −1/−2. Industries split by object centre into per-gfx tile models using layout 0 (or `@layout<n>`). Engines that share a base sprite (`shared_with`) share the model.
- **Converter validation:** errors (bounds outside the footprint/vehicle box, missing materials, unknown states, triangle budget) block writing. Categories without a runtime hook yet are warned about and skipped.
- **Converter output:** `src/video/asset3d_art.h` with `Art3D::models` and lookups `House`, `IndustryTile`, `Engine` (loaded falls back to empty) and `Tree`. It advances inventory status: `not_started → modelled`, `approved → in_game`.
- **Runtime:** `TerrainTile::art` and `Train3DSnapshot::art` take precedence over Phase 5 assets, which in turn take precedence over the placeholder.
  - Houses draw the whole model from the north tile; other parts draw ground only.
  - Industries are drawn per gfx and stage, trees per type and growth at authored size.
  - Rail and road vehicles scale X by `half/3.6` like Phase 5; ships and aircraft use world size.
  - `cc1`/`cc2` faces take `livery[LS_DEFAULT]` colours through `GetColourGradient(…, SHADE_NORMAL)`; unowned objects get neutral greys.
  - Art3D models are included in the culling-bounds padding. Non-base (NewGRF) houses, industry tiles and engines never use base art.
- `art.py status` reports coverage by category and status. This replaces the planned `verify.py` extension.
- **Test model:** `road_007` (Balogh coal truck, engine 123), 12 objects per state, `empty`/`loaded`, cab in `cc1`. It was built by a script in headless Blender, exactly as an MCP session would. Export → convert: 2 models, 536 triangles, no errors.
- **Build and tests:** the capped Release build passes. 109/109 ctest unit tests pass, including the new Art3D table test (valid model indices, unknown identities → −1, finite positions, colours in range or −1/−2).
  - The two savegame regressions fail under ctest in this environment: `Regression.cmake` runs its copied exe by relative name, which `execute_process` reports as "no such file or directory". With the same script given an absolute exe path, both pass. No harness change was committed.
- **Gate evidence:** `tools/phase8-gate.ps1` loads the Phase 4 fixture with `fixtures/phase8/gate/*.scr` and takes three monthly 3D captures along the truck road. [In-game capture](evidence/phase8/phase8-truck-ingame.png): the coal truck model on the road at the right scale and heading, with the cab in the owning company's red (the default palette colour is blue, so `cc1` substitution is confirmed).
  - Whether a truck is in frame depends on where it is in its route when the monthly shot fires. The first run caught one; a rerun did not.
  - Picking was not separately rechecked: `PickTerrain3D` maps the cursor onto terrain and the engine resolves vehicles from that world position, so model meshes do not take part.
  - "One command" holds for `.blend` → runtime table (`art.py build`); the game rebuild remains a separate step.

## 8.3 Ground textures

Renderer work, done before the pilot set so models are reviewed on the final ground. The terrain keeps its current hard-edged slope geometry and existing per-triangle lighting; only its surface colour changes. Shadows, ambient occlusion and other lighting changes are out of scope for Phase 8 by user decision.

Current state: GLSL 150 shaders on OpenGL 3.2+, per-triangle lighting computed on the CPU (`AddTerrainFace` in `src/video/terrain3d_impl.h`), and a fragment shader that outputs a flat colour. Ground is one colour per `ClearGround` value with small random variation; there are no textures or samplers.

- A texture array with one layer per ground identity. Texture coordinates come from world position in the shader, tiling seamlessly every one or two tiles; terrain needs no stored UVs. The texture colour is multiplied by the existing per-triangle light value.
- A per-face layer index replaces the flat ground colour. Neighbouring ground types blend across tile edges using a noise mask so the tile grid does not show.
- Use the authoritative ground state already in the map that the renderer currently ignores: grass density 0–3, rough land as its own surface, rocky land, each farm field type (`GetFieldType`), snow density, desert density, shore/beach, and water. Snapshot comparison must include any newly used state so dirty-tile updates stay correct.
- Textures are authored or baked in Blender as tileable images, with the source `.blend` kept beside them in `assets/3d/textures/`, reviewed against the classic ground sprites from 8.1, and approved by the user like models. They are embedded at build time; no runtime search path.
- Works in every viewport, transparency mode and screenshot. Fallback: if texture creation fails (driver limits), use the current flat colours.

Gate: the current temperate capture scene renders with textured ground; the user approves the look; Phase 7 benchmarks are re-run with the measured cost recorded; picking, transparency and classic switching are unchanged.

Implemented and approved by the user (2026-10-17). The 8 texture identities are `in_game`:

- **Layers:** `src/video/ground3d.h` defines 26 layers:
  - grass density 0–3, rough, rocks;
  - field types 0–8;
  - snow and desert density 0–3;
  - beach, water and concrete.

  `ReadGround3D` maps the map state the way the classic `DrawTile_*` functions choose sprites:
  - clear tiles: ground type and density, field type, snow;
  - trees: tree ground and density;
  - rail ground type;
  - roads: roadside, snow or desert;
  - concrete for stations, road stops, airports and industries;
  - coasts are beach; open water never blends.

  The layer is part of the tile snapshot, so dirty-tile comparison covers it. Foundation tops now show their ground layer instead of flat grey; skirts are unchanged.
- **Textures:** `python tools/3d_assets/art.py textures` runs `ground_textures.py` in headless Blender, then `convert_textures.py`.
  - `ground_textures.py` writes 128×128 seamless PNGs from periodic-noise recipes, plus `assets/3d/textures/ground_textures.blend` for review and hand painting. Existing PNGs are kept unless `--force`.
  - `convert_textures.py` embeds them as `src/video/ground3d_textures.h` (0x00RRGGBB texels and per-layer means). It also advances the 8 texture identities in `inventory.json` from `not_started` to `modelled`.
  - `preview_textures.py` writes the [review sheet](evidence/phase8/ground/texture-review.png): classic sprites beside each layer.
- **Renderer:**
  - A `GL_TEXTURE_2D_ARRAY` with mipmaps holds the layers, plus an `R8UI` per-tile layer map. Changed tiles are uploaded as a dirty rectangle.
  - Ground faces carry their layer; their vertex colour is the layer mean times the existing per-triangle light. The fragment shader recovers the light from that colour and samples the texture at world X/Y / 32, one repeat per two tiles.
  - Neighbour blending reads the 3×3 tiles around the fragment:
    - Soft layers (grass, rough, rocks, snow, desert, beach) blend within 0.3 tiles of the edge, at a noise-warped position, so the grid does not show.
    - Fields and concrete blend over 0.04 tiles on the true edges and take priority, as their classic sprites have straight borders.
    - Water never blends.
  - Every term is a function of world position, so both sides of an edge agree.
  - Lighting is unchanged.
- **Fallback:** without `glTexImage3D`/`glGenerateMipmap`, or on a GL error while creating the textures, ground uses the layer means. The same applies to maps larger than `GL_MAX_TEXTURE_SIZE`, which keep textures but skip neighbour blending.
  - Console `renderer_3d ground on|off` forces the flat fallback for A/B checks.
  - The frame log reports `ground_textured` and `ground_map_upload_bytes`.
- **Tests:** a unit test checks:
  - layer mapping for every density and field type, including out-of-range field types;
  - that the layer count matches the texture table;
  - mean colours.

  The capped Release build passes. 112/114 ctest tests pass; the two savegame regressions fail only through the known relative-exe issue (8.2) and pass when the same script is given the absolute exe path.
- **Gate runs:** `tools/phase8-ground.ps1 -Scene town|farm`, verified by `tools/verify-phase8-ground.py`.
  - The `town` run is the Phase 4 save with the Phase 5 town/mine/power/railway views. The `farm` run is a generated 128×128 temperate map with all nine field stages and rocks.
  - Both run with `verifydirty` and `verifygpu` on: 2,911 and 1,678 dirty-reference checks, zero missed tiles, and zero mesh mismatches. The retained GPU path and the CPU-projected reference differ on 0 pixels.
  - `renderer_3d check`: 5,120 height checks and 281/275 classic picks, with no failures. Phase 4 audit: 3,072 height checks, no failures.
  - Transparent mode, the orbit camera, and the switch to classic and back were all captured: [town](evidence/phase8/ground/town.jpg), [flat fallback](evidence/phase8/ground/town-flat.jpg), [close-up](evidence/phase8/ground/closeup.jpg), [overview](evidence/phase8/ground/overview.jpg), [orbit](evidence/phase8/ground/orbit.jpg), [transparent](evidence/phase8/ground/transparent.jpg), [classic](evidence/phase8/ground/classic.jpg), [farm](evidence/phase8/ground/farm.jpg), [farm close-up](evidence/phase8/ground/farm-closeup.jpg), [rocks](evidence/phase8/ground/rocks.jpg), [farm orbit](evidence/phase8/ground/farm-orbit.jpg).
  - The magenta farm buildings in the farm scene are the existing Phase 5 missing-asset placeholder, not part of 8.3.
- **Measured cost:** Phase 7 benchmark, `optimized` mode, one sequential trial per case, `-Ground off` vs `-Ground on` ([flat](evidence/phase8/ground/benchmark-flat.json), [textured](evidence/phase8/ground/benchmark-textured.json)). Times are drawing-pass wall time, not FPS.

| Case | Mean draw ms flat → textured | p95 draw ms | GPU ms |
|---|---|---|---|
| 64², no extra views | 4.43 → 5.04 | 6.66 → 7.74 | 0.53 → 0.94 |
| 64², 1 vehicle view | 5.12 → 5.42 | 8.98 → 9.59 | 0.77 → 0.99 |
| 64², 4 vehicle views | 6.19 → 6.05 | 12.35 → 12.78 | 0.76 → 0.84 |
| 64², 4 views, 200-truck stress | 19.62 → 19.78 | 24.49 → 24.13 | 2.88 → 3.29 |
| 128² generated | 6.18 → 5.50 | 8.22 → 6.82 | 0.56 → 0.92 |
| 512² generated | 6.85 → 7.05 | 9.57 → 8.67 | 1.10 → 1.32 |
| 1024² generated | 8.80 → 9.75 | 11.26 → 13.33 | 0.64 → 1.00 |

  The textured shader adds about 0.1–0.4 ms of GPU time per pass. Wall-time differences of −0.7 to +0.9 ms are within run-to-run variation, in both directions.
  - Retained vertex storage grows by one float per vertex (the layer). The map texture costs one byte per tile (1 MiB at 1024²); steady-state map uploads are only the changed rectangle.
  - Snow and desert layers exist and are mapped, but their textures are first-pass placeholders until their climates are reviewed in Phase 10.

## 8.4 Pilot set

Model the static identities visible in the current temperate town capture, all the way into the game. Vehicles are not part of the pilot; they have their own step (8.5). The temperate grass/rough/field ground textures were completed in 8.3. The pilot also includes the temperate tree family script, to test the `family` approach early. Review in game at normal zoom beside the classic view.

The identities come from the map of the Phase 4 fixture save (`fixtures/phase4/infrastructure.sav`):

- Houses (`bespoke`): 3 church, 6 town houses, 9 statue, 14/15/16/29 shops and offices, 20 stadium (2×2), 24 old houses, 25 cottages, 26 houses, 27 flats, 39 cinema.
- Industries (`bespoke`): coal mine and power station (tile graphics 0–10).
- Trees (`family`): all 12 temperate species, every growth and dying state.
- Rail furniture: the signals and the level crossing on its rail line. These need a runtime hook, as the 8.2 converter only knows houses, industry tiles, engines and trees.

The church (`house_003`) is the first model. The user approved its look on 2026-10-17 as the static-object style reference: flat palette colours, readable low-poly massing at the reference's proportions, about 600 triangles per tile.

The review loop for every model: reference PNG → model in Blender → preview render beside the reference → corrections → user approval → export/convert → in-game check. Record the approval in `inventory.json`.

Modelled and in game; the user approved the whole pilot set on 2026-10-17 (inventory status `in_game`). Everything was built through the user's Blender MCP (blender-mcp 1.29.1 at `127.0.0.1:9191`).

- **Houses (13):** `house_003` (approved), 006, 009, 014, 015, 016, 020, 024, 025, 026, 027, 029 and 039.
  - Each has four states; the construction stages are open walls at two heights, then the building without its garden.
  - Gardens, paths, fences, flowers and paving are part of the complete state.
  - The largest is 474 triangles per tile (house 015).
  - Review sheets: [houses 1](evidence/phase8/pilot/review-houses-1.png), [houses 2](evidence/phase8/pilot/review-houses-2.png), [offices](evidence/phase8/pilot/review-offices.png), [statue, cinema, stadium, flats](evidence/phase8/pilot/review-landmarks.png).
- **Industries:** the coal mine (`industry_00`, gfx 0 and 2–6) and the power station (`industry_01`, gfx 7–10).
  - Each is modelled as one scene. Gfx 4 is only in coal mine layout 1, so it is in the `…@layout1` collections.
  - Two converter changes:
    - A gfx that appears on several tiles of a layout is taken from its first tile.
    - `INDUSTRY_GFX_ALIAS` maps the animated headframe frame (gfx 1) to gfx 0.
  - Largest piece: 398 triangles. [Review sheet](evidence/phase8/pilot/review-industries.png).
- **Trees:** `tools/3d_assets/families/trees_temperate.py` is the first `family` script.
  - Its parameter table covers all 12 temperate species: crown kind (ellipsoid blobs, flat pads, stacked cones), crown parts, colours per growth and dying state, and dead form (bare branches or a brown crown).
  - Sizes per state come from the reference sprites: crown diameter = sprite width / 2.83, top ≈ sprite height − 0.37 · diameter.
  - At most 189 triangles per state. [Review sheet](evidence/phase8/pilot/review-trees.png).
- **Signals and level crossing:**
  - `tools/3d_assets/families/signals.py` generates all 12 base signals (electric and semaphore × block, entry, exit, combo, path, one-way path) in `red` and `green`.
  - The crossing (`crossing_rail_road`) has `open` and `closed` states. [Review sheet](evidence/phase8/pilot/review-signals.png).
  - New runtime hook:
    - The converter writes an `Art3D::furniture` table. Signals use id `variant · 8 + SignalType`; the crossing is 16.
    - Lookups are `Art3D::Signal(variant, type, green)` and `Art3D::Crossing(closed)`. Aspects never substitute for each other: a missing aspect keeps the old coloured boxes.
    - `TerrainTile::signal_kinds` stores type and variant per track (4 bits each), so a signal type change is a dirty-tile change.
    - Signals are placed at the existing signal position, turned so local +X is the direction of travel. The crossing is turned 90° for a road along Y.
  - Like the classic sprites, signal lamps face only the approaching train. Readability from other angles is rechecked in 8.8.
  - The crossing gets the per-tile budget of 600 (it uses 380).
- **Palette additions:** `window_blue`, `roof_thatch`, `crowd`, `pitch_line`, `cooling_tower`, `brick_brown`, and leaf/bark colours for the trees (`leaf_red`, `leaf_yellow`, `leaf_orange`, `leaf_olive`, `leaf_brown`, `leaf_blue`, `bark_grey`, `bark_white`). Existing `.blend` files were given the new materials.
- **Converter fix:** values that round to a whole number (12.99999) were written as `13f`, which is not a C++ literal. They are now `13.f`.
- **Build and tests:**
  - The capped Release build passes.
  - 112/114 ctest tests pass. The Art3D test now also checks furniture lookups.
  - The two savegame regressions fail only through the known relative-exe issue (8.2).
- **In game:** `tools/phase8-ground.ps1 -Scene town -RunTag phase8-pilot`.
  - Results: GPU worst difference 0.00001, 3,584 dirty-reference checks and 3,324 mesh checks with no misses or mismatches, 281 picks and 5,120 height checks with no failures.
  - Captures: [town](evidence/phase8/pilot/town.jpg), [mine](evidence/phase8/pilot/mine.jpg), [power](evidence/phase8/pilot/power.jpg), [railway](evidence/phase8/pilot/railway.jpg), [close-up](evidence/phase8/pilot/closeup.jpg), [overview](evidence/phase8/pilot/overview.jpg), [orbit](evidence/phase8/pilot/orbit.jpg), [transparent](evidence/phase8/pilot/transparent.jpg), [classic](evidence/phase8/pilot/classic.jpg), [restored](evidence/phase8/pilot/restored.jpg).
  - The first run crashed with an access violation inside the NVIDIA OpenGL driver (`glTexImage2D`) when switching from classic back to 3D. The stack had no game symbols, and an identical rerun passed. It is recorded here as unexplained; if it recurs, the texture uploads on re-enabling the 3D renderer are the first place to look.

Gate: the user approves the pilot set and its look. The approved pilot models become the style reference for the rest of the library; the conventions file is updated with anything learned.

## 8.5 Vehicles (high detail)

Requested by the user (2026-10-17): trains and other vehicles get the most detail in the library, as a separate step with an expanded triangle budget. The 8.2 coal truck (`road_007`, 12 boxes) is a pipeline test only, not a style reference.

- Vehicles keep the `kit` approach. Kit parts (bogies, wheels and rods, cabs, boilers, buffers, couplers, wagon bodies, cargo inserts, chassis, hulls, fuselages) are modelled at the higher detail level, and the user approves them before members are produced.
- The budget is raised well above the 600-triangle static budget. The exact number is set with the user, then checked against the Phase 7 benchmark's 200-truck stress case, since vehicle triangles are rebuilt on the CPU every frame. If the cost shows, LOD (full detail close up, a reduced mesh further out) is preferred over a lower budget.
- First set: the pilot vehicles from the Phase 4 fixture, then the remaining temperate vehicles. These are the steam locomotive (engine 9, the Ginzu 'A4'; its sprite is shared with toyland engine 4), the coal wagons (29, 59, 91, empty/loaded) and the coal truck (123, `road_007` remade).
- The gate is the same as for the pilot: user approval of the kit and the first members, reviewed in game beside the classic view.

**Budget measurement (2026-10-17).**
- Setup:
  - Phase 7 200-truck stress with `optimized` mode, 20 s per case.
  - Same machine and settings as Phase 7 (RTX 3090, 1280×900).
  - A temporary switch drew each truck model (about 260 triangles) N times, standing in for a model N times as detailed. The switch was removed afterwards.
- Mean drawing pass in ms; the CPU projection share is in brackets:

| Triangles per vehicle | 200 vehicles | No windows | Four vehicle windows |
|---|---|---|---|
| ~260 (today) | 52k | 11.7 (1.6) | 24.0 (9.0) |
| ~1,000 | 208k | 19.4 (6.1) | 46.9 (21.2) |
| ~2,000 | 416k | 29.2 (12.3) | 86.7 (45.2) |
| ~5,000 | 1.04M | 54.3 (24.3) | 184.3 (120.8) |

  The 10,000-triangle case ran but failed an unrelated verifier sanity check (no pending chunks), so it is not reported.
- Cause: vehicle faces are rebuilt and every vertex is projected on the CPU, then uploaded again on every render pass for every view, without off-screen culling (`_train3d_faces` in `proof3d_impl.h`).
- Cost: about 4 ms per 100k vehicle triangles in the main view, rising steeply with vehicle windows. GPU time stays small. The limit is this CPU path, not the triangle count itself.

**Decision (user, 2026-10-17): renderer first, then about 4,000 triangles per locomotive or road vehicle and 2,500 per wagon.**
- First step, the GPU vehicle path:
  - Every Art3D and Asset3D model is uploaded once in model space, with the face normal in the vertex metadata.
  - `RefreshTrains3D` records instances (model, origin, direction, length, company colours) instead of world faces.
  - In retained mode, each vehicle that passes the view-culling test is one draw. The vertex shader applies `AppendModel3D`'s placement, the company colours and `AddTerrainFace`'s light.
  - The CPU reference path (`renderer_3d verifygpu`) still expands the instances with `AppendModel3D`, so the existing GPU-reference pixel check compares the two.
  - Vehicles without art keep their placeholder boxes.
- Then a reduced far model (LOD) per kit part, if the measurements call for it.

**GPU vehicle path: implemented and measured (2026-10-17).**
- Code: `Vehicle3DInstance`, `_vehicle3d_instances` and `AppendVehicleInstances3D` in `rail3d_impl.h`; `LoadProofModels`, `DrawProofVehicles` and the shader's model mode (`cameraC.w == 2`) in `proof3d_impl.h`. The frame log has a new `vehicle_draws` field.
- Correctness:
  - The town gate passes: GPU worst difference 0.00001, no dirty-reference or mesh misses, 281 picks.
  - Its 181 GPU-reference checks differ by at most 13 of 1,152,000 pixels (mean 4.4). The run before this change: at most 13, mean 4.6. The vehicles therefore add no differences.
  - Trains and the company-coloured truck look the same in the captures.
- Same stress benchmark as above, with the temporary switch now repeating each vehicle's GPU draw. That also multiplies the draw calls, so it is a worst case. Mean drawing pass in ms, CPU projection in brackets:

| Triangles per vehicle | No windows | Four vehicle windows |
|---|---|---|
| ~260 | 13.3 (0.15) | 30.0 (0.80) |
| ~1,000 | 14.0 (0.16) | 32.1 (0.74) |
| ~2,000 | 11.6 (0.16) | 12.7 (0.61) |
| ~5,000 | 10.2 (0.13) | 12.6 (0.59) |
| ~10,000 | 9.9 (0.13) | 12.9 (0.61) |

- Reading the results:
  - Detail no longer shows in drawing time. The differences between rows are run-to-run variation in the shared parts of the pass (readback, terrain). GPU time stays near 3 ms.
  - Culling draws about 55 of the 200 trucks in the main view (about 80 with the vehicle windows).
  - LOD is not needed for this budget. The switch was removed again.

**First kit member: engine 9, Ginzu 'A4' (2026-10-17, approved by the user the same day; status in_game).**
- Identity: engine 9 is the A4 streamliner (image 1), not the tank engine (engine 0). The inventory listed the toyland engine 4 (`train_004`) as the owner of image 1. Ownership moved to the temperate `train_009`, and `train_004` is now `shared_with` it. Toyland gets its own model when it is reached.
- Budgets: `convert_gltf.py` now allows 4,000 triangles per locomotive or road vehicle and 2,500 per wagon (inventory `type == 'wagon'`).
- Kit: `tools/3d_assets/kits/vehicle_kit.py` holds the shared parts:
  - lofted bodies from cross-section profiles, and plain or spoked rail wheels on the rail line (Y ±1.6, top Z 0.65);
  - coupling and connecting rods, buffers with hooks, and cylinders along X/Y/Z.
- Model: the member script is `tools/3d_assets/kits/train_009_a4.py`, giving 3,066 triangles. It has:
  - a streamlined casing with the wedge nose and a black smokebox mouth, and a cab with side and spectacle windows;
  - a 4-6-2 chassis: 10-spoke drivers with balance weights, plain bogie and trailing wheels, rods, slide bars and cylinders;
  - buffer beams, buffers, lamps, a nameplate, a handrail and a cc2 lining stripe. The body is cc1, so it takes the company colour.
- Review tooling:
  - `renderer_3d follow <engine>` stops the first front vehicle of that engine and centres the main view on it.
  - `tools/phase8-vehicles.ps1` (scripts in `docs/3d/fixtures/phase8/vehicles`) captures it in 3D from three angles, plus the classic view.
  - In the fixture, the A4 stops on the steel bridge, so the classic capture shows the bridge sprite drawn over the train. The reference sprite sheet is the classic comparison.
- Evidence: `docs/3d/evidence/phase8/vehicles/train_009-angles.jpg` (Blender close-ups above the reference) and `train_009-in-game.jpg`.

**Coal wagons and coal truck (2026-10-17, approved by the user the same day; status in_game).**
- Kit additions in `vehicle_kit.py`:
  - `open_wagon` (walls, rim, ribs), `bulk_load` (a heaped cargo mound) and `bogie` (a two-axle diamond-frame freight bogie);
  - `road_wheel` (tyre, hub and boss, with an inner dual that is tyre only);
  - `sync_palette`, which adds new palette colours to an older `.blend` and updates changed ones.
- Palette: new `wagon_grey` and `hazard_yellow`.
- `train_029` (rail coal truck), from `kits/train_coal_wagons.py`: 1,902 triangles empty, 2,046 loaded. It has:
  - a grey open body with ribs, a centre door, hinges and a number panel;
  - solebars, buffers, steps and brake gear;
  - two diamond bogies in company colour, as in the sprite.
- `train_059` (monorail coal truck, shared by maglev 91): 620 triangles empty, 764 loaded. The same body sits on a closed base with company-colour panels and a hazard stripe.
  - No monorail or maglev train runs in the fixture, so it is reviewed from the Blender renders only.
- `road_007` (truck 123), remade (now built by `kits/road_kit.py` and `kits/road_vehicles.py`): 1,420 triangles empty, 1,540 loaded. It has:
  - a company-colour cab with wheel arches, a raked windscreen, side windows, doors, mirrors, headlights, a grille and a bumper;
  - a chassis, fuel tank, exhaust and tipper ram;
  - a grey tipper body with a headboard and tailgate hinges;
  - single front wheels and dual rear wheels.
- Review tooling:
  - `renderer_3d follow` now also matches wagons, stopping the consist that contains them.
  - `tools/phase8-vehicles.ps1 -Engine <id>` follows any engine.
- Evidence: `coal_wagons-angles.jpg`, `coal_wagons-in-game.jpg`, `road_007-angles.jpg` and `road_007-in-game.jpg` in `docs/3d/evidence/phase8/vehicles/`.

**Temperate wagons (2026-10-17, approved by the user the same day; status in_game).**
- Kit: the coal truck's underframes moved into `vehicle_kit.py` as `rail_underframe` and `mono_base`. The coal trucks rebuild with identical triangle counts.
- Palette: new `grain`.
- Script: `tools/3d_assets/kits/train_wagons.py` builds one body per cargo for rail wagons 27-37 and their monorail/maglev twins 57-67:
  - passenger carriage: windows, end doors, gangways and roof vents;
  - mail van: centre double doors, end windows and a post panel;
  - oil tanker: domed tank, grey centre band, dome, ladders and walkway on a cradle;
  - livestock van: open slats over a dark interior;
  - goods van: ribbed sides and a sliding door;
  - grain hopper: grey hopper with a company-colour foot stripe, chutes and grain load;
  - wood truck: plank deck and stakes; loaded, a log stack with company-colour binders;
  - iron ore hopper: company-colour open wagon with ore load;
  - steel truck: plank deck; loaded, three coils on chocks;
  - armoured van: panel seams, rivet rows, door and spy windows.
- Roofs: rail vans have dark roofs; the monorail passenger, mail and armoured vans have white roofs, as in their sprites. Freight bogies are company colour under the grey and wooden wagons, black under the company-colour bodies.
- Triangles (empty / loaded): rail 1,742-2,462 (the loaded wood truck 2,298, the armoured van 2,462); monorail 460-1,180. All are under the 2,500 wagon budget.
- Arctic and tropic wagons that share these sprites (for example 39, 40, 44-48, 69, 70, 74-78, 89-110) pick up the models through `shared_with`.
- Review: the fixture AI only builds coal trains, so these are reviewed from Blender renders beside their sprites. They use the same in-game path as the coal wagons.
- Evidence: `wagons_vans-angles.jpg`, `wagons_bulk-angles.jpg` and `wagons_mono-angles.jpg` in `docs/3d/evidence/phase8/vehicles/`.

**Temperate road vehicles (2026-10-17, approved by the user the same day after the road_003 door change; status in_game).**
- Kit: `tools/3d_assets/kits/road_kit.py` holds the lorry parts taken from the approved coal truck (cab, chassis, rear fittings, wheels). It adds two more cab styles, because each lorry cargo has three makers of different generations in the base set:
  - style 0: the coal truck's raked cab;
  - style 1: a taller rounded cab with an upright split windscreen, a visor, roof lamps and a vertical-bar grille;
  - style 2: a wedge cab with a long sloped dark windscreen, a roof deflector and a wide black grille band.
  The style is the maker's place in its cargo group.
- Script: `tools/3d_assets/kits/road_vehicles.py` builds the buses and lorries 007-039. `road_007` now comes from it too, with identical triangle counts; the old `road_007_coal_truck.py` is removed.
  - Buses: lower body between the wheel arches with arch liners, window band, entrance doors ahead of the front wheel, front and rear details. The Foster MkII (`road_003`) has the raked dark windscreen and roof air-conditioning pods; its doors are mid-body behind the front wheel and its mirrors sit on the sides, so nothing stands proud of the raked front (user feedback, 2026-10-17); the Hereford Leopard has a cc2 waist rail.
  - Tippers (coal, grain, iron ore): the coal truck's body, in grey or company colour, with heaped loads.
  - Box bodies (mail, goods, livestock, armoured): curved roof and rear doors; a post panel, ribs, slatted sides, or rivets and spy windows.
  - Oil tanker: elliptical tank with a grey band, manhole, walkway and hose lockers.
  - Flatbeds (wood, steel): plank deck and a company-colour headboard; loaded, two log bundles lying across with binders, or two steel coils.
- Triangles: buses 992-1,082; lorries 1,236-2,108. All are under the 4,000 budget.
- Review: only the coal truck runs in the fixture (it still renders correctly in game); the rest are reviewed from Blender renders beside their sprites.
- Evidence: `road_buses_vans-angles.jpg`, `road_boxvans-angles.jpg`, `road_tippers-angles.jpg` and `road_flatbeds-angles.jpg` in `docs/3d/evidence/phase8/vehicles/`.

**Temperate locomotives (2026-10-17, approved, in_game).**
- Inventory: the Jubilee (`train_008`) now owns image 0, as the A4 did for image 1. The toyland Powernaut (`train_003`) and the SH '8P' (`train_010`) are `shared_with` it.
- Renderer: the rear head of a multiheaded train, and a unit the player flipped, are now drawn turned round. This matches `Train::GetImage`, where the rear head uses the reversed sprite set (`spritenum + 1`) and a flipped unit reverses its direction. The change is in `RefreshTrains3D` in `rail3d_impl.h`. The A4 still faces forward in the vehicle capture.
- Script: `tools/3d_assets/kits/train_locos.py`.
  - Steam, built from the A4's parts:
    - Kirby Paul Tank (0): 0-6-0 side-tank engine with a bunker;
    - Jubilee (8, shared by 10): 4-6-0 with a short coal tender, splashers and outside cylinders.
  - Modern units come from one builder. The body is lofted, and each end is shaped by a nose: a flat cab, a short hood, a wedge or a bullet.
  - Paint zones (warning-yellow ends, stripes, roofs, skirts, windscreens) follow the nose shaping.
  - Roof kits: diesel fans and grilles, electric pantographs and insulators, or a sleek pod.
  - Underframes: rail bogies (two- or three-axle) with buffers and ploughs, or a monorail/maglev skirt.
  - Members: DMU (11), 'Dash' (12), '25' (13, shared by 15), '37' (14, short hoods, three-axle bogies), '125' power car (22, wedge nose), SH '30' (23, shared by 24), 'T.I.M.' (25), 'AsiaStar' (26), 'X2001' (54), 'Millennium Z1' (55), and Lev1-Lev4 (84-87).
- Triangles: 904-3,282. All are under the 4,000 budget.
- Review: only the A4 runs in the fixture, so these are reviewed from Blender renders beside their sprites.
- Evidence: `locos_steam_diesel-angles.jpg`, `locos_express_electric-angles.jpg` and `locos_monorail_maglev-angles.jpg` in `docs/3d/evidence/phase8/vehicles/`.

**Temperate ships (2026-10-17, approved, in_game).**
- Script: `tools/3d_assets/kits/ships.py`. Ships are authored at world size (a tile is 16 units), with the waterline at Z = 0. Lengths come from the diagonal sprites and beams from the end-on sprites:
  - tanker: 24 units long;
  - ferry: 17;
  - hovercraft: 18.5;
  - cargo ship: 28.
- Hulls are lofted with a fine raked bow, a rounded transom, sheer and a bulwark. The bottom band is dark and the topsides are cc1. The deck is olive, as in the sprites.
- Palette: added `deck_olive`, `hull_dark` and `paint_orange`.
- Members:
  - Oil tanker (`ship_000`, shared by 001): accommodation aft with a wheelhouse, bridge wings, a cc1 funnel and lifeboats. The deck has pipelines and a catwalk, tank hatches, cc1 pump houses, the manifold and a kingpost.
  - Passenger ferry (`ship_002`, shared by 003, 005 and 006): two saloon decks with window rows, red lifeboats, a sun deck with a cc1 panel, a bridge tower forward and a funnel aft.
  - Hovercraft (`ship_004`): rubber skirt, cc1 band, white hull with a cabin window row, and a forward cockpit. On top are cabin roofs either side of the car deck, four red pylons with propellers and rudders, and twin tail fins.
  - Cargo ship (`ship_007`, shared by 008, 009 and 010): two holds with black hatch covers, two orange deck cranes with red posts, and accommodation aft with a cc1 funnel. It also has mooring winches, a stores crane and a forecastle mast.
- Triangles: 1,220-1,972.
- Review: the fixture has no ships, so these are reviewed from Blender renders. Evidence: `ships-angles.jpg`.

**Temperate aircraft (2026-10-17, approved, in_game).**
- Script: `tools/3d_assets/kits/aircraft.py`. Aircraft are authored at world size, with Z = 0 the ground under the wheels. Span is measured from the nose-on sprite and length from the side-on sprite. The sizes run from 10 units (Sampson U52) to 26 (Yate Haugan).
- Parts:
  - lofted fuselage with a windscreen band and an upswept tail cone;
  - tapered and swept wing, tailplane and fin surfaces;
  - turbofan nacelles on pylons, prop engines with stopped propellers, and tail nozzles;
  - tricycle gear, window rows, and paint schemes on the fuselage (all-cc1, white with a cc1 cheatline, cc1 over a white belly).
- Members:
  - Sampson U52 (0) and Cotswald LB-3 (4), both twin piston;
  - Coleman Count (1), four turboprops;
  - FFP Dart (2), rear-engined with a T-tail;
  - Yate Haugan (3), a supersonic delta;
  - Luckett LB-8 (5), high wing, four jets and a white T-tail;
  - Luckett LB-10 (8), a trijet;
  - Darwin 200 (12) and Darwin 300 (13, a four-engined jumbo with an upper-deck hump);
  - Kelling K6 (27), with big nacelles and winglets;
  - Kelling K7 (28), a lifting-body spaceplane;
  - Hyperdart 2 (30), with twin canted fins;
  - Dinger 200 (31), three lobes with a box tail;
  - Dinger 1000 (32), three hulls on a bat-wing delta;
  - Tricario (38) and Guru X2 (39) helicopters.
- Helicopters: the game's separate rotor sprite vehicle is not drawn in 3D, so each helicopter model carries a stopped main rotor and tail rotor.
- Shared images follow the inventory.
  - Temperate engines that share an image show its model.
  - The inventory files several toyland aircraft (33-37, 40) as `shared_with` temperate owners because their base sprites coincide, so they show these models until toyland is modelled.
- Triangles: 892-2,262.
- Review: the fixture has no aircraft, so these are reviewed from Blender renders. Evidence: `aircraft_airliners-angles.jpg` and `aircraft_future_heli-angles.jpg`.

**Other climates' vehicles: deferred to Phase 10 (2026-10-17).** The user moved them out of Phase 8 because they are not a priority. 38 owner identities remain: 11 arctic/tropic, 12 tropic-only and 15 toyland. See Phase 10 in `OPENTTD_3D_CODEX_GUIDE.md`. Until then, the toyland engines filed `shared_with` temperate owners show the temperate models.

**Everything else specific to the other climates: deferred to Phase 10 (2026-10-17).** At the user's request, Phase 8 now finishes the temperate climate only. Moved: 63 houses, 25 industries and 37 trees found only in the sub-arctic, sub-tropical and toyland climates, and the review of the snow and desert ground textures. Identities that temperate shares with the other climates (bridges, tunnels, stations, signals, catenary and so on) stay in Phase 8.

## 8.6 Production

Work through `inventory.json` by category: one identity per task for `bespoke`, one kit then its members for `kit`, one family script then its member review for `family`. Suggested order, adjustable by the user: temperate houses, temperate industries, trees, map objects and field edges, stations/depots/stops, bridges and tunnel portals, then catenary. Temperate vehicles were done in 8.5. Signals, crossings and catenary follow stations. Everything specific to the other climates (vehicles, houses, industries, trees and their ground textures) is Phase 10. Rail/road surfaces stay renderer geometry unless the user asks otherwise.

Each task delivers the `.blend` (or kit/family script and member `.blend` files), exports, previews, converted assets and inventory updates, and touches no unrelated identity. Batches are committed per category once their in-game check passes.

**Temperate houses (2026-10-17, approved, in_game).** All 31 temperate houses are now in game.

- **The 18 houses the pilot didn't cover:** 000, 001, 002, 004, 007 (1×2), 010, 011, 012, 013, 017, 018, 019, 028, 030, 031, 032 (2×2), 036 and 040 (2×2).
- **Scripts:**
  - The pilot's scratch helpers are now `tools/3d_assets/kits/house_kit.py`. It adds barrel vaults, lofted walls, window grids (one strip per bay split into storeys by floor bands), pilasters, rooftop rails, steel construction frames, park trees and per-state overrides.
  - `kits/houses_temperate.py` holds one builder per house.
  - Run in Blender with `KEY` set, after `house_kit.py`.
- **Construction states:** these follow each sprite where it isn't the usual open shell:
  - piles and then a frame for 004;
  - towers first for 017;
  - masts before the tower for 036;
  - planting squares before the glass roof for 040;
  - for the parks, fountain and theatre, bare ground and then the finished scene.
- **Triangle budgets:** every model is within budget. The largest are 017 (596), 036 (593), the hotel (1,128 of 1,200) and the shopping centre (824 of 2,400).
- **Review sheets:** [offices and flats](evidence/phase8/houses/offices_flats.jpg), [tall offices](evidence/phase8/houses/offices_tall.jpg), [parks and landmarks](evidence/phase8/houses/parks_landmarks.jpg), [hotel, stadium, shopping centre](evidence/phase8/houses/large.jpg).
- **Build and tests:** the capped Release build passes, and ctest is 112/114 (the known savegame regressions).

**Temperate industries (2026-10-17, approved, in_game).** All 12 temperate industries are now in game: the pilot's coal mine and power station, plus sawmill (02), forest (03), oil refinery (04), oil rig (05), factory (06), steel mill (08), farm (09), oil wells (11), bank (12) and iron ore mine (18).

- **Scripts:**
  - `tools/3d_assets/kits/industry_kit.py` places one model per tile graphic on the layout 0 tiles, adds `<state>@layout<n>` collections for graphics only found in later layouts, and holds the shared parts (log piles, striped pipes, banded chimneys, sawtooth roofs, mine buildings on stilts).
  - `kits/industries_temperate.py` holds one function per tile graphic, grouped by industry. Run in Blender with `KEY` set, after `house_kit.py` and `industry_kit.py`.
- **Review method:** the sprite references only show assembled layouts, so each tile graphic was rendered alone at every construction stage, at the same scale as its sprite, side by side.
- **Construction states:** each follows its sprite. Oil rig tiles show the legs first, then the decks, then the modules. Farm, sawmill log piles and refinery tiles start as bare ground where the sprite does.
- **Done in 8.7:** the gas-flare flames on the refinery flare stack and the oil rig flare boom were taken off the static models. They came back as animated flames, as moving parts (see 8.7).
- **Palette:** added `tank_blue`, `copper_green` and `pig_pink`.
- **Triangle budgets:** every tile graphic is within 600; the largest is a forest tile at 522.
- **Review sheets:** [sawmill](evidence/phase8/industries/02_sawmill.jpg), [forest](evidence/phase8/industries/03_forest.jpg), [refinery](evidence/phase8/industries/04_refinery.jpg), [oil rig](evidence/phase8/industries/05_oil_rig.jpg), [factory](evidence/phase8/industries/06_factory.jpg), [steel mill](evidence/phase8/industries/08_steel_mill.jpg), [farm](evidence/phase8/industries/09_farm.jpg), [oil wells](evidence/phase8/industries/11_oil_wells.jpg), [bank](evidence/phase8/industries/12_bank.jpg), [iron ore mine](evidence/phase8/industries/18_iron_ore_mine.jpg). They were made before the flames were removed.
- **Build and tests:** the capped Release build passes, and ctest is 112/114 (the known savegame regressions).

**Map objects, field edges and rocks (2026-10-17, approved, in_game).** The temperate trees were already done in the pilot; the other climates' trees are Phase 10. This batch covers the transmitter, lighthouse, company statue, owned-land flag, all five company HQ sizes (2x2), the six field fence and hedge types and the rock clusters. The canal lock is filed under water and follows with stations and docks.

- **Runtime hooks (new):** these identities had no 3D drawing before.
  - Map objects use `Art3D::Object`: the ObjectType, or `OBJECT_HQ` plus the HQ size from the animation frame. The 2x2 HQ is one model drawn from its north tile. Faces in `cc1` take the owner's company colour, and objects are tagged `TO_STRUCTURES` for transparency.
  - Field fences use `Art3D::Fence`. `TerrainTile::fences` holds the fence type per side; one edge model is turned to each side.
  - Rock clusters use `Art3D::Rocks` on rocky land, turned by the tile hash.
  - Fences, rocks and the owned-land flag keep every vertex at its height above the rendered tile surface, so they follow slopes. As in `DrawTile_Clear`, none are drawn under snow. Owned land shows bare earth.
  - The converter writes two new tables, `objects` and `landscape`. `renderer_3d coverage` logs every object, fence and rock tile with the model it resolves to.
- **Scripts:** `tools/3d_assets/kits/objects_temperate.py`, one builder per identity, run in Blender with `KEY` set after `house_kit.py`.
- **Triangle budgets:** every model is within budget; the largest is the huge HQ (1,072 of 2,400).
- **In-game check:** `tools/phase8-objects.ps1` (`-Pass scan` or `capture`) runs the 8.3 farm map (seed 20261016). The fixture AI in `fixtures/phase8/objects/ai` builds a company HQ and a statue.
  - The statue, the tiny HQ, four lighthouses, 513 fence edges and 303 rock tiles all resolve to models.
  - The dirty, mesh and bounds references report no mismatches, and the GPU reference differs by at most 1 pixel. The 3D check reports zero failures.
  - The flat map has no transmitter, scripts cannot buy land, and HQs only grow with company performance. These identities and the four larger HQ sizes were reviewed on the sprite comparison sheets.
  - The first run hit the known NVIDIA `glTexImage2D` crash on the classic-to-3D switch, so the classic shot now comes last.
- **Review sheets:** [objects](evidence/phase8/objects/objects.jpg), [company HQs](evidence/phase8/objects/hq.jpg), [fences and rocks](evidence/phase8/objects/fences.jpg).
- **Game shots:** [town](evidence/phase8/objects/game-town.jpg), [town, classic view](evidence/phase8/objects/game-town-classic.jpg), [town orbit](evidence/phase8/objects/game-town-orbit.jpg), [fields](evidence/phase8/objects/game-fields.jpg), [fields orbit](evidence/phase8/objects/game-fields-orbit.jpg), [rocks](evidence/phase8/objects/game-rocks.jpg), [lighthouse](evidence/phase8/objects/game-lighthouse.jpg).
- **Build and tests:** the capped Release build passes, and ctest is 112/114 (the known savegame regressions).

**Stations, stops, depots and water (2026-10-17, approved, in_game).** This batch covers the rail platform, station building, the two halves of the large glass train shed (roofs A and B), the rail waypoint, the bus and lorry bays, the drive-through bus and lorry stops, the road waypoint, the dock (land and water parts), the buoy, the rail, road and ship depots, and the canal lock. The nine airports follow as their own batch, one model per airport tile graphic.

- **Canonical turn:** every piece is one tile, authored in a canonical turn that the renderer rotates.
  - Track or road runs along local X.
  - Bay entrances, depot exits and the dock's water side face +Y.
  - The lock rises towards +Y.
  - Multi-tile pieces are cut per tile in Blender: dock land and water parts, ship depot north and south (`DepotPart`), and lock middle, lower and upper (`LockPart`). Each lock part is placed relative to its own tile's base height.
- **Runtime hooks:**
  - `Art3D::Station(id, part)` selects the model. The ids are `STATION_IDS` in the converter and `Station3D` in `asset3d_impl.h`.
  - `ReadStation3D` reads the piece, its turn (`TerrainTile::art_turn`) and its owner from the map. It covers rail station graphics 0–7, waypoints, road stops, docks, buoys, depots and locks.
  - The dock's water part takes its direction from the land part beside it.
  - Pieces from NewGRF stations and NewGRF road stops, oil rigs and airports keep the Phase 6 placeholders. Those placeholders are now drawn only where no model exists.
  - Water pieces sit at the water level. The dock's land part follows its slope. Everything else stands on its foundation.
  - `cc1` faces take the owner's company colour, as the sprites' company-colour remap does. Pieces are tagged `TO_BUILDINGS`.
  - A lock's sloped middle tile now draws as water instead of beach.
  - `renderer_3d coverage` logs each piece with its tile count, turn and model, plus any pieces that resolve to no model.
- **Glass roofs:** station glass is left open, as frames and glazing bars with thin panes, so trains stay visible under the roofs, as with the transparent roof sprites.
- **Scripts:** `tools/3d_assets/kits/stations_temperate.py`, run in Blender with `KEY` set after `house_kit.py` and `industry_kit.py`.
- **Triangle budgets:** every model is within the 600 per tile budget; the largest is the dock's water part (552).
- **In-game check:** `tools/phase8-stations.ps1` (`-Pass scan` or `capture`) runs the farm map. The fixture AI in `fixtures/phase8/stations/ai` builds every piece near the largest town:
  - a 3x5 X-axis station and a 1x3 Y-axis station, which give platforms, buildings and both roofs;
  - rail and road depots, a waypoint, bus and lorry bays and drive-through stops;
  - a dock, a buoy, two ship depots and a lock.
- **Results:**
  - Every piece resolves to a model (`missing=0`).
  - The dirty, mesh and bounds references report no mismatches, and the GPU reference differs by at most 2 pixels. The 3D check reports zero failures.
  - There is no script command for road waypoints, so that model was reviewed on the comparison sheet only.
- **Review sheets:** [rail](evidence/phase8/stations/rail.jpg), [road](evidence/phase8/stations/road.jpg), [water](evidence/phase8/stations/water.jpg).
- **Game shots:** [rail](evidence/phase8/stations/game-rail.jpg), [rail orbit](evidence/phase8/stations/game-rail-orbit.jpg), [rail, classic view](evidence/phase8/stations/game-rail-classic.jpg), [stops and depots](evidence/phase8/stations/game-stops.jpg), [stops orbit](evidence/phase8/stations/game-stops-orbit.jpg), [stops, classic view](evidence/phase8/stations/game-stops-classic.jpg), [dock, buoy and ship depots](evidence/phase8/stations/game-water.jpg), [water orbit](evidence/phase8/stations/game-water-orbit.jpg), [water, classic view](evidence/phase8/stations/game-water-classic.jpg), [lock](evidence/phase8/stations/game-lock.jpg), [lock orbit](evidence/phase8/stations/game-lock-orbit.jpg).
- **Build and tests:** the capped Release build passes, and ctest is 112/114 (the known savegame regressions).

**Airports (2026-10-17, approved, in_game).** All nine original airports (country, commuter, city, metropolitan, international, intercontinental, heliport, helidepot, helistation) are now in game, as one model per base airport tile graphic (0–73).

- **Layouts:** `build_references.py` now records each airport's tile layout in `inventory.json` and writes one reference image per tile graphic (`airport_tiles/`).
  - Each airport's `.blend` holds its whole assembled layout, authored in world axes. The converter cuts it per tile by object centre, as for industries.
  - A graphic shared by several airports is taken from the first airport in inventory order.
- **Animation:** states `default` and `frame_1`..`frame_11` hold only the animated tiles. The radar dish (graphics 31, 51, 52) turns through 12 frames and the wind sock (39, 73) swings through 4. Other tiles fall back to frame 0.
- **Ground:**
  - Each tile's terrain is concrete or grass (`GRASS_3`), whichever covers most of its sprite.
  - Taxiway tiles that split between the two get a flat overlay for the smaller part, cut along the sprite's edges with screen-aligned half-planes. The new palette colours `apron` and `turf` are the means of the two terrain textures; the overlays have no texture.
  - Plain apron and grass tiles have no model, and `TerrainTile::art_bare` stops the Phase 6 placeholder drawing on them.
- **Details:**
  - The heliport pad is at z=60, where helicopters land.
  - Fences, terminals, hangars and the tower use `cc1` for the owner's company colour.
- **Runtime hooks:** `ReadStation3D` reads the airport graphic and its animation frame, and `Art3D::AirportTile(gfx, frame)` selects the model. NewGRF airport tiles keep the placeholder.
- **Scripts:** `tools/3d_assets/kits/airports_temperate.py`, one function per tile graphic. Run in Blender with `KEY` set, after `house_kit.py` and `industry_kit.py`.
- **Triangle budgets:** every tile is within 600; the largest is 396.
- **In-game check:** `tools/phase8-airports.ps1` (`-Pass scan` or `capture`) runs the farm map in 2005.
  - The fixture sets `never_expire_airports`, so the country airfield can still be built, and `town_council_tolerance = 3`, since a stricter council allows only two airports per town.
  - The fixture AI in `fixtures/phase8/airports/ai` builds all nine types near the largest towns.
- **Results:**
  - Every tile resolves to a model or is bare by design (`missing=0`).
  - The dirty, mesh and bounds references report no mismatches, and the GPU reference differs by at most 7 pixels. The 3D check reports zero failures.
  - The aircraft the fixture orders at the city airport doesn't appear in the shots.
- **Review sheets:** [city, metropolitan, international](evidence/phase8/airports/large.jpg), [intercontinental, commuter, country](evidence/phase8/airports/hub.jpg), [heliport, helidepot, helistation](evidence/phase8/airports/heli.jpg).
- **Game shots:** [city](evidence/phase8/airports/game-city.jpg), [city orbit](evidence/phase8/airports/game-city-orbit.jpg), [city, classic view](evidence/phase8/airports/game-city-classic.jpg), [international](evidence/phase8/airports/game-international.jpg), [international orbit](evidence/phase8/airports/game-international-orbit.jpg), [intercontinental](evidence/phase8/airports/game-intercontinental.jpg), [intercontinental orbit](evidence/phase8/airports/game-intercontinental-orbit.jpg), [intercontinental, classic view](evidence/phase8/airports/game-intercontinental-classic.jpg), [metropolitan](evidence/phase8/airports/game-metropolitan.jpg), [small airports](evidence/phase8/airports/game-small.jpg), [small orbit](evidence/phase8/airports/game-small-orbit.jpg), [country](evidence/phase8/airports/game-country.jpg), [country orbit](evidence/phase8/airports/game-country-orbit.jpg).
- **Build and tests:** the capped Release build passes, and ctest is 112/114 (the known savegame regressions).

**Bridges and tunnels (2026-10-17, approved, in_game).** All 13 original bridge types (`bridge_00`..`bridge_12`) and both tunnel portals (`tunnel_rail`, `tunnel_road`) are now in game. Bridge sprites are the same in every climate, so one set covers all four.

- **Pieces:** each bridge has deck pieces as `CalcBridgePiece` names them (north, south, inner north, inner south, middle odd, middle even), a sloped `ramp`, a flat `ramp_flat` for heads on sloped tiles, and pillars (`pillar` or `pillar_<piece>`).
  - A piece with no model of its own uses the type's `middle` model. Wood, concrete, arch girder and girder have only `middle`; suspension has all six; cantilever and tubular have north, south and middle.
  - Pieces are authored along local X and placed with `AppendTurnedModel3D` and `TravelTurn3D`, so one model serves both axes. Ramps are authored as the north head of an X bridge.
  - Pillar segments are 8 high and stack under the deck down to the ground. They are left out where routes cross below, and on stations, depots, ramps, portals, locks and ship depots.
- **Palette:** six new colours for the steel bridges: `oxide`, `oxide_light`, `steel_yellow`, `steel_blue`, `steel_brown`, `steel_red`.
- **Converter:** `convert_gltf.py` writes the `bridges` and `tunnels` tables, read through `Art3D::BridgePiece`, `BridgePillar`, `BridgeRamp` and `Tunnel`.
- **Runtime hooks:** `ReadRail3D` records the deck piece and type, the ramp type and the portal kind; `BuildRail3D` places the models. NewGRF bridges and bridges over water keep the placeholders. `AuditCoverage3D` logs `PHASE8 BRIDGE` lines.
- **Scripts:** `tools/3d_assets/kits/bridges.py`, one function per family plus the two portals. Run in Blender with `KEY` set, after `house_kit.py` and `industry_kit.py`. `build_references.py` also writes assembled span references (`bridge_spans/`).
- **Triangle budgets:** the largest piece is a tubular middle at about 424 triangles; the portals are 145 (rail) and 78 (road).
- **In-game check:** `tools/phase8-bridges.ps1` (`-Pass scan` or `capture`) runs the farm map in 2012, when every type is available.
  - The fixture AI in `fixtures/phase8/bridges/ai` builds every type as a rail bridge along X, 7 tiles where allowed. Extra 5-tile suspension bridges show the middle-odd piece. It also builds road bridges along Y.
  - It raises two plateaus with four valley bridges between them (heads on slopes), a rail and a road tunnel through one plateau, and an arch bridge over a railway.
  - The capture runs its checks before the classic-view shots and quits without switching back to 3D, because two earlier runs hit the known NVIDIA `glTexImage2D` crash on that switch.
- **Results:**
  - Every piece, ramp and portal resolves to a model (`missing=0`).
  - The dirty, mesh and bounds references report no mismatches, and the GPU reference differs by at most 23 pixels. The 3D check reports zero failures.
- **Review sheets:** [wood, concrete, arch girder, girder](evidence/phase8/bridges/beam_arch.jpg), [suspension](evidence/phase8/bridges/suspension.jpg), [cantilever](evidence/phase8/bridges/cantilever.jpg), [tubular](evidence/phase8/bridges/tubular.jpg), [Y axis](evidence/phase8/bridges/y_axis.jpg).
- **Game shots:** [valley bridges](evidence/phase8/bridges/game-valley.jpg), [valley orbit](evidence/phase8/bridges/game-valley-orbit.jpg), [valley, from behind](evidence/phase8/bridges/game-valley-back.jpg), [valley, classic view](evidence/phase8/bridges/game-valley-classic.jpg), [tunnels](evidence/phase8/bridges/game-tunnels.jpg), [tunnels orbit](evidence/phase8/bridges/game-tunnels-orbit.jpg), [tunnels, from the north](evidence/phase8/bridges/game-tunnels-north.jpg), [tunnels, classic view](evidence/phase8/bridges/game-tunnels-classic.jpg), [suspension, cantilever and tubular](evidence/phase8/bridges/game-west.jpg), [west orbit](evidence/phase8/bridges/game-west-orbit.jpg), [west, classic view](evidence/phase8/bridges/game-west-classic.jpg), [arch, wood and girder](evidence/phase8/bridges/game-north.jpg), [north orbit](evidence/phase8/bridges/game-north-orbit.jpg), [north, classic view](evidence/phase8/bridges/game-north-classic.jpg), [road bridges](evidence/phase8/bridges/game-road.jpg), [road orbit](evidence/phase8/bridges/game-road-orbit.jpg), [arch bridge over rail](evidence/phase8/bridges/game-over-rail.jpg).
- **Build and tests:** the capped Release build passes, and ctest is 112/114 (the known savegame regressions).

**Catenary (2026-10-18, approved, in_game).** `catenary_rail`, the last rail furniture identity, is now drawn in 3D. Before this, the 3D view drew no catenary at all. Catenary sprites are the same in every climate.

- **Placement:** pylons and wires go where the classic view draws them, using the same code.
  - `CollectRailCatenary(tile, pieces)` in `elrail.cpp` runs the classic drawing functions with a capture switch on. Instead of drawing each sprite, they record a `RailCatenaryPiece`.
  - A pylon records its position, elevation and the pylon control point it serves.
  - A wire records its two end points and which ends have a pylon. Rail wires run between the track's two control points at their `GetPCPElevation` heights, so slopes, foundations and bridge ramps keep the classic heights. Bridge wires sit at deck height. Tunnel wires run from the entrance into the hill, and depot wires from the exit to the door.
  - Recording ignores the transparency and invisibility settings, so the snapshot doesn't depend on them. A wire under a low bridge is always left out.
- **Models** (`tools/3d_assets/families/catenary.py`, one `.blend` with four states):
  - `pylon` and `pylon_diagonal`: a concrete mast with the sprite's triangular cantilever and red insulators. The cantilever reaches 4 units (straight positions) or 2.83 (diagonal positions). The renderer turns it towards the control point.
  - `wire_both` and `wire_half`: a contact wire, a messenger wire and droppers. `wire_both` sags between pylons one tile apart; `wire_half` is half of a two-tile span. The renderer stretches a span between its end points and shears it on slopes (`AppendSpanModel3D`).
  - The contact wire is at 7.3, just above the raised pantographs of the electric locomotives (7.06).
  - Every state has 74 triangles or fewer.
- **Runtime:** `TerrainTile::catenary` holds the pieces, so the dirty-tile comparison picks up changes to them. The 3×3 dirty marking covers changes from neighbouring tiles. The faces are tagged `TO_CATENARY`. `Art3D::Catenary(piece)` selects the model, and `renderer_3d coverage` logs a `PHASE8 CATENARY` line with the piece counts and any piece without a model.
- **In-game check:** `tools/phase8-catenary.ps1` runs the farm map in 2012. `-Pass scan` logs the layout, `capture` takes the 3D shots and runs the checks, and `classic` takes the classic-view shots in a run that never switches to 3D.
  - The fixture AI in `fixtures/phase8/catenary/ai` levels a 26x16 site near the largest town. On it, it builds:
    - an X line that climbs over a raised block, crossed by a Y line (junction) and by a road (level crossing);
    - a diagonal line;
    - a two-platform station with track at both ends and a depot;
    - a tunnel through the raised block and a rail bridge;
    - an AsiaStar that leaves the depot and is stopped east of the station, under the wire.
- **Results:**
  - Every piece resolves to a model (`missing=0`): 69 tiles, 35 pylons, 7 diagonal pylons, 9 single-tile wires and 61 half-span wires.
  - The dirty, mesh and bounds references report no mismatches, and the GPU reference differs by at most 7 pixels. The 3D check reports zero failures.
  - Pylons repeat every two tiles and alternate sides as in the classic view. The contact wire runs at the pantograph heads.
- **The `glTexImage2D` crash, found and fixed:** the crash recorded in earlier batches came from our code, not the driver.
  - The classic driver leaves `GL_UNPACK_ROW_LENGTH` at the screen pitch after its screen uploads.
  - `renderer_3d check` (it switches the chunk size) and switching the view both reset the terrain, so the next 3D frame uploads the whole ground map. That upload (`UploadGroundMap`) didn't reset the row length, so the driver read the 128x128 map as 1280-byte rows, far past its end.
  - It now sets the row length to 0 first. The bridges capture, which had crashed on every run, passed twice in a row with all its shots, and so did the catenary capture.
  - The classic shots still have their own pass.
- **Review sheet:** [pylons and wires](evidence/phase8/catenary/catenary.jpg).
- **Game shots:** [overview](evidence/phase8/catenary/game-overview.jpg), [overview orbit](evidence/phase8/catenary/game-overview-orbit.jpg), [overview, classic view](evidence/phase8/catenary/game-overview-classic.jpg), [junction](evidence/phase8/catenary/game-junction.jpg), [junction orbit](evidence/phase8/catenary/game-junction-orbit.jpg), [junction, classic view](evidence/phase8/catenary/game-junction-classic.jpg), [hill and tunnel](evidence/phase8/catenary/game-hill.jpg), [hill orbit](evidence/phase8/catenary/game-hill-orbit.jpg), [hill, classic view](evidence/phase8/catenary/game-hill-classic.jpg), [station](evidence/phase8/catenary/game-station.jpg), [station orbit](evidence/phase8/catenary/game-station-orbit.jpg), [station, classic view](evidence/phase8/catenary/game-station-classic.jpg), [train under the wire](evidence/phase8/catenary/game-train.jpg), [train, from behind](evidence/phase8/catenary/game-train-back.jpg), [diagonal](evidence/phase8/catenary/game-diagonal.jpg), [diagonal, classic view](evidence/phase8/catenary/game-diagonal-classic.jpg), [bridge](evidence/phase8/catenary/game-bridge.jpg), [bridge orbit](evidence/phase8/catenary/game-bridge-orbit.jpg), [bridge, classic view](evidence/phase8/catenary/game-bridge-classic.jpg).
- **Build and tests:** the capped Release build passes, and ctest is 112/114 (the known savegame regressions). The art table test now also covers the catenary pieces.

## 8.7 States and polish

Complete construction stages, cargo/load variants, growth stages, company colours and any presentation-only animation the user wants (e.g. rotating headframes, smoke, and simple gas-flare flames for the refinery flare stack and the oil rig flare boom, which were left off the static models), driven only by existing authoritative state.

The user chose industry animations, gas-flare flames, and smoke and other effects for this step. Disaster vehicles are not included.

- **Industry moving parts** (`tools/3d_assets/kits/industry_kit.py`, `build_parts`):
  - A moving part is left out of the static tile model. Each step of it is a `part_<n>` state on the graphic's first tile, and the game draws the step over the static tile.
  - Coal mine headframe wheel: 3 steps.
  - Power station sparks: 6 steps of a bolt between the pylons, none on frame 0.
  - Refinery flare stack and oil rig flare boom: 4 steps of a flickering flame each (`flame` in the kit).
  - Oil well pump: 12 steps of the walking beam, horsehead, crank and counterweight. The static well keeps the pad, Samson post, gearbox and casing.
  - At most 120 triangles per step.
- **Effects** (`tools/3d_assets/families/effects.py`, nine `.blend` files):
  - One model per sprite of each classic sequence (`frame_<n>`): chimney smoke, steam, diesel smoke, electric sparks, smoke, large and small explosions, breakdown smoke.
  - The roadworks bulldozer is one model (`default`), turned to the sprite's direction.
  - Puffs grow and then break up as the sprites thin out. Plumes lean towards −X, as the classic plumes lean up and right on screen.
  - At most 280 triangles per frame.
- **Glowing colours:** `flame_yellow`, `flame_orange`, `flame_red` and `spark_blue` are drawn unlit, at full colour on every side.
  - The converter adds 2 to these colours.
  - The CPU path (`AddTerrainFace`) and the shader draw any colour above 1.5 unlit, less 2.
- **Runtime** (`RefreshEffects3D` in `rail3d_impl.h`):
  - Every frame it collects the effect vehicles. `EFFECT3D_SEQUENCES` maps each vehicle's sprite to a sequence and frame.
  - It also collects the moving parts of completed base industry tiles. `IndustryPartStep3D` picks the step from the tile's animation frame, except the flare stacks: they have no animation, so the flame flickers with the game tick.
  - Both are drawn from the model library like vehicles (`DrawProofVehicles`), with a CPU reference for the checks (`AppendEffectInstances3D`).
  - The list is only rebuilt, and the view redrawn, when an instance changes.
  - Effects hide with their transparency option, as in the classic view. Parts follow the industries option and stipple like their tile.
  - Toyland bubbles have no model yet (Phase 10).
  - `renderer_3d coverage` logs a `PHASE8 EFFECTS` line with counts per sequence, the industry parts and any effect without a model.
- **In-game check:** `tools/phase8-effects.ps1` runs a generated 128x128 temperate map with sea, in 1975, with breakdowns set to normal. `-Pass scan` logs the layout, `capture` takes the 3D shots and runs the checks, and `classic` takes the classic-view shots.
  - The fixture AI in `fixtures/phase8/effects/ai` funds a power station, coal mine, oil wells, refinery and oil rig.
  - It runs a steam, a diesel and an electric train on their own lines.
  - It rebuilds the town's roads, which brings out the roadworks bulldozer.
  - It crashes two diesel trains with four wagons each. They run between stations on a line with a gap. The AI holds them, closes the gap and restarts them so that they collide about 30 ticks before the 1 February shot. The config sets `competitor_speed = 4`, so the AI runs every tick and `GetTick()` counts game ticks.
- **Results:**
  - Every effect resolves to a model (`missing=0`), and the 9 moving parts are drawn.
  - The run drew chimney smoke, steam, diesel smoke, sparks, the large explosion, breakdown smoke and the bulldozer. Generic smoke (from disasters, which are off) and the small explosion did not appear; they were reviewed on the sheets only.
  - The crash came on 31 January at the planned tick, and the 1 February shot shows the explosion.
  - The 3D check reports zero failures for heights and for 286 picks. The dirty, mesh and bounds references report no mismatches.
  - **Open:** the GPU reference differs by more than 7 pixels on 94 of 279 checks, up to 1390, but only while the camera is on the oil wells and on the power station orbit. A dump of one such frame shows a one-pixel shift along a long edge of a pump beam. Thin moving parts there round to a different pixel row in the instanced draw than in the CPU reference. The other shots with parts and effects stay within 7 pixels.
  - A screenshot is only taken at the next draw, and scripts can only be scheduled a month apart, so the crash has no orbit shot: the wreck is cleared before the next month.
- **Review sheets:** [smoke](evidence/phase8/effects/smoke.jpg), [sparks, explosions and the bulldozer](evidence/phase8/effects/fire.jpg), [industry moving parts](evidence/phase8/effects/parts.jpg).
- **Game shots:** [crash](evidence/phase8/effects/game-crash.jpg), [crash, classic view](evidence/phase8/effects/game-crash-classic.jpg), [power station](evidence/phase8/effects/game-power.jpg), [power station orbit](evidence/phase8/effects/game-power-orbit.jpg), [power station, classic view](evidence/phase8/effects/game-power-classic.jpg), [coal mine](evidence/phase8/effects/game-coal.jpg), [coal mine orbit](evidence/phase8/effects/game-coal-orbit.jpg), [coal mine, classic view](evidence/phase8/effects/game-coal-classic.jpg), [oil wells](evidence/phase8/effects/game-wells.jpg), [oil wells orbit](evidence/phase8/effects/game-wells-orbit.jpg), [oil wells, classic view](evidence/phase8/effects/game-wells-classic.jpg), [trains](evidence/phase8/effects/game-trains.jpg), [trains orbit](evidence/phase8/effects/game-trains-orbit.jpg), [trains, classic view](evidence/phase8/effects/game-trains-classic.jpg), [refinery](evidence/phase8/effects/game-refinery.jpg), [refinery orbit](evidence/phase8/effects/game-refinery-orbit.jpg), [refinery, classic view](evidence/phase8/effects/game-refinery-classic.jpg), [oil rig](evidence/phase8/effects/game-rig.jpg), [oil rig orbit](evidence/phase8/effects/game-rig-orbit.jpg), [oil rig, classic view](evidence/phase8/effects/game-rig-classic.jpg), [roadworks](evidence/phase8/effects/game-roadworks.jpg), [roadworks, classic view](evidence/phase8/effects/game-roadworks-classic.jpg).
- **Build and tests:** the capped Release build passes, and ctest is 112/114 (the known savegame regressions). The art table test now accepts the glowing colours.

## 8.8 Final checks

Re-run the Phase 7 benchmarks and packaging checks with the full library; adjust triangle budgets or add LOD only where measurements require it. Re-run the Phase 4–6 live fixtures for footprint, picking, occlusion and signal readability.

## Gate

Every identity in `inventory.json` used in the temperate climate, including landscape objects and ground textures, is `in_game` or `shared` with a reason; identities only found in other climates are Phase 10. No accidental Phase 5 fallbacks or magenta placeholders remain in temperate. The user has approved the models. Textured ground works in every viewport. Picking, footprints, occlusion, simulation behavior and Phase 7 performance are preserved. NewGRF models remain separate scope.

## Licensing

Models are original work by the user and the assisting agents, licensed GPL-2.0-only with the repository. `.blend` sources, exports, previews and the converter are kept together; `manifest.json` records provenance per model. Reference sprites come from the installed base set and are not distributed with the game.
