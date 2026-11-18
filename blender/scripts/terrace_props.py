"""Detailed, procedural farm structure and logistics for the terraces (lot 2).

Credible but stylised, no brand anywhere. The henhouse interior shows laying hens in stacked
cages (docs/DECISIONS.md, « Poules »): a schematic depiction, not a documented installation, with
no figure attached (TODO_SOURCE). Coordinates are the terrace module's Blender frame (metres,
Z up), see build_terrace_eggs.py.

Everything here is seen from a raised terrace, 20 m and more away: parts are low-poly, unseen
faces are left out, and weathering (rain streaks under the eaves, splashed wall bases, sheet to
sheet variation) is baked per vertex (lowpoly.TINT → COLOR_0) on top of the tileable corrugated
sheet texture bound by material name (blender/textures/surfaces.json, set `cladding`).

Animal meshes use a material whose name starts with `M_ANIMAL_` and carry the `_PHASE`
attribute (lowpoly.py) for the runtime's idle animation.
"""

from __future__ import annotations

import math

from mathutils import Vector

import lowpoly as lp
from common import MeshBuilder, bevel, box, empty, glass, helper_volume, material

M: dict = {}

HEN_WHITE = lp.lin("#EFEBE0")
HEN_BROWN = lp.lin("#A87C55")
HEN_COMB = lp.lin("#C2382E")
HEN_BEAK = lp.lin("#D9A23C")
# Baked tints of the one material shared by loads and small yard equipment (M_LOAD_PAINT, white).
WOOD = lp.lin("#B79C78")
CRATE = lp.lin("#86A590")
WRAP = lp.lin("#E2DCCB")
WRAP_BAND = lp.lin("#C7BB9E")
HEN_CRATE = lp.lin("#8A98A2")
DOOR = lp.lin("#9EA6AC")
DOOR_RIB = lp.lin("#868E94")
SHELTER = lp.lin("#3E4347")
BUMPER = lp.lin("#2F3133")
FORKLIFT = lp.lin("#C9A548")
DARK = lp.lin("#3E4245")
TYRE = lp.lin("#2B2D2F")
HUB = lp.lin("#B9BDBF")


def materials() -> None:
    M["steel"] = material("M_FRAME_STEEL", "#8E9296", roughness=0.5, metallic=0.5)
    M["base"] = material("M_CONCRETE_BASE", "#B4B1A9", roughness=0.9)
    M["grill"] = material("M_FAN_GRILL", "#4A4C4D", roughness=0.6, metallic=0.4)
    M["fan_housing"] = material("M_FAN_HOUSING", "#C4C6C6", roughness=0.5, metallic=0.3)
    M["silo"] = material("M_SILO", "#C8CCCF", roughness=0.4, metallic=0.5)
    M["door"] = material("M_ROLLER_DOOR", "#9EA6AC", roughness=0.6, metallic=0.3)
    M["door_rib"] = material("M_ROLLER_DOOR_RIB", "#868E94", roughness=0.6, metallic=0.3)
    M["window"] = material("M_WINDOW_DARK", "#3A4246", roughness=0.15, metallic=0.2)
    M["annex"] = material("M_FARM_ANNEX", "#C9C1B1", roughness=0.8)
    # Pallets, crates, cartons, dock doors, forklift: one white material, colours are baked tints
    # (each load is a single draw call, and nothing here is seen from less than 30 m).
    M["load"] = material("M_LOAD_PAINT", "#FFFFFF", roughness=0.75)
    M["cab_farm"] = material("M_TRUCK_CAB_FARM", "#E6E4DE", roughness=0.45, metallic=0.1)
    M["cab_delivery"] = material("M_TRUCK_CAB_DELIVERY", "#D3DCE0", roughness=0.45, metallic=0.1)
    M["chassis"] = material("M_TRUCK_CHASSIS", "#3E4245", roughness=0.7, metallic=0.3)
    M["tyre"] = material("M_TYRE", "#2B2D2F", roughness=0.95)
    M["hub"] = material("M_WHEEL_HUB", "#B9BDBF", roughness=0.4, metallic=0.6)
    M["glass_dark"] = material("M_TRUCK_GLASS_DARK", "#2E3438", roughness=0.15, metallic=0.2)
    M["lamp"] = material("M_TRUCK_LAMP", "#F4F1E8", roughness=0.3, emission="#FFF6E0", emission_strength=0.6)
    M["deck"] = material("M_TRUCK_DECK", "#8F969A", roughness=0.6, metallic=0.3)
    M["rail_glass"] = glass("M_RAIL_GLASS", "#D7E1E4", alpha=0.32)
    M["cage"] = material("M_CAGE_FRAME", "#A3AAAE", roughness=0.5, metallic=0.5)
    # Dark belts under the wire floors: the hens stand out against them.
    M["cage_floor"] = material("M_CAGE_FLOOR", "#585C5E", roughness=0.9)
    # Gutters, downpipes, ridge caps and roof vents: plain galvanised steel, no texture.
    M["gutter"] = material("M_GUTTER", "#6F767A", roughness=0.55, metallic=0.4)
    M["trim"] = material("M_ROOF_TRIM", "#A5AAAC", roughness=0.5, metallic=0.4)
    # One white material for every hen: plumage, comb and beak colours are baked tints.
    M["animal_hen"] = material("M_ANIMAL_HEN", "#FFFFFF", roughness=0.95)


