"""Faceted low-poly parts with baked per-vertex data, for what is seen from the terrace (30 m and
more away): vegetation, animals, weathered sheet metal, roads.

Two pieces of data ride on the meshes besides positions and normals:

- `TINT`, a face-corner colour (linear RGB multiplier, at most 1). At export, `apply_tint`
  multiplies it into the baked occlusion and the result leaves as COLOR_0, which three.js
  multiplies into the albedo. One material can then carry a whole tree, hen or weathered wall:
  fewer draw calls, and colour variation costs no texture.
- `_PHASE`, a per-vertex vector for the runtime's vertex-shader animations (glTF attribute
  `_PHASE`, three.js attribute `_phase`): x = random phase of the animal or plant in [0, 1],
  y = height above its feet or the ground, normalised to [0, 1], z = head weight for animals
  (1 on the head, 0 on the body), 0 for plants.

Everything is deterministic: jitter comes from fixed hashes and Blender's Perlin noise.
"""

from __future__ import annotations

import math

import bmesh
import numpy as np
from mathutils import Vector, noise

from common import AO_ATTRIBUTE, srgb_to_linear

TINT = "TINT"
PHASE = "_PHASE"

RGB = tuple[float, float, float]
WHITE: RGB = (1.0, 1.0, 1.0)


def lin(hex_color: str) -> RGB:
    h = hex_color.lstrip("#")
    return tuple(srgb_to_linear(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4))


def rel(hex_color: str, base_hex: str) -> RGB:
    """Tint that turns the material colour `base_hex` into `hex_color` (clipped to 1)."""
    return tuple(min(1.0, c / max(b, 1e-4)) for c, b in zip(lin(hex_color), lin(base_hex)))


def scale(c: RGB, k: float) -> RGB:
    return (min(1.0, c[0] * k), min(1.0, c[1] * k), min(1.0, c[2] * k))


def mul(a: RGB, b: RGB) -> RGB:
    return (a[0] * b[0], a[1] * b[1], a[2] * b[2])


def mix(a: RGB, b: RGB, t: float) -> RGB:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def hash32(*values: int) -> int:
    h = 2166136261
    for v in values:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    # Final avalanche: FNV alone leaves the low bits of small inputs correlated.
    h ^= h >> 15
    h = (h * 0x2C1B3C6D) & 0xFFFFFFFF
    h ^= h >> 12
    return h


def rand(*values: int) -> float:
    """Deterministic value in [0, 1)."""
    return (hash32(*values) % 100003) / 100003.0


def _tint_layer(bm):
    return bm.loops.layers.float_color.get(TINT) or bm.loops.layers.float_color.new(TINT)


def _phase_layer(bm):
    return bm.verts.layers.float_vector.get(PHASE) or bm.verts.layers.float_vector.new(PHASE)


def paint(b, faces, tint) -> None:
    """Sets the tint of `faces`: one RGB for all, or a function of (face, loop)."""
    layer = _tint_layer(b.bm)
    for face in faces:
        for loop in face.loops:
            c = tint(face, loop) if callable(tint) else tint
            loop[layer] = (min(1.0, c[0]), min(1.0, c[1]), min(1.0, c[2]), 1.0)


def add(b, coords, faces, mat, tint=None, smooth=False, phase=None, vert_tint=None):
    """Adds a small mesh to the builder `b`. `coords`: points; `faces`: index tuples, counter-
    clockwise seen from outside (use a builder with recalc_normals=False for open shells).

    `tint`: RGB for every face, or a list with one RGB per face. `vert_tint`: one RGB per point
    instead (smooth gradients). `phase`: one (phase, height, head) for all points, or one per
    point. Returns the new faces."""
    bm = b.bm
    # Layers first: creating one reallocates the custom data of existing elements.
    tints = _tint_layer(bm) if (tint is not None or vert_tint is not None) else None
    layer = _phase_layer(bm) if phase is not None else None
    verts = [bm.verts.new(c) for c in coords]
    if phase is not None:
        single = not isinstance(phase[0], (tuple, list))
        for k, v in enumerate(verts):
            v[layer] = phase if single else phase[k]
    slot = b._slot(mat)
    out = []
    per_face = tint is not None and isinstance(tint[0], (tuple, list))
    for k, idx in enumerate(faces):
        face = bm.faces.new([verts[i] for i in idx])
        face.material_index = slot
        face.smooth = smooth
        if tints is not None:
            for loop, i in zip(face.loops, idx):
                c = vert_tint[i] if vert_tint is not None else (tint[k] if per_face else tint)
                loop[tints] = (min(1.0, c[0]), min(1.0, c[1]), min(1.0, c[2]), 1.0)
        out.append(face)
    return out


# --- shapes ------------------------------------------------------------------------------------

_ICO: dict[int, tuple[list[Vector], list[tuple[int, ...]]]] = {}


