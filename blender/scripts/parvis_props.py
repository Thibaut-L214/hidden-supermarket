"""Forecourt, facade and volunteers (lot 4, docs/GDD.md §03.10, §09; docs/DA.md §03–04).

Natural light and human tones. The store sign carries a generic word only (no brand, no
logo); the volunteers' stand and leaflets are blank. Volunteers are stylised and calm: no
facial features, no caricature, standing aside the walkway with a leaflet in hand.
Coordinates are Blender store coordinates (metres, Z up), see build_store.py.
"""

from __future__ import annotations

import math

from common import MeshBuilder, bevel, box, glass, helper_volume, material

M: dict = {}


def materials() -> None:
    M["facade"] = material("M_FACADE_PANEL", "#E7DFCF", roughness=0.75)
    M["facade_joint"] = material("M_FACADE_JOINT", "#C9C0AE", roughness=0.8)
    M["parapet"] = material("M_PARAPET", "#D6CCB8", roughness=0.7)
    M["base"] = material("M_FACADE_BASE", "#9E978A", roughness=0.9)
    M["shop_glass"] = glass("M_SHOP_WINDOW", "#A9B9BF", alpha=0.55)
    M["mullion"] = material("M_MULLION", "#5E6468", roughness=0.4, metallic=0.5)
    M["canopy"] = material("M_CANOPY", "#F1ECE2", roughness=0.6)
    M["canopy_edge"] = material("M_CANOPY_EDGE", "#8FA889", roughness=0.6)
    M["canopy_light"] = material("M_CANOPY_LIGHT", "#FFFFFF", emission="#FFF2DD", emission_strength=1.2)
    M["sign"] = material("M_STORE_SIGN_PANEL", "#F7F4EC", roughness=0.6)
    M["paving_tile"] = material("M_PAVING_TILE", "#C9BEAB", roughness=0.85)
    M["paving_joint"] = material("M_PAVING_JOINT", "#ADA391", roughness=0.9)
    M["wood"] = material("M_BENCH_WOOD", "#A8865F", roughness=0.8)
    M["metal"] = material("M_STREET_METAL", "#5E6468", roughness=0.45, metallic=0.5)
    M["soil"] = material("M_PLANTER_SOIL", "#6E5E4C", roughness=1.0)
    M["shrub"] = material("M_PLANTER_SHRUB", "#7E9466", roughness=1.0)
    M["banner"] = material("M_STAND_BANNER", "#F3EFE6", roughness=0.7)
    M["skirt"] = material("M_STAND_SKIRT", "#8FA889", roughness=0.8)
    # People: varied skin tones and everyday clothes (docs/DA.md §03: human tones).
    M["skin"] = [material("M_PERSON_SKIN_A", "#C69C7B", roughness=0.7), material("M_PERSON_SKIN_B", "#8D5E43", roughness=0.7), material("M_PERSON_SKIN_C", "#E3C1A0", roughness=0.7)]
    M["hair"] = [material("M_PERSON_HAIR_DARK", "#2F2925", roughness=0.8), material("M_PERSON_HAIR_GREY", "#9A958E", roughness=0.8), material("M_PERSON_HAIR_BROWN", "#5C4331", roughness=0.8)]
    M["top"] = [material("M_PERSON_TOP_TEAL", "#5E8C84", roughness=0.9), material("M_PERSON_TOP_TERRACOTTA", "#B8735A", roughness=0.9), material("M_PERSON_TOP_MUSTARD", "#C9A548", roughness=0.9)]
    M["trousers"] = [material("M_PERSON_TROUSERS_NAVY", "#4F5660", roughness=0.9), material("M_PERSON_TROUSERS_SAND", "#A99A80", roughness=0.9), material("M_PERSON_TROUSERS_DENIM", "#5B6B7F", roughness=0.9)]
    M["shoes"] = material("M_PERSON_SHOES", "#3A3735", roughness=0.8)
    M["leaflet"] = material("M_LEAFLET_BLANK", "#FBFAF6", roughness=0.7)
    M["tote"] = material("M_TOTE_BAG", "#E8E0CF", roughness=0.9)


# --- facade -----------------------------------------------------------------------------------

