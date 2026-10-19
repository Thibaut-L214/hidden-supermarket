"""Detailed, procedural farm structure and logistics for the eggs terrace (lot 2).

Same method as store_props.py: chamfered parts, credible but stylised, no brand anywhere.
The henhouse interior shows laying hens in stacked cages (docs/DECISIONS.md, « Poules »): a
schematic depiction, not a documented installation, with no figure attached (TODO_SOURCE).
Coordinates are the terrace module's Blender frame (metres, Z up), see build_terrace_eggs.py.
"""

from __future__ import annotations

import math

from common import MeshBuilder, bevel, box, empty, glass, helper_volume, material

M: dict = {}


def materials() -> None:
    M["steel"] = material("M_FRAME_STEEL", "#8E9296", roughness=0.5, metallic=0.5)
    M["rib"] = material("M_CLADDING_RIB", "#ADA492", roughness=0.8)
    M["base"] = material("M_CONCRETE_BASE", "#B4B1A9", roughness=0.9)
    M["grill"] = material("M_FAN_GRILL", "#4A4C4D", roughness=0.6, metallic=0.4)
    M["fan_housing"] = material("M_FAN_HOUSING", "#C4C6C6", roughness=0.5, metallic=0.3)
    M["silo"] = material("M_SILO_DETAIL", "#C8CCCF", roughness=0.4, metallic=0.5)
    M["door"] = material("M_ROLLER_DOOR", "#9EA6AC", roughness=0.6, metallic=0.3)
    M["door_rib"] = material("M_ROLLER_DOOR_RIB", "#868E94", roughness=0.6, metallic=0.3)
    M["window"] = material("M_WINDOW_DARK", "#3A4246", roughness=0.15, metallic=0.2)
    M["annex"] = material("M_FARM_ANNEX", "#C9C1B1", roughness=0.8)
    M["bumper"] = material("M_DOCK_BUMPER", "#2F3133", roughness=0.9)
    M["shelter"] = material("M_DOCK_SHELTER", "#3E4347", roughness=0.9)
    M["pallet"] = material("M_PALLET_WOOD", "#B79C78", roughness=0.9)
    M["crate"] = material("M_EGG_CRATE", "#7E9C88", roughness=0.7)
    M["crate_slot"] = material("M_EGG_CRATE_SLOT", "#4D6355", roughness=0.8)
    M["wrap"] = material("M_PALLET_WRAP", "#E2DCCB", roughness=0.4)
    M["wrap_band"] = material("M_PALLET_WRAP_BAND", "#C7BB9E", roughness=0.6)
    M["cab_farm"] = material("M_TRUCK_CAB_FARM", "#E6E4DE", roughness=0.45, metallic=0.1)
    M["cab_delivery"] = material("M_TRUCK_CAB_DELIVERY", "#D3DCE0", roughness=0.45, metallic=0.1)
    M["chassis"] = material("M_TRUCK_CHASSIS", "#3E4245", roughness=0.7, metallic=0.3)
    M["tyre"] = material("M_TYRE", "#2B2D2F", roughness=0.95)
    M["hub"] = material("M_WHEEL_HUB", "#B9BDBF", roughness=0.4, metallic=0.6)
    M["glass_dark"] = material("M_TRUCK_GLASS_DARK", "#2E3438", roughness=0.15, metallic=0.2)
    M["lamp"] = material("M_TRUCK_LAMP", "#F4F1E8", roughness=0.3, emission="#FFF6E0", emission_strength=0.6)
    M["deck"] = material("M_TRUCK_DECK", "#8F969A", roughness=0.6, metallic=0.3)
    M["forklift"] = material("M_FORKLIFT", "#C9A548", roughness=0.6)
    M["marking"] = material("M_ROAD_MARKING", "#E8E6DF", roughness=0.7)
    M["rail_glass"] = glass("M_RAIL_GLASS", "#D7E1E4", alpha=0.32)
    M["hen_white"] = material("M_HEN_WHITE", "#E9E4D8", roughness=0.95)
    M["hen_brown"] = material("M_HEN_BROWN", "#A9825E", roughness=0.95)
    M["cage"] = material("M_CAGE_FRAME", "#A3AAAE", roughness=0.5, metallic=0.5)
    M["hen_crate"] = material("M_HEN_CRATE", "#7C8A94", roughness=0.7)


# --- henhouse structure ----------------------------------------------------------------------

