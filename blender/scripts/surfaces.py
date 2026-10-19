"""Export-time UV0 for the tileable surface sets (blender/textures/surfaces.json).

The builders are procedural and carry no UVs. Before export, every mesh gets a box projection
in object space, scaled so one texture repeat covers `tile` metres: texel density is uniform
whatever the object size, and flat, chamfered and curved faces all take a texture. The
textures themselves are bound to the materials later, by name, in scripts/lib/surfaces.mjs.
"""

from __future__ import annotations

import json
import math
import os

import bmesh
import bpy
import numpy as np

SURFACES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "textures", "surfaces.json")
UV_NAME = "UVMap"


def load_surfaces() -> tuple[dict, dict]:
    with open(SURFACES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["sets"], data["materials"]


def project_surface_uvs(objects) -> int:
    """Adds the UV0 layer to `objects`; returns how many carry at least one textured material."""
    sets, mapping = load_surfaces()
    textured = 0
    for obj in objects:
        mesh = obj.data
        if not mesh.polygons:
            continue
        # Per material slot: metres per repeat (1 when the material has no surface set).
        tiles = np.array(
            [sets[mapping[m.name]]["tile"] if m and m.name in mapping else 1.0 for m in mesh.materials] or [1.0],
            dtype=np.float64,
        )
        if any(m and m.name in mapping for m in mesh.materials):
            textured += 1

        verts = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("co", verts)
        verts = verts.reshape(-1, 3)
        loop_vertex = np.empty(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", loop_vertex)
        normals = np.empty(len(mesh.polygons) * 3)
        mesh.polygons.foreach_get("normal", normals)
        normals = normals.reshape(-1, 3)
        totals = np.empty(len(mesh.polygons), dtype=np.int32)
        mesh.polygons.foreach_get("loop_total", totals)
        slots = np.empty(len(mesh.polygons), dtype=np.int32)
        mesh.polygons.foreach_get("material_index", slots)

        face = np.repeat(np.arange(len(mesh.polygons)), totals)
        axis = np.argmax(np.abs(normals), axis=1)[face]
        co = verts[loop_vertex]
        # Dominant axis X -> (y, z), Y -> (x, z), Z -> (x, y).
        first = np.where(axis == 0, co[:, 1], co[:, 0])
        second = np.where(axis == 2, co[:, 1], co[:, 2])
        scale = tiles[np.clip(slots[face], 0, len(tiles) - 1)]
        uv = np.stack([first / scale, second / scale], axis=1).astype(np.float32)

        layer = mesh.uv_layers.get(UV_NAME) or mesh.uv_layers.new(name=UV_NAME)
        layer.data.foreach_set("uv", uv.ravel())
    return textured


# --- goods ---------------------------------------------------------------------------------------
# Products are low-poly (6-7 sided cylinders, boxes). Their detail lives in one small normal atlas
# (make_textures.py): rounded box edges, bevelled and grooved cylinder profiles. Each product part
# is a connected piece of mesh; boxes map every face onto the "box" cell, cylinders map height onto
# the "cyl" profile (identical around the circumference) and their caps onto the flat cell.
GOODS_PREFIX = "M_GOODS_"
CELLS = {"box": (0, 0), "cyl": (1, 0), "flat": (0, 1)}  # (column, row) in the 2 × 2 atlas, row 0 at the bottom
CELL_INSET = 0.04


def _cell_uv(cell: str, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    cx, cy = CELLS[cell]
    u = CELL_INSET + np.clip(u, 0.0, 1.0) * (1 - 2 * CELL_INSET)
    v = CELL_INSET + np.clip(v, 0.0, 1.0) * (1 - 2 * CELL_INSET)
    return np.stack([(cx + u) / 2, (cy + v) / 2], axis=1)


def project_goods_uvs(objects) -> int:
    """Overwrites UV0 on the faces that use goods materials; returns the number of parts mapped."""
    parts = 0
    for obj in objects:
        mesh = obj.data
        goods_slots = {i for i, m in enumerate(mesh.materials) if m and m.name.startswith(GOODS_PREFIX)}
        if not obj.name.endswith("_GOODS") or not goods_slots or UV_NAME not in mesh.uv_layers:
            continue
        uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
        layer = mesh.uv_layers[UV_NAME]
        layer.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)

        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.normal_update()
        bm.faces.ensure_lookup_table()
        seen: set[int] = set()
        for start in bm.faces:
            if start.index in seen:
                continue
            seen.add(start.index)
            stack, part = [start], []
            while stack:
                face = stack.pop()
                part.append(face)
                for vert in face.verts:
                    for other in vert.link_faces:
                        if other.index not in seen:
                            seen.add(other.index)
                            stack.append(other)
            if mesh.polygons[part[0].index].material_index not in goods_slots:
                continue
            parts += 1
            _map_part(mesh, part, uv)
        bm.free()
        layer.data.foreach_set("uv", uv.ravel())
    return parts


def _map_part(mesh, part, uv) -> None:
    coords = np.array([v.co for f in part for v in f.verts])
    lo, hi = coords.min(axis=0), coords.max(axis=0)
    centre = (lo + hi) / 2
    size = np.maximum(hi - lo, 1e-6)
    # Faces whose normal is not along an axis: the sides of a cylinder, frustum or gable.
    oblique = sum(1 for f in part if np.max(np.abs(f.normal)) < 0.999)
    cylinder = oblique >= 4
    for face in part:
        poly = mesh.polygons[face.index]
        loops = range(poly.loop_start, poly.loop_start + poly.loop_total)
        co = np.array([v.co for v in face.verts])
        n = np.array(face.normal)
        if cylinder and abs(n[2]) > 0.95:  # flat cap
            u, v = (co[:, 0] - centre[0]) / size[0] + 0.5, (co[:, 1] - centre[1]) / size[1] + 0.5
            cell = "flat"
        elif cylinder:
            mid = math.atan2(*(co[:, 1].mean() - centre[1], co[:, 0].mean() - centre[0]))
            diff = np.arctan2(co[:, 1] - centre[1], co[:, 0] - centre[0]) - mid
            diff = (diff + math.pi) % (2 * math.pi) - math.pi  # unwrapped around the face's own centre
            u, v = 0.5 + diff / (2 * math.pi), (co[:, 2] - lo[2]) / size[2]
            cell = "cyl"
        else:
            axis = int(np.argmax(np.abs(n)))
            a = co[:, 1] if axis == 0 else co[:, 0]
            b = co[:, 1] if axis == 2 else co[:, 2]
            u = (a - a.min()) / max(a.max() - a.min(), 1e-6)
            v = (b - b.min()) / max(b.max() - b.min(), 1e-6)
            cell = "box"
        uv[list(loops)] = _cell_uv(cell, u, v)


# --- printed faces (logo on leaflets and banner) -------------------------------------------------
# Each connected group of faces with a brand material shows its image once, upright and readable
# from outside: right = (looking direction) × up, with up the world Z projected on the group's mean
# plane (world Y for faces that lie flat), and the group's extent spanning the whole image.

def brand_materials() -> set[str]:
    with open(SURFACES_PATH, encoding="utf-8") as f:
        return set(json.load(f).get("brand", {}))


def project_brand_uvs(objects) -> int:
    """Overwrites UV0 on brand-material faces; returns the number of printed faces mapped."""
    from mathutils import Vector

    names = brand_materials()
    mapped = 0
    for obj in objects:
        mesh = obj.data
        slots = {i for i, m in enumerate(mesh.materials) if m and m.name in names}
        if not slots or UV_NAME not in mesh.uv_layers:
            continue
        layer = mesh.uv_layers[UV_NAME]
        uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
        layer.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)

        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.normal_update()
        bm.faces.ensure_lookup_table()
        seen: set[int] = set()
        for start in bm.faces:
            if start.index in seen or mesh.polygons[start.index].material_index not in slots:
                continue
            seen.add(start.index)
            stack, group = [start], []
            while stack:
                face = stack.pop()
                group.append(face)
                for vert in face.verts:
                    for other in vert.link_faces:
                        if other.index not in seen and mesh.polygons[other.index].material_index in slots:
                            seen.add(other.index)
                            stack.append(other)
            normal = sum((f.normal for f in group), Vector()).normalized()
            up = Vector((0.0, 0.0, 1.0)) - normal * normal.z
            if up.length < 0.3:
                up = Vector((0.0, 1.0, 0.0)) - normal * normal.y
            up.normalize()
            right = (-normal).cross(up).normalized()
            coords = {}
            for face in group:
                poly = mesh.polygons[face.index]
                for k, vert in zip(range(poly.loop_start, poly.loop_start + poly.loop_total), face.verts):
                    coords[k] = (vert.co.dot(right), vert.co.dot(up))
            us = [c[0] for c in coords.values()]
            vs = [c[1] for c in coords.values()]
            u0, v0 = min(us), min(vs)
            du, dv = max(max(us) - u0, 1e-6), max(max(vs) - v0, 1e-6)
            for k, (u, v) in coords.items():
                uv[k] = ((u - u0) / du, (v - v0) / dv)
            mapped += len(group)
        bm.free()
        layer.data.foreach_set("uv", uv.ravel())
    return mapped
