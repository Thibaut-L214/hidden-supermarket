"""Shared helpers for blockout builders and the GLB export.

Conventions (see docs/TECH.md §03 and docs/DECISIONS.md):
- 1 Blender unit = 1 metre, Z up in Blender. The glTF exporter converts to Y up:
  glTF (x, y, z) = Blender (x, z, -y). Blender +Y (north) becomes glTF -Z.
- Object scale stays at 1 and rotation at 0: geometry is built in place, so
  nothing needs applying before export.
- Colours are authored as sRGB hex and converted to linear, which is what
  Principled BSDF and glTF baseColorFactor expect.
"""

from __future__ import annotations

import bmesh
import bpy
from mathutils import Matrix


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(hex_color: str) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    r, g, b = (srgb_to_linear(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4))
    return (r, g, b, 1.0)


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0


def material(
    name: str,
    color: str,
    roughness: float = 0.6,
    metallic: float = 0.0,
    emission: str | None = None,
    emission_strength: float = 1.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex_rgba(color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = hex_rgba(emission)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    mat.diffuse_color = hex_rgba(color)
    return mat


def empty(
    name: str,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent: bpy.types.Object | None = None,
    rotation_z: float = 0.0,
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.3
    _link(obj, location, parent)
    obj.rotation_euler = (0.0, 0.0, rotation_z)
    return obj


class MeshBuilder:
    """Accumulates axis-aligned boxes into one mesh object, one slot per material.

    Box coordinates are given in the object's local space, so an object whose
    origin sits on a hinge can be built directly around that pivot.
    """

    def __init__(self) -> None:
        self.bm = bmesh.new()
        self.materials: list[bpy.types.Material] = []

    def box(
        self,
        min_corner: tuple[float, float, float],
        max_corner: tuple[float, float, float],
        mat: bpy.types.Material | None = None,
    ) -> "MeshBuilder":
        (x0, y0, z0), (x1, y1, z1) = min_corner, max_corner
        verts = [
            self.bm.verts.new(v)
            for v in (
                (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
            )
        ]
        faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
        index = self._slot(mat)
        for f in faces:
            face = self.bm.faces.new([verts[i] for i in f])
            face.material_index = index
        return self

    def cylinder(
        self,
        base: tuple[float, float, float],
        radius: float,
        height: float,
        mat: bpy.types.Material | None = None,
        segments: int = 14,
    ) -> "MeshBuilder":
        """Vertical cylinder standing on `base` (centre of its bottom face)."""
        x, y, z = base
        matrix = Matrix.Translation((x, y, z + height / 2))
        return self._primitive(
            lambda: bmesh.ops.create_cone(
                self.bm, cap_ends=True, segments=segments, radius1=radius, radius2=radius, depth=height, matrix=matrix
            ),
            mat,
        )

    def sphere(
        self,
        centre: tuple[float, float, float],
        radius: float,
        mat: bpy.types.Material | None = None,
    ) -> "MeshBuilder":
        matrix = Matrix.Translation(centre)
        return self._primitive(
            lambda: bmesh.ops.create_uvsphere(self.bm, u_segments=16, v_segments=10, radius=radius, matrix=matrix),
            mat,
        )

    def _primitive(self, create, mat) -> "MeshBuilder":
        before = set(self.bm.faces)
        create()
        index = self._slot(mat)
        for face in set(self.bm.faces) - before:
            face.material_index = index
        return self

    def build(
        self,
        name: str,
        location: tuple[float, float, float] = (0.0, 0.0, 0.0),
        parent: bpy.types.Object | None = None,
    ) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(f"ME_{name}")  # distinct from node names in glTF
        self.bm.normal_update()
        self.bm.to_mesh(mesh)
        self.bm.free()
        for mat in self.materials:
            mesh.materials.append(mat)
        obj = bpy.data.objects.new(name, mesh)
        _link(obj, location, parent)
        return obj

    def _slot(self, mat: bpy.types.Material | None) -> int:
        if mat is None:
            return 0
        if mat not in self.materials:
            self.materials.append(mat)
        return self.materials.index(mat)


def box(
    name: str,
    min_corner: tuple[float, float, float],
    max_corner: tuple[float, float, float],
    mat: bpy.types.Material | None = None,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    """Single box whose origin is its own centre (world-space corners)."""
    centre = tuple((a + b) / 2 for a, b in zip(min_corner, max_corner))
    half = tuple((b - a) / 2 for a, b in zip(min_corner, max_corner))
    local = MeshBuilder().box(tuple(-h for h in half), half, mat)
    origin = centre if parent is None else tuple(c - p for c, p in zip(centre, parent.matrix_world.translation))
    return local.build(name, origin, parent)


def helper_volume(obj: bpy.types.Object) -> bpy.types.Object:
    """Collider, scan target or trigger: exported, hidden at runtime, wireframe in Blender."""
    obj.display_type = "WIRE"
    obj.hide_render = True
    return obj


def save_blend(path: str) -> None:
    bpy.ops.wm.save_as_mainfile(filepath=path)


def export_glb(path: str) -> None:
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_extras=True,
        export_cameras=False,
        export_lights=False,
        export_animations=False,
        export_materials="EXPORT",
        use_selection=False,
        use_visible=False,
    )


def _link(obj: bpy.types.Object, location, parent) -> None:
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    obj.location = location
    bpy.context.view_layer.update()
