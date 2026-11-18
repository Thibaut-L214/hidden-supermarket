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
import lowpoly as lp  # noqa: E402
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
    ((HOUSE_HALF_L + 4.0, 35.0), (170.0, 35.0), 6.0),  # egg room dock → east, out of the farm
    ((75.0, 32.0), (75.0, 100.0), 6.0),  # → packing centre (joins the road above)
    ((46.0, 111.0), (60.0, 111.0), 6.0),  # packing centre → west
    ((49.0, 8.0), (49.0, 114.0), 6.0),  # down the east side of the farm, clear of the parked trucks
    ((14.0, 11.0), (49.0, 11.0), 6.0),  # → in front of the store
    ((HOUSE_HALF_L + 4.0, 28.0), (49.0, 28.0), 6.0),  # apron south of the egg room (animal truck) → joins x = 49
]
# Five long houses of the same footprint in a row (docs/DA.md §06: repeated long volumes); only
# the nearest opens. They differ the way sheds of different ages do: tone of the sheets, number
# of wall fans and ridge vents. (y0, y1, tone, wall fans a side, ridge vents)
HOUSE_ROWS = [(26.0, 42.0, 1.0, 7, 5), (50.0, 66.0, 0.95, 6, 0), (74.0, 90.0, 1.0, 7, 6), (98.0, 114.0, 0.9, 8, 0), (122.0, 138.0, 0.97, 7, 4)]
FENCE = (-48.0, 20.0, 40.5, 140.0)
FARM_COMPOUND = (-50.0, 18.0, 42.0, 142.0)
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
    M["plant_flat"] = material("M_PLANT_ROOF_FLAT", "#8E9499", roughness=0.9)
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
    # Rough grass left under the fence, bare compacted ground inside the farm and the yard.
    fx0, fy0, fx1, fy1 = FENCE
    bands = [(fx0 - 0.9, fy0 - 0.9, fx1 + 0.9, fy0 + 0.9), (fx0 - 0.9, fy1 - 0.9, fx1 + 0.9, fy1 + 0.9),
             (fx0 - 0.9, fy0, fx0 + 0.9, fy1), (fx1 - 0.9, fy0, fx1 + 0.9, 24.0), (fx1 - 0.9, 41.0, fx1 + 0.9, fy1)]
    # Concrete service strips: along the east ends of the houses, and under the silos.
    lanes = [(HOUSE_HALF_L, 22.0, HOUSE_HALF_L + 4.5, 140.0), (-HOUSE_HALF_L - 6.5, 24.0, -HOUSE_HALF_L, 140.0)]
    terrain.build("TERRAIN_EGGS", (-250.0, -100.0, 250.0, 400.0), 5.0, (45.0, 55.0), root,
                  yards=[FARM_COMPOUND, PACKING_YARD], bands=bands, lanes=lanes, roads=ROADS)

    # Dashes follow the centre of every road except the short apron spur; none cross a junction.
    land.roads("ROAD_EGGS", ROADS, GROUND_Z, M["road"], root, dashed=[True] * (len(ROADS) - 1) + [False])

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
    def crosses_road(seg) -> bool:
        (ax, ay), (bx, by) = seg
        return any(
            min(ax, bx) <= x1 + 4.0 and max(ax, bx) >= x0 - 4.0 and min(ay, by) <= y1 + 4.0 and max(ay, by) >= y0 - 4.0
            for x0, y0, x1, y1 in road_rects
        )

    def between_fields(seg) -> bool:
        (ax, ay), (bx, _) = seg
        fx, fy = round((ax + 1000.0) / 45.0), round((ay + 1000.0) / 55.0)
        return land.is_field_boundary((fx - 1, fy), (fx, fy)) if ax == bx else land.is_field_boundary((fx, fy - 1), (fx, fy))

    # No hedge across a road (the farm's roads leave the scene to the east), none inside a field.
    hedges = [h for h in hedges if not crosses_road(h) and between_fields(h)]
    rows = [
        ((55.0, 16.0), (55.0, 26.0), "poplar"),
        ((55.0, 44.0), (55.0, 104.0), "poplar"),
        ((50.0, 117.0), (60.0, 117.0), "round"),
        ((18.0, 17.0), (43.0, 17.0), "round"),
    ]
    groves = [
        (-90.0, 40.0, 12), (-130.0, 120.0, 15), (120.0, 60.0, 12), (140.0, 180.0, 14), (-60.0, 170.0, 10),
        (20.0, 200.0, 12), (-170.0, -20.0, 10), (180.0, -40.0, 10), (90.0, 250.0, 14), (-110.0, 260.0, 12),
    ]
    land.vegetation("LAND_EGGS", terrain, rows, groves, hedges, root)

    # The fence is open on the east side where the apron roads leave the farm.
    land.perimeter_fence("FENCE_EGGS_FARM", FENCE, [(40.0, 25.0, 41.0, 40.0)], GROUND_Z, root)
    land.power_line("POWER_LINE_EGGS", terrain, [(210.0, 140.0), (150.0, 120.0), (103.0, 118.0), (103.0, 82.0), (84.0, 48.0), (41.5, 46.0)], root)

    land.hills("HILLS_EGGS", [(-180.0, 330.0, 90.0, 26.0), (60.0, 380.0, 120.0, 30.0), (220.0, 300.0, 80.0, 22.0)], GROUND_Z - 0.5, M["hill"], root)


