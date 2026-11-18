"""Detailed, procedural store furniture and goods (lot 1, docs/DA.md §02A, §04).

Stylised but credible: chamfered edges, varied product silhouettes, printed packaging. Nothing
here imitates a real brand: every printed face comes from the fictitious atlas of
make_store_textures.py (colour bands, pictograms, bars standing for text; no price, no claim).
Coordinates are Blender store coordinates (metres, Z up), see build_store.py.
"""

from __future__ import annotations

import math

import bpy

import pack_atlas as atlas
from common import MeshBuilder, bevel, box, glass, helper_volume, material

M: dict = {}

# UV0 authored by the builders for the printed atlas; objects made only of such faces carry the
# `uv_authored` property, so the export keeps their UVs (blender/scripts/surfaces.py).
UV_NAME = "UVMap"


def materials() -> None:
    # Every printed face of the store (packaging, shelf-edge labels, posters) shares this one.
    M["pack"] = material(atlas.MATERIAL, "#FFFFFF", roughness=0.5)
    M["metal"] = material("M_FIXTURE_METAL", "#D3D1CB", roughness=0.4, metallic=0.4)
    M["metal_dark"] = material("M_FIXTURE_DARK", "#6A6F73", roughness=0.5, metallic=0.4)
    M["rail"] = material("M_PRICE_RAIL_ACCENT", "#9DB896", roughness=0.6)
    M["fridge_inner"] = material("M_FRIDGE_INNER", "#F3F6F6", roughness=0.4)
    M["fridge_light"] = material("M_FRIDGE_LIGHT", "#FFFFFF", emission="#EEF6FF", emission_strength=1.6)
    # LED strips inside the refrigerated cases: cool white, bright enough to bloom slightly
    # (the runtime's bloom threshold is 1.05, linear).
    M["fridge_led"] = material("M_FRIDGE_LED", "#FFFFFF", emission="#E6F1FF", emission_strength=3.5)
    M["fridge_glass"] = glass("M_FRIDGE_GLASS", "#DCE8EE", alpha=0.22)
    M["rubber"] = material("M_RUBBER", "#3B3F42", roughness=0.9)
    M["screen"] = material("M_SCREEN_DARK", "#2C3236", roughness=0.2, metallic=0.2)
    M["seat"] = material("M_SEAT", "#5E8C84", roughness=0.8)
    M["mat"] = material("M_ENTRANCE_MAT", "#5A5E60", roughness=1.0)
    M["duct"] = material("M_DUCT", "#C9CBCB", roughness=0.35, metallic=0.6)
    M["tbar"] = material("M_CEILING_TBAR", "#E2DED5", roughness=0.6)


# --- printed faces ----------------------------------------------------------------------------
# Geometry mapped on the atlas. Faces are built with their final winding and UVs; use a builder
# with recalc_normals=False (these are open shells: hidden faces are never built).

_CORNERS = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))
_FACES = {
    "-z": (0, 3, 2, 1), "+z": (4, 5, 6, 7), "-y": (0, 1, 5, 4),
    "+x": (1, 2, 6, 5), "+y": (2, 3, 7, 6), "-x": (3, 0, 4, 7),
}
# Image axes on each face, seen from outside: (s, t) from the corner's (fx, fy, fz) in {0, 1}.
_ST = {
    "+x": lambda f: (f[1], f[2]), "-x": lambda f: (1 - f[1], f[2]),
    "+y": lambda f: (1 - f[0], f[2]), "-y": lambda f: (f[0], f[2]),
    "+z": lambda f: (f[0], f[1]), "-z": lambda f: (f[0], 1 - f[1]),
}


def _uv_layer(b: MeshBuilder):
    layers = b.bm.loops.layers.uv
    return layers.get(UV_NAME) or layers.new(UV_NAME)


