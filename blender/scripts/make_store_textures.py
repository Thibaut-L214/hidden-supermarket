"""Printed atlas of the store: fictitious packaging, shelf-edge labels, carton and tray labels,
posters (layout in pack_atlas.py).

Usage (headless):
  Blender -b --factory-startup -P blender/scripts/make_store_textures.py

Writes blender/textures/pack_color.jpg (sRGB) and pack_normal.jpg (rounded pack edges, can rims,
jar lids; OpenGL convention). Deterministic: every design draws from a generator seeded by its
own index. Nothing is written and nothing imitates a real brand: bars stand for text, pictograms
are generic (leaf, drop, sun, ear of grain, flower), colours follow docs/DA.md §03 (ivory, beige,
soft green, moderate saturation). No figure, no claim.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pack_atlas as atlas  # noqa: E402
from imageio_util import to_u8, write_jpeg  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "textures")


def hexc(h: str) -> np.ndarray:
    return np.array([int(h[i : i + 2], 16) for i in (1, 3, 5)], dtype=np.float32) / 255.0


LIGHT = [hexc(h) for h in ("#EFE7D6", "#E4D8BE", "#C9D8C2", "#BFD0DA", "#E6CBC2", "#F4F2EC", "#E6D49E", "#D5DCC0")]
DEEP = [hexc(h) for h in ("#6F8752", "#4F6B4A", "#B9694A", "#5F6E7A", "#3F5068", "#9E4B3C", "#C9973A", "#7A5568", "#4E8580", "#8A6A4A")]
LIQUIDS = [hexc(h) for h in ("#B77A3A", "#5E7D55", "#BFD8E2", "#F1EEE4", "#E0A040", "#4A3328", "#D9A9A0", "#A8A04A", "#C9DDC0", "#8E3B46")]
CONTENTS = [hexc(h) for h in ("#9E3B3B", "#C9902F", "#EDE3C8", "#7F8F5A", "#5C3D2E", "#D98A3D")]
INK, WHITE, SILVER, SHADOW = hexc("#2E3336"), hexc("#FBFAF5"), hexc("#C9CBCB"), hexc("#2B2D2E")
RAIL, LINER, DARK = hexc("#9DB896"), hexc("#EEF1F1"), hexc("#3B3F42")
IVORY, BEIGE, SAGE, FOREST, TERRACOTTA, SKY, MUSTARD = (
    hexc(h) for h in ("#F3EEE2", "#DDD0B6", "#B8C9B4", "#4F6B4A", "#B9694A", "#BFD0DA", "#D8BE7A")
)
PICTOS = ("leaf", "drop", "sun", "grain", "flower", "ring", "peaks")


class Canvas:
    """Supersampled drawing surface. x runs 0-1 left to right, y 0-1 bottom to top; radii and
    corner sizes are fractions of the height, and `ar` (physical width / height of the printed
    face) keeps circles round whatever the cell's pixel shape."""

    def __init__(self, w: int, h: int, ar: float | None = None, ss: int = 3) -> None:
        self.w, self.h, self.ss = w, h, ss
        self.ar = ar or w / h
        xs = (np.arange(w * ss, dtype=np.float32) + 0.5) / (w * ss)
        ys = (np.arange(h * ss, dtype=np.float32) + 0.5) / (h * ss)
        self.x, self.y = np.meshgrid(xs, ys)
        self.X = self.x * self.ar
        self.px = np.ones((h * ss, w * ss, 3), dtype=np.float32)

    def fill(self, colour) -> None:
        self.px[:] = colour

    def paint(self, mask, colour, alpha: float = 1.0) -> None:
        self.px[mask] = self.px[mask] * (1 - alpha) + np.asarray(colour, dtype=np.float32) * alpha

    def circle(self, cx, cy, r):
        return (self.X - cx * self.ar) ** 2 + (self.y - cy) ** 2 < r * r

    def ellipse(self, cx, cy, rx, ry, angle: float = 0.0):
        dx, dy = self.X - cx * self.ar, self.y - cy
        ca, sa = math.cos(angle), math.sin(angle)
        return ((dx * ca + dy * sa) / rx) ** 2 + ((-dx * sa + dy * ca) / ry) ** 2 < 1

    def rect(self, x0, y0, x1, y1, r: float = 0.0):
        hx, hy = (x1 - x0) / 2 * self.ar, (y1 - y0) / 2
        r = min(r, hx, hy)
        qx = np.abs(self.X - (x0 + x1) / 2 * self.ar) - hx + r
        qy = np.abs(self.y - (y0 + y1) / 2) - hy + r
        return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) < r + 1e-6

    def triangle(self, a, b, c):
        def side(p, q):
            return (self.X - p[0] * self.ar) * (q[1] - p[1]) - (self.y - p[1]) * (q[0] - p[0]) * self.ar

        d0, d1, d2 = side(a, b), side(b, c), side(c, a)
        return ((d0 >= 0) & (d1 >= 0) & (d2 >= 0)) | ((d0 <= 0) & (d1 <= 0) & (d2 <= 0))

    def bars(self, x0, y0, x1, y1, rows: int, colour, rng, alpha: float = 1.0, centre: bool = False) -> None:
        """Rows of rounded bars of uneven length: they stand for lines of text."""
        pitch = (y1 - y0) / rows
        for k in range(rows):
            length = (x1 - x0) * (1.0 if k == 0 else float(rng.uniform(0.5, 0.95)))
            xa = (x0 + x1 - length) / 2 if centre else x0
            ya = y1 - (k + 1) * pitch + pitch * 0.22
            self.paint(self.rect(xa, ya, xa + length, ya + pitch * 0.56, pitch * 0.28), colour, alpha)

    def barcode(self, x0, y0, x1, y1, rng) -> None:
        self.paint(self.rect(x0, y0, x1, y1), WHITE)
        u = (self.x - x0) / (x1 - x0)
        stripes = rng.random(28) < 0.55
        index = np.clip((u * 28).astype(int), 0, 27)
        inside = (u > 0.06) & (u < 0.94) & (self.y > y0 + (y1 - y0) * 0.14) & (self.y < y1 - (y1 - y0) * 0.14)
        self.paint(inside & stripes[index], INK)

    def picto(self, name: str, cx, cy, r, colour, ground=None) -> None:
        """Generic pictogram of radius r; `ground` is the colour behind it (for cut-outs)."""
        if name == "leaf":
            lens = self.ellipse(cx, cy, r, r * 0.52, 0.9)
            self.paint(lens, colour)
            if ground is not None:
                self.paint(lens & self.ellipse(cx, cy, r * 0.92, r * 0.035, 0.9), ground)
        elif name == "drop":
            apex = (cx, cy + r)
            left, right = (cx - 0.62 * r / self.ar, cy - 0.1 * r), (cx + 0.62 * r / self.ar, cy - 0.1 * r)
            self.paint(self.circle(cx, cy - 0.3 * r, 0.66 * r) | self.triangle(left, right, apex), colour)
        elif name == "sun":
            self.paint(self.circle(cx, cy, 0.52 * r), colour)
            for k in range(8):
                a = k * math.pi / 4
                self.paint(self.circle(cx + math.cos(a) * 0.84 * r / self.ar, cy + math.sin(a) * 0.84 * r, 0.11 * r), colour)
        elif name == "grain":
            self.paint(self.rect(cx - 0.035 * r / self.ar, cy - r, cx + 0.035 * r / self.ar, cy + 0.5 * r), colour)
            for k in range(3):
                for s in (-1, 1):
                    self.paint(self.ellipse(cx + s * 0.24 * r / self.ar, cy - 0.3 * r + k * 0.42 * r, 0.3 * r, 0.14 * r, s * 0.9), colour)
            self.paint(self.ellipse(cx, cy + 0.82 * r, 0.14 * r, 0.26 * r), colour)
        elif name == "flower":
            for k in range(5):
                a = math.pi / 2 + k * 2 * math.pi / 5
                self.paint(self.circle(cx + math.cos(a) * 0.52 * r / self.ar, cy + math.sin(a) * 0.52 * r, 0.36 * r), colour)
            if ground is not None:
                self.paint(self.circle(cx, cy, 0.24 * r), ground)
        elif name == "ring":
            self.paint(self.circle(cx, cy, r), colour)
            if ground is not None:
                self.paint(self.circle(cx, cy, 0.58 * r), ground)
                self.paint(self.circle(cx, cy, 0.26 * r), colour)
        else:  # peaks
            base = cy - 0.7 * r
            self.paint(self.triangle((cx - r / self.ar, base), (cx + 0.25 * r / self.ar, base), (cx - 0.35 * r / self.ar, cy + 0.75 * r)), colour)
            self.paint(self.triangle((cx - 0.3 * r / self.ar, base), (cx + r / self.ar, base), (cx + 0.38 * r / self.ar, cy + 0.3 * r)), colour)

    def out(self) -> np.ndarray:
        s = self.ss
        return self.px.reshape(self.h, s, self.w, s, 3).mean(axis=(1, 3))


