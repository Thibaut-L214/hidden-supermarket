"""Generates the tileable PBR sets listed in blender/textures/surfaces.json.

Usage (headless):
  Blender -b --factory-startup -P blender/scripts/make_textures.py

Everything is periodic noise, so the sets tile without seams and the output is deterministic.
Each set writes three files into blender/textures/:
  <set>_color.jpg   tint multiplied with the material's base colour (values just under 1)
  <set>_normal.jpg  tangent-space normal map, OpenGL convention (glTF)
  <set>_orm.jpg     G = roughness modulation (centred on ROUGH_CENTRE), B = metalness (1: the
                    material's metallicFactor decides), R = 1 (no occlusion: the lightmap does)
scripts/lib/surfaces.mjs rescales the factors so a material keeps its authored average.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from imageio_util import to_u8, write_jpeg  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "textures")
ROUGH_CENTRE = 0.85  # keep in sync with scripts/lib/surfaces.mjs
COLOUR_CENTRE = 0.93


def noise(n: int, fx: int, fy: int, rng: np.random.Generator) -> np.ndarray:
    """Periodic value noise in [0, 1]: a fy × fx random grid, smoothly interpolated, wrapping."""
    grid = rng.random((fy, fx))
    xs = np.arange(n) * fx / n
    ys = np.arange(n) * fy / n
    x0, y0 = xs.astype(int), ys.astype(int)
    tx, ty = xs - x0, ys - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    x1, y1 = (x0 + 1) % fx, (y0 + 1) % fy
    a = grid[np.ix_(y0, x0)]
    b = grid[np.ix_(y0, x1)]
    c = grid[np.ix_(y1, x0)]
    d = grid[np.ix_(y1, x1)]
    top = a + (b - a) * tx[None, :]
    bottom = c + (d - c) * tx[None, :]
    return top + (bottom - top) * ty[:, None]


def fbm(n: int, layers, seed: int) -> np.ndarray:
    """Weighted sum of noise layers (fx, fy, weight), centred on 0 with unit-ish amplitude."""
    rng = np.random.default_rng(seed)
    total = sum(w for _, _, w in layers)
    out = sum(w * (noise(n, fx, fy, rng) - 0.5) for fx, fy, w in layers)
    return out * 2 / total


def hash_tiles(n: int, tiles: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    values = rng.random((tiles, tiles))
    idx = (np.arange(n) * tiles // n)
    return values[np.ix_(idx, idx)]


def edge_distance(n: int, tiles: int) -> np.ndarray:
    """Distance in pixels to the nearest tile boundary (grout lines)."""
    step = n / tiles
    p = np.arange(n) % step
    d = np.minimum(p, step - p)
    return np.minimum(d[None, :], d[:, None])


# Each generator returns (height, colour, roughness), all in [-1, 1] / [0, 1] float arrays.
def gen_floor(n, seed):
    cloud = fbm(n, [(3, 3, 1), (7, 7, 0.6)], seed)
    scuff = fbm(n, [(2, 22, 1), (4, 40, 0.5)], seed + 1)
    grout = np.clip(1 - edge_distance(n, 2) / 3.0, 0, 1)
    tone = (hash_tiles(n, 2, seed + 2) - 0.5) * 0.05
    height = -grout + 0.04 * fbm(n, [(96, 96, 1)], seed + 3)
    colour = COLOUR_CENTRE + tone + 0.02 * cloud - 0.05 * grout - 0.012 * scuff
    rough = ROUGH_CENTRE + 0.05 * cloud + 0.06 * scuff + 0.12 * grout
    return height, colour, rough


def gen_plaster(n, seed):
    height = fbm(n, [(64, 64, 0.5), (128, 128, 0.3), (256, 256, 0.2)], seed)
    cloud = fbm(n, [(3, 3, 1), (9, 9, 0.5)], seed + 1)
    return height * 0.5, COLOUR_CENTRE + 0.035 * cloud, ROUGH_CENTRE + 0.05 * height


def gen_plaster_fine(n, seed):
    """Smooth painted plaster seen from arm's length (store walls and ceiling): roller stipple
    of a few millimetres at a 1 m repeat, hardly any tonal cloud (it would show the repeat on a
    24 m wall; the lightmap gives the walls their variation). Fixed seeds."""
    stipple = fbm(n, [(180, 180, 0.6), (256, 256, 0.4)], 9101)
    trowel = fbm(n, [(5, 5, 0.6), (11, 11, 0.4)], 9102)
    height = 0.42 * stipple + 0.1 * trowel
    return height, COLOUR_CENTRE + 0.008 * trowel + 0.006 * stipple, ROUGH_CENTRE + 0.04 * stipple


def gen_concrete(n, seed):
    base = fbm(n, [(8, 8, 0.4), (32, 32, 0.3), (128, 128, 0.2), (256, 256, 0.1)], seed)
    pores = np.clip((fbm(n, [(200, 200, 1)], seed + 1) - 0.55) * 4, 0, 1)
    cloud = fbm(n, [(3, 3, 1), (11, 11, 0.6)], seed + 2)
    height = base * 0.6 - pores
    colour = COLOUR_CENTRE + 0.05 * cloud - 0.05 * pores + 0.015 * base
    return height, colour, ROUGH_CENTRE + 0.08 * base


def gen_metal(n, seed):
    streaks = fbm(n, [(2, 200, 0.6), (4, 400, 0.4)], seed)
    wear = fbm(n, [(3, 9, 1)], seed + 1)
    height = streaks * 0.35
    colour = COLOUR_CENTRE + 0.03 * streaks + 0.02 * wear
    return height, colour, ROUGH_CENTRE + 0.12 * streaks + 0.04 * wear


def gen_paint(n, seed):
    peel = fbm(n, [(48, 48, 0.6), (96, 96, 0.4)], seed)
    cloud = fbm(n, [(3, 3, 1)], seed + 1)
    return peel * 0.5, COLOUR_CENTRE + 0.02 * cloud + 0.01 * peel, ROUGH_CENTRE + 0.06 * peel


def gen_carton(n, seed):
    fibres = fbm(n, [(150, 120, 0.5), (300, 240, 0.5)], seed)
    blotch = fbm(n, [(5, 5, 1), (14, 14, 0.5)], seed + 1)
    return fibres * 0.5, COLOUR_CENTRE + 0.05 * blotch + 0.02 * fibres, ROUGH_CENTRE + 0.08 * fibres


def gen_wood(n, seed):
    grain = fbm(n, [(3, 120, 0.5), (6, 260, 0.3), (2, 24, 0.2)], seed)
    rings = np.sin(fbm(n, [(2, 6, 1)], seed + 1) * 9) * 0.5
    height = grain * 0.5 + rings * 0.2
    return height, COLOUR_CENTRE + 0.05 * grain + 0.03 * rings, ROUGH_CENTRE + 0.07 * grain


def gen_grass(n, seed):
    clumps = fbm(n, [(4, 4, 0.5), (16, 16, 0.3), (64, 64, 0.2)], seed)
    blades = fbm(n, [(200, 200, 1)], seed + 1)
    return blades * 0.4 + clumps * 0.2, COLOUR_CENTRE - 0.04 + 0.09 * clumps + 0.03 * blades, ROUGH_CENTRE + 0.1 * blades


def gen_soil(n, seed):
    clods = fbm(n, [(6, 6, 0.4), (24, 24, 0.3), (96, 96, 0.3)], seed)
    grit = fbm(n, [(220, 220, 1)], seed + 1)
    return clods * 0.8 + grit * 0.3, COLOUR_CENTRE - 0.02 + 0.07 * clods + 0.02 * grit, ROUGH_CENTRE + 0.1 * grit

# --- terraces: sheet metal, sandwich panels, roads, crop rows -----------------------------------
# Seen from a raised terrace, 30 m and more away: coarse, directional patterns that survive
# mip-mapping. Ribs, joints and rows run along V (they vary along U); meshes that need another
# direction author their own UV0 (blender/scripts/landscape_props.py). These generators use fixed
# seeds, so adding a set elsewhere in surfaces.json never changes them.

def _across(n):
    """U coordinate of each pixel column, in [0, 1)."""
    return ((np.arange(n) + 0.5) / n)[None, :] * np.ones((n, 1))


def gen_cladding(n, seed):
    """Trapezoidal steel sheet, six ribs per repeat, with rain streaks along the ribs."""
    x = _across(n)
    d = np.abs((x * 6) % 1.0 - 0.5)
    rib = np.clip((0.30 - d) / 0.15, 0, 1)
    streaks = fbm(n, [(40, 2, 0.6), (90, 3, 0.4)], 7001)
    cloud = fbm(n, [(3, 3, 1)], 7002)
    sheet = (np.random.default_rng(7003).random(2)[(x * 2).astype(int) % 2] - 0.5) * 0.045
    colour = COLOUR_CENTRE + sheet + 0.035 * streaks + 0.02 * cloud - 0.035 * (1 - rib)
    return rib + 0.03 * streaks, colour, ROUGH_CENTRE + 0.08 * streaks + 0.05 * (1 - rib)


def gen_panel(n, seed):
    """Insulated sandwich panels, three per repeat: narrow joints, faint micro-ribbing."""
    x = _across(n)
    p = (x * 3) % 1.0
    joint = np.clip(1 - np.minimum(p, 1 - p) * (n / 3) / 2.5, 0, 1)
    micro = 0.05 * np.sin(2 * np.pi * x * 36)
    streaks = fbm(n, [(30, 2, 1)], 7011)
    tone = (np.random.default_rng(7012).random(3)[(x * 3).astype(int) % 3] - 0.5) * 0.025
    colour = COLOUR_CENTRE + tone + 0.02 * streaks - 0.12 * joint
    return micro - 0.6 * joint, colour, ROUGH_CENTRE - 0.03 + 0.05 * streaks + 0.1 * joint


def gen_asphalt(n, seed):
    """Worn asphalt: aggregate grain, blotches, faint lengthwise streaks (roads map V along)."""
    grit = fbm(n, [(180, 180, 0.6), (90, 90, 0.4)], 7021)
    blotch = fbm(n, [(5, 5, 0.6), (13, 13, 0.4)], 7022)
    streak = fbm(n, [(26, 2, 1)], 7023)
    colour = COLOUR_CENTRE - 0.01 + 0.05 * blotch + 0.025 * grit + 0.035 * streak
    return grit * 0.6 + blotch * 0.2, colour, ROUGH_CENTRE + 0.08 * grit - 0.04 * streak


def gen_gravel(n, seed):
    """Compacted gravel: yards and road shoulders."""
    stones = fbm(n, [(70, 70, 0.5), (150, 150, 0.5)], 7031)
    blotch = fbm(n, [(4, 4, 0.6), (11, 11, 0.4)], 7032)
    return stones, COLOUR_CENTRE - 0.015 + 0.06 * stones + 0.06 * blotch, ROUGH_CENTRE + 0.1 * stones


def gen_furrows(n, seed):
    """Ploughed soil: sixteen ridges per repeat, lighter (drier) crests, cloddy."""
    x = _across(n)
    ridge = np.sin(2 * np.pi * x * 16)
    clods = fbm(n, [(40, 40, 0.5), (110, 110, 0.5)], 7041)
    blotch = fbm(n, [(4, 4, 1)], 7042)
    colour = COLOUR_CENTRE - 0.03 + 0.085 * ridge + 0.03 * clods + 0.03 * blotch
    return ridge * 0.8 + clods * 0.3, colour, ROUGH_CENTRE + 0.08 * clods


def gen_croprows(n, seed):
    """Drilled crop: thirty-two plant rows per repeat on bare soil, one pair of tramlines.
    Returns an RGB tint: the rows keep the material's colour, the soil between them turns warm."""
    x = _across(n)
    row = smoothstep(0.3, 0.7, 0.5 + 0.5 * np.cos(2 * np.pi * x * 32))
    tram = np.exp(-(((x - 0.444) / 0.011) ** 2)) + np.exp(-(((x - 0.556) / 0.011) ** 2))
    leaf = fbm(n, [(60, 90, 0.5), (140, 200, 0.5)], 7051)
    blotch = fbm(n, [(4, 4, 1)], 7052)
    plant = np.clip(row * (1 - np.clip(tram, 0, 1)) * (0.85 + 0.3 * leaf), 0, 1)
    soil = np.array([0.86, 0.76, 0.68])
    green = np.array([0.93, 0.985, 0.9])
    colour = soil + (green - soil) * plant[..., None] + (0.03 * blotch + 0.02 * leaf)[..., None]
    return plant * (0.75 + 0.25 * leaf), colour, ROUGH_CENTRE + 0.08 * leaf