def pack_box(b: MeshBuilder, lo, hi, faces: dict) -> None:
    """Axis-aligned box of which only `faces` exist: {"+x": (u0, v0, u1, v1), ...}. Each image
    stands upright seen from outside; on a top face u runs along X."""
    layer = _uv_layer(b)  # before any element: a new layer reallocates their custom data
    slot = b._slot(M["pack"])
    verts: dict[int, object] = {}
    for key, (u0, v0, u1, v1) in faces.items():
        index = _FACES[key]
        for i in index:
            if i not in verts:
                verts[i] = b.bm.verts.new(tuple(hi[a] if _CORNERS[i][a] else lo[a] for a in range(3)))
        face = b.bm.faces.new([verts[i] for i in index])
        face.material_index = slot
        for loop, i in zip(face.loops, index):
            s, t = _ST[key](_CORNERS[i])
            loop[layer].uv = (u0 + s * (u1 - u0), v0 + t * (v1 - v0))


def pack_quad(b: MeshBuilder, points, rect, facing, smooth: bool = False) -> None:
    """One face through `points` (image corners: bottom-left, bottom-right, top-right, top-left;
    three points for a triangle, the last one at the top centre), looking towards `facing`."""
    layer = _uv_layer(b)
    u0, v0, u1, v1 = rect
    corners = ((u0, v0), (u1, v0), (u1, v1), (u0, v1)) if len(points) == 4 else ((u0, v0), (u1, v0), ((u0 + u1) / 2, v1))
    face = b.bm.faces.new([b.bm.verts.new(p) for p in points])
    face.material_index = b._slot(M["pack"])
    face.smooth = smooth
    for loop, uv in zip(face.loops, corners):
        loop[layer].uv = uv
    face.normal_update()
    if sum(n * f for n, f in zip(face.normal, facing)) < 0:
        face.normal_flip()


def pack_cylinder(b: MeshBuilder, cx: float, cy: float, profile, wrap, facing: int, cap=None, vspan=(0.0, 1.0), segments: int = 6) -> None:
    """Lathe of `profile` [(radius, z), ...] around a vertical axis. The label wraps once around
    (u), its middle towards the aisle (`facing` = ±1 along X) and the seam at the back; v follows
    the height over `vspan` of the wrap. `cap` maps a lid seen from above on the top ring."""
    layer = _uv_layer(b)
    slot = b._slot(M["pack"])
    u0, v0, u1, v1 = wrap
    z0, z1 = profile[0][1], profile[-1][1]
    start = math.pi if facing > 0 else 0.0  # seam away from the aisle
    rings = []
    for radius, z in profile:
        rings.append([
            b.bm.verts.new((cx + radius * math.cos(start + 2 * math.pi * k / segments), cy + radius * math.sin(start + 2 * math.pi * k / segments), z))
            for k in range(segments)
        ])

    def v_at(z: float) -> float:
        t = vspan[0] + (vspan[1] - vspan[0]) * (z - z0) / (z1 - z0)
        return v0 + t * (v1 - v0)

    for i in range(len(profile) - 1):
        va, vb = v_at(profile[i][1]), v_at(profile[i + 1][1])
        for k in range(segments):
            n = (k + 1) % segments
            face = b.bm.faces.new((rings[i][k], rings[i][n], rings[i + 1][n], rings[i + 1][k]))
            face.material_index = slot
            face.smooth = True
            ua, ub = u0 + (u1 - u0) * k / segments, u0 + (u1 - u0) * (k + 1) / segments
            for loop, uv in zip(face.loops, ((ua, va), (ub, va), (ub, vb), (ua, vb))):
                loop[layer].uv = uv
    if cap is not None:
        c0, d0, c1, d1 = cap
        face = b.bm.faces.new(rings[-1])
        face.material_index = slot
        for loop, k in zip(face.loops, range(segments)):
            a = 2 * math.pi * k / segments
            loop[layer].uv = ((c0 + c1) / 2 + (c1 - c0) / 2 * math.cos(a), (d0 + d1) / 2 + (d1 - d0) / 2 * math.sin(a))


