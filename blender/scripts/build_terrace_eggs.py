"""Blockout of the eggs terrace module: elevated terrace, laying-hen house, road, packing centre.

Usage (headless):
  Blender -b --factory-startup -P blender/scripts/build_terrace_eggs.py -- <out.blend>

Local frame (metres, Z up): the origin is the threshold, i.e. the back face of the store
wall at floor level, where the runtime places it on ANCHOR_EGGS_TERRACE. The terrace extends
towards +Y. Distances to the buildings are compressed on purpose (docs/TECH.md §06:
« représentation schématique »); the layout states no fact about real installations.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from common import MeshBuilder, box, empty, helper_volume, material, reset_scene, save_blend  # noqa: E402

TERRACE_HALF_W, TERRACE_DEPTH = 6.0, 7.0
RAIL_H = 1.05
GROUND_Z = -24.0
# The store sits on a plinth; in this frame the store spans Y ∈ [-18.9, 0].
STORE_HALF_W, STORE_BACK_Y = 12.3, -18.9
HOUSE_HALF_L, HOUSE_H = 35.0, 4.0

M = {}


def materials() -> None:
    # Palette from docs/DA.md §03: terrace concrete and blue-grey, farm warm grey and
    # desaturated ochre, plant steel and slate.
    M["slab"] = material("M_TERRACE_CONCRETE", "#D5D2CB", roughness=0.85)
    M["plinth"] = material("M_TERRACE_FACADE", "#B9BFC2", roughness=0.9)
    M["rail"] = material("M_RAIL_METAL", "#8F969A", roughness=0.4, metallic=0.6)
    M["rail_panel"] = material("M_RAIL_PANEL", "#C9D3D6", roughness=0.2, metallic=0.1)
    M["ground"] = material("M_GROUND_FIELDS", "#9FA083", roughness=1.0)
    M["road"] = material("M_ROAD", "#8A8A86", roughness=0.9)
    M["farm"] = material("M_FARM_WALL", "#B9AF9D", roughness=0.85)
    M["farm_floor"] = material("M_FARM_FLOOR", "#8C857A", roughness=0.95)
    M["placeholder"] = material("M_PLACEHOLDER", "#D8D2C4", roughness=0.9)
    M["placeholder_alt"] = material("M_PLACEHOLDER_ALT", "#A8B3B8", roughness=0.8)
    M["farm_roof"] = material("M_FARM_ROOF", "#7F7A72", roughness=0.7, metallic=0.2)
    M["plant"] = material("M_PLANT_WALL", "#C7CCD1", roughness=0.6, metallic=0.2)
    M["plant_roof"] = material("M_PLANT_ROOF", "#7C838A", roughness=0.6, metallic=0.3)


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
        b.box((x0, y0, 0.1), (x1, y1, RAIL_H - 0.08), M["rail_panel"])
        b.box((x0 - 0.02, y0 - 0.02, RAIL_H - 0.06), (x1 + 0.02, y1 + 0.02, RAIL_H), M["rail"])
        # Posts every 1.5 m make the guardrail readable at a glance.
        along_x = (x1 - x0) > (y1 - y0)
        length = (x1 - x0) if along_x else (y1 - y0)
        for i in range(int(length / 1.5) + 1):
            t = min(i * 1.5, length - 0.06)
            px, py = (x0 + t, y0) if along_x else (x0, y0 + t)
            b.box((px - 0.01, py - 0.01, 0.0), (px + 0.07, py + 0.07, RAIL_H - 0.06), M["rail"])
        b.build(f"TERRACE_RAIL_{key}", parent=root)
        helper_volume(box(f"COL_RAIL_{key}", (x0, y0, 0.0), (x1, y1, RAIL_H), None, root))

    empty("ANCHOR_EGGS_VIEW", (0.0, TERRACE_DEPTH - 0.8, 0.0), root)


def landscape(root) -> None:
    box("GROUND_EGGS", (-250.0, -100.0, GROUND_Z - 0.2), (250.0, 400.0, GROUND_Z), M["ground"], root)

    roads = MeshBuilder()
    z0, z1 = GROUND_Z, GROUND_Z + 0.05
    for (x0, y0), (x1, y1) in (
        ((HOUSE_HALF_L, 32.0), (78.0, 38.0)),  # henhouses → east
        ((72.0, 32.0), (78.0, 100.0)),  # east → packing centre
        ((18.0, 108.0), (60.0, 114.0)),  # packing centre → west
        ((18.0, -5.0), (24.0, 114.0)),  # west → beside the store
    ):
        roads.box((x0, y0, z0), (x1, y1, z1), M["road"])
    roads.build("ROAD_EGGS", parent=root)


def hollow_house(name: str, y0: float, y1: float, root):
    """Long building with thin walls and an open top, so its inside shows once the roof goes."""
    x0, x1, z0, z1, t = -HOUSE_HALF_L, HOUSE_HALF_L, GROUND_Z, GROUND_Z + HOUSE_H, 0.25
    b = MeshBuilder()
    b.box((x0, y0, z0), (x1, y0 + t, z1), M["farm"])
    b.box((x0, y1 - t, z0), (x1, y1, z1), M["farm"])
    b.box((x0, y0, z0), (x0 + t, y1, z1), M["farm"])
    b.box((x1 - t, y0, z0), (x1, y1, z1), M["farm"])
    b.box((x0, y0, z0), (x1, y1, z0 + 0.1), M["farm_floor"])
    return b.build(name, parent=root)


def buildings(root) -> None:
    # Laying-hen houses: repeated long volumes (docs/DA.md §06). The near one opens on reveal.
    # Close and low enough that, from the guardrail, the near wall hides little of the inside.
    near_y0, near_y1 = 26.0, 42.0
    hollow_house("BUILDING_EGGS_FARM", near_y0, near_y1, root)
    roof_z = GROUND_Z + HOUSE_H
    # Roof as its own object, origin at its centre, so it can be lifted or faded.
    box("ROOF_EGGS", (-HOUSE_HALF_L - 0.6, near_y0 - 0.6, roof_z), (HOUSE_HALF_L + 0.6, near_y1 + 0.6, roof_z + 0.5), M["farm_roof"], root)
    interior(root, near_y0, near_y1)
    empty("ANCHOR_EGGS_FOCUS", (0.0, (near_y0 + near_y1) / 2, GROUND_Z + 1.0), root)

    far = hollow_house("BUILDING_EGGS_FARM_2", 50.0, 66.0, root)
    box("BUILDING_EGGS_FARM_2_ROOF", (-HOUSE_HALF_L - 0.6, 49.4, roof_z), (HOUSE_HALF_L + 0.6, 66.6, roof_z + 0.5), M["farm_roof"], far)

    plant = box("PACKING_EGGS_CENTER", (60.0, 100.0, GROUND_Z), (95.0, 125.0, GROUND_Z + 8.0), M["plant"], root)
    box("PACKING_EGGS_ROOF", (59.5, 99.5, GROUND_Z + 8.0), (95.5, 125.5, GROUND_Z + 8.4), M["plant_roof"], plant)


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
    save_blend(os.path.abspath(argv[0]))


main()
