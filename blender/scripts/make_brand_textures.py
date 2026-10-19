"""Printed faces of the forecourt: the volunteers' leaflets and the banner two of them hold.

Usage (headless):
  Blender -b --factory-startup -P blender/scripts/make_brand_textures.py

Writes blender/textures/brand/brand_leaflet.jpg and brand_banner.jpg (bound to the materials
M_LEAFLET_L214 and M_BANNER_L214 by scripts/lib/surfaces.mjs, see surfaces.json).

The logo comes from blender/textures/brand/l214_logo.png (RGBA, transparent background) when that
file exists: drop the official artwork there once the association has validated its use
(docs/GDD.md §12, docs/DECISIONS.md). Until then a plain placeholder wordmark is drawn, in
seven-segment strokes, so that nothing here can pass for the real logo. Only the logo area changes
between the two; the layout is the same. The banner also carries the line BANNER_TEXT, drawn with
Blender's own font. No figure is printed.
"""

from __future__ import annotations

import math
import os
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from imageio_util import to_u8, write_jpeg  # noqa: E402

BRAND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "textures", "brand")
LOGO = os.path.join(BRAND, "l214_logo.png")

GREEN = np.array([0x3F, 0x5A, 0x3C]) / 255.0
CREAM = np.array([0xF3, 0xEF, 0xE6]) / 255.0
PAPER = np.array([0xFB, 0xFA, 0xF6]) / 255.0
INK = np.array([0x1F, 0x24, 0x20]) / 255.0
LINE = np.array([0xC9, 0xC6, 0xBC]) / 255.0

# The line written under the logo on the banner (supplied by the editorial team).
BANNER_TEXT = "L214 - Sauvetage du Siècle"

# Seven segments: a top, b upper right, c lower right, d bottom, e lower left, f upper left, g middle.
SEGMENTS = {"L": "def", "2": "abged", "1": "bc", "4": "fgbc"}


