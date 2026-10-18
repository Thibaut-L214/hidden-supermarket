"""Procedural landscape around the eggs terrace (lot 3): relief, field patchwork, roads with
shoulders, hedgerows, varied trees, the farm's perimeter fence and an overhead power line.

Everything is deterministic (fixed hashes and Blender's Perlin noise), schematic and generic:
no claim about a real site. The relief is flat where buildings and roads stand, rises behind
the store into the plateau that carries the forecourt, and rolls gently towards the horizon.
Coordinates are the terrace module's Blender frame (metres, Z up).
"""

from __future__ import annotations

import math

from mathutils import Vector, noise

from common import MeshBuilder, material

M: dict = {}

Rect = tuple[float, float, float, float]  # x0, y0, x1, y1
Road = tuple[tuple[float, float], tuple[float, float], float]  # a, b, width (axis-aligned)


def materials() -> None:
    M["grass"] = material("M_LAND_GRASS", "#9EA582", roughness=1.0)
    M["yard"] = material("M_LAND_YARD", "#A9A48F", roughness=1.0)
    M["fields"] = [
        material("M_FIELD_MEADOW", "#97A27B", roughness=1.0),
        material("M_FIELD_WHEAT", "#C3B488", roughness=1.0),
        material("M_FIELD_PLOUGHED", "#9C8A70", roughness=1.0),
        material("M_FIELD_CROP", "#8B9A6E", roughness=1.0),
        material("M_FIELD_FALLOW", "#B5AE91", roughness=1.0),
    ]
    M["shoulder"] = material("M_ROAD_SHOULDER", "#A8A18D", roughness=1.0)
    M["edge_line"] = material("M_ROAD_EDGE_LINE", "#E2E0D8", roughness=0.7)
    M["hedge"] = [
        material("M_HEDGE_DARK", "#647553", roughness=1.0),
        material("M_HEDGE_LIGHT", "#768A60", roughness=1.0),
    ]
    M["trunk"] = material("M_TREE_BARK", "#6E5D4A", roughness=0.95)
    M["crowns"] = {
        "round": [material("M_CROWN_OAK", "#7F9468", roughness=0.9), material("M_CROWN_BEECH", "#8C9C6C", roughness=0.9)],
        "conifer": [material("M_CROWN_PINE", "#5D7058", roughness=0.9)],
        "poplar": [material("M_CROWN_POPLAR", "#94A472", roughness=0.9)],
    }
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


def road_rect(road: Road) -> Rect:
    (ax, ay), (bx, by), w = road
    if abs(bx - ax) > abs(by - ay):
        return (min(ax, bx), ay - w / 2, max(ax, bx), ay + w / 2)
    return (ax - w / 2, min(ay, by), ax + w / 2, max(ay, by))


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

    def build(self, name: str, bounds: Rect, cell: float, field_cell: tuple[float, float], parent):
        """Grid mesh with a field patchwork: one material per face, chosen by a coarse lattice."""
        x0, y0, x1, y1 = bounds
        nx, ny = round((x1 - x0) / cell), round((y1 - y0) / cell)
        b = MeshBuilder(recalc_normals=False)
        verts = [[b.bm.verts.new((x0 + i * cell, y0 + j * cell, self.height(x0 + i * cell, y0 + j * cell))) for j in range(ny + 1)] for i in range(nx + 1)]
        slots = {"grass": b._slot(M["grass"]), "yard": b._slot(M["yard"])}
        fields = [b._slot(m) for m in M["fields"]]
        for i in range(nx):
            for j in range(ny):
                cx, cy = x0 + (i + 0.5) * cell, y0 + (j + 0.5) * cell
                if self.flatness(cx, cy) > 0.6:
                    slot = slots["yard"]
                elif _rect_distance(cx, cy, self.plateau) < 30.0:
                    slot = slots["grass"]
                else:
                    fx, fy = math.floor((cx + 1000.0) / field_cell[0]), math.floor((cy + 1000.0) / field_cell[1])
                    slot = fields[_hash(fx, fy) % len(fields)]
                face = b.bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
                face.material_index = slot
        return b.build(name, parent=parent)