def house_structure(name: str, x0: float, x1: float, y0: float, y1: float, z0: float, wall_h: float, ridge: float, parent) -> None:
    """Portal frames, purlins and ridge beam under the roof; visible once the roof is removed.

    The rafters follow the roof pitch (gable from the eaves at z0 + wall_h up `ridge` metres).
    """
    s = MeshBuilder()
    ym = (y0 + y1) / 2
    eaves = z0 + wall_h
    half_span = ym - (y0 + 0.4)
    pitch = math.atan2(ridge - 0.25, half_span)
    rafter = math.hypot(half_span, ridge - 0.25)
    bays = 14
    for i in range(bays + 1):
        x = x0 + 0.6 + i * (x1 - x0 - 1.2) / bays
        for yc in (y0 + 0.4, y1 - 0.4):
            s.box((x - 0.12, yc - 0.15, z0), (x + 0.12, yc + 0.15, eaves), M["steel"])
        for sign, y_start in ((1, y0 + 0.4), (-1, y1 - 0.4)):
            cy = y_start + sign * half_span / 2
            cz = eaves + (ridge - 0.25) / 2
            s.oriented_box((x, cy, cz), (0.18, rafter, 0.28), M["steel"], rot_x=sign * pitch)
        # Tie beam: reads as a frame from the terrace.
        s.box((x - 0.06, y0 + 0.4, eaves - 0.12), (x + 0.06, y1 - 0.4, eaves), M["steel"])
    for k in range(1, 4):
        t = k / 4
        for sign, y_start in ((1, y0 + 0.4), (-1, y1 - 0.4)):
            py = y_start + sign * half_span * t
            pz = eaves + (ridge - 0.25) * t + 0.16
            s.box((x0 + 0.4, py - 0.06, pz - 0.06), (x1 - 0.4, py + 0.06, pz + 0.06), M["steel"])
    s.box((x0 + 0.4, ym - 0.08, eaves + ridge - 0.2), (x1 - 0.4, ym + 0.08, eaves + ridge - 0.05), M["steel"])
    bevel(s.build(name, parent=parent), 0.02)


def house_cladding(name: str, x0: float, x1: float, y0: float, y1: float, z0: float, wall_h: float, parent) -> None:
    """Concrete base course, vertical cladding ribs and wall fans with grilles."""
    c = MeshBuilder()
    for y, d in ((y0, -1), (y1, 1)):
        lo, hi = sorted((y, y + d * 0.08))
        c.box((x0, lo, z0), (x1, hi, z0 + 0.6), M["base"])
        rx = x0 + 0.5
        while rx < x1 - 0.3:
            rlo, rhi = sorted((y, y + d * 0.05))
            c.box((rx - 0.03, rlo, z0 + 0.6), (rx + 0.03, rhi, z0 + wall_h - 0.05), M["rib"])
            rx += 1.0
        for i in range(7):
            fx = x0 + 6.0 + i * ((x1 - x0) - 12.0) / 6
            hlo, hhi = sorted((y, y + d * 0.35))
            c.box((fx - 0.75, hlo, z0 + 1.4), (fx + 0.75, hhi, z0 + 2.9), M["fan_housing"])
            face = y + d * 0.36
            for k in range(6):
                gz = z0 + 1.55 + k * 0.24
                glo, ghi = sorted((face - d * 0.01, face + d * 0.01))
                c.box((fx - 0.62, glo, gz - 0.015), (fx + 0.62, ghi, gz + 0.015), M["grill"])
            c.cylinder_along((fx, y + d * 0.3, z0 + 2.15), "Y", 0.14, 0.12, M["grill"], segments=10)
    for x, d in ((x0, -1), (x1, 1)):
        lo, hi = sorted((x, x + d * 0.08))
        c.box((lo, y0, z0), (hi, y1, z0 + 0.6), M["base"])
    # Seen from 15 m and more: no chamfer on the many small parts.
    c.build(name, parent=parent)


def silo_details(name: str, silos: list[tuple[float, float]], house_x: float, z0: float, parent) -> None:
    """Ladders, hatches, discharge cones and feed pipes into the henhouse wall."""
    d = MeshBuilder()
    for x, y in silos:
        d.frustum((x, y, z0 + 0.5), 0.25, 1.6, 0.7, M["silo"], segments=18)
        for lx in (-0.18, 0.18):
            d.box((x + lx - 0.02, y - 1.66, z0 + 1.2), (x + lx + 0.02, y - 1.62, z0 + 7.9), M["steel"])
        rz = z0 + 1.4
        while rz < z0 + 7.8:
            d.box((x - 0.18, y - 1.66, rz - 0.015), (x + 0.18, y - 1.62, rz + 0.015), M["steel"])
            rz += 0.35
        d.cylinder((x, y, z0 + 9.05), 0.35, 0.18, M["steel"], segments=10)
        # Feed pipe from the discharge to the wall, then into the building.
        d.cylinder_along(((x + house_x) / 2, y, z0 + 0.65), "X", 0.1, house_x - x, M["steel"], segments=8)
    bevel(d.build(name, parent=parent), 0.01)


