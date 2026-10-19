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
import terrace_props as props
from common import MeshBuilder, bevel, box, empty, helper_volume, material, reset_scene, save_blend

G = -12.0
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
        "tag": ("M_BEEF_EAR_TAG", "#E0BC50", 0.6, 0),
        "muzzle": ("M_BEEF_MUZZLE", "#6B5A50", 0.9, 0),
        "hoof": ("M_BEEF_HOOF", "#423F3A", 0.8, 0),
        "eye": ("M_BEEF_EYE", "#282924", 0.3, 0),
        "white": ("M_BEEF_PANEL", "#E5E5D9", 0.6, 0),
        "cold": ("M_BEEF_COLD_PANEL", "#D9E5E3", 0.5, 0),
        "tray": ("M_BEEF_TRAY", "#E8E4D8", 0.5, 0),
        "meat": ("M_BEEF_MEAT", "#98594F", 0.55, 0),
        "carton": ("M_BEEF_CARTON", "#BEA784", 0.9, 0),
        "label": ("M_BEEF_LABEL", "#C9D3D6", 0.6, 0),
        "blue": ("M_BEEF_REEFER", "#78969B", 0.5, 0.1),
        "tarp": ("M_BEEF_TARP", "#4F5A52", 0.9, 0),
    }.items():
        M[key] = material(name, color, roughness=rough, metallic=metal)
    for key, color in {"cream": "#D8C8A4", "tan": "#BA9873", "brown": "#8D6952", "blond": "#B88556"}.items():
        M["hide_" + key] = material("M_BEEF_HIDE_" + key.upper(), color, roughness=0.95)
    props.materials()
    land.materials()


# --- pens, gates, rails ------------------------------------------------------------------------

def rails(name, a, b, parent, z=G, height=1.5):
    """Tubular pen fence: round posts every 2 m, horizontal rails, post caps."""
    x0, y0 = a
    x1, y1 = b
    length = math.hypot(x1 - x0, y1 - y0)
    count = max(1, math.ceil(length / 2))
    low = height < 1.1
    m = MeshBuilder()
    for i in range(count + 1):
        f = i / count
        x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        m.cylinder((x, y, z), 0.025 if low else 0.045, height, M["rail"], segments=8)
        m.sphere((x, y, z + height), 0.03 if low else 0.055, M["rail"])
    for h in (0.3, 0.7, 1.02) if low else (0.45, 0.95, 1.4):
        r = 0.018 if low else 0.035
        m.limb((x0, y0, z + h), (x1, y1, z + h), r, r, M["rail"], segments=8)
    m.build(name, parent=parent)


def ribbed_wall(name, a, b, z0, height, normal, parent, base=0.6):
    """Concrete base course and vertical cladding ribs along the wall a→b, on its `normal` side."""
    (x0, y0), (x1, y1) = a, b
    length = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    nx, ny = normal
    c = MeshBuilder()

    def slab(t0, t1, d0, d1, za, zb, mat):
        pts = [(x0 + ux * t + nx * d, y0 + uy * t + ny * d) for t, d in ((t0, d0), (t1, d0), (t1, d1), (t0, d1))]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        c.box((min(xs), min(ys), za), (max(xs), max(ys), zb), mat)

    slab(0, length, 0, 0.08, z0, z0 + base, props.M["base"])
    t = 0.5
    while t < length - 0.3:
        slab(t - 0.03, t + 0.03, 0, 0.05, z0 + base, z0 + height - 0.05, props.M["rib"])
        t += 1.0
    c.build(name, parent=parent)


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


def cow_body(m, hide, fine=True):
    """Body, neck, head, ears, tags and tail of a standing, polled beef steer, facing local +Y.
    `m` is a MeshBuilder or an Xf. `fine=False` halves the facets for the merged crowd."""
    seg = 14 if fine else 9
    m.loft([
        ((0, -0.98, 1.28), 0.14, 0.18), ((0, -0.86, 1.29), 0.27, 0.33), ((0, -0.55, 1.22), 0.37, 0.45),
        ((0, -0.15, 1.16), 0.40, 0.50), ((0, 0.25, 1.17), 0.39, 0.50), ((0, 0.5, 1.22), 0.33, 0.46),
        ((0, 0.68, 1.30), 0.22, 0.34),
    ], hide, segments=seg)
    m.loft([
        ((0, 0.60, 1.30), 0.22, 0.34), ((0, 0.82, 1.32), 0.17, 0.28), ((0, 0.98, 1.26), 0.155, 0.24),
        ((0, 1.10, 1.13), 0.14, 0.19), ((0, 1.22, 1.03), 0.125, 0.15), ((0, 1.31, 0.97), 0.115, 0.12),
        ((0, 1.35, 0.96), 0.10, 0.10),
    ], hide, segments=seg - 4)
    m.ellipsoid((0, 1.33, 0.955), (0.105, 0.075, 0.085), M["muzzle"], u=8, v=5)
    for side in (-1, 1):
        m.ellipsoid((side * 0.24, 0.97, 1.33), (0.15, 0.05, 0.045), hide, u=6, v=4)  # ear
        m.box((side * 0.31 - 0.03, 0.93, 1.2), (side * 0.31 + 0.03, 0.955, 1.3), M["tag"])
        if fine:
            m.ellipsoid((side * 0.135, 1.09, 1.18), (0.022, 0.03, 0.026), M["eye"], u=6, v=4)
            m.ellipsoid((side * 0.05, 1.395, 0.975), (0.03, 0.012, 0.02), M["hoof"], u=6, v=4)  # nostril
    if fine:
        m.ellipsoid((0, 0.62, 0.9), (0.1, 0.19, 0.2), hide, u=8, v=6)  # dewlap
    m.limb((0, -0.97, 1.36), (0.04, -1.06, 0.62), 0.032, 0.015, hide, segments=6)  # tail


