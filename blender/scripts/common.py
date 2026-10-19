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

import math

import bmesh
import bpy
from mathutils import Matrix, Vector


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


def glass(name: str, color: str, alpha: float = 0.3) -> bpy.types.Material:
    """Blended, see-through material (exported with alphaMode BLEND)."""
    mat = material(name, color, roughness=0.08, metallic=0.0)
    mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = alpha
    mat.surface_render_method = "BLENDED"
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

    def __init__(self, recalc_normals: bool = True) -> None:
        self.bm = bmesh.new()
        self.materials: list[bpy.types.Material] = []
        # Open surfaces (grids) keep the orientation they were built with.
        self.recalc_normals = recalc_normals

    def box(
        self,
        min_corner: tuple[float, float, float],
        max_corner: tuple[float, float, float],
        mat: bpy.types.Material | None = None,
        skip: tuple[str, ...] = (),
    ) -> "MeshBuilder":
        """Axis-aligned box. `skip` drops faces that can never be seen ("-z", "+x", …)."""
        (x0, y0, z0), (x1, y1, z1) = min_corner, max_corner
        verts = [
            self.bm.verts.new(v)
            for v in (
                (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
            )
        ]
        faces = {
            "-z": (0, 3, 2, 1), "+z": (4, 5, 6, 7), "-y": (0, 1, 5, 4),
            "+x": (1, 2, 6, 5), "+y": (2, 3, 7, 6), "-x": (3, 0, 4, 7),
        }
        index = self._slot(mat)
        for key, f in faces.items():
            if key in skip:
                continue
            face = self.bm.faces.new([verts[i] for i in f])
            face.material_index = index
        for vert in verts:
            if not vert.link_faces:
                self.bm.verts.remove(vert)
        return self

    def drop_bottom_caps(self) -> "MeshBuilder":
        """Removes downward n-gon caps (bases resting on a surface, never seen)."""
        self.bm.normal_update()
        caps = [f for f in self.bm.faces if len(f.verts) > 4 and f.normal.z < -0.99]
        bmesh.ops.delete(self.bm, geom=caps, context="FACES_ONLY")
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
            smooth_sides=True,
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

    def cylinder_along(
        self,
        centre: tuple[float, float, float],
        axis: str,
        radius: float,
        length: float,
        mat: bpy.types.Material | None = None,
        segments: int = 12,
    ) -> "MeshBuilder":
        """Cylinder centred on `centre`, its length along the X or Y axis (rollers, ducts, bars)."""
        turn = Matrix.Rotation(math.pi / 2, 4, "Y") if axis == "X" else Matrix.Rotation(-math.pi / 2, 4, "X")
        matrix = Matrix.Translation(centre) @ turn
        return self._primitive(
            lambda: bmesh.ops.create_cone(
                self.bm, cap_ends=True, segments=segments, radius1=radius, radius2=radius, depth=length, matrix=matrix
            ),
            mat,
            smooth_sides=True,
        )

    def frustum(
        self,
        base: tuple[float, float, float],
        r_bottom: float,
        r_top: float,
        height: float,
        mat: bpy.types.Material | None = None,
        segments: int = 12,
    ) -> "MeshBuilder":
        """Truncated cone standing on `base` (bottle shoulders, lids)."""
        x, y, z = base
        matrix = Matrix.Translation((x, y, z + height / 2))
        return self._primitive(
            lambda: bmesh.ops.create_cone(
                self.bm, cap_ends=True, segments=segments, radius1=r_bottom, radius2=r_top, depth=height, matrix=matrix
            ),
            mat,
            smooth_sides=True,
        )

    def ellipsoid(
        self,
        centre: tuple[float, float, float],
        radii: tuple[float, float, float],
        mat: bpy.types.Material | None = None,
        u: int = 10,
        v: int = 7,
    ) -> "MeshBuilder":
        matrix = Matrix.Translation(centre) @ Matrix.Diagonal((*radii, 1.0))
        return self._primitive(
            lambda: bmesh.ops.create_uvsphere(self.bm, u_segments=u, v_segments=v, radius=1.0, matrix=matrix),
            mat,
            smooth_sides=True,
        )

    def oriented_box(
        self,
        centre: tuple[float, float, float],
        size: tuple[float, float, float],
        mat: bpy.types.Material | None = None,
        rot_x: float = 0.0,
        rot_z: float = 0.0,
        pivot: tuple[float, float, float] | None = None,
    ) -> "MeshBuilder":
        """Box of `size` rotated about X then Z (radians), around `pivot` (default: its centre)."""
        pivot = pivot or centre
        offset = Vector(centre) - Vector(pivot)
        rotation = Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Rotation(rot_x, 4, "X")
        matrix = Matrix.Translation(pivot) @ rotation @ Matrix.Translation(offset) @ Matrix.Diagonal((*size, 1.0))
        return self._primitive(lambda: bmesh.ops.create_cube(self.bm, size=1.0, matrix=matrix), mat)

    def grid(
        self,
        origin: tuple[float, float, float],
        u: tuple[float, float, float],
        v: tuple[float, float, float],
        cells: tuple[int, int],
        mat: bpy.types.Material | None = None,
    ) -> "MeshBuilder":
        """Flat quad grid spanning origin + s·u + t·v; faces point along u × v.

        Large surfaces need vertices for per-vertex ambient occlusion to show contact shadows.
        """
        nu, nv = cells
        o, du, dv = Vector(origin), Vector(u) / nu, Vector(v) / nv
        verts = [[self.bm.verts.new(o + du * i + dv * j) for j in range(nv + 1)] for i in range(nu + 1)]
        index = self._slot(mat)
        for i in range(nu):
            for j in range(nv):
                face = self.bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
                face.material_index = index
        return self

    def cone(
        self,
        base: tuple[float, float, float],
        radius: float,
        height: float,
        mat: bpy.types.Material | None = None,
        segments: int = 14,
    ) -> "MeshBuilder":
        x, y, z = base
        matrix = Matrix.Translation((x, y, z + height / 2))
        return self._primitive(
            lambda: bmesh.ops.create_cone(
                self.bm, cap_ends=True, segments=segments, radius1=radius, radius2=0.0, depth=height, matrix=matrix
            ),
            mat,
        )

    def gable(
        self,
        min_corner: tuple[float, float, float],
        max_corner: tuple[float, float, float],
        ridge: float,
        mat: bpy.types.Material | None = None,
    ) -> "MeshBuilder":
        """Pitched roof prism along X: eaves at min z, ridge `ridge` metres above, closed ends."""
        (x0, y0, z0), (x1, y1, z1) = min_corner, max_corner
        ym = (y0 + y1) / 2
        index = self._slot(mat)
        ends = []
        for x in (x0, x1):
            ends.append([self.bm.verts.new(v) for v in ((x, y0, z0), (x, y1, z0), (x, y1, z1), (x, ym, z1 + ridge), (x, y0, z1))])
        a, b = ends
        faces = [list(reversed(a)), b]
        for i in range(5):
            j = (i + 1) % 5
            faces.append([a[i], a[j], b[j], b[i]])
        for verts in faces:
            self.bm.faces.new(verts).material_index = index
        return self

    def _primitive(self, create, mat, smooth_sides: bool = False) -> "MeshBuilder":
        before = set(self.bm.faces)
        create()
        index = self._slot(mat)
        for face in set(self.bm.faces) - before:
            face.material_index = index
            # Round sides shade smooth (shared vertices); caps (n-gons) stay flat.
            if smooth_sides and len(face.verts) == 4:
                face.smooth = True
        return self

    def build(
        self,
        name: str,
        location: tuple[float, float, float] = (0.0, 0.0, 0.0),
        parent: bpy.types.Object | None = None,
    ) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(f"ME_{name}")  # distinct from node names in glTF
        if self.recalc_normals:
            bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
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


def bevel(obj: bpy.types.Object, width: float = 0.008, segments: int = 1) -> bpy.types.Object:
    """Non-destructive chamfer on edges sharper than 50° (box edges, caps; not the facets of
    coarse cylinders); applied at export with the other modifiers.

    A face-area weighted normal modifier follows: flat faces stay flat while the chamfer strip
    shades like a rounded edge, so it catches the light for the cost of one triangle strip."""
    mod = obj.modifiers.new("Chamfer", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(50)
    mod.use_clamp_overlap = True
    mesh = obj.data
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    normals = obj.modifiers.new("Normals", "WEIGHTED_NORMAL")
    normals.mode = "FACE_AREA"
    normals.weight = 50
    normals.keep_sharp = True
    normals.thresh = 0.01
    return obj


AO_ATTRIBUTE = "AO"


def rendered_meshes() -> list[bpy.types.Object]:
    """Meshes that are drawn at runtime (colliders, triggers and the like are hidden from render)."""
    return [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.hide_render]


def apply_modifiers(objects) -> None:
    """Replaces each object's mesh with its evaluated one (chamfers, custom normals) so UVs and
    bakes see the final topology. The .blend on disk keeps the modifiers: this runs on the
    in-memory copy just before export."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        if not obj.modifiers:
            continue
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
        mesh.name = obj.data.name
        obj.modifiers.clear()
        obj.data = mesh


def bake_ambient_occlusion(objects, samples: int = 24, distance: float = 0.8, strength: float = 0.75, isolate=None, ground=None) -> int:
    """Bakes ambient occlusion into a linear colour attribute on `objects` (modifiers already
    applied). `strength` < 1 softens the result to keep the stylised, bright look
    (docs/DA.md §04). Returns the number of meshes baked.

    `isolate(obj)` returns a group key for parts that move at runtime (doors, vehicles, loads) or
    None. Each group is baked alone: the rest of the scene is hidden meanwhile, otherwise a part
    would keep the shadows of the place it starts in (the inner face of a shelf door, dark from
    standing against the wall, would stay dark once the door swings out). `ground(obj)` keeps the
    floor and terrain visible meanwhile, for contact shadows.
    """
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.light_settings.distance = distance

    # Glass neither receives nor casts occlusion (it would darken what stands behind it).
    skipped = [o for o in scene.objects if o.get("ao_skip") and not o.hide_render]
    for obj in skipped:
        obj.hide_render = True
    targets = [o for o in objects if o.type == "MESH" and not o.hide_render]
    for obj in targets:
        # Per point, not per face corner: neighbouring faces can share vertices in the GLB.
        attr = obj.data.color_attributes.new(AO_ATTRIBUTE, "FLOAT_COLOR", "POINT")
        obj.data.color_attributes.active_color = attr
        obj.data.color_attributes.render_color_index = obj.data.color_attributes.find(AO_ATTRIBUTE)

    groups: dict[str | None, list] = {}
    for obj in targets:
        groups.setdefault(isolate(obj) if isolate else None, []).append(obj)
    visible = [o for o in scene.objects if o.type == "MESH" and not o.hide_render]
    for key, members in groups.items():
        if key is not None:
            for obj in visible:
                obj.hide_render = obj not in members and not (ground and ground(obj))
        bpy.ops.object.select_all(action="DESELECT")
        for obj in members:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = members[0]
        bpy.ops.object.bake(type="AO", target="VERTEX_COLORS")
        for obj in visible:
            obj.hide_render = False

    for obj in targets:
        data = obj.data.color_attributes[AO_ATTRIBUTE].data
        for item in data:
            ao = item.color[0]
            v = 1.0 - strength * (1.0 - ao)
            item.color = (v, v, v, 1.0)
    for obj in skipped:
        obj.hide_render = False
    return len(targets)


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
        # Baked ambient occlusion travels as COLOR_0 (three.js multiplies it into the albedo).
        export_vertex_color="NAME",
        export_vertex_color_name=AO_ATTRIBUTE,
        use_selection=False,
        use_visible=False,
    )


def _link(obj: bpy.types.Object, location, parent) -> None:
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    obj.location = location
    bpy.context.view_layer.update()