# --- roads ------------------------------------------------------------------------------------

def roads(name: str, network: list[Road], z: float, road_mat, parent) -> None:
    """Asphalt, gravel shoulders (1 m each side) and continuous edge lines."""
    asphalt, sides = MeshBuilder(), MeshBuilder()
    for road in network:
        x0, y0, x1, y1 = road_rect(road)
        horizontal = (x1 - x0) > (y1 - y0)
        asphalt.box((x0, y0, z), (x1, y1, z + 0.05), road_mat)
        if horizontal:
            sides.box((x0, y0 - 1.0, z), (x1, y0, z + 0.03), M["shoulder"])
            sides.box((x0, y1, z), (x1, y1 + 1.0, z + 0.03), M["shoulder"])
            for y in (y0 + 0.25, y1 - 0.35):
                sides.box((x0 + 1.0, y, z + 0.05), (x1 - 1.0, y + 0.1, z + 0.06), M["edge_line"])
        else:
            sides.box((x0 - 1.0, y0, z), (x0, y1, z + 0.03), M["shoulder"])
            sides.box((x1, y0, z), (x1 + 1.0, y1, z + 0.03), M["shoulder"])
            for x in (x0 + 0.25, x1 - 0.35):
                sides.box((x, y0 + 1.0, z + 0.05), (x + 0.1, y1 - 1.0, z + 0.06), M["edge_line"])
    asphalt.build(name, parent=parent)
    sides.build(f"{name}_SIDES", parent=parent)["ao_skip"] = True


# --- vegetation -------------------------------------------------------------------------------

def tree(b: MeshBuilder, x: float, y: float, z: float, species: str, seed: int) -> None:
    s = 0.8 + 0.4 * (_jitter(seed, 1) + 1) / 2
    crowns = M["crowns"][species]
    crown = crowns[_hash(seed, 2) % len(crowns)]
    if species == "round":
        b.cylinder((x, y, z), 0.2 * s, 3.0 * s, M["trunk"], segments=6)
        for k, (dx, dy, dz, r) in enumerate(((0.0, 0.0, 4.2, 2.2), (0.9, 0.4, 3.6, 1.5), (-0.8, -0.5, 3.8, 1.6))):
            jx, jy = 0.4 * _jitter(seed, 10 + k), 0.4 * _jitter(seed, 20 + k)
            b.ellipsoid((x + (dx + jx) * s, y + (dy + jy) * s, z + dz * s), (r * s, r * s, r * 0.85 * s), crown, u=8, v=6)
    elif species == "conifer":
        b.cylinder((x, y, z), 0.15 * s, 1.6 * s, M["trunk"], segments=6)
        for k, (zb, r, h) in enumerate(((1.2, 1.9, 3.2), (3.0, 1.45, 2.8), (4.7, 0.95, 2.4))):
            b.cone((x, y, z + zb * s), r * s, h * s, crown, segments=8)
    else:  # poplar
        b.cylinder((x, y, z), 0.16 * s, 2.0 * s, M["trunk"], segments=6)
        b.ellipsoid((x, y, z + 5.2 * s), (1.1 * s, 1.1 * s, 3.8 * s), crown, u=8, v=7)