def cow_leg(m, rear, hide, fine=True):
    """One leg from the hip joint (local origin) down to the hoof, 1 m below."""
    seg = 8 if fine else 6
    m.loft([
        ((0, 0.0, 0.05), 0.12 if rear else 0.10, 0.17 if rear else 0.14),
        ((0, -0.04 if rear else 0.0, -0.25), 0.10 if rear else 0.085, 0.13 if rear else 0.10),
        ((0, -0.10 if rear else 0.02, -0.5), 0.055, 0.07),
        ((0, -0.03, -0.78), 0.04, 0.045),
        ((0, 0.0, -0.9), 0.047, 0.05),
    ], hide, segments=seg, caps=False)
    m.loft([((0, 0.0, -0.9), 0.05, 0.055), ((0, 0.03, -1.0), 0.052, 0.085)], M["hoof"], segments=seg)


LEGS = ((-0.25, -0.58), (0.25, -0.58), (-0.25, 0.48), (0.25, 0.48))


def animal(name, position, parent, variation=0):
    """Ground-centred independent root, top-jointed legs, facing local +Y (schematic standing
    steer, see cow_body). Legs are separate joints so the walk can swing them."""
    root = empty(name, position, parent)
    root["animalIndex"] = variation
    hide = M["hide_" + HIDES[variation % len(HIDES)]]
    body = MeshBuilder()
    cow_body(body, hide)
    body.build(name + "_BODY", parent=root)
    for j, (x, y) in enumerate(LEGS):
        leg = empty("CATTLE_LEG_" + name + "_" + str(j), (x, y, 1.0), root)
        limb = MeshBuilder()
        cow_leg(limb, y < 0, hide)
        limb.build(name + "_LIMB_" + str(j), parent=leg)
    return root


def crowd(name, cows, parent):
    """Many static cattle merged into one mesh (a handful of draw calls for dozens of animals).
    `cows`: (x, y, z, hide index) in the parent's frame, all facing +X."""
    m = MeshBuilder()
    for x, y, z, k in cows:
        hide = M["hide_" + HIDES[k % len(HIDES)]]
        frame = Xf(m, (x, y, z), True)
        cow_body(frame, hide, fine=False)
        for lx, ly in LEGS:
            cow_leg(Xf(m, frame.p((lx, ly, 1.0)), True), ly < 0, hide, fine=False)
    return m.build(name, parent=parent)


def cattle_group(name, positions, parent):
    group = empty(name, parent=parent)
    for i, p in enumerate(positions):
        animal(name + "_" + str(i + 1).zfill(2), p, group, i)
    return group


