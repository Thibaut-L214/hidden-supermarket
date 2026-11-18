"""First-person scanner: a right hand holding a handheld store terminal (docs/DA.md §05).

Usage (headless):
  Blender -b --factory-startup -P blender/scripts/build_scanner_hand.py -- <out.blend>

The tool is deliberately non-militarised: a rectangular inventory terminal held like a
phone, not a pistol-grip scanner. Its screen (SCANNER_SCREEN) shows the shelf aimed at and
the scan progress, drawn at runtime; the scan window (SCANNER_WINDOW) lights up when aiming.

Frame (metres, Z up): origin at the device's centre; the device's long axis is Z, its screen
faces -Y (towards the player, glTF +Z), its scan head points up. The runtime places and tilts
the whole in front of the camera.

Seen from very close, so both meshes are finished here rather than left to a modifier stack:
- the terminal is assembled from parts chamfered at their own scale (a 5 mm round on the shell,
  under a millimetre on the keys), then shaded with face-weighted normals;
- the hand is sketched with tapered tubes (palm, phalanges, thumb), fused into one skin by a
  voxel remesh, relaxed and decimated to a real-time budget.
"""

from __future__ import annotations

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))

from common import MeshBuilder, empty, material, reset_scene, save_blend  # noqa: E402

M = {}

# Triangle budget of the fused skin (nails and sleeve come on top, a few hundred more).
SKIN_TRIANGLES = 3400


def materials() -> None:
    M["body"] = material("M_TERMINAL_BODY", "#444A4E", roughness=0.5, metallic=0.1)
    M["rubber"] = material("M_TERMINAL_RUBBER", "#2A2C2E", roughness=0.9)
    M["accent"] = material("M_TERMINAL_ACCENT", "#6F8A68", roughness=0.5)
    M["key"] = material("M_TERMINAL_KEY", "#C4C7C8", roughness=0.55)
    M["bezel"] = material("M_TERMINAL_BEZEL", "#16191B", roughness=0.4)
    M["screen"] = material("M_TERMINAL_SCREEN", "#1D2326", roughness=0.15)
    M["window"] = material("M_TERMINAL_WINDOW", "#2F3A33", roughness=0.1, emission="#9BE3A6", emission_strength=0.0)
    # A muted mid tone, neither pale nor dark, low in saturation so the warm store light does not
    # push it to orange; stylised, no wrinkles.
    M["skin"] = material("M_HAND_SKIN", "#A38473", roughness=0.6)
    M["nail"] = material("M_HAND_NAIL", "#BFA398", roughness=0.4)
    M["sleeve"] = material("M_HAND_SLEEVE", "#6F7F87", roughness=0.9)


def evaluated(builder: MeshBuilder, setup) -> bpy.types.Mesh:
    """Mesh of a temporary object once `setup(obj)` has added its modifiers."""
    obj = builder.build("TMP_PART")
    setup(obj)
    bpy.context.view_layer.update()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    old = obj.data
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(old)
    return mesh


def part(slots: list) -> MeshBuilder:
    """Builder whose material slots follow `slots`, so parts can be merged index for index."""
    builder = MeshBuilder()
    builder.materials = list(slots)
    return builder


def chamfered(builder: MeshBuilder, width: float, segments: int) -> bpy.types.Mesh:
    def setup(obj) -> None:
        mod = obj.modifiers.new("Chamfer", "BEVEL")
        mod.width = width
        mod.segments = segments
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(50)
        mod.use_clamp_overlap = True

    return evaluated(builder, setup)


def merge(builder: MeshBuilder, meshes) -> None:
    for mesh in meshes:
        builder.bm.from_mesh(mesh)
        bpy.data.meshes.remove(mesh)


# ---------------------------------------------------------------------------------- terminal

SCREEN_HALF = (0.029, 0.037)
SCREEN_CENTRE = (0.0, -0.0163, 0.033)
FRONT = -0.016


