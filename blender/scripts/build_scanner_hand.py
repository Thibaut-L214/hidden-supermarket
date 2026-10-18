"""First-person scanner: a right hand holding a handheld store terminal (docs/DA.md §05).

Usage (headless):
  Blender -b --factory-startup -P blender/scripts/build_scanner_hand.py -- <out.blend>

The tool is deliberately non-militarised: a rectangular inventory terminal held like a
phone, not a pistol-grip scanner. Its screen (SCANNER_SCREEN) shows the shelf aimed at and
the scan progress, drawn at runtime; the scan window (SCANNER_WINDOW) lights up when aiming.

Frame (metres, Z up): origin at the device's centre; the device's long axis is Z, its screen
faces -Y (towards the player, glTF +Z), its scan head points up. The runtime places and tilts
the whole in front of the camera.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from common import MeshBuilder, bevel, empty, material, reset_scene, save_blend  # noqa: E402

M = {}


def materials() -> None:
    M["body"] = material("M_TERMINAL_BODY", "#3E4347", roughness=0.45, metallic=0.2)
    M["rubber"] = material("M_TERMINAL_RUBBER", "#2B2D2F", roughness=0.9)
    M["accent"] = material("M_TERMINAL_ACCENT", "#6F8A68", roughness=0.5)
    M["key"] = material("M_TERMINAL_KEY", "#C9CCCE", roughness=0.5)
    M["screen"] = material("M_TERMINAL_SCREEN", "#1D2326", roughness=0.15)
    M["window"] = material("M_TERMINAL_WINDOW", "#2F3A33", roughness=0.1, emission="#9BE3A6", emission_strength=0.0)
    # A mid skin tone and a neutral sleeve; stylised, no nails or wrinkles.
    M["skin"] = material("M_HAND_SKIN", "#B98868", roughness=0.65)
    M["sleeve"] = material("M_HAND_SLEEVE", "#6F7F87", roughness=0.9)


def device(root) -> None:
    d = MeshBuilder()
    d.box((-0.038, -0.016, -0.085), (0.038, 0.016, 0.085), M["body"])
    for z0, z1 in ((0.075, 0.097), (-0.097, -0.075)):
        d.box((-0.041, -0.018, z0), (0.041, 0.018, z1), M["rubber"])
    d.box((-0.027, -0.013, 0.097), (0.027, 0.013, 0.108), M["rubber"])
    # Keypad under the screen, side scan buttons, hand strap at the back.
    for row in range(4):
        for col in range(3):
            x0 = -0.024 + col * 0.017
            z0 = -0.07 + row * 0.014
            d.box((x0, -0.0175, z0), (x0 + 0.013, -0.016, z0 + 0.009), M["key"])
    for x0, x1 in ((-0.0415, -0.0385), (0.0385, 0.0415)):
        d.box((x0, -0.008, 0.01), (x1, 0.008, 0.04), M["accent"])
    d.box((-0.03, 0.016, -0.06), (0.03, 0.021, 0.03), M["rubber"])
    bevel(d.build("SCANNER_BODY", parent=root), 0.004, segments=2)

    screen = MeshBuilder().box((-0.029, -0.0003, -0.037), (0.029, 0.0003, 0.037), M["screen"])
    screen.build("SCANNER_SCREEN", (0.0, -0.0163, 0.033), root)
    window = MeshBuilder().box((-0.022, -0.008, -0.002), (0.022, 0.008, 0.002), M["window"])
    window.build("SCANNER_WINDOW", (0.0, 0.0, 0.11), root)


def finger(b: MeshBuilder, z: float, length: float, mat) -> None:
    """One finger wrapping round the device's left edge, from the palm to the front."""
    t = 0.018
    # Proximal phalanx behind the device, going left.
    b.oriented_box((-0.03, 0.03, z), (0.03, t, t), mat, rot_z=math.radians(-20))
    # Middle phalanx round the edge.
    b.oriented_box((-0.047, 0.012, z), (t, 0.03, t), mat, rot_z=math.radians(-10))
    # Distal phalanx on the front edge, rounded tip.
    b.oriented_box((-0.043, -0.012, z), (t * 0.95, length, t * 0.95), mat, rot_z=math.radians(15))
    b.ellipsoid((-0.039, -0.012 - length / 2, z), (t * 0.5, t * 0.5, t * 0.5), mat, u=8, v=5)
    b.ellipsoid((-0.046, 0.026, z), (t * 0.62, t * 0.62, t * 0.6), mat, u=8, v=5)  # knuckle


def hand(root) -> None:
    h = MeshBuilder()
    skin, sleeve = M["skin"], M["sleeve"]
    # Palm against the back of the device, slightly below its centre.
    h.oriented_box((0.004, 0.036, -0.03), (0.085, 0.03, 0.095), skin, rot_z=math.radians(8))
    for z, length in ((0.022, 0.022), (-0.004, 0.026), (-0.03, 0.025), (-0.054, 0.02)):
        finger(h, z, length, skin)
    # Thumb resting on the right edge, its tip on the front.
    h.oriented_box((0.04, 0.02, -0.03), (0.024, 0.04, 0.022), skin, rot_x=math.radians(25), rot_z=math.radians(25))
    h.oriented_box((0.045, -0.006, -0.012), (0.02, 0.035, 0.02), skin, rot_x=math.radians(40), rot_z=math.radians(10))
    h.ellipsoid((0.043, -0.022, 0.0), (0.011, 0.011, 0.011), skin, u=8, v=5)
    # Wrist and sleeve, going down, back and to the right, out of frame.
    h.oriented_box((0.03, 0.06, -0.1), (0.06, 0.045, 0.09), skin, rot_x=math.radians(-25), rot_z=math.radians(-20))
    h.oriented_box((0.06, 0.1, -0.2), (0.085, 0.085, 0.2), sleeve, rot_x=math.radians(-30), rot_z=math.radians(-25))
    bevel(h.build("SCANNER_HAND", parent=root), 0.006, segments=2)


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