# --- weathered sheet metal ---------------------------------------------------------------------

def wall_tint(seed: int, tone: float = 1.0, columns: int = 1):
    """Tint of a clad wall at (s along, t up): splashed and dusty at the base, clean in the
    middle, rain streaks of uneven length under the eaves."""

    def at(s: float, t: float) -> lp.RGB:
        col = round(s * columns)
        r = lp.rand(seed, col, 3)
        if t < 0.05:
            c = lp.scale((0.86, 0.82, 0.76), 0.86 + 0.14 * lp.rand(seed, col, 5))
        elif t > 0.95:
            c = lp.scale((0.9, 0.9, 0.87), 0.84 + 0.16 * r)
        elif t > 0.6:
            c = lp.scale((0.97, 0.97, 0.95), 0.9 + 0.1 * r)
        else:
            c = lp.scale(lp.WHITE, 0.95 + 0.05 * lp.rand(seed, col, 7))
        return lp.scale(c, tone)

    return at


def clad_wall(b: MeshBuilder, a, c, z0: float, z1: float, normal, mat, seed: int, tone: float = 1.0, spacing: float = 2.5) -> None:
    """Outer face of a clad wall from `a` to `c` (x, y), facing `normal`: a grid whose vertices
    carry the weathering."""
    (ax, ay), (cx, cy) = a, c
    u = Vector((cx - ax, cy - ay, 0.0))
    if u.cross(Vector((0.0, 0.0, 1.0))).dot(Vector((normal[0], normal[1], 0.0))) < 0:
        (ax, ay), u = (cx, cy), -u
    columns = max(1, round(u.length / spacing))
    lp.panel(b, (ax, ay, z0), u, (0.0, 0.0, z1 - z0), (columns, 3), mat, wall_tint(seed, tone, columns))


def downpipe(b: MeshBuilder, x: float, y: float, z0: float, z1: float) -> None:
    lp.tube(b, (x, y, z0), (x, y, z1), 0.07, M["gutter"])


