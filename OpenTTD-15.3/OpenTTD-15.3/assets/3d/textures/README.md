# Ground textures

One 128×128 seamless image per ground layer (`Ground3D::Layer`, `src/video/ground3d.h`). Each image covers two tiles (32 world units) and repeats in world X/Y; terrain has no UVs.

| Layers | Game state |
|---|---|
| `grass_0`…`grass_3` | Clear grass density 0–3 (also trees on grass, rail/road on barren or grassy ground) |
| `rough`, `rocks` | Rough and rocky land |
| `field_0`…`field_8` | Farm field type (`GetFieldType`) |
| `snow_0`…`snow_3` | Snow density (arctic) |
| `desert_0`…`desert_3` | Desert density (tropic) |
| `beach`, `water` | Shore and open water |
| `concrete` | Paved roadsides, road stops, airports, industry lots |

- `ground_textures.blend` shows every layer tiled 2×2 for review. Paint an image in Texture Paint and save it, then run `python tools/3d_assets/art.py textures` to embed the PNGs in `src/video/ground3d_textures.h`. Hand-painted PNGs are kept.
- The starting images come from `tools/3d_assets/ground_textures.py` (periodic noise recipes in Blender). `art.py textures --force <layer>` regenerates one layer from its recipe and overwrites any hand edits.
- `python tools/3d_assets/preview_textures.py` writes `previews/ground_textures.png`: the classic sprites beside the new layers.
- Rendering: the texture is multiplied by the face's existing light. Near tile edges, neighbouring layers blend through a noise-warped band. Fields and concrete keep straight tile edges, and water never blends. Without texture support the game uses each layer's mean colour.
