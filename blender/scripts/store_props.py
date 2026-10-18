"""Detailed, procedural store furniture and goods (lot 1, docs/DA.md §02A, §04).

Stylised but credible: chamfered edges, varied product silhouettes, plain label bands. Nothing
here imitates a real brand: labels are colour bands only, price tags are blank.
Coordinates are Blender store coordinates (metres, Z up), see build_store.py.
"""

from __future__ import annotations

from common import MeshBuilder, bevel, box, glass, helper_volume, material

M: dict = {}

# Muted palette with moderate saturation (docs/DA.md §03, store).
PRODUCT_COLOURS = {
    "cream": "#EFE7D6",
    "sand": "#D9CBB0",
    "sage": "#B8C9B4",
    "olive": "#A7B08A",
    "sky": "#A9BCC8",
    "terracotta": "#C79A82",
    "mustard": "#D6C08A",
    "rose": "#CFA7A0",
    "white": "#F4F2EC",
    "slate": "#7E8A93",
}


def materials() -> None:
    for key, colour in PRODUCT_COLOURS.items():
        M[key] = material(f"M_GOODS_{key.upper()}", colour, roughness=0.65)
    M["metal"] = material("M_FIXTURE_METAL", "#D3D1CB", roughness=0.4, metallic=0.4)
    M["metal_dark"] = material("M_FIXTURE_DARK", "#6A6F73", roughness=0.5, metallic=0.4)
    M["tag"] = material("M_PRICE_TAG", "#FBFAF5", roughness=0.6)
    M["rail"] = material("M_PRICE_RAIL_ACCENT", "#9DB896", roughness=0.6)
    M["fridge_inner"] = material("M_FRIDGE_INNER", "#E9ECEC", roughness=0.5)
    M["fridge_light"] = material("M_FRIDGE_LIGHT", "#FFFFFF", emission="#EEF6FF", emission_strength=1.6)
    M["fridge_glass"] = glass("M_FRIDGE_GLASS", "#DCE8EE", alpha=0.22)
    M["rubber"] = material("M_RUBBER", "#3B3F42", roughness=0.9)
    M["screen"] = material("M_SCREEN_DARK", "#2C3236", roughness=0.2, metallic=0.2)
    M["seat"] = material("M_SEAT", "#5E8C84", roughness=0.8)
    M["mat"] = material("M_ENTRANCE_MAT", "#5A5E60", roughness=1.0)
    M["duct"] = material("M_DUCT", "#C9CBCB", roughness=0.35, metallic=0.6)
    M["tbar"] = material("M_CEILING_TBAR", "#E2DED5", roughness=0.6)


# --- goods ----------------------------------------------------------------------------------

def product(b: MeshBuilder, kind: str, cx: float, cy: float, z: float, size, body, accent, facing: int = 1) -> None:
    """One item standing at (cx, cy, z), its front towards `facing` (±X). size = (sx, sy, h);
    label band in `accent`. Faces that rest on the shelf or face the back panel are omitted."""
    sx, sy, h = size
    r = min(sx, sy) / 2
    back = "-x" if facing > 0 else "+x"
    hidden = ("-z", back)
    band = ("-z", "+z", back)
    if kind in ("box", "tall_box"):
        b.box((cx - sx / 2, cy - sy / 2, z), (cx + sx / 2, cy + sy / 2, z + h), body, hidden)
        b.box((cx - sx / 2 - 0.003, cy - sy / 2 - 0.003, z + h * 0.35), (cx + sx / 2 + 0.003, cy + sy / 2 + 0.003, z + h * 0.6), accent, band)
    elif kind == "bag":
        b.box((cx - sx / 2, cy - sy / 2, z), (cx + sx / 2, cy + sy / 2, z + h * 0.85), body, hidden)
        b.box((cx - sx / 2 + 0.02, cy - sy / 2, z + h * 0.85), (cx + sx / 2 - 0.02, cy + sy / 2, z + h), accent, hidden)
    elif kind == "brick":
        b.box((cx - sx / 2, cy - sy / 2, z), (cx + sx / 2, cy + sy / 2, z + h * 0.84), body, hidden)
        top = z + h * 0.84
        b.gable((cx - sx / 2, cy - sy / 2, top), (cx + sx / 2, cy + sy / 2, top + 0.002), h * 0.12, accent)
        b.box((cx - sx / 2 - 0.002, cy - sy / 2 - 0.002, z + h * 0.2), (cx + sx / 2 + 0.002, cy + sy / 2 + 0.002, z + h * 0.45), accent, band)
    elif kind == "bottle":
        b.cylinder((cx, cy, z), r, h * 0.6, body, segments=6)
        b.frustum((cx, cy, z + h * 0.6), r, r * 0.38, h * 0.14, body, segments=6)
        b.cylinder((cx, cy, z + h * 0.74), r * 0.36, h * 0.18, body, segments=6)
        b.cylinder((cx, cy, z + h * 0.92), r * 0.42, h * 0.08, accent, segments=6)
    elif kind == "jar":
        b.cylinder((cx, cy, z), r, h * 0.82, body, segments=7)
        b.cylinder((cx, cy, z + h * 0.82), r * 1.04, h * 0.18, accent, segments=7)
    elif kind == "can":
        b.cylinder((cx, cy, z), r, h, body, segments=7)
        b.cylinder((cx, cy, z + h * 0.3), r + 0.002, h * 0.4, accent, segments=7)
    elif kind == "pot":
        b.frustum((cx, cy, z), r * 0.8, r, h, body, segments=7)


