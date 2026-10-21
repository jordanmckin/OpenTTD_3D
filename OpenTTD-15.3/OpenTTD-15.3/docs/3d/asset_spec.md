# Phase 5 asset specification

The runtime format is a generated, immutable C++ triangle table (`src/video/asset3d_generated.h`). The matching `assets/3d/library.json` is the interchange/debug export. This deliberately fits the existing untextured triangle renderer: no glTF loader, runtime parser, Blender installation or external resource search path is needed. Python source is in workspace `tools/3d_assets/generate.py`. Both exports and a vector contact sheet are checked in. Run `python tools/3d_assets/generate.py` to rebuild and `python tools/3d_assets/verify.py` to validate. Python uses only the standard library.

## Coordinates and geometry

- One unit is one engine world pixel: a tile is 16 by 16, one terrain height step is 8. Z points up. Static tiles start at their north corner `(0,0,0)` and extend along engine X/Y, with the foundation height applied at placement.
- Vehicles are centered at their authoritative simulation position. Local +X is forward; the existing eight-direction basis rotates each independent vehicle part. Longitudinal scale follows cached vehicle length. Local Z=0 is the wheel contact plane; visible wheel boxes start at 0.3 to avoid ground fighting.
- Trees are centered at their trunk base and placed at individual terrain heights. Count and growth come from the map. Four fixed in-tile offsets avoid a simulation RNG dependency.
- Platforms use tile-local +X along the track. Y-axis stations rotate the model 90 degrees and translate it inside the same tile. Four stadium quadrants follow the engine's `(0,0), (0,1), (1,0), (1,1)` house-ID order.
- Faces contain three positions and an RGB material color in `[0,1]`. No textures, alpha, UVs, bones, tangents, external materials or PBR are required. Lighting is computed after placement, so rotated surfaces use world-space normals. Bottom faces are intentionally omitted. Bounds are derived from emitted triangles for existing chunk culling.

## Naming, reproducibility and budget

Models use lower-case snake-case names; generated enums use upper-case names. JSON schema version is 1, library seed/version marker is 20261016. The current generator uses deterministic ID-based variants and fixed coordinates, without any random-number calls; the seed is provenance metadata, not a runtime random source. Roof, window, box and cone modules share brick, cream, slate, glass, steel, coal and green colors. House variants are stable by base-house identity.

Each asset is under 600 triangles. The current LOD policy is one low-poly mesh at every zoom; chunk culling remains active, with no unmeasured instancing or extra LOD levels. Per-model counts are in `manifest.json`. Runtime assets are embedded in the executable; source scripts, JSON and previews are authoring artifacts, not required game data. Regeneration is explicit and never occurs during a game or ordinary build.

## Registry and coverage

`library.json` enumerates all 110 original house identities, reading labels and IDs from this checkout's `table/town_land.h`; generation asserts contiguous IDs. A named category model is a stylized substitute, not an exact reconstruction of the original artwork. Offices, hotels and apartment blocks share a model, and most multi-tile buildings use a module per occupied tile. Stadiums have four matching quadrants. Igloo (102), tepees (103) and piggy bank (109) remain conspicuous magenta placeholders. Out-of-range house IDs also use that placeholder.

Industry identities come from `table/build_industry.h`: type 0, graphics 0..6 map to mine headframes, halls and coal yards; type 1, graphics 7..10 map to power halls, stacks and yards. Type 6 uses the factory module on each occupied tile. Other industries use the magenta placeholder. The live fixture tests the mine/power chain; factory is export/geometry tested only. Construction stages 0..2 use a common construction-site model; completed tiles use the registered asset. Construction/removal/growth changes are included in chunk snapshot comparisons.

Engine IDs from `table/engines.h`: 0 and 9 use the locomotive; 29, 59 and 91 use the coal wagon; 123..125 use the truck. The fixture exercises 9, 29 and 123. Other engines retain the explicit Phase 4 generic boxes; GRF-backed engines are not assigned these base models. Loaded coal wagons contain a visible coal insert based on stored cargo. Vehicles still use the original authoritative hidden/depot state and discrete directions. Wheels are static low-poly geometry; animation and company colors are follow-up.

Trees currently share a generic green silhouette, with a bare silhouette for dying/dead stages. Species and climate-specific art are not covered. Rail station platforms share one canopy model. Depot, road-stop and bridge geometry remains from Phase 4. Ships, aircraft, remaining industry types, exact hotel footprints, seasonal materials and arbitrary NewGRF mapping are outside this library gate.

## Licensing

The generator, generated geometry, preview and integration are original procedural work licensed GPL-2.0-only with the repository. No third-party models, textures or image-generation service were used. `assets/3d/manifest.json` records provenance, per-model triangle counts and the JSON SHA-256. Preserve OpenTTD's existing copyright and license notices and distribute the generator alongside exported assets. The original house/engine/industry tables remain covered by OpenTTD's license. OpenGFX remains separately required for the original GUI/classic view and retains its existing notices.