def facade(half_x: float, half_y: float, wall: float, height: float, entrance_half: float, root) -> None:
    """South facade: base course, panel joints, shop windows, parapet all around the roof."""
    f = MeshBuilder()
    y = -half_y - wall
    out = y - 0.05
    for x0, x1 in ((-half_x - wall, -entrance_half - 0.1), (entrance_half + 0.1, half_x + wall)):
        f.box((x0, out, -0.1), (x1, y, 0.45), M["base"])
        f.box((x0, out + 0.02, 0.45), (x1, y, height), M["facade"])
        x = x0 + 1.5
        while x < x1 - 0.5:
            f.box((x - 0.012, out - 0.004, 0.45), (x + 0.012, out + 0.02, height), M["facade_joint"])
            x += 1.5
    # Shop windows either side of the entrance (opaque tinted glass with mullions).
    glazing = MeshBuilder()
    for sign in (-1, 1):
        wx0, wx1 = sorted((sign * (entrance_half + 1.0), sign * (entrance_half + 7.0)))
        glazing.box((wx0, out - 0.03, 0.5), (wx1, out - 0.01, 2.7), M["shop_glass"])
        mx = wx0
        while mx <= wx1 + 0.01:
            f.box((mx - 0.04, out - 0.06, 0.45), (mx + 0.04, out, 2.75), M["mullion"])
            mx += 1.5
        f.box((wx0 - 0.04, out - 0.06, 0.45), (wx1 + 0.04, out, 0.52), M["mullion"])
        f.box((wx0 - 0.04, out - 0.06, 2.68), (wx1 + 0.04, out, 2.75), M["mullion"])
    # Parapet around the flat roof, slightly proud of the walls.
    p_lo, p_hi = height, height + 0.7
    for x0, y0, x1, y1 in (
        (-half_x - wall - 0.06, -half_y - wall - 0.06, half_x + wall + 0.06, -half_y - wall + 0.3),
        (-half_x - wall - 0.06, half_y + wall - 0.3, half_x + wall + 0.06, half_y + wall + 0.06),
        (-half_x - wall - 0.06, -half_y - wall, -half_x - wall + 0.3, half_y + wall),
        (half_x + wall - 0.3, -half_y - wall, half_x + wall + 0.06, half_y + wall),
    ):
        f.box((x0, y0, p_lo), (x1, y1, p_hi), M["parapet"])
        f.box((x0 - 0.03, y0 - 0.03, p_hi), (x1 + 0.03, y1 + 0.03, p_hi + 0.06), M["mullion"])
    bevel(f.build("STORE_FACADE", parent=root), 0.01)
    pane = glazing.build("STORE_SHOP_WINDOWS", parent=root)
    pane["ao_skip"] = True

    # Generic sign above the canopy; its word is drawn at runtime from the `label` extra.
    sign = box("STORE_SIGN", (-2.6, out - 0.12, height - 0.35), (2.6, out - 0.04, height + 0.55), M["sign"], root)
    sign["label"] = "Supermarché"
    bevel(sign, 0.02)


def canopy(half_y: float, wall: float, root) -> None:
    """Cantilevered entrance canopy on two slender columns, warm soffit lights."""
    c = MeshBuilder()
    y0, y1 = -half_y - wall - 0.05, -half_y - wall - 3.0
    c.box((-3.6, y1, 3.0), (3.6, y0, 3.22), M["canopy"])
    c.box((-3.65, y1 - 0.05, 3.0), (3.65, y1 + 0.05, 3.32), M["canopy_edge"])
    for x in (-3.65, 3.55):
        c.box((x, y1, 3.0), (x + 0.1, y0, 3.32), M["canopy_edge"])
    for x in (-2.4, 0.0, 2.4):
        c.box((x - 0.8, y1 + 0.6, 2.98), (x + 0.8, y1 + 0.75, 3.0), M["canopy_light"])
    for x in (-3.35, 3.35):
        c.cylinder((x, y1 + 0.25, 0.0), 0.07, 3.0, M["metal"], segments=10)
    bevel(c.build("STORE_CANOPY", parent=root), 0.01)
    for side, x in (("L", -3.35), ("R", 3.35)):
        helper_volume(box(f"COL_CANOPY_{side}", (x - 0.15, y1 + 0.1, 0.0), (x + 0.15, y1 + 0.4, 3.0), None, root))


# --- forecourt furniture ----------------------------------------------------------------------

def paving(x0: float, y0: float, x1: float, y1: float, root) -> None:
    """Fine paving grid (per-vertex occlusion shows contact shadows) and flush joints."""
    g = MeshBuilder(recalc_normals=False)
    g.grid((x0, y0, 0.002), (x1 - x0, 0, 0), (0, y1 - y0, 0), (round((x1 - x0) / 0.6), round((y1 - y0) / 0.6)), M["paving_tile"])
    g.build("PARVIS_PAVING", parent=root)
    j = MeshBuilder()
    x = x0 + 1.2
    while x < x1:
        j.box((x - 0.01, y0, 0.002), (x + 0.01, y1, 0.005), M["paving_joint"])
        x += 1.2
    y = y0 + 1.2
    while y < y1:
        j.box((x0, y - 0.01, 0.002), (x1, y + 0.01, 0.005), M["paving_joint"])
        y += 1.2
    j.build("PARVIS_PAVING_JOINTS", parent=root)["ao_skip"] = True