def egg_room(name: str, x: float, y0: float, y1: float, z0: float, parent) -> None:
    """Small annex at the east end where crates leave the henhouse; canopy over the dock."""
    a = MeshBuilder()
    a.box((x, y0, z0), (x + 4.0, y1, z0 + 3.2), M["annex"])
    a.box((x - 0.2, y0 - 0.2, z0 + 3.2), (x + 4.2, y1 + 0.2, z0 + 3.4), M["steel"])
    # Roller door facing the dock (south side) and a window on the east face.
    a.box((x + 0.6, y0 - 0.05, z0), (x + 3.4, y0, z0 + 2.6), M["door"])
    for k in range(10):
        a.box((x + 0.6, y0 - 0.07, z0 + 0.2 + k * 0.24), (x + 3.4, y0 - 0.05, z0 + 0.24 + k * 0.24), M["door_rib"])
    a.box((x + 4.0, y0 + 1.0, z0 + 1.2), (x + 4.05, y0 + 2.4, z0 + 2.2), M["window"])
    # Canopy on two posts over the dock apron.
    a.box((x - 0.3, y0 - 6.5, z0 + 3.6), (x + 4.3, y0 - 0.1, z0 + 3.8), M["steel"])
    for px, py in ((x - 0.1, y0 - 6.3), (x + 4.1, y0 - 6.3)):
        a.box((px - 0.08, py - 0.08, z0), (px + 0.08, py + 0.08, z0 + 3.6), M["steel"])
    bevel(a.build(name, parent=parent), 0.015)


# --- packing centre docks and yard ------------------------------------------------------------

def dock_doors(b: MeshBuilder, doors: list[tuple[tuple[float, float, float], str]], z0: float) -> None:
    """Roller doors with ribs, dark shelters and bumpers. Each door: ((x, y, width), face)."""
    for (x, y, w), face in doors:
        if face == "south":
            b.box((x - 0.25, y - 0.4, z0), (x + w + 0.25, y, z0 + 3.9), M["shelter"])
            b.box((x, y - 0.42, z0 + 0.1), (x + w, y - 0.38, z0 + 3.5), M["door"])
            for k in range(13):
                b.box((x, y - 0.44, z0 + 0.25 + k * 0.25), (x + w, y - 0.42, z0 + 0.29 + k * 0.25), M["door_rib"])
            for bx in (x + 0.2, x + w - 0.5):
                b.box((bx, y - 0.65, z0 + 0.9), (bx + 0.3, y - 0.4, z0 + 1.3), M["bumper"])
        else:
            b.box((x - 0.4, y - 0.25, z0), (x, y + w + 0.25, z0 + 3.9), M["shelter"])
            b.box((x - 0.42, y, z0 + 0.1), (x - 0.38, y + w, z0 + 3.5), M["door"])
            for k in range(13):
                b.box((x - 0.44, y, z0 + 0.25 + k * 0.25), (x - 0.42, y + w, z0 + 0.29 + k * 0.25), M["door_rib"])
            for by in (y + 0.2, y + w - 0.5):
                b.box((x - 0.65, by, z0 + 0.9), (x - 0.4, by + 0.3, z0 + 1.3), M["bumper"])