GENERATORS = {
    "floor": gen_floor,
    "plaster": gen_plaster,
    "concrete": gen_concrete,
    "metal": gen_metal,
    "paint": gen_paint,
    "carton": gen_carton,
    "wood": gen_wood,
    "grass": gen_grass,
    "soil": gen_soil,
    "cladding": gen_cladding,
    "panel": gen_panel,
    "asphalt": gen_asphalt,
    "gravel": gen_gravel,
    "furrows": gen_furrows,
    "croprows": gen_croprows,
    "plaster_fine": gen_plaster_fine,
}


def normal_map(height: np.ndarray, strength: float) -> np.ndarray:
    """Tangent-space normals from a periodic height field, rows top to bottom, +Y up."""
    n = height.shape[0]
    slope = strength * n / 256.0  # gradient per pixel grows with resolution
    gx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5 * slope
    gy = (np.roll(height, 1, axis=0) - np.roll(height, -1, axis=0)) * 0.5 * slope
    nz = np.ones_like(height)
    length = np.sqrt(gx * gx + gy * gy + nz * nz)
    return np.stack([-gx / length, gy / length, nz / length], axis=-1) * 0.5 + 0.5


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def goods_atlas(size: int = 512) -> np.ndarray:
    """Normal atlas for the products (surfaces.py, project_goods_uvs): 2 × 2 cells, row 0 at the
    bottom (Blender UV space). box: rounded edges with a faint inset panel; cyl: bevelled ends
    and a shallow groove, identical around the circumference; flat: neutral (caps)."""
    half = size // 2
    t = (np.arange(half) + 0.5) / half
    u, v = np.meshgrid(t, t)  # v rows run upwards, like the cell's UV
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    box = smoothstep(0.0, 0.16, edge) + 0.12 * smoothstep(0.2, 0.24, edge)
    cyl = smoothstep(0.0, 0.1, v) * smoothstep(0.0, 0.1, 1 - v) - 0.18 * np.exp(-(((v - 0.52) / 0.035) ** 2))
    height = np.zeros((size, size))
    height[:half, :half] = box  # (column 0, row 0)
    height[:half, half:] = cyl  # (column 1, row 0)
    # The flat cell (column 0, row 1) stays at 0.
    height = height[::-1]  # top-first rows, as normal_map expects
    slope = 14.0
    gx = np.gradient(height, axis=1) * slope * half / 256
    gy = -np.gradient(height, axis=0) * slope * half / 256
    nz = np.ones_like(height)
    length = np.sqrt(gx * gx + gy * gy + nz * nz)
    return np.stack([-gx / length, gy / length, nz / length], axis=-1) * 0.5 + 0.5


def main() -> None:
    with open(os.path.join(ROOT, "surfaces.json"), encoding="utf-8") as f:
        sets = json.load(f)["sets"]
    # Optional set names after `--`: regenerate only those (the others stay untouched on disk).
    only = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    for seed, (name, spec) in enumerate(sets.items(), start=1):
        if only and name not in only:
            continue
        n = spec["size"]
        height, colour, rough = GENERATORS[name](n, seed * 101)
        c = colour if colour.ndim == 3 else np.broadcast_to(colour[..., None], (n, n, 3))
        write_jpeg(os.path.join(ROOT, f"{name}_color.jpg"), to_u8(c))
        write_jpeg(os.path.join(ROOT, f"{name}_normal.jpg"), to_u8(normal_map(height, 3.0)), quality=92)
        orm = np.stack([np.ones_like(rough), rough, np.ones_like(rough)], axis=-1)
        write_jpeg(os.path.join(ROOT, f"{name}_orm.jpg"), to_u8(orm))
        print(f"{name}: {n}² ok")
    if not only:
        write_jpeg(os.path.join(ROOT, "goods_normal.jpg"), to_u8(goods_atlas()), quality=95)
        print("goods atlas ok")


main()
