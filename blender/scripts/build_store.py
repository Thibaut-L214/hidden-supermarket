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

import math  # noqa: E402

import bpy  # noqa: E402
import landscape_props as land  # noqa: E402
import parvis_props as outside  # noqa: E402
import store_props as props  # noqa: E402
from common import (  # noqa: E402
    MeshBuilder,
    bevel,
    box,
    empty,
    glass,
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
    # Clear glass: the forecourt and the volunteers show through the sliding leaves.
    M["glass"] = glass("M_ENTRANCE_GLASS", "#C9D3D6", alpha=0.2)
    # Forecourt: natural light and human tones (docs/DA.md §03, « Sortie L214 »).
    M["paving"] = material("M_PARVIS_PAVING", "#C4B9A6", roughness=0.85)
    M["grass"] = material("M_PARVIS_GRASS", "#A3A885", roughness=1.0)
    M["planter"] = material("M_PARVIS_PLANTER", "#B7A58E", roughness=0.9)
    M["egg_brown"] = material("M_EGG_BROWN", "#E2C9A6", roughness=0.55)
    M["egg_cream"] = material("M_EGG_CREAM", "#F2EBDD", roughness=0.55)
    M["sticker"] = material("M_CARTON_STICKER", "#F6F1E4", roughness=0.6)
    M["shelf_light"] = material("M_SHELF_LIGHT", "#FFFFFF", emission="#FFF4E2", emission_strength=1.4)
    M["skirting"] = material("M_SKIRTING", "#B9B2A3", roughness=0.6)
    props.materials()
    outside.materials()
    land.materials()


def inner_walls(root) -> None:
    """Gridded inner faces just inside the wall boxes, skirting and a soft accent band."""
    g = MeshBuilder(recalc_normals=False)
    e = 0.003
    hx, hy, h = HALF_X, HALF_Y, HEIGHT

    def cells(length: float) -> int:
        return max(1, round(length / 0.5))

    # North (faces -Y), around the eggs opening.
    for x0, x1, z0, z1 in ((-hx, -OPENING_HALF_W, 0, h), (OPENING_HALF_W, 4.5, 0, h), (7.5, hx, 0, h), (-OPENING_HALF_W, OPENING_HALF_W, OPENING_H, h), (4.5, 7.5, OPENING_H, h)):
        g.grid((x0, hy - e, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0), (cells(x1 - x0), cells(z1 - z0)), M["wall"])
    # South (faces +Y), around the entrance.
    for x0, x1, z0, z1 in ((-hx, -ENTRANCE_HALF_W, 0, h), (ENTRANCE_HALF_W, hx, 0, h), (-ENTRANCE_HALF_W, ENTRANCE_HALF_W, 2.6, h)):
        g.grid((x0, -hy + e, z0), (0, 0, z1 - z0), (x1 - x0, 0, 0), (cells(z1 - z0), cells(x1 - x0)), M["wall"])
    # East (faces -X) and west (faces +X).
    g.grid((hx - e, -hy, 0), (0, 0, h), (0, 2 * hy, 0), (cells(h), cells(2 * hy)), M["wall"])
    g.grid((-hx + e, -hy, 0), (0, 2 * hy, 0), (0, 0, h), (cells(2 * hy), cells(h)), M["wall"])
    g.build("STORE_WALLS_INNER", parent=root)

    trim = MeshBuilder()
    for z0, z1, mat in ((0.0, 0.1, M["skirting"]), (3.05, 3.2, M["accent"])):
        # Openings interrupt the trim only below their lintel.
        for x0, x1 in ((-hx, -OPENING_HALF_W), (OPENING_HALF_W, 4.5), (7.5, hx)):
            trim.box((x0, hy - 0.02, z0), (x1, hy, z1), mat)
        if z0 > OPENING_H:
            trim.box((-OPENING_HALF_W, hy - 0.02, z0), (OPENING_HALF_W, hy, z1), mat)
            trim.box((4.5, hy - 0.02, z0), (7.5, hy, z1), mat)
        for x0, x1 in ((-hx, -ENTRANCE_HALF_W), (ENTRANCE_HALF_W, hx)):
            trim.box((x0, -hy, z0), (x1, -hy + 0.02, z1), mat)
        if z0 > 2.6:
            trim.box((-ENTRANCE_HALF_W, -hy, z0), (ENTRANCE_HALF_W, -hy + 0.02, z1), mat)
        trim.box((hx - 0.02, -hy, z0), (hx, hy, z1), mat)
        trim.box((-hx, -hy, z0), (-hx + 0.02, hy, z1), mat)
    bevel(trim.build("STORE_WALL_TRIM", parent=root), 0.004)


def shell(root) -> None:
    # Floor and ceiling as fine grids: per-vertex occlusion needs vertices to show contact
    # shadows under the furniture.
    MeshBuilder(recalc_normals=False).grid(
        (-HALF_X, -HALF_Y, 0.0), (2 * HALF_X, 0, 0), (0, 2 * HALF_Y, 0), (60, 45), M["floor"]
    ).build("STORE_FLOOR", parent=root)
    MeshBuilder(recalc_normals=False).grid(
        (-HALF_X, -HALF_Y, HEIGHT), (0, 2 * HALF_Y, 0), (2 * HALF_X, 0, 0), (36, 48), M["ceiling"]
    ).build("STORE_CEILING", parent=root)
    inner_walls(root)

    # Walls start below floor level so no slit shows where they meet the plinth outside.
    walls = {
        # North wall, split around the eggs opening.
        "N_W": ((-HALF_X, HALF_Y, -0.1), (-OPENING_HALF_W, HALF_Y + WALL, HEIGHT)),
        "N_E": ((OPENING_HALF_W, HALF_Y, -0.1), (4.5, HALF_Y + WALL, HEIGHT)),
        "N_BEEF_E": ((7.5, HALF_Y, -0.1), (HALF_X, HALF_Y + WALL, HEIGHT)),
        "N_BEEF_LINTEL": ((4.5, HALF_Y, OPENING_H), (7.5, HALF_Y + WALL, HEIGHT)),
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

    lights, frames = MeshBuilder(), MeshBuilder()
    for x in range(-9, 10, 3):
        for y in range(-6, 7, 3):
            lights.box((x - 0.6, y - 0.3, HEIGHT - 0.04), (x + 0.6, y + 0.3, HEIGHT - 0.02), M["light"])
            for x0, x1, y0, y1 in (
                (x - 0.63, x + 0.63, y - 0.33, y - 0.3), (x - 0.63, x + 0.63, y + 0.3, y + 0.33),
                (x - 0.63, x - 0.6, y - 0.3, y + 0.3), (x + 0.6, x + 0.63, y - 0.3, y + 0.3),
            ):
                frames.box((x0, y0, HEIGHT - 0.05), (x1, y1, HEIGHT - 0.02), props.M["metal"])
    # Flush with the ceiling: excluded from the occlusion bake, or they would leave dark halos.
    lights.build("STORE_LIGHT_PANELS", parent=root)["ao_skip"] = True
    frames.build("STORE_LIGHT_FRAMES", parent=root)["ao_skip"] = True
    props.ceiling(HALF_X, HALF_Y, HEIGHT, root)
    props.entrance(HALF_Y, WALL, ENTRANCE_HALF_W, root)

    # Two sliding leaves inside the wall thickness; each slides into the wall (pocket door).
    for side, (x0, x1) in (("L", (-ENTRANCE_HALF_W, 0.0)), ("R", (0.0, ENTRANCE_HALF_W))):
        lo, hi = (x0, -HALF_Y - 0.2, 0.0), (x1, -HALF_Y - 0.1, 2.6)
        leaf = box(f"STORE_ENTRANCE_DOOR_{side}", lo, hi, M["glass"], root)
        leaf["ao_skip"] = True  # glass neither receives nor casts occlusion
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
    joints.build("STORE_FLOOR_JOINTS", parent=root)["ao_skip"] = True

    # Two checkout counters by the entrance, clear of the central walkway.
    props.checkout("STORE_CHECKOUT_L", -7.0, -4.6, root)
    props.checkout("STORE_CHECKOUT_R", 4.6, 7.0, root)
    props.carts_and_baskets(root)


def generic_shelving(root) -> None:
    """Four gondola runs with generic aisle categories and their hanging signs."""
    rows = ((-7.95, "Épicerie"), (-4.95, "Petit-déjeuner"), (4.05, "Boissons"), (7.05, "Hygiène"))
    for i, (x, aisle) in enumerate(rows, start=1):
        props.gondola(f"SHELF_GENERIC_{i:02d}", x, -4.0, 7, aisle, root, M["accent"], M["sign"])
        sign_name = f"AISLE_SIGN_{i:02d}"
        props.aisle_sign(sign_name, x + 0.45, -4.0 + 7 * 1.25 / 2, root, M["sign"])
        # The label is drawn at runtime from this extra (glTF extras → userData.label).
        bpy.data.objects[sign_name]["label"] = aisle
    props.fridge_run("FRIDGE_W", -HALF_X, 1, -5.0, 8, root)
    props.fridge_run("FRIDGE_E", HALF_X, -1, -5.0, 8, root)


def carton(b: MeshBuilder, x0: float, x1: float, y0: float, y1: float, z: float, mat, open_eggs: MeshBuilder | None) -> None:
    """Six-egg carton, unbranded: tray, ribbed lid and a blank sticker. When `open_eggs` is
    given, the lid stands open towards the wall and six eggs show in the tray."""
    tray = 0.055
    b.box((x0, y0, z), (x1, y1, z + tray), mat)
    if open_eggs is None:
        b.box((x0 + 0.004, y0 + 0.004, z + tray), (x1 - 0.004, y1 - 0.004, z + 0.1), mat)
        for k in (1, 2):
            rx = x0 + k * (x1 - x0) / 3
            b.box((rx - 0.006, y0 + 0.02, z + 0.1), (rx + 0.006, y1 - 0.02, z + 0.11), mat)
        b.box((x0 + 0.04, y0 - 0.002, z + 0.062), (x1 - 0.04, y0, z + 0.092), M["sticker"])
        return
    cx = (x0 + x1) / 2
    lid = (x1 - x0 - 0.008, y1 - y0 - 0.008, 0.045)
    b.oriented_box((cx, (y0 + y1) / 2, z + tray + 0.022), lid, mat, rot_x=math.radians(-100), pivot=(cx, y1 - 0.004, z + tray))
    for i in range(3):
        for j in range(2):
            ex = x0 + (i + 0.5) * (x1 - x0) / 3
            ey = y0 + 0.04 + j * (y1 - y0 - 0.08)
            egg = M["egg_brown"] if (i + j) % 3 else M["egg_cream"]
            open_eggs.ellipsoid((ex, ey, z + tray + 0.012), (0.021, 0.021, 0.029), egg)


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

    frame, goods, eggs = MeshBuilder(), MeshBuilder(), MeshBuilder()
    bx0, bx1 = span(0.0, width)
    # Back panel, outer side panel, canopy with a warm light strip, recessed kick plate.
    frame.box((bx0, SHELF_DEPTH - 0.03, 0.12), (bx1, SHELF_DEPTH, h - 0.06), M["shelf"])
    sx0, sx1 = span(0.0, 0.04)
    frame.box((sx0, 0.0, 0.0), (sx1, SHELF_DEPTH, h), M["shelf"])
    frame.box((bx0, -0.05, h - 0.08), (bx1, SHELF_DEPTH, h), M["accent"])
    frame.box((bx0, 0.0, h - 0.1), (bx1, 0.04, h - 0.08), M["shelf_light"])
    frame.box((bx0, 0.03, 0.0), (bx1, SHELF_DEPTH, 0.12), M["accent"])
    # Hinge barrel on the pivot, with plates.
    frame.cylinder((0.0, 0.0, 0.1), 0.02, h - 0.2, props.M["metal_dark"], segments=10)
    for z in (0.25, h / 2, h - 0.35):
        px0, px1 = span(0.0, 0.08)
        frame.box((px0, -0.005, z), (px1, 0.005, z + 0.12), props.M["metal_dark"])

    levels = (0.12, 0.6, 1.08, 1.56)
    for level, z in enumerate(levels):
        frame.box((bx0, 0.0, z), (bx1, SHELF_DEPTH - 0.03, z + 0.025), M["shelf"])
        frame.box((bx0, -0.012, z - 0.035), (bx1, 0.012, z + 0.03), props.M["rail"])
        for i in range(5):
            tx0, tx1 = span(0.12 + i * 0.28, 0.2 + i * 0.28)
            frame.box((tx0, -0.016, z - 0.03), (tx1, -0.012, z + 0.02), props.M["tag"])
        for i in range(5):
            cx0, cx1 = span(0.08 + i * 0.28, 0.08 + i * 0.28 + 0.24)
            mat = M["carton"] if (i + level) % 2 == 0 else M["carton_alt"]
            # Eye-level shelf: two open cartons per door show the eggs.
            is_open = level == 2 and i in (1, 3)
            carton(goods, cx0, cx1, 0.05, 0.33, z + 0.025, mat, eggs if is_open else None)
            if not is_open:
                carton(goods, cx0, cx1, 0.05, 0.33, z + 0.025 + 0.12, mat, None)

    door = bevel(frame.build(f"DOOR_EGGS_{name}", parent=hinge), 0.006)
    # Large faces whose four corners touch the canopy and kick plate: per-vertex occlusion would
    # darken the whole panel (the door's outer face turns to face the aisle when it opens).
    door["ao_skip"] = True
    bevel(goods.build(f"DOOR_EGGS_{name}_GOODS", parent=door), 0.003)
    eggs.build(f"DOOR_EGGS_{name}_EGGS", parent=door)
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
    bevel(box("SIGN_EGGS", (-0.9, HALF_Y - 0.03, 2.45), (0.9, HALF_Y, 2.95), M["sign"], shelf), 0.008)
    # « Scannable » pictogram next to the sign (docs/GDD.md §06.0), drawn at runtime too.
    bevel(box("PICTO_SCAN_EGGS", (1.0, HALF_Y - 0.03, 2.5), (1.4, HALF_Y, 2.9), M["sign"], shelf), 0.008)


def parvis(root) -> None:
    """Forecourt outside the entrance (docs/GDD.md §03.10, §09). Volunteers stand aside the
    walkway; none blocks the way out. No logo, no organisation name: leaflets are blank."""
    south = -HALF_Y - WALL
    plaza = empty("PARVIS_ROOT", (0.0, 0.0, 0.0), root)
    box("PARVIS_GROUND", (-40.0, -80.0, -0.7), (40.0, south, -0.62), M["grass"], plaza)
    box("PARVIS_SLAB", (-14.0, -30.0, -0.6), (14.0, south, 0.0), M["paving"], plaza)
    outside.paving(-13.4, -29.4, 13.4, south - 0.05, plaza)

    outside.facade(HALF_X, HALF_Y, WALL, HEIGHT, ENTRANCE_HALF_W, root)
    outside.canopy(HALF_Y, WALL, root)

    edges = {
        "W": ((-14.0, -30.0), (-13.4, south)),
        "E": ((13.4, -30.0), (14.0, south)),
        "S": ((-14.0, -30.0), (14.0, -29.4)),
    }
    for key, ((x0, y0), (x1, y1)) in edges.items():
        bevel(box(f"PARVIS_PLANTER_{key}", (x0, y0, 0.0), (x1, y1, 0.55), M["planter"], plaza), 0.02)
        helper_volume(box(f"COL_PARVIS_{key}", (x0, y0, 0.0), (x1, y1, 1.2), None, plaza))
    outside.planter_greenery([(x0, y0, x1, y1) for (x0, y0), (x1, y1) in edges.values()], plaza)

    trees = MeshBuilder()
    for k, (x, y) in enumerate(((-13.7, -14.0), (-13.7, -22.0), (13.7, -14.0), (13.7, -22.0), (-6.0, -29.7), (6.0, -29.7))):
        land.tree(trees, x, y, 0.5, "round", 900 + k)
    trees.build("PARVIS_TREES", parent=plaza)

    outside.street_furniture(plaza)
    outside.stand(-7.6, -21.0, -4.4, -20.2, plaza)

    # Facing the walkway: +X for the west side, -X for the east side (built facing +Y).
    outside.volunteer("VOLUNTEER_01", -3.6, -13.0, -math.pi / 2, 0, plaza)
    outside.volunteer("VOLUNTEER_02", 3.9, -14.5, math.pi / 2, 1, plaza)
    outside.volunteer("VOLUNTEER_03", -6.0, -19.4, -math.pi / 2 + 0.3, 2, plaza)
    # Two more hold a banner on the east side, facing the store: seen straight ahead on the way
    # out, clear of the walkway. Poles stand 0.25 m inside each person, 0.3 m in front of them.
    banner_y = -20.5
    outside.volunteer("VOLUNTEER_04", 3.9, banner_y, 0.0, 3, plaza, pose="banner", pole_x=0.25)
    outside.volunteer("VOLUNTEER_05", 8.1, banner_y, 0.0, 4, plaza, pose="banner", pole_x=-0.25)
    outside.banner("BANNER_PARVIS", 3.9 + 0.25, 8.1 - 0.25, banner_y + 0.3, 0.95, 2.2, plaza)

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
    from beef_store import beef_shelf
    beef_shelf(root, M)
    parvis(root)
    save_blend(os.path.abspath(argv[0]))


main()
