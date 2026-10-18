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
    M["carton_alt"] = material("M_EGG_CARTON_ALT", "#BDB8AC", roughness=0.9)
    M["rail_label"] = material("M_PRICE_RAIL", "#F4F1E8", roughness=0.6)
    M["joint"] = material("M_FLOOR_JOINT", "#CFC9BC", roughness=0.6)
    M["belt"] = material("M_CHECKOUT_BELT", "#4A4F52", roughness=0.7)
    M["sign"] = material("M_SIGN", "#F7F4EC", roughness=0.7)
    M["glass"] = material("M_ENTRANCE_GLASS", "#C9D3D6", roughness=0.15, metallic=0.1)
    # Forecourt: natural light and human tones (docs/DA.md §03, « Sortie L214 »).
    M["paving"] = material("M_PARVIS_PAVING", "#C4B9A6", roughness=0.85)
    M["grass"] = material("M_PARVIS_GRASS", "#A3A885", roughness=1.0)
    M["planter"] = material("M_PARVIS_PLANTER", "#B7A58E", roughness=0.9)
    M["trunk"] = material("M_TREE_TRUNK", "#7A6650", roughness=0.9)
    M["foliage"] = material("M_TREE_FOLIAGE", "#8FA77A", roughness=0.9)
    M["stand"] = material("M_STAND", "#E9E2D3", roughness=0.8)
    M["leaflet"] = material("M_LEAFLET", "#FBFAF6", roughness=0.7)
    M["trousers"] = material("M_TROUSERS", "#4F5660", roughness=0.9)
    M["clothes_teal"] = material("M_CLOTHES_TEAL", "#5E8C84", roughness=0.9)
    M["clothes_terracotta"] = material("M_CLOTHES_TERRACOTTA", "#B8735A", roughness=0.9)
    M["clothes_mustard"] = material("M_CLOTHES_MUSTARD", "#C9A548", roughness=0.9)
    M["skin_a"] = material("M_SKIN_A", "#C69C7B", roughness=0.7)
    M["skin_b"] = material("M_SKIN_B", "#8D5E43", roughness=0.7)
    M["skin_c"] = material("M_SKIN_C", "#E3C1A0", roughness=0.7)
    M["prod_a"] = material("M_PRODUCT_A", "#D9CBB0", roughness=0.7)
    M["prod_b"] = material("M_PRODUCT_B", "#B8C9B4", roughness=0.7)
    M["prod_c"] = material("M_PRODUCT_C", "#E3D9C6", roughness=0.7)


