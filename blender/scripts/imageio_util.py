"""Image output shared by the texture generator and the lightmap bake (bpy + numpy)."""

from __future__ import annotations

import bpy
import numpy as np


def to_u8(a: np.ndarray) -> np.ndarray:
    return np.clip(np.round(a * 255), 0, 255).astype(np.uint8)


def write_jpeg(path: str, pixels: np.ndarray, quality: int = 88) -> None:
    """JPEG through Blender's image writer, Non-Color so the bytes are written untouched.

    `pixels` holds uint8 rows from top to bottom: (h, w, 3) for colour, (h, w) for greyscale.
    """
    grey = pixels.ndim == 2
    h, w = pixels.shape[:2]
    rgb = np.repeat(pixels[..., None], 3, axis=2) if grey else pixels
    image = bpy.data.images.new("tmp", w, h, alpha=False)
    image.colorspace_settings.name = "Non-Color"
    flat = np.ones((h, w, 4), dtype=np.float32)
    flat[..., :3] = rgb[::-1].astype(np.float32) / 255.0  # Blender rows run bottom to top
    image.pixels.foreach_set(flat.ravel())
    scene = bpy.context.scene
    settings = scene.render.image_settings
    settings.file_format = "JPEG"
    settings.quality = quality
    settings.color_mode = "BW" if grey else "RGB"
    settings.color_management = "OVERRIDE"
    settings.view_settings.view_transform = "Standard"
    settings.display_settings.display_device = "sRGB"
    image.save_render(path, scene=scene)
    bpy.data.images.remove(image)