def _pick(rng, colours, avoid=None):
    while True:
        c = colours[int(rng.integers(len(colours)))]
        if avoid is None or float(np.abs(c - avoid).sum()) > 0.35:
            return c


# --- product faces --------------------------------------------------------------------------------

def front(c: Canvas, rng, kind: str, base, acc, acc2, template: int) -> None:
    ink = INK
    picto = PICTOS[int(rng.integers(len(PICTOS)))]
    wide = c.ar  # how much room there is across, in height units
    c.fill(base)
    if template == 0:  # badge over a foot band
        c.paint(c.rect(0, 0, 1, 0.16), acc)
        r = min(0.2, 0.4 * wide)
        c.paint(c.circle(0.5, 0.67, r), acc2)
        c.picto(picto, 0.5, 0.67, r * 0.62, WHITE, acc2)
        c.bars(0.14, 0.36, 0.86, 0.46, 1, ink, rng)
        c.bars(0.2, 0.22, 0.8, 0.34, 2, ink, rng, 0.45, centre=True)
        c.bars(0.3, 0.05, 0.7, 0.12, 1, WHITE, rng, 0.9)
    elif template == 1:  # header band
        c.paint(c.rect(0, 0.72, 1, 1), acc)
        c.bars(0.14, 0.8, 0.86, 0.92, 1, WHITE, rng)
        c.paint(c.rect(0, 0.695, 1, 0.72), acc2)
        r = min(0.17, 0.36 * wide)
        c.picto(picto, 0.5, 0.47, r, acc2, base)
        c.bars(0.16, 0.1, 0.84, 0.26, 3, ink, rng, 0.5, centre=True)
    elif template == 2:  # label on a full colour
        c.fill(acc)
        c.paint(c.rect(0.09, 0.24, 0.91, 0.82, 0.045), WHITE)
        r = min(0.11, 0.26 * wide)
        c.picto(picto, 0.5, 0.67, r, acc2, WHITE)
        c.bars(0.18, 0.42, 0.82, 0.52, 1, ink, rng)
        c.bars(0.22, 0.28, 0.78, 0.4, 2, ink, rng, 0.45, centre=True)
        c.bars(0.25, 0.08, 0.75, 0.17, 1, WHITE, rng, 0.85, centre=True)
        c.bars(0.3, 0.87, 0.7, 0.94, 1, WHITE, rng, 0.6, centre=True)
    elif template == 3:  # wave
        c.paint(c.y < 0.44 + 0.035 * np.sin(c.x * 3.0 * math.pi + float(rng.uniform(0, 6))), acc)
        r = min(0.15, 0.34 * wide)
        c.picto(picto, 0.5, 0.72, r, acc2, base)
        c.bars(0.14, 0.26, 0.86, 0.37, 1, WHITE, rng)
        c.bars(0.2, 0.08, 0.8, 0.22, 2, WHITE, rng, 0.7, centre=True)
    else:  # fine stripes and an oval
        c.paint(np.floor(c.y * 26) % 2 == 0, acc, 0.3)
        c.paint(c.ellipse(0.5, 0.5, min(0.47 * wide, 0.42), 0.24), WHITE)
        c.paint(c.ellipse(0.5, 0.5, min(0.47 * wide, 0.42), 0.24) & ~c.ellipse(0.5, 0.5, min(0.44 * wide, 0.39), 0.215), acc2)
        c.bars(0.2, 0.5, 0.8, 0.6, 1, ink, rng, centre=True)
        c.bars(0.26, 0.38, 0.74, 0.5, 2, ink, rng, 0.45, centre=True)
        c.picto(picto, 0.5, 0.84, min(0.085, 0.3 * wide), acc2, base)
        c.paint(c.rect(0, 0, 1, 0.1), acc)
    if rng.random() < 0.4:  # a small round seal in a corner
        c.paint(c.circle(0.8, 0.9, 0.045), acc2 if template != 1 else WHITE)
    if kind == "bag":  # crimped top seam
        c.paint(c.rect(0, 0.925, 1, 1), base * 0.86)
        c.paint((c.y > 0.925) & (np.floor(c.x * 30) % 2 == 0), base * 0.76)