def shell(root) -> None:
    box("STORE_FLOOR", (-HALF_X, -HALF_Y, -0.1), (HALF_X, HALF_Y, 0.0), M["floor"], root)
    box("STORE_CEILING", (-HALF_X, -HALF_Y, HEIGHT), (HALF_X, HALF_Y, HEIGHT + 0.1), M["ceiling"], root)

    # Walls start below floor level so no slit shows where they meet the plinth outside.
    walls = {
        # North wall, split around the eggs opening.
        "N_W": ((-HALF_X, HALF_Y, -0.1), (-OPENING_HALF_W, HALF_Y + WALL, HEIGHT)),
        "N_E": ((OPENING_HALF_W, HALF_Y, -0.1), (HALF_X, HALF_Y + WALL, HEIGHT)),
        "N_LINTEL": ((-OPENING_HALF_W, HALF_Y, OPENING_H), (OPENING_HALF_W, HALF_Y + WALL, HEIGHT)),
        # South wall, split around the entrance.
        "S_W": ((-HALF_X, -HALF_Y - WALL, -0.1), (-ENTRANCE_HALF_W, -HALF_Y, HEIGHT)),
        "S_E": ((ENTRANCE_HALF_W, -HALF_Y - WALL, -0.1), (HALF_X, -HALF_Y, HEIGHT)),
        "S_LINTEL": ((-ENTRANCE_HALF_W, -HALF_Y - WALL, 2.6), (ENTRANCE_HALF_W, -HALF_Y, HEIGHT)),
        "E": ((HALF_X, -HALF_Y - WALL, -0.1), (HALF_X + WALL, HALF_Y + WALL, HEIGHT)),
        "W": ((-HALF_X - WALL, -HALF_Y - WALL, -0.1), (-HALF_X, HALF_Y + WALL, HEIGHT)),
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

    # Two sliding leaves inside the wall thickness; each slides into the wall (pocket door).
    for side, (x0, x1) in (("L", (-ENTRANCE_HALF_W, 0.0)), ("R", (0.0, ENTRANCE_HALF_W))):
        lo, hi = (x0, -HALF_Y - 0.2, 0.0), (x1, -HALF_Y - 0.1, 2.6)
        leaf = box(f"STORE_ENTRANCE_DOOR_{side}", lo, hi, M["glass"], root)
        half = ((x1 - x0) / 2, 0.05, 1.3)
        collider = MeshBuilder().box(tuple(-h for h in half), half).build(f"COL_ENTRANCE_DOOR_{side}", parent=leaf)
        helper_volume(collider)
    helper_volume(box("TRIGGER_EXIT", (-ENTRANCE_HALF_W, -HALF_Y, 0), (ENTRANCE_HALF_W, -HALF_Y + 0.8, 2.4), None, root))

    empty("SPAWN_PLAYER", (0.0, -7.0, 0.0), root)

    # Floor joints every 2.4 m give the eye a sense of scale.
    joints = MeshBuilder()
    for i in range(-4, 5):
        x = i * 2.4
        joints.box((x - 0.006, -HALF_Y, 0.0), (x + 0.006, HALF_Y, 0.002), M["joint"])
    for j in range(-3, 4):
        y = j * 2.4
        joints.box((-HALF_X, y - 0.006, 0.0), (HALF_X, y + 0.006, 0.002), M["joint"])
    joints.build("STORE_FLOOR_JOINTS", parent=root)

    # Two checkout counters by the entrance, clear of the central walkway.
    for side, (x0, x1) in (("L", (-7.0, -4.6)), ("R", (4.6, 7.0))):
        c = MeshBuilder()
        c.box((x0, -6.4, 0.0), (x1, -5.6, 0.85), M["shelf"])
        c.box((x0, -6.3, 0.85), (x1 - 0.6, -5.7, 0.9), M["belt"])
        c.box((x1 - 0.5, -6.25, 0.85), (x1 - 0.15, -5.95, 1.15), M["belt"])
        c.build(f"STORE_CHECKOUT_{side}", parent=root)
        helper_volume(box(f"COL_CHECKOUT_{side}", (x0, -6.4, 0.0), (x1, -5.6, 1.15), None, root))


def gondola_module(builder: MeshBuilder, x0: float, y0: float, length: float, depth: float, height: float) -> None:
    """Double-sided generic gondola: frame, shelves and stylised product blocks."""
    x1, y1 = x0 + depth, y0 + length
    builder.box((x0 + depth / 2 - 0.03, y0, 0.0), (x0 + depth / 2 + 0.03, y1, height), M["shelf"])
    builder.box((x0, y0, 0.0), (x1, y1, 0.12), M["accent"])
    products = (M["prod_a"], M["prod_b"], M["prod_c"])
    heights = (0.3, 0.22, 0.26, 0.18)
    for level, z in enumerate((0.12, 0.55, 0.98, 1.41)):
        builder.box((x0, y0, z), (x1, y1, z + 0.03), M["shelf"])
        # Blank price rails on both faces: commercial look, no real prices or brands.
        builder.box((x0 - 0.01, y0, z - 0.02), (x0 + 0.01, y1, z + 0.05), M["rail_label"])
        builder.box((x1 - 0.01, y0, z - 0.02), (x1 + 0.01, y1, z + 0.05), M["rail_label"])
        for side in (0, 1):
            sx0 = x0 + 0.04 if side == 0 else x0 + depth / 2 + 0.06
            for i in range(int(length / 0.3)):
                py = y0 + 0.03 + i * 0.3
                mat = products[(i + level + side) % 3]
                h = heights[(i * 3 + level + side) % 4]
                builder.box((sx0, py, z + 0.03), (sx0 + depth / 2 - 0.1, py + 0.24, z + 0.03 + h), mat)


def generic_shelving(root) -> None:
    depth, height, module_len = 0.9, 1.8, 1.25
    y_start, modules = -4.0, 7
    for row, x in enumerate((-7.95, -4.95, 4.05, 7.05)):
        b = MeshBuilder()
        for m in range(modules):
            gondola_module(b, 0.0, m * module_len, module_len, depth, height)
        # End caps and a blank header at both ends of the gondola run.
        run = modules * module_len
        for y0, y1 in ((-0.06, 0.0), (run, run + 0.06)):
            b.box((0.0, y0, 0.0), (depth, y1, height + 0.05), M["accent"])
            b.box((0.05, y0 - 0.01, height + 0.12), (depth - 0.05, y1 + 0.01, height + 0.42), M["sign"])
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
        # Blank price rail along the shelf front.
        b.box((bx0, -0.01, z - 0.02), (bx1, 0.01, z + 0.05), M["rail_label"])
        # Egg cartons: base and slightly narrower lid, two stacked, unbranded.
        for i in range(5):
            cx0, cx1 = span(0.08 + i * 0.28, 0.08 + i * 0.28 + 0.24)
            mat = M["carton"] if (i + int(z * 10)) % 2 == 0 else M["carton_alt"]
            for k in range(2):
                zb = z + 0.03 + k * 0.17
                b.box((cx0, 0.06, zb), (cx1, 0.36, zb + 0.08), mat)
                b.box((cx0 + 0.01, 0.07, zb + 0.08), (cx1 - 0.01, 0.35, zb + 0.15), mat)
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
    # Threshold zone: from the shelf front to just past the wall. Outside it, the side of its
    # centre plane tells whether the player stands in the store or on the terrace.
    helper_volume(
        box("TRIGGER_EGGS_ENTRY", (-OPENING_HALF_W, front_y, 0.0), (OPENING_HALF_W, HALF_Y + WALL + 0.3, OPENING_H), None, shelf)
    )
    # Floor across the wall thickness, so the store floor meets the terrace slab.
    box("STORE_THRESHOLD_EGGS", (-OPENING_HALF_W, HALF_Y, -0.1), (OPENING_HALF_W, HALF_Y + WALL, 0.0), M["floor"], shelf)
    # The terrace module's root is placed on this anchor (back face of the wall, floor level).
    empty("ANCHOR_EGGS_TERRACE", (0.0, SHELF_DEPTH + WALL, 0.0), shelf)
    # Sign panel: the label itself is drawn at runtime (docs/DECISIONS.md, signage).
    box("SIGN_EGGS", (-0.9, HALF_Y - 0.03, 2.45), (0.9, HALF_Y, 2.95), M["sign"], shelf)


def volunteer(name: str, x: float, y: float, facing_x: float, clothes, skin, root) -> None:
    """Stylised, calm standing figure holding a leaflet (docs/DA.md §04, docs/GDD.md §09)."""
    b = MeshBuilder()
    b.cylinder((x, y, 0.0), 0.17, 0.85, M["trousers"])
    b.cylinder((x, y, 0.85), 0.24, 0.65, clothes)
    b.sphere((x, y, 1.72), 0.14, skin)
    hand_x = x + facing_x * 0.3
    b.box((hand_x - 0.1, y - 0.15, 1.05), (hand_x + 0.1, y + 0.15, 1.07), M["leaflet"])
    b.build(name, parent=root)
    helper_volume(box(f"COL_{name}", (x - 0.3, y - 0.3, 0.0), (x + 0.3, y + 0.3, 1.8), None, root))


def parvis(root) -> None:
    """Forecourt outside the entrance (docs/GDD.md §03.10, §09). Volunteers stand aside the
    walkway; none blocks the way out. No logo, no organisation name: leaflets are blank."""
    south = -HALF_Y - WALL
    plaza = empty("PARVIS_ROOT", (0.0, 0.0, 0.0), root)
    box("PARVIS_GROUND", (-40.0, -80.0, -0.7), (40.0, south, -0.62), M["grass"], plaza)
    box("PARVIS_SLAB", (-14.0, -30.0, -0.6), (14.0, south, 0.0), M["paving"], plaza)

    edges = {
        "W": ((-14.0, -30.0), (-13.4, south)),
        "E": ((13.4, -30.0), (14.0, south)),
        "S": ((-14.0, -30.0), (14.0, -29.4)),
    }
    for key, ((x0, y0), (x1, y1)) in edges.items():
        box(f"PARVIS_PLANTER_{key}", (x0, y0, 0.0), (x1, y1, 0.55), M["planter"], plaza)
        helper_volume(box(f"COL_PARVIS_{key}", (x0, y0, 0.0), (x1, y1, 1.2), None, plaza))

    trees = MeshBuilder()
    for x, y in ((-13.7, -14.0), (-13.7, -22.0), (13.7, -14.0), (13.7, -22.0), (-6.0, -29.7), (6.0, -29.7)):
        trees.cylinder((x, y, 0.55), 0.12, 2.2, M["trunk"])
        trees.sphere((x, y, 3.3), 1.3, M["foliage"])
    trees.build("PARVIS_TREES", parent=plaza)

    stand = MeshBuilder()
    stand.box((-7.6, -21.0, 0.0), (-4.4, -20.2, 0.9), M["stand"])
    stand.box((-7.3, -20.8, 0.9), (-6.7, -20.4, 0.98), M["leaflet"])
    stand.build("STAND_PARVIS", parent=plaza)
    helper_volume(box("COL_STAND_PARVIS", (-7.6, -21.0, 0.0), (-4.4, -20.2, 0.9), None, plaza))

    volunteer("VOLUNTEER_01", -3.6, -13.0, 1.0, M["clothes_teal"], M["skin_a"], plaza)
    volunteer("VOLUNTEER_02", 3.9, -14.5, -1.0, M["clothes_terracotta"], M["skin_b"], plaza)
    volunteer("VOLUNTEER_03", -6.0, -19.4, 1.0, M["clothes_mustard"], M["skin_c"], plaza)

    # Walking past the volunteers opens the end menu.
    helper_volume(box("TRIGGER_PARVIS", (-10.0, -18.0, 0.0), (10.0, -16.0, 2.4), None, plaza))


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
    parvis(root)
    save_blend(os.path.abspath(argv[0]))


main()