def lying_cow(name, x, y, parent, hide):
    """Resting individual, legs folded under the body, head up (not on the timeline)."""
    m = MeshBuilder()
    m.loft([
        ((x, y - 0.85, 0.5), 0.16, 0.2), ((x, y - 0.6, 0.52), 0.38, 0.34), ((x, y - 0.1, 0.5), 0.45, 0.4),
        ((x, y + 0.4, 0.52), 0.43, 0.4), ((x, y + 0.75, 0.62), 0.3, 0.34),
    ], hide, segments=12)
    m.loft([
        ((x, y + 0.7, 0.82), 0.2, 0.28), ((x, y + 0.95, 0.98), 0.16, 0.22), ((x, y + 1.12, 0.9), 0.13, 0.17),
        ((x, y + 1.3, 0.78), 0.105, 0.11),
    ], hide, segments=9)
    m.ellipsoid((x, y + 1.3, 0.76), (0.1, 0.07, 0.08), M["muzzle"], u=8, v=5)
    for side in (-1, 1):
        m.ellipsoid((x + side * 0.23, y + 0.9, 1.13), (0.14, 0.05, 0.04), hide, u=8, v=5)
        m.ellipsoid((x + side * 0.38, y - 0.45, 0.17), (0.09, 0.3, 0.1), hide, u=8, v=5)
        m.ellipsoid((x + side * 0.3, y + 0.55, 0.13), (0.07, 0.22, 0.08), hide, u=8, v=5)
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
    flat = [
        (-42.0, 14.0, 0.0, 82.0), (10.0, 22.0, 46.0, 52.0), (30.0, 17.0, 44.0, 50.0),
        (STORE_X0, STORE_BACK_Y, STORE_X1, TERRACE_DEPTH), (-14.0, 0.0, -3.0, 20.0),
    ]
    flat += [(x0 - 2.5, y0 - 2.5, x1 + 2.5, y1 + 2.5) for x0, y0, x1, y1 in road_rects]
    terrain = land.Terrain(G, flat, PLATEAU, PLATEAU_Z)
    terrain.build("TERRAIN_BEEF", (-250.0, -100.0, 250.0, 400.0), 5.0, (45.0, 55.0), root)
    land.roads("ROAD_BEEF", ROADS, G, M["road"], root)

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

    hedges = [h for h in hedges if not crosses_road(h)]
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
    hills = MeshBuilder()
    for x, y, rad, h in ((-190.0, 330.0, 90.0, 26.0), (60.0, 380.0, 120.0, 30.0), (230.0, 300.0, 80.0, 22.0)):
        hills.cone((x, y, G - 0.5), rad, h, M["hill"], segments=24)
    hills.build("HILLS_BEEF", parent=root)


# --- cattle shed -------------------------------------------------------------------------------

def hay_bale(b, x, y, z, along="Y"):
    b.cylinder_along((x, y, z + 0.6), along, 0.6, 1.2, M["hay"], segments=14)