# --- goods ----------------------------------------------------------------------------------

# Footprint (sx, sy, h) per kind; sx is the depth of one pack into the shelf.
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


def product(b: MeshBuilder, kind: str, variant: int, cy: float, z: float, front: float, back: float, facing: int) -> None:
    """One facing of a product at `cy`, its printed front at x = `front` looking towards `facing`
    (±X). Only what a shopper can see is built: boxes are one shell from the shelf edge to
    `back` whose top shows the packs standing behind; short jars, cans and pots get a row of
    lids behind them; nothing has a base or a back."""
    sx, sy, h = SIZES[kind]
    rects = {name: atlas.uv(rect) for name, rect in atlas.block(kind, variant).items()}
    front_key = "+x" if facing > 0 else "-x"
    lo_x, hi_x = min(front, back), max(front, back)
    y0, y1 = cy - sy / 2, cy + sy / 2
    if kind in ("box", "tall_box", "bag"):
        pack_box(b, (lo_x, y0, z), (hi_x, y1, z + h), {front_key: rects["front"], "-y": rects["side"], "+y": rects["side"], "+z": rects["top"]})
        return
    if kind == "brick":
        body, ridge = z + h * 0.84, z + h
        pack_box(b, (lo_x, y0, z), (hi_x, y1, body), {front_key: rects["front"], "-y": rects["side"], "+y": rects["side"]})
        for side, ya in ((-1, y0), (1, y1)):
            pack_quad(b, ((front, ya, body), (back, ya, body), (back, cy, ridge), (front, cy, ridge)), rects["top"], (0.0, side, 1.0))
        u0, v0, u1, v1 = rects["top"]
        plain = (u0 + (u1 - u0) * 0.04, v0 + (v1 - v0) * 0.62, u0 + (u1 - u0) * 0.2, v0 + (v1 - v0) * 0.9)
        pack_quad(b, ((front, y0, body), (front, y1, body), (front, cy, ridge)), plain, (facing, 0.0, 0.0))
        return
    r = sy / 2
    cx = front - facing * r
    if kind == "bottle":
        pack_cylinder(b, cx, cy, ((r, z), (r, z + h * 0.6), (r * 0.4, z + h * 0.74), (r * 0.4, z + h)), rects["wrap"], facing, rects["cap"])
        return
    if kind == "jar":
        pack_cylinder(b, cx, cy, ((r, z), (r, z + h * 0.82)), rects["wrap"], facing, vspan=(0.0, 0.82))
        pack_cylinder(b, cx, cy, ((r * 1.05, z + h * 0.82), (r * 1.05, z + h)), rects["wrap"], facing, rects["cap"], vspan=(0.82, 1.0))
    elif kind == "can":
        pack_cylinder(b, cx, cy, ((r, z), (r, z + h)), rects["wrap"], facing, rects["cap"])
    else:  # pot
        pack_cylinder(b, cx, cy, ((r * 0.8, z), (r, z + h)), rects["wrap"], facing, rects["cap"])
    # The rows behind: up to four lids seen from above, one quad.
    behind = front - facing * (sy + 0.006)
    rows = min(4, int(abs(back - behind) // sy))
    if rows > 0:
        u0, v0, u1, v1 = rects["top"]
        end = behind - facing * rows * sy
        top = z + h * 0.985
        pack_quad(b, ((behind, y0, top), (end, y0, top), (end, y1, top), (behind, y1, top)), (u0, v0, u0 + (u1 - u0) * rows / 4, v1), (0.0, 0.0, 1.0))


def shelf_row(b: MeshBuilder, kind: str, front_x: float, facing: int, y0: float, y1: float, z: float, seed: int, back_x: float) -> None:
    """Fills one shelf face; facing = +1 when the face looks towards +X. Packs reach `back_x`."""
    _, sy, _ = SIZES[kind]
    gap = 0.025 if sy > 0.12 else 0.015
    count = int((y1 - y0 + gap) // (sy + gap))
    offset = (y1 - y0 - (count * sy + (count - 1) * gap)) / 2
    front = front_x - facing * 0.02
    for i in range(count):
        cy = y0 + offset + sy / 2 + i * (sy + gap)
        # Small groups share a design, as facings of one product would.
        variant = (seed + i // 3) % atlas.variants(kind)
        product(b, kind, variant, cy, z, front, back_x, facing)


def rail_labels(b: MeshBuilder, x: float, facing: int, y0: float, y1: float, z: float, seed: int, cells: int = 5) -> None:
    """Printed shelf-edge strip at x, looking towards `facing`: `cells` atlas cells side by side,
    each a length of accent rail carrying one label (bars for text, no price)."""
    step = (y1 - y0) / cells
    for k in range(cells):
        pick = (seed * 7 + k * 3) % 11
        rect = atlas.uv(atlas.rail(3 if pick == 0 else pick % 3))
        ya, yb = (y0 + k * step, y0 + (k + 1) * step) if facing > 0 else (y0 + (k + 1) * step, y0 + k * step)
        pack_quad(b, ((x, ya, z - 0.035), (x, yb, z - 0.035), (x, yb, z + 0.03), (x, ya, z + 0.03)), rect, (facing, 0.0, 0.0))


def price_rail(b: MeshBuilder, x: float, facing: int, y0: float, y1: float, z: float, seed: int) -> None:
    """Accent rail on a shelf edge: printed front, plain top and underside."""
    plain = atlas.uv(atlas.swatch("rail"), 8)
    face = x + facing * 0.012
    rail_labels(b, face, facing, y0, y1, z, seed)
    for zz, up in ((z + 0.03, 1.0), (z - 0.035, -1.0)):
        pack_quad(b, ((x - 0.012, y0, zz), (x + 0.012, y0, zz), (x + 0.012, y1, zz), (x - 0.012, y1, zz)), plain, (0.0, 0.0, up))


def gondola(name: str, x: float, y_start: float, modules: int, aisle: str, root, accent, sign_mat):
    """Double-sided gondola run along Y: uprights, back panel, shelves, rails, goods, end caps."""
    depth, height, length = 0.9, 1.8, 1.25
    run = modules * length
    # Goods are open shells mapped on the printed atlas: one material, windings as built.
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
                seed = m * 7 + level * 3 + (facing > 0) * 5
                price_rail(goods, front, facing, y0, y1, z, seed)
                shelf_row(goods, kinds[level], front, facing, y0, y1, z + 0.01, seed, inner + facing * 0.005)
    for y0, y1 in ((-0.05, 0.0), (run, run + 0.05)):
        frame.box((0.0, y0, 0.0), (depth, y1, height + 0.05), accent)
        frame.box((0.05, y0 - 0.012, height + 0.14), (depth - 0.05, y1 + 0.012, height + 0.44), sign_mat)

    structure = bevel(frame.build(name, (x, y_start, 0.0), root), 0.006)
    goods.build(f"{name}_GOODS", parent=structure)["uv_authored"] = True
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

def bake_light(name: str, location, towards_x: int, height: float, width: float, watts: float) -> None:
    """Area light used by the lightmap and environment bakes only (lights are not exported): it
    stands for the LED strips of a refrigerated case, whose emissive meshes are too thin to light
    the interior in a bake. Shines along ±X, invisible to the camera."""
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = height, width
    data.energy = watts
    data.color = (0.9, 0.95, 1.0)
    light = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (0.0, -towards_x * math.pi / 2, 0.0)  # an area light shines along its -Z
    light.visible_camera = False


def fridge_run(name: str, wall_x: float, facing: int, y_start: float, modules: int, root) -> None:
    """Upright glass-door cases against a side wall; facing = +1 when the doors look to +X.
    White liner, LED strips behind the door posts and under the canopy, printed shelf edges."""
    depth, height, length = 0.85, 2.1, 1.25
    front = wall_x + facing * depth
    lo_x, hi_x = sorted((wall_x, front))
    run = modules * length
    body, goods, doors, leds = MeshBuilder(), MeshBuilder(recalc_normals=False), MeshBuilder(), MeshBuilder()

    def span(a: float, b: float) -> tuple[float, float]:
        return (a, b) if a < b else (b, a)

    back = wall_x + facing * 0.04
    inner = front - facing * 0.06  # front edge of the shelves, behind the doors
    ix0, ix1 = span(back, inner)
    body.box((lo_x, y_start, 0.0), (hi_x, y_start + run, 0.16), M["metal_dark"])
    body.box((lo_x, y_start, height), (hi_x, y_start + run, height + 0.32), M["metal"])
    body.box((front - facing * 0.02 - 0.01, y_start, height + 0.06), (front - facing * 0.02 + 0.01, y_start + run, height + 0.26), M["fridge_light"])
    # Liner: back, floor and ceiling of the cold space.
    bx0, bx1 = span(wall_x, back)
    body.box((bx0, y_start, 0.16), (bx1, y_start + run, height), M["fridge_inner"])
    body.box((ix0, y_start, 0.16), (ix1, y_start + run, 0.175), M["fridge_inner"])
    body.box((ix0, y_start, height - 0.015), (ix1, y_start + run, height), M["fridge_inner"])
    px0, px1 = span(inner, front)
    kinds = ("brick", "pot", "brick", "bottle", "brick")
    for m in range(modules + 1):
        y = y_start + m * length
        if m in (0, modules):  # closed end of the run
            body.box((lo_x, y - 0.03, 0.0), (hi_x, y + 0.03, height + 0.32), M["metal"])
            inside = y + 0.03 if m == 0 else y - 0.036
            body.box((ix0, inside, 0.175), (ix1, inside + 0.006, height - 0.015), M["fridge_inner"])
        else:  # door post in front, thin liner partition behind
            body.box((px0, y - 0.03, 0.0), (px1, y + 0.03, height + 0.32), M["metal"])
            body.box((ix0, y - 0.012, 0.175), (ix1, y + 0.012, height - 0.015), M["fridge_inner"])
    for m in range(modules):
        y0, y1 = y_start + m * length + 0.04, y_start + (m + 1) * length - 0.04
        for level, z in enumerate((0.2, 0.58, 0.96, 1.34, 1.72)):
            body.box((ix0, y0, z - 0.012), (ix1, y1, z), M["fridge_inner"])
            seed = m * 5 + level * 2 + 11
            rail_labels(goods, inner + facing * 0.002, facing, y0, y1, z - 0.012, seed)
            shelf_row(goods, kinds[level], inner - facing * 0.01, facing, y0, y1, z, seed, back + facing * 0.01)
        # LED strips: one down each side of the bay, one under the canopy.
        lx0, lx1 = span(inner + facing * 0.012, inner + facing * 0.026)
        for ya in (y0 - 0.008, y1 - 0.006):
            leds.box((lx0, ya, 0.2), (lx1, ya + 0.014, height - 0.04), M["fridge_led"])
        leds.box((lx0, y0 + 0.01, height - 0.032), (lx1, y1 - 0.01, height - 0.018), M["fridge_led"])
        bake_light(f"BAKE_{name}_{m + 1:02d}", (inner + facing * 0.03, (y0 + y1) / 2, 0.2 + (height - 0.24) / 2), -facing, height - 0.3, y1 - y0 - 0.1, 2.5)
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
    # Lit from within by the strips: the goods take no baked occlusion (it would read as black).
    stock = goods.build(f"{name}_GOODS", parent=structure)
    stock["uv_authored"] = True
    stock["ao_skip"] = True
    leds.build(f"{name}_LEDS", parent=structure)["ao_skip"] = True
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
