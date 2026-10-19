"""Blockout of the eggs terrace module: elevated terrace, laying-hen house, road, packing centre.

Usage (headless):
  Blender -b --factory-startup -P blender/scripts/build_terrace_eggs.py -- <out.blend>

Local frame (metres, Z up): the origin is the threshold, i.e. the back face of the store
wall at floor level, where the runtime places it on ANCHOR_EGGS_TERRACE. The terrace extends
towards +Y. Distances to the buildings are compressed on purpose (docs/TECH.md §06:
« représentation schématique »); the layout states no fact about real installations.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import landscape_props as land  # noqa: E402
import terrace_props as props  # noqa: E402
from common import MeshBuilder, bevel, box, empty, helper_volume, material, reset_scene, save_blend  # noqa: E402

TERRACE_HALF_W, TERRACE_DEPTH = 6.0, 7.0
RAIL_H = 1.05
GROUND_Z = -24.0
# The store sits on a plinth; in this frame the store spans Y ∈ [-18.9, 0].
STORE_HALF_W, STORE_BACK_Y = 12.3, -18.9
HOUSE_HALF_L, HOUSE_H = 35.0, 4.0

# Road network (axis-aligned centre lines, width). The delivery route runs east of the
# henhouses (x = 45) and ends in front of the store's plinth, below the terrace.
ROADS = [
    ((HOUSE_HALF_L + 4.0, 35.0), (78.0, 35.0), 6.0),  # egg room dock → east
    ((75.0, 32.0), (75.0, 100.0), 6.0),  # east → packing centre
    ((42.0, 111.0), (60.0, 111.0), 6.0),  # packing centre → west
    ((45.0, 8.0), (45.0, 114.0), 6.0),  # down the east side of the farm
    ((14.0, 11.0), (48.0, 11.0), 6.0),  # → in front of the store
]
FARM_COMPOUND = (-50.0, 18.0, 42.0, 74.0)
PACKING_YARD = (50.0, 92.0, 106.0, 130.0)
# Behind the store, the plateau that carries the forecourt (store GLB, ground at -0.7).
PLATEAU, PLATEAU_Z = (-45.0, -100.0, 45.0, -19.0), -0.8

M = {}


def materials() -> None:
    # Palette from docs/DA.md §03: terrace concrete and blue-grey, farm warm grey and
    # desaturated ochre, plant steel and slate.
    M["slab"] = material("M_TERRACE_CONCRETE", "#D5D2CB", roughness=0.85)
    M["plinth"] = material("M_TERRACE_FACADE", "#B9BFC2", roughness=0.9)
    M["rail"] = material("M_RAIL_METAL", "#8F969A", roughness=0.4, metallic=0.6)
    M["rail_panel"] = material("M_RAIL_PANEL", "#C9D3D6", roughness=0.2, metallic=0.1)
    M["road"] = material("M_ROAD", "#8A8A86", roughness=0.9)
    M["farm"] = material("M_FARM_WALL", "#B9AF9D", roughness=0.85)
    M["farm_floor"] = material("M_FARM_FLOOR", "#8C857A", roughness=0.95)
    M["placeholder"] = material("M_PLACEHOLDER", "#D8D2C4", roughness=0.9)
    M["placeholder_alt"] = material("M_PLACEHOLDER_ALT", "#A8B3B8", roughness=0.8)
    M["farm_roof"] = material("M_FARM_ROOF", "#7F7A72", roughness=0.7, metallic=0.2)
    M["fan"] = material("M_FARM_FAN", "#5C5A55", roughness=0.7)
    M["silo"] = material("M_SILO", "#C8CCCF", roughness=0.4, metallic=0.5)
    M["dock"] = material("M_DOCK_DOOR", "#5F666C", roughness=0.6, metallic=0.3)
    M["plant_annex"] = material("M_PLANT_ANNEX", "#D9DCDF", roughness=0.7)
    M["glass_dark"] = material("M_TRUCK_GLASS", "#2E3438", roughness=0.15, metallic=0.2)
    M["hill"] = material("M_HILL", "#9AA08A", roughness=1.0)
    M["crate"] = material("M_CRATE", "#7E9C88", roughness=0.8)
    M["carton"] = material("M_CARTON", "#D9C9A6", roughness=0.9)
    M["truck_cab"] = material("M_TRUCK_CAB", "#E6E4DE", roughness=0.5, metallic=0.1)
    M["truck_bed"] = material("M_TRUCK_BED", "#8F969A", roughness=0.6, metallic=0.3)
    M["truck_wheel"] = material("M_TRUCK_WHEEL", "#3E4245", roughness=0.9)
    M["plant"] = material("M_PLANT_WALL", "#C7CCD1", roughness=0.6, metallic=0.2)
    M["plant_roof"] = material("M_PLANT_ROOF", "#7C838A", roughness=0.6, metallic=0.3)
    props.materials()
    land.materials()


def terrace(root) -> None:
    box("TERRACE_FLOOR", (-TERRACE_HALF_W, 0.0, -0.3), (TERRACE_HALF_W, TERRACE_DEPTH, 0.0), M["slab"], root)
    box("TERRACE_PLINTH", (-STORE_HALF_W, STORE_BACK_Y, GROUND_Z), (STORE_HALF_W, TERRACE_DEPTH, -0.1), M["plinth"], root)

    rails = {
        "N": ((-TERRACE_HALF_W, TERRACE_DEPTH - 0.1), (TERRACE_HALF_W, TERRACE_DEPTH)),
        "E": ((TERRACE_HALF_W - 0.1, 0.0), (TERRACE_HALF_W, TERRACE_DEPTH)),
        "W": ((-TERRACE_HALF_W, 0.0), (-TERRACE_HALF_W + 0.1, TERRACE_DEPTH)),
    }
    for key, ((x0, y0), (x1, y1)) in rails.items():
        b = MeshBuilder()
        # See-through panel: the guardrail must not hide the view over the farm.
        b.box((x0, y0, 0.1), (x1, y1, RAIL_H - 0.08), props.M["rail_glass"])
        b.box((x0 - 0.02, y0 - 0.02, RAIL_H - 0.06), (x1 + 0.02, y1 + 0.02, RAIL_H), M["rail"])
        # Posts every 1.5 m make the guardrail readable at a glance.
        along_x = (x1 - x0) > (y1 - y0)
        length = (x1 - x0) if along_x else (y1 - y0)
        for i in range(int(length / 1.5) + 1):
            t = min(i * 1.5, length - 0.06)
            px, py = (x0 + t, y0) if along_x else (x0, y0 + t)
            b.box((px - 0.01, py - 0.01, 0.0), (px + 0.07, py + 0.07, RAIL_H - 0.06), M["rail"])
        bevel(b.build(f"TERRACE_RAIL_{key}", parent=root), 0.006)
        helper_volume(box(f"COL_RAIL_{key}", (x0, y0, 0.0), (x1, y1, RAIL_H), None, root))

    empty("ANCHOR_EGGS_VIEW", (0.0, TERRACE_DEPTH - 0.8, 0.0), root)

    # Expansion joints in the slab (flush details stay out of the occlusion bake).
    joints = MeshBuilder()
    for x in (-3.0, 0.0, 3.0):
        joints.box((x - 0.01, 0.0, 0.0), (x + 0.01, TERRACE_DEPTH, 0.004), props.M["base"])
    joints.box((-TERRACE_HALF_W, 3.5 - 0.01, 0.0), (TERRACE_HALF_W, 3.5 + 0.01, 0.004), props.M["base"])
    joints.build("TERRACE_JOINTS", parent=root)["ao_skip"] = True


def landscape(root) -> None:
    """Relief, field patchwork, roads, vegetation, fence and power line (lot 3)."""
    road_rects = [land.road_rect(rd) for rd in ROADS]
    flat = [FARM_COMPOUND, PACKING_YARD, (-STORE_HALF_W, STORE_BACK_Y, STORE_HALF_W, TERRACE_DEPTH)]
    flat += [(x0 - 2.5, y0 - 2.5, x1 + 2.5, y1 + 2.5) for x0, y0, x1, y1 in road_rects]
    terrain = land.Terrain(GROUND_Z, flat, PLATEAU, PLATEAU_Z)
    terrain.build("TERRAIN_EGGS", (-250.0, -100.0, 250.0, 400.0), 5.0, (45.0, 55.0), root)

    land.roads("ROAD_EGGS", ROADS, GROUND_Z, M["road"], root)

    # Hedgerows on some field boundaries (the lattice used for the patchwork).
    hedges = []
    for bx in range(-235, 240, 45):
        for by in range(-65, 390, 55):
            if math.hypot(bx, by - 60) > 230:
                continue
            h = land._hash(bx, by)
            if h % 4 == 0:
                hedges.append(((float(bx), float(by)), (float(bx), float(by + 55))))
            if h % 5 == 1:
                hedges.append(((float(bx), float(by)), (float(bx + 45), float(by))))
    rows = [
        ((52.0, 16.0), (52.0, 26.0), "poplar"),
        ((52.0, 44.0), (52.0, 104.0), "poplar"),
        ((46.0, 117.0), (60.0, 117.0), "round"),
        ((18.0, 17.0), (40.0, 17.0), "round"),
    ]
    groves = [
        (-90.0, 40.0, 12), (-130.0, 120.0, 15), (120.0, 60.0, 12), (140.0, 180.0, 14), (-60.0, 170.0, 10),
        (20.0, 200.0, 12), (-170.0, -20.0, 10), (180.0, -40.0, 10), (90.0, 250.0, 14), (-110.0, 260.0, 12),
    ]
    land.vegetation("LAND_EGGS", terrain, rows, groves, hedges, root)

    land.perimeter_fence("FENCE_EGGS_FARM", (-48.0, 20.0, 40.5, 72.0), [(40.0, 30.0, 41.0, 40.0)], GROUND_Z, root)
    land.power_line("POWER_LINE_EGGS", terrain, [(210.0, 140.0), (150.0, 120.0), (103.0, 118.0), (103.0, 82.0), (84.0, 48.0), (41.5, 46.0)], root)

    hills = MeshBuilder()
    for x, y, rad, h in ((-180.0, 330.0, 90.0, 26.0), (60.0, 380.0, 120.0, 30.0), (220.0, 300.0, 80.0, 22.0)):
        hills.cone((x, y, GROUND_Z - 0.5), rad, h, M["hill"], segments=24)
    hills.build("HILLS_EGGS", parent=root)


def hollow_house(name: str, y0: float, y1: float, root):
    """Long building with thin walls and an open top, so its inside shows once the roof goes."""
    x0, x1, z0, z1, t = -HOUSE_HALF_L, HOUSE_HALF_L, GROUND_Z, GROUND_Z + HOUSE_H, 0.25
    b = MeshBuilder()
    b.box((x0, y0, z0), (x1, y0 + t, z1), M["farm"])
    b.box((x0, y1 - t, z0), (x1, y1, z1), M["farm"])
    b.box((x0, y0, z0), (x0 + t, y1, z1), M["farm"])
    b.box((x1 - t, y0, z0), (x1, y1, z1), M["farm"])
    b.box((x0, y0, z0), (x1, y1, z0 + 0.1), M["farm_floor"])
    # Service door at the east end, towards the egg room and the dock.
    b.box((x1, (y0 + y1) / 2 - 1.5, z0), (x1 + 0.1, (y0 + y1) / 2 + 1.5, z0 + 3.0), M["fan"])
    house = bevel(b.build(name, parent=root), 0.02)
    props.house_structure(f"{name}_STRUCTURE", x0, x1, y0, y1, z0, HOUSE_H, 2.2 + 0.3, house)
    props.house_cladding(f"{name}_CLADDING", x0, x1, y0, y1, z0, HOUSE_H, house)
    return house


def gable_roof(name: str, lo, hi, ridge: float, mat, parent):
    """Pitched roof with closed gables, origin at the centre of its eaves (for lifting)."""
    centre = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])
    local_lo = tuple(a - c for a, c in zip(lo, centre))
    local_hi = tuple(a - c for a, c in zip(hi, centre))
    origin = centre if parent is None else tuple(c - p for c, p in zip(centre, parent.matrix_world.translation))
    return MeshBuilder().gable(local_lo, local_hi, ridge, mat).build(name, origin, parent)


def buildings(root) -> None:
    # Laying-hen houses: repeated long volumes (docs/DA.md §06). The near one opens on reveal.
    # Close and low enough that, from the guardrail, the near wall hides little of the inside.
    near_y0, near_y1 = 26.0, 42.0
    hollow_house("BUILDING_EGGS_FARM", near_y0, near_y1, root)
    roof_z = GROUND_Z + HOUSE_H
    # Roof as its own object, origin at its centre, so it can be lifted or faded.
    roof = gable_roof("ROOF_EGGS", (-HOUSE_HALF_L - 0.6, near_y0 - 0.6, roof_z), (HOUSE_HALF_L + 0.6, near_y1 + 0.6, roof_z + 0.3), 2.2, M["farm_roof"], root)
    # The roof is removed on reveal: it must not darken the structure and interior it covers.
    roof["ao_skip"] = True
    props.egg_room("EGG_ROOM_EGGS", HOUSE_HALF_L, 37.5, 42.0, GROUND_Z, root)
    interior(root, near_y0, near_y1)
    empty("ANCHOR_EGGS_FOCUS", (0.0, (near_y0 + near_y1) / 2, GROUND_Z + 1.0), root)

    far = hollow_house("BUILDING_EGGS_FARM_2", 50.0, 66.0, root)
    gable_roof("BUILDING_EGGS_FARM_2_ROOF", (-HOUSE_HALF_L - 0.6, 49.4, roof_z), (HOUSE_HALF_L + 0.6, 66.6, roof_z + 0.3), 2.2, M["farm_roof"], far)

    # Feed silos at the west end of the henhouses.
    silos = MeshBuilder()
    for i, y in enumerate((30.0, 36.0, 54.0)):
        x = -HOUSE_HALF_L - 4.0
        silos.cylinder((x, y, GROUND_Z + 1.2), 1.6, 6.5, M["silo"], segments=18)
        silos.cone((x, y, GROUND_Z + 7.7), 1.65, 1.4, M["silo"], segments=18)
        for lx, ly in ((-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0), (1.0, 1.0)):
            silos.box((x + lx - 0.08, y + ly - 0.08, GROUND_Z), (x + lx + 0.08, y + ly + 0.08, GROUND_Z + 1.3), M["truck_bed"])
    bevel(silos.build("SILOS_EGGS", parent=root), 0.02)
    props.silo_details("SILOS_EGGS_DETAILS", [(-HOUSE_HALF_L - 4.0, y) for y in (30.0, 36.0, 54.0)], -HOUSE_HALF_L, GROUND_Z, root)

    box("PACKING_EGGS_CENTER", (60.0, 100.0, GROUND_Z), (95.0, 125.0, GROUND_Z + 8.0), M["plant"], root)
    details = MeshBuilder()
    details.box((59.5, 99.5, GROUND_Z + 8.0), (95.5, 125.5, GROUND_Z + 8.4), M["plant_roof"])
    # Loading docks: inbound on the south face, outbound on the west face, under canopies.
    props.dock_doors(
        details,
        [((68.0 + i * 6.0, 100.0, 3.2), "south") for i in range(3)] + [((60.0, 106.0 + i * 6.0, 3.2), "west") for i in range(2)],
        GROUND_Z,
    )
    details.box((64.0, 96.0, GROUND_Z + 4.4), (88.0, 100.0, GROUND_Z + 4.7), M["plant_roof"])
    details.box((56.0, 104.0, GROUND_Z + 4.4), (60.0, 118.0, GROUND_Z + 4.7), M["plant_roof"])
    props.forklift(details, 57.5, 119.5, GROUND_Z)
    # Office annex, lower and lighter.
    details.box((95.0, 112.0, GROUND_Z), (103.0, 124.0, GROUND_Z + 4.5), M["plant_annex"])
    # Absolute coordinates: built under the module root, not under the centred plant box.
    bevel(details.build("PACKING_EGGS_DETAILS", parent=root), 0.015)


def interior(root, y0: float, y1: float) -> None:
    """Deliberately neutral placeholder: the farming system is not chosen yet (TODO_SOURCE).

    Plain long platforms and a cross collection strip at the east end; no cages, perches or
    animals, so nothing here can pass for a documented installation.
    """
    b = MeshBuilder()
    floor_z = GROUND_Z + 0.1
    usable = HOUSE_HALF_L - 3.5
    rows = 3
    pitch = (y1 - y0) / (rows + 1)
    for i in range(1, rows + 1):
        cy = y0 + i * pitch
        b.box((-usable, cy - 1.2, floor_z), (usable, cy + 1.2, floor_z + 0.7), M["placeholder"])
    b.box((usable + 0.8, y0 + 1.0, floor_z), (usable + 2.2, y1 - 1.0, floor_z + 0.9), M["placeholder_alt"])
    b.build("INTERIOR_EGGS", parent=root)


def path(route: str, points, parent) -> None:
    """Ordered empties PATH_<route>_<NN>; glTF has no curves, the runtime rebuilds a spline."""
    for i, (x, y) in enumerate(points):
        empty(f"PATH_EGGS_{route}_{i:02d}", (x, y, GROUND_Z + 0.05), parent)


def logistics(root) -> None:
    """Schematic flow (docs/GDD.md §06.4): collection at the henhouse, crates by truck to the
    packing centre, packed goods by truck towards the store. No animal transport here."""
    g = GROUND_Z + 0.05
    east = HOUSE_HALF_L
    box("DOCK_EGGS_FARM", (east, 29.0, GROUND_Z), (east + 4.0, 37.0, g), M["road"], root)
    # Units are pallets: crates stacked on pallets read at the terrace's distance.
    props.unit_group("CRATES_EGGS_COLLECT", (east + 0.4, 30.0, g), [(x, y) for y in range(3) for x in range(2)], props.crate_pallet, root, step=(1.3, 1.5))
    props.unit_group("CARTONS_EGGS_PACKED", (54.0, 101.0, g), [(x, y) for y in range(2) for x in range(2)], props.carton_pallet, root, step=(1.3, 1.5))

    props.truck("TRUCK_EGGS_FARM", "CARGO_EGGS_FARM", props.crate_pallet, props.M["cab_farm"], (east + 6.0, 35.0, g), root)
    props.truck("TRUCK_EGGS_DELIVERY", "CARGO_EGGS_DELIVERY", props.carton_pallet, props.M["cab_delivery"], (57.0, 111.0, g), root)

    props.road_markings(
        "ROAD_EGGS_MARKINGS",
        [
            ((HOUSE_HALF_L + 4.0, 35.0), (75.0, 35.0)),
            ((75.0, 35.0), (75.0, 100.0)),
            ((45.0, 111.0), (60.0, 111.0)),
            ((45.0, 11.0), (45.0, 111.0)),
            ((14.0, 11.0), (45.0, 11.0)),
        ],
        GROUND_Z + 0.05,
        root,
    )

    path("FARM", [(east + 6.0, 35.0), (56.0, 35.0), (72.0, 35.5), (75.0, 40.0), (75.0, 70.0), (75.0, 96.0)], root)
    path(
        "DELIVERY",
        [(57.0, 111.0), (47.0, 111.0), (45.0, 104.0), (45.0, 60.0), (45.0, 22.0), (44.0, 13.0), (32.0, 11.0), (17.0, 11.0)],
        root,
    )


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: build_terrace_eggs.py -- <out.blend>")
    reset_scene()
    materials()
    root = empty("TERRACE_EGGS_ROOT")
    terrace(root)
    landscape(root)
    buildings(root)
    logistics(root)
    save_blend(os.path.abspath(argv[0]))


main()