def hollow_house(name: str, y0: float, y1: float, root, tone: float, fans: int):
    """Long building with thin walls and an open top, so its inside shows once the roof goes.
    The wall boxes give the inner and top faces; the weathered outer faces come with the cladding."""
    x0, x1, z0, z1, t = -HOUSE_HALF_L, HOUSE_HALF_L, GROUND_Z, GROUND_Z + HOUSE_H, 0.25
    b = MeshBuilder(recalc_normals=False)
    b.box((x0, y0, z0), (x1, y0 + t, z1), M["farm"], skip=("-z", "-y"))
    b.box((x0, y1 - t, z0), (x1, y1, z1), M["farm"], skip=("-z", "+y"))
    b.box((x0, y0, z0), (x0 + t, y1, z1), M["farm"], skip=("-z", "-x"))
    b.box((x1 - t, y0, z0), (x1, y1, z1), M["farm"], skip=("-z", "+x"))
    b.box((x0, y0, z0), (x1, y1, z0 + 0.1), M["farm_floor"], skip=("-z",))
    # Service door at the east end, towards the egg room and the dock.
    b.box((x1, (y0 + y1) / 2 - 1.5, z0), (x1 + 0.1, (y0 + y1) / 2 + 1.5, z0 + 3.0), M["fan"], skip=("-z", "-x"))
    house = b.build(name, parent=root)
    props.house_structure(f"{name}_STRUCTURE", x0, x1, y0, y1, z0, HOUSE_H, 2.2 + 0.3, house)
    props.house_cladding(f"{name}_CLADDING", x0, x1, y0, y1, z0, HOUSE_H, house, wall_mat=M["farm"], seed=1, tone=tone, fans=fans)
    return house


