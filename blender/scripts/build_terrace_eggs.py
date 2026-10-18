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
GROUND_Z = -14.0
# The store sits on a plinth; in this frame the store spans Y ∈ [-18.9, 0].
STORE_HALF_W, STORE_BACK_Y = 12.3, -18.9

M = {}


def materials() -> None:
    # Palette from docs/DA.md §03: terrace concrete and blue-grey, farm warm grey and
    # desaturated ochre, plant steel and slate.
    M["slab"] = material("M_TERRACE_CONCRETE", "#D5D2CB", roughness=0.85)
    M["plinth"] = material("M_TERRACE_FACADE", "#B9BFC2", roughness=0.9)
    M["rail"] = material("M_RAIL_METAL", "#8F969A", roughness=0.4, metallic=0.6)
    M["rail_panel"] = material("M_RAIL_PANEL", "#C9D3D6", roughness=0.2, metallic=0.1)
    M["ground"] = material("M_GROUND_FIELDS", "#B3AC95", roughness=1.0)
    M["road"] = material("M_ROAD", "#8A8A86", roughness=0.9)
    M["farm"] = material("M_FARM_WALL", "#A39C8E", roughness=0.85)
    M["farm_roof"] = material("M_FARM_ROOF", "#8E8A82", roughness=0.7, metallic=0.2)
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
        b.build(f"TERRACE_RAIL_{key}", parent=root)
        helper_volume(box(f"COL_RAIL_{key}", (x0, y0, 0.0), (x1, y1, RAIL_H), None, root))

    empty("ANCHOR_EGGS_VIEW", (0.0, TERRACE_DEPTH - 0.8, 0.0), root)


def landscape(root) -> None:
    box("GROUND_EGGS", (-250.0, -100.0, GROUND_Z - 0.2), (250.0, 400.0, GROUND_Z), M["ground"], root)

    roads = MeshBuilder()
    z0, z1 = GROUND_Z, GROUND_Z + 0.05
    for (x0, y0), (x1, y1) in (
        ((40.0, 44.0), (78.0, 50.0)),  # farm → east
        ((72.0, 44.0), (78.0, 100.0)),  # east → packing centre
        ((18.0, 108.0), (72.0, 114.0)),  # packing centre → west
        ((18.0, -5.0), (24.0, 114.0)),  # west → beside the store
    ):
        roads.box((x0, y0, z0), (x1, y1, z1), M["road"])
    roads.build("ROAD_EGGS", parent=root)


def buildings(root) -> None:
    # Laying-hen house: long, repeated volume (docs/DA.md §06). Interior comes with the reveal.
    farm_lo, farm_hi = (-60.0, 38.0, GROUND_Z), (40.0, 56.0, GROUND_Z + 6.0)
    box("BUILDING_EGGS_FARM", farm_lo, farm_hi, M["farm"], root)
    # Roof as its own object, origin at its centre, so it can be lifted or faded.
    box("ROOF_EGGS", (-61.0, 37.0, GROUND_Z + 6.0), (41.0, 57.0, GROUND_Z + 6.6), M["farm_roof"], root)

    plant = box("PACKING_EGGS_CENTER", (60.0, 100.0, GROUND_Z), (95.0, 125.0, GROUND_Z + 8.0), M["plant"], root)
    box("PACKING_EGGS_ROOF", (59.5, 99.5, GROUND_Z + 8.0), (95.5, 125.5, GROUND_Z + 8.4), M["plant_roof"], plant)


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
