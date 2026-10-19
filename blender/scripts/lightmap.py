"""Baked interior lighting for the store (docs/DA.md §04: precomputed static lighting).

At export, on the in-memory copy only:
  1. every mesh gets a second UV layer, "Lightmap" (TEXCOORD_1 in the GLB). Coplanar, connected
     faces form one island; islands are packed into a single atlas at a uniform texel density.
     Objects that are not lit by the bake (goods, the doors that swing open, outdoors, glass)
     point at one of two reserved blocks of the atlas: full light, or the average aisle level;
  2. Cycles bakes direct + indirect diffuse lighting from the emissive ceiling panels, the
     fridge strips and a daylight spill at the entrance;
  3. the result is normalised and written as a greyscale JPEG.

scripts/lib/surfaces.mjs binds that image to the materials as glTF occlusionTexture on
TEXCOORD_1: three.js multiplies it into the indirect (hemisphere and environment) light, so
the baked soft shadows and light pools modulate the ambient light without any runtime code.
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass

import bmesh
import bpy
import numpy as np
from imageio_util import to_u8, write_jpeg

UV_NAME = "Lightmap"
MARGIN_PX = 4  # around each island, inside its packed rectangle
# Islands thinner or smaller than this (shelf edges, chamfers, tags) take the average level
# instead of a texel of their own: they would eat the atlas for no visible gain.
MIN_SIDE = 0.06
MIN_EXTENT = 0.15
RESERVED = 8  # side of each reserved block, bottom-left corner of the atlas
STRENGTH = 0.9  # softens the bake, like the vertex AO it replaces
NEVER = re.compile(r"(?!)")


@dataclass(frozen=True)
class Profile:
    """What is baked, how, and what the runtime light it modulates looks like."""

    atlas: int
    samples: int
    max_density: float  # texels per metre; the atlas usually allows less
    blur: float  # sigma in texels, against bake noise
    outdoors: re.Pattern  # not baked: full light (neutral block 1)
    aisle: re.Pattern  # not baked: average light (neutral block 2)
    moving: re.Pattern  # hidden while baking: parts that move at runtime, or glass
    floor: str  # the open floor object that sets the yardstick
    floor_level: float  # its median maps to this occlusion value
    aisle_level: float
    lighting: str  # "store": ceiling panels + daylight spill; "sky": uniform overcast sky only


PROFILES = {
    # Closed interior: lit by the emissive ceiling panels; the doors swing open at runtime.
    "store": Profile(
        atlas=2048,
        samples=256,
        max_density=40.0,
        blur=1.6,
        outdoors=re.compile(
            r"^(PARVIS_|STORE_FACADE|STORE_CANOPY|STORE_SIGN|STORE_SHOP_WINDOWS|VOLUNTEER_|STAND_)"
            r"|(_DOORS$|^STORE_ENTRANCE_DOOR_)"
        ),
        aisle=re.compile(r"^DOOR_EGGS_[LR]|_GOODS$"),
        moving=re.compile(r"^DOOR_EGGS_[LR]|_DOORS$|^STORE_ENTRANCE_DOOR_|^STORE_SHOP_WINDOWS$"),
        floor="STORE_FLOOR",
        floor_level=0.85,
        aisle_level=0.75,
        lighting="store",
    ),
    # Open air: the sun stays dynamic (shadow-mapped), so the bake only keeps what the sky and
    # the bounces reach, which is what modulates the hemisphere light at runtime. Terrain,
    # vegetation, roads and anything that moves (roof, vehicles, cargo) are not baked; the roof
    # is hidden while baking so the hall is lit once it has lifted.
    "terrace": Profile(
        atlas=4096,
        samples=96,
        max_density=20.0,
        blur=2.0,
        outdoors=re.compile(
            r"^(TERRAIN_|HILLS_|LAND_|ROAD_|POWER_LINE_|FENCE_|ROOF_|BUILDING_EGGS_FARM_2_ROOF"
            r"|TRUCK_|CARGO_|CRATES_|CARTONS_|HENCRATES_|HENS_|INTERIOR_)"
        ),
        aisle=NEVER,
        moving=re.compile(r"^(ROOF_|BUILDING_EGGS_FARM_2_ROOF|TRUCK_|CARGO_|CRATES_|CARTONS_|HENCRATES_)"),
        floor="TERRACE_FLOOR",
        floor_level=0.95,
        aisle_level=0.9,
        lighting="sky",
    ),
}


def isolation_key(name: str) -> str:
    """Group of parts baked together for occlusion: `CARGO_EGGS_FARM_03` → `CARGO_EGGS_FARM`,
    `DOOR_EGGS_L_GOODS` → `DOOR_EGGS_L` (a door, its goods and eggs; the other door apart)."""
    return re.sub(r"(_\d+|_BODY|_GOODS|_EGGS)+$", "", name) if not re.match(r"^DOOR_EGGS_[LR]", name) else name[:11]


def classify(obj: bpy.types.Object, profile: Profile) -> str:
    """'baked' | 'outdoors' (full light) | 'aisle' (average light)."""
    if profile.outdoors.search(obj.name):
        return "outdoors"
    if profile.aisle.search(obj.name):
        return "aisle"
    return "baked"


# --- UV layout ---------------------------------------------------------------------------------

def _islands(mesh: bpy.types.Mesh):
    """Connected coplanar face groups: yields lists of polygon indices."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    seen: set[int] = set()
    groups = []
    for face in bm.faces:
        if face.index in seen:
            continue
        seen.add(face.index)
        stack, group = [face], []
        while stack:
            current = stack.pop()
            group.append(current.index)
            for edge in current.edges:
                for other in edge.link_faces:
                    if other.index not in seen and current.normal.dot(other.normal) > 0.9995:
                        seen.add(other.index)
                        stack.append(other)
        groups.append(group)
    bm.free()
    return groups


