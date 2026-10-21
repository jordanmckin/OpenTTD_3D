"""Create a Phase 8 .blend for one inventory identity (run by art.py inside Blender).

blender -b --factory-startup -P new_blend.py -- <blend> <palette.json> <states,comma,separated> <footprint WxH|vehicle|tree> [reference.png]
"""
import json
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_common as bc  # noqa: E402

args = sys.argv[sys.argv.index('--') + 1:]
blend_path, palette_path, states, footprint = args[0], args[1], args[2].split(','), args[3]
reference = args[4] if len(args) > 4 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = 'model'
scene.unit_settings.system = 'NONE'

# Palette materials, kept even when unused so every .blend offers the same colours.
for name, rgb in json.load(open(palette_path, encoding='utf-8'))['colours'].items():
	mat = bpy.data.materials.new(name)
	linear = [bc.srgb_to_linear(c) for c in rgb] + [1.0]
	mat.diffuse_color = linear
	mat.use_nodes = True
	bsdf = mat.node_tree.nodes.get('Principled BSDF')
	if bsdf:
		bsdf.inputs['Base Color'].default_value = linear
		bsdf.inputs['Roughness'].default_value = 1.0
	mat.use_fake_user = True

for state in states:
	scene.collection.children.link(bpy.data.collections.new(state))

# Reference collection: never exported.
ref = bpy.data.collections.new('reference')
scene.collection.children.link(ref)
if footprint not in ('vehicle', 'tree'):
	w, h = (int(v) for v in footprint.split('x'))
	mesh = bpy.data.meshes.new('footprint')
	mesh.from_pydata([(0, 0, 0), (16 * w, 0, 0), (16 * w, 16 * h, 0), (0, 16 * h, 0)], [(0, 1), (1, 2), (2, 3), (3, 0)], [])
	ref.objects.link(bpy.data.objects.new('footprint', mesh))
	for tx in range(w):
		for ty in range(h):
			grid = bpy.data.objects.new(f'tile_{tx}_{ty}', None)
			grid.empty_display_type = 'PLAIN_AXES'
			grid.empty_display_size = 1
			grid.location = (16 * tx, 16 * ty, 0)
			ref.objects.link(grid)
else:
	mesh = bpy.data.meshes.new('footprint')
	mesh.from_pydata([(-4, -2, 0), (4, -2, 0), (4, 2, 0), (-4, 2, 0)] if footprint == 'vehicle' else [(-2, -2, 0), (2, -2, 0), (2, 2, 0), (-2, 2, 0)],
		[(0, 1), (1, 2), (2, 3), (3, 0)], [])
	ref.objects.link(bpy.data.objects.new('footprint', mesh))
if reference and os.path.exists(reference):
	img = bpy.data.images.load(reference)
	img.pack()
	empty = bpy.data.objects.new('reference_image', None)
	empty.empty_display_type = 'IMAGE'
	empty.data = img
	empty.empty_display_size = 40
	empty.rotation_euler = bc.GAME_CAMERA_ROTATION
	empty.location = (60, -60, 20)
	ref.objects.link(empty)

# game_view scene: the state collections squashed to the in-game projection, seen through the game camera.
view = bpy.data.scenes.new('game_view')
view.unit_settings.system = 'NONE'
bc.setup_workbench(view)
for i, state in enumerate(states):
	bc.instance(view, bpy.data.collections[state], f'view_{state}', (-40 * i, 40 * i, 0))
cam = bc.game_camera(view)
cam.location = (300, 300, 300 * 0.577 * 1.414)
if reference and os.path.exists(reference):
	cam.data.show_background_images = True
	bg = cam.data.background_images.new()
	bg.image = bpy.data.images[os.path.basename(reference)]
	bg.alpha = 0.35
	bg.display_depth = 'BACK'

bc.setup_workbench(scene)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend_path), compress=True)
print(f'created {blend_path}')
