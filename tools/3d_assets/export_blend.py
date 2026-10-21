"""Export each state collection of a Phase 8 .blend to glTF and render previews (run by art.py inside Blender).

blender -b <file.blend> -P export_blend.py -- <key> <export_dir> <preview_dir>
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_common as bc  # noqa: E402

args = sys.argv[sys.argv.index('--') + 1:]
key, export_dir, preview_dir = args[0], args[1], args[2]
scene = bpy.context.scene
if scene.name != 'model':
	sys.exit(f'active scene is {scene.name!r}; save the .blend with the "model" scene active')
view_layer = bpy.context.view_layer
os.makedirs(export_dir, exist_ok=True)
os.makedirs(preview_dir, exist_ok=True)

# Old exports of states that no longer exist must not linger.
for f in os.listdir(export_dir):
	if f.endswith('.glb'):
		os.remove(os.path.join(export_dir, f))


def layer_collection(root, name):
	if root.collection.name == name:
		return root
	for child in root.children:
		found = layer_collection(child, name)
		if found:
			return found
	return None


exported = []
for col in bc.state_collections(scene):
	meshes = [o for o in col.all_objects if o.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT')]
	if not meshes:
		continue
	lc = layer_collection(view_layer.layer_collection, col.name)
	lc.exclude = False
	lc.hide_viewport = False
	for o in scene.objects:
		o.select_set(False)
	for o in meshes:
		o.hide_set(False)
		o.hide_viewport = False
		o.select_set(True)
	path = os.path.join(export_dir, f'{col.name}.glb')
	bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=False, export_apply=True,
		export_materials='EXPORT', export_animations=False, export_cameras=False, export_lights=False, export_extras=False)
	exported.append(col)
	print(f'exported {path} ({len(meshes)} objects)')

# Previews: each state alone, squashed to the game projection and framed by the game camera.
preview = bpy.data.scenes.new('_preview')
bc.setup_workbench(preview)
cam = bc.game_camera(preview)
for col in exported:
	for o in list(preview.collection.objects):
		if o.type == 'EMPTY':
			bpy.data.objects.remove(o)
	inst = bc.instance(preview, col, f'preview_{col.name}')
	bpy.context.view_layer.update()
	points = [p * 1 for p in bc.collection_bounds(col)]
	for p in points:
		p.z *= bc.GAME_Z_SCALE
	bc.frame_camera(preview, cam, points)
	preview.render.filepath = os.path.join(preview_dir, f'{key}_{col.name}.png')
	bpy.ops.render.render(write_still=True, scene=preview.name)
	print(f'preview {preview.render.filepath}')
bpy.data.scenes.remove(preview)