def _pack(sizes, atlas: int):
    """Shelf packing; returns pixel origins or None when the atlas overflows. The reserved
    blocks occupy the first row's first 2 × RESERVED pixels."""
    order = sorted(range(len(sizes)), key=lambda i: -sizes[i][1])
    positions = [None] * len(sizes)
    x, y, row = 2 * RESERVED, 0, RESERVED
    for i in order:
        w, h = sizes[i]
        if x + w > atlas:
            x, y, row = 0, y + row, 0
        if y + h > atlas or w > atlas:
            return None
        positions[i] = (x, y)
        x += w
        row = max(row, h)
    return positions


def build_lightmap_uvs(objects, profile: Profile) -> dict:
    """Adds the Lightmap UV layer to every object in `objects`; returns the layout stats and
    the baked objects."""
    layout = []  # (object, loop ids, a coords, b coords, mean height)
    baked = []
    kinds: dict[str, str] = {}
    for obj in objects:
        mesh = obj.data
        if not mesh.polygons:
            continue
        kind = classify(obj, profile)
        layer = mesh.uv_layers.get(UV_NAME) or mesh.uv_layers.new(name=UV_NAME)
        mesh.uv_layers.active = layer
        kinds[obj.name] = kind
        if kind != "baked":
            continue
        baked.append(obj)
        verts = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("co", verts)
        verts = verts.reshape(-1, 3)
        loop_vertex = np.empty(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", loop_vertex)
        starts = np.empty(len(mesh.polygons), dtype=np.int32)
        totals = np.empty(len(mesh.polygons), dtype=np.int32)
        mesh.polygons.foreach_get("loop_start", starts)
        mesh.polygons.foreach_get("loop_total", totals)
        normals = np.empty(len(mesh.polygons) * 3)
        mesh.polygons.foreach_get("normal", normals)
        normals = normals.reshape(-1, 3)
        for group in _islands(mesh):
            loops = np.concatenate([np.arange(starts[p], starts[p] + totals[p]) for p in group])
            axis = int(np.argmax(np.abs(normals[group].mean(axis=0))))
            co = verts[loop_vertex[loops]]
            a = co[:, 1] if axis == 0 else co[:, 0]
            b = co[:, 1] if axis == 2 else co[:, 2]
            w, h = float(a.max() - a.min()), float(b.max() - b.min())
            if min(w, h) >= MIN_SIDE and max(w, h) >= MIN_EXTENT:
                layout.append((obj, loops, a, b, float(co[:, 2].mean())))

    # Largest density that fits the atlas.
    spans = [(float(a.max() - a.min()), float(b.max() - b.min())) for _, _, a, b, _ in layout]

    def sizes_for(d: float):
        return [(math.ceil(w * d) + 2 * MARGIN_PX, math.ceil(h * d) + 2 * MARGIN_PX) for w, h in spans]

    lo, hi = 1.0, profile.max_density
    if _pack(sizes_for(hi), profile.atlas) is None:
        for _ in range(14):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if _pack(sizes_for(mid), profile.atlas) else (lo, mid)
        density = lo
    else:
        density = hi
    sizes = sizes_for(density)
    positions = _pack(sizes, profile.atlas)
    if positions is None:
        raise RuntimeError("lightmap atlas overflow")

    floor = None
    for (obj, loops, a, b, z), (x, y), (w, h) in zip(layout, positions, spans):
        # The floor's top face: the box also has an equally large underside, lower down.
        if obj.name == profile.floor and (floor is None or (z, w * h) > floor[2]):
            floor = (x + MARGIN_PX, y + MARGIN_PX, (z, w * h), math.ceil(w * density), math.ceil(h * density))
    uvs: dict[str, np.ndarray] = {}
    block = {"outdoors": (RESERVED / 2, RESERVED / 2), "aisle": (RESERVED * 1.5, RESERVED / 2)}
    for obj in objects:
        if obj.data.polygons:
            # Skipped faces of baked objects fall back to the aisle level too.
            default = block["outdoors"] if kinds[obj.name] == "outdoors" else block["aisle"]
            uvs[obj.name] = np.tile(np.array(default, dtype=np.float32) / profile.atlas, (len(obj.data.loops), 1))
    for (obj, loops, a, b, _), (x, y), (w, h) in zip(layout, positions, spans):
        u = (x + MARGIN_PX + (a - a.min()) * density) / profile.atlas
        v = (y + MARGIN_PX + (b - b.min()) * density) / profile.atlas
        uvs[obj.name][loops] = np.stack([u, v], axis=1)
    for obj in objects:
        if obj.name in uvs:
            obj.data.uv_layers[UV_NAME].data.foreach_set("uv", uvs[obj.name].ravel())
    return {"density": density, "islands": len(layout), "baked": baked, "floor": floor}


# --- bake --------------------------------------------------------------------------------------

def _setup_cycles(samples: int) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == "METAL"]
        for d in prefs.devices:
            d.use = d.type == "METAL"
        if gpus:
            scene.cycles.device = "GPU"
    except Exception:  # noqa: BLE001 - no GPU backend: CPU is fine
        pass