def forklift(b: MeshBuilder, x: float, y: float, z0: float) -> None:
    """Parked counterbalance forklift, forks towards -X. Static prop."""
    b.box((x - 0.6, y - 0.55, z0 + 0.25), (x + 1.2, y + 0.55, z0 + 1.0), M["forklift"])
    b.box((x + 0.9, y - 0.55, z0 + 0.3), (x + 1.35, y + 0.55, z0 + 1.15), M["chassis"])
    for px, py in ((x - 0.5, y - 0.5), (x - 0.5, y + 0.5), (x + 0.6, y - 0.5), (x + 0.6, y + 0.5)):
        b.box((px - 0.03, py - 0.03, z0 + 1.0), (px + 0.03, py + 0.03, z0 + 2.15), M["chassis"])
    b.box((x - 0.55, y - 0.55, z0 + 2.15), (x + 0.65, y + 0.55, z0 + 2.2), M["chassis"])
    for py in (y - 0.35, y + 0.35):
        b.box((x - 0.75, py - 0.05, z0 + 0.1), (x - 0.65, py + 0.05, z0 + 2.4), M["chassis"])
        b.box((x - 1.85, py - 0.06, z0 + 0.1), (x - 0.75, py + 0.06, z0 + 0.15), M["hub"])
    for wx in (x - 0.35, x + 0.85):
        for wy in (y - 0.58, y + 0.58):
            b.cylinder_along((wx, wy, z0 + 0.25), "Y", 0.25, 0.2, M["tyre"], segments=12)
    b.box((x + 0.05, y - 0.25, z0 + 1.0), (x + 0.45, y + 0.25, z0 + 1.35), M["chassis"])


def road_markings(name: str, roads: list[tuple[tuple[float, float], tuple[float, float], tuple[float, float, float, float], bool]], z: float, parent) -> None:
    """Dashed centre lines (3 m dashes every 6 m), none across another road. Each road is
    (start, end, asphalt rect, dashed): roads without dashes still keep the others clear of them.
    Kept out of the occlusion bake."""
    m = MeshBuilder()
    for i, ((ax, ay), (bx, by), _, dashed) in enumerate(roads):
        if not dashed:
            continue
        others = [r[2] for j, r in enumerate(roads) if j != i]
        length = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / length, (by - ay) / length
        t = 1.5
        while t + 3.0 < length:
            cx, cy = ax + ux * (t + 1.5), ay + uy * (t + 1.5)
            t += 6.0
            half = (1.5, 0.075) if abs(ux) > abs(uy) else (0.075, 1.5)
            lo, hi = (cx - half[0], cy - half[1]), (cx + half[0], cy + half[1])
            # A dash that touches another road's asphalt (a junction) is dropped.
            if any(lo[0] < o[2] and hi[0] > o[0] and lo[1] < o[3] and hi[1] > o[1] for o in others):
                continue
            m.box((lo[0], lo[1], z), (hi[0], hi[1], z + 0.01), M["marking"])
    m.build(name, parent=parent)["ao_skip"] = True


# --- loads and trucks -------------------------------------------------------------------------

def pallet(b: MeshBuilder, x: float, y: float, z: float) -> float:
    """1.0 × 1.2 m wooden pallet with its corner at (x, y, z); returns its top height."""
    b.box((x, y, z + 0.1), (x + 1.0, y + 1.2, z + 0.14), M["pallet"])
    for rx in (x, x + 0.44, x + 0.88):
        b.box((rx, y, z), (rx + 0.12, y + 1.2, z + 0.1), M["pallet"])
    return z + 0.14


def crate_pallet(b: MeshBuilder, x: float, y: float, z: float) -> None:
    """Pallet of open-sided egg crates, 2 × 2 × 3, slots as dark inset strips."""
    top = pallet(b, x, y, z)
    for i in range(2):
        for j in range(2):
            for k in range(3):
                cx0, cy0, cz0 = x + 0.02 + i * 0.49, y + 0.02 + j * 0.59, top + k * 0.3
                cx1, cy1, cz1 = cx0 + 0.47, cy0 + 0.57, cz0 + 0.28
                b.box((cx0, cy0, cz0), (cx1, cy1, cz1), M["crate"])
                for sz in (cz0 + 0.07, cz0 + 0.17):
                    b.box((cx0 + 0.05, cy0 - 0.005, sz), (cx1 - 0.05, cy0, sz + 0.05), M["crate_slot"])
                    b.box((cx0 + 0.05, cy1, sz), (cx1 - 0.05, cy1 + 0.005, sz + 0.05), M["crate_slot"])
                    b.box((cx0 - 0.005, cy0 + 0.05, sz), (cx0, cy1 - 0.05, sz + 0.05), M["crate_slot"])
                    b.box((cx1, cy0 + 0.05, sz), (cx1 + 0.005, cy1 - 0.05, sz + 0.05), M["crate_slot"])


def carton_pallet(b: MeshBuilder, x: float, y: float, z: float) -> None:
    """Pallet of packed egg boxes under stretch film, with two strapping bands."""
    top = pallet(b, x, y, z)
    b.box((x + 0.02, y + 0.02, top), (x + 0.98, y + 1.18, top + 1.0), M["wrap"])
    for bx in (x + 0.3, x + 0.65):
        b.box((bx, y + 0.015, top), (bx + 0.05, y + 1.185, top + 1.005), M["wrap_band"])