def shed_roof(name: str, x0: float, x1: float, y0: float, y1: float, z0: float, z1: float, ridge: float, mat, parent,
              seed: int, tone: float = 1.0, vents: int = 0, centred: bool = False, gutters: bool = True, builder: MeshBuilder | None = None):
    """Pitched sheet roof with its ridge along X: eaves from z0 to z1, ridge `ridge` above z1.

    Slopes are grids so that dirt can run down from the ridge (baked tint); a ridge cap,
    gutters under both eaves and optional ridge vents complete it. No underside: the roof is
    only ever seen from above. `centred` puts the object's origin at the centre of the eaves.
    With `builder`, the roof joins that mesh instead of becoming the object `name`."""
    ox, oy, oz = ((x0 + x1) / 2, (y0 + y1) / 2, z0) if centred else (0.0, 0.0, 0.0)
    x0, x1, y0, y1, z0, z1 = x0 - ox, x1 - ox, y0 - oy, y1 - oy, z0 - oz, z1 - oz
    ym, zr = (y0 + y1) / 2, z1 + ridge
    length = x1 - x0
    columns = max(2, round(length / 2.5))
    b = builder or MeshBuilder(recalc_normals=False)

    def slope_tint(side: int):
        def at(s: float, t: float) -> lp.RGB:
            col = round(s * columns)
            sheet = 0.9 if lp.rand(seed, side, col, 3) < 0.1 else 1.0  # a replaced or older sheet
            if t < 0.05:
                c = lp.scale((0.9, 0.86, 0.82), 0.8 + 0.18 * lp.rand(seed, side, col, 5))
            elif t > 0.95:
                c = lp.scale(lp.WHITE, 0.95 + 0.05 * lp.rand(seed, side, col, 7))
            else:
                c = lp.scale((0.96, 0.94, 0.92), 0.88 + 0.12 * lp.rand(seed, side, col, 9))
            return lp.scale(c, tone * sheet)

        return at

    lp.panel(b, (x0, y0, z1), (length, 0.0, 0.0), (0.0, ym - y0, ridge), (columns, 2), mat, slope_tint(0))
    lp.panel(b, (x1, y1, z1), (-length, 0.0, 0.0), (0.0, ym - y1, ridge), (columns, 2), mat, slope_tint(1))
    edge = lp.scale(lp.WHITE, 0.85 * tone)
    lp.quad(b, ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)), mat, tint=edge)
    lp.quad(b, ((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)), mat, tint=edge)
    gable = lp.scale(lp.WHITE, 0.93 * tone)
    lp.add(b, [Vector(p) for p in ((x0, y0, z0), (x0, y0, z1), (x0, ym, zr), (x0, y1, z1), (x0, y1, z0))], [(0, 1, 2, 3, 4)], mat, tint=gable)
    lp.add(b, [Vector(p) for p in ((x1, y1, z0), (x1, y1, z1), (x1, ym, zr), (x1, y0, z1), (x1, y0, z0))], [(0, 1, 2, 3, 4)], mat, tint=gable)
    # Ridge cap: a shallow inverted V over the joint between the two slopes.
    drop = 0.45 * ridge / (ym - y0)
    lp.quad(b, ((x0, ym - 0.45, zr - drop + 0.05), (x1, ym - 0.45, zr - drop + 0.05), (x1, ym, zr + 0.07), (x0, ym, zr + 0.07)), M["trim"])
    lp.quad(b, ((x1, ym + 0.45, zr - drop + 0.05), (x0, ym + 0.45, zr - drop + 0.05), (x0, ym, zr + 0.07), (x1, ym, zr + 0.07)), M["trim"])
    if gutters:
        lp.box_faces(b, (x0, y0 - 0.18, z0 - 0.04), (x1, y0, z0 + 0.1), M["gutter"], skip=("-z", "+y"))
        lp.box_faces(b, (x0, y1, z0 - 0.04), (x1, y1 + 0.18, z0 + 0.1), M["gutter"], skip=("-z", "-y"))
    for k in range(vents):
        vx = x0 + length * (k + 0.5) / vents
        lp.box_faces(b, (vx - 0.55, ym - 0.45, zr - 0.2), (vx + 0.55, ym + 0.45, zr + 0.45), M["trim"], tint=(0.9, 0.9, 0.9))
        lp.box_faces(b, (vx - 0.7, ym - 0.6, zr + 0.45), (vx + 0.7, ym + 0.6, zr + 0.55), M["gutter"])
    if builder is not None:
        return None
    roof = b.build(name, (ox, oy, oz), parent)
    # Open to the sky, and removed on reveal: it must not darken what it covers.
    roof["ao_skip"] = True
    return roof


# --- henhouse structure ----------------------------------------------------------------------

def house_structure(name: str, x0: float, x1: float, y0: float, y1: float, z0: float, wall_h: float, ridge: float, parent, bays: int = 14) -> None:
    """Portal frames, purlins and ridge beam under the roof; visible once the roof is removed.

    The rafters follow the roof pitch (gable from the eaves at z0 + wall_h up `ridge` metres).
    """
    s = MeshBuilder(recalc_normals=False)
    ym = (y0 + y1) / 2
    eaves = z0 + wall_h
    half_span = ym - (y0 + 0.4)
    pitch = math.atan2(ridge - 0.25, half_span)
    rafter = math.hypot(half_span, ridge - 0.25)
    for i in range(bays + 1):
        x = x0 + 0.6 + i * (x1 - x0 - 1.2) / bays
        for yc in (y0 + 0.4, y1 - 0.4):
            s.box((x - 0.12, yc - 0.15, z0), (x + 0.12, yc + 0.15, eaves), M["steel"], skip=("-z", "+z"))
        for sign, y_start in ((1, y0 + 0.4), (-1, y1 - 0.4)):
            cy = y_start + sign * half_span / 2
            cz = eaves + (ridge - 0.25) / 2
            s.oriented_box((x, cy, cz), (0.18, rafter, 0.28), M["steel"], rot_x=sign * pitch)
        # Tie beam: reads as a frame from the terrace.
        s.box((x - 0.06, y0 + 0.4, eaves - 0.12), (x + 0.06, y1 - 0.4, eaves), M["steel"], skip=("-y", "+y"))
    for k in range(1, 4):
        t = k / 4
        for sign, y_start in ((1, y0 + 0.4), (-1, y1 - 0.4)):
            py = y_start + sign * half_span * t
            pz = eaves + (ridge - 0.25) * t + 0.16
            s.box((x0 + 0.4, py - 0.06, pz - 0.06), (x1 - 0.4, py + 0.06, pz + 0.06), M["steel"], skip=("-x", "+x"))
    s.box((x0 + 0.4, ym - 0.08, eaves + ridge - 0.2), (x1 - 0.4, ym + 0.08, eaves + ridge - 0.05), M["steel"], skip=("-x", "+x"))
    # Seen from 20 m and more: no chamfer.
    s.build(name, parent=parent)