def side(c: Canvas, rng, base, acc, full: bool) -> None:
    c.fill(acc if full else base)
    ink = WHITE if full else INK
    c.bars(0.16, 0.42, 0.84, 0.86, 7, ink, rng, 0.55)
    c.barcode(0.18, 0.1, 0.82, 0.24, rng)
    c.paint(c.rect(0, 0, 1, 0.045), acc if not full else base)


def top_strip(c: Canvas, base, packs: int) -> None:
    """Tops of the packs behind one another: u runs from the shelf front to the back."""
    c.fill(base * 0.94)
    for k in range(1, packs):
        c.paint(np.abs(c.x - k / packs) < 0.006, INK, 0.55)
    c.paint(np.abs(c.y - 0.5) < 0.02, base * 0.8, 0.6)


def lids(c: Canvas, lid, detail, kind: str) -> None:
    """Four lids seen from above on the dark gap between them."""
    c.fill(SHADOW)
    for k in range(4):
        cx = (k + 0.5) / 4
        c.paint(c.circle(cx, 0.5, 0.5), lid)
        if kind == "can":
            c.paint(c.circle(cx, 0.5, 0.42) & ~c.circle(cx, 0.5, 0.38), lid * 0.82)
            c.paint(c.ellipse(cx, 0.44, 0.1, 0.16), lid * 0.78)
        elif kind == "pot":
            c.paint(c.circle(cx, 0.5, 0.44) & ~c.circle(cx, 0.5, 0.41), lid * 0.88)
            c.paint(c.circle(cx, 0.5, 0.17), detail)
        else:
            c.paint(c.circle(cx, 0.5, 0.4) & ~c.circle(cx, 0.5, 0.35), lid * 0.8)
            c.paint(c.circle(cx, 0.5, 0.1), lid * 1.12)


