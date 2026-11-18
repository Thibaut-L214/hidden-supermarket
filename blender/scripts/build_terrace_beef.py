"""Schematic indoor cattle finishing chain, elevated observation only.

Blender +Y faces forward (glTF -Z). Ground -12m, terrace 0m. Distances are compressed. The
opaque killing building never reveals its interior (docs/DECISIONS.md). Same method as the eggs
terrace: shared prop kit (terrace_props.py), relief and vegetation (landscape_props.py), textured
materials by name (blender/textures/surfaces.json) and baked sky light (lightmap profile
`terrace`). Cattle are schematic: sober volumes, no gesture, no figure attached (TODO_SOURCE).

Local frame: the origin is the threshold, i.e. the back face of the store wall at floor level
where the runtime places it on ANCHOR_BEEF_TERRACE. The beef shelf sits at x = 6 in the store,
so the store spans x ∈ [-18.3, 6.3], y ∈ [-18.6, 0] here.
Run: Blender -b --factory-startup -P this.py -- blender/terrace_beef.blend
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bpy
import landscape_props as land
import lowpoly as lp
import terrace_props as props
from common import MeshBuilder, bevel, box, empty, helper_volume, material, reset_scene, save_blend
from mathutils import Vector

G = -12.0
# Road surface: trucks, ramps and the path points that follow roads stand on it.
R = land.ROAD_TOP
M = {}

TERRACE_HALF_W, TERRACE_DEPTH, RAIL_H = 6.0, 7.0, 1.05
STORE_X0, STORE_X1, STORE_BACK_Y = -18.3, 6.3, -18.9
FARM = (-18.0, 19.0, -3.0, 34.0)  # x0, y0, x1, y1 of the cattle shed
FARM_WALL_H, FARM_RIDGE = 3.0, 1.7

# Axis-aligned centre lines and widths. The animal truck loads in the lane x = -8.5 and leaves by
# the main road (x = 5); the delivery truck joins it from the east.
ROADS = [
    ((-8.5, 2.0), (-8.5, 19.0), 7.0),  # loading lane under the ramp
    ((-13.0, 16.0), (11.0, 16.0), 6.0),  # farm road
    ((5.0, 10.0), (5.0, 110.0), 8.0),  # main road, leaves the scene to the north
    ((4.0, 29.0), (19.0, 29.0), 8.0),  # abattoir unloading apron
    ((8.0, 15.0), (46.0, 15.0), 6.0),  # delivery road from the processing rooms
]
SITE_FENCE = (-42.0, 10.0, 47.0, 84.0)
# Two more finishing sheds behind the first, same footprint (docs/DA.md §06: repeated volumes).
CROWD_SHEDS = [(-18.0, 41.0, -3.0, 56.0), (-18.0, 63.0, -3.0, 78.0)]
PLATEAU, PLATEAU_Z = (-51.0, -100.0, 39.0, -19.0), -0.8
HIDES = ("cream", "tan", "brown", "blond", "cream", "brown")
# Baked tints of the one cattle material (M_ANIMAL_CATTLE, white): hides, muzzle, hooves, ear tags.
HIDE = {"cream": lp.lin("#D8C8A4"), "tan": lp.lin("#BA9873"), "brown": lp.lin("#8D6952"), "blond": lp.lin("#B88556")}
MUZZLE, HOOF, TAG = lp.lin("#6B5A50"), lp.lin("#423F3A"), lp.lin("#E0BC50")
# Baked tints of the loads (props M_LOAD_PAINT): trays, product, cartons, labels.
TRAY, MEAT, CARTON, LABEL = lp.lin("#E8E4D8"), lp.lin("#98594F"), lp.lin("#BEA784"), lp.lin("#C9D3D6")
# Height of a standing steer, to normalise the height baked in `_PHASE`.
COW_HEIGHT = 1.65
# The two finishing sheds behind the first differ a little, like sheds of different ages:
# (tone of the sheets, ridge vents).
SHED_LOOK = {1: (1.0, 3), 2: (0.93, 0), 3: (0.98, 4)}


def mats():
    # Shared infrastructure keeps the eggs terrace's names: same textures, same look.
    M["slab"] = material("M_TERRACE_CONCRETE", "#D5D2CB", roughness=0.85)
    M["plinth"] = material("M_TERRACE_FACADE", "#B9BFC2", roughness=0.9)
    M["rail"] = material("M_RAIL_METAL", "#8F969A", roughness=0.4, metallic=0.6)
    M["road"] = material("M_ROAD", "#8A8A86", roughness=0.9)
    M["farm"] = material("M_FARM_WALL", "#B9AF9D", roughness=0.85)
    M["farm_floor"] = material("M_FARM_FLOOR", "#8C857A", roughness=0.95)
    M["farm_roof"] = material("M_FARM_ROOF", "#7F7A72", roughness=0.7, metallic=0.2)
    M["plant"] = material("M_PLANT_WALL", "#C7CCD1", roughness=0.6, metallic=0.2)
    M["plant_roof"] = material("M_PLANT_ROOF", "#7C838A", roughness=0.6, metallic=0.3)
    M["hill"] = material("M_HILL", "#9AA08A", roughness=1.0)
    M["silo"] = material("M_SILO", "#C8CCCF", roughness=0.4, metallic=0.5)
    # Beef-specific surfaces.
    for key, (name, color, rough, metal) in {
        "straw": ("M_BEEF_STRAW", "#C8AC66", 1.0, 0),
        "feed": ("M_BEEF_FEED", "#A19464", 1.0, 0),
        "hay": ("M_BEEF_HAY", "#C9B26E", 1.0, 0),
        "water": ("M_BEEF_WATER", "#6E9396", 0.1, 0),
        "white": ("M_BEEF_PANEL", "#E5E5D9", 0.6, 0),
        "cold": ("M_BEEF_COLD_PANEL", "#D9E5E3", 0.5, 0),
        "blue": ("M_BEEF_REEFER", "#78969B", 0.5, 0.1),
        "tarp": ("M_BEEF_TARP", "#4F5A52", 0.9, 0),
    }.items():
        M[key] = material(name, color, roughness=rough, metallic=metal)
    M["plant_flat"] = material("M_PLANT_ROOF_FLAT", "#8E9499", roughness=0.9)
    # One white material for all cattle: hide, muzzle, hoof and tag colours are baked tints.
    M["cattle"] = material("M_ANIMAL_CATTLE", "#FFFFFF", roughness=0.9)
    props.materials()
    land.materials()


# --- pens, gates, rails ------------------------------------------------------------------------

def rails(name, a, b, parent, z=G, height=1.5):
    """Tubular pen fence: posts every 2 m and three horizontal rails, square in section (round
    tubes of 7 cm cannot be told apart from 20 m)."""
    x0, y0 = a
    x1, y1 = b
    length = math.hypot(x1 - x0, y1 - y0)
    count = max(1, math.ceil(length / 2))
    low = height < 1.1
    m = MeshBuilder(recalc_normals=False)
    pr = 0.025 if low else 0.045
    for i in range(count + 1):
        f = i / count
        x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        lp.box_faces(m, (x - pr, y - pr, z), (x + pr, y + pr, z + height + pr), M["rail"])
    for h in (0.3, 0.7, 1.02) if low else (0.45, 0.95, 1.4):
        lp.tube(m, (x0, y0, z + h), (x1, y1, z + h), 0.025 if low else 0.045, M["rail"])
    m.build(name, parent=parent)


def ribbed_wall(c, a, b, z0, height, normal, base=0.6, mat=None, seed=1, tone=1.0, pipes=True):
    """Outside of a clad wall a→b, on its `normal` side, added to the builder `c`: concrete base
    course, weathered sheet (the ribs come from the `cladding` texture), a downpipe at each end."""
    (x0, y0), (x1, y1) = a, b
    nx, ny = normal
    lo = (min(x0, x1) + min(0, nx * 0.08), min(y0, y1) + min(0, ny * 0.08), z0)
    hi = (max(x0, x1) + max(0, nx * 0.08), max(y0, y1) + max(0, ny * 0.08), z0 + base)
    hidden = {(-1, 0): "+x", (1, 0): "-x", (0, -1): "+y", (0, 1): "-y"}[(nx, ny)]
    c.box(lo, hi, props.M["base"], skip=("-z", hidden))
    props.clad_wall(c, a, b, z0 + base, z0 + height, normal, mat or M["farm"], seed, tone)
    if pipes:
        for x, y in ((x0, y0), (x1, y1)):
            ux, uy = (x1 - x0), (y1 - y0)
            length = math.hypot(ux, uy)
            inset = 0.4 if (x, y) == (x0, y0) else -0.4
            props.downpipe(c, x + ux / length * inset + nx * 0.1, y + uy / length * inset + ny * 0.1, z0, z0 + height)


# --- cattle ------------------------------------------------------------------------------------

class Xf:
    """Draws into a MeshBuilder with a local frame: origin `o`, optionally turned so that local
    +Y (the animal's front) points along world +X. Lets one cow description serve both the
    articulated timeline cattle and the static, merged crowd."""

    def __init__(self, m, o=(0.0, 0.0, 0.0), turned=False):
        self.m, self.o, self.turned = m, o, turned

    def p(self, v):
        x, y, z = v
        if self.turned:
            x, y = y, -x
        return (self.o[0] + x, self.o[1] + y, self.o[2] + z)

    def loft(self, rings, mat, segments=12, caps=True):
        vertical = abs(rings[-1][0][2] - rings[0][0][2]) > abs(rings[-1][0][1] - rings[0][0][1])
        if self.turned and vertical:
            rings = [(c, rv, ru) for c, ru, rv in rings]
        ref = (0.0, 0.0, 1.0) if self.turned and not vertical else (0.0, 1.0, 0.0)
        self.m.loft([(self.p(c), ru, rv) for c, ru, rv in rings], mat, segments=segments, caps=caps, ref=ref)

    def ellipsoid(self, c, r, mat, u=10, v=7):
        self.m.ellipsoid(self.p(c), (r[1], r[0], r[2]) if self.turned else r, mat, u=u, v=v)

    def limb(self, a, b, ra, rb, mat, segments=8):
        self.m.limb(self.p(a), self.p(b), ra, rb, mat, segments=segments)

    def box(self, lo, hi, mat):
        a, b = self.p(lo), self.p(hi)
        self.m.box(tuple(map(min, a, b)), tuple(map(max, a, b)), mat)

    def along(self, v):
        """Local Y (towards the head) of a point of the mesh."""
        return (v[0] - self.o[0]) if self.turned else (v[1] - self.o[1])


class Coat:
    """Paints what was added to a mesh since the last call: tint per vertex, and the `_PHASE`
    data of the animal (phase, height above its feet, head weight)."""

    def __init__(self, m, frame, feet_z, phase):
        self.bm = (m.m if isinstance(m, Xf) else m).bm
        self.builder = m.m if isinstance(m, Xf) else m
        self.frame = frame if isinstance(frame, Xf) else Xf(self.builder)
        self.feet_z, self.phase = feet_z, phase
        self.tints = lp._tint_layer(self.bm)
        self.layer = lp._phase_layer(self.bm)
        self.done = len(self.bm.faces)

    def apply(self, tint, head=0.0):
        """`tint`: RGB, or a function of the point's local Y (towards the head) and height."""
        self.bm.faces.ensure_lookup_table()
        for face in self.bm.faces[self.done:]:
            for loop in face.loops:
                co = loop.vert.co
                h = min(1.0, max(0.0, (co.z - self.feet_z) / COW_HEIGHT))
                y = self.frame.along(co)
                c = tint(y, co.z - self.feet_z) if callable(tint) else tint
                loop[self.tints] = (c[0], c[1], c[2], 1.0)
                loop.vert[self.layer] = (self.phase, h, head(y) if callable(head) else head)
        self.done = len(self.bm.faces)


def _frame_of(m):
    return m if isinstance(m, Xf) else Xf(m)


def cow_body(m, hide, coat, fine=True):
    """Body, neck, head, ears, tags and tail of a standing, polled beef steer, facing local +Y.
    `m` is a MeshBuilder or an Xf, `hide` the RGB of its coat, `coat` the Coat that paints it.
    `fine=False` builds the low version of the merged crowds."""
    m = _frame_of(m)
    mat = M["cattle"]
    belly = lp.scale(hide, 0.78)
    body = [
        ((0, -0.98, 1.28), 0.14, 0.18), ((0, -0.86, 1.29), 0.27, 0.33), ((0, -0.55, 1.22), 0.37, 0.45),
        ((0, -0.15, 1.16), 0.40, 0.50), ((0, 0.25, 1.17), 0.39, 0.50), ((0, 0.5, 1.22), 0.33, 0.46),
        ((0, 0.68, 1.30), 0.22, 0.34),
    ]
    neck = [
        ((0, 0.60, 1.30), 0.22, 0.34), ((0, 0.82, 1.32), 0.17, 0.28), ((0, 0.98, 1.26), 0.155, 0.24),
        ((0, 1.10, 1.13), 0.14, 0.19), ((0, 1.22, 1.03), 0.125, 0.15), ((0, 1.31, 0.97), 0.115, 0.12),
        ((0, 1.36, 0.955), 0.095, 0.095),
    ]
    if not fine:
        body = [body[0], body[2], body[4], body[5], body[6]]
        neck = [neck[0], neck[2], neck[4], neck[6]]
    m.loft(body, mat, segments=10 if fine else 6)
    # Lighter along the back, darker under the belly: the volume reads from above.
    coat.apply(lambda y, z: lp.mix(belly, hide, min(1.0, max(0.0, (z - 0.95) / 0.5))))
    m.loft(neck, mat, segments=8 if fine else 5)
    head = lambda y: min(1.0, max(0.0, (y - 0.6) / 0.5))  # noqa: E731
    coat.apply(lambda y, z: MUZZLE if y > 1.27 else hide, head)
    for side in (-1, 1):
        if fine:
            m.ellipsoid((side * 0.24, 0.97, 1.33), (0.15, 0.05, 0.045), mat, u=6, v=4)  # ear
            coat.apply(lp.scale(hide, 0.9), 1.0)
            m.box((side * 0.31 - 0.03, 0.93, 1.2), (side * 0.31 + 0.03, 0.955, 1.3), mat)
            coat.apply(TAG, 1.0)
        else:
            lo, hi = sorted((side * 0.12, side * 0.38))
            m.box((lo, 0.95, 1.3), (hi, 1.0, 1.36), mat)
            coat.apply(lp.scale(hide, 0.9), 1.0)
    if fine:
        m.ellipsoid((0, 0.62, 0.9), (0.1, 0.19, 0.2), mat, u=6, v=4)  # dewlap
        coat.apply(belly, 0.3)
    m.limb((0, -0.97, 1.36), (0.04, -1.06, 0.62), 0.032, 0.015, mat, segments=4 if fine else 3)  # tail
    coat.apply(lp.scale(hide, 0.85))


def cow_leg(m, rear, hide, coat, fine=True):
    """One leg from the hip joint (local origin) down to the hoof, 1 m below."""
    m = _frame_of(m)
    rings = [
        ((0, 0.0, 0.05), 0.12 if rear else 0.10, 0.17 if rear else 0.14),
        ((0, -0.04 if rear else 0.0, -0.25), 0.10 if rear else 0.085, 0.13 if rear else 0.10),
        ((0, -0.10 if rear else 0.02, -0.5), 0.055, 0.07),
        ((0, -0.03, -0.78), 0.04, 0.045),
        ((0, 0.0, -0.9), 0.05, 0.055),
        ((0, 0.03, -1.0), 0.052, 0.085),
    ]
    if not fine:
        rings = [rings[0], rings[2], rings[5]]
    m.loft(rings, M["cattle"], segments=6 if fine else 4, caps=False)
    shade = lp.scale(hide, 0.86)
    coat.apply(lambda y, z: HOOF if z < 0.11 else shade)


LEGS = ((-0.25, -0.58), (0.25, -0.58), (-0.25, 0.48), (0.25, 0.48))


def animal(name, position, parent, variation=0):
    """Ground-centred independent root, top-jointed legs, facing local +Y (schematic standing
    steer, see cow_body). Legs are separate joints so the walk can swing them; body and legs
    share the animal's phase, and heights are measured from its feet."""
    root = empty(name, position, parent)
    root["animalIndex"] = variation
    hide = lp.scale(HIDE[HIDES[variation % len(HIDES)]], 0.94 + 0.06 * lp.rand(variation, len(name), 3))
    phase = lp.rand(sum(map(ord, name)), 5)
    body = MeshBuilder()
    cow_body(body, hide, Coat(body, body, 0.0, phase))
    body.build(name + "_BODY", parent=root)
    for j, (x, y) in enumerate(LEGS):
        leg = empty("CATTLE_LEG_" + name + "_" + str(j), (x, y, 1.0), root)
        limb = MeshBuilder()
        cow_leg(limb, y < 0, hide, Coat(limb, limb, -1.0, phase))
        limb.build(name + "_LIMB_" + str(j), parent=leg)
    return root


def crowd(name, cows, parent):
    """Many static cattle merged into one mesh and one material (one draw call for dozens of
    animals). `cows`: (x, y, z, hide index) in the parent's frame, all facing +X."""
    m = MeshBuilder()
    for n, (x, y, z, k) in enumerate(cows):
        hide = lp.scale(HIDE[HIDES[k % len(HIDES)]], 0.9 + 0.1 * lp.rand(n, k, 7))
        frame = Xf(m, (x, y, z), True)
        coat = Coat(m, frame, z, lp.rand(n, int(x * 10), int(y * 10)))
        cow_body(frame, hide, coat, fine=False)
        for lx, ly in LEGS:
            cow_leg(Xf(m, frame.p((lx, ly, 1.0)), True), ly < 0, hide, coat, fine=False)
    return m.build(name, parent=parent)


def cattle_group(name, positions, parent):
    group = empty(name, parent=parent)
    for i, p in enumerate(positions):
        animal(name + "_" + str(i + 1).zfill(2), p, group, i)
    return group


def lying_cow(name, x, y, parent, hide):
    """Resting individual, legs folded under the body, head up (not on the timeline)."""
    m = MeshBuilder()
    mat = M["cattle"]
    coat = Coat(m, Xf(m, (x, y, 0.0)), 0.0, lp.rand(int(x * 7), int(y * 13)))
    m.loft([
        ((x, y - 0.85, 0.5), 0.16, 0.2), ((x, y - 0.6, 0.52), 0.38, 0.34), ((x, y - 0.1, 0.5), 0.45, 0.4),
        ((x, y + 0.4, 0.52), 0.43, 0.4), ((x, y + 0.75, 0.62), 0.3, 0.34),
    ], mat, segments=8)
    coat.apply(lambda yy, z: lp.mix(lp.scale(hide, 0.78), hide, min(1.0, max(0.0, (z - 0.3) / 0.4))))
    m.loft([
        ((x, y + 0.7, 0.82), 0.2, 0.28), ((x, y + 0.95, 0.98), 0.16, 0.22), ((x, y + 1.12, 0.9), 0.13, 0.17),
        ((x, y + 1.33, 0.77), 0.1, 0.1),
    ], mat, segments=6)
    coat.apply(lambda yy, z: MUZZLE if yy > 1.24 else hide, lambda yy: min(1.0, max(0.0, (yy - 0.6) / 0.5)))
    for side in (-1, 1):
        m.ellipsoid((x + side * 0.23, y + 0.9, 1.13), (0.14, 0.05, 0.04), mat, u=6, v=4)
        coat.apply(lp.scale(hide, 0.9), 1.0)
        m.ellipsoid((x + side * 0.38, y - 0.45, 0.17), (0.09, 0.3, 0.1), mat, u=6, v=4)
        m.ellipsoid((x + side * 0.3, y + 0.55, 0.13), (0.07, 0.22, 0.08), mat, u=6, v=4)
        coat.apply(lp.scale(hide, 0.82))
    m.build(name, (0, 0, G + 0.12), parent)


# --- site: terrace, ground, roads, vegetation --------------------------------------------------

def terrace(root):
    box("TERRACE_FLOOR", (-TERRACE_HALF_W, 0, -0.3), (TERRACE_HALF_W, TERRACE_DEPTH, 0), M["slab"], root)
    box("TERRACE_PLINTH", (STORE_X0, STORE_BACK_Y, G), (STORE_X1, TERRACE_DEPTH, -0.1), M["plinth"], root)
    runs = {
        "N": ((-TERRACE_HALF_W, TERRACE_DEPTH - 0.1), (TERRACE_HALF_W, TERRACE_DEPTH)),
        "E": ((TERRACE_HALF_W - 0.1, 0), (TERRACE_HALF_W, TERRACE_DEPTH)),
        "W": ((-TERRACE_HALF_W, 0), (-TERRACE_HALF_W + 0.1, TERRACE_DEPTH)),
    }
    for key, ((x0, y0), (x1, y1)) in runs.items():
        b = MeshBuilder()
        b.box((x0, y0, 0.1), (x1, y1, RAIL_H - 0.08), props.M["rail_glass"])
        b.box((x0 - 0.02, y0 - 0.02, RAIL_H - 0.06), (x1 + 0.02, y1 + 0.02, RAIL_H), M["rail"])
        along_x = (x1 - x0) > (y1 - y0)
        length = (x1 - x0) if along_x else (y1 - y0)
        for i in range(int(length / 1.5) + 1):
            t = min(i * 1.5, length - 0.06)
            px, py = (x0 + t, y0) if along_x else (x0, y0 + t)
            b.box((px - 0.01, py - 0.01, 0), (px + 0.07, py + 0.07, RAIL_H - 0.06), M["rail"])
        bevel(b.build("TERRACE_RAIL_" + key, parent=root), 0.006)
        helper_volume(box("COL_RAIL_" + key, (x0 - 0.05, y0 - 0.05, 0), (x1 + 0.05, y1 + 0.05, RAIL_H), None, root))
    # Solid rear guards around the 3m portal prevent leaving the observation area.
    for label, x0, x1 in (("L", -6, -1.5), ("R", 1.5, 6)):
        box("TERRACE_BEEF_BACK_" + label, (x0, -0.15, 0), (x1, 0, 2.3), M["plinth"], root)
        helper_volume(box("COL_BEEF_BACK_" + label, (x0, -0.15, 0), (x1, 0, 2.3), None, root))
    empty("ANCHOR_BEEF_VIEW", (0, 6.2, 1.6), root)
    empty("ANCHOR_BEEF_FOCUS", (-2, 28, G + 1), root)
    joints = MeshBuilder()
    for x in (-3.0, 0.0, 3.0):
        joints.box((x - 0.01, 0, 0), (x + 0.01, TERRACE_DEPTH, 0.004), props.M["base"])
    joints.box((-TERRACE_HALF_W, 3.49, 0), (TERRACE_HALF_W, 3.51, 0.004), props.M["base"])
    joints.build("TERRACE_JOINTS", parent=root)["ao_skip"] = True


def landscape(root):
    road_rects = [land.road_rect(r) for r in ROADS]
    yards = [(-42.0, 14.0, 0.0, 82.0), (10.0, 22.0, 46.0, 52.0), (30.0, 17.0, 44.0, 50.0)]
    flat = yards + [(STORE_X0, STORE_BACK_Y, STORE_X1, TERRACE_DEPTH), (-14.0, 0.0, -3.0, 20.0)]
    flat += [(x0 - 2.5, y0 - 2.5, x1 + 2.5, y1 + 2.5) for x0, y0, x1, y1 in road_rects]
    terrain = land.Terrain(G, flat, PLATEAU, PLATEAU_Z)
    # Rough grass left under the fence; concrete service strip along the east side of the sheds.
    fx0, fy0, fx1, fy1 = SITE_FENCE
    bands = [(fx0 - 0.9, fy1 - 0.9, 0.0, fy1 + 0.9), (10.0, fy1 - 0.9, fx1 + 0.9, fy1 + 0.9), (fx0 - 0.9, fy0, fx0 + 0.9, fy1),
             (fx1 - 0.9, 19.0, fx1 + 0.9, fy1), (fx0 - 0.9, fy0 - 0.9, -12.0, fy0 + 0.9), (10.0, fy0 - 0.9, fx1 + 0.9, fy0 + 0.9)]
    lanes = [(-3.0, 19.0, 1.0, 80.0)]
    terrain.build("TERRAIN_BEEF", (-250.0, -100.0, 250.0, 400.0), 5.0, (45.0, 55.0), root, yards=yards, bands=bands, lanes=lanes, roads=ROADS,
                  fine=(-50.0, 0.0, 55.0, 90.0))
    # Dashes follow the centre of the through roads, not the loading lane or the aprons.
    land.roads("ROAD_BEEF", ROADS, G, M["road"], root, dashed=[False, True, True, False, True])

    hedges = []
    for bx in range(-235, 240, 45):
        for by in range(-65, 390, 55):
            if math.hypot(bx - 10, by - 60) > 230:
                continue
            h = land._hash(bx + 7, by)
            if h % 4 == 0:
                hedges.append(((float(bx), float(by)), (float(bx), float(by + 55))))
            if h % 5 == 1:
                hedges.append(((float(bx), float(by)), (float(bx + 45), float(by))))

    def crosses_road(seg):
        (ax, ay), (bx, by) = seg
        return any(
            min(ax, bx) <= x1 + 4 and max(ax, bx) >= x0 - 4 and min(ay, by) <= y1 + 4 and max(ay, by) >= y0 - 4
            for x0, y0, x1, y1 in road_rects
        )

    def between_fields(seg):
        (ax, ay), (bx, _) = seg
        fx, fy = round((ax + 1000.0) / 45.0), round((ay + 1000.0) / 55.0)
        return land.is_field_boundary((fx - 1, fy), (fx, fy)) if ax == bx else land.is_field_boundary((fx, fy - 1), (fx, fy))

    hedges = [h for h in hedges if not crosses_road(h) and between_fields(h)]
    rows = [((11.0, 62.0), (11.0, 104.0), "poplar"), ((-47.0, 12.0), (-47.0, 70.0), "round"), ((50.0, 20.0), (50.0, 55.0), "round")]
    groves = [
        (-90.0, 60.0, 12), (-140.0, 150.0, 14), (110.0, 90.0, 12), (150.0, 200.0, 14), (-40.0, 190.0, 10),
        (30.0, 210.0, 12), (-170.0, -20.0, 10), (170.0, -40.0, 10), (90.0, 260.0, 14), (-110.0, 270.0, 12),
    ]
    land.vegetation("LAND_BEEF", terrain, rows, groves, hedges, root)
    land.perimeter_fence(
        "FENCE_BEEF_SITE", SITE_FENCE,
        [(-12.0, 9.0, -5.0, 11.0), (0.0, 9.0, 10.0, 11.0), (0.0, 83.0, 10.0, 85.0), (46.0, 11.0, 48.0, 19.0)],
        G, root,
    )
    land.power_line("POWER_LINE_BEEF", terrain, [(210.0, 140.0), (150.0, 110.0), (90.0, 90.0), (60.0, 62.0), (47.5, 57.5)], root)
    land.hills("HILLS_BEEF", [(-190.0, 330.0, 90.0, 26.0), (60.0, 380.0, 120.0, 30.0), (230.0, 300.0, 80.0, 22.0)], G - 0.5, M["hill"], root)


# --- cattle shed -------------------------------------------------------------------------------

def hay_bale(b, x, y, z, along="Y"):
    b.cylinder_along((x, y, z + 0.6), along, 0.6, 1.2, M["hay"], segments=10)


def shed_shell(tag, rect, parent, roofs, roof_name, index, front_gap=None):
    """Walls, weathered cladding, lifting roof and steel frame of a cattle shed. The low south
    wall leaves the cattle visible once the roof is off; `front_gap` is the x from which that
    wall is left open (the doorway to the loading lane)."""
    x0, y0, x1, y1 = rect
    tone, vents = SHED_LOOK[index]
    walls = MeshBuilder(recalc_normals=False)
    east_y0 = 23.0 if front_gap is not None else y0
    # Inner and top faces; the outer faces are the cladding's.
    walls.box((x0, y0, G), (x0 + 0.2, y1, G + 3), M["farm"], skip=("-z", "-x"))
    walls.box((x0, y1 - 0.2, G), (x1, y1, G + 3), M["farm"], skip=("-z", "+y"))
    walls.box((x1 - 0.2, east_y0, G), (x1, y1, G + 3), M["farm"], skip=("-z", "+x"))
    walls.box((x0, y0, G), (front_gap if front_gap is not None else x1, y0 + 0.2, G + 1), M["farm"], skip=("-z",))
    walls.build(tag + "_WALLS", parent=parent)
    cladding = MeshBuilder(recalc_normals=False)
    ribbed_wall(cladding, (x0, y1), (x0, y0), G, FARM_WALL_H, (-1, 0), seed=index * 11 + 1, tone=tone)
    ribbed_wall(cladding, (x1, y1), (x0, y1), G, FARM_WALL_H, (0, 1), seed=index * 11 + 2, tone=tone, pipes=False)
    ribbed_wall(cladding, (x1, east_y0), (x1, y1), G, FARM_WALL_H, (1, 0), seed=index * 11 + 3, tone=tone)
    cladding.build(tag + "_CLADDING", parent=parent)
    # Roof as its own object (lifted on reveal); the steel frame under it stays in place.
    props.shed_roof(roof_name, x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.3, G + 3.1, G + 3.25, FARM_RIDGE, M["farm_roof"], roofs,
                    seed=index * 37, tone=tone, vents=vents)
    props.house_structure(tag + "_FRAME", x0 + 0.2, x1 - 0.2, y0, y1, G, FARM_WALL_H, FARM_RIDGE + 0.1, parent, bays=5)


def farm(root, roofs, interior):
    x0, y0, x1, y1 = FARM
    farm = empty("BUILDING_BEEF_FARM", parent=root)
    box("BEEF_FARM_SLAB", (x0, y0, G - 0.1), (x1, y1, G + 0.05), M["farm_floor"], farm)
    shed_shell("BEEF_FARM", FARM, farm, roofs, "ROOF_BEEF_FARM", 1, front_gap=-9.5)

    # Bedding area: deep straw pack, scattered straw, concrete feed alley, feed barrier and trough.
    box("BEEF_STRAW_BED", (-17.4, 22, G + 0.06), (-7, 33.4, G + 0.12), M["straw"], interior)
    rng = _rng(22)
    straw = MeshBuilder(recalc_normals=False)
    for _ in range(320):
        x, y = rng.uniform(-17.2, -7.2), rng.uniform(22.2, 33.2)
        dx, w = rng.uniform(-0.18, 0.18), 0.012
        lp.quad(straw, ((x - w, y, G + 0.135), (x + w, y, G + 0.135), (x + dx + w, y + 0.21, G + 0.135), (x + dx - w, y + 0.21, G + 0.135)), M["feed"],
                tint=lp.scale(lp.WHITE, rng.uniform(0.75, 1.0)))
    straw.build("BEEF_STRAW_DETAIL", parent=interior)["ao_skip"] = True
    box("BEEF_FEED_ALLEY", (-7.0, 22.5, G + 0.05), (-4.2, 33.6, G + 0.09), props.M["base"], interior)
    rails("BEEF_FEED_BARRIER", (-6.7, 23), (-6.7, 33), interior)
    trough = MeshBuilder(recalc_normals=False)
    trough.box((-6.4, 23, G + 0.04), (-5.4, 33, G + 0.25), props.M["base"], skip=("-z",))
    # Feed along the trough: a low, uneven bank.
    rings = []
    for k in range(11):
        y = 23.2 + k * 0.96
        w, h = 0.36 + 0.07 * rng.uniform(-1, 1), 0.1 + 0.05 * rng.uniform(-1, 1)
        rings.append([Vector((-5.9 + w, y, G + 0.25)), Vector((-5.9 + 0.1 * rng.uniform(-1, 1), y, G + 0.25 + h)), Vector((-5.9 - w, y, G + 0.25))])
    coords = [p for ring in rings for p in ring]
    faces = [(k * 3 + s, (k + 1) * 3 + s, (k + 1) * 3 + s + 1, k * 3 + s + 1) for k in range(10) for s in range(2)]
    lp.add(trough, coords, faces, M["feed"], tint=[lp.scale(lp.WHITE, 0.82 + 0.18 * rng.random()) for _ in faces])
    trough.build("BEEF_FEED_TROUGH", parent=interior)
    drink = MeshBuilder()
    drink.box((-17.1, 20, G + 0.05), (-14.5, 21, G + 0.55), M["rail"])
    for x in (-17.0, -14.7):
        drink.box((x - 0.05, 20.05, G), (x + 0.05, 20.95, G + 0.05), M["rail"])
    drink.build("BEEF_WATER_TROUGH", parent=interior)
    box("BEEF_DRINKING_WATER", (-17, 20.1, G + 0.5), (-14.6, 20.9, G + 0.52), M["water"], interior)
    # Side and collecting lane rails, leaving a real loading exit at y=19.
    rails("BEEF_LANE_LEFT", (-9.4, 19), (-9.4, 22), interior)
    rails("BEEF_LANE_RIGHT", (-6.6, 19), (-6.6, 22), interior)

    animals = empty("ANIMALS_BEEF", parent=interior)
    cattle_group("CATTLE_BEEF_FARM", [(x, y, G + 0.13) for y in (24.5, 27.6, 30.7) for x in (-14.5, -10.6)], animals)
    # A row at the feed barrier, heads through the bars; the walkers' lane stays clear.
    feeding = empty("BEEF_FEEDING_ROW", parent=animals)
    crowd("BEEF_FEEDING_CROWD", [(-7.7, 25.2 + k * 1.1, G + 0.13, k + 2) for k in range(8)], feeding)
    resting = empty("BEEF_RESTING_CATTLE", parent=animals)
    for i, (x, y) in enumerate(((-16, 23), (-16, 28))):
        lying_cow("BEEF_RESTING_" + str(i), x, y, resting, HIDE[("brown", "cream")[i]])

    # Feed silos and bales outside, hay stack under a tarp, as around any cattle farm.
    props.silos("SILOS_BEEF", [(x0 - 4.0, y) for y in (23.0, 29.0)], x0, G, root)
    bales = MeshBuilder()
    for i, (x, y, z) in enumerate(((0.8, 36.0, 0), (2.2, 36.0, 0), (1.5, 36.0, 1.2), (0.8, 38.2, 0), (2.2, 38.2, 0))):
        hay_bale(bales, x - 3.0, y, G + z, "X")
    bales.build("BEEF_HAY_BALES", parent=root)
    tarp = MeshBuilder()
    tarp.box((-38.5, 22.0, G), (-30.5, 27.0, G + 2.0), M["hay"], skip=("-z",))
    tarp.gable((-38.7, 21.8, G + 2.0), (-30.3, 27.2, G + 2.2), 0.8, M["tarp"])
    tarp.build("BEEF_HAY_STORE", parent=root)


def crowd_shed(index, rect, root, roofs, animals):
    """Finishing shed with its roof in the lifting set: slatted concrete floor, a feed barrier
    and trough along the east side, and rows of cattle packed head to the barrier. Static and
    merged: it states the scale of a site, not a number of animals."""
    x0, y0, x1, y1 = rect
    tag = f"BEEF_SHED{index}"
    shed = empty(f"BUILDING_BEEF_FARM_{index}", parent=root)
    box(tag + "_SLAB", (x0, y0, G - 0.1), (x1, y1, G + 0.05), M["farm_floor"], shed)
    shed_shell(tag, rect, shed, roofs, f"ROOF_BEEF_FARM_{index}", index)
    # Slatted floor: dark gaps between concrete slats, running across the pen.
    slats = MeshBuilder(recalc_normals=False)
    gx0, gx1 = x0 + 0.4, x1 - 2.6
    y = y0 + 0.5
    while y < y1 - 0.6:
        lp.quad(slats, ((gx0, y, G + 0.062), (gx1, y, G + 0.062), (gx1, y + 0.07, G + 0.062), (gx0, y + 0.07, G + 0.062)), props.M["grill"])
        y += 0.42
    slats.build(tag + "_SLATS", parent=shed)["ao_skip"] = True
    # Feed barrier, alley and trough on the east side.
    bx = x1 - 2.4
    rails(tag + "_BARRIER", (bx, y0 + 0.6), (bx, y1 - 0.6), shed)
    box(tag + "_ALLEY", (bx + 0.3, y0 + 0.3, G + 0.05), (x1 - 0.3, y1 - 0.3, G + 0.09), props.M["base"], shed)
    trough = MeshBuilder().box((bx + 0.35, y0 + 0.6, G + 0.09), (bx + 1.25, y1 - 0.6, G + 0.3), props.M["base"], skip=("-z",))
    trough.build(tag + "_TROUGH", parent=shed)
    drink = MeshBuilder()
    for y in (y0 + 2.5, y1 - 2.5):
        drink.box((x0 + 0.5, y - 0.5, G + 0.05), (x0 + 2.5, y + 0.5, G + 0.55), M["rail"], skip=("-z",))
    drink.build(tag + "_WATER", parent=shed)
    # Cattle facing the barrier, four ranks deep, shoulder to shoulder; a few gaps keep it organic.
    rng = _rng(100 + index)
    cows = []
    for rank in range(4):
        x = bx - 1.45 - rank * 2.55
        y = y0 + 1.3
        while y < y1 - 1.2:
            if rng.random() > 0.07:
                cows.append((x + rng.uniform(-0.12, 0.12), y, G + 0.07, int(rng.random() * 6)))
            y += 1.05
    crowd(f"BEEF_CROWD_{index}", cows, animals)
    return shed


def _rng(seed):
    import random

    return random.Random(seed)


# --- ramps and trucks --------------------------------------------------------------------------

def ramp(name, x, y0, y1, root, z0=G + 0.03):
    """Rear ramp from the ground (z0) at y0 to the truck deck, 0.9 m above the road, at y1."""
    top = G + R + 0.9
    m = MeshBuilder(recalc_normals=False)
    m.quad(((x - 1.1, y0, z0), (x + 1.1, y0, z0), (x + 1.1, y1, top), (x - 1.1, y1, top)), M["rail"], facing=(0, 0, 1))
    for side in (-1, 1):
        xx = x + side * 1.08
        lp.tube(m, (xx, y0, z0 + 1.0), (xx, y1, top + 1.0), 0.04, M["rail"])
        for t in (0, 0.5, 1):
            zz = z0 + (top - z0) * t
            lp.tube(m, (xx, y0 + (y1 - y0) * t, zz), (xx, y0 + (y1 - y0) * t, zz + 1.0), 0.035, M["rail"])
    for i in range(1, 12):  # anti-slip cleats
        f = i / 12
        yy, zz = y0 + (y1 - y0) * f, z0 + (top - z0) * f + 0.012
        lp.quad(m, ((x - 1.05, yy - 0.02, zz), (x + 1.05, yy - 0.02, zz), (x + 1.05, yy + 0.02, zz + 0.012), (x - 1.05, yy + 0.02, zz + 0.012)), props.M["grill"])
    m.build(name, parent=root)


def truck(name, position, root, refrigerated=False):
    # Shared cab and wheels; the whole body drops so its deck top sits at 0.9m.
    cab = props.M["cab_delivery"] if refrigerated else props.M["cab_farm"]
    vehicle = props.truck(name, name + "_UNUSED_CARGO", lambda b, x, y, z: None, cab, position, root, slats=not refrigerated)
    unused = bpy.data.objects.get(name + "_UNUSED_CARGO")
    if unused:
        for child in list(unused.children):
            bpy.data.objects.remove(child, do_unlink=True)
        bpy.data.objects.remove(unused, do_unlink=True)
    bpy.data.objects[name + "_BODY"].location.z = -0.4
    m = MeshBuilder()
    if refrigerated:
        m.box((-1.2, -4.3, 0.9), (1.2, 2.1, 3.2), M["cold"], skip=("-z",))
        m.box((-0.6, 2.11, 2.35), (0.6, 2.45, 3.15), M["white"])  # refrigeration unit
        for x in (-0.4, -0.2, 0, 0.2, 0.4):
            m.box((x, 2.451, 2.48), (x + 0.07, 2.47, 3), M["rail"], skip=("-y",))
        for x in (-1.15, 0.03):  # rear pair of insulated doors, hinges and latches
            m.box((x, -4.34, 1), (x + 1.1, -4.3, 3.12), M["white"], skip=("+y",))
            m.box((x + 0.78, -4.39, 1.1), (x + 0.82, -4.34, 3.0), M["rail"], skip=("+y",))
        for z in (1.0, 3.1):  # side skirt and roof edge strips
            m.box((-1.22, -4.3, z - 0.04), (1.22, 2.1, z + 0.04), M["rail"])
        m.build(name + "_INSULATED_BODY", parent=vehicle)
    else:
        # Solid lower livestock panels and a rear gate, the slatted racks stay above.
        for x in (-1.2, 1.14):
            m.box((x - 0.01, -4.3, 0.9), (x + 0.07, 2.1, 1.35), props.M["deck"])
        m.box((-1.2, -4.32, 0.9), (1.2, -4.28, 1.5), props.M["deck"])
        m.build(name + "_GATE", parent=vehicle)
    return vehicle


# --- abattoir and processing -------------------------------------------------------------------

def crate_unit(b, x, y, z, colour, lid=None):
    """Stack of food-grade crates on a pallet (3 high)."""
    mat = props.M["load"]
    top = props.pallet(b, x, y, z)
    for k in range(3):
        lp.box_faces(b, (x + 0.03, y + 0.03, top + k * 0.28), (x + 0.97, y + 1.17, top + k * 0.28 + 0.26), mat, colour)
        lp.box_faces(b, (x + 0.2, y + 0.015, top + k * 0.28 + 0.08), (x + 0.8, y + 0.03, top + k * 0.28 + 0.2), mat, LABEL, skip=("+y", "-z", "+z", "-x", "+x"))
    if lid:
        lp.box_faces(b, (x + 0.08, y + 0.08, top + 0.84), (x + 0.92, y + 1.12, top + 0.88), mat, lid)


def tray_unit(b, x, y, z):
    """Stainless tray of cuts on a table: three stacked trays with product, label on the rim."""
    mat = props.M["load"]
    for k in range(3):
        zz = z + k * 0.12
        lp.box_faces(b, (x, y, zz), (x + 1.2, y + 0.6, zz + 0.1), mat, TRAY)
        lp.box_faces(b, (x + 0.05, y + 0.05, zz + 0.09), (x + 1.15, y + 0.55, zz + 0.115), mat, MEAT)
    lp.box_faces(b, (x + 0.5, y - 0.015, z + 0.05), (x + 0.8, y, z + 0.1), mat, LABEL, skip=("+y",))


def beef_carton_pallet(b, x, y, z):
    """Pallet of packed boxes, banded."""
    mat = props.M["load"]
    top = props.pallet(b, x, y, z)
    for k in range(4):
        lp.box_faces(b, (x + 0.02, y + 0.02, top + k * 0.25), (x + 0.98, y + 1.18, top + k * 0.25 + 0.24), mat, lp.scale(CARTON, 0.94 + 0.06 * (k % 2)))
    for bx in (x + 0.3, x + 0.65):
        lp.box_faces(b, (bx, y + 0.005, top), (bx + 0.05, y + 1.195, top + 1.0), mat, props.WRAP_BAND, skip=("-z", "-x", "+x"))


def rooftop_units(b, x0, y0, x1, y1, z, count=3):
    """Condensers and extract units on a flat roof."""
    step = (x1 - x0) / count
    for i in range(count):
        cx, cy = x0 + step * (i + 0.5), (y0 + y1) / 2
        b.box((cx - 0.9, cy - 0.7, z), (cx + 0.9, cy + 0.7, z + 0.9), props.M["fan_housing"], skip=("-z",))
        lp.quad(b, ((cx - 0.6, cy - 0.5, z + 0.91), (cx + 0.6, cy - 0.5, z + 0.91), (cx + 0.6, cy + 0.5, z + 0.91), (cx - 0.6, cy + 0.5, z + 0.91)), props.M["grill"])
        lp.tube(b, (cx + 0.3, cy + 1.0, z), (cx + 0.3, cy + 1.0, z + 1.2), 0.12, props.M["steel"], caps=True)


def plant(root, roofs, interior):
    plant = empty("ABATTOIR_BEEF", parent=root)
    box("BEEF_ABATTOIR_SLAB", (13, 30, G - 0.1), (31, 49, G + 0.03), M["farm_floor"], plant)
    # Lairage: open pens under a lifting roof, solid back wall, steel frame stays.
    back = MeshBuilder(recalc_normals=False)
    back.box((13, 42, G), (24, 42.2, G + 3), M["plant"], skip=("-z", "+y"))
    back.build("BEEF_WAITING_BACK", parent=plant)
    cladding = MeshBuilder(recalc_normals=False)
    ribbed_wall(cladding, (24, 42.2), (13, 42.2), G, 3.0, (0, 1), base=0.5, mat=M["plant"], seed=41, pipes=False)
    props.shed_roof("ROOF_BEEF_WAITING", 12.8, 24.2, 30.0, 42.4, G + 3.0, G + 3.2, 0.7, M["plant_roof"], roofs, seed=43, vents=0)
    frame = MeshBuilder()
    for x in (13.1, 15.5, 18.0, 20.5, 23.0, 23.9):
        for y in (30.15, 41.9):
            frame.box((x - 0.07, y - 0.07, G), (x + 0.07, y + 0.07, G + 3.0), props.M["steel"], skip=("-z", "+z"))
    for y in (30.15, 36.0, 41.9):
        frame.box((12.9, y - 0.06, G + 2.95), (24.1, y + 0.06, G + 3.08), props.M["steel"])
    frame.build("BEEF_WAITING_FRAME", parent=plant)
    for n, a, b in (("W", (13, 30), (13, 42)), ("E_S", (23, 30), (23, 31)), ("E_N", (23, 35), (23, 42)), ("N", (13, 41.5), (23, 41.5))):
        rails("BEEF_WAITING_RAIL_" + n, a, b, interior)
    rails("BEEF_WAITING_DIVIDER", (13, 41), (18, 41), interior)
    pen = MeshBuilder()
    pen.box((13.3, 39, G), (15.3, 40, G + 0.5), M["rail"], skip=("-z",))
    pen.box((13.4, 39.1, G + 0.48), (15.2, 39.9, G + 0.5), M["water"], skip=("-z",))
    pen.box((17.0, 41.2, G + 0.9), (20.0, 41.4, G + 1.1), props.M["steel"])  # hay rack
    pen.build("BEEF_WAITING_WATER", parent=interior)
    # Drain channel across the lairage floor.
    box("BEEF_WAITING_DRAIN", (13.1, 34.4, G + 0.03), (22.9, 34.6, G + 0.045), props.M["grill"], interior)
    cattle_group("CATTLE_BEEF_WAITING", [(x, y, G + 0.05) for y in (33, 36, 39) for x in (15.6, 20.8)], interior)
    # Offset approach corridor enters an opaque building; no machinery or carcasses.
    for n, a, b in (("A", (23.5, 35), (23.5, 43)), ("B", (25.5, 35), (25.5, 42.7))):
        rails("BEEF_APPROACH_RAIL_" + n, a, b, interior)
    opaque = empty("BEEF_KILLING_OPAQUE", parent=plant)
    # Inner and top faces of the walls; the clad faces (east, north, front) come with the cladding.
    enclosure = MeshBuilder(recalc_normals=False)
    for a, b, hidden in (
        ((23.2, 42.1, G), (23.4, 49, G + 4), ()), ((30.8, 42.1, G), (31, 49, G + 4), ("+x",)), ((23.2, 48.8, G), (31, 49, G + 4), ("+y",)),
        ((23.2, 42.1, G), (23.5, 42.3, G + 4), ()), ((25.5, 42.1, G), (31, 42.3, G + 4), ("-y",)), ((23.5, 42.1, G + 2.5), (25.5, 42.3, G + 4), ()),
        ((23.4, 44, G), (25.7, 44.2, G + 4), ()),
    ):
        enclosure.box(a, b, M["plant"], skip=("-z", *hidden) if a[2] == G else hidden)
    enclosure.build("BEEF_KILLING_ENCLOSURE", parent=opaque)
    roof = MeshBuilder(recalc_normals=False)
    lp.panel(roof, (23.1, 42.0, G + 4.2), (8.0, 0.0, 0.0), (0.0, 7.1, 0.0), (4, 3), M["plant_flat"],
             lambda s, t: lp.scale(lp.WHITE, 0.82 + 0.18 * lp.rand(int(s * 4), int(t * 3), 7)))
    for lo, hi in (((23.0, 41.9), (31.2, 42.05)), ((23.0, 49.05), (31.2, 49.2)), ((23.0, 41.9), (23.15, 49.2)), ((31.05, 41.9), (31.2, 49.2))):
        roof.box((lo[0], lo[1], G + 4.0), (hi[0], hi[1], G + 4.55), props.M["trim"], skip=("-z",))  # parapet
    rooftop_units(roof, 24.0, 43.0, 30.5, 48.5, G + 4.2, 3)
    roof.build("BEEF_KILLING_ROOF", parent=opaque)
    ribbed_wall(cladding, (31, 42.1), (31, 49), G, 4.0, (1, 0), base=0.8, mat=M["plant"], seed=51)
    ribbed_wall(cladding, (31, 49), (23.2, 49), G, 4.0, (0, 1), base=0.8, mat=M["plant"], seed=53, pipes=False)
    ribbed_wall(cladding, (31, 42.1), (25.5, 42.1), G, 4.0, (0, -1), base=0.8, mat=M["plant"], seed=55, pipes=False)
    cladding.build("BEEF_ABATTOIR_CLADDING", parent=plant)
    entry = MeshBuilder()  # door frame, light and hazard strip at the animal entrance
    entry.box((23.45, 41.95, G), (23.6, 42.1, G + 2.5), props.M["steel"], skip=("-z",))
    entry.box((25.35, 41.95, G), (25.5, 42.1, G + 2.5), props.M["steel"], skip=("-z",))
    entry.box((24.0, 41.95, G + 2.3), (25.0, 42.0, G + 2.4), props.M["lamp"])
    entry.build("BEEF_KILLING_ENTRY", parent=opaque)
    # Condenser bank and pipe run on the east wall, a stack on the roof.
    plantside = MeshBuilder(recalc_normals=False)
    for i in range(3):
        y = 43.0 + i * 2.0
        plantside.box((31.0, y, G), (32.2, y + 1.4, G + 1.6), props.M["fan_housing"], skip=("-z", "-x"))
        lp.quad(plantside, ((32.21, y + 0.2, G + 0.3), (32.21, y + 1.2, G + 0.3), (32.21, y + 1.2, G + 1.4), (32.21, y + 0.2, G + 1.4)), props.M["grill"])
    lp.tube(plantside, (31.12, 42.5, G + 3.4), (31.12, 49.5, G + 3.4), 0.08, props.M["steel"])
    lp.tube(plantside, (29.5, 48.2, G + 4.2), (29.5, 48.2, G + 6.6), 0.3, props.M["steel"], sides=8, caps=True)
    plantside.build("BEEF_KILLING_DETAILS", parent=opaque)
    cattle_group("CATTLE_BEEF_APPROACH", [(27 + (i % 3) * 1.2, 45.5 + (i // 3) * 1.6, G + 0.05) for i in range(6)], interior)

    # Three separate sanitary rooms, closed boxes with the roof omitted. Their insulated panels
    # (joints, micro-ribs) come from the `panel` texture.
    for name, x0, x1, y0, y1, col in (("COLD_ROOM_BEEF", 33, 41, 38, 47, "cold"), ("CUTTING_BEEF", 33, 41, 28, 36, "plant"), ("PACKING_BEEF", 33, 41, 19, 26, "white")):
        room = empty(name, parent=root)
        box(name + "_FLOOR", (x0, y0, G), (x1, y1, G + 0.08), props.M["base"], room)
        shell = MeshBuilder()
        shell.box((x0, y1 - 0.15, G), (x1, y1, G + 2.2), M[col], skip=("-z",))
        shell.box((x1 - 0.15, y0, G), (x1, y1, G + 2.2), M[col], skip=("-z",))
        shell.box((x0, y0, G), (x0 + 0.15, y1, G + 2.2), M[col], skip=("-z",))
        shell.box((x0, y0, G), (x1, y0 + 0.15, G + 0.9), M[col], skip=("-z",))  # low front wall: the room stays readable
        shell.box((x0 + 0.3, y1 - 0.2, G + 1.9), (x1 - 0.3, y1 - 0.15, G + 1.98), props.M["lamp"], skip=("+y",))  # light strip
        shell.build(name + "_SHELL", parent=room)
        # Refrigeration unit and roller door seen from outside, on the east wall.
        outside = MeshBuilder(recalc_normals=False)
        outside.box((x1, y0 + 2.0, G + 0.1), (x1 + 0.9, y0 + 3.6, G + 1.5), props.M["fan_housing"], skip=("-x",))
        lp.quad(outside, ((x1 + 0.91, y0 + 2.2, G + 0.3), (x1 + 0.91, y0 + 3.4, G + 0.3), (x1 + 0.91, y0 + 3.4, G + 1.3), (x1 + 0.91, y0 + 2.2, G + 1.3)), props.M["grill"])
        outside.box((x1, y0 + 4.5, G), (x1 + 0.05, y0 + 7.0, G + 2.3), props.M["door"], skip=("-x", "-z"))
        for k in range(5):
            outside.box((x1 + 0.05, y0 + 4.5, G + 0.2 + k * 0.44), (x1 + 0.08, y0 + 7.0, G + 0.26 + k * 0.44), props.M["door_rib"], skip=("-x",))
        props.downpipe(outside, x1 + 0.1, y1 - 0.3, G, G + 2.2)
        outside.build(name + "_OUTSIDE", parent=room)

    cold = MeshBuilder()  # steel racking along the back wall of the cold room
    for x in (33.4, 37.0):
        for px in (x, x + 3.2):
            cold.box((px, 46.3, G + 0.08), (px + 0.06, 46.4, G + 2.0), props.M["steel"], skip=("-z",))
        for z in (0.6, 1.2, 1.8):
            cold.box((x, 46.3, G + z), (x + 3.26, 46.7, G + z + 0.04), props.M["steel"])
    cold.build("COLD_ROOM_BEEF_RACKS", parent=bpy.data.objects["COLD_ROOM_BEEF"])
    cutting = MeshBuilder()
    for y in (29.0, 31.0, 33.0):
        cutting.box((34.0, y, G + 0.7), (39.0, y + 0.8, G + 0.78), props.M["hub"])
        cutting.box((34.05, y + 0.05, G + 0.4), (38.95, y + 0.75, G + 0.43), props.M["hub"])
        for lx in (34.1, 38.84):
            for ly in (y + 0.06, y + 0.68):
                cutting.box((lx, ly, G + 0.08), (lx + 0.06, ly + 0.06, G + 0.7), props.M["hub"], skip=("-z", "+z"))
    cutting.build("CUTTING_BEEF_TABLES", parent=bpy.data.objects["CUTTING_BEEF"])
    packing = MeshBuilder()
    packing.box((33.4, 25.0, G + 0.7), (40.6, 25.8, G + 0.78), props.M["hub"])  # bench along the back wall
    for lx in range(7):
        packing.box((33.5 + lx * 1.1, 25.05, G + 0.08), (33.56 + lx * 1.1, 25.11, G + 0.7), props.M["hub"], skip=("-z", "+z"))
    packing.build("PACKING_BEEF_BENCH", parent=bpy.data.objects["PACKING_BEEF"])

    for group, origin, unit, step in (
        ("MEAT_BEEF_CHILLED", (34.2, 38.8, G + 0.08), lambda b, x, y, z: crate_unit(b, x, y, z, TRAY, MEAT), (1.7, 1.7)),
        ("MEAT_BEEF_CUT", (34.1, 29.1, G + 0.78), tray_unit, (1.7, 2.0)),
        ("CARTONS_BEEF_PACKED", (34.2, 20.0, G + 0.08), beef_carton_pallet, (1.7, 1.7)),
    ):
        props.unit_group(group, origin, [(i % 3, i // 3) for i in range(6)], unit, root, step=step)


def paths(root):
    # Heights: G + R on the roads, G + R + 0.9 on the truck decks, the slabs' own level elsewhere.
    points = {
        "PATH_BEEF_LOAD": [(-8, 23.5, G + 0.13), (-8, 18.8, G + R), (-11, 17.5, G + R), (-11, 2.7, G + R), (-8, 2.7, G + R), (-8, 5.7, G + R + 0.9), (-8, 6.5, G + R + 0.9)],
        "PATH_BEEF_ANIMALS": [(-8, 10, G + R), (-8, 12.5, G + R), (7, 12.5, G + R), (7, 22, G + R), (18, 22, G + R), (18, 28, G + R)],
        "PATH_BEEF_UNLOAD": [(18, 23.7, G + R + 0.9), (18, 20.7, G + 0.03), (15, 25, G + R), (15, 33.5, G + 0.05), (18, 33.5, G + 0.05)],
        "PATH_BEEF_APPROACH": [(21.5, 32, G + 0.05), (24.5, 34, G + 0.05), (24.5, 43.4, G + 0.05), (26.8, 43.4, G + 0.05), (27, 45, G + 0.05)],
        "PATH_BEEF_DELIVERY": [(37, 15, G + R), (18, 15, G + R), (8, 15, G + R), (8, 9, G + R)],
    }
    for name, coords in points.items():
        for i, p in enumerate(coords):
            empty(name + "_" + str(i).zfill(2), p, root)


def main():
    reset_scene()
    mats()
    root = empty("TERRACE_BEEF_ROOT")
    terrace(root)
    landscape(root)
    roofs = empty("ROOF_BEEF", parent=root)
    interior = empty("INTERIOR_BEEF", parent=root)
    farm(root, roofs, interior)
    plant(root, roofs, interior)
    animals = bpy.data.objects["ANIMALS_BEEF"]
    for i, rect in enumerate(CROWD_SHEDS, start=2):
        crowd_shed(i, rect, root, roofs, animals)
    empty("ANCHOR_BEEF_WIDE", (-10, 52, G + 1), root)
    empty("ANCHOR_BEEF_MARK_CROWD", (-10, 48.5, G + 3.4), root)
    empty("ANCHOR_BEEF_MARK_SITE", (-10, 70.5, G + 4.4), root)
    livestock = truck("TRUCK_BEEF_ANIMALS", (-8, 10, G + R), root)
    # Two abreast, three rows, enough head clearance and a correct 0.9m deck.
    cattle_group("CATTLE_BEEF_TRUCK", [(x, y, 0.9) for y in (-3.35, -1.35, 0.65) for x in (-0.56, 0.56)], livestock)
    ramp("BEEF_LOADING_RAMP", -8, 2.7, 5.7, root, z0=G + R)
    ramp("BEEF_UNLOADING_RAMP", 18, 20.7, 23.7, root)
    delivery = truck("TRUCK_BEEF_DELIVERY", (37, 15, G + R), root, True)
    cargo = empty("CARGO_BEEF_DELIVERY", parent=delivery)
    for i in range(6):
        x, y = -1 + (i % 2) * 1.05, -4 + (i // 2) * 1.8
        b = MeshBuilder(recalc_normals=False)
        beef_carton_pallet(b, x, y, 0.9)
        b.build("BEEF_DELIVERY_CARTON_" + str(i), parent=cargo)
    paths(root)
    # Anchors for documentary panels, all visible from the terrace.
    for name, p in (("FARM", (-10, 24, G + 3)), ("TRANSPORT", (3, 21, G + 2)), ("ABATTOIR", (22, 36, G + 3)), ("COLD_ROOM", (36, 42, G + 2)), ("CUTTING", (36, 32, G + 2)), ("PACKING", (36, 23, G + 2))):
        empty("ANCHOR_BEEF_" + name, p, root)
    argv = sys.argv[sys.argv.index("--") + 1 :]
    save_blend(os.path.abspath(argv[0]))


if __name__ == "__main__":
    main()
