"""Procedural landscape around the terraces (lot 3): relief, field patchwork with crop rows,
roads with wear and markings, hedgerows, stylised trees, perimeter fence and a power line.

Everything is deterministic (fixed hashes and Blender's Perlin noise), schematic and generic:
no claim about a real site. The relief is flat where buildings and roads stand, rises behind
the store into the plateau that carries the forecourt, and rolls gently towards the horizon.
Coordinates are the terrace module's Blender frame (metres, Z up).

Seen from a raised terrace, 30 to 300 m away: shapes are faceted and low-poly, colour variation
is baked per face corner (lowpoly.TINT, multiplied into COLOR_0 at export) so each family of
objects needs a single material, and mid-scale detail (crop rows, furrows, wheel tracks) comes
from tileable textures bound by material name (blender/textures/surfaces.json).

Foliage materials start with `M_FOLIAGE_` (canopies and hedges, not trunks) and their meshes
carry `_PHASE` (see lowpoly.py) for the runtime's wind sway.
"""

from __future__ import annotations

import math

from mathutils import Vector, noise

import lowpoly as lp
from common import MeshBuilder, material

M: dict = {}

Rect = tuple[float, float, float, float]  # x0, y0, x1, y1
Road = tuple[tuple[float, float], tuple[float, float], float]  # a, b, width (axis-aligned)

# Gravel shoulder on each side of a road, metres.
SHOULDER = 1.0
# Asphalt surface above the ground, and the outer edge of the shoulders: far enough from the
# terrain underneath for the depth buffer at the distances roads are seen from (up to 200 m).
ROAD_TOP = 0.09
SHOULDER_EDGE = 0.04
# Half-width of the unmown strip along field boundaries.
MARGIN = 1.25

# Brightest foliage shade: every canopy and hedge colour is a tint of it (at most 1).
FOLIAGE_BASE = "#B8C992"
BARK_BASE = "#8A7660"
SPECIES = {
    "round": ("#7F9468", "#8C9C6C", "#75895F"),
    "conifer": ("#5D7058", "#566A55"),
    "poplar": ("#94A472", "#8B9D6A"),
    "hedge": ("#647553", "#768A60", "#6C7F58"),
}

# Field kinds: material key, metres per texture repeat, whether rows turn with the field.
FIELDS = (
    ("meadow", 6.0, False),
    ("wheat", 11.0, True),
    ("ploughed", 12.8, True),
    ("crop", 16.0, True),
    ("fallow", 4.0, False),
)
ROW_ANGLES = (0.0, 90.0, 28.0, -34.0, 62.0, 90.0, 0.0, -58.0)


def materials() -> None:
    M["grass"] = material("M_LAND_GRASS", "#98A37D", roughness=1.0)
    M["yard"] = material("M_LAND_YARD", "#ACA794", roughness=1.0)
    M["verge"] = material("M_FIELD_VERGE", "#8B9A70", roughness=1.0)
    M["lane"] = material("M_FARM_FLOOR", "#8C857A", roughness=0.95)
    M["meadow"] = material("M_FIELD_MEADOW", "#9AA67E", roughness=1.0)
    M["wheat"] = material("M_FIELD_WHEAT", "#CDBD8C", roughness=1.0)
    M["ploughed"] = material("M_FIELD_PLOUGHED", "#A08B70", roughness=1.0)
    M["crop"] = material("M_FIELD_CROP", "#8FA072", roughness=1.0)
    M["fallow"] = material("M_FIELD_FALLOW", "#B7B093", roughness=1.0)
    M["shoulder"] = material("M_ROAD_SHOULDER", "#ADA692", roughness=1.0)
    M["marking"] = material("M_ROAD_MARKING", "#E8E6DF", roughness=0.7)
    M["foliage_tree"] = material("M_FOLIAGE_TREE", FOLIAGE_BASE, roughness=0.95)
    # Not the same roughness as the trees: identical materials are merged when the GLB is optimised,
    # and the runtime tells the two apart by name (different sway).
    M["foliage_hedge"] = material("M_FOLIAGE_HEDGE", FOLIAGE_BASE, roughness=1.0)
    M["trunk"] = material("M_TREE_TRUNK", BARK_BASE, roughness=0.95)
    M["fence"] = material("M_FENCE_METAL", "#8A9094", roughness=0.5, metallic=0.5)
    M["pole"] = material("M_POWER_POLE", "#7A6A57", roughness=0.9)
    M["wire"] = material("M_POWER_WIRE", "#3C3F41", roughness=0.6, metallic=0.4)
    M["insulator"] = material("M_INSULATOR", "#C9CFD2", roughness=0.3)