# --- laying hens, cages and transport crates --------------------------------------------------
# Stylised and sober (docs/DA.md §04): simple volumes, regular groups, no gesture, nothing that
# suggests distress. Seen from the terrace, 20 m and more away, so each hen is a few dozen
# triangles. They face the aisle they are in.

def hen(b: MeshBuilder, x: float, y: float, z: float, facing: int, brown: bool) -> None:
    """One hen standing at (x, y, z), its head towards `facing` (±Y)."""
    mat = M["hen_brown"] if brown else M["hen_white"]
    b.ellipsoid((x, y, z + 0.14), (0.11, 0.17, 0.12), mat, u=6, v=3)
    # Head on a short neck; the base and the face towards the body are never seen.
    hy = y + facing * 0.17
    b.box((x - 0.035, hy - 0.04, z + 0.2), (x + 0.035, hy + 0.04, z + 0.31), mat)


def battery_cages(name: str, x0: float, x1: float, y0: float, y1: float, floor_z: float, parent, hens_parent) -> None:
    """Rows of stacked cages in the henhouse, three tiers, with one small group of hens in each
    compartment. Blocks are back to back, with an aisle between blocks. Returns nothing: the
    frames become `name`, the hens one mesh per row under `hens_parent`."""
    frame = MeshBuilder()
    blocks, tiers = 3, 3
    pitch, depth = 1.5, 0.55
    aisle = ((y1 - y0) - blocks * 2 * depth) / (blocks + 1)
    rows = []  # (y_front, facing)
    for blk in range(blocks):
        yc = y0 + aisle * (blk + 1) + 2 * depth * blk + depth
        rows.append((yc - depth, -1, yc - depth, yc))  # south row: front at y_c - depth
        rows.append((yc + depth, 1, yc, yc + depth))  # north row: front at y_c + depth
    count = int((x1 - x0) // pitch)
    for r, (front, facing, ya, yb) in enumerate(rows, start=1):
        hens = MeshBuilder()
        for t in range(tiers):
            z = floor_z + 0.35 + t * 0.55
            frame.box((x0, ya, z), (x0 + count * pitch, yb, z + 0.03), M["cage"])
            for bar in (0.17, 0.34):
                fy = front + facing * 0.01
                frame.box((x0, min(front, fy) - 0.008, z + bar), (x0 + count * pitch, max(front, fy) + 0.008, z + bar + 0.016), M["cage"])
            for i in range(count):
                cx = x0 + (i + 0.5) * pitch
                for k in range(3):
                    seed = r * 7919 + t * 104729 + i * 31 + k * 17
                    jx = ((seed % 11) - 5) * 0.025
                    jy = (((seed // 11) % 7) - 3) * 0.02
                    hen(hens, cx + (k - 1) * 0.42 + jx, (ya + yb) / 2 + jy, z + 0.03, facing, (seed // 77) % 3 == 0)
        # Posts at each compartment boundary, full height of the stack.
        for i in range(count + 1):
            px = x0 + i * pitch
            frame.box((px - 0.015, front - 0.015, floor_z + 0.2), (px + 0.015, front + 0.015, floor_z + 0.35 + tiers * 0.55), M["cage"])
        hens.drop_bottom_caps().build(f"{hens_parent.name}_{r:02d}", parent=hens_parent)
    frame.build(name, parent=parent)


def hen_module(b: MeshBuilder, x: float, y: float, z: float) -> None:
    """Stack of five open transport crates (slotted sides) with hens in the top one."""
    w, d, h = 0.78, 0.56, 0.2
    for k in range(5):
        z0 = z + k * h
        b.box((x, y, z0), (x + w, y + d, z0 + h - 0.01), M["hen_crate"])
        for sx in (0.12, 0.34, 0.56):
            b.box((x + sx, y - 0.005, z0 + 0.06), (x + sx + 0.1, y, z0 + 0.15), M["crate_slot"])
            b.box((x + sx, y + d, z0 + 0.06), (x + sx + 0.1, y + d + 0.005, z0 + 0.15), M["crate_slot"])
    top = z + 5 * h - 0.01
    for k in range(4):
        hen(b, x + 0.1 + k * 0.19, y + d / 2 + (0.07 if k % 2 else -0.07), top - 0.08, 1 if k % 2 else -1, k == 1)


def unit_group(name: str, origin, cells: list[tuple[int, int]], unit, parent, step=(1.3, 1.5)):
    """Empty holding one mesh per unit (shown or hidden one by one by the timeline)."""
    group = empty(name, origin, parent)
    for i, (gx, gy) in enumerate(cells, start=1):
        b = MeshBuilder()
        unit(b, gx * step[0], gy * step[1], 0.0)
        # Seen from 15 m and more: no chamfer (it would multiply the triangles of every crate).
        b.build(f"{name}_{i:02d}", parent=group)
    return group


def truck(name: str, cargo: str, unit, cab_mat, location, parent, cells=None, step=(1.1, 1.75), slats=False):
    """Unbranded rigid truck facing Blender +Y (glTF -Z), origin on the ground at its centre.

    `slats` adds open-slatted side racks (livestock body); `cells`/`step` lay out the cargo units."""
    root = empty(name, location, parent)
    b = MeshBuilder()
    for x in (-0.55, 0.45):
        b.box((x, -4.3, 0.55), (x + 0.1, 3.9, 0.8), M["chassis"])
    # Cab: body, roof fairing, windscreen, side windows, grille, lamps, bumper, step, mirrors.
    b.box((-1.2, 2.25, 0.8), (1.2, 4.2, 3.0), cab_mat)
    b.box((-1.15, 2.3, 3.0), (1.15, 3.6, 3.35), cab_mat)
    b.box((-1.05, 4.2, 1.9), (1.05, 4.23, 2.85), M["glass_dark"])
    for x in (-1.2, 1.17):
        b.box((x, 3.2, 2.0), (x + 0.03, 4.0, 2.75), M["glass_dark"])
    b.box((-0.8, 4.2, 1.0), (0.8, 4.24, 1.65), M["chassis"])
    for x in (-1.05, 0.75):
        b.box((x, 4.2, 1.05), (x + 0.3, 4.25, 1.3), M["lamp"])
    b.box((-1.25, 4.2, 0.5), (1.25, 4.42, 0.9), M["chassis"])
    for x, arm in ((-1.36, (-1.36, -1.2)), (1.26, (1.2, 1.36))):
        b.box((x, 3.95, 2.1), (x + 0.1, 4.05, 2.6), M["chassis"])
        b.box((arm[0], 3.98, 2.5), (arm[1], 4.02, 2.54), M["chassis"])
    b.box((-1.25, 2.4, 0.45), (-1.2, 3.0, 0.8), M["chassis"])
    # Fuel tank and wheels with hubs (front axle, tandem rear axles).
    b.cylinder_along((-0.9, 0.6, 0.75), "Y", 0.28, 1.1, M["hub"], segments=10)
    for wy in (3.2, -2.6, -3.7):
        for wx in (-1.02, 1.02):
            b.cylinder_along((wx, wy, 0.52), "X", 0.52, 0.36, M["tyre"], segments=14)
            b.cylinder_along((wx + (0.18 if wx > 0 else -0.18), wy, 0.52), "X", 0.26, 0.02, M["hub"], segments=10)
        b.box((-1.25, wy - 0.65, 1.08), (1.25, wy + 0.65, 1.14), M["chassis"])
    # Flat deck with low side rails and headboard.
    b.box((-1.2, -4.3, 1.15), (1.2, 2.1, 1.3), M["deck"])
    for x in (-1.2, 1.14):
        b.box((x, -4.3, 1.3), (x + 0.06, 2.1, 1.5), M["deck"])
    b.box((-1.2, 2.0, 1.3), (1.2, 2.1, 2.7), M["deck"])
    if slats:
        # Side racks: posts and four slats a side, open at the rear for loading, open above.
        for x in (-1.2, 1.14):
            for y in (-4.3, -2.2, -0.1, 2.04):
                b.box((x, y, 1.3), (x + 0.06, y + 0.06, 2.7), M["deck"])
            for z in (1.55, 1.9, 2.25, 2.6):
                b.box((x, -4.3, z), (x + 0.06, 2.1, z + 0.06), M["deck"])
    bevel(b.build(f"{name}_BODY", parent=root), 0.02)
    # Pallets or crate stacks, two abreast, loaded from the rear (default: six pallets).
    cells = cells or [(i, j) for j in range(3) for i in range(2)]
    unit_group(cargo, (-1.05 if not slats else -0.9, -4.15 if not slats else -4.1, 1.3), cells, unit, root, step=step)
    return root
