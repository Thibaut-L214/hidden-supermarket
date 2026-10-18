"""Blockout of the store with a scannable eggs shelf.

Usage (headless):
  Blender -b --factory-startup -P blender/scripts/build_store.py -- <out.blend>

Layout in Blender coordinates (metres, Z up):
- Interior X ∈ [-12, 12], Y ∈ [-9, 9], height 4.5.
- Entrance in the south wall (Y = -9), eggs shelf against the north wall (Y = +9)
  in front of a 3 × 2.2 m opening that leads to the terrace module.
- Doors open towards the store: each hinge sits on a front outer corner of the
  shelf and the door rotates ±90° around Z (clear passage 1.8 m).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from common import (  # noqa: E402
    MeshBuilder,
    box,
    empty,
    helper_volume,
    material,
    reset_scene,
    save_blend,
)

HALF_X, HALF_Y, HEIGHT, WALL = 12.0, 9.0, 4.5, 0.3
OPENING_HALF_W, OPENING_H = 1.5, 2.2
SHELF_DEPTH = 0.6
ENTRANCE_HALF_W = 1.5

# Palette from docs/DA.md §03 (store: ivory, beige, soft green).
M = {}


def materials() -> None:
    M["floor"] = material("M_STORE_FLOOR", "#E6E1D5", roughness=0.35)
    M["wall"] = material("M_STORE_WALL", "#EDE6D6", roughness=0.8)
    M["ceiling"] = material("M_STORE_CEILING", "#F2EEE6", roughness=0.9)
    M["light"] = material("M_STORE_LIGHT", "#FFFFFF", emission="#FFF8EC", emission_strength=2.0)
    M["shelf"] = material("M_SHELF_METAL", "#DAD7CF", roughness=0.45, metallic=0.2)
    M["accent"] = material("M_SHELF_ACCENT", "#A9C2A0", roughness=0.6)
    M["carton"] = material("M_EGG_CARTON", "#CDBFA4", roughness=0.9)
    M["sign"] = material("M_SIGN", "#F7F4EC", roughness=0.7)
    M["glass"] = material("M_ENTRANCE_GLASS", "#C9D3D6", roughness=0.15, metallic=0.1)
    M["prod_a"] = material("M_PRODUCT_A", "#D9CBB0", roughness=0.7)
    M["prod_b"] = material("M_PRODUCT_B", "#B8C9B4", roughness=0.7)
    M["prod_c"] = material("M_PRODUCT_C", "#E3D9C6", roughness=0.7)


def shell(root) -> None:
    box("STORE_FLOOR", (-HALF_X, -HALF_Y, -0.1), (HALF_X, HALF_Y, 0.0), M["floor"], root)
    box("STORE_CEILING", (-HALF_X, -HALF_Y, HEIGHT), (HALF_X, HALF_Y, HEIGHT + 0.1), M["ceiling"], root)

    walls = {
        # North wall, split around the eggs opening.
        "N_W": ((-HALF_X, HALF_Y, 0), (-OPENING_HALF_W, HALF_Y + WALL, HEIGHT)),
        "N_E": ((OPENING_HALF_W, HALF_Y, 0), (HALF_X, HALF_Y + WALL, HEIGHT)),
        "N_LINTEL": ((-OPENING_HALF_W, HALF_Y, OPENING_H), (OPENING_HALF_W, HALF_Y + WALL, HEIGHT)),
        # South wall, split around the entrance.
        "S_W": ((-HALF_X, -HALF_Y - WALL, 0), (-ENTRANCE_HALF_W, -HALF_Y, HEIGHT)),
        "S_E": ((ENTRANCE_HALF_W, -HALF_Y - WALL, 0), (HALF_X, -HALF_Y, HEIGHT)),
        "S_LINTEL": ((-ENTRANCE_HALF_W, -HALF_Y - WALL, 2.6), (ENTRANCE_HALF_W, -HALF_Y, HEIGHT)),
        "E": ((HALF_X, -HALF_Y - WALL, 0), (HALF_X + WALL, HALF_Y + WALL, HEIGHT)),
        "W": ((-HALF_X - WALL, -HALF_Y - WALL, 0), (-HALF_X, HALF_Y + WALL, HEIGHT)),
    }
    for key, (lo, hi) in walls.items():
        box(f"STORE_WALL_{key}", lo, hi, M["wall"], root)
        if "LINTEL" not in key:
            helper_volume(box(f"COL_WALL_{key}", lo, hi, None, root))

    lights = MeshBuilder()
    for x in range(-9, 10, 3):
        for y in range(-6, 7, 3):
            lights.box((x - 0.6, y - 0.3, HEIGHT - 0.04), (x + 0.6, y + 0.3, HEIGHT), M["light"])
    lights.build("STORE_LIGHT_PANELS", parent=root)

    entrance = (-ENTRANCE_HALF_W, -HALF_Y - 0.2, 0), (ENTRANCE_HALF_W, -HALF_Y - 0.1, 2.6)
    box("STORE_ENTRANCE_DOORS", *entrance, M["glass"], root)
    helper_volume(box("COL_ENTRANCE_DOORS", *entrance, None, root))
    helper_volume(box("TRIGGER_EXIT", (-ENTRANCE_HALF_W, -HALF_Y, 0), (ENTRANCE_HALF_W, -HALF_Y + 0.8, 2.4), None, root))

    empty("SPAWN_PLAYER", (0.0, -7.0, 0.0), root)


def gondola_module(builder: MeshBuilder, x0: float, y0: float, length: float, depth: float, height: float) -> None:
    """Double-sided generic gondola: frame, shelves and stylised product blocks."""
    x1, y1 = x0 + depth, y0 + length
    builder.box((x0 + depth / 2 - 0.03, y0, 0.0), (x0 + depth / 2 + 0.03, y1, height), M["shelf"])
    builder.box((x0, y0, 0.0), (x1, y1, 0.12), M["accent"])
    products = (M["prod_a"], M["prod_b"], M["prod_c"])
    for level, z in enumerate((0.12, 0.55, 0.98, 1.41)):
        builder.box((x0, y0, z), (x1, y1, z + 0.03), M["shelf"])
        for side in (0, 1):
            sx0 = x0 + 0.04 if side == 0 else x0 + depth / 2 + 0.06
            for i in range(int(length / 0.3)):
                py = y0 + 0.03 + i * 0.3
                mat = products[(i + level + side) % 3]
                builder.box((sx0, py, z + 0.03), (sx0 + depth / 2 - 0.1, py + 0.24, z + 0.33), mat)


def generic_shelving(root) -> None:
    depth, height, module_len = 0.9, 1.8, 1.25
    y_start, modules = -4.0, 7
    for row, x in enumerate((-7.95, -4.95, 4.05, 7.05)):
        b = MeshBuilder()
        for m in range(modules):
            gondola_module(b, 0.0, m * module_len, module_len, depth, height)
        b.build(f"SHELF_GENERIC_{row + 1:02d}", (x, y_start, 0.0), root)
        helper_volume(
            box(f"COL_SHELF_GENERIC_{row + 1:02d}", (x, y_start, 0), (x + depth, y_start + modules * module_len, height), None, root)
        )


def door_half(hinge, side: int):
    """One rigid half of the eggs shelf, built around its hinge (origin on the pivot).

    side = -1 for the left door (hinge at x = -1.5), +1 for the right door.
    Local X points from the hinge towards the centre of the shelf.
    """
    name = "L" if side < 0 else "R"
    width, h = OPENING_HALF_W, OPENING_H
    inward = -side  # local +x goes towards the shelf centre for the left door

    def span(a: float, b: float) -> tuple[float, float]:
        lo, hi = sorted((a * inward, b * inward))
        return lo, hi

    b = MeshBuilder()
    # Back panel, outer side panel, top, plinth (accent) and four shelves.
    bx0, bx1 = span(0.0, width)
    b.box((bx0, SHELF_DEPTH - 0.04, 0.0), (bx1, SHELF_DEPTH, h), M["shelf"])
    sx0, sx1 = span(0.0, 0.04)
    b.box((sx0, 0.0, 0.0), (sx1, SHELF_DEPTH, h), M["shelf"])
    b.box((bx0, 0.0, h - 0.04), (bx1, SHELF_DEPTH, h), M["shelf"])
    b.box((bx0, 0.0, 0.0), (bx1, SHELF_DEPTH, 0.12), M["accent"])
    for z in (0.12, 0.6, 1.08, 1.56):
        b.box((bx0, 0.0, z), (bx1, SHELF_DEPTH - 0.04, z + 0.03), M["shelf"])
        # Egg cartons: stylised, unbranded blocks.
        for i in range(5):
            cx0, cx1 = span(0.08 + i * 0.28, 0.08 + i * 0.28 + 0.24)
            b.box((cx0, 0.06, z + 0.03), (cx1, 0.36, z + 0.13), M["carton"])
            b.box((cx0, 0.06, z + 0.13), (cx1, 0.36, z + 0.23), M["carton"])
    door = b.build(f"DOOR_EGGS_{name}", parent=hinge)
    collider = MeshBuilder().box((bx0, 0.0, 0.0), (bx1, SHELF_DEPTH, h)).build(f"COL_DOOR_EGGS_{name}", parent=door)
    helper_volume(collider)
    return door


def eggs_shelf(root) -> None:
    front_y = HALF_Y - SHELF_DEPTH
    shelf = empty("SHELF_EGGS_ROOT", (0.0, front_y, 0.0), root)
    shelf["chainId"] = "eggs"

    for side in (-1, 1):
        hinge = empty(f"HINGE_EGGS_{'L' if side < 0 else 'R'}", (side * OPENING_HALF_W, 0.0, 0.0), shelf)
        door_half(hinge, side)

    helper_volume(box("SCAN_EGGS", (-OPENING_HALF_W, front_y, 0.0), (OPENING_HALF_W, HALF_Y, OPENING_H), None, shelf))
    helper_volume(
        box("TRIGGER_EGGS_ENTRY", (-OPENING_HALF_W, HALF_Y, 0.0), (OPENING_HALF_W, HALF_Y + WALL + 0.3, OPENING_H), None, shelf)
    )
    # Sign panel: the label itself is drawn at runtime (docs/DECISIONS.md, signage).
    box("SIGN_EGGS", (-0.9, HALF_Y - 0.03, 2.45), (0.9, HALF_Y, 2.95), M["sign"], shelf)


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: build_store.py -- <out.blend>")
    reset_scene()
    materials()
    root = empty("STORE_ROOT")
    shell(root)
    generic_shelving(root)
    eggs_shelf(root)
    save_blend(os.path.abspath(argv[0]))


main()