def icosphere(subdivisions: int):
    """Unit icosphere (points, triangles), cached: 20 faces at level 1, 80 at level 2."""
    if subdivisions not in _ICO:
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, radius=1.0)
        bm.verts.ensure_lookup_table()
        bm.normal_update()
        faces = []
        for f in bm.faces:
            idx = [v.index for v in f.verts]
            centre = sum((v.co for v in f.verts), Vector()) / 3
            if f.normal.dot(centre) < 0:
                idx.reverse()
            faces.append(tuple(idx))
        _ICO[subdivisions] = ([v.co.copy() for v in bm.verts], faces)
        bm.free()
    return _ICO[subdivisions]


def blob(b, centre, radii, mat, shade, seed: int, subdivisions: int = 2, lumps: float = 0.22,
         drop_below: float | None = -0.5, phase=None):
    """Faceted, slightly irregular ellipsoid: a clump of foliage. `shade(nz, k)` returns the tint
    of a facet from its normal's vertical component and its index. Facets that point steeply
    down are dropped when `drop_below` is set (never seen from a raised viewpoint)."""
    points, tris = icosphere(subdivisions)
    cx, cy, cz = centre
    offset = Vector(((seed % 97) * 0.37, (seed % 89) * 0.53, (seed % 83) * 0.71))
    coords = []
    for p in points:
        r = 1.0 + lumps * noise.noise(p * 1.7 + offset)
        coords.append(Vector((cx + p.x * radii[0] * r, cy + p.y * radii[1] * r, cz + p.z * radii[2] * r)))
    faces, tints = [], []
    for k, (i0, i1, i2) in enumerate(tris):
        n = (coords[i1] - coords[i0]).cross(coords[i2] - coords[i0])
        if n.length < 1e-9:
            continue
        n.normalize()
        if drop_below is not None and n.z < drop_below:
            continue
        faces.append((i0, i1, i2))
        tints.append(shade(n.z, k))
    used = sorted({i for f in faces for i in f})
    remap = {old: new for new, old in enumerate(used)}
    coords = [coords[i] for i in used]
    faces = [tuple(remap[i] for i in f) for f in faces]
    ph = [phase(c) for c in coords] if callable(phase) else phase
    return add(b, coords, faces, mat, tint=tints, phase=ph)


def ring(centre, radius_x: float, radius_y: float, sides: int, turn: float = 0.0, z: float | None = None):
    cx, cy, cz = centre
    if z is not None:
        cz = z
    return [
        Vector((cx + math.cos(turn + 2 * math.pi * k / sides) * radius_x, cy + math.sin(turn + 2 * math.pi * k / sides) * radius_y, cz))
        for k in range(sides)
    ]


def loft(b, rings, mat, tint=None, ring_tints=None, smooth=False, cap_top=False, cap_bottom=False, phase=None, apex=None, apex_tint=None):
    """Skin through rings of equal size (lists of points, counter-clockwise seen from the end of
    the path). `ring_tints`: one RGB per ring (gradients along the path). `apex`: closing point
    after the last ring."""
    n = len(rings[0])
    coords = [p for r in rings for p in r]
    vert_tint = [ring_tints[i] for i in range(len(rings)) for _ in range(n)] if ring_tints else None
    faces = []
    for i in range(len(rings) - 1):
        for k in range(n):
            a, c = i * n + k, i * n + (k + 1) % n
            faces.append((a, c, c + n, a + n))
    last = (len(rings) - 1) * n
    if apex is not None:
        coords.append(Vector(apex))
        if vert_tint:
            vert_tint.append(apex_tint or ring_tints[-1])
        for k in range(n):
            faces.append((last + k, last + (k + 1) % n, len(coords) - 1))
    elif cap_top:
        faces.append(tuple(last + k for k in range(n)))
    if cap_bottom:
        faces.append(tuple(reversed(range(n))))
    ph = [phase(c) for c in coords] if callable(phase) else phase
    return add(b, coords, faces, mat, tint=None if vert_tint else tint, vert_tint=vert_tint, smooth=smooth, phase=ph)


def quad(b, corners, mat, tint=None, corner_tints=None, phase=None):
    """One quad, corners counter-clockwise seen from its visible side."""
    return add(b, [Vector(c) for c in corners], [(0, 1, 2, 3)], mat, tint=tint, vert_tint=corner_tints, phase=phase)[0]


def panel(b, origin, u, v, cells, mat, tint_at, smooth=False):
    """Flat grid origin + s·u + t·v facing u × v, with a tint per grid point: `tint_at(s, t)`,
    s and t in [0, 1]. Vertices are what carries streaks and dirt on large flat walls."""
    nu, nv = cells
    o, uu, vv = Vector(origin), Vector(u), Vector(v)
    coords, tints = [], []
    for i in range(nu + 1):
        for j in range(nv + 1):
            s, t = i / nu, j / nv
            coords.append(o + uu * s + vv * t)
            tints.append(tint_at(s, t))
    faces = []
    for i in range(nu):
        for j in range(nv):
            a = i * (nv + 1) + j
            faces.append((a, a + nv + 1, a + nv + 2, a + 1))
    return add(b, coords, faces, mat, vert_tint=tints, smooth=smooth)