def bench(b: MeshBuilder, x: float, y: float, along_y: bool) -> None:
    """Slatted bench, 1.8 m, on two metal frames."""
    length, depth = 1.8, 0.5
    sx, sy = (depth, length) if along_y else (length, depth)
    x0, y0 = x - sx / 2, y - sy / 2
    for k in range(4):
        if along_y:
            b.box((x0 + k * 0.125, y0, 0.44), (x0 + k * 0.125 + 0.1, y0 + sy, 0.48), M["wood"])
        else:
            b.box((x0, y0 + k * 0.125, 0.44), (x0 + sx, y0 + k * 0.125 + 0.1, 0.48), M["wood"])
    for t in (0.15, 0.85):
        if along_y:
            fy = y0 + sy * t
            b.box((x0 + 0.02, fy - 0.03, 0.0), (x0 + 0.06, fy + 0.03, 0.44), M["metal"])
            b.box((x0 + sx - 0.06, fy - 0.03, 0.0), (x0 + sx - 0.02, fy + 0.03, 0.44), M["metal"])
            b.box((x0 + 0.02, fy - 0.03, 0.38), (x0 + sx - 0.02, fy + 0.03, 0.44), M["metal"])
        else:
            fx = x0 + sx * t
            b.box((fx - 0.03, y0 + 0.02, 0.0), (fx + 0.03, y0 + 0.06, 0.44), M["metal"])
            b.box((fx - 0.03, y0 + sy - 0.06, 0.0), (fx + 0.03, y0 + sy - 0.02, 0.44), M["metal"])
            b.box((fx - 0.03, y0 + 0.02, 0.38), (fx + 0.03, y0 + sy - 0.02, 0.44), M["metal"])


def street_furniture(root) -> None:
    f = MeshBuilder()
    benches = ((-10.5, -15.0, True), (-10.5, -23.0, True), (10.5, -15.0, True), (10.5, -23.0, True))
    for x, y, along_y in benches:
        bench(f, x, y, along_y)
    # Bike hoops by the facade, east side; two bins by the walkway.
    for k in range(5):
        hx = 6.0 + k * 0.9
        for dx in (-0.3, 0.3):
            f.box((hx + dx - 0.03, -10.6, 0.0), (hx + dx + 0.03, -10.54, 0.8), M["metal"])
        f.box((hx - 0.33, -10.6, 0.77), (hx + 0.33, -10.54, 0.83), M["metal"])
    for x in (-2.8, 2.8):
        f.cylinder((x, -24.0, 0.0), 0.25, 0.85, M["metal"], segments=12)
        f.cylinder((x, -24.0, 0.85), 0.28, 0.06, M["mullion"], segments=12)
    bevel(f.build("PARVIS_FURNITURE", parent=root), 0.008)
    for i, (x, y, _) in enumerate(benches, start=1):
        helper_volume(box(f"COL_PARVIS_BENCH_{i}", (x - 0.3, y - 0.95, 0.0), (x + 0.3, y + 0.95, 0.5), None, root))
    helper_volume(box("COL_PARVIS_BIKES", (5.6, -10.75, 0.0), (10.0, -10.4, 0.85), None, root))
    for side, x in (("L", -2.8), ("R", 2.8)):
        helper_volume(box(f"COL_PARVIS_BIN_{side}", (x - 0.3, -24.3, 0.0), (x + 0.3, -23.7, 0.9), None, root))


def planter_greenery(planters: list[tuple[float, float, float, float]], root) -> None:
    """Soil and low shrubs inside the existing planters."""
    g = MeshBuilder()
    for k, (x0, y0, x1, y1) in enumerate(planters):
        g.box((x0 + 0.05, y0 + 0.05, 0.5), (x1 - 0.05, y1 - 0.05, 0.53), M["soil"])
        along_y = (y1 - y0) > (x1 - x0)
        length = (y1 - y0) if along_y else (x1 - x0)
        n = int(length / 1.1)
        for i in range(n):
            t = (i + 0.5) / n
            cx = (x0 + x1) / 2 if along_y else x0 + (x1 - x0) * t
            cy = y0 + (y1 - y0) * t if along_y else (y0 + y1) / 2
            r = 0.38 + 0.08 * ((i * 7 + k) % 3)
            g.ellipsoid((cx, cy, 0.62), (r, r, r * 0.8), M["shrub"], u=7, v=5)
    g.build("PARVIS_GREENERY", parent=root)