def wall_fan(b: MeshBuilder, x: float, y: float, d: int, z0: float) -> None:
    """Wall fan on a face at `y`, looking along d·Y: housing, dark opening, three louvres."""
    lo, hi = sorted((y, y + d * 0.35))
    b.box((x - 0.75, lo, z0 + 1.4), (x + 0.75, hi, z0 + 2.9), M["fan_housing"], skip=("+y" if d < 0 else "-y",))
    face = y + d * 0.36
    corners = ((x - 0.62, face, z0 + 1.52), (x + 0.62, face, z0 + 1.52), (x + 0.62, face, z0 + 2.78), (x - 0.62, face, z0 + 2.78))
    lp.quad(b, corners if d < 0 else tuple(reversed(corners)), M["grill"], tint=(0.75, 0.75, 0.75))
    for k in range(3):
        gz = z0 + 1.72 + k * 0.42
        glo, ghi = sorted((face, face + d * 0.03))
        b.box((x - 0.62, glo, gz - 0.03), (x + 0.62, ghi, gz + 0.03), M["fan_housing"], skip=("+y" if d < 0 else "-y", "-x", "+x"))


def house_cladding(name: str, x0: float, x1: float, y0: float, y1: float, z0: float, wall_h: float, parent, wall_mat=None,
                   seed: int = 1, tone: float = 1.0, fans: int = 7, hidden_north: bool = False, builder: MeshBuilder | None = None) -> None:
    """Everything on the outside of a long house: weathered cladding (when `wall_mat` is given),
    concrete base course, wall fans, downpipes. `hidden_north` leaves out what stands on the
    north face (houses whose far side can never be seen from the terrace). With `builder`, the
    parts join that mesh instead of becoming the object `name`."""
    c = builder or MeshBuilder(recalc_normals=False)
    faces = (((x0, y0), (x1, y0), (0, -1), -1), ((x0, y1), (x1, y1), (0, 1), 1))
    for a, e, normal, d in faces:
        if wall_mat is not None:
            clad_wall(c, a, e, z0 + 0.6, z0 + wall_h, normal, wall_mat, seed + (7 if d > 0 else 0), tone)
        if d > 0 and hidden_north:
            continue
        y = a[1]
        lo, hi = sorted((y, y + d * 0.08))
        c.box((x0, lo, z0), (x1, hi, z0 + 0.6), M["base"], skip=("-z", "+y" if d < 0 else "-y"))
        for i in range(fans):
            fx = x0 + 6.0 + i * ((x1 - x0) - 12.0) / max(1, fans - 1)
            wall_fan(c, fx, y, d, z0)
        for px in (x0 + 0.5, (x0 + x1) / 2 + 2.0 * (lp.rand(seed, 91) - 0.5), x1 - 0.5):
            downpipe(c, px, y + d * 0.1, z0, z0 + wall_h)
    for x, d, normal in ((x0, -1, (-1, 0)), (x1, 1, (1, 0))):
        if wall_mat is not None:
            clad_wall(c, (x, y0), (x, y1), z0 + 0.6, z0 + wall_h, normal, wall_mat, seed + 13 * (2 + d), tone)
        lo, hi = sorted((x, x + d * 0.08))
        c.box((lo, y0, z0), (hi, y1, z0 + 0.6), M["base"], skip=("-z", "+x" if d < 0 else "-x"))
    if builder is None:
        c.build(name, parent=parent)