def gloss(c: Canvas, y0: float, y1: float) -> None:
    band = (c.y > y0) & (c.y < y1)
    c.paint(band & (np.abs(c.x - 0.37) < 0.022), WHITE, 0.22)
    c.paint(band & (np.abs(c.x - 0.66) < 0.01), WHITE, 0.12)


def wrap(c: Canvas, rng, kind: str, variant: int):
    """Label wrapped around a cylinder: the front is u = 0.5. Returns (lid colour, detail)."""
    picto = PICTOS[int(rng.integers(len(PICTOS)))]
    acc = _pick(rng, DEEP)
    acc2 = _pick(rng, DEEP, acc)
    light = _pick(rng, LIGHT)
    if kind == "bottle":
        liquid = LIQUIDS[variant % len(LIQUIDS)]
        c.fill(liquid)
        c.paint(c.y < 0.03, liquid * 0.8)
        c.paint(c.y > 0.6, liquid * 0.9 + 0.1)
        gloss(c, 0.03, 0.88)
        paper = light if float(liquid.mean()) < 0.62 else acc
        ink = INK if paper is light else WHITE
        c.paint(c.rect(0.18, 0.13, 0.82, 0.5, 0.02), paper)
        c.picto(picto, 0.5, 0.39, 0.075, acc2 if paper is light else WHITE, paper)
        c.bars(0.3, 0.2, 0.7, 0.3, 2, ink, rng, 0.75, centre=True)
        c.paint(c.rect(0.18, 0.13, 0.82, 0.16), acc2)
        cap = acc if rng.random() < 0.6 else WHITE
        c.paint(c.y > 0.905, cap)
        c.paint((c.y > 0.905) & (np.floor(c.x * 40) % 2 == 0), cap * 0.86)
        return cap, acc2
    if kind == "can":
        c.fill(acc)
        c.paint(c.rect(0, 0.1, 1, 0.19), acc2)
        c.paint(c.circle(0.5, 0.56, 0.27), WHITE)
        c.picto(picto, 0.5, 0.56, 0.17, acc, WHITE)
        for u in (0.1, 0.9):
            c.bars(u - 0.07, 0.3, u + 0.07, 0.85, 6, WHITE, rng, 0.7)
        gloss(c, 0.08, 0.92)
        c.paint((c.y < 0.07) | (c.y > 0.93), SILVER)
        return SILVER, acc
    if kind == "jar":
        content = CONTENTS[variant % len(CONTENTS)]
        c.fill(content)
        gloss(c, 0.02, 0.8)
        c.paint(c.rect(0.2, 0.14, 0.8, 0.7, 0.03), light)
        c.picto(picto, 0.5, 0.52, 0.11, acc, light)
        c.bars(0.3, 0.2, 0.7, 0.36, 2, INK, rng, 0.7, centre=True)
        c.paint(c.rect(0.2, 0.64, 0.8, 0.7), acc)
        lid = acc2 if rng.random() < 0.5 else hexc("#C8A64A")
        c.paint(c.y > 0.82, lid)
        c.paint((c.y > 0.84) & (c.y < 0.98) & (np.floor(c.x * 48) % 2 == 0), lid * 0.84)
        return lid, acc
    # pot: a pale cup with a colour band and a foil lid
    cup = hexc("#F4F2EC")
    c.fill(cup)
    c.paint(c.y < 0.36, acc)
    c.picto(picto, 0.5, 0.63, 0.2, acc2, cup)
    c.bars(0.32, 0.12, 0.68, 0.28, 1, WHITE, rng, 0.9)
    c.paint(c.y > 0.9, hexc("#DADCDC"))
    return hexc("#E8EAEA"), acc


