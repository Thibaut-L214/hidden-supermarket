"""Panorama of the store interior, the image-based light of the store zone (docs/DA.md §04).

Usage (headless):
  Blender -b blender/store.blend -P blender/scripts/bake_env.py -- <out.hdr>

An equirectangular render from the middle of the central aisle at eye height, lit like the
lightmap bake (ceiling panels, fridge strips, daylight at the entrance). The result is a small
Radiance HDR: three.js prefilters it with PMREM, so only the broad distribution of light and
colour matters. The panorama centre looks along +X (three.js equirect convention).
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import bpy  # noqa: E402
from lightmap import PROFILES, _daylight_spill, _setup_cycles  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
if not argv:
    raise SystemExit("usage: bake_env.py -- <out.hdr>")
out = os.path.abspath(argv[0])
os.makedirs(os.path.dirname(out), exist_ok=True)

scene = bpy.context.scene
_setup_cycles(64)
scene.cycles.use_denoising = True
if scene.world is None:
    scene.world = bpy.data.worlds.new("World")
tree = scene.world.node_tree
background = tree.nodes.get("Background")
if background is None:
    tree.nodes.clear()
    background = tree.nodes.new("ShaderNodeBackground")
    tree.links.new(background.outputs["Background"], tree.nodes.new("ShaderNodeOutputWorld").inputs["Surface"])
background.inputs["Color"].default_value = (0.55, 0.6, 0.65, 1.0)
background.inputs["Strength"].default_value = 0.05
_daylight_spill()

# Glass would be opaque in Blender and wall off the entrance.
moving = PROFILES["store"].moving
for obj in scene.objects:
    if obj.type == "MESH" and moving.search(obj.name):
        obj.hide_render = True

data = bpy.data.cameras.new("ENV")
data.type = "PANO"
data.panorama_type = "EQUIRECTANGULAR"
camera = bpy.data.objects.new("ENV", data)
scene.collection.objects.link(camera)
camera.location = (0.0, -1.0, 1.6)
camera.rotation_euler = (math.pi / 2, 0.0, -math.pi / 2)  # forward = +X
scene.camera = camera

scene.render.resolution_x, scene.render.resolution_y = 512, 256
scene.render.resolution_percentage = 100
settings = scene.render.image_settings
settings.file_format = "HDR"
settings.color_management = "OVERRIDE"
settings.view_settings.view_transform = "Raw"
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print(f"environment written: {out}")