def stand(x0: float, y0: float, x1: float, y1: float, root) -> None:
    """Information table with a blank skirt, blank leaflet stacks and a blank roll-up banner."""
    s = MeshBuilder()
    s.box((x0, y0, 0.86), (x1, y1, 0.9), M["banner"])
    s.box((x0 + 0.02, y1 - 0.02, 0.05), (x1 - 0.02, y1, 0.86), M["skirt"])
    for x in (x0 + 0.05, x1 - 0.1):
        for y in (y0 + 0.05, y1 - 0.1):
            s.box((x, y, 0.0), (x + 0.05, y + 0.05, 0.86), M["metal"])
    for k in range(4):
        lx = x0 + 0.3 + k * 0.7
        s.box((lx, y0 + 0.2, 0.9), (lx + 0.3, y0 + 0.62, 0.9 + 0.03 + 0.01 * k), M["leaflet"])
    bx = x0 - 0.7
    s.box((bx, y1 - 0.25, 0.0), (bx + 0.6, y1 - 0.05, 0.08), M["metal"])
    s.box((bx + 0.02, y1 - 0.17, 0.08), (bx + 0.58, y1 - 0.15, 2.0), M["banner"])
    bevel(s.build("STAND_PARVIS", parent=root), 0.006)
    helper_volume(box("COL_STAND_PARVIS", (bx, y0, 0.0), (x1, y1, 0.9), None, root))


# --- volunteers -------------------------------------------------------------------------------

def volunteer(name: str, x: float, y: float, facing: float, variant: int, root) -> None:
    """Stylised standing volunteer, built facing +Y then turned by `facing` (radians about Z).

    variant selects skin tone, hair, clothes and a detail (tote bag, bun, cardigan length) so
    the three figures differ without any caricature. One forearm holds a leaflet forward.
    """
    v = variant % 3
    skin, hair, top, legs = M["skin"][v], M["hair"][v], M["top"][v], M["trousers"][v]
    b = MeshBuilder()
    # Shoes and legs.
    for lx in (-0.1, 0.1):
        b.box((lx - 0.06, -0.06, 0.0), (lx + 0.06, 0.16, 0.08), M["shoes"])
        b.frustum((lx, 0.0, 0.08), 0.065, 0.085, 0.8, legs, segments=8)
    # Torso (slightly tapered), longer top for variant 2.
    hem = 0.82 if v == 2 else 0.9
    b.frustum((0.0, 0.0, hem), 0.2, 0.23, 1.45 - hem, top, segments=10)
    b.ellipsoid((0.0, 0.0, 1.45), (0.22, 0.14, 0.07), top, u=10, v=5)
    b.cylinder((0.0, 0.0, 1.47), 0.045, 0.09, skin, segments=8)
    # Head and hair (bun for variant 1, short cap otherwise).
    b.ellipsoid((0.0, 0.01, 1.66), (0.095, 0.105, 0.12), skin, u=10, v=7)
    b.ellipsoid((0.0, -0.01, 1.71), (0.1, 0.105, 0.085), hair, u=10, v=6)
    if v == 1:
        b.ellipsoid((0.0, -0.09, 1.72), (0.05, 0.05, 0.05), hair, u=8, v=5)
    # Arms: left hangs relaxed; right forearm comes forward holding a leaflet.
    b.oriented_box((-0.26, 0.0, 1.2), (0.08, 0.08, 0.5), top, rot_x=0.05)
    b.ellipsoid((-0.27, 0.01, 0.92), (0.04, 0.035, 0.05), skin, u=6, v=4)
    b.oriented_box((0.26, 0.02, 1.25), (0.08, 0.08, 0.36), top, rot_x=0.15)
    b.oriented_box((0.26, 0.15, 1.08), (0.07, 0.3, 0.07), top, rot_x=-0.2)
    b.ellipsoid((0.26, 0.31, 1.05), (0.035, 0.045, 0.035), skin, u=6, v=4)
    b.oriented_box((0.26, 0.36, 1.07), (0.15, 0.002, 0.21), M["leaflet"], rot_x=-0.35)
    if v == 0:
        # Tote bag on the left shoulder.
        b.oriented_box((-0.3, -0.04, 1.0), (0.05, 0.32, 0.36), M["tote"], rot_x=0.05)
        b.oriented_box((-0.27, -0.04, 1.3), (0.02, 0.2, 0.3), M["tote"], rot_x=0.0)
    figure = b.build(name, (x, y, 0.0), root)
    figure.rotation_euler = (0.0, 0.0, facing)
    bevel(figure, 0.004)
    helper_volume(box(f"COL_{name}", (x - 0.3, y - 0.3, 0.0), (x + 0.3, y + 0.3, 1.8), None, root))