def product_block(kind: str, variant: int, colour: np.ndarray, height: np.ndarray) -> None:
    rects = atlas.block(kind, variant)
    index = list(atlas.KINDS).index(kind)
    rng = np.random.default_rng(7919 * (index + 1) + 131 * variant)
    _, cylinder, (pw, ph) = atlas.KINDS[kind]
    if cylinder:
        x0, y0, x1, y1 = rects["wrap"]
        c = Canvas(x1 - x0, y1 - y0, pw / ph)
        lid, detail = wrap(c, rng, kind, variant)
        colour[y0:y1, x0:x1] = c.out()
        height[y0:y1, x0:x1] = wrap_height(kind, x1 - x0, y1 - y0)
        x0, y0, x1, y1 = rects["top"]
        c = Canvas(x1 - x0, y1 - y0)
        lids(c, lid, detail, kind)
        colour[y0:y1, x0:x1] = c.out()
        return
    base = LIGHT[(variant * 3 + index) % len(LIGHT)]
    acc = DEEP[(variant * 7 + index * 3) % len(DEEP)]
    acc2 = _pick(rng, DEEP, acc)
    template = (variant + index) % 5
    x0, y0, x1, y1 = rects["front"]
    c = Canvas(x1 - x0, y1 - y0, pw / ph)
    front(c, rng, kind, base, acc, acc2, template)
    colour[y0:y1, x0:x1] = c.out()
    height[y0:y1, x0:x1] = pillow_height(x1 - x0, y1 - y0) if kind == "bag" else edge_height(x1 - x0, y1 - y0, 7)
    x0, y0, x1, y1 = rects["side"]
    c = Canvas(x1 - x0, y1 - y0, 0.3 / ph)
    side(c, rng, base, acc, template == 2)
    colour[y0:y1, x0:x1] = c.out()
    height[y0:y1, x0:x1] = edge_height(x1 - x0, y1 - y0, 7)
    x0, y0, x1, y1 = rects["top"]
    c = Canvas(x1 - x0, y1 - y0)
    packs = 4 if kind == "brick" else 2
    top_strip(c, acc if template == 2 else base, packs)
    colour[y0:y1, x0:x1] = c.out()
    grooves = np.abs(((np.arange(x1 - x0) + 0.5) / (x1 - x0) * packs) % 1 - 0.5) * 2  # 1 on a seam
    height[y0:y1, x0:x1] = edge_height(x1 - x0, y1 - y0, 5) * (1 - 0.8 * smoothstep(0.9, 1.0, grooves))[None, :]


