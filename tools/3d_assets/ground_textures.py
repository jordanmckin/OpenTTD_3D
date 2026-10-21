"""Generate the Phase 8 ground textures inside Blender (run by art.py textures).

  blender -b --factory-startup -P ground_textures.py -- <textures dir> [--force] [layer ...]

Every layer is a seamless 128x128 sRGB image covering two tiles (32 world units), built from
periodic value noise so it tiles exactly. The recipe for each layer is the TABLE below; the
order of TABLE is the order of Ground3D::Layer in src/video/ground3d.h.

Existing PNGs are kept (they may have been painted by hand in Blender) unless --force or the
layer is named. ground_textures.blend is rebuilt every run: one plane per layer, textured
with its PNG, laid out for review beside the classic sprite colours.
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np

SIZE = 128
BRIGHTNESS = 1.08  # The 3D light on flat ground is ~0.91; keep the classic tone after lighting.


def rgb(hex_colour):
	return np.array([int(hex_colour[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def noise(period, seed):
	"""Periodic value noise in [0, 1] with `period` lattice cells across the texture."""
	rng = np.random.default_rng(seed)
	lattice = rng.random((period, period), dtype=np.float32)
	t = np.arange(SIZE, dtype=np.float32) * period / SIZE
	i0 = t.astype(np.int32) % period
	i1 = (i0 + 1) % period
	f = t - np.floor(t)
	f = f * f * (3 - 2 * f)
	a = lattice[np.ix_(i0, i0)] * (1 - f)[None, :] + lattice[np.ix_(i0, i1)] * f[None, :]
	b = lattice[np.ix_(i1, i0)] * (1 - f)[None, :] + lattice[np.ix_(i1, i1)] * f[None, :]
	return a * (1 - f)[:, None] + b * f[:, None]


def fbm(seed, periods=(4, 8, 16, 32), gain=0.5):
	total, weight, amplitude = np.zeros((SIZE, SIZE), np.float32), 0.0, 1.0
	for n, period in enumerate(periods):
		total += noise(period, seed * 31 + n) * amplitude
		weight += amplitude
		amplitude *= gain
	return total / weight


def speckle(seed):
	return np.random.default_rng(seed).random((SIZE, SIZE), dtype=np.float32)


def mix(a, b, t):
	t = np.clip(np.asarray(t, np.float32), 0, 1)[..., None]
	return a * (1 - t) + b * t


def mask(field, coverage, softness=0.06):
	"""Threshold a [0,1] field so roughly `coverage` of it is set, with a soft edge."""
	if coverage <= 0:
		return np.zeros_like(field)
	if coverage >= 1:
		return np.ones_like(field)
	threshold = np.quantile(field, 1 - coverage)
	return np.clip((field - threshold) / softness + 0.5, 0, 1)


def grainy(colour, seed, amount=0.22):
	return colour * (1 - amount / 2 + amount * speckle(seed))[..., None]


def grass(density, seed=1):
	coverage = [0.12, 0.45, 0.78, 1.0][density]
	base = grainy(np.broadcast_to(rgb('3a5c1c'), (SIZE, SIZE, 3)), seed, 0.35)
	base = mix(base, base * 0.88, mask(fbm(seed + 5, (8, 16, 32)), 0.35, 0.15))
	dirt = grainy(np.broadcast_to(rgb('523618'), (SIZE, SIZE, 3)), seed + 1, 0.3)
	return mix(dirt, base, mask(fbm(seed + 2, (8, 16, 64)) * 0.7 + speckle(seed + 3) * 0.3, coverage, 0.1))


def rough(seed=11):
	out = grass(3, seed) * 0.82
	tufts = mask(fbm(seed + 1, (16, 32, 64)), 0.3, 0.08)
	out = mix(out, grainy(np.broadcast_to(rgb('1c3a0e'), (SIZE, SIZE, 3)), seed + 2, 0.3), tufts)
	return mix(out, rgb('4a3a1a'), mask(fbm(seed + 3, (16, 32)), 0.07, 0.05))


def rocks(seed=21):
	out = grass(3, seed)
	blobs = fbm(seed + 1, (8, 16, 32))
	stone = grainy(np.broadcast_to(rgb('8a8a84'), (SIZE, SIZE, 3)), seed + 2, 0.25)
	shade = np.clip((blobs - np.quantile(blobs, 0.84)) * 12, 0, 1)
	stone = stone * (0.7 + 0.3 * shade)[..., None]
	return mix(out, stone, mask(blobs, 0.16, 0.03))


FIELD_COLOURS = [
	# (soil, crop, crop coverage on ridges)
	('52321e', '52321e', 0.0),   # 0 bare, freshly ploughed
	('543420', '3e5a1c', 0.25),  # 1 sprouting
	('4a3420', '34561a', 0.65),  # 2 green rows
	('3e3a1c', '385c1a', 0.95),  # 3 full green
	('48461e', '56562a', 0.95),  # 4 ripening olive
	('4e4630', '645a36', 0.95),  # 5 ripening
	('5a4a30', '7c6a44', 0.95),  # 6 ripe, tan
	('5a4228', '76603e', 0.75),  # 7 harvest, tan with furrows
	('5a4630', '6e5a3a', 0.85),  # 8 stubble with haypacks
]


def field(kind, seed=31):
	soil_hex, crop_hex, coverage = FIELD_COLOURS[kind]
	y = np.arange(SIZE, dtype=np.float32)[:, None] * np.ones((1, SIZE), np.float32)
	ridge = 0.5 + 0.5 * np.sin(2 * math.pi * 16 * y / SIZE + (noise(4, seed + kind) - 0.5) * 1.2)
	soil = grainy(np.broadcast_to(rgb(soil_hex), (SIZE, SIZE, 3)), seed + kind, 0.25) * (0.75 + 0.35 * ridge)[..., None]
	crop = grainy(np.broadcast_to(rgb(crop_hex), (SIZE, SIZE, 3)), seed + kind + 50, 0.35)
	growth = ridge * 0.75 + speckle(seed + kind + 60) * 0.25
	out = mix(soil, crop, mask(growth, coverage, 0.12))
	if kind == 8:
		bales = np.zeros((SIZE, SIZE), np.float32)
		yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
		rng = np.random.default_rng(seed + 99)
		for _ in range(10):
			cx, cy = rng.random(2) * SIZE
			dx = (xx - cx + SIZE / 2) % SIZE - SIZE / 2
			dy = (yy - cy + SIZE / 2) % SIZE - SIZE / 2
			bales = np.maximum(bales, np.clip(1.4 - np.hypot(dx, dy) / 3.2, 0, 1))
		hay = grainy(np.broadcast_to(rgb('b49c5a'), (SIZE, SIZE, 3)), seed + 98, 0.25)
		out = mix(out, hay * (0.6 + 0.4 * bales)[..., None], bales > 0.15)
	return out


def snow(density, seed=41):
	coverage = [0.0, 0.35, 0.82, 1.0][density]
	ground = grainy(np.broadcast_to(rgb('5e602c'), (SIZE, SIZE, 3)), seed, 0.35)
	white = grainy(np.broadcast_to(rgb('bcd8e2'), (SIZE, SIZE, 3)), seed + 1, 0.12)
	white = white * (0.9 + 0.1 * fbm(seed + 2, (8, 16)))[..., None]
	return mix(ground, white, mask(fbm(seed + 3, (4, 8, 16, 32)), coverage, 0.04))


def desert(density, seed=51):
	sand = grainy(np.broadcast_to(rgb('a67c3c'), (SIZE, SIZE, 3)), seed, 0.25)
	sand = sand * (0.92 + 0.12 * fbm(seed + 1, (4, 8)))[..., None]
	if density >= 2:
		return sand
	xs = np.arange(SIZE, dtype=np.float32)[None, :] * np.ones((SIZE, 1), np.float32)
	streaks = noise(16, seed + 2) * 0.4 + (0.5 + 0.5 * np.sin(2 * math.pi * 12 * xs / SIZE)) * 0.3 + speckle(seed + 3) * 0.3
	green = grainy(np.broadcast_to(rgb('3e6230'), (SIZE, SIZE, 3)), seed + 4, 0.3)
	return mix(sand, green, mask(streaks, 0.22, 0.08))


def beach(seed=61):
	sand = grainy(np.broadcast_to(rgb('b29e6c'), (SIZE, SIZE, 3)), seed, 0.18)
	return sand * (0.9 + 0.15 * fbm(seed + 1, (4, 8, 16)))[..., None]


def water(seed=71):
	waves = fbm(seed, (4, 8, 16))
	out = mix(rgb('22446e'), rgb('34608e'), waves)
	return grainy(out, seed + 1, 0.06)


def concrete(seed=81):
	out = grainy(np.broadcast_to(rgb('707070'), (SIZE, SIZE, 3)), seed, 0.12)
	out = out * (0.94 + 0.1 * fbm(seed + 1, (8, 16)))[..., None]
	yy, xx = np.mgrid[0:SIZE, 0:SIZE]
	joints = (xx % 32 == 0) | (yy % 32 == 0)
	return np.where(joints[..., None], out * 0.78, out)


# Order must match Ground3D::Layer.
TABLE = (
	[(f'grass_{d}', lambda d=d: grass(d)) for d in range(4)]
	+ [('rough', rough), ('rocks', rocks)]
	+ [(f'field_{k}', lambda k=k: field(k)) for k in range(9)]
	+ [(f'snow_{d}', lambda d=d: snow(d)) for d in range(4)]
	+ [(f'desert_{d}', lambda d=d: desert(d)) for d in range(4)]
	+ [('beach', beach), ('water', water), ('concrete', concrete)]
)


def save_png(path, pixels):
	pixels = np.clip(pixels * BRIGHTNESS, 0, 255) / 255.0
	image = bpy.data.images.new(path.stem, SIZE, SIZE, alpha=False)
	rgba = np.ones((SIZE, SIZE, 4), np.float32)
	rgba[..., :3] = pixels[::-1]  # Blender stores rows bottom-up; row 0 of the array is the image top.
	image.pixels.foreach_set(rgba.ravel())
	image.filepath_raw = str(path)
	image.file_format = 'PNG'
	image.save()
	bpy.data.images.remove(image)


def review_scene(directory):
	"""One plane per layer, 2x2 repeats, so seams and repetition are visible."""
	bpy.ops.wm.read_factory_settings(use_empty=True)
	scene = bpy.context.scene
	columns = 6
	for index, (name, _) in enumerate(TABLE):
		mesh = bpy.data.meshes.new(name)
		size = 64  # Two repeats of the 32-unit texture in each direction.
		mesh.from_pydata([(0, 0, 0), (size, 0, 0), (size, size, 0), (0, size, 0)], [], [(0, 1, 2, 3)])
		uv = mesh.uv_layers.new()
		for loop, (u, v) in zip(uv.data, [(0, 0), (2, 0), (2, 2), (0, 2)]):
			loop.uv = (u, v)
		material = bpy.data.materials.new(name)
		material.use_nodes = True
		nodes = material.node_tree.nodes
		texture = nodes.new('ShaderNodeTexImage')
		texture.image = bpy.data.images.load(str(directory / f'{name}.png'))
		texture.interpolation = 'Closest'
		material.node_tree.links.new(texture.outputs['Color'], nodes['Principled BSDF'].inputs['Base Color'])
		mesh.materials.append(material)
		obj = bpy.data.objects.new(name, mesh)
		obj.location = ((index % columns) * 72, -(index // columns) * 72, 0)
		scene.collection.objects.link(obj)
	text = bpy.data.texts.new('README')
	text.write('Ground textures for the 3D renderer. Paint the images in Texture Paint and save them (Image > Save);\n'
		'run `python tools/3d_assets/art.py textures` to embed them. Regenerating a layer from its recipe\n'
		'needs `art.py textures --force <layer>` and overwrites hand edits.\n')
	bpy.ops.wm.save_as_mainfile(filepath=str(directory / 'ground_textures.blend'), relative_remap=True)


def main():
	args = sys.argv[sys.argv.index('--') + 1:]
	directory = Path(args[0])
	force = '--force' in args
	named = {a for a in args[1:] if not a.startswith('--')}
	directory.mkdir(parents=True, exist_ok=True)
	unknown = named - {name for name, _ in TABLE}
	if unknown:
		sys.exit(f'unknown layers: {", ".join(sorted(unknown))}')
	for name, recipe in TABLE:
		path = directory / f'{name}.png'
		if path.exists() and not force and name not in named:
			continue
		save_png(path, recipe())
		print(f'created {path}')
	review_scene(directory)
	print(f'created {directory / "ground_textures.blend"}')


main()