def box_faces(b, lo, hi, mat, tint=WHITE, skip: tuple[str, ...] = ("-z",), phase=None):
    """Axis-aligned box as loose quads with a tint; `skip` drops unseen faces (default: bottom)."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    coords = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    table = {"-z": (0, 3, 2, 1), "+z": (4, 5, 6, 7), "-y": (0, 1, 5, 4), "+x": (1, 2, 6, 5), "+y": (2, 3, 7, 6), "-x": (3, 0, 4, 7)}
    faces = [f for key, f in table.items() if key not in skip]
    used = sorted({i for f in faces for i in f})
    remap = {old: new for new, old in enumerate(used)}
    return add(b, [Vector(coords[i]) for i in used], [tuple(remap[i] for i in f) for f in faces], mat, tint=tint, phase=phase)


def tube(b, start, end, radius: float, mat, tint=WHITE, sides: int = 4, caps: bool = False):
    """Straight bar between two points, `sides` flat faces, no end caps by default."""
    a, c = Vector(start), Vector(end)
    d = c - a
    if d.length < 1e-6:
        return []
    d.normalize()
    ref = Vector((0.0, 0.0, 1.0)) if abs(d.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    u = d.cross(ref).normalized()
    v = d.cross(u).normalized()
    rings = []
    for p in (a, c):
        rings.append([p + (u * math.cos(2 * math.pi * k / sides + math.pi / 4) + v * math.sin(2 * math.pi * k / sides + math.pi / 4)) * radius for k in range(sides)])
    return loft(b, rings, mat, tint=tint, cap_top=caps, cap_bottom=caps)


# --- export ------------------------------------------------------------------------------------

# Name of the attribute that carries the final vertex colour out of Blender. It is a plain
# vector, not a colour attribute, on purpose: Blender 5.2's glTF exporter only writes a named
# colour attribute for the first material of a mesh and fills the other primitives with white
# (io_scene_gltf2/blender/exp/primitive_extract.py: `material_idxs_using_vc` is given the
# attribute's name instead of `COLOR_0` for every material after the first). Custom attributes
# do not go through that code. scripts/lib/surfaces.mjs renames `_COLOR` to COLOR_0.
COLOUR_OUT = "_COLOR"


def apply_tint(objects, every: bool = False) -> int:
    """Export step: on every mesh that carries a TINT attribute, writes occlusion × tint into
    `_COLOR` (face-corner domain, so hard colour edges survive) and removes TINT and the baked
    occlusion attribute. Meshes without baked occlusion (lightmapped ones, or --no-ao) get the
    tint alone. With `every`, meshes that only carry baked occlusion take the same route, so the
    occlusion reaches all their materials. Returns the number of meshes written."""
    count = 0
    for obj in objects:
        mesh = obj.data
        if mesh is None or not mesh.loops:
            continue
        has_tint = TINT in mesh.color_attributes
        has_ao = AO_ATTRIBUTE in mesh.color_attributes
        if not has_tint and not (every and has_ao):
            continue
        loops = len(mesh.loops)
        loop_vertex = np.empty(loops, dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", loop_vertex)

        def corner_values(attribute) -> np.ndarray:
            values = np.empty(len(attribute.data) * 4, dtype=np.float32)
            attribute.data.foreach_get("color", values)
            values = values.reshape(-1, 4)
            return values if attribute.domain == "CORNER" else values[loop_vertex]

        colour = np.ones((loops, 3), dtype=np.float32)
        if has_tint:
            tint = corner_values(mesh.color_attributes[TINT])
            painted = tint[:, 3] >= 0.5  # corners never painted stay white
            colour[painted] = tint[painted, :3]
            mesh.color_attributes.remove(mesh.color_attributes[TINT])
        if has_ao:
            colour *= corner_values(mesh.color_attributes[AO_ATTRIBUTE])[:, :3]
            mesh.color_attributes.remove(mesh.color_attributes[AO_ATTRIBUTE])
        out = mesh.attributes.new(COLOUR_OUT, "FLOAT_VECTOR", "CORNER")
        out.data.foreach_set("vector", np.clip(colour, 0.0, 1.0).ravel())
        count += 1
    return count


def banded_box(b, lo, hi, mat, levels, tints, top_tint=WHITE, phase=None):
    """Box whose four sides are cut into horizontal bands of different tints (crate slots, silo
    rings) and closed by a top; no bottom. `levels`: heights between lo.z and hi.z, exclusive;
    `tints`: one per band, bottom to top."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    zs = [z0, *levels, z1]
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    coords, faces, face_tints = [], [], []
    for z in zs:
        coords += [Vector((x, y, z)) for x, y in corners]
    for k in range(len(zs) - 1):
        for s in range(4):
            a, c = k * 4 + s, k * 4 + (s + 1) % 4
            faces.append((a, c, c + 4, a + 4))
            face_tints.append(tints[k])
    top = (len(zs) - 1) * 4
    faces.append((top, top + 1, top + 2, top + 3))
    face_tints.append(top_tint)
    return add(b, coords, faces, mat, tint=face_tints, phase=phase)