def farm(root, roofs, interior):
    x0, y0, x1, y1 = FARM
    farm = empty("BUILDING_BEEF_FARM", parent=root)
    box("BEEF_FARM_SLAB", (x0, y0, G - 0.1), (x1, y1, G + 0.05), M["farm_floor"], farm)
    # Low front wall leaves cattle visible after roof reveal; side doorway to loading lane.
    walls = MeshBuilder()
    for a, b in (((x0, y0, G), (x0 + 0.2, y1, G + 3)), ((x0, y1 - 0.2, G), (x1, y1, G + 3)),
                 ((x1 - 0.2, 23, G), (x1, y1, G + 3)), ((x0, y0, G), (-9.5, y0 + 0.2, G + 1))):
        walls.box(a, b, M["farm"])
    bevel(walls.build("BEEF_FARM_WALLS", parent=farm), 0.02)
    ribbed_wall("BEEF_FARM_CLADDING_W", (x0, y1), (x0, y0), G, FARM_WALL_H, (-1, 0), farm)
    ribbed_wall("BEEF_FARM_CLADDING_N", (x1, y1), (x0, y1), G, FARM_WALL_H, (0, 1), farm)
    ribbed_wall("BEEF_FARM_CLADDING_E", (x1, 23), (x1, y1), G, FARM_WALL_H, (1, 0), farm)
    # Roof as its own object (lifted on reveal); the steel frame under it stays in place.
    MeshBuilder().gable((x0 - 0.3, y0 - 0.3, G + 3.1), (x1 + 0.3, y1 + 0.3, G + 3.25), FARM_RIDGE, M["farm_roof"]).build(
        "ROOF_BEEF_FARM", parent=roofs)["ao_skip"] = True
    props.house_structure("BEEF_FARM_FRAME", x0 + 0.2, x1 - 0.2, y0, y1, G, FARM_WALL_H, FARM_RIDGE + 0.1, farm, bays=5)

    # Bedding area: deep straw pack, scattered straw, concrete feed alley, feed barrier and trough.
    box("BEEF_STRAW_BED", (-17.4, 22, G + 0.06), (-7, 33.4, G + 0.12), M["straw"], interior)
    rng = _rng(22)
    straw = MeshBuilder()
    for _ in range(320):
        x, y = rng.uniform(-17.2, -7.2), rng.uniform(22.2, 33.2)
        straw.limb((x, y, G + 0.13), (x + rng.uniform(-0.18, 0.18), y + 0.21, G + 0.13), 0.009, 0.009, M["feed"], segments=4)
    straw.build("BEEF_STRAW_DETAIL", parent=interior)
    box("BEEF_FEED_ALLEY", (-7.0, 22.5, G + 0.05), (-4.2, 33.6, G + 0.09), props.M["base"], interior)
    rails("BEEF_FEED_BARRIER", (-6.7, 23), (-6.7, 33), interior)
    trough = MeshBuilder()
    trough.box((-6.4, 23, G + 0.04), (-5.4, 33, G + 0.25), props.M["base"])
    for k in range(9):  # feed heaped in the trough
        y = 23.5 + k * 1.05
        trough.ellipsoid((-5.9, y, G + 0.27), (0.4, 0.45, 0.1), M["feed"], u=8, v=4)
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
        lying_cow("BEEF_RESTING_" + str(i), x, y, resting, M["hide_" + ("brown", "cream")[i]])

    # Feed silos and bales outside, hay stack under a tarp, as around any cattle farm.
    silos = MeshBuilder()
    sx = x0 - 4.0
    sys_ = (23.0, 29.0)
    for y in sys_:
        silos.cylinder((sx, y, G + 1.2), 1.6, 6.5, M["silo"], segments=18)
        silos.cone((sx, y, G + 7.7), 1.65, 1.4, M["silo"], segments=18)
        for lx, ly in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            silos.box((sx + lx - 0.08, y + ly - 0.08, G), (sx + lx + 0.08, y + ly + 0.08, G + 1.3), props.M["chassis"])
    bevel(silos.build("SILOS_BEEF", parent=root), 0.02)
    props.silo_details("SILOS_BEEF_DETAILS", [(sx, y) for y in sys_], x0, G, root)
    bales = MeshBuilder()
    for i, (x, y, z) in enumerate(((0.8, 36.0, 0), (2.2, 36.0, 0), (1.5, 36.0, 1.2), (0.8, 38.2, 0), (2.2, 38.2, 0))):
        hay_bale(bales, x - 3.0, y, G + z, "X")
    bales.build("BEEF_HAY_BALES", parent=root)
    tarp = MeshBuilder()
    tarp.box((-38.5, 22.0, G), (-30.5, 27.0, G + 2.0), M["hay"])
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
    walls = MeshBuilder()
    for a, b in (((x0, y0, G), (x0 + 0.2, y1, G + 3)), ((x0, y1 - 0.2, G), (x1, y1, G + 3)),
                 ((x1 - 0.2, y0, G), (x1, y1, G + 3)), ((x0, y0, G), (x1, y0 + 0.2, G + 1))):
        walls.box(a, b, M["farm"])
    bevel(walls.build(tag + "_WALLS", parent=shed), 0.02)
    ribbed_wall(tag + "_CLADDING_W", (x0, y1), (x0, y0), G, FARM_WALL_H, (-1, 0), shed)
    ribbed_wall(tag + "_CLADDING_N", (x1, y1), (x0, y1), G, FARM_WALL_H, (0, 1), shed)
    ribbed_wall(tag + "_CLADDING_E", (x1, y0), (x1, y1), G, FARM_WALL_H, (1, 0), shed)
    MeshBuilder().gable((x0 - 0.3, y0 - 0.3, G + 3.1), (x1 + 0.3, y1 + 0.3, G + 3.25), FARM_RIDGE, M["farm_roof"]).build(
        f"ROOF_BEEF_FARM_{index}", parent=roofs)["ao_skip"] = True
    props.house_structure(tag + "_FRAME", x0 + 0.2, x1 - 0.2, y0, y1, G, FARM_WALL_H, FARM_RIDGE + 0.1, shed, bays=5)
    # Slatted floor: dark gaps between concrete slats, running across the pen.
    slats = MeshBuilder()
    gx0, gx1 = x0 + 0.4, x1 - 2.6
    y = y0 + 0.5
    while y < y1 - 0.6:
        slats.box((gx0, y, G + 0.05), (gx1, y + 0.07, G + 0.062), props.M["grill"])
        y += 0.42
    slats.build(tag + "_SLATS", parent=shed)["ao_skip"] = True
    # Feed barrier, alley and trough on the east side.
    bx = x1 - 2.4
    rails(tag + "_BARRIER", (bx, y0 + 0.6), (bx, y1 - 0.6), shed)
    box(tag + "_ALLEY", (bx + 0.3, y0 + 0.3, G + 0.05), (x1 - 0.3, y1 - 0.3, G + 0.09), props.M["base"], shed)
    trough = MeshBuilder().box((bx + 0.35, y0 + 0.6, G + 0.09), (bx + 1.25, y1 - 0.6, G + 0.3), props.M["base"])
    trough.build(tag + "_TROUGH", parent=shed)
    drink = MeshBuilder()
    for y in (y0 + 2.5, y1 - 2.5):
        drink.box((x0 + 0.5, y - 0.5, G + 0.05), (x0 + 2.5, y + 0.5, G + 0.55), M["rail"])
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