def silos(name: str, positions: list[tuple[float, float]], house_x: float, z0: float, parent) -> None:
    """Feed silos: ringed bins on four legs with a discharge cone, a ladder and a feed pipe into
    the house wall. The rings of the bolted sheets are baked tints on twelve-sided shells."""
    b = MeshBuilder(recalc_normals=False)
    for n, (x, y) in enumerate(positions):
        sides, turn = 12, math.pi / 12
        tone = 0.92 + 0.08 * lp.rand(n, int(y), 3)
        rings, tints = [], []
        levels = (1.9, 3.2, 3.25, 4.5, 4.55, 5.8, 5.85, 7.1, 7.15, 7.7)
        for k, zz in enumerate(levels):
            rings.append(lp.ring((x, y, z0 + zz), 1.6, 1.6, sides, turn))
            seam = k % 2 == 1 and k < len(levels) - 1
            tints.append(lp.scale(lp.WHITE, tone * (0.8 if seam else 0.94 + 0.06 * lp.rand(n, k, 5))))
        lp.loft(b, rings, M["silo"], ring_tints=tints, smooth=True)
        lp.loft(b, [lp.ring((x, y, z0 + 7.7), 1.68, 1.68, sides, turn)], M["silo"], ring_tints=[lp.scale(lp.WHITE, 0.88 * tone)],
                apex=(x, y, z0 + 9.05), apex_tint=lp.scale(lp.WHITE, tone), smooth=True)
        # Discharge cone, pointing down.
        lp.loft(b, [lp.ring((x, y, z0 + 0.55), 0.25, 0.25, sides, turn), lp.ring((x, y, z0 + 1.9), 1.6, 1.6, sides, turn)], M["silo"],
                ring_tints=[(0.7, 0.7, 0.7), (0.85, 0.85, 0.85)], smooth=True)
        for lx, ly in ((-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0), (1.0, 1.0)):
            lp.tube(b, (x + lx * 1.12, y + ly * 1.12, z0), (x + lx * 1.12, y + ly * 1.12, z0 + 2.3), 0.09, M["steel"])
        # Ladder on the south side, towards the terrace: two rails, a rung every 0.7 m.
        for lx in (-0.2, 0.2):
            lp.tube(b, (x + lx, y - 1.66, z0 + 1.2), (x + lx, y - 1.66, z0 + 7.9), 0.025, M["steel"])
        rz = z0 + 1.5
        while rz < z0 + 7.8:
            lp.quad(b, ((x - 0.2, y - 1.68, rz - 0.025), (x + 0.2, y - 1.68, rz - 0.025), (x + 0.2, y - 1.68, rz + 0.025), (x - 0.2, y - 1.68, rz + 0.025)), M["steel"])
            rz += 0.7
        lp.box_faces(b, (x - 0.3, y - 0.3, z0 + 9.0), (x + 0.3, y + 0.3, z0 + 9.2), M["steel"])
        # Feed pipe from the discharge to the wall.
        lp.tube(b, (x, y, z0 + 0.65), (house_x, y, z0 + 0.65), 0.1, M["steel"])
    b.build(name, parent=parent)


def egg_room(name: str, x: float, y0: float, y1: float, z0: float, parent) -> None:
    """Small annex at the east end where crates leave the henhouse; canopy over the dock."""
    a = MeshBuilder(recalc_normals=False)
    a.box((x, y0, z0), (x + 4.0, y1, z0 + 3.2), M["annex"], skip=("-z",))
    a.box((x - 0.2, y0 - 0.2, z0 + 3.2), (x + 4.2, y1 + 0.2, z0 + 3.4), M["steel"], skip=("-z",))
    # Roller door facing the dock (south side) and a window on the east face.
    a.box((x + 0.6, y0 - 0.05, z0), (x + 3.4, y0, z0 + 2.6), M["door"], skip=("-z", "+y"))
    for k in range(5):
        a.box((x + 0.6, y0 - 0.07, z0 + 0.3 + k * 0.48), (x + 3.4, y0 - 0.05, z0 + 0.36 + k * 0.48), M["door_rib"], skip=("+y",))
    a.box((x + 4.0, y0 + 1.0, z0 + 1.2), (x + 4.05, y0 + 2.4, z0 + 2.2), M["window"], skip=("-x",))
    # Canopy on two posts over the dock apron.
    a.box((x - 0.3, y0 - 6.5, z0 + 3.6), (x + 4.3, y0 - 0.1, z0 + 3.8), M["steel"])
    for px, py in ((x - 0.1, y0 - 6.3), (x + 4.1, y0 - 6.3)):
        a.box((px - 0.08, py - 0.08, z0), (px + 0.08, py + 0.08, z0 + 3.6), M["steel"], skip=("-z", "+z"))
    downpipe(a, x + 4.08, y1 - 0.3, z0, z0 + 3.2)
    bevel(a.build(name, parent=parent), 0.015)


# --- packing centre docks and yard ------------------------------------------------------------

def dock_doors(b: MeshBuilder, doors: list[tuple[tuple[float, float, float], str]], z0: float) -> None:
    """Roller doors with ribs, dark shelters and bumpers. Each door: ((x, y, width), face)."""
    mat = M["load"]
    for (x, y, w), face in doors:
        if face == "south":
            lp.box_faces(b, (x - 0.25, y - 0.4, z0), (x + w + 0.25, y, z0 + 3.9), mat, SHELTER, skip=("-z", "+y"))
            lp.box_faces(b, (x, y - 0.43, z0 + 0.1), (x + w, y - 0.4, z0 + 3.5), mat, DOOR, skip=("+y", "-z", "+z", "-x", "+x"))
            for k in range(6):
                lp.box_faces(b, (x, y - 0.47, z0 + 0.3 + k * 0.54), (x + w, y - 0.43, z0 + 0.38 + k * 0.54), mat, DOOR_RIB, skip=("+y", "-x", "+x"))
            for bx in (x + 0.2, x + w - 0.5):
                lp.box_faces(b, (bx, y - 0.65, z0 + 0.9), (bx + 0.3, y - 0.4, z0 + 1.3), mat, BUMPER, skip=("+y",))
        else:
            lp.box_faces(b, (x - 0.4, y - 0.25, z0), (x, y + w + 0.25, z0 + 3.9), mat, SHELTER, skip=("-z", "+x"))
            lp.box_faces(b, (x - 0.43, y, z0 + 0.1), (x - 0.4, y + w, z0 + 3.5), mat, DOOR, skip=("+x", "-z", "+z", "-y", "+y"))
            for k in range(6):
                lp.box_faces(b, (x - 0.47, y, z0 + 0.3 + k * 0.54), (x - 0.43, y + w, z0 + 0.38 + k * 0.54), mat, DOOR_RIB, skip=("+x", "-y", "+y"))
            for by in (y + 0.2, y + w - 0.5):
                lp.box_faces(b, (x - 0.65, by, z0 + 0.9), (x - 0.4, by + 0.3, z0 + 1.3), mat, BUMPER, skip=("+x",))