# --- relief (normal map) ----------------------------------------------------------------------------

def smoothstep(e0: float, e1: float, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def edge_height(w: int, h: int, radius: float) -> np.ndarray:
    """Flat face with rounded edges: 0 on the border, 1 inside."""
    x = np.minimum(np.arange(w) + 0.5, w - np.arange(w) - 0.5)
    y = np.minimum(np.arange(h) + 0.5, h - np.arange(h) - 0.5)
    return smoothstep(0.0, radius, np.minimum(x[None, :], y[:, None]))


def pillow_height(w: int, h: int) -> np.ndarray:
    """A filled bag: puffed in the middle, a ridged seam along the top."""
    x = (np.arange(w) + 0.5) / w
    y = (np.arange(h) + 0.5) / h
    puff = np.sqrt(np.sin(math.pi * x)[None, :] * np.sin(math.pi * np.clip(y / 0.92, 0, 1))[:, None]) * 2.2
    seam = (y > 0.925)[:, None] * (0.3 + 0.25 * np.sin(x * 60 * math.pi))[None, :]
    return np.where((y > 0.925)[:, None], seam, puff)


def wrap_height(kind: str, w: int, h: int) -> np.ndarray:
    v = (np.arange(h) + 0.5) / h
    if kind == "can":
        profile = smoothstep(0.0, 0.05, v) * smoothstep(0.0, 0.05, 1 - v) - 0.5 * np.exp(-(((v - 0.07) / 0.012) ** 2)) - 0.5 * np.exp(-(((v - 0.93) / 0.012) ** 2))
    elif kind == "jar":
        profile = smoothstep(0.0, 0.06, v) + 0.25 * (v > 0.84) * np.sin(v * 150) + 0.25 * ((v > 0.14) & (v < 0.7))
    elif kind == "pot":
        profile = smoothstep(0.0, 0.08, v) + 0.6 * smoothstep(0.88, 0.92, v)
    else:  # bottle: a faint step at the label and a ribbed cap
        profile = 0.2 * ((v > 0.13) & (v < 0.5)) + 0.3 * smoothstep(0.9, 0.91, v)
    return np.repeat(profile[:, None], w, axis=1)


def normals(height: np.ndarray, slope: float) -> np.ndarray:
    """Tangent-space normals (OpenGL) of a bottom-up height field; cells do not wrap."""
    gx = np.gradient(height, axis=1) * slope
    gy = np.gradient(height, axis=0) * slope
    length = np.sqrt(gx * gx + gy * gy + 1.0)
    return np.stack([-gx / length, -gy / length, 1.0 / length], axis=-1) * 0.5 + 0.5


# --- labels ---------------------------------------------------------------------------------------

def rail_cell(i: int) -> np.ndarray:
    x0, y0, x1, y1 = atlas.rail(i)
    rng = np.random.default_rng(4201 + i)
    c = Canvas(x1 - x0, y1 - y0, 0.238 / 0.065)
    c.fill(RAIL)
    c.paint(c.y < 0.07, RAIL * 0.82)
    c.paint(c.y > 0.94, RAIL * 1.08)
    promo = i == 3
    paper = hexc("#F2DC86") if promo else WHITE
    c.paint(c.rect(0.345, 0.09, 0.655, 0.91, 0.07), RAIL * 0.7)
    c.paint(c.rect(0.35, 0.11, 0.65, 0.89, 0.06), paper)
    c.bars(0.375, 0.56, 0.6, 0.83, 2, INK, rng, 0.55)
    c.paint(c.rect(0.5, 0.2, 0.63, 0.5, 0.05), TERRACOTTA if promo else INK)
    c.barcode(0.372, 0.2, 0.47, 0.44, rng)
    return c.out()


def carton_label(i: int) -> np.ndarray:
    x0, y0, x1, y1 = atlas.carton_label(i)
    rng = np.random.default_rng(5303 + i)
    c = Canvas(x1 - x0, y1 - y0, 0.16 / 0.03)
    paper, acc = (hexc("#F6F1E4"), FOREST) if i == 0 else (hexc("#EFE3CB"), TERRACOTTA)
    c.fill(paper)
    c.paint(c.rect(0, 0, 0.2, 1), acc)
    c.paint(c.ellipse(0.1, 0.5, 0.24, 0.32), WHITE)
    c.bars(0.25, 0.2, 0.72, 0.84, 2, INK, rng, 0.75)
    c.picto("leaf", 0.88, 0.5, 0.3, acc, paper)
    return c.out()


def tray_label(i: int) -> np.ndarray:
    x0, y0, x1, y1 = atlas.tray_label(i)
    rng = np.random.default_rng(6101 + i)
    c = Canvas(x1 - x0, y1 - y0, 0.09 / 0.05)
    c.fill(WHITE)
    c.paint(c.rect(0, 0.74, 1, 1), hexc("#8E3B46") if i == 0 else hexc("#5F6E7A"))
    c.bars(0.1, 0.8, 0.7, 0.94, 1, WHITE, rng)
    c.bars(0.08, 0.44, 0.92, 0.7, 2, INK, rng, 0.6)
    c.barcode(0.08, 0.08, 0.48, 0.38, rng)
    c.paint(c.rect(0.58, 0.1, 0.92, 0.36, 0.05), INK)
    return c.out()


# --- posters ----------------------------------------------------------------------------------------

def poster(i: int) -> np.ndarray:
    """Generic in-store posters: soft shapes, bars for text, no figure and no claim."""
    x0, y0, x1, y1 = atlas.poster(i)
    rng = np.random.default_rng(7001 + i)
    c = Canvas(x1 - x0, y1 - y0, 1.05 / 1.2, ss=2)
    if i == 0:
        c.fill(IVORY)
        c.paint(c.circle(0.5, 0.63, 0.25), SAGE)
        c.picto("leaf", 0.5, 0.63, 0.15, FOREST, SAGE)
        c.bars(0.18, 0.2, 0.82, 0.32, 2, INK, rng, 0.9, centre=True)
        c.paint(c.rect(0, 0, 1, 0.1), BEIGE)
        c.bars(0.3, 0.03, 0.7, 0.075, 1, WHITE, rng, 0.9, centre=True)
    elif i == 1:
        c.fill(BEIGE)
        packs = ((0.14, 0.36, 0.76, SAGE, FOREST), (0.39, 0.61, 0.83, IVORY, TERRACOTTA), (0.64, 0.86, 0.72, SKY, hexc("#5F6E7A")))
        for xa, xb, top, body, band in packs:
            c.paint(c.ellipse((xa + xb) / 2, 0.385, 0.13, 0.018), BEIGE * 0.82)
            c.paint(c.rect(xa, 0.39, xb, top, 0.02), body)
            c.paint(c.rect(xa, 0.39 + (top - 0.39) * 0.3, xb, 0.39 + (top - 0.39) * 0.52), band)
            c.bars(xa + 0.04, 0.39 + (top - 0.39) * 0.62, xb - 0.04, 0.39 + (top - 0.39) * 0.8, 2, INK, rng, 0.5, centre=True)
        c.paint(c.circle(0.8, 0.87, 0.085), TERRACOTTA)
        c.picto("sun", 0.8, 0.87, 0.06, WHITE, TERRACOTTA)
        c.bars(0.14, 0.14, 0.86, 0.29, 2, INK, rng, 0.9)
    elif i == 2:
        c.fill(hexc("#C9D8C2"))
        c.paint(c.circle(0.5, 0.4, 0.3) & (c.y > 0.4), IVORY)
        c.paint(c.rect(0.1, 0.392, 0.9, 0.404), FOREST)
        for cx, r in ((0.3, 0.05), (0.5, 0.065), (0.7, 0.05)):
            c.picto("leaf", cx, 0.5, r, FOREST, IVORY)
        c.bars(0.2, 0.78, 0.8, 0.9, 2, FOREST, rng, 0.95, centre=True)
        c.bars(0.28, 0.2, 0.72, 0.32, 2, IVORY, rng, 0.9, centre=True)
    else:
        c.fill(IVORY)
        c.paint(c.rect(0.06, 0.05, 0.94, 0.95, 0.02) & ~c.rect(0.075, 0.062, 0.925, 0.938, 0.015), BEIGE)
        for cx, cy, r, col in ((0.34, 0.6, 0.13, TERRACOTTA), (0.62, 0.57, 0.15, MUSTARD), (0.49, 0.74, 0.11, SAGE)):
            c.paint(c.circle(cx, cy, r), col)
            c.picto("leaf", cx + 0.04, cy + r * 0.98, r * 0.3, FOREST)
        c.paint(c.rect(0.2, 0.36, 0.8, 0.52, 0.03), BEIGE)
        c.paint(c.rect(0.2, 0.36, 0.8, 0.52, 0.03) & (np.floor(c.x * 34) % 2 == 0), BEIGE * 0.88)
        c.paint(c.rect(0.18, 0.5, 0.82, 0.535, 0.015), BEIGE * 0.8)
        c.bars(0.2, 0.14, 0.8, 0.28, 2, INK, rng, 0.9, centre=True)
    return c.out()


def main() -> None:
    n = atlas.SIZE
    colour = np.empty((n, n, 3), dtype=np.float32)
    colour[:] = hexc("#D8D2C4")
    height = np.zeros((n, n), dtype=np.float32)
    for kind, (count, _, _) in atlas.KINDS.items():
        for variant in range(count):
            product_block(kind, variant, colour, height)
    for i in range(atlas.POSTERS):
        x0, y0, x1, y1 = atlas.poster(i)
        colour[y0:y1, x0:x1] = poster(i)
    for i in range(atlas.RAILS):
        x0, y0, x1, y1 = atlas.rail(i)
        colour[y0:y1, x0:x1] = rail_cell(i)
    for i in range(atlas.CARTON_LABELS):
        x0, y0, x1, y1 = atlas.carton_label(i)
        colour[y0:y1, x0:x1] = carton_label(i)
    for i in range(atlas.TRAY_LABELS):
        x0, y0, x1, y1 = atlas.tray_label(i)
        colour[y0:y1, x0:x1] = tray_label(i)
    for name, value in zip(atlas.SWATCHES, (RAIL, WHITE, DARK, LINER)):
        x0, y0, x1, y1 = atlas.swatch(name)
        colour[y0:y1, x0:x1] = value
    # Arrays are bottom-up (UV space); the writer takes rows top first.
    write_jpeg(os.path.join(ROOT, "pack_color.jpg"), to_u8(colour[::-1]), quality=90)
    relief = normals(height, 3.0)
    half = relief.reshape(n // 2, 2, n // 2, 2, 3).mean(axis=(1, 3))
    write_jpeg(os.path.join(ROOT, "pack_normal.jpg"), to_u8(half[::-1]), quality=92)
    print("pack atlas ok")


main()