def device(root) -> None:
    slots = [M["body"], M["rubber"], M["accent"], M["key"], M["bezel"]]
    body, rubber, accent, key, bezel = slots
    parts = []

    shell = part(slots).box((-0.038, FRONT, -0.085), (0.038, 0.016, 0.085), body)
    parts.append(chamfered(shell, 0.005, 3))

    # Rubber bumpers at both ends and the scan head carrying the window.
    bumpers = part(slots)
    bumpers.box((-0.0405, -0.0178, 0.077), (0.0405, 0.0178, 0.0985), rubber)
    bumpers.box((-0.0405, -0.0178, -0.0905), (0.0405, 0.0178, -0.072), rubber)
    parts.append(chamfered(bumpers, 0.004, 3))
    head = part(slots).box((-0.0285, -0.014, 0.094), (0.0285, 0.014, 0.1085), rubber)
    parts.append(chamfered(head, 0.003, 2))

    small = part(slots)
    # Rim round the scan window (SCANNER_WINDOW: x ±0.022, y ±0.008, z 0.108 to 0.112).
    for x0, x1, y0, y1 in (
        (-0.0245, 0.0245, -0.0105, -0.008),
        (-0.0245, 0.0245, 0.008, 0.0105),
        (-0.0245, -0.022, -0.008, 0.008),
        (0.022, 0.0245, -0.008, 0.008),
    ):
        small.box((x0, y0, 0.107), (x1, y1, 0.1126), body)
    # Bezel: a glossy frame standing 1.5 mm proud of the screen, which reads as recessed.
    sx, sz = SCREEN_HALF
    cz = SCREEN_CENTRE[2]
    outer = 0.0045
    y0, y1 = -0.0181, -0.0155
    small.box((-sx - outer, y0, cz + sz), (sx + outer, y1, cz + sz + outer), bezel)
    small.box((-sx - outer, y0, cz - sz - outer), (sx + outer, y1, cz - sz), bezel)
    small.box((-sx - outer, y0, cz - sz), (-sx, y1, cz + sz), bezel)
    small.box((sx, y0, cz - sz), (sx + outer, y1, cz + sz), bezel)
    # Side scan triggers above the grip.
    for x0, x1 in ((-0.0412, -0.0375), (0.0375, 0.0412)):
        small.box((x0, -0.0075, 0.032), (x1, 0.0075, 0.058), accent)
    # Rubber grip strips down both sides.
    for x0, x1 in ((-0.0402, -0.037), (0.037, 0.0402)):
        small.box((x0, -0.0115, -0.069), (x1, 0.0115, 0.024), rubber)
    parts.append(chamfered(small, 0.0009, 1))

    # Keypad: a wide scan key between two function keys, then twelve keys.
    keys = part(slots)
    k0, k1 = -0.0181, -0.0155
    keys.box((-0.0115, k0, -0.0235), (0.0115, k1, -0.0125), accent)
    for x0, x1 in ((-0.0265, -0.016), (0.016, 0.0265)):
        keys.box((x0, k0, -0.0225), (x1, k1, -0.0135), key)
    for row in range(4):
        for col in range(3):
            x0 = -0.0255 + col * 0.018
            z0 = -0.066 + row * 0.0105
            keys.box((x0, k0, z0), (x0 + 0.015, k1, z0 + 0.0075), key, skip=("+y",))
    parts.append(chamfered(keys, 0.0008, 1))

    # Fine relief, left sharp: grip ribs, speaker slots and a status light on the top bumper.
    fine = part(slots)
    for side in (-1, 1):
        for i in range(9):
            z0 = -0.064 + i * 0.0095
            xa, xb = sorted((side * 0.0396, side * 0.0414))
            fine.box((xa, -0.009, z0), (xb, 0.009, z0 + 0.0035), rubber)
    for i in range(5):
        x0 = -0.011 + i * 0.0048
        fine.box((x0, -0.0182, 0.0835), (x0 + 0.0018, -0.017, 0.091), bezel)
    fine.box((0.024, -0.0184, 0.0855), (0.029, -0.017, 0.0885), accent)

    whole = part(slots)
    merge(whole, parts + [evaluated(fine, lambda obj: None)])
    whole.bm.normal_update()
    for edge in whole.bm.edges:
        if len(edge.link_faces) == 2 and edge.calc_face_angle(0.0) > math.radians(50):
            edge.smooth = False
    for face in whole.bm.faces:
        face.smooth = True
    obj = whole.build("SCANNER_BODY", parent=root)
    # Face-weighted normals: flat faces stay flat, the chamfer strips shade as rounded edges.
    normals = obj.modifiers.new("Normals", "WEIGHTED_NORMAL")
    normals.mode = "FACE_AREA"
    normals.weight = 50
    normals.keep_sharp = True
    normals.thresh = 0.01

    # Screen and window stay plain boxes at fixed places: the runtime lays its canvas on the
    # screen's front face and reads the window's position and material.
    screen = MeshBuilder().box((-sx, -0.0003, -sz), (sx, 0.0003, sz), M["screen"])
    screen.build("SCANNER_SCREEN", SCREEN_CENTRE, root)
    window = MeshBuilder().box((-0.022, -0.008, -0.002), (0.022, 0.008, 0.002), M["window"])
    window.build("SCANNER_WINDOW", (0.0, 0.0, 0.11), root)