def ramp(name, x, y0, y1, root):
    """Rear ramp from ground at y0 to 0.9m truck deck at y1."""
    m = MeshBuilder()
    m.quad(((x - 1.1, y0, G + 0.03), (x + 1.1, y0, G + 0.03), (x + 1.1, y1, G + 0.9), (x - 1.1, y1, G + 0.9)), M["rail"])
    for side in (-1, 1):
        xx = x + side * 1.08
        m.limb((xx, y0, G + 1), (xx, y1, G + 1.9), 0.04, 0.04, M["rail"])
        for t in (0, 0.5, 1):
            m.cylinder((xx, y0 + (y1 - y0) * t, G + 0.9 * t), 0.035, 1, M["rail"], segments=6)
    for i in range(12):
        f = i / 12
        yy, zz = y0 + (y1 - y0) * f, G + 0.9 * f + 0.04
        m.limb((x - 1.05, yy, zz), (x + 1.05, yy, zz), 0.014, 0.014, M["hoof"], segments=6)
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
        m.box((-1.2, -4.3, 0.9), (1.2, 2.1, 3.2), M["cold"])
        m.box((-0.6, 2.11, 2.35), (0.6, 2.45, 3.15), M["white"])  # refrigeration unit
        for x in (-0.4, -0.2, 0, 0.2, 0.4):
            m.box((x, 2.451, 2.48), (x + 0.07, 2.47, 3), M["rail"])
        for x in (-1.15, 0.03):  # rear pair of insulated doors, hinges and latches
            m.box((x, -4.34, 1), (x + 1.1, -4.3, 3.12), M["white"])
            m.cylinder((x + 0.8, -4.37, 1.1), 0.025, 1.9, M["rail"], segments=8)
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

def crate_unit(b, x, y, z, mat, lid=None):
    """Stack of food-grade crates on a pallet (3 high)."""
    top = props.pallet(b, x, y, z)
    for k in range(3):
        b.box((x + 0.03, y + 0.03, top + k * 0.28), (x + 0.97, y + 1.17, top + k * 0.28 + 0.26), mat)
        b.box((x + 0.2, y + 0.025, top + k * 0.28 + 0.08), (x + 0.8, y + 0.03, top + k * 0.28 + 0.2), M["label"])
    if lid:
        b.box((x + 0.08, y + 0.08, top + 0.84), (x + 0.92, y + 1.12, top + 0.88), lid)


def tray_unit(b, x, y, z):
    """Stainless tray of cuts on a table: three stacked trays with product, label on the rim."""
    for k in range(3):
        zz = z + k * 0.12
        b.box((x, y, zz), (x + 1.2, y + 0.6, zz + 0.1), M["tray"])
        b.box((x + 0.05, y + 0.05, zz + 0.09), (x + 1.15, y + 0.55, zz + 0.115), M["meat"])
    b.box((x + 0.5, y - 0.005, z + 0.05), (x + 0.8, y, z + 0.1), M["label"])


def beef_carton_pallet(b, x, y, z):
    """Pallet of packed boxes, banded."""
    top = props.pallet(b, x, y, z)
    for k in range(4):
        b.box((x + 0.02, y + 0.02, top + k * 0.25), (x + 0.98, y + 1.18, top + k * 0.25 + 0.24), M["carton"])
    for bx in (x + 0.3, x + 0.65):
        b.box((bx, y + 0.015, top), (bx + 0.05, y + 1.185, top + 1.0), props.M["wrap_band"])


def rooftop_units(b, x0, y0, x1, y1, z, count=3):
    """Condensers and extract units on a flat roof."""
    step = (x1 - x0) / count
    for i in range(count):
        cx = x0 + step * (i + 0.5)
        b.box((cx - 0.9, (y0 + y1) / 2 - 0.7, z), (cx + 0.9, (y0 + y1) / 2 + 0.7, z + 0.9), props.M["fan_housing"])
        b.cylinder_along((cx, (y0 + y1) / 2, z + 0.92), "X", 0.5, 0.05, props.M["grill"], segments=12)
        b.cylinder((cx + 0.3, (y0 + y1) / 2 + 1.0, z), 0.12, 1.2, props.M["steel"], segments=8)