def _daylight_spill() -> bpy.types.Object:
    """Soft light through the glass entrance, facing into the store."""
    data = bpy.data.lights.new("LM_DAYLIGHT", "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = 2.8, 2.4
    data.energy = 150.0
    data.color = (0.92, 0.96, 1.0)
    light = bpy.data.objects.new("LM_DAYLIGHT", data)
    bpy.context.scene.collection.objects.link(light)
    light.location = (0.0, -9.0, 1.3)
    light.rotation_euler = (math.pi / 2, 0.0, 0.0)  # emits along +Y
    return light


def _blur(values: np.ndarray, mask: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian blur over valid texels only (normalised convolution)."""
    radius = max(1, int(math.ceil(sigma * 2.5)))
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    num, den = values * mask, mask.astype(np.float64)
    for axis in (0, 1):
        n = np.zeros_like(num)
        d = np.zeros_like(den)
        for k, w in zip(range(-radius, radius + 1), kernel):
            n += w * np.roll(num, k, axis=axis)
            d += w * np.roll(den, k, axis=axis)
        num, den = n, d
    return np.where(den > 1e-6, num / np.maximum(den, 1e-6), 0.0)


def bake_lightmap(baked, floor, out_path: str, profile: Profile) -> dict:
    scene = bpy.context.scene
    atlas, samples = profile.atlas, profile.samples
    _setup_cycles(samples)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    tree = scene.world.node_tree
    background = tree.nodes.get("Background")
    if background is None:
        tree.nodes.clear()
        background = tree.nodes.new("ShaderNodeBackground")
        output = tree.nodes.new("ShaderNodeOutputWorld")
        tree.links.new(background.outputs["Background"], output.inputs["Surface"])
    if profile.lighting == "store":
        background.inputs["Color"].default_value = (0.55, 0.6, 0.65, 1.0)
        background.inputs["Strength"].default_value = 0.05
        light = _daylight_spill()
    else:
        background.inputs["Color"].default_value = (0.8, 0.86, 0.95, 1.0)
        background.inputs["Strength"].default_value = 1.0
        light = None

    # Glass and swinging doors stay out of the bake; the rest of the scene still casts shadows.
    hidden = [o for o in scene.objects if o.type == "MESH" and not o.hide_render and profile.moving.search(o.name)]
    for obj in hidden:
        obj.hide_render = True

    image = bpy.data.images.new("LM_ATLAS", atlas, atlas, alpha=True, float_buffer=True)
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(np.zeros(atlas * atlas * 4, dtype=np.float32))
    materials = {m for o in baked for m in o.data.materials if m}
    for material in materials:
        material.use_nodes = True
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        material.node_tree.nodes.active = node

    bake = scene.render.bake
    bake.use_pass_direct, bake.use_pass_indirect, bake.use_pass_color = True, True, False
    bake.margin, bake.margin_type = 8, "EXTEND"
    bake.use_clear = False
    bpy.ops.object.select_all(action="DESELECT")
    for obj in baked:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = baked[0]
    started = time.time()
    bpy.ops.object.bake(type="DIFFUSE", target="IMAGE_TEXTURES")
    print(f"lightmap baked in {time.time() - started:.0f} s ({scene.cycles.device}, {samples} spp)")

    pixels = np.empty(atlas * atlas * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(atlas, atlas, 4)
    mask = pixels[..., 3] > 0.5
    mask[:RESERVED, : 2 * RESERVED] = False
    luminance = pixels[..., 0] * 0.2126 + pixels[..., 1] * 0.7152 + pixels[..., 2] * 0.0722
    luminance = _blur(luminance.astype(np.float64), mask.astype(np.float64), profile.blur)

    # The open floor is the yardstick: its median maps to the floor level, brighter spots clip.
    fx, fy, _, fw, fh = floor
    reference = float(np.median(luminance[fy : fy + fh, fx : fx + fw])) / profile.floor_level
    level = np.clip(luminance / reference, 0.0, 1.0)
    level = 1.0 - STRENGTH * (1.0 - level)
    aisle = profile.aisle_level
    out = np.full((atlas, atlas), aisle)
    out[mask] = level[mask]
    # Dilated margins keep their baked values; the blocks below stay constant.
    out[:RESERVED, :RESERVED] = 1.0
    out[:RESERVED, RESERVED : 2 * RESERVED] = aisle
    # Blender rows run bottom to top; the JPEG is written top to bottom.
    write_jpeg(out_path, to_u8(out[::-1]), quality=90)

    for obj in hidden:
        obj.hide_render = False
    if light is not None:
        bpy.data.objects.remove(light)
    stats = {"reference": reference, "aisle": aisle, "covered": float(mask.mean())}
    print(f"lightmap: {stats}")
    return stats