# Footprint (sx, sy, h) per kind; sx is the depth into the shelf.
SIZES = {
    "box": (0.26, 0.2, 0.24),
    "tall_box": (0.22, 0.19, 0.35),
    "bag": (0.2, 0.17, 0.29),
    "brick": (0.09, 0.09, 0.25),
    "bottle": (0.09, 0.09, 0.32),
    "jar": (0.11, 0.11, 0.15),
    "can": (0.08, 0.08, 0.12),
    "pot": (0.09, 0.09, 0.09),
}

# Aisle categories (generic, no brand): product kind per shelf level, bottom to top.
AISLES = {
    "Épicerie": ("bag", "box", "jar", "box"),
    "Petit-déjeuner": ("tall_box", "jar", "box", "tall_box"),
    "Boissons": ("bottle", "brick", "can", "bottle"),
    "Hygiène": ("bottle", "box", "jar", "box"),
}

COLOUR_CYCLE = ("cream", "sage", "sand", "sky", "terracotta", "mustard", "rose", "olive", "white")


def shelf_row(b: MeshBuilder, kind: str, front_x: float, facing: int, y0: float, y1: float, z: float, seed: int) -> None:
    """Fills one shelf face front-first; facing = +1 when the face looks towards +X."""
    sx, sy, h = SIZES[kind]
    gap = 0.025 if sy > 0.12 else 0.015
    count = int((y1 - y0 + gap) // (sy + gap))
    offset = (y1 - y0 - (count * sy + (count - 1) * gap)) / 2
    cx = front_x - facing * (sx / 2 + 0.02)
    for i in range(count):
        cy = y0 + offset + sy / 2 + i * (sy + gap)
        # Small groups share a colour, as facings of one product would.
        colour = COLOUR_CYCLE[(seed + i // 3) % len(COLOUR_CYCLE)]
        accent = COLOUR_CYCLE[(seed + i // 3 + 4) % len(COLOUR_CYCLE)]
        product(b, kind, cx, cy, z, (sx, sy, h), M[colour], M[accent], facing)


def price_rail(b: MeshBuilder, x: float, facing: int, y0: float, y1: float, z: float, step: float) -> None:
    """Accent rail on a shelf edge with blank tags (no real prices)."""
    b.box((x - 0.012, y0, z - 0.035), (x + 0.012, y1, z + 0.03), M["rail"])
    y = y0 + step / 2
    while y < y1 - 0.04:
        tx = x + facing * 0.013
        b.box((tx - 0.002, y - 0.035, z - 0.03), (tx + 0.002, y + 0.035, z + 0.02), M["tag"])
        y += step


def gondola(name: str, x: float, y_start: float, modules: int, aisle: str, root, accent, sign_mat):
    """Double-sided gondola run along Y: uprights, back panel, shelves, rails, goods, end caps."""
    depth, height, length = 0.9, 1.8, 1.25
    run = modules * length
    # Goods are open shells (hidden faces dropped): keep their winding as built.
    frame, goods = MeshBuilder(), MeshBuilder(recalc_normals=False)
    mid = depth / 2
    levels = (0.14, 0.57, 1.0, 1.43)
    kinds = AISLES[aisle]

    frame.box((mid - 0.025, 0.0, 0.0), (mid + 0.025, run, height), M["metal"])
    frame.box((0.03, 0.0, 0.0), (depth - 0.03, run, 0.12), accent)
    frame.box((0.0, 0.0, height), (depth, run, height + 0.03), M["metal"])
    for m in range(modules + 1):
        y = m * length
        for px in (mid - 0.06, mid + 0.03):
            frame.box((px, y - 0.02, 0.0), (px + 0.03, y + 0.02, height), M["metal_dark"])
    for m in range(modules):
        y0, y1 = m * length + 0.03, (m + 1) * length - 0.03
        for level, z in enumerate(levels):
            for facing, front in ((-1, 0.0), (1, depth)):
                inner = mid - 0.03 if facing < 0 else mid + 0.03
                lo, hi = sorted((front, inner))
                frame.box((lo, y0, z - 0.02), (hi, y1, z + 0.01), M["metal"])
                price_rail(goods, front, facing, y0, y1, z, 0.25)
                shelf_row(goods, kinds[level], front, facing, y0, y1, z + 0.01, m * 7 + level * 3 + (facing > 0) * 5)
    for y0, y1 in ((-0.05, 0.0), (run, run + 0.05)):
        frame.box((0.0, y0, 0.0), (depth, y1, height + 0.05), accent)
        frame.box((0.05, y0 - 0.012, height + 0.14), (depth - 0.05, y1 + 0.012, height + 0.44), sign_mat)

    structure = bevel(frame.build(name, (x, y_start, 0.0), root), 0.006)
    # Goods stay unchamfered: at shelf distance a chamfer is invisible but costs triangles.
    goods.drop_bottom_caps().build(f"{name}_GOODS", parent=structure)
    helper_volume(box(f"COL_{name}", (x, y_start, 0.0), (x + depth, y_start + run, height), None, root))
    return structure


def aisle_sign(name: str, cx: float, cy: float, root, sign_mat) -> None:
    """Hanging aisle sign; its label is drawn at runtime (AISLE_SIGN_*)."""
    sign = box(name, (cx - 0.8, cy - 0.015, 3.0), (cx + 0.8, cy + 0.015, 3.42), sign_mat, root)
    bevel(sign, 0.008)
    cables = MeshBuilder()
    for dx in (-0.65, 0.65):
        cables.cylinder((cx + dx, cy, 3.42), 0.004, 1.08, M["metal_dark"], segments=6)
    cables.build(f"{name}_CABLES", parent=root)


# --- refrigerated cases ---------------------------------------------------------------------

def fridge_run(name: str, wall_x: float, facing: int, y_start: float, modules: int, root) -> None:
    """Upright glass-door cases against a side wall; facing = +1 when the doors look to +X."""
    depth, height, length = 0.85, 2.1, 1.25
    front = wall_x + facing * depth
    lo_x, hi_x = sorted((wall_x, front))
    run = modules * length
    body, goods, doors = MeshBuilder(), MeshBuilder(recalc_normals=False), MeshBuilder()

    body.box((lo_x, y_start, 0.0), (hi_x, y_start + run, 0.16), M["metal_dark"])
    body.box((lo_x, y_start, height), (hi_x, y_start + run, height + 0.32), M["metal"])
    body.box((front - facing * 0.02 - 0.01, y_start, height + 0.06), (front - facing * 0.02 + 0.01, y_start + run, height + 0.26), M["fridge_light"])
    back = wall_x + facing * 0.04
    body.box((min(wall_x, back), y_start, 0.16), (max(wall_x, back), y_start + run, height), M["fridge_inner"])
    kinds = ("brick", "pot", "brick", "bottle", "brick")
    for m in range(modules + 1):
        y = y_start + m * length
        body.box((lo_x, y - 0.03, 0.0), (hi_x, y + 0.03, height + 0.32), M["metal"])
    for m in range(modules):
        y0, y1 = y_start + m * length + 0.04, y_start + (m + 1) * length - 0.04
        for level, z in enumerate((0.2, 0.58, 0.96, 1.34, 1.72)):
            body.box((min(back, front - facing * 0.06), y0, z - 0.012), (max(back, front - facing * 0.06), y1, z), M["metal"])
            shelf_row(goods, kinds[level], front - facing * 0.07, facing, y0, y1, z, m * 5 + level * 2 + 11)
        for half in range(2):
            d0 = y0 + half * (y1 - y0) / 2 + 0.01
            d1 = y0 + (half + 1) * (y1 - y0) / 2 - 0.01
            doors.box((front - 0.008, d0, 0.18), (front + 0.008, d1, height - 0.02), M["fridge_glass"])
            hy = d1 - 0.06 if half == 0 else d0 + 0.06
            hx = front + facing * 0.035
            body.box((min(front, hx), hy - 0.012, 0.75), (max(front, hx), hy + 0.012, 1.55), M["metal_dark"])
            body.box((front - 0.02, d0 - 0.01, 0.16), (front + 0.02, d1 + 0.01, 0.2), M["metal"])
            body.box((front - 0.02, d0 - 0.01, height - 0.04), (front + 0.02, d1 + 0.01, height), M["metal"])

    structure = bevel(body.build(name, parent=root), 0.006)
    goods.drop_bottom_caps().build(f"{name}_GOODS", parent=structure)
    pane = doors.build(f"{name}_DOORS", parent=structure)
    pane["ao_skip"] = True
    # Collider includes the door handles on the aisle side.
    col_lo, col_hi = (lo_x, hi_x + 0.05) if facing > 0 else (lo_x - 0.05, hi_x)
    helper_volume(box(f"COL_{name}", (col_lo, y_start, 0.0), (col_hi, y_start + run, height), None, root))


# --- checkout, carts, baskets ----------------------------------------------------------------

def checkout(name: str, x0: float, x1: float, root) -> None:
    c = MeshBuilder()
    y0, y1 = -6.4, -5.6
    c.box((x0, y0, 0.0), (x1, y1, 0.08), M["metal_dark"])
    c.box((x0, y0, 0.08), (x1, y1, 0.82), M["metal"])
    c.box((x0, y0 + 0.08, 0.82), (x1 - 0.7, y1 - 0.08, 0.86), M["rubber"])
    for k in range(int((x1 - 0.7 - x0) / 0.6) + 1):
        c.cylinder_along((x0 + 0.05 + k * 0.6, (y0 + y1) / 2, 0.85), "Y", 0.02, y1 - y0 - 0.2, M["metal_dark"], segments=6)
    c.box((x0, y0, 0.82), (x0 + 0.04, y1, 0.92), M["metal"])
    # Scanner window, card terminal on a post, bagging shelf.
    c.box((x1 - 0.68, y0 + 0.15, 0.84), (x1 - 0.38, y1 - 0.15, 0.85), M["screen"])
    c.cylinder((x1 - 0.2, y1 - 0.12, 0.82), 0.015, 0.22, M["metal_dark"], segments=6)
    c.box((x1 - 0.27, y1 - 0.18, 1.04), (x1 - 0.13, y1 - 0.06, 1.18), M["screen"])
    c.box((x1 - 0.35, y0 - 0.25, 0.7), (x1, y0, 0.73), M["metal"])
    # Cashier seat behind the counter.
    seat_y = y1 + 0.45
    c.cylinder(((x0 + x1) / 2 + 0.3, seat_y, 0.0), 0.2, 0.03, M["metal_dark"], segments=10)
    c.cylinder(((x0 + x1) / 2 + 0.3, seat_y, 0.03), 0.025, 0.6, M["metal"], segments=6)
    c.cylinder(((x0 + x1) / 2 + 0.3, seat_y, 0.63), 0.2, 0.06, M["seat"], segments=12)
    bevel(c.build(name, parent=root), 0.006)
    helper_volume(box(f"COL_{name}", (x0, y0 - 0.25, 0.0), (x1, y1, 1.2), None, root))


def cart(b: MeshBuilder, x: float, y: float) -> None:
    """Wire trolley facing -Y (handle at +Y); thin bars, small casters."""
    w, l, z0, z1 = 0.52, 0.85, 0.32, 0.9
    t = 0.008
    for xx in (x - w / 2, x + w / 2):
        b.box((xx - t, y, z0), (xx + t, y + l, z0 + t * 2), M["metal"])
        b.box((xx - t, y, z1 - t * 2), (xx + t, y + l, z1), M["metal"])
        for k in range(6):
            yy = y + k * l / 5
            b.box((xx - t, yy - t, z0), (xx + t, yy + t, z1), M["metal"])
    for k in range(7):
        xx = x - w / 2 + k * w / 6
        b.box((xx - t, y, z0), (xx + t, y + l, z0 + t * 2), M["metal"])
        b.box((xx - t, y - t, z0), (xx + t, y + t, z1), M["metal"])
        b.box((xx - t, y + l - t, z0), (xx + t, y + l + t, z1), M["metal"])
    b.cylinder_along((x, y + l + 0.12, z1 + 0.08), "X", 0.018, w + 0.04, M["seat"], segments=6)
    for xx in (x - w / 2 + 0.03, x + w / 2 - 0.03):
        b.box((xx - 0.01, y + l, z1 - 0.02), (xx + 0.01, y + l + 0.12, z1 + 0.09), M["metal"])
        for yy in (y + 0.05, y + l - 0.05):
            b.box((xx - 0.012, yy - 0.012, 0.08), (xx + 0.012, yy + 0.012, z0), M["metal"])
            b.cylinder_along((xx, yy, 0.05), "X", 0.045, 0.03, M["rubber"], segments=10)


def carts_and_baskets(root) -> None:
    carts = MeshBuilder()
    for k in range(3):
        cart(carts, 9.4, -8.75 + k * 0.32)
    bevel(carts.build("STORE_CARTS", parent=root), 0.003)
    helper_volume(box("COL_STORE_CARTS", (9.1, -8.8, 0.0), (9.7, -7.0, 1.0), None, root))

    baskets = MeshBuilder()
    for k in range(5):
        z = 0.02 + k * 0.07
        baskets.box((-9.65, -8.6, z), (-9.15, -8.25, z + 0.02), M["seat"])
        for x0, x1, y0, y1 in ((-9.65, -9.15, -8.6, -8.58), (-9.65, -9.15, -8.27, -8.25), (-9.65, -9.63, -8.6, -8.25), (-9.17, -9.15, -8.6, -8.25)):
            baskets.box((x0, y0, z), (x1, y1, z + 0.2), M["seat"])
    bevel(baskets.build("STORE_BASKETS", parent=root), 0.003)
    helper_volume(box("COL_STORE_BASKETS", (-9.7, -8.65, 0.0), (-9.1, -8.2, 0.6), None, root))


# --- ceiling and entrance --------------------------------------------------------------------

def ceiling(half_x: float, half_y: float, height: float, root) -> None:
    bars = MeshBuilder()
    step = 1.2
    x = -half_x + step
    while x < half_x:
        bars.box((x - 0.012, -half_y, height - 0.02), (x + 0.012, half_y, height), M["tbar"])
        x += step
    y = -half_y + step
    while y < half_y:
        bars.box((-half_x, y - 0.012, height - 0.02), (half_x, y + 0.012, height), M["tbar"])
        y += step
    # Flush with the ceiling: kept out of the occlusion bake (no dark lines along the bars).
    bars.build("STORE_CEILING_GRID", parent=root)["ao_skip"] = True

    ducts = MeshBuilder()
    for dx in (-2.4, 2.4):
        ducts.cylinder_along((dx, 0.0, height - 0.45), "Y", 0.22, 2 * half_y - 0.4, M["duct"], segments=16)
        y = -half_y + 1.2
        while y < half_y - 0.6:
            ducts.cylinder_along((dx, y, height - 0.45), "Y", 0.232, 0.05, M["duct"], segments=16)
            ducts.box((dx - 0.01, y - 0.01, height - 0.45), (dx + 0.01, y + 0.01, height - 0.02), M["metal_dark"])
            y += 2.4
    bevel(ducts.build("STORE_DUCTS", parent=root), 0.004)


def entrance(half_y: float, wall: float, opening_half: float, root) -> None:
    e = MeshBuilder()
    y0, y1 = -half_y - wall - 0.02, -half_y + 0.02
    for x in (-opening_half - 0.08, opening_half):
        e.box((x, y0, 0.0), (x + 0.08, y1, 2.7), M["metal_dark"])
    e.box((-opening_half - 0.08, y0, 2.6), (opening_half + 0.08, y1, 2.7), M["metal_dark"])
    e.box((-0.2, y1, 2.72), (0.2, y1 + 0.12, 2.82), M["metal"])
    e.box((-1.4, -half_y + 0.05, 0.0), (1.4, -half_y + 1.3, 0.006), M["mat"])
    bevel(e.build("STORE_ENTRANCE_FRAME", parent=root), 0.004)