def forklift(b: MeshBuilder, x: float, y: float, z0: float) -> None:
    """Parked counterbalance forklift, forks towards -X. Static prop."""
    mat = M["load"]
    lp.box_faces(b, (x - 0.6, y - 0.55, z0 + 0.25), (x + 1.2, y + 0.55, z0 + 1.0), mat, FORKLIFT)
    lp.box_faces(b, (x + 0.9, y - 0.55, z0 + 0.3), (x + 1.35, y + 0.55, z0 + 1.15), mat, DARK)
    for px, py in ((x - 0.5, y - 0.5), (x - 0.5, y + 0.5), (x + 0.6, y - 0.5), (x + 0.6, y + 0.5)):
        lp.box_faces(b, (px - 0.03, py - 0.03, z0 + 1.0), (px + 0.03, py + 0.03, z0 + 2.15), mat, DARK, skip=("-z", "+z"))
    lp.box_faces(b, (x - 0.55, y - 0.55, z0 + 2.15), (x + 0.65, y + 0.55, z0 + 2.2), mat, DARK, skip=())
    for py in (y - 0.35, y + 0.35):
        lp.box_faces(b, (x - 0.75, py - 0.05, z0 + 0.1), (x - 0.65, py + 0.05, z0 + 2.4), mat, DARK)
        lp.box_faces(b, (x - 1.85, py - 0.06, z0 + 0.1), (x - 0.75, py + 0.06, z0 + 0.15), mat, HUB)
    for wx in (x - 0.35, x + 0.85):
        for wy in (y - 0.68, y + 0.48):
            lp.tube(b, (wx, wy, z0 + 0.25), (wx, wy + 0.2, z0 + 0.25), 0.25, mat, TYRE, sides=8, caps=True)
    lp.box_faces(b, (x + 0.05, y - 0.25, z0 + 1.0), (x + 0.45, y + 0.25, z0 + 1.35), mat, DARK)


# --- loads and trucks -------------------------------------------------------------------------

def pallet(b: MeshBuilder, x: float, y: float, z: float) -> float:
    """1.0 × 1.2 m wooden pallet with its corner at (x, y, z); returns its top height."""
    lp.box_faces(b, (x, y, z + 0.1), (x + 1.0, y + 1.2, z + 0.14), M["load"], WOOD)
    for rx in (x, x + 0.44, x + 0.88):
        lp.box_faces(b, (rx, y, z), (rx + 0.12, y + 1.2, z + 0.1), M["load"], lp.scale(WOOD, 0.85), skip=("-z", "+z"))
    return z + 0.14


def crate_pallet(b: MeshBuilder, x: float, y: float, z: float) -> None:
    """Pallet of open-sided egg crates, 2 × 2 × 3: the slots are dark bands (baked tint)."""
    top = pallet(b, x, y, z)
    solid, slot, gap = CRATE, lp.scale(CRATE, 0.5), lp.scale(CRATE, 0.4)
    levels, tints = [], []
    for k in range(3):
        cz0 = top + k * 0.3
        levels += [cz0 + 0.07, cz0 + 0.12, cz0 + 0.17, cz0 + 0.22, cz0 + 0.28, cz0 + 0.3]
        tints += [solid, slot, solid, slot, solid, gap]
    lp.banded_box(b, (x + 0.02, y + 0.02, top), (x + 0.98, y + 1.18, top + 0.88), M["load"], levels[:-2], tints[:-1], top_tint=lp.scale(CRATE, 0.85))


def carton_pallet(b: MeshBuilder, x: float, y: float, z: float) -> None:
    """Pallet of packed egg boxes under stretch film, with two strapping bands."""
    top = pallet(b, x, y, z)
    lp.box_faces(b, (x + 0.02, y + 0.02, top), (x + 0.98, y + 1.18, top + 1.0), M["load"], WRAP)
    for bx in (x + 0.3, x + 0.65):
        lp.box_faces(b, (bx, y + 0.005, top), (bx + 0.05, y + 1.195, top + 1.015), M["load"], WRAP_BAND, skip=("-z", "-x", "+x"))


