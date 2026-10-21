"""Cut grfcodec sprite sheets into one PNG per sprite, using the .nfo rectangles.

Usage: python tools/3d_assets/slice_sprites.py [sprites_pulled] [out_dir]

Writes <out>/<grf>/<number>.png for the normal zoom and <number>_<zoom>.png for
extra zoom levels (zi2, zi4), plus <out>/<grf>/index.csv with offsets.
Reference material only; never shipped with the game.
"""
import csv
import re
import sys
from pathlib import Path

from PIL import Image

LINE = re.compile(r'^\s*(\d+|\|)\s+sprites/(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(-?\d+)\s+(\S+)')


def slice_grf(folder: Path, out: Path):
	nfo = next(folder.glob('*.nfo'))
	out.mkdir(parents=True, exist_ok=True)
	sheets = {}
	number = None
	rows = []
	for line in nfo.read_text(encoding='latin-1').splitlines():
		m = LINE.match(line)
		if not m:
			continue
		num, sheet, depth, x, y, w, h, xrel, yrel, zoom = m.groups()
		if num != '|':
			number = int(num)
		if sheet not in sheets:
			sheets[sheet] = Image.open(folder / sheet)
		x, y, w, h = int(x), int(y), int(w), int(h)
		sprite = sheets[sheet].crop((x, y, x + w, y + h))
		suffix = '' if zoom == 'normal' else '_' + zoom
		name = f'{number}{suffix}.png'
		sprite.save(out / name, transparency=0) if sprite.mode == 'P' else sprite.save(out / name)
		rows.append((number, zoom, name, w, h, xrel, yrel, depth))
	with open(out / 'index.csv', 'w', newline='') as f:
		writer = csv.writer(f)
		writer.writerow(('sprite', 'zoom', 'file', 'width', 'height', 'xrel', 'yrel', 'depth'))
		writer.writerows(rows)
	return len(rows)


def main():
	src = Path(sys.argv[1] if len(sys.argv) > 1 else 'sprites_pulled')
	dst = Path(sys.argv[2] if len(sys.argv) > 2 else src / 'sliced')
	for folder in sorted(p for p in src.iterdir() if p.is_dir() and any(p.glob('*.nfo'))):
		print(f'{folder.name}: {slice_grf(folder, dst / folder.name)} images')


if __name__ == '__main__':
	main()