# -------------------------------------------------------------------------------------- hand


def digit(b: MeshBuilder, joints, r_base: float, r_tip: float, ref) -> None:
    """Phalanges through `joints` (last one is the centre of the fingertip): straight tapered
    segments, slightly thicker at the knuckles, closed by a rounded tip."""
    pts = [Vector(j) for j in joints]
    last = len(pts) - 1
    rings = []
    for i in range(last):
        for s in (0.0, 0.5):
            t = (i + s) / last
            radius = r_base + (r_tip - r_base) * t
            swell = 1.06 if s == 0.0 and i > 0 else 0.96 if s else 1.0
            rings.append((tuple(pts[i].lerp(pts[i + 1], s)), radius * swell, radius * swell * 1.04))
    along = (pts[last] - pts[last - 1]).normalized()
    for angle in (0, 30, 55, 75):
        a = math.radians(angle)
        r = r_tip * math.cos(a)
        rings.append((tuple(pts[last] + along * (r_tip * math.sin(a))), r, r * 1.04))
    b.loft(rings, M["skin"], segments=12, ref=ref)


def nail(b: MeshBuilder, joints, radius: float, outward) -> None:
    """Flat nail on the back of the last phalanx, `outward` pointing away from the device.

    The skin under it is pressed just below the nail's rim first: the decimated skin is too
    irregular for a thin shell to cross it along a clean outline."""
    tip, prev = Vector(joints[-1]), Vector(joints[-2])
    along = (tip - prev).normalized()
    out = Vector(outward)
    out = (out - along * out.dot(along)).normalized()
    across = along.cross(out)
    centre = tip - along * 0.002 + out * (radius * 0.9)
    basis = Matrix((along, across, out)).transposed().to_4x4()
    matrix = Matrix.Translation(centre) @ basis @ Matrix.Diagonal((0.006, radius * 0.62, radius * 0.2, 1.0))
    to_local = matrix.inverted()
    for vert in b.bm.verts:
        local = to_local @ vert.co
        if local.x**2 + local.y**2 < 1.35**2 and -0.15 < local.z < 6.0:
            local.z = -0.15
            vert.co = matrix @ local
    before = set(b.bm.faces)
    bmesh.ops.create_uvsphere(b.bm, u_segments=12, v_segments=4, radius=1.0, matrix=matrix)
    index = b._slot(M["nail"])
    for face in set(b.bm.faces) - before:
        face.material_index = index
        face.smooth = True


# Fingers wrap round the device's left edge: knuckle behind it, then the back-left corner, the
# front-left corner, and the pad resting on the front. (knuckle x, z at knuckle, z at tip, radius, reach)
FINGERS = (
    (-0.008, 0.000, 0.019, 0.0084, 0.0),
    (-0.013, -0.019, -0.002, 0.0087, 0.001),
    (-0.014, -0.037, -0.0225, 0.0081, 0.0),
    (-0.010, -0.053, -0.0415, 0.0070, -0.004),
)
THUMB = ((0.034, 0.030, -0.072), (0.0505, 0.014, -0.041), (0.0512, -0.010, -0.017), (0.0435, -0.0243, -0.001))
THUMB_RADII = (0.0125, 0.0092)


