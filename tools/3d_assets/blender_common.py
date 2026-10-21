"""Helpers shared by the Blender-side Phase 8 scripts (run inside Blender only)."""
import math

import bpy
from mathutils import Vector

# The game draws with the classic TTD projection: screen x = 2(y - x), screen y = (x + y) - z.
# An orthographic camera at 30 degrees elevation matches it exactly once Z is scaled by this factor.
GAME_Z_SCALE = math.sqrt(2) / 2 / 2 / math.cos(math.radians(30))
GAME_CAMERA_ROTATION = (math.radians(60), 0.0, math.radians(135))
SKIP_COLLECTIONS = {'reference'}


def srgb_to_linear(c):
	return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def state_collections(scene):
	"""Top-level collections that hold exportable states."""
	return [c for c in scene.collection.children if c.name not in SKIP_COLLECTIONS and not c.name.startswith('_')]


def game_camera(scene, name='game_camera'):
	data = bpy.data.cameras.new(name)
	data.type = 'ORTHO'
	data.ortho_scale = 48
	data.clip_start = 0.1
	data.clip_end = 2000
	cam = bpy.data.objects.new(name, data)
	cam.rotation_euler = GAME_CAMERA_ROTATION
	scene.collection.objects.link(cam)
	scene.camera = cam
	return cam


def setup_workbench(scene, resolution=(512, 512)):
	scene.render.engine = 'BLENDER_WORKBENCH'
	shading = scene.display.shading
	shading.light = 'STUDIO'
	shading.color_type = 'MATERIAL'
	shading.show_object_outline = False
	scene.render.film_transparent = True
	scene.render.resolution_x, scene.render.resolution_y = resolution
	scene.render.resolution_percentage = 100
	scene.render.image_settings.file_format = 'PNG'
	scene.render.image_settings.color_mode = 'RGBA'


def instance(scene, collection, name, offset=(0, 0, 0)):
	"""Collection instance squashed to the game projection."""
	empty = bpy.data.objects.new(name, None)
	empty.instance_type = 'COLLECTION'
	empty.instance_collection = collection
	empty.scale = (1, 1, GAME_Z_SCALE)
	empty.location = offset
	scene.collection.objects.link(empty)
	return empty


def collection_bounds(collection):
	points = []
	for obj in collection.all_objects:
		if obj.type == 'MESH':
			points += [obj.matrix_world @ Vector(c) for c in obj.bound_box]
	return points


def frame_camera(scene, cam, points, margin=1.15):
	"""Fit an orthographic camera to points (already in the squashed space), using its rotation directly."""
	rot = cam.rotation_euler.to_quaternion()
	right, up, back = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0)), rot @ Vector((0, 0, 1))
	us = [p.dot(right) for p in points]
	vs = [p.dot(up) for p in points]
	ws = [p.dot(back) for p in points]
	cu, cv = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
	cam.location = right * cu + up * cv + back * (max(ws) + 500)
	aspect = scene.render.resolution_x / scene.render.resolution_y
	cam.data.ortho_scale = max(max(us) - min(us), (max(vs) - min(vs)) * aspect, 4) * margin