def buildings(root) -> None:
    # Laying-hen houses: repeated long volumes (docs/DA.md §06). The near one opens on reveal.
    # Close and low enough that, from the guardrail, the near wall hides little of the inside.
    near_y0, near_y1, near_tone, near_fans, near_vents = HOUSE_ROWS[0]
    hollow_house("BUILDING_EGGS_FARM", near_y0, near_y1, root, near_tone, near_fans)
    roof_z = GROUND_Z + HOUSE_H
    x0, x1 = -HOUSE_HALF_L, HOUSE_HALF_L
    # Roof as its own object, origin at the centre of its eaves, so it can be lifted or faded.
    props.shed_roof("ROOF_EGGS", x0 - 0.6, x1 + 0.6, near_y0 - 0.6, near_y1 + 0.6, roof_z, roof_z + 0.3, 2.2, M["farm_roof"], root,
                    seed=11, tone=near_tone, vents=near_vents, centred=True)
    props.egg_room("EGG_ROOM_EGGS", HOUSE_HALF_L, 37.5, 42.0, GROUND_Z, root)
    interior(root, near_y0, near_y1)
    empty("ANCHOR_EGGS_FOCUS", (0.0, (near_y0 + near_y1) / 2, GROUND_Z + 1.0), root)

    # The other houses stay closed, so they are shells: outer walls and roofs, merged into two
    # meshes for the whole row. Their north faces can never be seen from the terrace.
    silo_ys = [30.0, 36.0]
    row, roofs = MeshBuilder(recalc_normals=False), MeshBuilder(recalc_normals=False)
    for n, (y0, y1, tone, fans, vents) in enumerate(HOUSE_ROWS[1:], start=2):
        props.house_cladding("", x0, x1, y0, y1, GROUND_Z, HOUSE_H, None, wall_mat=M["farm"], seed=n * 17, tone=tone, fans=fans, hidden_north=True, builder=row)
        row.box((x1, (y0 + y1) / 2 - 1.5, GROUND_Z), (x1 + 0.1, (y0 + y1) / 2 + 1.5, GROUND_Z + 3.0), M["fan"], skip=("-z", "-x"))
        props.shed_roof("", x0 - 0.6, x1 + 0.6, y0 - 0.6, y1 + 0.6, roof_z, roof_z + 0.3, 2.2, M["farm_roof"], None, seed=n * 29, tone=tone, vents=vents, builder=roofs)
        silo_ys += [y0 + 4.0, y0 + 10.0]
    row.build("BUILDING_EGGS_FARM_ROW", parent=root)
    # Named like a single house's roof for the lightmap profile (roofs are left out of the bake).
    roofs.build("BUILDING_EGGS_FARM_2345_ROOF", parent=root)["ao_skip"] = True

    # Feed silos at the west end of every house.
    props.silos("SILOS_EGGS", [(-HOUSE_HALF_L - 4.0, y) for y in silo_ys], -HOUSE_HALF_L, GROUND_Z, root)

    # Framing and information anchors: the whole row from the terrace, the cages, the repetition.
    empty("ANCHOR_EGGS_WIDE", (0.0, 84.0, GROUND_Z + 2.0), root)
    empty("ANCHOR_EGGS_MARK_CAGES", (-14.0, (near_y0 + near_y1) / 2, GROUND_Z + 3.4), root)
    empty("ANCHOR_EGGS_MARK_SITE", (-24.0, 106.0, GROUND_Z + 6.5), root)

    packing_centre(root)