def vegetation(name: str, terrain: Terrain, rows: list[tuple[tuple[float, float], tuple[float, float], str]], groves: list[tuple[float, float, int]], hedges: list[tuple[tuple[float, float], tuple[float, float]]], parent) -> None:
    """Tree rows (along roads), groves (mixed species) and hedgerows (field boundaries)."""
    trees, shrubs = MeshBuilder(), MeshBuilder()
    for r, ((ax, ay), (bx, by), species) in enumerate(rows):
        length = math.hypot(bx - ax, by - ay)
        count = max(1, int(length // 9.0))
        for k in range(count + 1):
            t = k / count
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            tree(trees, x, y, terrain.height(x, y), species, _hash(r, k))
    species_cycle = ("round", "round", "conifer", "poplar")
    for g, (gx, gy, n) in enumerate(groves):
        for k in range(n):
            angle = 2 * math.pi * (_jitter(g, 100 + k) + 1) / 2
            dist = 14.0 * math.sqrt((_jitter(g, 200 + k) + 1) / 2)
            x, y = gx + math.cos(angle) * dist, gy + math.sin(angle) * dist
            if terrain.flatness(x, y) > 0.3:
                continue
            tree(trees, x, y, terrain.height(x, y) - 0.1, species_cycle[_hash(g, k) % 4], _hash(g, k, 7))
    for h, ((ax, ay), (bx, by)) in enumerate(hedges):
        length = math.hypot(bx - ax, by - ay)
        steps = int(length // 3.2)
        for k in range(steps + 1):
            x, y = ax + (bx - ax) * k / steps, ay + (by - ay) * k / steps
            if terrain.flatness(x, y) > 0.3:
                continue
            r = 1.5 + 0.4 * _jitter(h, k)
            mat = M["hedge"][_hash(h, k) % 2]
            shrubs.ellipsoid((x, y, terrain.height(x, y) + 0.8), (r, r, 1.1 + 0.3 * _jitter(h, k + 500)), mat, u=7, v=5)
    trees.build(f"{name}_TREES", parent=parent)
    shrubs.build(f"{name}_HEDGEROWS", parent=parent)


# --- fence and power line ---------------------------------------------------------------------

def perimeter_fence(name: str, rect: Rect, gaps: list[Rect], z: float, parent) -> None:
    """Perimeter fence well clear of the buildings (an enclosure, not an outdoor run)."""
    x0, y0, x1, y1 = rect
    f = MeshBuilder()
    sides = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    for (ax, ay), (bx, by) in sides:
        length = math.hypot(bx - ax, by - ay)
        n = int(length // 3.0)
        prev = None
        for k in range(n + 1):
            x, y = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
            blocked = any(g[0] <= x <= g[2] and g[1] <= y <= g[3] for g in gaps)
            if not blocked:
                f.box((x - 0.04, y - 0.04, z), (x + 0.04, y + 0.04, z + 1.9), M["fence"])
            if prev is not None and not blocked and not prev[2]:
                px, py = prev[0], prev[1]
                lo_x, hi_x = sorted((px, x))
                lo_y, hi_y = sorted((py, y))
                for hz in (0.25, 1.0, 1.75):
                    f.box((lo_x - 0.012, lo_y - 0.012, z + hz), (hi_x + 0.012, hi_y + 0.012, z + hz + 0.025), M["fence"])
            prev = (x, y, blocked)
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
    b = MeshBuilder()
    top = 9.0
    arm_offsets = (-1.1, 0.0, 1.1)
    for i, (x, y, z) in enumerate(poles):
        nxt = poles[min(i + 1, len(poles) - 1)]
        prv = poles[max(i - 1, 0)]
        heading = math.atan2(nxt[1] - prv[1], nxt[0] - prv[0])
        b.frustum((x, y, z - 0.2), 0.17, 0.12, top + 0.2, M["pole"], segments=7)
        # Cross-arm perpendicular to the line, three insulators on top.
        b.oriented_box((x, y, z + top - 0.4), (2.6, 0.12, 0.12), M["pole"], rot_z=heading + math.pi / 2)
        for o in arm_offsets:
            ix, iy = x - math.sin(heading) * o, y + math.cos(heading) * o
            b.cylinder((ix, iy, z + top - 0.34), 0.05, 0.22, M["insulator"], segments=6)
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
                d = q1 - q0
                horizontal = math.hypot(d.x, d.y)
                b.oriented_box(
                    tuple((q0 + q1) / 2),
                    (0.025, d.length, 0.025),
                    M["wire"],
                    rot_x=math.atan2(d.z, horizontal),
                    rot_z=math.atan2(d.y, d.x) - math.pi / 2,
                )
    # Seen from afar: no chamfer.
    b.build(name, parent=parent)