# --- laying hens, cages and transport crates --------------------------------------------------
# Stylised and sober (docs/DA.md §04): simple volumes, regular groups, nothing that suggests
# distress. A hen is about 0.43 m long and 0.45 m tall to the comb: a plump body with a raised
# tail, a head held high, a red comb and a yellow beak, which is what reads from the terrace.
# Three levels of detail, chosen by what the terrace can see of each cage tier.

def hen(b: MeshBuilder, x: float, y: float, z: float, facing: int, brown: bool, seed: int, detail: int = 2) -> None:
    """One hen standing at (x, y, z), its head towards `facing` (±Y). `detail`: 2 with comb and
    beak, 1 without the beak, 0 a proxy for hens that are behind others."""
    k = 0.94
    phase = lp.rand(seed, 17)
    plumage = lp.scale(HEN_BROWN if brown else HEN_WHITE, 0.92 + 0.08 * lp.rand(seed, 19))

    def at(px: float, py: float, pz: float) -> Vector:
        return Vector((x + facing * px * k, y + facing * py * k, z + pz * k))

    def ph(pz: float, head: float):
        return (phase, min(1.0, pz / 0.47), head)

    if detail == 0:
        pts = [at(0, 0.14, 0.12), at(-0.1, -0.12, 0.1), at(0.1, -0.12, 0.1), at(0, -0.02, 0.33)]
        lp.add(b, pts, [(0, 3, 2), (0, 1, 3), (1, 2, 3)], M["animal_hen"], tint=lp.scale(plumage, 0.9), smooth=True, phase=[ph(0.12, 0.3), ph(0.1, 0), ph(0.1, 0), ph(0.33, 0.5)])
        return
    # Body: breast, a ring behind the shoulders, a ring at the hips, tail tip. Seen from above it
    # is an oval, from the side a boat with a raised stern.
    body = [(0, 0.165, 0.18),
            (0.095, 0.05, 0.11), (0.05, 0.05, 0.275), (-0.05, 0.05, 0.275), (-0.095, 0.05, 0.11),
            (0.065, -0.08, 0.12), (0.035, -0.08, 0.27), (-0.035, -0.08, 0.27), (-0.065, -0.08, 0.12),
            (0, -0.21, 0.37)]
    shade = [0.95, 0.72, 1.0, 1.0, 0.72, 0.72, 1.0, 1.0, 0.72, 0.6 if brown else 0.88]
    faces = [(0, 1 + (i + 1) % 4, 1 + i) for i in range(4)]
    faces += [(1 + i, 1 + (i + 1) % 4, 5 + (i + 1) % 4, 5 + i) for i in range(4)]
    faces += [(5 + i, 5 + (i + 1) % 4, 9) for i in range(4)]
    lp.add(b, [at(*p) for p in body], faces, M["animal_hen"], vert_tint=[lp.scale(plumage, s) for s in shade], smooth=True,
           phase=[ph(p[2], 0.4 if i == 0 else (0.3 if i in (2, 3) else 0.0)) for i, p in enumerate(body)])
    # Head and neck: face, two cheeks, crown above, throat below (inside the breast).
    head = [(0, 0.225, 0.355), (-0.045, 0.135, 0.35), (0.045, 0.135, 0.35), (0, 0.17, 0.42), (0, 0.12, 0.2)]
    head_faces = [(0, 1, 3), (1, 2, 3), (2, 0, 3), (1, 0, 4), (2, 1, 4), (0, 2, 4)]
    lp.add(b, [at(*p) for p in head], head_faces, M["animal_hen"], vert_tint=[plumage, plumage, plumage, plumage, lp.scale(plumage, 0.85)], smooth=True,
           phase=[ph(p[2], 0.0 if i == 4 else 1.0) for i, p in enumerate(head)])
    # Comb: what tells a hen from a white dot at a distance.
    comb = [(0, 0.215, 0.405), (-0.022, 0.13, 0.41), (0.022, 0.13, 0.41), (0, 0.165, 0.48)]
    lp.add(b, [at(*p) for p in comb], [(0, 1, 3), (1, 2, 3), (2, 0, 3)], M["animal_hen"], tint=HEN_COMB, phase=[ph(p[2], 1.0) for p in comb])
    if detail < 2:
        return
    beak = [(0.016, 0.215, 0.365), (-0.016, 0.215, 0.365), (0, 0.215, 0.335), (0, 0.27, 0.345)]
    lp.add(b, [at(*p) for p in beak], [(1, 0, 3), (2, 1, 3), (0, 2, 3)], M["animal_hen"], tint=HEN_BEAK, phase=[ph(p[2], 1.0) for p in beak])