def packing_centre(root) -> None:
    """Packing centre (docs/DA.md §03: steel, slate, cold white): insulated panel walls with
    rain streaks under the parapet, flat roof with plant, loading docks under canopies."""
    px0, py0, px1, py1, top = 60.0, 100.0, 95.0, 125.0, GROUND_Z + 8.0
    shell = MeshBuilder(recalc_normals=False)
    for a, c, normal, seed in (((px0, py0), (px1, py0), (0, -1), 3), ((px1, py0), (px1, py1), (1, 0), 5), ((px1, py1), (px0, py1), (0, 1), 7), ((px0, py1), (px0, py0), (-1, 0), 9)):
        props.clad_wall(shell, a, c, GROUND_Z + 0.5, top, normal, M["plant"], seed, spacing=3.0)
    # Flat roof behind a parapet, mottled by standing water and dust.
    lp.panel(shell, (px0, py0, top - 0.25), (px1 - px0, 0.0, 0.0), (0.0, py1 - py0, 0.0), (7, 5), M["plant_flat"],
             lambda s, t: lp.scale(lp.WHITE, 0.82 + 0.18 * lp.rand(int(s * 7), int(t * 5), 3)))
    shell.build("PACKING_EGGS_CENTER", parent=root)

    details = MeshBuilder(recalc_normals=False)
    cap = props.M["trim"]
    for lo, hi in (((px0 - 0.1, py0 - 0.1), (px1 + 0.1, py0 + 0.2)), ((px0 - 0.1, py1 - 0.2), (px1 + 0.1, py1 + 0.1)),
                   ((px0 - 0.1, py0 - 0.1), (px0 + 0.2, py1 + 0.1)), ((px1 - 0.2, py0 - 0.1), (px1 + 0.1, py1 + 0.1))):
        details.box((lo[0], lo[1], top - 0.25), (hi[0], hi[1], top + 0.12), cap, skip=("-z",))
    # Plinth course, downpipes at the corners of the long faces.
    details.box((px0 - 0.06, py0 - 0.06, GROUND_Z), (px1 + 0.06, py1 + 0.06, GROUND_Z + 0.5), props.M["base"], skip=("-z",))
    for x, y in ((px0 + 0.4, py0 - 0.1), (px1 - 0.4, py0 - 0.1), (px1 + 0.1, py0 + 0.4), (px1 + 0.1, py1 - 0.4), ((px0 + px1) / 2, py0 - 0.1)):
        props.downpipe(details, x, y, GROUND_Z, top)
    # Rooftop plant: air handling units and a run of duct.
    for k, (ux, uy) in enumerate(((68.0, 108.0), (76.0, 108.0), (84.0, 116.0))):
        details.box((ux - 1.4, uy - 1.0, top - 0.25), (ux + 1.4, uy + 1.0, top + 0.95), props.M["fan_housing"], skip=("-z",))
        lp.quad(details, ((ux - 1.0, uy - 0.7, top + 0.96), (ux + 1.0, uy - 0.7, top + 0.96), (ux + 1.0, uy + 0.7, top + 0.96), (ux - 1.0, uy + 0.7, top + 0.96)), props.M["grill"])
    details.box((68.0, 111.5, top - 0.25), (84.0, 112.1, top + 0.3), props.M["trim"], skip=("-z",))
    # Loading docks: inbound on the south face, outbound on the west face, under canopies.
    props.dock_doors(
        details,
        [((68.0 + i * 6.0, 100.0, 3.2), "south") for i in range(3)] + [((60.0, 106.0 + i * 6.0, 3.2), "west") for i in range(2)],
        GROUND_Z,
    )
    details.box((64.0, 96.0, GROUND_Z + 4.4), (88.0, 100.0, GROUND_Z + 4.7), M["plant_roof"])
    details.box((56.0, 104.0, GROUND_Z + 4.4), (60.0, 118.0, GROUND_Z + 4.7), M["plant_roof"])
    for x, y in ((64.3, 96.3), (76.0, 96.3), (87.7, 96.3), (56.3, 104.3), (56.3, 117.7)):
        details.box((x - 0.08, y - 0.08, GROUND_Z), (x + 0.08, y + 0.08, GROUND_Z + 4.4), props.M["trim"], skip=("-z", "+z"))
    props.forklift(details, 57.5, 119.5, GROUND_Z)
    details.build("PACKING_EGGS_DETAILS", parent=root)
    # Office annex, lower and lighter.
    annex = MeshBuilder(recalc_normals=False)
    for a, c, normal, seed in (((95.0, 112.0), (103.0, 112.0), (0, -1), 21), ((103.0, 112.0), (103.0, 124.0), (1, 0), 23), ((103.0, 124.0), (95.0, 124.0), (0, 1), 25)):
        props.clad_wall(annex, a, c, GROUND_Z, GROUND_Z + 4.5, normal, M["plant_annex"], seed, spacing=3.0)
    annex.box((94.9, 111.9, GROUND_Z + 4.5), (103.1, 124.1, GROUND_Z + 4.65), props.M["trim"], skip=("-z",))
    for k in range(3):
        annex.box((96.5 + k * 2.2, 111.96, GROUND_Z + 1.6), (98.0 + k * 2.2, 112.0, GROUND_Z + 3.0), props.M["window"], skip=("+y",))
    annex.build("PACKING_EGGS_ANNEX", parent=root)


