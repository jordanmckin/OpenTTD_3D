"""Review sheet for the ground textures: each inventory texture identity's classic sprites beside
its new layers, each layer tiled 2x2 so seams and repetition show.

  python tools/3d_assets/preview_textures.py   -> assets/3d/previews/ground_textures.png

Needs Pillow (as build_references.py does) and the 8.1 reference images.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parents[2] / 'OpenTTD-15.3' / 'OpenTTD-15.3' / 'assets' / '3d'
# Inventory identity -> (reference climate, texture layers)
ROWS = [
	('texture_bare', 'temperate', ['grass_0']),
	('texture_grass', 'temperate', ['grass_1', 'grass_2', 'grass_3']),
	('texture_rough', 'temperate', ['rough']),
	('texture_rocks', 'temperate', ['rocks']),
	('texture_fields', 'temperate', [f'field_{k}' for k in range(9)]),
	('texture_snow_desert', 'arctic', [f'snow_{d}' for d in range(4)]),
	('texture_snow_desert', 'tropic', [f'desert_{d}' for d in range(4)]),
	('texture_water', 'temperate', ['water', 'beach']),
	('texture_concrete', 'temperate', ['concrete']),
]
TILE = 96  # Each 128px texture covers two tiles; shown 2x2 at 96px per repeat.


def main():
	entries = {e['key']: e for e in json.loads((ASSETS / 'inventory.json').read_text(encoding='utf-8'))['entries']}
	blocks = []
	for key, climate, layers in ROWS:
		reference = Image.open(ASSETS / entries[key]['reference'][climate]).convert('RGBA')
		scale = min(1.0, 900 / reference.width)
		reference = reference.resize((int(reference.width * scale), int(reference.height * scale)), Image.NEAREST)
		textures = []
		for name in layers:
			texture = Image.open(ASSETS / 'textures' / f'{name}.png').convert('RGB').resize((TILE, TILE), Image.LANCZOS)
			tiled = Image.new('RGB', (TILE * 2, TILE * 2))
			for x in range(2):
				for y in range(2):
					tiled.paste(texture, (x * TILE, y * TILE))
			textures.append((name, tiled))
		width = max(reference.width, len(textures) * (TILE * 2 + 8))
		block = Image.new('RGB', (width + 16, reference.height + TILE * 2 + 60), (32, 34, 38))
		draw = ImageDraw.Draw(block)
		draw.text((8, 4), f'{key} ({climate}) - classic sprites, then new texture layers', fill=(230, 230, 230))
		block.paste(reference, (8, 18), reference)
		for i, (name, tiled) in enumerate(textures):
			x = 8 + i * (TILE * 2 + 8)
			block.paste(tiled, (x, reference.height + 24))
			draw.text((x, reference.height + 28 + TILE * 2), name, fill=(230, 230, 230))
		blocks.append(block)
	sheet = Image.new('RGB', (max(b.width for b in blocks), sum(b.height for b in blocks)), (32, 34, 38))
	y = 0
	for block in blocks:
		sheet.paste(block, (0, y))
		y += block.height
	out = ASSETS / 'previews' / 'ground_textures.png'
	sheet.save(out)
	print(f'wrote {out}')


if __name__ == '__main__':
	main()