def battery_cages(name: str, x0: float, x1: float, y0: float, y1: float, floor_z: float, parent, hens_parent) -> None:
    """Rows of stacked cages in the henhouse, three tiers, with one small group of hens in each
    compartment. Blocks are back to back, with an aisle between blocks. The frames become
    `name`, the hens one mesh per block under `hens_parent`.

    The terrace looks down from the south: the top tier shows from above, the lower tiers of the
    rows that face south show through their fronts, and the lower tiers of the rows that face
    north are behind them. Hens get the matching level of detail."""
    frame = MeshBuilder(recalc_normals=False)
    blocks, tiers = 4, 3
    pitch, depth = 1.5, 0.55
    aisle = ((y1 - y0) - blocks * 2 * depth) / (blocks + 1)
    count = int((x1 - x0) // pitch)
    xe = x0 + count * pitch
    for blk in range(blocks):
        yc = y0 + aisle * (blk + 1) + 2 * depth * blk + depth
        hens = MeshBuilder(recalc_normals=False)
        for t in range(tiers):
            z = floor_z + 0.35 + t * 0.55
            # Belt and wire floor of the two back-to-back rows.
            frame.box((x0, yc - depth, z), (xe, yc + depth, z + 0.03), M["cage_floor"], skip=("-z",))
        rows = ((yc - depth, -1, yc - depth, yc), (yc + depth, 1, yc, yc + depth))  # (front, facing, y range)
        for r, (front, facing, ya, yb) in enumerate(rows, start=blk * 2 + 1):
            for t in range(tiers):
                z = floor_z + 0.35 + t * 0.55
                for bar in (0.17, 0.34):
                    lo, hi = sorted((front, front + facing * 0.02))
                    frame.box((x0, lo, z + bar), (xe, hi, z + bar + 0.02), M["cage"], skip=("-x", "+x", "+y" if facing < 0 else "-y"))
                detail = 2 if t == tiers - 1 else (1 if facing < 0 else 0)
                for i in range(count):
                    cx = x0 + (i + 0.5) * pitch
                    for k in range(3):
                        seed = r * 7919 + t * 104729 + i * 31 + k * 17
                        jx = ((seed % 11) - 5) * 0.025
                        jy = (((seed // 11) % 7) - 3) * 0.012
                        hen(hens, cx + (k - 1) * 0.42 + jx, (ya + yb) / 2 + jy, z + 0.03, facing, (seed // 77) % 3 == 0, seed, detail)
            # Posts at each compartment boundary, full height of the stack.
            for i in range(count + 1):
                px = x0 + i * pitch
                frame.box((px - 0.018, front - 0.018, floor_z + 0.2), (px + 0.018, front + 0.018, floor_z + 0.35 + tiers * 0.55), M["cage"], skip=("-z", "+z"))
        hens.build(f"{hens_parent.name}_{blk + 1:02d}", parent=hens_parent)
    frame.build(name, parent=parent)


def hen_module(b: MeshBuilder, x: float, y: float, z: float) -> None:
    """Stack of five open transport crates (slotted sides) with hens in the top one."""
    w, d, h = 0.78, 0.56, 0.2
    levels, tints = [], []
    for k in range(5):
        z0 = z + k * h
        levels += [z0 + 0.06, z0 + 0.15, z0 + h - 0.012, z0 + h]
        tints += [HEN_CRATE, lp.scale(HEN_CRATE, 0.47), HEN_CRATE, lp.scale(HEN_CRATE, 0.42)]
    lp.banded_box(b, (x, y, z), (x + w, y + d, z + 5 * h - 0.01), M["load"], levels[:-2], tints[:-1], top_tint=lp.scale(HEN_CRATE, 0.52))
    top = z + 5 * h - 0.01
    for k in range(4):
        hen(b, x + 0.1 + k * 0.19, y + d / 2 + (0.07 if k % 2 else -0.07), top - 0.1, 1 if k % 2 else -1, k == 1, int(x * 131 + y * 71) + k, detail=2)


def unit_group(name: str, origin, cells: list[tuple[int, int]], unit, parent, step=(1.3, 1.5)):
    """Empty holding one mesh per unit (shown or hidden one by one by the timeline)."""
    group = empty(name, origin, parent)
    for i, (gx, gy) in enumerate(cells, start=1):
        b = MeshBuilder(recalc_normals=False)
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
    b.cylinder_along((-0.9, 0.6, 0.75), "Y", 0.28, 1.1, M["hub"], segments=8)
    for wy in (3.2, -2.6, -3.7):
        for wx in (-1.02, 1.02):
            b.cylinder_along((wx, wy, 0.52), "X", 0.52, 0.36, M["tyre"], segments=12)
            b.cylinder_along((wx + (0.18 if wx > 0 else -0.18), wy, 0.52), "X", 0.26, 0.02, M["hub"], segments=8)
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