def interior(root, y0: float, y1: float) -> None:
    """Laying hens in stacked cages (docs/DECISIONS.md, « Poules »): a schematic depiction of
    one housing type chosen by the editorial team, not a documented installation. Cage frames
    are INTERIOR_EGGS; the hens are HENS_EGGS_NN, hidden by the runtime until the roof is off."""
    hens = empty("HENS_EGGS", (0.0, 0.0, 0.0), root)
    usable = HOUSE_HALF_L - 4.5
    props.battery_cages("INTERIOR_EGGS", -usable, usable, y0 + 0.4, y1 - 0.4, GROUND_Z + 0.1, root, hens)


def path(route: str, points, parent) -> None:
    """Ordered empties PATH_<route>_<NN>; glTF has no curves, the runtime rebuilds a spline."""
    for i, (x, y) in enumerate(points):
        empty(f"PATH_EGGS_{route}_{i:02d}", (x, y, GROUND_Z + land.ROAD_TOP), parent)


def logistics(root) -> None:
    """Schematic flow (docs/GDD.md §06.4): at the henhouse, hens in crates are loaded onto an
    animal transport truck that leaves the farm; eggs are collected in crates, taken by truck to
    the packing centre, and packed goods go by truck towards the store. Where the hens are going
    is not shown (TODO_SOURCE)."""
    # Road surface: trucks, loads on the dock and path points stand on it.
    g = GROUND_Z + land.ROAD_TOP
    east = HOUSE_HALF_L
    box("DOCK_EGGS_FARM", (east, 29.0, GROUND_Z), (east + 4.0, 37.0, g), M["road"], root)
    # Units are pallets: crates stacked on pallets read at the terrace's distance.
    props.unit_group("CRATES_EGGS_COLLECT", (east + 0.4, 33.2, g), [(x, y) for y in range(3) for x in range(2)], props.crate_pallet, root, step=(1.3, 1.5))
    props.unit_group("CARTONS_EGGS_PACKED", (54.0, 101.0, g), [(x, y) for y in range(2) for x in range(2)], props.carton_pallet, root, step=(1.3, 1.5))
    # Hen crates wait by the henhouse's service door, then travel to the truck's deck.
    props.unit_group("HENCRATES_EGGS_HALL", (east + 0.5, 26.8, g), [(x, y) for y in range(4) for x in range(2)], props.hen_module, root, step=(0.95, 0.8))

    props.truck("TRUCK_EGGS_FARM", "CARGO_EGGS_FARM", props.crate_pallet, props.M["cab_farm"], (east + 6.0, 35.0, g), root)
    props.truck(
        "TRUCK_EGGS_ANIMALS", "HENCRATES_EGGS_TRUCK", props.hen_module, props.M["cab_farm"], (east + 7.0, 28.0, g), root,
        cells=[(x, y) for y in range(4) for x in range(2)], step=(1.1, 1.3), slats=True,
    )
    props.truck("TRUCK_EGGS_DELIVERY", "CARGO_EGGS_DELIVERY", props.carton_pallet, props.M["cab_delivery"], (57.0, 111.0, g), root)

    path("ANIMALS", [(east + 7.0, 28.0), (46.0, 28.2), (48.0, 30.4), (49.6, 33.4), (52.5, 35.0), (62.0, 35.0), (100.0, 35.0), (170.0, 35.0)], root)
    path("FARM", [(east + 6.0, 35.0), (56.0, 35.0), (72.0, 35.5), (75.0, 40.0), (75.0, 70.0), (75.0, 96.0)], root)
    path(
        "DELIVERY",
        [(57.0, 111.0), (51.0, 111.0), (49.0, 104.0), (49.0, 60.0), (49.0, 22.0), (48.0, 13.0), (32.0, 11.0), (17.0, 11.0)],
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