def placeholder_logo(height: int) -> np.ndarray:
    """RGBA wordmark `L214`: ink strokes on transparent, `height` pixels tall."""
    t = max(2, height // 7)  # stroke
    w = int(height * 0.5)
    gap = height // 6
    width = 4 * w + 3 * gap
    mask = np.zeros((height, width), dtype=bool)
    for i, ch in enumerate("L214"):
        x0 = i * (w + gap)
        boxes = {
            "a": (x0, 0, x0 + w, t),
            "g": (x0, height // 2 - t // 2, x0 + w, height // 2 + t // 2 + 1),
            "d": (x0, height - t, x0 + w, height),
            "f": (x0, 0, x0 + t, height // 2 + t // 2),
            "b": (x0 + w - t, 0, x0 + w, height // 2 + t // 2),
            "e": (x0, height // 2 - t // 2, x0 + t, height),
            "c": (x0 + w - t, height // 2 - t // 2, x0 + w, height),
        }
        for seg in SEGMENTS[ch]:
            xa, ya, xb, yb = boxes[seg]
            mask[ya:yb, xa:xb] = True
    out = np.zeros((height, width, 4))
    out[..., :3] = INK
    out[..., 3] = mask
    return out


def load_logo(height: int) -> np.ndarray:
    """The official logo scaled to `height` pixels (RGBA, top row first), else the placeholder."""
    if not os.path.exists(LOGO):
        return placeholder_logo(height)
    image = bpy.data.images.load(LOGO)
    ratio = image.size[0] / image.size[1]
    image.scale(max(1, round(height * ratio)), height)
    w, h = image.size
    pixels = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    return pixels.reshape(h, w, 4)[::-1].astype(np.float64)


def render_text(text: str, height_px: int, embolden: int = 2) -> np.ndarray:
    """Alpha mask (rows top first, values 0..1) of `text` in Blender's font, `height_px` tall.

    A flat white render of a text object on a transparent film; `embolden` thickens the strokes
    by that many pixels (the regular font is too light at banner scale; a curve bevel would do
    it but leaves artefacts on some glyphs)."""
    scene = bpy.context.scene
    for other in scene.objects:  # the factory scene's cube would hide part of the text
        other.hide_render = True
    curve = bpy.data.curves.new("TXT", "FONT")
    curve.body = text
    curve.size = 1.0
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    obj = bpy.data.objects.new("TXT", curve)
    scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = [min(c[i] for c in corners) for i in range(3)]
    hi = [max(c[i] for c in corners) for i in range(3)]
    width, height = hi[0] - lo[0], hi[1] - lo[1]
    ppu = height_px / height
    res = (int(math.ceil(width * ppu * 1.04)) + 4, int(math.ceil(height * ppu * 1.04)) + 4)

    camera_data = bpy.data.cameras.new("TXT")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = res[0] / ppu
    camera = bpy.data.objects.new("TXT", camera_data)
    camera.location = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 5.0)
    scene.collection.objects.link(camera)
    scene.camera = camera

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.display.render_aa = "8"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (1.0, 1.0, 1.0)
    scene.display.shading.show_object_outline = False
    scene.view_settings.view_transform = "Standard"
    path = os.path.join(tempfile.gettempdir(), "l214_banner_text.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

    image = bpy.data.images.load(path)
    w, h = image.size
    pixels = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    alpha = pixels.reshape(h, w, 4)[::-1, :, 3].astype(np.float64)
    for _ in range(embolden):  # grow the strokes by one pixel per pass
        grown = alpha.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            grown = np.maximum(grown, np.roll(alpha, (dy, dx), axis=(0, 1)))
        alpha = grown
    for datablock in (image,):
        bpy.data.images.remove(datablock)
    bpy.data.objects.remove(obj)
    bpy.data.objects.remove(camera)
    os.remove(path)
    return alpha


def paste_mask(canvas: np.ndarray, mask: np.ndarray, centre_x: int, top: int, colour) -> None:
    h, w = mask.shape
    x0 = centre_x - w // 2
    region = canvas[top : top + h, x0 : x0 + w]
    alpha = mask[..., None]
    region[:] = region * (1 - alpha) + np.asarray(colour) * alpha


def paste(canvas: np.ndarray, logo: np.ndarray, centre_x: int, top: int) -> None:
    h, w = logo.shape[:2]
    x0 = centre_x - w // 2
    region = canvas[top : top + h, x0 : x0 + w]
    alpha = logo[..., 3:4]
    region[:] = region * (1 - alpha) + logo[..., :3] * alpha


def leaflet(width: int = 420, height: int = 594) -> np.ndarray:
    canvas = np.tile(PAPER, (height, width, 1))
    canvas[: height // 7] = GREEN
    logo = load_logo(int(height * 0.14))
    paste(canvas, logo, width // 2, int(height * 0.3))
    # Greyed lines stand for text: nothing is written.
    for k in range(7):
        y = int(height * 0.58) + k * int(height * 0.045)
        end = int(width * (0.86 if k % 3 != 2 else 0.6))
        canvas[y : y + 5, int(width * 0.14) : end] = LINE
    return canvas


def banner(width: int = 1536, height: int = 448) -> np.ndarray:
    canvas = np.tile(GREEN, (height, width, 1))
    m = height // 10
    canvas[m : height - m, m : width - m] = CREAM
    logo = load_logo(int(height * 0.36))
    paste(canvas, logo, width // 2, int(height * 0.17))
    line = render_text(BANNER_TEXT, int(height * 0.15))
    paste_mask(canvas, line, width // 2, int(height * 0.62), INK)
    return canvas


def main() -> None:
    os.makedirs(BRAND, exist_ok=True)
    source = "official logo" if os.path.exists(LOGO) else "placeholder wordmark"
    write_jpeg(os.path.join(BRAND, "brand_leaflet.jpg"), to_u8(leaflet()), quality=90)
    write_jpeg(os.path.join(BRAND, "brand_banner.jpg"), to_u8(banner()), quality=90)
    print(f"brand textures written ({source})")


main()