def _hash(*values: int) -> int:
    h = 2166136261
    for v in values:
        h = ((h ^ (v & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return h


def _jitter(seed: int, k: int) -> float:
    """Deterministic value in [-1, 1]."""
    return (_hash(seed, k) % 20001) / 10000.0 - 1.0


def _smooth(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def _rect_distance(x: float, y: float, r: Rect) -> float:
    dx = max(r[0] - x, 0.0, x - r[2])
    dy = max(r[1] - y, 0.0, y - r[3])
    return math.hypot(dx, dy)


def _inside(x: float, y: float, r: Rect, grow: float = 0.0) -> bool:
    return r[0] - grow < x < r[2] + grow and r[1] - grow < y < r[3] + grow


def road_rect(road: Road) -> Rect:
    (ax, ay), (bx, by), w = road
    if abs(bx - ax) > abs(by - ay):
        return (min(ax, bx), ay - w / 2, max(ax, bx), ay + w / 2)
    return (ax - w / 2, min(ay, by), ax + w / 2, max(ay, by))


def field_of(fx: int, fy: int) -> tuple[int, int]:
    """Field that the lattice cell (fx, fy) belongs to. A third of the cells join their eastern
    or northern neighbour, so the patchwork has fields of one and two cells: less of a grid."""
    px, py = fx - (fx & 1), fy - (fy & 1)
    if lp.hash32(px, fy, 211) % 3 == 0:
        return (px, fy)
    if lp.hash32(fx, py, 223) % 4 == 0:
        return (fx, py)
    return (fx, fy)


def is_field_boundary(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Whether two neighbouring lattice cells belong to different fields."""
    return field_of(*a) != field_of(*b)


def _lines(lo: float, hi: float, cell: float, fine: tuple[float, float], special: list[float]) -> list[float]:
    """Grid lines: `cell` apart inside `fine`, twice that outside, plus the `special` lines
    (boundaries that faces must follow). Regular lines too close to a special one are dropped."""
    special = sorted({round(s, 3) for s in special if lo < s < hi})
    kept: list[float] = []
    for s in special:  # two special lines closer than 0.3 m: keep the first
        if not kept or s - kept[-1] > 0.3:
            kept.append(s)
    regular = []
    v = lo
    while v < hi - 1e-6:
        regular.append(v)
        v += cell if fine[0] <= v < fine[1] else 2 * cell
    regular.append(hi)
    out = list(kept)
    for r in regular:
        if all(abs(r - s) > 1.2 for s in kept):
            out.append(r)
    return sorted(out)


class Terrain:
    """Height field: GROUND_Z on flat zones, a plateau behind the store, gentle relief elsewhere."""

    def __init__(self, ground_z: float, flat: list[Rect], plateau: Rect, plateau_z: float) -> None:
        self.ground_z = ground_z
        self.flat = flat
        self.plateau = plateau
        self.plateau_z = plateau_z

    def flatness(self, x: float, y: float) -> float:
        """1 on flat zones, fading to 0 over 25 m around them."""
        d = min(_rect_distance(x, y, r) for r in self.flat)
        return 1.0 - _smooth(d / 25.0)

    def height(self, x: float, y: float) -> float:
        # Rolling relief, stronger towards the horizon; only rises (no pits next to buildings).
        n = 0.6 * noise.noise(Vector((x / 85.0, y / 85.0, 0.3))) + 0.4 * noise.noise(Vector((x / 33.0, y / 33.0, 1.7)))
        amplitude = 3.0 + 13.0 * _smooth(math.hypot(x, y - 60.0) / 260.0)
        relief = self.ground_z + (1.0 - self.flatness(x, y)) * amplitude * (0.5 + 0.5 * n)
        # The plateau carrying the store's forecourt, with a 25 m slope down to the plain.
        d = _rect_distance(x, y, self.plateau)
        hill = self.plateau_z - (self.plateau_z - self.ground_z) * _smooth(d / 25.0)
        return max(relief, hill)

    def build(
        self,
        name: str,
        bounds: Rect,
        cell: float,
        field_cell: tuple[float, float],
        parent,
        yards: list[Rect] | None = None,
        bands: list[Rect] | None = None,
        lanes: list[Rect] | None = None,
        roads: list[Road] | None = None,
        fine: Rect = (-60.0, 0.0, 110.0, 150.0),
    ):
        """Grid mesh with a field patchwork.

        Faces follow the boundaries that matter: field edges (with an unmown margin on each
        side), `yards` (bare, compacted ground around buildings), `lanes` (concrete service
        strips inside a yard), `bands` (rough grass strips, e.g. under a fence) and the grass
        verges of `roads`. Each field gets its own tone and its crop rows their own direction:
        UV0 is authored here (the export keeps it, see surfaces.py) and the tint is baked."""
        x0, y0, x1, y1 = bounds
        yards, bands, lanes = yards or [], bands or [], lanes or []
        # Mown verge on both sides of each road, beyond the gravel shoulder.
        verges = []
        for road in roads or []:
            r = road_rect(road)
            grow = SHOULDER + 2.5
            verges.append((r[0], r[1] - grow, r[2], r[3] + grow) if (r[2] - r[0]) > (r[3] - r[1]) else (r[0] - grow, r[1], r[2] + grow, r[3]))
        sx, sy = [], []
        k = math.ceil((x0 + 1000.0) / field_cell[0])
        while -1000.0 + k * field_cell[0] < x1:
            sx += [-1000.0 + k * field_cell[0] - MARGIN, -1000.0 + k * field_cell[0] + MARGIN]
            k += 1
        k = math.ceil((y0 + 1000.0) / field_cell[1])
        while -1000.0 + k * field_cell[1] < y1:
            sy += [-1000.0 + k * field_cell[1] - MARGIN, -1000.0 + k * field_cell[1] + MARGIN]
            k += 1
        for r in yards + bands + lanes:
            sx += [r[0], r[2]]
            sy += [r[1], r[3]]
        # Lawn around the plateau that carries the store.
        lawn = (self.plateau[0] - 30.0, self.plateau[1] - 30.0, self.plateau[2] + 30.0, self.plateau[3] + 30.0)
        sx += [lawn[0], lawn[2]]
        sy += [lawn[1], lawn[3]]
        for r in verges:  # only the long edges matter
            if (r[2] - r[0]) > (r[3] - r[1]):
                sy += [r[1], r[3]]
            else:
                sx += [r[0], r[2]]
        xs = _lines(x0, x1, cell, (fine[0], fine[2]), sx)
        ys = _lines(y0, y1, cell, (fine[1], fine[3]), sy)

        b = MeshBuilder(recalc_normals=False)
        bm = b.bm
        tint_layer = lp._tint_layer(bm)
        uv_layer = bm.loops.layers.uv.new("UVMap")
        verts, mottle = [], []
        for x in xs:
            column, tones = [], []
            for y in ys:
                column.append(bm.verts.new((x, y, self.height(x, y))))
                tones.append(0.93 + 0.07 * noise.noise(Vector((x / 21.0, y / 21.0, 5.3))) + 0.035 * noise.noise(Vector((x / 6.0, y / 6.0, 9.1))))
            verts.append(column)
            mottle.append(tones)

        def classify(cx: float, cy: float):
            """(material key, metres per repeat, row angle, tint) of the face centred there."""
            if any(_inside(cx, cy, r) for r in lanes):
                return "lane", 2.0, 0.0, (0.95, 0.95, 0.95)
            if any(_inside(cx, cy, r) for r in bands):
                return "verge", 6.0, 0.0, (0.86, 0.9, 0.84)
            if any(_inside(cx, cy, r) for r in yards):
                return "yard", 3.0, 0.0, (0.97, 0.97, 0.97)
            if any(_inside(cx, cy, r) for r in verges):
                return "grass", 6.0, 0.0, (0.95, 0.97, 0.93)
            if _inside(cx, cy, lawn):
                return "grass", 6.0, 0.0, (0.97, 0.97, 0.97)
            u, v = (cx + 1000.0) / field_cell[0], (cy + 1000.0) / field_cell[1]
            cx_i, cy_i = math.floor(u), math.floor(v)
            fx, fy = field_of(cx_i, cy_i)
            # Unmown margin along the edges this cell shares with another field.
            du, dv = (u - cx_i) * field_cell[0], (v - cy_i) * field_cell[1]
            for near, other in ((du, (cx_i - 1, cy_i)), (field_cell[0] - du, (cx_i + 1, cy_i)), (dv, (cx_i, cy_i - 1)), (field_cell[1] - dv, (cx_i, cy_i + 1))):
                if near < MARGIN and field_of(*other) != (fx, fy):
                    return "verge", 6.0, 0.0, (0.92, 0.94, 0.9)
            key, tile, turns = FIELDS[_hash(fx, fy) % len(FIELDS)]
            tone = 0.86 + 0.14 * lp.rand(fx, fy, 3)
            warm = 0.04 * (lp.rand(fx, fy, 5) - 0.5)
            angle = ROW_ANGLES[lp.hash32(fx, fy, 7) % len(ROW_ANGLES)] if turns else 0.0
            return key, tile, angle, (tone * (1 + warm), tone, tone * (1 - warm))

        for i in range(len(xs) - 1):
            for j in range(len(ys) - 1):
                cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
                key, tile, angle, tint = classify(cx, cy)
                face = bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
                face.material_index = b._slot(M[key])
                ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
                for loop, (di, dj) in zip(face.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                    x, y = xs[i + di], ys[j + dj]
                    loop[uv_layer].uv = ((x * ca + y * sa) / tile, (-x * sa + y * ca) / tile)
                    m = mottle[i + di][j + dj]
                    loop[tint_layer] = (min(1.0, tint[0] * m), min(1.0, tint[1] * m), min(1.0, tint[2] * m), 1.0)
        obj = b.build(name, parent=parent)
        obj["uv_authored"] = True
        return obj


# --- roads ------------------------------------------------------------------------------------

def _frame(road: Road):
    """(runs along X, start, end, centre across, width)."""
    (ax, ay), (bx, by), w = road
    if abs(bx - ax) > abs(by - ay):
        return True, min(ax, bx), max(ax, bx), ay, w
    return False, min(ay, by), max(ay, by), ax, w


def roads(name: str, network: list[Road], z: float, road_mat, parent, dashed: list[bool] | None = None) -> None:
    """One mesh for the whole network: asphalt with wheel tracks and patches (baked tint), edge
    lines, a dashed centre line (3 m dashes every 13 m), gravel shoulders. Roads whose `dashed`
    flag is off (aprons, loading lanes) carry no marking at all.

    Roads never overlap: where two meet, the one that is crossed over its full width stops at
    the other's edge (ties go to the first in `network`), and the through road's shoulder and
    edge line give way to asphalt across the mouth. Lines are faces of the same strip mesh, so
    no line is coplanar with the asphalt and nothing flickers at a distance."""
    dashed = dashed or [True] * len(network)
    frames = [_frame(r) for r in network]
    rects = [road_rect(r) for r in network]
    b = MeshBuilder(recalc_normals=False)
    bm = b.bm
    tint_layer = lp._tint_layer(bm)
    uv_layer = bm.loops.layers.uv.new("UVMap")
    asphalt, shoulder, marking = b._slot(road_mat), b._slot(M["shoulder"]), b._slot(M["marking"])

    for i, (horizontal, a0, a1, c, w) in enumerate(frames):
        h = w / 2

        def along(r: Rect) -> tuple[float, float]:
            return (r[0], r[2]) if horizontal else (r[1], r[3])

        def across(r: Rect) -> tuple[float, float]:
            return (r[1], r[3]) if horizontal else (r[0], r[2])

        cuts, breaks, mouths = [], {a0, a1}, []
        for j, rj in enumerate(rects):
            if j == i:
                continue
            other_horizontal, _, _, _, wj = frames[j]
            (u0, u1), (v0, v1) = along(rj), across(rj)
            ou = (max(u0, a0), min(u1, a1))
            ov = (max(v0, c - h), min(v1, c + h))
            if ou[1] - ou[0] > 0.01 and ov[1] - ov[0] > 0.01:
                mine = (ov[1] - ov[0]) / w
                theirs = ((ou[1] - ou[0]) if other_horizontal != horizontal else (ov[1] - ov[0])) / wj
                if mine >= 0.8 and (theirs < 0.8 or j < i):
                    cuts.append(ou)
            # Mouth of the other road: its asphalt, prolonged over this road's shoulder.
            reach = SHOULDER + 0.6
            mouth = (rj[0] - reach, rj[1], rj[2] + reach, rj[3]) if other_horizontal else (rj[0], rj[1] - reach, rj[2], rj[3] + reach)
            mouths.append(mouth)
            (mu0, mu1), (mv0, mv1) = along(mouth), across(mouth)
            if mv0 < c + h + SHOULDER and mv1 > c - h - SHOULDER:
                breaks.update(u for u in (u0, u1) if other_horizontal != horizontal and a0 < u < a1)
        for u0, u1 in cuts:
            breaks.update(u for u in (u0, u1) if a0 <= u <= a1)
        if dashed[i]:
            t = a0 + 5.0
            while t + 3.0 < a1:
                breaks.update((t, t + 3.0))
                t += 13.0
        # No stretch longer than 13 m: vertices are what carries wear along the road.
        ordered = sorted(breaks)
        stops = []
        for u0, u1 in zip(ordered, ordered[1:]):
            n = max(1, math.ceil((u1 - u0) / 13.0))
            stops += [u0 + (u1 - u0) * k / n for k in range(n)]
        stops.append(ordered[-1])
        stops = [s for k, s in enumerate(stops) if k == 0 or s - stops[k - 1] > 0.05]

        # Cross-section, from one shoulder to the other: (offset, height, tint), then the kind of
        # the strip that follows each point.
        lane = (h - 0.4) / 2 + 0.04
        half = [
            (-(h + SHOULDER), SHOULDER_EDGE, 0.9), (-h, ROAD_TOP, 0.97), (-h + 0.25, ROAD_TOP, 0.97), (-h + 0.4, ROAD_TOP, 0.95),
            (-lane - 0.85, ROAD_TOP, 0.8), (-lane, ROAD_TOP, 0.93), (-lane + 0.85, ROAD_TOP, 0.8), (-0.075, ROAD_TOP, 0.92),
        ]
        section = half + [(-o, zz, t) for o, zz, t in reversed(half)]
        kinds = ["shoulder", "asphalt", "edge", "asphalt", "asphalt", "asphalt", "asphalt", "dash"]
        kinds = kinds + list(reversed(kinds[:-1]))

        def point(u: float, v: float) -> tuple[float, float]:
            return (u, c + v) if horizontal else (c + v, u)

        rows = []
        for r, u in enumerate(stops):
            row = []
            for s, (o, zz, _) in enumerate(section):
                x, y = point(u, o)
                row.append(bm.verts.new((x, y, z + zz)))
            rows.append(row)
        for r, (u0, u1) in enumerate(zip(stops, stops[1:])):
            um = (u0 + u1) / 2
            if any(lo - 0.01 < um < hi + 0.01 for lo, hi in cuts):
                continue
            # A dash sits on a 3 m stretch that starts on the dash pattern, away from junctions.
            on_pattern = dashed[i] and abs(u1 - u0 - 3.0) < 0.05 and abs(((u0 - a0 - 5.0) / 13.0) - round((u0 - a0 - 5.0) / 13.0)) < 0.01
            mx, my = point(um, 0.0)
            clear = all(not _inside(mx, my, rects[j], 4.0) for j in range(len(rects)) if j != i)
            patch = 0.86 if lp.rand(i, r, 11) < 0.12 else 1.0  # resurfaced stretch, darker
            for s, kind in enumerate(kinds):
                o0, o1 = section[s][0], section[s + 1][0]
                fx, fy = point(um, (o0 + o1) / 2)
                in_mouth = any(_inside(fx, fy, m) for m in mouths)
                slot, flat_tint = asphalt, None
                if kind == "shoulder":
                    slot = asphalt if in_mouth else shoulder
                elif kind == "edge" and dashed[i] and not in_mouth:
                    slot, flat_tint = marking, 0.92 + 0.08 * lp.rand(i, r, s)
                elif kind == "dash" and on_pattern and clear:
                    slot, flat_tint = marking, 0.92 + 0.08 * lp.rand(i, r, s)
                # Horizontal: u runs along +X and the section along +Y, so (u, v) → (x, y) keeps
                # its orientation; vertical swaps them, hence the other winding.
                if horizontal:
                    corners = (rows[r][s], rows[r + 1][s], rows[r + 1][s + 1], rows[r][s + 1])
                    order = ((r, s), (r + 1, s), (r + 1, s + 1), (r, s + 1))
                else:
                    corners = (rows[r][s], rows[r][s + 1], rows[r + 1][s + 1], rows[r + 1][s])
                    order = ((r, s), (r, s + 1), (r + 1, s + 1), (r + 1, s))
                face = bm.faces.new(corners)
                face.material_index = slot
                tile = 3.0 if slot == shoulder else 4.0
                for loop, (rr, ss) in zip(face.loops, order):
                    loop[uv_layer].uv = (section[ss][0] / tile, stops[rr] / tile)
                    if flat_tint is not None:
                        t = flat_tint
                    elif slot == shoulder:
                        t = section[ss][2] * (0.94 + 0.06 * lp.rand(i, rr, ss, 5))
                    else:
                        wear = section[ss][2] if not in_mouth and kind != "shoulder" else 0.93
                        t = wear * patch * (0.95 + 0.05 * lp.rand(i, rr, ss, 9))
                    loop[tint_layer] = (t, t, t, 1.0)
    # Flat and open to the sky: baked occlusion would add nothing.
    road = b.build(name, parent=parent)
    road["ao_skip"] = True
    road["uv_authored"] = True


# --- vegetation -------------------------------------------------------------------------------

def _species_tint(species: str, seed: int) -> lp.RGB:
    """Colour of one plant: its species' shade, with its own tone and a slight hue drift."""
    shades = SPECIES[species]
    base = lp.rel(shades[lp.hash32(seed, 2) % len(shades)], FOLIAGE_BASE)
    tone = 0.88 + 0.12 * lp.rand(seed, 31)
    drift = 0.06 * (lp.rand(seed, 37) - 0.5)
    return (base[0] * tone * (1 + drift), base[1] * tone, base[2] * tone * (1 - drift))


def _shader(colour: lp.RGB, seed: int):
    """Facet tint: lighter on top, darker underneath, a little noise from facet to facet. The
    gradient is what makes the layers of a canopy read from far away."""

    def shade(nz: float, k: int) -> lp.RGB:
        light = 0.66 + 0.34 * _smooth(nz * 0.5 + 0.55)
        return lp.scale(colour, light * (0.93 + 0.07 * lp.rand(seed, k, 41)))

    return shade


def tree(b: MeshBuilder, x: float, y: float, z: float, species: str, seed: int, detail: int = 1) -> None:
    """Stylised tree standing at (x, y, z): visible trunk, faceted canopy in one foliage
    material. `detail`: 2 near the viewpoint, 1 in the middle distance, 0 on the horizon."""
    s = 0.8 + 0.4 * (_jitter(seed, 1) + 1) / 2
    colour = _species_tint(species, seed)
    shade = _shader(colour, seed)
    wind = lp.rand(seed, 43)
    bark = lp.scale(lp.WHITE, 0.8 + 0.2 * lp.rand(seed, 47))
    # A closed builder recalculates normals: keep the clumps closed so that stays reliable.
    drop = None if b.recalc_normals else -0.5
    sides = 5 if detail else 4
    turn = 2 * math.pi * lp.rand(seed, 53)

    def trunk(r0: float, r1: float, bare: float, top: float, height: float) -> None:
        rings = [lp.ring((x, y, z - 0.15), r0 * 1.35 * s, r0 * 1.35 * s, sides, turn), lp.ring((x, y, z + bare * 0.5 * s), r0 * s, r0 * s, sides, turn),
                 lp.ring((x, y, z + top * s), r1 * s, r1 * s, sides, turn)]
        lp.loft(b, rings, M["trunk"], ring_tints=[lp.scale(bark, 0.75), bark, lp.scale(bark, 0.9)], cap_top=b.recalc_normals, cap_bottom=b.recalc_normals,
                phase=lambda p: (wind, min(1.0, max(0.0, (p.z - z) / (height * s))), 0.0))

    def sway(height: float):
        return lambda p: (wind, min(1.0, max(0.0, (p.z - z) / (height * s))), 0.0)

    if species == "round":
        height = 7.0
        trunk(0.24, 0.13, 2.9, 3.9, height)
        clumps = [(0.0, 0.0, 4.7, 2.35, 1.95), (1.15, 0.45, 3.9, 1.5, 1.2), (-0.95, -0.6, 4.1, 1.6, 1.3)]
        if detail >= 2:
            clumps.append((0.2, 1.0, 5.4, 1.35, 1.1))
        if detail == 0:
            clumps = clumps[:2]
        for k, (dx, dy, dz, r, rz) in enumerate(clumps):
            jx, jy = 0.4 * _jitter(seed, 10 + k), 0.4 * _jitter(seed, 20 + k)
            fine = 2 if (detail >= 2 or (detail == 1 and k == 0)) else 1
            lp.blob(b, (x + (dx + jx) * s, y + (dy + jy) * s, z + dz * s), (r * s, r * s, rz * s), M["foliage_tree"], shade, seed + k * 131,
                    subdivisions=fine, lumps=0.2 if fine == 2 else 0.12, drop_below=drop, phase=sway(height))
    elif species == "conifer":
        height = 7.4
        trunk(0.17, 0.1, 1.4, 2.0, height)
        tiers = ((1.1, 2.0, 2.6), (2.6, 1.6, 2.4), (4.0, 1.2, 2.2), (5.3, 0.8, 2.1))
        n = 7 if detail else 6
        for k, (zb, r, hh) in enumerate(tiers):
            base = lp.ring((x, y, z + zb * s), r * s, r * s, n, turn + k * 0.5)
            for p_index, p in enumerate(base):  # ragged skirt
                p.z += 0.25 * s * (lp.rand(seed, k, p_index) - 0.5)
            # Dark skirt, light tip: the gradient separates the tiers from far away.
            lp.loft(b, [base], M["foliage_tree"], ring_tints=[lp.scale(colour, 0.6 + 0.1 * lp.rand(seed, k, 59))], apex=(x, y, z + (zb + hh) * s),
                    apex_tint=colour, phase=sway(height))
    else:  # poplar
        height = 9.8
        trunk(0.2, 0.1, 1.6, 2.4, height)
        fine = 2 if detail else 1
        lean = 0.25 * _jitter(seed, 71)
        # Two overlapping clumps: a wide lower one and a pointed crown.
        lp.blob(b, (x, y, z + 4.3 * s), (1.15 * s, 1.15 * s, 2.9 * s), M["foliage_tree"], shade, seed, subdivisions=fine, lumps=0.2, drop_below=drop, phase=sway(height))
        lp.blob(b, (x + lean * s, y + lean * s, z + 7.2 * s), (0.8 * s, 0.8 * s, 2.6 * s), M["foliage_tree"], shade, seed + 131,
                subdivisions=1 if detail < 2 else 2, lumps=0.16, drop_below=drop, phase=sway(height))


def _flatten(b: MeshBuilder, faces, seed: int) -> None:
    layer = lp._tint_layer(b.bm)
    for k, face in enumerate(faces):
        mean = [sum(l[layer][c] for l in face.loops) / len(face.loops) for c in range(3)]
        j = 0.92 + 0.08 * lp.rand(seed, k, 67)
        for l in face.loops:
            l[layer] = (mean[0] * j, mean[1] * j, mean[2] * j, 1.0)


def _hedge_run(b: MeshBuilder, trees: MeshBuilder, samples, seed: int, detail_at) -> None:
    """Clipped hedge swept through `samples` (x, y, ground z): a faceted prism whose width and
    height drift, closed at both ends, with a small tree here and there."""
    colour = _species_tint("hedge", seed)
    profile = []
    for k, (x, y, z) in enumerate(samples):
        prev, nxt = samples[max(k - 1, 0)], samples[min(k + 1, len(samples) - 1)]
        t = Vector((nxt[0] - prev[0], nxt[1] - prev[1], 0.0)).normalized()
        left = Vector((-t.y, t.x, 0.0))
        w = 1.05 + 0.3 * _jitter(seed, 300 + k)
        hh = 1.9 + 0.55 * _jitter(seed, 500 + k)
        centre = Vector((x, y, z - 0.1)) + left * (0.35 * _jitter(seed, 700 + k))
        profile.append([centre - left * w, centre - left * (0.8 * w) + Vector((0, 0, 0.62 * hh)), centre + Vector((0, 0, hh)) + left * (0.2 * _jitter(seed, 900 + k)),
                        centre + left * (0.8 * w) + Vector((0, 0, 0.62 * hh)), centre + left * w])
    coords = [p for ring in profile for p in ring]
    faces, tints = [], []
    for k in range(len(profile) - 1):
        for s in range(4):
            a, c = k * 5 + s, (k + 1) * 5 + s
            faces.append((a, c, c + 1, a + 1))
            light = (0.7, 0.98, 0.98, 0.7)[s] * (0.9 + 0.1 * lp.rand(seed, k, s, 71))
            tints.append(lp.scale(colour, light))
    faces.append((0, 1, 2, 3, 4))
    tints.append(lp.scale(colour, 0.72))
    last = (len(profile) - 1) * 5
    faces.append((last + 4, last + 3, last + 2, last + 1, last))
    tints.append(lp.scale(colour, 0.72))
    phases = []
    for k, ring in enumerate(profile):
        base = ring[0].z
        for p in ring:
            phases.append((lp.rand(seed, k // 3, 73), min(1.0, max(0.0, (p.z - base) / 2.4)), 0.0))
    lp.add(b, coords, faces, M["foliage_hedge"], tint=tints, phase=phases)
    for k, (x, y, z) in enumerate(samples):
        if lp.hash32(seed, k, 79) % 6 == 0:
            tree(trees, x, y, z - 0.1, "round" if lp.hash32(seed, k, 83) % 3 else "poplar", lp.hash32(seed, k, 89), detail_at(x, y))


def vegetation(
    name: str,
    terrain: Terrain,
    rows: list[tuple[tuple[float, float], tuple[float, float], str]],
    groves: list[tuple[float, float, int]],
    hedges: list[tuple[tuple[float, float], tuple[float, float]]],
    parent,
    view: tuple[float, float] = (0.0, 4.0),
) -> None:
    """Tree rows (along roads), groves (mixed species) and hedgerows (field boundaries).
    Two meshes: `<name>_TREES` (canopies + trunks) and `<name>_HEDGEROWS`."""
    trees, shrubs = MeshBuilder(recalc_normals=False), MeshBuilder(recalc_normals=False)

    def detail_at(x: float, y: float) -> int:
        d = math.hypot(x - view[0], y - view[1])
        return 2 if d < 75.0 else (1 if d < 170.0 else 0)

    for r, ((ax, ay), (bx, by), species) in enumerate(rows):
        length = math.hypot(bx - ax, by - ay)
        count = max(1, int(length // 9.0))
        for k in range(count + 1):
            t = k / count
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            tree(trees, x, y, terrain.height(x, y), species, _hash(r, k), detail_at(x, y))
    species_cycle = ("round", "round", "conifer", "poplar")
    for g, (gx, gy, n) in enumerate(groves):
        for k in range(n):
            angle = 2 * math.pi * (_jitter(g, 100 + k) + 1) / 2
            dist = 14.0 * math.sqrt((_jitter(g, 200 + k) + 1) / 2)
            x, y = gx + math.cos(angle) * dist, gy + math.sin(angle) * dist
            if terrain.flatness(x, y) > 0.3:
                continue
            tree(trees, x, y, terrain.height(x, y) - 0.1, species_cycle[_hash(g, k) % 4], _hash(g, k, 7), detail_at(x, y))
    for h, ((ax, ay), (bx, by)) in enumerate(hedges):
        length = math.hypot(bx - ax, by - ay)
        steps = max(1, int(length // 4.0))
        run = []
        for k in range(steps + 1):
            x, y = ax + (bx - ax) * k / steps, ay + (by - ay) * k / steps
            # A hedge stops at flat, built ground and leaves a gateway now and then.
            gap = terrain.flatness(x, y) > 0.3 or lp.hash32(h, k, 97) % 11 == 0
            if not gap:
                run.append((x, y, terrain.height(x, y)))
            if gap or k == steps:
                if len(run) >= 2:
                    _hedge_run(shrubs, trees, run, lp.hash32(h, k, 101), detail_at)
                run = []
    trees.build(f"{name}_TREES", parent=parent)
    shrubs.build(f"{name}_HEDGEROWS", parent=parent)


def hills(name: str, mounds: list[tuple[float, float, float, float]], z: float, mat, parent) -> None:
    """Distant rounded hills (x, y, radius, height): low-poly domes with an irregular outline."""
    b = MeshBuilder(recalc_normals=False)
    for m, (x, y, radius, height) in enumerate(mounds):
        n, levels = 18, 5
        rings, tints = [], []
        for k in range(levels):
            t = k / levels
            points = []
            for s in range(n):
                a = 2 * math.pi * s / n
                r = radius * (1 - t) * (1.0 + 0.16 * noise.noise(Vector((math.cos(a) * 1.3 + m * 7.1, math.sin(a) * 1.3, t * 2.0))))
                points.append(Vector((x + math.cos(a) * r, y + math.sin(a) * r, z + height * (1 - (1 - t) ** 2.2) * (0.92 + 0.08 * lp.rand(m, k, s)))))
            rings.append(points)
            tints.append(lp.scale((0.9, 0.95, 0.97), 0.8 + 0.2 * t))
        faces = lp.loft(b, rings, mat, ring_tints=tints, apex=(x, y, z + height))
        _flatten(b, faces, 500 + m)
    b.build(name, parent=parent)


# --- fence and power line ---------------------------------------------------------------------

def perimeter_fence(name: str, rect: Rect, gaps: list[Rect], z: float, parent) -> None:
    """Perimeter fence well clear of the buildings (an enclosure, not an outdoor run): posts
    every 3 m, three rails running from gap to gap."""
    x0, y0, x1, y1 = rect
    f = MeshBuilder(recalc_normals=False)
    sides = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    for (ax, ay), (bx, by) in sides:
        length = math.hypot(bx - ax, by - ay)
        n = int(length // 3.0)
        run = []
        for k in range(n + 1):
            x, y = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
            blocked = any(g[0] <= x <= g[2] and g[1] <= y <= g[3] for g in gaps)
            if not blocked:
                lp.box_faces(f, (x - 0.045, y - 0.045, z), (x + 0.045, y + 0.045, z + 1.95), M["fence"], tint=lp.scale(lp.WHITE, 0.88 + 0.12 * lp.rand(k, int(x), int(y))))
                run.append((x, y))
            if blocked or k == n:
                if len(run) >= 2:
                    for hz in (0.3, 1.0, 1.8):
                        lp.tube(f, (*run[0], z + hz), (*run[-1], z + hz), 0.03, M["fence"])
                run = []
    f.build(name, parent=parent)


def power_line(name: str, terrain: Terrain, route: list[tuple[float, float]], parent, span: float = 42.0) -> None:
    """Wooden distribution poles with cross-arms and three sagging conductors."""
    poles: list[tuple[float, float, float]] = []
    for (ax, ay), (bx, by) in zip(route, route[1:]):
        length = math.hypot(bx - ax, by - ay)
        n = max(1, round(length / span))
        for k in range(n + (1 if (bx, by) == route[-1] else 0)):
            x, y = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
            poles.append((x, y, terrain.height(x, y)))
    b = MeshBuilder(recalc_normals=False)
    top = 9.0
    arm_offsets = (-1.1, 0.0, 1.1)
    for i, (x, y, z) in enumerate(poles):
        nxt = poles[min(i + 1, len(poles) - 1)]
        prv = poles[max(i - 1, 0)]
        heading = math.atan2(nxt[1] - prv[1], nxt[0] - prv[0])
        lp.loft(b, [lp.ring((x, y, z - 0.2), 0.17, 0.17, 5), lp.ring((x, y, z + top), 0.12, 0.12, 5)], M["pole"],
                ring_tints=[(0.75, 0.75, 0.75), lp.WHITE], cap_top=True)
        # Cross-arm perpendicular to the line, three insulators on top.
        ax_, ay_ = -math.sin(heading) * 1.3, math.cos(heading) * 1.3
        lp.tube(b, (x - ax_, y - ay_, z + top - 0.4), (x + ax_, y + ay_, z + top - 0.4), 0.085, M["pole"], caps=True)
        for o in arm_offsets:
            ix, iy = x - math.sin(heading) * o, y + math.cos(heading) * o
            lp.box_faces(b, (ix - 0.05, iy - 0.05, z + top - 0.34), (ix + 0.05, iy + 0.05, z + top - 0.12), M["insulator"])
    for (ax, ay, az), (bx, by, bz) in zip(poles, poles[1:]):
        heading = math.atan2(by - ay, bx - ax)
        for o in arm_offsets:
            p0 = Vector((ax - math.sin(heading) * o, ay + math.cos(heading) * o, az + top - 0.12))
            p1 = Vector((bx - math.sin(heading) * o, by + math.cos(heading) * o, bz + top - 0.12))
            segments = 6
            points = []
            for k in range(segments + 1):
                t = k / segments
                p = p0.lerp(p1, t)
                p.z -= 0.9 * 4 * t * (1 - t)  # sag
                points.append(p)
            for q0, q1 in zip(points, points[1:]):
                lp.tube(b, q0, q1, 0.02, M["wire"], sides=3)
    # Seen from afar: no chamfer.
    b.build(name, parent=parent)