def plant(root, roofs, interior):
    plant = empty("ABATTOIR_BEEF", parent=root)
    box("BEEF_ABATTOIR_SLAB", (13, 30, G - 0.1), (31, 49, G + 0.03), M["farm_floor"], plant)
    # Lairage: open pens under a lifting roof, solid back wall, steel frame stays.
    box("BEEF_WAITING_BACK", (13, 42, G), (24, 42.2, G + 3), M["plant"], plant)
    ribbed_wall("BEEF_WAITING_CLADDING", (24, 42.2), (13, 42.2), G, 3.0, (0, 1), plant, base=0.5)
    MeshBuilder().gable((12.8, 30, G + 3), (24.2, 42.4, G + 3.2), 0.7, M["plant_roof"]).build("ROOF_BEEF_WAITING", parent=roofs)["ao_skip"] = True
    frame = MeshBuilder()
    for x in (13.1, 15.5, 18.0, 20.5, 23.0, 23.9):
        for y in (30.15, 41.9):
            frame.box((x - 0.07, y - 0.07, G), (x + 0.07, y + 0.07, G + 3.0), props.M["steel"])
    for y in (30.15, 36.0, 41.9):
        frame.box((12.9, y - 0.06, G + 2.95), (24.1, y + 0.06, G + 3.08), props.M["steel"])
    frame.build("BEEF_WAITING_FRAME", parent=plant)
    for n, a, b in (("W", (13, 30), (13, 42)), ("E_S", (23, 30), (23, 31)), ("E_N", (23, 35), (23, 42)), ("N", (13, 41.5), (23, 41.5))):
        rails("BEEF_WAITING_RAIL_" + n, a, b, interior)
    rails("BEEF_WAITING_DIVIDER", (13, 41), (18, 41), interior)
    pen = MeshBuilder()
    pen.box((13.3, 39, G), (15.3, 40, G + 0.5), M["rail"])
    pen.box((13.4, 39.1, G + 0.48), (15.2, 39.9, G + 0.5), M["water"])
    pen.box((17.0, 41.2, G + 0.9), (20.0, 41.4, G + 1.1), props.M["steel"])  # hay rack
    pen.build("BEEF_WAITING_WATER", parent=interior)
    # Drain channel across the lairage floor.
    box("BEEF_WAITING_DRAIN", (13.1, 34.4, G + 0.03), (22.9, 34.6, G + 0.045), props.M["grill"], interior)
    cattle_group("CATTLE_BEEF_WAITING", [(x, y, G + 0.05) for y in (33, 36, 39) for x in (15.6, 20.8)], interior)
    # Offset approach corridor enters an opaque building; no machinery or carcasses.
    for n, a, b in (("A", (23.5, 35), (23.5, 43)), ("B", (25.5, 35), (25.5, 42.7))):
        rails("BEEF_APPROACH_RAIL_" + n, a, b, interior)
    opaque = empty("BEEF_KILLING_OPAQUE", parent=plant)
    enclosure = MeshBuilder()
    for a, b in (
        ((23.2, 42.1, G), (23.4, 49, G + 4)), ((30.8, 42.1, G), (31, 49, G + 4)), ((23.2, 48.8, G), (31, 49, G + 4)),
        ((23.2, 42.1, G), (23.5, 42.3, G + 4)), ((25.5, 42.1, G), (31, 42.3, G + 4)), ((23.5, 42.1, G + 2.5), (25.5, 42.3, G + 4)),
        ((23.4, 44, G), (25.7, 44.2, G + 4)),
    ):
        enclosure.box(a, b, M["plant"])
    bevel(enclosure.build("BEEF_KILLING_ENCLOSURE", parent=opaque), 0.02)
    roof = MeshBuilder().box((23.1, 42, G + 4), (31.1, 49.1, G + 4.2), M["plant_roof"])
    roof.box((23.0, 41.9, G + 4.2), (31.2, 42.05, G + 4.55), M["plant_roof"])  # parapet
    roof.box((23.0, 49.05, G + 4.2), (31.2, 49.2, G + 4.55), M["plant_roof"])
    roof.box((23.0, 41.9, G + 4.2), (23.15, 49.2, G + 4.55), M["plant_roof"])
    roof.box((31.05, 41.9, G + 4.2), (31.2, 49.2, G + 4.55), M["plant_roof"])
    rooftop_units(roof, 24.0, 43.0, 30.5, 48.5, G + 4.2, 3)
    roof.build("BEEF_KILLING_ROOF", parent=opaque)
    ribbed_wall("BEEF_KILLING_CLADDING_E", (31, 42.1), (31, 49), G, 4.0, (1, 0), opaque, base=0.8)
    ribbed_wall("BEEF_KILLING_CLADDING_N", (31, 49), (23.2, 49), G, 4.0, (0, 1), opaque, base=0.8)
    ribbed_wall("BEEF_KILLING_CLADDING_FRONT", (31, 42.1), (25.5, 42.1), G, 4.0, (0, -1), opaque, base=0.8)
    entry = MeshBuilder()  # door frame, light and hazard strip at the animal entrance
    entry.box((23.45, 41.95, G), (23.6, 42.1, G + 2.5), props.M["steel"])
    entry.box((25.35, 41.95, G), (25.5, 42.1, G + 2.5), props.M["steel"])
    entry.box((24.0, 41.95, G + 2.3), (25.0, 42.0, G + 2.4), props.M["lamp"])
    entry.build("BEEF_KILLING_ENTRY", parent=opaque)
    # Condenser bank and pipe run on the east wall, a stack on the roof.
    plantside = MeshBuilder()
    for i in range(3):
        y = 43.0 + i * 2.0
        plantside.box((31.0, y, G), (32.2, y + 1.4, G + 1.6), props.M["fan_housing"])
        plantside.cylinder_along((32.21, y + 0.7, G + 0.85), "X", 0.5, 0.04, props.M["grill"], segments=12)
    plantside.cylinder_along((31.1, 46.0, G + 3.4), "Y", 0.08, 7.0, props.M["steel"], segments=8)
    plantside.cylinder((29.5, 48.2, G + 4.2), 0.3, 2.4, props.M["steel"], segments=10)
    plantside.build("BEEF_KILLING_DETAILS", parent=opaque)
    cattle_group("CATTLE_BEEF_APPROACH", [(27 + (i % 3) * 1.2, 45.5 + (i // 3) * 1.6, G + 0.05) for i in range(6)], interior)

    # Three separate sanitary rooms, closed boxes with the roof omitted.
    for name, x0, x1, y0, y1, col in (("COLD_ROOM_BEEF", 33, 41, 38, 47, "cold"), ("CUTTING_BEEF", 33, 41, 28, 36, "plant"), ("PACKING_BEEF", 33, 41, 19, 26, "white")):
        room = empty(name, parent=root)
        box(name + "_FLOOR", (x0, y0, G), (x1, y1, G + 0.08), props.M["base"], room)
        shell = MeshBuilder()
        shell.box((x0, y1 - 0.15, G), (x1, y1, G + 2.2), M[col])
        shell.box((x1 - 0.15, y0, G), (x1, y1, G + 2.2), M[col])
        shell.box((x0, y0, G), (x0 + 0.15, y1, G + 2.2), M[col])
        shell.box((x0, y0, G), (x1, y0 + 0.15, G + 0.9), M[col])  # low front wall: the room stays readable
        for t in range(1, 8):  # sandwich-panel joints
            for x in (x0 + t,):
                shell.box((x - 0.012, y1 - 0.16, G + 0.05), (x + 0.012, y1 - 0.14, G + 2.15), props.M["rib"])
        shell.box((x0 + 0.3, y1 - 0.2, G + 1.9), (x1 - 0.3, y1 - 0.15, G + 1.98), props.M["lamp"])  # light strip
        shell.build(name + "_SHELL", parent=room)
        # Refrigeration unit and roller door seen from outside, on the east wall.
        outside = MeshBuilder()
        outside.box((x1, y0 + 2.0, G + 0.1), (x1 + 0.9, y0 + 3.6, G + 1.5), props.M["fan_housing"])
        outside.cylinder_along((x1 + 0.91, y0 + 2.8, G + 0.8), "X", 0.45, 0.04, props.M["grill"], segments=12)
        outside.box((x1, y0 + 4.5, G), (x1 + 0.05, y0 + 7.0, G + 2.3), props.M["door"])
        for k in range(10):
            outside.box((x1 + 0.05, y0 + 4.5, G + 0.15 + k * 0.22), (x1 + 0.07, y0 + 7.0, G + 0.18 + k * 0.22), props.M["door_rib"])
        outside.build(name + "_OUTSIDE", parent=room)

    def table(room_name, x, y, w=5.0):
        t = MeshBuilder()
        t.box((x, y, G + 0.7), (x + w, y + 0.8, G + 0.78), props.M["hub"])
        t.box((x + 0.05, y + 0.05, G + 0.4), (x + w - 0.05, y + 0.75, G + 0.43), props.M["hub"])  # lower shelf
        for lx in (x + 0.1, x + w - 0.16):
            for ly in (y + 0.06, y + 0.68):
                t.box((lx, ly, G + 0.08), (lx + 0.06, ly + 0.06, G + 0.7), props.M["hub"])
        return t

    cold = MeshBuilder()  # steel racking along the back wall of the cold room
    for x in (33.4, 37.0):
        for px in (x, x + 3.2):
            cold.box((px, 46.3, G + 0.08), (px + 0.06, 46.4, G + 2.0), props.M["steel"])
        for z in (0.6, 1.2, 1.8):
            cold.box((x, 46.3, G + z), (x + 3.26, 46.7, G + z + 0.04), props.M["steel"])
    cold.build("COLD_ROOM_BEEF_RACKS", parent=bpy.data.objects["COLD_ROOM_BEEF"])
    cutting = MeshBuilder()
    for y in (29.0, 31.0, 33.0):
        cutting.box((34.0, y, G + 0.7), (39.0, y + 0.8, G + 0.78), props.M["hub"])
        cutting.box((34.05, y + 0.05, G + 0.4), (38.95, y + 0.75, G + 0.43), props.M["hub"])
        for lx in (34.1, 38.84):
            for ly in (y + 0.06, y + 0.68):
                cutting.box((lx, ly, G + 0.08), (lx + 0.06, ly + 0.06, G + 0.7), props.M["hub"])
    cutting.build("CUTTING_BEEF_TABLES", parent=bpy.data.objects["CUTTING_BEEF"])
    packing = MeshBuilder()
    packing.box((33.4, 25.0, G + 0.7), (40.6, 25.8, G + 0.78), props.M["hub"])  # bench along the back wall
    for lx in range(7):
        packing.box((33.5 + lx * 1.1, 25.05, G + 0.08), (33.56 + lx * 1.1, 25.11, G + 0.7), props.M["hub"])
    packing.build("PACKING_BEEF_BENCH", parent=bpy.data.objects["PACKING_BEEF"])

    for group, origin, unit, step in (
        ("MEAT_BEEF_CHILLED", (34.2, 38.8, G + 0.08), lambda b, x, y, z: crate_unit(b, x, y, z, M["tray"], M["meat"]), (1.7, 1.7)),
        ("MEAT_BEEF_CUT", (34.1, 29.1, G + 0.78), tray_unit, (1.7, 2.0)),
        ("CARTONS_BEEF_PACKED", (34.2, 20.0, G + 0.08), beef_carton_pallet, (1.7, 1.7)),
    ):
        props.unit_group(group, origin, [(i % 3, i // 3) for i in range(6)], unit, root, step=step)


def paths(root):
    points = {
        "PATH_BEEF_LOAD": [(-8, 23.5, G + 0.13), (-8, 18.8, G + 0.03), (-11, 17.5, G + 0.03), (-11, 2.7, G + 0.03), (-8, 2.7, G + 0.03), (-8, 5.7, G + 0.9), (-8, 6.5, G + 0.9)],
        "PATH_BEEF_ANIMALS": [(-8, 10, G), (-8, 12.5, G), (7, 12.5, G), (7, 22, G), (18, 22, G), (18, 28, G)],
        "PATH_BEEF_UNLOAD": [(18, 23.7, G + 0.9), (18, 20.7, G + 0.03), (15, 25, G + 0.03), (15, 33.5, G + 0.05), (18, 33.5, G + 0.05)],
        "PATH_BEEF_APPROACH": [(21.5, 32, G + 0.05), (24.5, 34, G + 0.05), (24.5, 43.4, G + 0.05), (26.8, 43.4, G + 0.05), (27, 45, G + 0.05)],
        "PATH_BEEF_DELIVERY": [(37, 15, G), (18, 15, G), (8, 15, G), (8, 9, G)],
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
    livestock = truck("TRUCK_BEEF_ANIMALS", (-8, 10, G), root)
    # Two abreast, three rows, enough head clearance and a correct 0.9m deck.
    cattle_group("CATTLE_BEEF_TRUCK", [(x, y, 0.9) for y in (-3.35, -1.35, 0.65) for x in (-0.56, 0.56)], livestock)
    ramp("BEEF_LOADING_RAMP", -8, 2.7, 5.7, root)
    ramp("BEEF_UNLOADING_RAMP", 18, 20.7, 23.7, root)
    delivery = truck("TRUCK_BEEF_DELIVERY", (37, 15, G), root, True)
    cargo = empty("CARGO_BEEF_DELIVERY", parent=delivery)
    for i in range(6):
        x, y = -1 + (i % 2) * 1.05, -4 + (i // 2) * 1.8
        b = MeshBuilder()
        beef_carton_pallet(b, x, y, 0.9)
        b.build("BEEF_DELIVERY_CARTON_" + str(i), parent=cargo)
    paths(root)
    # Dashes follow the centre of every road except the short apron spur; none cross a junction.
    props.road_markings(
        "ROAD_BEEF_MARKINGS",
        [(rd[0], rd[1], land.road_rect(rd), rd[2] >= 6.0 and i != 0) for i, rd in enumerate(ROADS)],
        G + 0.05,
        root,
    )
    # Anchors for documentary panels, all visible from the terrace.
    for name, p in (("FARM", (-10, 24, G + 3)), ("TRANSPORT", (3, 21, G + 2)), ("ABATTOIR", (22, 36, G + 3)), ("COLD_ROOM", (36, 42, G + 2)), ("CUTTING", (36, 32, G + 2)), ("PACKING", (36, 23, G + 2))):
        empty("ANCHOR_BEEF_" + name, p, root)
    argv = sys.argv[sys.argv.index("--") + 1 :]
    save_blend(os.path.abspath(argv[0]))


if __name__ == "__main__":
    main()
