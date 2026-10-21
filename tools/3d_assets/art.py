"""Phase 8 art pipeline driver.

  python tools/3d_assets/art.py new <key>      create assets/3d/blender/<category>/<key>.blend from the template
  python tools/3d_assets/art.py build <key>... export state collections + previews, then convert
  python tools/3d_assets/art.py build --all    export every .blend, then convert
  python tools/3d_assets/art.py convert        convert existing exports into src/video/asset3d_art.h
  python tools/3d_assets/art.py status         coverage by category and status
  python tools/3d_assets/art.py textures [--force] [layer...]
                                               generate missing ground textures in Blender, then embed them

Blender is located through $BLENDER, D:/Blender/blender.exe, or PATH. See assets/3d/blender/CONVENTIONS.md.
"""
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ASSETS = TOOLS.parents[1] / 'OpenTTD-15.3' / 'OpenTTD-15.3' / 'assets' / '3d'
INVENTORY = ASSETS / 'inventory.json'
BLENDS = ASSETS / 'blender'


def blender():
	for candidate in (os.environ.get('BLENDER'), 'D:/Blender/blender.exe', shutil.which('blender')):
		if candidate and Path(candidate).exists():
			return candidate
	sys.exit('Blender not found; set BLENDER to blender.exe')


def inventory():
	return {e['key']: e for e in json.loads(INVENTORY.read_text(encoding='utf-8'))['entries']}


def blend_path(entry):
	return BLENDS / entry['category'] / f'{entry["key"]}.blend'


def run(args):
	print('>', ' '.join(str(a) for a in args))
	result = subprocess.run([str(a) for a in args], capture_output=True, text=True, encoding='utf-8', errors='replace')
	for line in result.stdout.splitlines() + result.stderr.splitlines():
		if any(w in line for w in ('created', 'exported', 'preview', 'Error', 'error', 'Traceback', 'File "')):
			print('  ' + line)
	if result.returncode != 0:
		sys.exit(f'Blender exited with {result.returncode}')


def cmd_new(keys):
	entries = inventory()
	for key in keys:
		entry = entries.get(key) or sys.exit(f'unknown inventory key {key}')
		path = blend_path(entry)
		if path.exists():
			sys.exit(f'{path} already exists; open it instead')
		path.parent.mkdir(parents=True, exist_ok=True)
		states = entry.get('states') or ['default']
		footprint = {'vehicle': 'vehicle', 'tree': 'tree'}.get(entry['category'], entry.get('footprint', '1x1'))
		if entry['category'] == 'industry':
			layout = entry['layouts'][0]
			footprint = f'{max(t[0] for t in layout) + 1}x{max(t[1] for t in layout) + 1}'
		ref = next(iter(entry.get('reference', {}).values()), None)
		args = [blender(), '-b', '--factory-startup', '-P', TOOLS / 'new_blend.py', '--', path, ASSETS / 'blender' / 'palette.json',
			','.join(states), footprint]
		if ref:
			args.append(ASSETS / ref)
		run(args)


def cmd_build(keys):
	entries = inventory()
	if keys == ['--all']:
		keys = [p.stem for p in BLENDS.glob('*/*.blend')]
	for key in keys:
		entry = entries.get(key) or sys.exit(f'unknown inventory key {key}')
		path = blend_path(entry)
		if not path.exists():
			sys.exit(f'{path} does not exist; run: art.py new {key}')
		run([blender(), '-b', path, '-P', TOOLS / 'export_blend.py', '--', key, ASSETS / 'export' / key, ASSETS / 'previews'])
	cmd_convert()


def cmd_convert():
	code = subprocess.call([sys.executable, str(TOOLS / 'convert_gltf.py')])
	if code:
		sys.exit(code)


def cmd_textures(args):
	run([blender(), '-b', '--factory-startup', '-P', TOOLS / 'ground_textures.py', '--', ASSETS / 'textures', *args])
	code = subprocess.call([sys.executable, str(TOOLS / 'convert_textures.py')])
	if code:
		sys.exit(code)


def cmd_status():
	entries = inventory().values()
	by = Counter((e['category'], e['status']) for e in entries)
	for cat in sorted({c for c, _ in by}):
		parts = ', '.join(f'{s} {n}' for (c, s), n in sorted(by.items()) if c == cat)
		print(f'{cat:15} {parts}')
	own = [e for e in entries if e['status'] != 'shared']
	done = [e for e in own if e['status'] in ('approved', 'in_game')]
	print(f'{len(done)}/{len(own)} own models approved or in game')


def main():
	if len(sys.argv) < 2:
		sys.exit(__doc__)
	cmd, rest = sys.argv[1], sys.argv[2:]
	if cmd == 'new':
		cmd_new(rest)
	elif cmd == 'build':
		cmd_build(rest)
	elif cmd == 'convert':
		cmd_convert()
	elif cmd == 'status':
		cmd_status()
	elif cmd == 'textures':
		cmd_textures(rest)
	else:
		sys.exit(__doc__)


if __name__ == '__main__':
	main()