def finger_joints(spec):
    mx, zm, zt, radius, reach = spec
    z = lambda t: zm + (zt - zm) * t  # noqa: E731
    return (
        (mx, 0.030, z(0.0)),
        (-0.0432 - radius, 0.0215, z(0.6)),
        (-0.0422 - radius, -0.0125, z(0.9)),
        (-0.0375 - reach, -0.0162 - radius, z(1.0)),
    )


def hand(root) -> None:
    slots = [M["skin"], M["nail"], M["sleeve"]]
    sketch = part(slots)
    # Palm against the back of the device, from the wrist up to the knuckles.
    sketch.loft(
        [
            ((0.024, 0.040, -0.114), 0.027, 0.018),
            ((0.018, 0.035, -0.085), 0.036, 0.016),
            ((0.012, 0.032, -0.050), 0.036, 0.014),
            ((0.008, 0.031, -0.015), 0.030, 0.0135),
            ((0.004, 0.031, 0.010), 0.022, 0.011),
            ((0.002, 0.031, 0.019), 0.012, 0.007),
        ],
        M["skin"],
        segments=16,
    )
    # Ball of the thumb and heel of the hand.
    sketch.ellipsoid((0.034, 0.030, -0.068), (0.019, 0.015, 0.030), M["skin"], u=14, v=9)
    sketch.ellipsoid((-0.008, 0.033, -0.078), (0.014, 0.013, 0.025), M["skin"], u=12, v=8)
    # Wrist and forearm, going down, back and to the right, out of frame under the sleeve.
    sketch.loft(
        [
            ((0.024, 0.040, -0.100), 0.027, 0.018),
            ((0.034, 0.048, -0.150), 0.026, 0.019),
            ((0.040, 0.053, -0.176), 0.027, 0.020),
        ],
        M["skin"],
        segments=16,
    )
    for spec in FINGERS:
        digit(sketch, finger_joints(spec), spec[3], spec[3] * 0.9, ref=(0.0, 0.0, 1.0))
    digit(sketch, THUMB, *THUMB_RADII, ref=(1.0, 0.0, 0.0))

    def fuse(obj) -> None:
        remesh = obj.modifiers.new("Fuse", "REMESH")
        remesh.mode = "VOXEL"
        remesh.voxel_size = 0.0013
        remesh.adaptivity = 0.0
        relax = obj.modifiers.new("Relax", "SMOOTH")
        relax.factor = 0.5
        relax.iterations = 5

    skin = evaluated(sketch, fuse)
    triangles = sum(len(p.vertices) - 2 for p in skin.polygons)
    dense = part(slots)
    merge(dense, [skin])

    def reduce(obj) -> None:
        decimate = obj.modifiers.new("Reduce", "DECIMATE")
        decimate.ratio = min(1.0, SKIN_TRIANGLES / triangles)

    h = part(slots)
    merge(h, [evaluated(dense, reduce)])
    for face in h.bm.faces:
        face.material_index = 0
        face.smooth = True

    for spec in FINGERS:
        nail(h, finger_joints(spec), spec[3] * 0.9, (-0.35, -1.0, 0.0))
    nail(h, THUMB, THUMB_RADII[1], (0.3, -1.0, 0.1))
    # Sleeve: a cuff, then the forearm leaving the frame.
    h.loft(
        [
            ((0.0355, 0.0495, -0.156), 0.031, 0.024),
            ((0.036, 0.050, -0.159), 0.0335, 0.0265),
            ((0.038, 0.052, -0.170), 0.034, 0.027),
            ((0.075, 0.085, -0.330), 0.041, 0.035),
        ],
        M["sleeve"],
        segments=14,
    )
    h.build("SCANNER_HAND", parent=root)


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: build_scanner_hand.py -- <out.blend>")
    reset_scene()
    materials()
    root = empty("SCANNER_ROOT")
    device(root)
    hand(root)
    save_blend(os.path.abspath(argv[0]))


main()
