#!/usr/bin/env python3
"""Builds Visio stencils (.vssx) of the Ubiquiti UniFi product range.

    python3 make_unifi_stencils.py [output-folder]

Every product is a master: a group of plain vector shapes drawn here from
scratch, labelled with its model number and carrying shape data (product,
model, product line, and empty fields for a name, an IP address, a MAC
address and a location). The drawings are schematic: they show the kind of
device and its ports, not an exact likeness. The product list follows
Ubiquiti's public device catalogue (static.ui.com/fingerprint/ui/public.json).

Developer: Eric De Pessemier. Licence: GPL-3.0-or-later.
Ubiquiti and UniFi are trademarks of Ubiquiti Inc.; these stencils are not
made or endorsed by Ubiquiti.
"""

import base64
import hashlib
import math
import os
import struct
import sys
import zipfile
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw

AUTHOR = "Eric De Pessemier"

# The colours every drawing is made of.
WHITE, EDGE, SILVER, EAR = "#F7F8FA", "#8E96A3", "#E3E6EA", "#C5CAD1"
DARK, PORT, METAL, GREY = "#3A3F47", "#2B3038", "#AEB5BF", "#D3D7DD"
GLASS, LENS, BLUE, RED, SOFT = "#1A1D23", "#4A6FA5", "#006FFF", "#E5484D", "#DDE1E6"
GREEN, AMBER = "#3FB97A", "#F5A524"


class Art:
    """A drawing in inches, x to the right and y upwards, made of shapes
    that each have one fill and one line and any number of outlines."""

    def __init__(self, w, h):
        self.w, self.h, self.shapes = w, h, []

    def add(self, paths, fill, line, lw=0.5, rad=0.0):
        self.shapes.append({"paths": paths, "fill": fill, "line": line, "lw": lw, "rad": rad})
        return self

    @staticmethod
    def _box(x, y, w, h):
        return ("P", [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True)

    def r(self, x, y, w, h, fill=WHITE, line=EDGE, rad=0.0, lw=0.5):
        return self.add([self._box(x, y, w, h)], fill, line, lw, rad)

    def rs(self, boxes, fill=PORT, line=None, rad=0.0, lw=0.5):
        return self.add([self._box(*b) for b in boxes], fill, line, lw, rad) if boxes else self

    def e(self, cx, cy, rx, ry=None, fill=WHITE, line=EDGE, lw=0.5):
        return self.add([("E", cx, cy, rx, rx if ry is None else ry)], fill, line, lw)

    def es(self, dots, r, fill=PORT, line=None):
        return self.add([("E", x, y, r, r) for x, y in dots], fill, line) if dots else self

    def p(self, pts, fill=WHITE, line=EDGE, lw=0.5):
        return self.add([("P", list(pts), True)], fill, line, lw)

    def l(self, pts, color=EDGE, lw=0.75):
        return self.add([("P", list(pts), False)], None, color, lw)

    def ring(self, cx, cy, r, color=BLUE, lw=1.5, ry=None):
        return self.add([("E", cx, cy, r, r if ry is None else ry)], None, color, lw)

    def arc(self, cx, cy, r, a0, a1, color=BLUE, lw=1.0):
        n = 10
        pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
        return self.l(pts, color, lw)

    def waves(self, cx, cy, r, mid=90, spread=50, n=2, color=BLUE):
        for i in range(n):
            self.arc(cx, cy, r * (i + 1) / n, mid - spread, mid + spread, color, 1.0)
        return self

    def half(self, cx, cy, rx, ry, fill, line=EDGE, down=True):
        """Half an ellipse, hanging down from or standing on a flat side."""
        s = -1 if down else 1
        pts = [(cx + rx * math.cos(math.radians(a)), cy + s * ry * math.sin(math.radians(a))) for a in range(0, 181, 15)]
        return self.p(pts, fill, line)

    def lens(self, cx, cy, r):
        self.e(cx, cy, r, r, GLASS, None)
        self.e(cx, cy, r * 0.55, r * 0.55, LENS, None)
        return self.e(cx - r * 0.2, cy + r * 0.2, r * 0.18, r * 0.18, "#BFD4F2", None)


# ----------------------------------------------------------------- devices
# The drawings follow Ubiquiti's own product pictures and port diagrams:
# rack devices from the front, with their screen, drive bays and ports where
# they really are; the others from the side they are usually shown from.

SCREEN = "#0B1220"


def cages(a, boxes):
    """SFP and QSFP cages: a metal frame around a dark opening."""
    a.rs(boxes, METAL, "#6B7280")
    a.rs([(x + w * 0.14, y + h * 0.2, w * 0.72, h * 0.6) for x, y, w, h in boxes], PORT, None)


def lcd(a, x, y, w, h, rad=0.02):
    """A small status screen."""
    a.r(x, y, w, h, GLASS, None, rad)
    a.r(x + w * 0.22, y + h / 2 - 0.012, w * 0.56, 0.024, BLUE, None)


def pillscreen(a, cx, cy, w=0.2, h=0.085):
    a.r(cx - w / 2, cy - h / 2, w, h, GLASS, None, h * 0.48)
    a.r(cx - w * 0.22, cy - 0.011, w * 0.44, 0.022, BLUE, None)


UNITS = {"rj": 1.0, "lit": 1.0, "sfp": 1.25, "q": 1.9}


def rack(groups=(), u=1, screen="lcd", bays=0, bayrows=1, outlets=None, dark=False, w=2.8, vents=False, panel=False, ring=False):
    """The front of a 19-inch rack device. `groups` are its blocks of ports
    from left to right, each (kind, count, rows): rj, lit (an RJ45 block
    with Etherlighting), sfp or q (QSFP)."""
    W, H = w, 0.28 * u
    a = Art(W, H)
    a.rs([(0, 0, 0.13, H), (W - 0.13, 0, 0.13, H)], "#4B5563" if dark else EAR, EDGE)
    a.es([(x, y) for x in (0.065, W - 0.065) for y in (0.07, H - 0.07)], 0.022, "#6B7280")
    a.r(0.13, 0, W - 0.26, H, DARK if dark else SILVER, EDGE)
    x, right = 0.2, W - 0.2
    if screen == "lcd":
        lcd(a, x, H - 0.14 - 0.085, 0.17, 0.17)
        x += 0.25
    elif screen == "led":
        a.add([Art._box(x, H / 2 - 0.07, 0.14, 0.14)], WHITE, BLUE, 1.0, 0.02)
        x += 0.22
    elif ring:
        a.ring(x + 0.09, H / 2, 0.07, BLUE, 1.25)
        x += 0.25
    units = sum(math.ceil(n / rows) * UNITS[k] for k, n, rows in groups) + 0.5 * max(0, len(groups) - 1)
    for k, n, rows in groups:
        cols = math.ceil(n / rows)
        if k in ("rj", "lit") and cols > 8:
            units += 0.4 * ((cols - 1) // (8 if cols % 8 == 0 else 6))
    if bays:
        per = math.ceil(bays / bayrows)
        area = (right - x) if not groups else (0.78 if bays == 1 else 1.2)
        bw = (area - 0.03 * (per - 1)) / per
        bh = (H - 0.07 - 0.03 * (bayrows - 1)) / bayrows
        short = bays - per * (bayrows - 1)
        boxes = []
        for row in range(bayrows):
            for i in range(short if row == 0 else per):
                boxes.append((x + i * (bw + 0.03), H - 0.035 - bh - row * (bh + 0.03), bw, bh))
        a.rs(boxes, GREY, EDGE, 0.012)
        a.es([(bx + bw - 0.05, by + bh / 2) for bx, by, _, _ in boxes], 0.012, "#7B8491")
        if short < per:  # the ports beside a short top row
            px = x + short * (bw + 0.03) + 0.1
            a.rs([(px, H - 0.035 - bh / 2 - 0.04, 0.085, 0.08)], PORT, None)
            cages(a, [(px + 0.12, H - 0.035 - bh / 2 - 0.04, 0.11, 0.08)])
        x += area + 0.08
    if vents:
        a.es([(x + 0.06 + i * 0.045, H / 2 + j * 0.045) for i in range(int((right - x - 0.1 - (units * 0.1 if groups else 0)) / 0.045)) for j in (-1, 0, 1)], 0.014, "#9AA3AF")
    if panel:
        a.r(W / 2 - 0.3, H / 2 - 0.09, 0.6, 0.18, GLASS, None, 0.02)
        a.r(W / 2 - 0.1, H / 2 - 0.012, 0.2, 0.024, BLUE, None)
    if outlets:
        pitch = min(0.15, (right - x) / max(outlets))
        s = pitch * 0.8
        rowh = H / len(outlets)
        boxes = [(right - (n - i) * pitch, H - (row + 0.5) * rowh - s / 2, s, s) for row, n in enumerate(outlets) for i in range(n)]
        a.rs(boxes, GLASS, None, 0.015)
        a.es([(bx + s * f, by + s / 2) for bx, by, _, _ in boxes for f in (0.32, 0.68)], s * 0.08, METAL)
    if groups:
        pitch = min(0.1, (right - x) / units)
        ph = min(pitch * 0.8, 0.095)
        cx = right - units * pitch
        rjs, lits, cage = [], [], []
        for k, n, rows in groups:
            cols = math.ceil(n / rows)
            ys = [H / 2 + 0.012, H / 2 - 0.012 - ph] if rows == 2 else [H / 2 - ph / 2]
            block = (8 if cols % 8 == 0 else 6) if k in ("rj", "lit") and cols > 8 else 0
            wide = UNITS[k]
            for c in range(cols):
                if block and c and c % block == 0:
                    cx += 0.4 * pitch
                for ri, y in enumerate(ys):
                    if c * rows + ri < n:
                        box = (cx, y, wide * pitch * (0.82 if wide == 1 else 0.9), ph)
                        (rjs if k == "rj" else lits if k == "lit" else cage).append(box)
                cx += wide * pitch
            cx += 0.5 * pitch
        edge = "#8E96A3" if dark else None
        a.rs(rjs, PORT, edge)
        a.rs(lits, PORT, edge)
        a.rs([(bx, by, bw, bh * 0.28) for bx, by, bw, bh in lits], BLUE, None)
        cages(a, cage)
    return a


def desk(rj=0, sfp=0, screen=False, dark=False, w=None, ants=0, rows=1, lit=False, led="dot", split=0):
    """The port side of a small desktop or wall device."""
    pitch, top = 0.11, 0.42 if ants else 0.0
    H = 0.3 if rows == 1 else 0.38
    cols = math.ceil(rj / rows)
    n = cols + sfp * 1.3 + (0.5 if split else 0)
    W = w or max(0.9, 0.3 + n * pitch + (0.22 if screen or led == "square" else 0.1))
    a = Art(W, H + top)
    for i in range(ants):
        ax = W * (i + 0.5) / ants
        a.r(ax - 0.022, H - 0.02, 0.044, top + 0.02, DARK, None, 0.02)
    a.r(0, 0, W, H, DARK if dark else WHITE, EDGE, 0.045)
    x = 0.09
    if screen:
        lcd(a, x, H / 2 - 0.07, 0.14, 0.14)
        x += 0.2
    elif led == "square":
        a.add([Art._box(x, H / 2 - 0.06, 0.12, 0.12)], None, BLUE, 1.0, 0.02)
        x += 0.18
    else:
        a.e(x, H / 2, 0.018, 0.018, BLUE, None)
        x += 0.06
    x = max(x, W - 0.08 - n * pitch)
    boxes = []
    for i in range(rj):
        c, r = i // rows, i % rows
        y = H / 2 - 0.045 if rows == 1 else (H / 2 + 0.012 if r == 0 else H / 2 - 0.012 - 0.09)
        boxes.append((x + (c + (0.5 if split and c >= split else 0)) * pitch, y, 0.09, 0.09))
    a.rs(boxes, PORT, "#8E96A3" if dark else None)
    if lit:
        a.rs([(bx, by, bw, 0.025) for bx, by, bw, _ in boxes], BLUE, None)
    x += (cols + (0.5 if split else 0)) * pitch
    cages(a, [(x + i * 1.3 * pitch, H / 2 - 0.045, 1.3 * pitch * 0.88, 0.09) for i in range(sfp)])
    return a


def flatbox(w=1.3, h=0.3, screen="pill", dark=False):
    """The front of a compact gateway: a plain box with a small screen or
    a single light."""
    a = Art(w, h)
    a.r(0, 0, w, h, DARK if dark else WHITE, EDGE, 0.06)
    if screen == "pill":
        pillscreen(a, w / 2, h / 2)
    elif screen == "lcd":
        lcd(a, 0.08, h / 2 - 0.08, 0.3, 0.16)
    else:
        a.e(w / 2, h / 2, 0.016, 0.016, BLUE, None)
    return a


def dinbox():
    """A DIN-rail switch: a tall dark box with its ports in two columns."""
    a = Art(0.62, 1.15)
    a.r(0.2, 1.09, 0.22, 0.06, METAL, EDGE)
    a.r(0, 0, 0.62, 1.1, DARK, EDGE, 0.03)
    a.rs([(0.14 + c * 0.2, 0.42 + r * 0.14, 0.11, 0.1) for c in range(2) for r in range(4)], PORT, "#6B7280")
    cages(a, [(0.14 + c * 0.2, 0.2, 0.13, 0.1) for c in range(2)])
    return a.e(0.31, 1.0, 0.02, 0.02, BLUE, None)


def disc(d=1.0, ring=0.3, square=False, color=BLUE, rim=False):
    """A ceiling access point seen from below."""
    a = Art(d, d)
    if square:
        a.r(0, 0, d, d, WHITE, EDGE, d * 0.24)
        a.e(d / 2, d / 2, 0.03, 0.03, color, None)
    else:
        a.e(d / 2, d / 2, d / 2)
        a.ring(d / 2, d / 2, d * 0.43, color if rim else SOFT, 1.0 if rim else 0.5)
        a.ring(d / 2, d / 2, d * ring / 2, color, 1.5)
    return a


def plate(w=0.65, h=1.0, led="ring", ports=0, rad=0.09, dark=False):
    """A flat wall or pole device seen from the front: in-wall and outdoor
    access points, bridges, modems."""
    a = Art(w, h)
    a.r(0, 0, w, h, DARK if dark else WHITE, EDGE, rad)
    if led == "ring":
        a.ring(w / 2, h * 0.58, 0.07, BLUE, 1.25)
    elif led == "top":
        a.r(w / 2 - 0.07, h - 0.14, 0.14, 0.02, BLUE, None)
    elif led == "bottom":
        a.r(w / 2 - 0.07, 0.1, 0.14, 0.02, BLUE, None)
    elif led == "screen":
        lcd(a, w / 2 - 0.09, h * 0.52, 0.18, 0.24)
    elif led == "dot":
        a.e(w / 2, h * 0.3, 0.016, 0.016, BLUE, None)
    if ports:
        a.rs([(w / 2 - 0.06, 0.16 + i * 0.16, 0.12, 0.11) for i in range(ports)], PORT, "#6B7280")
    return a


def tube(w=0.3, h=1.1, band="top", screen=False, foot=False):
    """A slim cylinder: mesh access points, LTE and 5G backup units."""
    base = 0.12 if foot else 0
    a = Art(max(w, 0.5 if foot else w), h + base)
    x = (a.w - w) / 2
    if foot:
        a.r(a.w / 2 - 0.25, 0, 0.5, 0.05, METAL, EDGE, 0.02)
        a.r(a.w / 2 - 0.06, 0.04, 0.12, 0.1, METAL, EDGE)
    a.r(x, base, w, h, WHITE, EDGE, w * 0.42)
    if band:
        a.r(x + 0.015, base + (h - 0.16 if band == "top" else 0.12), w - 0.03, 0.022, BLUE, None)
    if screen:
        a.r(x + w / 2 - 0.05, base + h * 0.5, 0.1, 0.16, GLASS, None, 0.03)
        a.r(x + w / 2 - 0.025, base + h * 0.5 + 0.07, 0.05, 0.02, BLUE, None)
    return a


def capsule(w=0.62, h=1.0, screen=None):
    """The Dream Machine and Dream Routers: a white capsule with a blue
    ring near the top, some with a screen."""
    a = Art(w, h)
    a.r(0, 0, w, h, WHITE, EDGE, w * 0.36)
    a.r(0.035, h - 0.2, w - 0.07, 0.024, BLUE, None)
    if screen == "pill":
        a.r(w / 2 - 0.045, h * 0.42, 0.09, 0.17, GLASS, None, 0.04)
        a.r(w / 2 - 0.02, h * 0.42 + 0.075, 0.04, 0.02, BLUE, None)
    elif screen == "tall":
        a.r(w / 2 - 0.1, h * 0.3, 0.2, h * 0.42, GLASS, None, 0.04)
        a.rs([(w / 2 - 0.06, h * 0.6, 0.12, 0.025), (w / 2 - 0.06, h * 0.52, 0.08, 0.02)], BLUE, None)
    return a


def dreamwall():
    a = Art(0.8, 1.15)
    a.r(0, 0, 0.8, 1.15, WHITE, EDGE, 0.05)
    a.r(0.36, 0.5, 0.08, 0.32, GLASS, None, 0.03)
    a.r(0.385, 0.62, 0.03, 0.08, BLUE, None)
    return a.e(0.4, 0.28, 0.016, 0.016, BLUE, None)


def audience():
    a = Art(1.3, 0.8)
    a.rs([(0.48, 0, 0.09, 0.14), (0.73, 0, 0.09, 0.14)], METAL, EDGE)
    a.r(0, 0.1, 1.3, 0.7, WHITE, EDGE, 0.16)
    return a.e(0.65, 0.45, 0.02, 0.02, BLUE, None)


def winged():
    """The U7 Industrial: a dark body with antenna panels on both sides."""
    a = Art(1.3, 0.9)
    a.p([(0, 0.2), (0.34, 0.12), (0.34, 0.8), (0, 0.88)], DARK, EDGE)
    a.p([(1.3, 0.2), (0.96, 0.12), (0.96, 0.8), (1.3, 0.88)], DARK, EDGE)
    a.r(0.36, 0, 0.58, 0.9, DARK, EDGE, 0.05)
    a.rs([(0.44, 0.2 + i * 0.1, 0.42, 0.03) for i in range(5)], "#5B6370", None)
    return a.e(0.65, 0.1, 0.018, 0.018, BLUE, None)


def stick(ants=2, vee=False):
    """A slim outdoor access point with antennas."""
    a = Art(0.7, 1.3)
    for i in range(ants):
        ax = 0.35 + (i - (ants - 1) / 2) * 0.16
        lean = (i - (ants - 1) / 2) * (0.5 if vee else 0)
        a.p([(ax - 0.022, 0.72), (ax + 0.022, 0.72), (ax + lean + 0.022, 1.3), (ax + lean - 0.022, 1.3)], WHITE, EDGE)
    a.r(0.24, 0, 0.22, 0.78, WHITE, EDGE, 0.06)
    return a.e(0.35, 0.22, 0.018, 0.018, BLUE, None)


def dish(d=1.0):
    a = Art(d, d + 0.18)
    a.r(d / 2 - 0.09, 0, 0.18, 0.3, METAL, EDGE, 0.02)
    a.e(d / 2, d / 2 + 0.18, d / 2)
    a.ring(d / 2, d / 2 + 0.18, d * 0.47, BLUE, 1.25)
    return a.e(d / 2, d / 2 + 0.18, 0.025, 0.025, BLUE, None)


def cloudkey(kind):
    if kind == "plus":
        a = Art(0.95, 0.42)
        a.r(0, 0, 0.95, 0.42, GLASS, EDGE, 0.05)
        a.r(0.08, 0.12, 0.26, 0.18, SCREEN, "#5B6370", 0.02)
        return a.r(0.14, 0.2, 0.14, 0.022, BLUE, None)
    a = Art(0.28, 1.0)
    a.r(0, 0, 0.28, 1.0, WHITE, EDGE, 0.06)
    if kind == "g2":
        lcd(a, 0.06, 0.72, 0.16, 0.16)
    else:
        a.r(0.125, 0.55, 0.03, 0.2, BLUE, None)
    return a


def travel(antenna=False):
    a = Art(0.62, 0.95 if antenna else 0.75)
    if antenna:
        a.r(0.08, 0.6, 0.46, 0.35, WHITE, EDGE, 0.04)
    a.r(0, 0, 0.62, 0.75, WHITE, EDGE, 0.08)
    lcd(a, 0.21, 0.3, 0.2, 0.26)
    return a


def darkbox(w=0.45, h=0.95, led=True, screen=False):
    """A black upright box: the UNAS towers, Display Cast, AI Port."""
    a = Art(w, h)
    a.r(0, 0, w, h, GLASS, EDGE, min(w, h) * 0.2)
    if screen:
        a.r(w * 0.2, h * 0.5, w * 0.6, h * 0.3, SCREEN, "#5B6370", 0.02)
        a.r(w * 0.32, h * 0.64, w * 0.36, 0.022, BLUE, None)
    if led:
        a.r(w / 2 - 0.06, 0.1, 0.12, 0.02, BLUE, None)
    return a


def cabinet():
    """A wall enclosure with its door open: the Enterprise Access Hub."""
    a = Art(1.2, 1.0)
    a.r(0, 0.03, 0.16, 0.94, SILVER, EDGE)
    a.r(0.14, 0, 1.06, 1.0, WHITE, EDGE, 0.02)
    a.r(0.22, 0.08, 0.9, 0.84, SILVER, EDGE)
    a.rs([(0.28 + c * 0.21, 0.5, 0.16, 0.34) for c in range(4)], WHITE, EDGE)
    a.rs([(0.28 + c * 0.21, 0.14, 0.16, 0.28) for c in range(4)], WHITE, EDGE)
    return a.rs([(0.3 + c * 0.21, 0.16, 0.12, 0.05) for c in range(4)], GREEN, None)


# ----------------------------------------------------------------- cameras

def bullet(big=False, dark=False, ring=False):
    """A bullet camera on its wall arm, seen from the side."""
    k = 1.2 if big else 1.0
    body = GLASS if dark else WHITE

    a = Art(1.25 * k, 0.72 * k)

    def s(*v):
        return [x * k for x in v]

    a.r(*s(0, 0.02, 0.07, 0.42), METAL, EDGE, 0.01)
    a.p([(0.07 * k, 0.18 * k), (0.07 * k, 0.3 * k), (0.42 * k, 0.5 * k), (0.5 * k, 0.4 * k)], METAL, EDGE)
    a.r(*s(0.24, 0.38, 0.9, 0.3), body, EDGE, 0.06 * k)
    a.r(*s(1.06, 0.4, 0.1, 0.26), GLASS, None, 0.03 * k)
    a.e(1.13 * k, 0.53 * k, 0.03 * k, 0.07 * k, LENS, None)
    if ring:
        a.r(*s(1.02, 0.385, 0.025, 0.29), BLUE, None)
    return a


def dome(mini=False, dark=False):
    w = 0.7 if mini else 0.9
    a = Art(w, w * 0.62)
    a.half(w / 2, w * 0.4, w * 0.36, w * 0.4, "#4B5563")
    a.lens(w / 2, w * 0.22, w * 0.1)
    return a.r(0, w * 0.4, w, w * 0.22, GLASS if dark else WHITE, EDGE, 0.04)


def turret(dark=False, ring=False):
    body = GLASS if dark else WHITE
    a = Art(0.85, 0.78)
    a.r(0.02, 0.62, 0.81, 0.16, body, EDGE, 0.04)
    a.half(0.425, 0.62, 0.36, 0.3, body)
    a.e(0.425, 0.33, 0.3, 0.3, body, EDGE)
    a.e(0.425, 0.31, 0.21, 0.21, GLASS, "#5B6370")
    if ring:
        a.ring(0.425, 0.31, 0.17, BLUE, 1.25)
    return a.lens(0.425, 0.31, 0.1)


def ptz(big=False, dark=False):
    k = 1.2 if big else 1.0
    a = Art(0.85 * k, 1.2 * k)
    a.r(0.3 * k, 1.05 * k, 0.25 * k, 0.15 * k, METAL, EDGE, 0.02)
    a.half(0.425 * k, 0.5 * k, 0.36 * k, 0.5 * k, "#4B5563")
    a.lens(0.425 * k, 0.26 * k, 0.12 * k)
    return a.r(0.02 * k, 0.48 * k, 0.81 * k, 0.6 * k, GLASS if dark else WHITE, EDGE, 0.1 * k)


def fisheye(d=0.85, dark=False):
    a = Art(d, d)
    a.e(d / 2, d / 2, d / 2, d / 2, GLASS if dark else WHITE, EDGE)
    a.e(d / 2, d / 2, d * 0.3, d * 0.3, GLASS, "#5B6370")
    return a.lens(d / 2, d / 2, d * 0.15)


def flexcam():
    a = Art(0.6, 0.85)
    a.e(0.3, 0.06, 0.24, 0.06, WHITE, EDGE)
    a.r(0.26, 0.06, 0.08, 0.3, METAL, EDGE)
    a.r(0.05, 0.33, 0.5, 0.5, WHITE, EDGE, 0.12)
    a.e(0.3, 0.58, 0.19, 0.19, GLASS, None)
    return a.lens(0.3, 0.58, 0.1)


def instant():
    a = Art(0.52, 0.9)
    a.r(0.06, 0, 0.4, 0.06, METAL, EDGE, 0.02)
    a.r(0, 0.05, 0.52, 0.85, WHITE, EDGE, 0.12)
    a.r(0.07, 0.38, 0.38, 0.45, GLASS, None, 0.09)
    a.lens(0.26, 0.62, 0.1)
    return a.e(0.26, 0.2, 0.02, 0.02, BLUE, None)


def doorbell(kind="std", white=False):
    """Doorbells and door-entry cameras. Kinds: lite, std, pro, entry."""
    w, h = {"lite": (0.3, 1.0), "entry": (0.34, 1.25)}.get(kind, (0.45, 1.2))
    a = Art(w, h)
    a.r(0, 0, w, h, WHITE if white else GLASS, EDGE, 0.08 if kind != "std" else w * 0.45)
    if white:
        a.r(0.05, h * 0.3, w - 0.1, h * 0.62, GLASS, None, 0.05)
    a.lens(w / 2, h - 0.2, min(0.09, w * 0.22))
    if kind == "pro":
        a.r(0.09, h * 0.38, w - 0.18, h * 0.24, SCREEN, "#5B6370", 0.02)
        a.r(0.14, h * 0.48, w - 0.28, 0.025, BLUE, None)
    a.ring(w / 2, 0.18, min(0.09, w * 0.24), BLUE, 1.5)
    return a


def multisensor(n=2, dark=False):
    w = 0.5 + n * 0.28
    a = Art(w, 0.62)
    for i in range(n):
        cx = w * (i + 0.5) / n
        a.half(cx, 0.36, 0.16, 0.34, "#4B5563")
        a.lens(cx, 0.2, 0.07)
    a.r(0, 0.34, w, 0.2, GLASS if dark else WHITE, EDGE, 0.05)
    return a.r(w / 2 - 0.12, 0.54, 0.24, 0.08, METAL, EDGE, 0.01)


def dslr():
    a = Art(1.2, 0.72)
    a.r(0, 0.02, 0.6, 0.6, GLASS, EDGE, 0.06)
    a.r(0.15, 0.62, 0.25, 0.1, GLASS, EDGE, 0.02)
    a.r(0.6, 0.1, 0.48, 0.44, GLASS, EDGE, 0.03)
    a.rs([(0.72, 0.1, 0.03, 0.44), (0.9, 0.1, 0.03, 0.44)], "#5B6370", None)
    a.r(1.0, 0.09, 0.025, 0.46, BLUE, None)
    return a.e(1.1, 0.32, 0.06, 0.2, LENS, None)


def theta():
    a = Art(1.1, 0.6)
    a.l([(0.3, 0.3), (0.5, 0.42), (0.7, 0.3)], EDGE, 1.25)
    a.r(0.64, 0.1, 0.46, 0.4, WHITE, EDGE, 0.06)
    a.e(0.72, 0.42, 0.018, 0.018, BLUE, None)
    a.e(0.17, 0.3, 0.17, 0.17, WHITE, EDGE)
    return a.lens(0.17, 0.3, 0.1)


def cam180(dark=True):
    a = Art(1.0, 0.5)
    a.r(0, 0, 1.0, 0.5, GLASS if dark else WHITE, EDGE, 0.2)
    a.r(0.1, 0.09, 0.8, 0.32, GLASS, "#5B6370", 0.14)
    a.lens(0.33, 0.25, 0.09)
    return a.lens(0.67, 0.25, 0.09)


def cube(w=0.5, dark=False):
    a = Art(w, w)
    a.r(0, 0, w, w, GLASS if dark else WHITE, EDGE, w * 0.2)
    a.e(w / 2, w / 2, w * 0.3, w * 0.3, GLASS, "#5B6370")
    return a.lens(w / 2, w / 2, w * 0.17)


# --------------------------------------------------- sensors and the rest

def grille(a, cx, cy, r, rings=((0.33, 6), (0.66, 12), (1.0, 18))):
    a.es([(cx + r * f * math.cos(math.radians(t)), cy + r * f * math.sin(math.radians(t))) for f, n in rings for t in range(0, 360, 360 // n)], 0.02, "#8E96A3")


def sensor(kind):
    a = Art(0.62, 0.62)
    if kind in ("bar", "motion", "glass"):
        a = Art(0.26, 1.0)
        a.r(0, 0, 0.26, 1.0, WHITE, EDGE, 0.1)
        if kind == "motion":
            a.r(0.05, 0.6, 0.16, 0.28, GREY, EDGE, 0.06)
        if kind == "glass":
            a.es([(0.13, 0.7 + i * 0.07) for i in range(3)], 0.018, "#8E96A3")
        a.e(0.13, 0.14, 0.016, 0.016, BLUE, None)
    elif kind == "entry":
        a = Art(0.42, 1.0)
        a.r(0, 0, 0.22, 1.0, WHITE, EDGE, 0.08)
        a.r(0.28, 0.1, 0.14, 0.5, WHITE, EDGE, 0.05)
        a.e(0.11, 0.86, 0.016, 0.016, BLUE, None)
    elif kind == "recessed":
        a.e(0.31, 0.31, 0.31)
        a.e(0.31, 0.31, 0.2, 0.2, WHITE, EDGE)
        a.r(0.19, 0.29, 0.24, 0.04, GREY, EDGE, 0.015)
    elif kind == "smoke":
        a.e(0.31, 0.31, 0.31)
        a.ring(0.31, 0.31, 0.22, GREY, 2.0)
        a.e(0.31, 0.31, 0.1, 0.1, WHITE, EDGE)
        a.e(0.31, 0.31, 0.02, 0.02, BLUE, None)
    elif kind == "env":
        a = Art(0.9, 0.6)
        a.r(0, 0, 0.9, 0.6, WHITE, EDGE, 0.1)
        a.es([(0.3 + i * 0.1, 0.25) for i in range(4)], 0.018, BLUE)
        a.r(0.38, 0.03, 0.14, 0.06, GREY, EDGE, 0.02)
    elif kind == "air":
        a = Art(0.8, 0.62)
        a.r(0.04, 0, 0.72, 0.2, WHITE, EDGE, 0.08)
        a.r(0, 0.14, 0.8, 0.48, WHITE, EDGE, 0.16)
        a.r(0.02, 0.2, 0.76, 0.02, BLUE, None)
    elif kind == "fob":
        a = Art(0.5, 0.9)
        a.r(0, 0, 0.5, 0.9, WHITE, EDGE, 0.24)
        a.es([(0.17, 0.3), (0.33, 0.3), (0.17, 0.6), (0.33, 0.6)], 0.065, SILVER, EDGE)
        a.e(0.25, 0.45, 0.018, 0.018, BLUE, None)
    elif kind == "pocket":
        a.ring(0.31, 0.5, 0.1, METAL, 1.5)
        a.e(0.31, 0.26, 0.26)
        a.e(0.31, 0.26, 0.02, 0.02, BLUE, None)
    elif kind == "button":
        a = Art(0.45, 0.9)
        a.r(0, 0, 0.45, 0.9, WHITE, EDGE, 0.2)
        a.e(0.225, 0.3, 0.15, 0.15, SILVER, EDGE)
        a.e(0.225, 0.72, 0.016, 0.016, BLUE, None)
    elif kind == "relay":
        a = Art(0.8, 0.7)
        a.r(0, 0, 0.8, 0.7, WHITE, EDGE, 0.05)
        a.rs([(0.08 + i * 0.11, 0.06, 0.085, 0.12) for i in range(6)], GREY, EDGE)
        a.es([(0.25, 0.52), (0.55, 0.52)], 0.016, BLUE)
    elif kind == "siren":
        a.r(0, 0, 0.62, 0.62, WHITE, EDGE, 0.16)
        a.es([(0.13 + i * 0.09, 0.13 + j * 0.09) for i in range(5) for j in range(5)], 0.022, "#B4BAC3")
    elif kind == "gateway":
        a = Art(0.5, 1.2)
        a.r(0.225, 0.5, 0.05, 0.7, WHITE, EDGE, 0.02)
        a.r(0, 0, 0.5, 0.62, WHITE, EDGE, 0.06)
        a.e(0.25, 0.4, 0.02, 0.02, BLUE, None)
    elif kind == "chime":
        a.e(0.31, 0.31, 0.31, 0.31, SILVER, EDGE)
        grille(a, 0.31, 0.31, 0.25)
        a.e(0.31, 0.31, 0.04, 0.04, WHITE, EDGE)
    elif kind == "key":
        a = Art(1.1, 0.3)
        a.r(0, 0, 1.1, 0.3, SILVER, EDGE, 0.04)
        a.r(0.07, 0.06, 0.22, 0.18, GLASS, None, 0.02)
        a.es([(0.12 + i * 0.06, 0.15) for i in range(3)], 0.016, BLUE)
    elif kind == "enhancer":
        a.e(0.31, 0.31, 0.31)
        a.e(0.31, 0.31, 0.17, 0.17, SILVER, EDGE)
        a.es([(0.31 + 0.24 * math.cos(math.radians(t)), 0.31 + 0.24 * math.sin(math.radians(t))) for t in range(0, 360, 45)], 0.026, "#8E96A3")
    elif kind == "lock":
        a = Art(0.85, 0.85)
        a.e(0.425, 0.425, 0.425)
        a.ring(0.425, 0.425, 0.34, BLUE, 1.25)
        a.e(0.425, 0.425, 0.27, 0.27, WHITE, EDGE)
        a.e(0.425, 0.425, 0.03, 0.03, BLUE, None)
    elif kind == "disc":
        a.e(0.31, 0.31, 0.31)
        a.e(0.31, 0.31, 0.13, 0.13, SILVER, EDGE)
    elif kind == "bulb":
        a = Art(0.55, 0.95)
        a.r(0.17, 0, 0.21, 0.26, METAL, EDGE, 0.03)
        a.e(0.275, 0.62, 0.275, 0.32, "#FFF3C4", AMBER)
    return a


def floodlight():
    a = Art(0.55, 1.0)
    a.r(0.2, 0, 0.15, 0.2, GLASS, EDGE)
    a.r(0, 0.12, 0.55, 0.88, GLASS, EDGE, 0.24)
    return a.es([(0.155 + i * 0.08, 0.5 + j * 0.08) for i in range(4) for j in range(5)], 0.028, "#FFF3C4")


def speaker(kind):
    if kind == "horn":
        a = Art(1.0, 0.75)
        a.r(0, 0.2, 0.07, 0.35, METAL, EDGE, 0.01)
        a.r(0.07, 0.3, 0.3, 0.16, WHITE, EDGE)
        a.p([(0.35, 0.27), (0.35, 0.49), (0.95, 0.75), (0.95, 0.0)], WHITE, EDGE)
        return a.e(0.95, 0.375, 0.05, 0.375, GREY, EDGE)
    if kind in ("wall", "ai"):
        w, h = (0.7, 1.0) if kind == "wall" else (0.6, 0.85)
        a = Art(w, h)
        a.r(0, 0, w, h, SILVER if kind == "wall" else WHITE, EDGE, 0.03 if kind == "wall" else 0.12)
        a.es([(0.1 + i * (w - 0.2) / 4, 0.12 + j * (h - 0.24) / 7) for i in range(5) for j in range(8)], 0.024, "#B4BAC3")
        return a
    a = Art(0.9, 0.9)
    a.e(0.45, 0.45, 0.45)
    a.e(0.45, 0.45, 0.38, 0.38, SILVER, EDGE)
    grille(a, 0.45, 0.45, 0.3)
    return a


def reader(kind="std", white=True):
    """Door readers. Kinds: std, slim, pro, keypad, flex, lite, round."""
    if kind == "round":
        a = Art(0.9, 0.9)
        a.e(0.45, 0.45, 0.45, 0.45, SILVER, EDGE)
        a.e(0.45, 0.45, 0.36, 0.36, SCREEN, None)
        a.rs([(0.3, 0.5, 0.3, 0.035), (0.3, 0.4, 0.2, 0.025)], BLUE, None)
        return a
    w, h = {"lite": (0.42, 0.85), "flex": (0.75, 0.75), "slim": (0.3, 1.1)}.get(kind, (0.46, 1.15))
    a = Art(w, h)
    a.r(0, 0, w, h, WHITE if white else GLASS, EDGE, w * 0.45 if kind == "lite" else 0.07)
    dots = "#B4BAC3" if white else "#6B7280"
    if kind == "pro":
        a.lens(w / 2, h - 0.1, 0.035)
        a.r(0.05, h * 0.3, w - 0.1, h * 0.52, SCREEN, "#5B6370", 0.02)
        a.rs([(0.11, h * 0.62, w - 0.22, 0.03), (0.11, h * 0.54, w * 0.3, 0.022)], BLUE, None)
    elif kind == "keypad":
        a.es([(w / 2 + (i - 1) * 0.11, h * 0.5 + j * 0.11) for i in range(3) for j in range(4)], 0.03, dots)
        a.ring(w / 2, h * 0.28, 0.07, METAL, 1.25)
    elif kind == "flex":
        a.es([(w / 2 + (i - 1) * 0.16, 0.36 + j * 0.13) for i in range(3) for j in range(3)], 0.028, dots)
    a.r(w * 0.3, 0.07, w * 0.4, 0.022, BLUE, None)
    return a


def accesshub(w=1.0, h=1.0, sides=True):
    """A door hub: a white box with its terminal blocks along the sides."""
    a = Art(w, h)
    a.r(0, 0, w, h, WHITE, EDGE, 0.05)
    if sides:
        n = int((h - 0.2) / 0.09)
        a.rs([(x, 0.1 + i * 0.09, 0.1, 0.07) for x in (0.06, w - 0.16) for i in range(n)], GREY, EDGE)
    else:
        n = int((w - 0.16) / 0.09)
        a.rs([(0.08 + i * 0.09, 0.06, 0.07, 0.1) for i in range(n)], GREY, EDGE)
    a.es([(w / 2 - 0.06, h * 0.62), (w / 2 + 0.06, h * 0.62)], 0.016, BLUE)
    return a.r(w / 2 - 0.05, 0.1 if sides else h * 0.3, 0.1, 0.09, PORT, None)


def intercom():
    a = Art(0.48, 1.3)
    a.r(0, 0, 0.48, 1.3, GLASS, EDGE, 0.06)
    a.lens(0.24, 1.2, 0.04)
    a.r(0.05, 0.62, 0.38, 0.48, SCREEN, "#5B6370", 0.02)
    a.rs([(0.1, 0.92, 0.2, 0.03), (0.1, 0.84, 0.28, 0.022)], BLUE, None)
    return a.es([(0.24 + (i - 1) * 0.11, 0.12 + j * 0.11) for i in range(3) for j in range(4)], 0.03, "#6B7280")


def tablet(w=1.0, h=0.7, stand=True, white=False):
    """A screen: a display, a viewer or a wall panel."""
    foot = 0.14 if stand else 0
    a = Art(w, h + foot)
    if stand:
        a.r(w / 2 - 0.05, 0.03, 0.1, 0.14, METAL, EDGE)
        a.r(w * 0.3, 0, w * 0.4, 0.04, METAL, EDGE, 0.015)
    a.r(0, foot, w, h, WHITE if white else GLASS, EDGE, 0.05)
    a.r(0.045, foot + 0.045, w - 0.09, h - 0.09, SCREEN, None, 0.02)
    a.rs([(0.1, foot + h - 0.17, w * 0.35, 0.035), (0.1, foot + h - 0.25, w * 0.5, 0.025)], BLUE, None)
    return a


def card():
    a = Art(0.86, 0.54)
    a.r(0, 0, 0.86, 0.54, GLASS, EDGE, 0.05)
    return a.waves(0.3, 0.27, 0.16, mid=0, n=3)


def phone(kind="touch", white=False):
    """Desk phones. Kinds: keys, touch, max."""
    body = WHITE if white else GLASS
    w = 1.25 if kind == "max" else 1.05
    a = Art(w, 0.85)
    a.p([(0.06, 0), (w - 0.04, 0), (w, 0.62), (0.28, 0.62)], body, EDGE)
    a.r(0, 0.05, 0.26, 0.76, body, EDGE, 0.1)
    if kind == "keys":
        a.r(0.38, 0.48, w - 0.5, 0.3, SCREEN, "#5B6370", 0.02)
        a.r(0.44, 0.66, 0.2, 0.025, BLUE, None)
        a.es([(0.46 + i * 0.12, 0.1 + j * 0.09) for i in range(3) for j in range(4)], 0.025, "#8E96A3")
    else:
        a.r(0.36, 0.14, w - 0.44, 0.68, SCREEN, "#5B6370", 0.03)
        a.rs([(0.43, 0.66, 0.26, 0.035), (0.43, 0.58, 0.4, 0.025)], BLUE, None)
    return a


def dimmer():
    a = Art(0.62, 0.95)
    a.r(0, 0, 0.62, 0.95, WHITE, EDGE, 0.04)
    return a.add([Art._box(0.19, 0.2, 0.24, 0.55)], None, BLUE, 1.25, 0.02)


def ledpanel():
    a = Art(1.0, 1.0)
    a.r(0, 0, 1.0, 1.0, SILVER, EDGE, 0.02)
    return a.r(0.05, 0.05, 0.9, 0.9, "#FFFFFF", SOFT)


def evstation(pro=False):
    a = Art(0.7, 1.3)
    a.r(0, 0, 0.7, 1.3, WHITE if pro else GLASS, EDGE, 0.1)
    if pro:
        a.r(0.06, 0.3, 0.58, 0.92, SCREEN, None, 0.06)
        a.rs([(0.16, 0.9, 0.3, 0.04), (0.16, 0.8, 0.2, 0.03)], BLUE, None)
    else:
        lcd(a, 0.22, 0.8, 0.26, 0.2)
    return a.e(0.35, 0.14, 0.02, 0.02, BLUE, None)


def plug(n=1):
    if n == 1:
        a = Art(0.6, 0.6)
        a.e(0.3, 0.3, 0.3)
        a.e(0.3, 0.3, 0.17, 0.17, SOFT, EDGE)
        a.es([(0.25, 0.32), (0.35, 0.32), (0.3, 0.24)], 0.016, DARK)
        return a
    a = Art(1.2, 0.6)
    a.r(0, 0, 1.2, 0.6, WHITE, EDGE, 0.08)
    for i in range(n):
        cx, cy = 0.42 + (i % 3) * 0.3, 0.44 - (i // 3) * 0.28
        a.e(cx, cy, 0.1, 0.1, SOFT, EDGE)
        a.es([(cx - 0.035, cy), (cx + 0.035, cy)], 0.014, DARK)
    return a.e(0.12, 0.3, 0.018, 0.018, BLUE, None)


def pduhd():
    a = Art(0.3, 2.6)
    a.r(0, 0, 0.3, 2.6, SILVER, EDGE, 0.02)
    lcd(a, 0.07, 2.32, 0.16, 0.16)
    return a.rs([(0.08, 0.1 + i * 0.09, 0.14, 0.07) for i in range(24)], GLASS, None, 0.01)


def tower():
    a = Art(0.5, 1.25)
    a.r(0, 0, 0.5, 1.25, WHITE, EDGE, 0.05)
    lcd(a, 0.16, 0.95, 0.18, 0.18)
    return a.l([(0.06, 0.1), (0.44, 0.1)], SOFT, 0.5)


def router(ants=2, dark=False, screen=True):
    """A mobile router with its antennas."""
    a = Art(0.9, 1.15)
    for i in range(ants):
        ax = 0.45 + (i - (ants - 1) / 2) * 0.2
        lean = (i - (ants - 1) / 2) * (0.5 if ants == 2 and not dark else 0)
        a.p([(ax - 0.025, 0.4), (ax + 0.025, 0.4), (ax + lean + 0.025, 1.15), (ax + lean - 0.025, 1.15)], GLASS if dark else WHITE, EDGE)
    a.r(0.18, 0, 0.54, 0.5, GLASS if dark else WHITE, EDGE, 0.05)
    if screen:
        lcd(a, 0.37, 0.17, 0.16, 0.16)
    else:
        a.e(0.45, 0.25, 0.018, 0.018, BLUE, None)
    return a


def wizard():
    a = Art(0.55, 1.0)
    a.r(0, 0, 0.55, 1.0, GLASS, EDGE, 0.06)
    a.r(0.1, 0.4, 0.35, 0.4, SCREEN, "#5B6370", 0.02)
    return a.rs([(0.16, 0.64, 0.2, 0.03), (0.16, 0.56, 0.14, 0.022)], BLUE, None)


# --------------------------------------------------------------- catalogue

def S(name, sku, *groups, **k):
    return (name, sku, rack(groups, **k))


def D(name, sku, rj=0, sfp=0, **k):
    return (name, sku, desk(rj, sfp, **k))


def rj(n, rows=2):
    return ("rj", n, rows)


def lit(n, rows=2):
    return ("lit", n, rows)


def sfp(n, rows=2):
    return ("sfp", n, rows)


def q(n, rows=2):
    return ("q", n, rows)


GATEWAYS = [
    S("Enterprise Firewall Core", "EF-Core", rj(10), sfp(4), q(4), q(1, 1), u=2),
    S("Enterprise Firewall", "EFG", rj(2), sfp(4)),
    S("Gateway Enterprise", "UXG-Enterprise", rj(2), sfp(4)),
    S("Dream Machine Beast", "UDM-Beast", rj(10), sfp(4), bays=2),
    S("Dream Machine Pro Max", "UDM-Pro-Max", rj(8), rj(1, 1), sfp(2), bays=2),
    S("Dream Machine Pro", "UDM-Pro", rj(8), rj(1, 1), sfp(2), bays=1),
    S("Dream Machine Special Edition", "UDM-SE", rj(8), rj(1, 1), sfp(2), bays=1),
    S("Gateway Pro", "UXG-Pro", rj(2), sfp(2)),
    ("Dream Machine", "UDM", capsule(0.62, 1.0)),
    ("Dream Router 7", "UDR7", capsule(0.62, 0.95, "pill")),
    ("Dream Router 5G Max", "UDR-5G-Max", capsule(0.5, 1.25, "tall")),
    ("Dream Router", "UDR", capsule(0.62, 1.0, "pill")),
    ("Dream Wall", "UDW", dreamwall()),
    ("Express 7", "UX7", flatbox(0.8, 0.5)),
    ("Express", "UX", flatbox(0.75, 0.36)),
    ("Cloud Gateway Fiber", "UCG-Fiber", flatbox(1.4, 0.26)),
    ("Cloud Gateway Max", "UCG-Max", flatbox(1.2, 0.32)),
    ("Cloud Gateway Ultra", "UCG-Ultra", flatbox(1.2, 0.26)),
    D("Cloud Gateway Industrial", "UCG-Industrial", 4, 2, dark=True),
    ("Gateway Fiber", "UXG-Fiber", flatbox(1.4, 0.26, "dot")),
    ("Gateway Max", "UXG-Max", flatbox(1.2, 0.3, "dot")),
    ("Gateway Lite", "UXG-Lite", flatbox(1.0, 0.36, "dot")),
    D("Security Gateway", "USG-3P", 4, w=1.2),
    S("Security Gateway Pro", "USG-PRO-4", rj(1, 1), rj(4, 1), sfp(2, 1), screen="led"),
    S("Security Gateway XG 8", "USG-XG-8", sfp(8), rj(1, 1), screen="led", panel=True),
    S("CloudKey Enterprise", "CK-Enterprise", rj(1, 1), sfp(2, 1)),
    ("CloudKey+", "UCK-G2-PLUS", cloudkey("plus")),
    ("CloudKey+ SSD", "UCK-G2-SSD", cloudkey("plus")),
    ("CloudKey Gen2", "UCK-G2", cloudkey("g2")),
    ("CloudKey Gen1", "UC-CK", cloudkey("g1")),
    S("Application Server XG", "UAS-XG", screen="led", bays=2, vents=True),
    ("Cable Internet", "UCI", flatbox(1.5, 0.22, "dot")),
    ("Travel Router", "UTR", travel()),
    ("Travel Router Long-Range", "UTR-LR", travel(antenna=True)),
]

SWITCHES = [
    S("Switch Enterprise Campus Core", "ECS-Core", *[q(4)] * 8),
    S("Switch Enterprise Campus Aggregation", "ECS-Aggregation", sfp(48), q(6)),
    S("Switch Enterprise Campus 48S PoE", "ECS-48S-PoE", lit(48), sfp(4), q(2)),
    S("Switch Enterprise Campus 48S", "ECS-48S", lit(48), sfp(4), q(2)),
    S("Switch Enterprise Campus 48 PoE", "ECS-48-PoE", lit(48), sfp(4)),
    S("Switch Enterprise Campus 24S PoE", "ECS-24S-PoE", lit(24, 1), sfp(4), q(2)),
    S("Switch Enterprise Campus 24S", "ECS-24S", lit(24, 1), sfp(4), q(2)),
    S("Switch Enterprise Campus 24 PoE", "ECS-24-PoE", lit(24, 1), sfp(2, 1)),
    S("Switch Enterprise AV XG 24 PoE", "EAV-XG-24-PoE", lit(24, 1), sfp(4), dark=True),
    S("Switch Enterprise AV Fiber", "EAV-Fiber", sfp(20, 1), q(2, 1), dark=True),
    S("Switch Leaf", "USW-Leaf", sfp(48), q(6)),
    S("Switch Pro XG Aggregation", "USW-Pro-XG-Aggregation", sfp(32)),
    S("Switch Pro Aggregation", "USW-Pro-Aggregation", sfp(28), sfp(4)),
    S("Switch Aggregation", "USW-Aggregation", sfp(8)),
    S("Switch Pro XG 48 PoE", "USW-Pro-XG-48-PoE", lit(48), sfp(4)),
    S("Switch Pro XG 48", "USW-Pro-XG-48", lit(48), sfp(4)),
    S("Switch Pro XG 24 PoE", "USW-Pro-XG-24-PoE", lit(24, 1), sfp(2, 1)),
    S("Switch Pro XG 24", "USW-Pro-XG-24", lit(24, 1), sfp(2, 1)),
    S("Switch Pro XG 10 PoE", "USW-Pro-XG-10-PoE", lit(10, 1), sfp(2, 1)),
    D("Switch Pro XG 8 PoE", "USW-Pro-XG-8-PoE", 8, 2, screen=True, lit=True),
    S("Switch Pro HD 24 PoE", "USW-Pro-HD-24-PoE", lit(24, 1), sfp(4)),
    S("Switch Pro HD 24", "USW-Pro-HD-24", lit(24, 1), sfp(4)),
    S("Switch Pro Max 48 PoE", "USW-Pro-Max-48-PoE", lit(48), sfp(4)),
    S("Switch Pro Max 48", "USW-Pro-Max-48", lit(48), sfp(4)),
    S("Switch Pro Max 24 PoE", "USW-Pro-Max-24-PoE", lit(24, 1), sfp(2, 1)),
    S("Switch Pro Max 24", "USW-Pro-Max-24", lit(24, 1), sfp(2, 1)),
    S("Switch Pro Max 16 PoE", "USW-Pro-Max-16-PoE", lit(16, 1), sfp(2, 1), w=2.2),
    S("Switch Pro Max 16", "USW-Pro-Max-16", lit(16, 1), sfp(2, 1), w=2.2),
    S("Switch Pro 48 PoE", "USW-Pro-48-PoE", rj(48), sfp(4)),
    S("Switch Pro 48", "USW-Pro-48", rj(48), sfp(4)),
    S("Switch Pro 24 PoE", "USW-Pro-24-PoE", rj(24), sfp(2)),
    S("Switch Pro 24", "USW-Pro-24", rj(24), sfp(2)),
    D("Switch Pro 8 PoE", "USW-Pro-8-PoE", 8, 2, screen=True),
    S("Switch EnterpriseXG 24", "USW-EnterpriseXG-24", rj(24, 1), sfp(2, 1)),
    S("Switch Enterprise 48 PoE", "USW-Enterprise-48-PoE", rj(48), sfp(4)),
    S("Switch Enterprise 24 PoE", "USW-Enterprise-24-PoE", rj(24, 1), sfp(2, 1)),
    D("Switch Enterprise 8 PoE", "USW-Enterprise-8-PoE", 8, 2, screen=True),
    S("Switch 48 PoE", "USW-48-PoE", rj(48), sfp(4, 1)),
    S("Switch 48", "USW-48", rj(48), sfp(4, 1)),
    S("Switch 24 PoE", "USW-24-PoE", rj(24), sfp(2, 1)),
    S("Switch 24", "USW-24", rj(24), sfp(2, 1)),
    S("Switch 16 PoE", "USW-16-PoE", rj(16), sfp(2, 1)),
    D("Switch Lite 16 PoE", "USW-Lite-16-PoE", 16, rows=2),
    D("Switch Lite 8 PoE", "USW-Lite-8-PoE", 8),
    D("Switch Ultra 210W", "USW-Ultra-210W", 8, split=1),
    D("Switch Ultra 60W", "USW-Ultra-60W", 8, split=1),
    D("Switch Ultra", "USW-Ultra", 8, split=1),
    D("Switch Flex 2.5G 8 PoE", "USW-Flex-2.5G-8-PoE", 9, 1, split=8),
    D("Switch Flex 2.5G 8", "USW-Flex-2.5G-8", 9, 1, split=8),
    D("Switch Flex 2.5G 5", "USW-Flex-2.5G-5", 5),
    D("Switch Flex XG", "USW-Flex-XG", 5, split=1),
    D("Switch Flex Mini", "USW-Flex-Mini", 5),
    D("Switch Flex", "USW-Flex", 5),
    D("Switch Industrial", "USW-Industrial", 8, 2, dark=True, led="square"),
    ("Switch Industrial DIN 2.5G 8 PoE", "USW-Industrial-DIN-2.5G-8-PoE", dinbox()),
    ("Switch Industrial DIN 8 PoE", "USW-Industrial-DIN-8-PoE", dinbox()),
    ("Switch Industrial DIN 8", "USW-Industrial-DIN-8", dinbox()),
    S("Switch Mission Critical", "USW-Mission-Critical", rj(8, 1), sfp(2, 1), w=2.2),
    S("Switch LR 8 PoE", "USW-LR-Switch-8-PoE", rj(8, 1), rj(1, 1), sfp(1, 1), w=2.0),
    S("Switch WAN Relay SFP+", "USW-WAN", sfp(2, 1), sfp(1, 1), rj(1, 1)),
    S("Switch WAN Relay RJ45", "USW-WAN-RJ45", rj(2, 1), rj(1, 1), rj(1, 1)),
    D("Device Bridge Switch", "UDB-Switch", 8),
    S("Switch XG 16", "US-16-XG", sfp(12), rj(4, 1), screen="led"),
    D("Switch XG 6 PoE", "US-XG-6PoE", 4, 2, led="square"),
    S("Switch L2 48 PoE", "US-L2-48-PoE", rj(48), sfp(2, 1), sfp(2, 1), screen="led"),
    S("Switch L2 24 PoE", "US-L2-24-PoE", rj(24), sfp(2, 1), screen="led"),
    S("Switch 48 PoE 750W", "US-48-750W", rj(48), sfp(2, 1), sfp(2, 1), screen="led"),
    S("Switch 48 PoE 500W", "US-48-500W", rj(48), sfp(2, 1), sfp(2, 1), screen="led"),
    S("Switch 48 Gen1", "US-48-G1", rj(48), sfp(2, 1), sfp(2, 1), screen="led"),
    S("Switch 24 PoE 500W", "US-24-500W", rj(24), sfp(2, 1), screen="led"),
    S("Switch 24 PoE 250W", "US-24-250W", rj(24), sfp(2, 1), screen="led"),
    S("Switch 24 Gen1", "US-24-G1", rj(24), sfp(2, 1), screen="led"),
    S("Switch 16 PoE 150W", "US-16-150W", rj(16), sfp(2, 1), screen="led"),
    D("Switch 8 PoE 150W", "US-8-150W", 8, 2, led="square"),
    D("Switch 8 PoE 60W", "US-8-60W", 8, led="square"),
    D("Switch 8", "US-8", 8, led="square"),
]

WIFI = [
    ("E7", "E7", disc(1.1, square=True)),
    ("E7 Campus", "E7-Campus", disc(1.1, square=True)),
    ("E7 Campus Indoor", "E7-Campus-Indoor", disc(1.1, square=True)),
    ("E7 Audience", "E7-Audience", audience()),
    ("E7 Audience Indoor", "E7-Audience-Indoor", audience()),
    ("U7 Pro XGS", "U7-Pro-XGS", disc(1.05, 0.3)),
    ("U7 Pro XG", "U7-Pro-XG", disc(1.0, 0.3)),
    ("U7 Pro XG Wall", "U7-Pro-XG-Wall", plate(0.6, 1.1, "top")),
    ("U7 Pro Max", "U7-Pro-Max", disc(1.05, 0.3)),
    ("U7 Pro", "U7-Pro", disc(1.0, 0.3)),
    ("U7 Pro Wall", "U7-Pro-Wall", plate(0.7, 1.05, "ring")),
    ("U7 Pro Outdoor", "U7-Pro-Outdoor", plate(0.85, 0.95, "dot", rad=0.16)),
    ("U7 Long-Range", "U7-LR", disc(0.95, 0.3)),
    ("U7 Lite", "U7-Lite", disc(0.85, 0.32)),
    ("U7 In-Wall", "U7-IW", plate(0.65, 0.95, "dot", rad=0.12)),
    ("U7 Outdoor", "U7-Outdoor", plate(0.8, 0.95, "dot", rad=0.16)),
    ("U7 Mesh", "U7-Mesh", tube(0.3, 1.1, "top")),
    ("U7 Industrial", "U7-Industrial", winged()),
    ("U6 Enterprise", "U6-Enterprise", disc(1.05, 0.3)),
    ("U6 Enterprise In-Wall", "U6-Enterprise-IW", plate(0.75, 1.0, "ring", rad=0.05)),
    ("U6 Pro", "U6-Pro", disc(1.0, 0.3)),
    ("U6 Long-Range", "U6-LR", disc(1.1, 0.28)),
    ("U6 Long-Range+", "U6-PLUS-LR", disc(1.0, 0.3)),
    ("U6+", "U6+", disc(0.85, 0.32)),
    ("U6 Lite", "U6-Lite", disc(0.85, 0.32)),
    ("U6 In-Wall", "U6-IW", plate(0.65, 1.0, "ring", rad=0.05)),
    ("U6 Mesh Pro", "U6-Mesh-Pro", plate(0.5, 1.15, "bottom")),
    ("U6 Mesh", "U6-Mesh", tube(0.3, 1.1, "bottom")),
    ("U6 Extender", "U6-Extender", plate(0.6, 0.9, "ring", rad=0.2)),
    ("AC HD", "UAP-AC-HD", disc(1.1, 0.3)),
    ("AC SHD", "UAP-AC-SHD", disc(1.1, 0.3)),
    ("AC Pro", "UAP-AC-Pro", disc(1.0, 0.3)),
    ("AC Long-Range", "UAP-AC-LR", disc(0.95, 0.3)),
    ("AC Lite", "UAP-AC-LITE", disc(0.85, 0.32)),
    ("Nano HD", "UAP-nanoHD", disc(0.85, 0.32)),
    ("AC EDU", "UAP-AC-EDU", disc(1.15, 0.5)),
    ("AC In-Wall Pro", "UAP-AC-IW-Pro", plate(0.6, 1.1, "top", rad=0.05)),
    ("AC In-Wall", "UAP-AC-IW", plate(0.5, 1.1, "top", rad=0.05)),
    ("In-Wall HD", "UAP-IW-HD", plate(0.65, 1.0, "ring", rad=0.05)),
    ("In-Wall", "UAP-IW", plate(0.62, 1.0, "top", ports=2, rad=0.05)),
    ("FlexHD", "UAP-FlexHD", tube(0.32, 1.05, None)),
    ("BeaconHD", "UAP-BeaconHD", plate(0.6, 0.9, "ring", rad=0.2)),
    ("AC Mesh Pro", "UAP-AC-M-PRO", plate(0.6, 1.05, "bottom", rad=0.05)),
    ("AC Mesh", "UAP-AC-M", stick(2, vee=True)),
    ("AC Outdoor", "UAP-AC-Outdoor", plate(0.6, 1.05, "bottom", rad=0.05)),
    ("Access Point XG", "UAP-XG", disc(1.2, 0.26)),
    ("WiFi BaseStation XG", "UWB-XG", audience()),
    ("Access Point AC", "UAP-AC", disc(1.0, 0.3)),
    ("Access Point Pro", "UAP-Pro", disc(1.0, 0.3)),
    ("Access Point Long-Range", "UAP-LR", disc(1.0, 0.3, color=GREEN)),
    ("Access Point", "UAP", disc(0.95, 0.3, color=GREEN)),
    ("Outdoor+", "UAP-Outdoor+", stick(2)),
    ("Outdoor 5", "UAP-Outdoor-5", stick(2)),
    ("Outdoor", "UAP-Outdoor", stick(2)),
    ("Swiss Army Knife", "UK-Ultra", plate(0.55, 0.95, "ring", rad=0.2)),
    ("Building Bridge XG", "UBB-XG", dish(1.15)),
    ("Building Bridge", "UBB", dish(1.0)),
    ("Device Bridge Pro Sector", "UDB-Pro-Sector", plate(0.36, 1.2, "bottom", rad=0.12)),
    ("Device Bridge Pro", "UDB-Pro", disc(0.85, 0.2)),
    ("Device Bridge", "UDB", plate(0.5, 0.95, "dot", rad=0.14)),
    ("Device Bridge IoT", "UDB-IoT", plate(0.45, 0.6, "dot", rad=0.06)),
    ("EAV Bridge", "EAVBRIDGE", flatbox(1.3, 0.4, "lcd", dark=True)),
    ("AirWire", "U-AirWire", flatbox(1.0, 0.6, "dot", dark=True)),
    ("Mesh Dual-Band Antenna", "UMA-D", plate(0.5, 1.1, None, rad=0.06)),
]

CAMERAS = [
    ("AI Pro", "UVC-AI-Pro", bullet(big=True, dark=True, ring=True)),
    ("AI Bullet", "UVC-AI-Bullet", bullet(dark=True, ring=True)),
    ("AI LPR", "UVC-AI-LPR", bullet(big=True, dark=True, ring=True)),
    ("AI DSLR", "UVC-AI-DSLR", dslr()),
    ("AI Dome", "UVC-AI-Dome", dome()),
    ("AI Turret", "UVC-AI-Turret", turret(ring=True)),
    ("AI 360", "UVC-AI-360", fisheye(dark=True)),
    ("AI Theta", "UVC-AI-Theta", theta()),
    ("AI MS 4", "UVC-AI-MS-4", multisensor(4, dark=True)),
    ("AI MS 2", "UVC-AI-MS-2", multisensor(2)),
    ("AI PTZ Precision", "UVC-AI-PTZ-Precision", ptz(big=True, dark=True)),
    ("AI PTZ Industrial", "UVC-AI-PTZ", ptz(big=True)),
    ("G6 Pro Bullet", "UVC-G6-Pro-Bullet", bullet(big=True, ring=True)),
    ("G6 Pro Dome", "UVC-G6-Pro-Dome", dome()),
    ("G6 Pro Turret", "UVC-G6-Pro-Turret", turret(ring=True)),
    ("G6 Pro 360", "UVC-G6-Pro-360", fisheye()),
    ("G6 Pro Entry", "UVC-G6-Pro-Entry", doorbell("entry")),
    ("G6 Entry", "UVC-G6-Entry", doorbell("entry")),
    ("G6 Bullet", "UVC-G6-Bullet", bullet(ring=True)),
    ("G6 Dome", "UVC-G6-Dome", dome()),
    ("G6 Mini Dome", "UVC-G6-Mini-Dome", dome(mini=True)),
    ("G6 Turret", "UVC-G6-Turret", turret()),
    ("G6 180", "UVC-G6-180", cam180()),
    ("G6 PTZ", "UVC-G6-PTZ", ptz()),
    ("G6 Instant", "UVC-G6-INS", instant()),
    ("G6 Edge Bullet", "UVC-G6-Edge-Bullet", bullet(ring=True)),
    ("G6 Edge Dome", "UVC-G6-Edge-Dome", dome()),
    ("G6 Edge Turret", "UVC-G6-Edge-Turret", turret(ring=True)),
    ("G5 Pro", "UVC-G5-Pro", bullet(big=True, ring=True)),
    ("G5 Bullet", "UVC-G5-Bullet", bullet()),
    ("G5 Dome", "UVC-G5-Dome", dome()),
    ("G5 Dome Ultra", "UVC-G5-Dome-Ultra", dome(mini=True)),
    ("G5 Turret Ultra", "UVC-G5-Turret-Ultra", turret()),
    ("G5 Flex", "UVC-G5-Flex", flexcam()),
    ("G5 PTZ", "UVC-G5-PTZ", ptz()),
    ("G4 Pro", "UVC-G4-PRO", bullet(big=True, ring=True)),
    ("G4 Bullet", "UVC-G4-Bullet", bullet()),
    ("G4 Dome", "UVC-G4-Dome", dome()),
    ("G4 Instant", "UVC-G4-INS", instant()),
    ("G4 PTZ", "UVC-G4-PTZ", ptz(big=True, dark=True)),
    ("G4 Doorbell Pro PoE", "UVC-G4-Doorbell-Pro-PoE", doorbell("pro", white=True)),
    ("G4 Doorbell Pro", "UVC-G4-Doorbell-Pro", doorbell("pro")),
    ("G4 Doorbell", "UVC-G4-Doorbell", doorbell("std", white=True)),
    ("Doorbell Lite", "UVC-Doorbell-Lite", doorbell("lite")),
    ("G3 Pro", "UVC-G3-PRO", bullet(big=True)),
    ("G3 Bullet", "UVC-G3-Bullet", bullet()),
    ("G3 AF", "UVC-G3-AF", bullet()),
    ("G3 Dome", "UVC-G3-Dome", dome()),
    ("G3 Flex", "UVC-G3-FLEX", flexcam()),
    ("G3 Instant", "UVC-G3-INS", instant()),
    ("G3 Micro", "UVC-G3-Micro", cube(0.45)),
    ("G3 Mini", "UVC-G3-Mini", cube(0.5)),
    ("G2 Pro", "UVC-Pro", bullet(big=True)),
    ("G2 Bullet", "UVC-G2-Bullet", bullet()),
    ("G2 Dome", "UVC-Dome", dome()),
    ("Camera Micro", "UVC-Micro", cube(0.45)),
    ("airCam Mini", "AirCam-Mini", cube(0.5, dark=True)),
]

PROTECT = [
    S("Enterprise NVR", "ENVR", bays=16, bayrows=4, u=4, screen=None),
    S("Enterprise NVR Core", "ENVR-Core", bays=16, bayrows=4, u=4, screen=None),
    S("NVR Gen 2 Pro", "UNVR-G2-Pro", bays=8, bayrows=2, u=2, screen=None),
    S("NVR Gen 2", "UNVR-G2", bays=4, screen=None),
    S("NVR Pro", "UNVR-Pro", bays=7, bayrows=2, u=2),
    S("NVR", "UNVR", bays=4),
    ("NVR Instant", "UNVR-Instant", flatbox(1.3, 0.34)),
    ("NVR (first generation)", "NVR", flatbox(1.3, 0.24, "dot")),
    ("AI Key", "UP-AI-Key", sensor("key")),
    ("AI Port", "UP-AI-Port", darkbox(0.32, 0.95)),
    ("AI Pro Enhancer", "UACC-AI-Pro-Enhancer", sensor("enhancer")),
    ("Protect Viewport", "UFP-VIEWPORT", darkbox(0.3, 1.0)),
    ("Protect AI Horn Speaker", "UP-AI-Horn-Speaker", speaker("horn")),
    ("Protect AI Speaker", "UP-AI-Speaker", speaker("ai")),
    ("In Ceiling Speaker", "UACC-In-Ceiling-Speaker", speaker("ceiling")),
    ("In Wall Speaker", "UACC-In-Wall-Speaker", speaker("wall")),
    ("Protect Siren PoE", "UP-Siren-PoE", sensor("siren")),
    ("Protect Chime PoE", "UP-Chime-PoE", sensor("chime")),
    ("Protect WiFi Chime", "UP-Chime", sensor("chime")),
    ("Protect Floodlight", "UP-FloodLight", floodlight()),
    ("Protect Door Lock", "UP-DoorLock", sensor("lock")),
    ("Protect Sensor", "UP-Sense", sensor("bar")),
    ("Protect Air Quality", "UP-AirQuality", sensor("air")),
    ("Protect AlarmHub Kit", "UP-AlarmHub-Kit", cabinet()),
    ("SuperLink G2 Gateway HA", "USL-G2-Gateway-HA", sensor("gateway")),
    ("SuperLink Gateway", "USL-Gateway", sensor("gateway")),
    ("SuperLink Siren", "USL-Siren", sensor("siren")),
    ("SuperLink Motion Sensor", "USL-Motion", sensor("motion")),
    ("SuperLink Entry Sensor", "USL-Entry", sensor("entry")),
    ("SuperLink Entry Recessed", "USL-Entry-R", sensor("recessed")),
    ("SuperLink Environmental Sensor", "USL-Environmental", sensor("env")),
    ("SuperLink GlassBreak Sensor", "USL-GlassBreak", sensor("glass")),
    ("SuperLink Smoke Sensor", "USL-Smoke", sensor("smoke")),
    ("SuperLink Button", "USL-Button", sensor("button")),
    ("SuperLink FOB", "USL-FOB", sensor("fob")),
    ("SuperLink Relay", "USL-Relay", sensor("relay")),
]

ACCESS = [
    ("Enterprise Access Hub", "EAH-8", cabinet()),
    ("Access Hub", "UA-Hub", accesshub(1.0, 1.0)),
    ("Door Hub", "UA-Hub-Door", accesshub(1.0, 0.9)),
    ("Door Hub Mini", "UA-Hub-Door-Mini", accesshub(0.7, 0.8, sides=False)),
    ("Gate Hub", "UA-Hub-Gate", accesshub(1.0, 1.0)),
    ("Elevator Hub", "UA-Elevator", accesshub(0.9, 1.25)),
    ("Retrofit Hub 2", "UA-Retrofit-Hub-2", accesshub(1.1, 0.9)),
    ("Access Ultra", "UA-Ultra", reader("slim")),
    ("G3 Intercom", "UA-G3-Intercom", intercom()),
    ("G3 Reader Pro", "UA-G3-Pro", reader("pro", white=False)),
    ("G3 Reader", "UA-G3", reader("std")),
    ("G3 Reader Flex", "UA-G3-Flex", reader("flex")),
    ("G3 Fingerprint", "UA-G3-Fingerprint", reader("keypad", white=False)),
    ("G2 Reader Pro", "UA-G2-Pro", reader("pro", white=False)),
    ("G2 Reader", "UA-G2", reader("std")),
    ("Reader Pro", "UA-Pro", reader("round")),
    ("Reader Lite", "UA-Reader-Lite", reader("lite")),
    ("Retrofit Reader", "UA-Retrofit-Reader", reader("std", white=False)),
    ("Retrofit Reader Fingerprint", "UA-Retrofit-Reader-Fingerprint", reader("keypad", white=False)),
    ("Intercom", "UA-Intercom", intercom()),
    ("Intercom Viewer", "UA-Intercom-Viewer", tablet(0.7, 0.95, stand=False)),
    ("Access Card", "UA-Card", card()),
    ("Pocket Keyfob", "UA-Pocket", sensor("pocket")),
    ("Phone G3 Touch Enterprise", "UTP-G3-Touch-Enterprise", phone("max")),
    ("Phone G3 Touch Pro", "UTP-G3-Touch-Pro", phone("touch")),
    ("Phone G3 Touch Wall", "UTP-G3-Wall", phone("touch")),
    ("Phone Touch Max", "UTP-TouchMax", phone("max")),
    ("Phone Touch", "UTP-Touch", phone("touch")),
    ("Phone Flex", "UTP-Flex", phone("keys")),
    ("Phone Executive", "UVP-Executive", phone("max")),
    ("Phone Professional", "UVP-Pro", phone("touch")),
    ("Talk Phone X", "UVP-X", phone("touch")),
    ("Talk Phone", "UVP", phone("touch")),
    ("Talk Telephone Adapter", "UT-ATA", flatbox(1.0, 0.55, "lcd", dark=True)),
    ("Connect Display 27", "UC-Display27", tablet(1.6, 0.95)),
    ("Connect Display 21", "UC-Display21", tablet(1.35, 0.82)),
    ("Connect Display 13", "UC-Display13", tablet(1.1, 0.7, white=True)),
    ("Connect Display 7", "UC-Display7", tablet(0.6, 0.9, white=True)),
    ("Connect Display Max", "UC-Display-SE-27", tablet(1.6, 0.95, white=True)),
    ("Connect Display", "UC-Display", tablet(1.1, 0.7, white=True)),
    ("Display Cast Pro", "UC-Cast-Pro", darkbox(0.45, 0.95)),
    ("Display Cast", "UC-Cast", darkbox(0.45, 0.8)),
    ("Display Cast Lite", "UC-Cast-Lite", darkbox(0.4, 0.7)),
    ("EV Station Pro", "UC-EV-Station-Pro", evstation(pro=True)),
    ("EV Station", "UC-EV-Station", evstation()),
    ("EV Station Lite", "UC-EV-Station-Lite", evstation()),
    ("LED Panel AC", "ULED-AC", ledpanel()),
    ("LED Bulb AT", "ULED-AT", sensor("bulb")),
    ("Dimmer Switch AC", "UDIM-AC", dimmer()),
    ("Dimmer Switch AT", "UDIM-AT", dimmer()),
    ("Motion Sensor (LED)", "ULS", sensor("disc")),
]

POWER = [
    S("Enterprise NAS", "ENAS", bays=12, bayrows=3, u=3, screen=None),
    S("UNAS Pro 8", "UNAS-Pro-8", bays=8, bayrows=2, u=2, screen=None),
    S("UNAS Pro", "UNAS-Pro", bays=7, bayrows=2, u=2),
    S("UNAS Pro 4", "UNAS-Pro-4", bays=4, screen=None),
    ("UNAS 4", "UNAS-4", darkbox(0.6, 1.0)),
    ("UNAS 2", "UNAS-2", darkbox(0.45, 1.0)),
    S("UPS 2U Pro", "UPS-2U-Pro", u=2, screen=None, ring=True, panel=True),
    S("UPS 2U", "UPS-2U", u=2, screen=None, ring=True),
    ("UPS Tower", "UPS-Tower", tower()),
    S("Power Distribution Pro", "USP-PDU-Pro", u=2, outlets=[16, 4]),
    ("Power Distribution Hi-Density", "USP-PDU-HD", pduhd()),
    S("Power Backup Pro", "USP-RPS-Pro", rj(1, 1)),
    S("Power Backup", "USP-RPS", rj(1, 1)),
    ("SmartPower Strip", "USP-Strip", plug(6)),
    ("SmartPower Plug", "USP-Plug", plug(1)),
    ("Mobile Router Industrial", "UMR-Industrial", router(3, dark=True, screen=False)),
    ("Mobile Router Ultra", "UMR-Ultra", router(2, dark=True, screen=False)),
    ("Mobile Router", "UMR", router(2)),
    ("U5G Max Outdoor", "U5G-Max-Outdoor", plate(0.65, 1.05, "dot", rad=0.16)),
    ("U5G Max", "U5G-Max", plate(0.65, 1.05, "screen", rad=0.16)),
    ("U5G Backup", "U5G", tube(0.26, 1.0, None, screen=True, foot=True)),
    ("LTE Backup Pro", "U-LTE-Backup-Pro", tube(0.26, 1.0, None, screen=True, foot=True)),
    ("LTE Backup", "U-LTE", tube(0.26, 1.0, None, screen=True, foot=True)),
    ("SFP Wizard", "UACC-SFP-Wizard", wizard()),
]

STENCILS = [
    ("UniFi - Gateways and Consoles", "UniFi Network", GATEWAYS),
    ("UniFi - Switches", "UniFi Network", SWITCHES),
    ("UniFi - WiFi and Bridges", "UniFi Network", WIFI),
    ("UniFi - Protect Cameras", "UniFi Protect", CAMERAS),
    ("UniFi - Protect Recorders and Sensors", "UniFi Protect", PROTECT),
    ("UniFi - Access, Talk and Connect", "UniFi Access, Talk and Connect", ACCESS),
    ("UniFi - Storage, Power and Mobility", "UniFi", POWER),
]

# ---------------------------------------------------------------- the file

MAIN = "xmlns='http://schemas.microsoft.com/office/visio/2012/main' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships' xml:space='preserve'"
HEAD = "<?xml version='1.0' encoding='utf-8' ?>\n"
REL = "http://schemas.microsoft.com/visio/2010/relationships/"
GROUP = 5  # the ID of the group in every master


def num(v):
    text = f"{v:.5f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def cell(name, value, formula=None, unit=None):
    return f"<Cell N='{name}' V='{value}'" + (f" U='{unit}'" if unit else "") + (f" F='{formula}'" if formula else "") + "/>"


def share(name, of, value, whole):
    part = value / whole if whole else 0
    return cell(name, num(value), f"{of}*{num(part)}")


def bounds(shape):
    xs, ys = [], []
    for path in shape["paths"]:
        if path[0] == "E":
            _, cx, cy, rx, ry = path
            xs += [cx - rx, cx + rx]
            ys += [cy - ry, cy + ry]
        else:
            xs += [p[0] for p in path[1]]
            ys += [p[1] for p in path[1]]
    return min(xs), min(ys), max(xs), max(ys)


def child_xml(sid, shape, art):
    x0, y0, x1, y1 = bounds(shape)
    w, h = x1 - x0, y1 - y0
    top = f"Sheet.{GROUP}!"
    xml = f"<Shape ID='{sid}' Type='Shape' LineStyle='0' FillStyle='0' TextStyle='0'>"
    xml += share("PinX", top + "Width", x0 + w / 2, art.w) + share("PinY", top + "Height", y0 + h / 2, art.h)
    xml += share("Width", top + "Width", w, art.w) + share("Height", top + "Height", h, art.h)
    xml += cell("LocPinX", num(w / 2), "Width*0.5") + cell("LocPinY", num(h / 2), "Height*0.5") + cell("Angle", "0")
    if shape["line"]:
        xml += cell("LineColor", shape["line"]) + cell("LinePattern", "1") + cell("LineWeight", num(shape["lw"] / 72)) + cell("LineCap", "0")
    else:
        xml += cell("LinePattern", "0")
    if shape["fill"]:
        xml += cell("FillForegnd", shape["fill"]) + cell("FillPattern", "1")
    else:
        xml += cell("FillPattern", "0")
    xml += cell("Rounding", num(shape["rad"])) + cell("ShdwPattern", "0")
    for index, path in enumerate(shape["paths"]):
        filled = bool(shape["fill"]) and (path[0] == "E" or path[2])
        xml += f"<Section N='Geometry' IX='{index}'>" + cell("NoFill", "0" if filled else "1") + cell("NoLine", "0") + cell("NoShow", "0") + cell("NoSnap", "0")
        if path[0] == "E":
            _, cx, cy, rx, ry = path
            cx, cy = cx - x0, cy - y0
            xml += "<Row T='Ellipse' IX='1'>" + share("X", "Width", cx, w) + share("Y", "Height", cy, h) + share("A", "Width", cx + rx, w) + share("B", "Height", cy, h) + share("C", "Width", cx, w) + share("D", "Height", cy + ry, h) + "</Row>"
        else:
            points = path[1] + (path[1][:1] if path[2] else [])
            for row, (x, y) in enumerate(points):
                xml += f"<Row T='{'MoveTo' if row == 0 else 'LineTo'}' IX='{row + 1}'>" + share("X", "Width", x - x0, w) + share("Y", "Height", y - y0, h) + "</Row>"
        xml += "</Section>"
    return xml + "</Shape>"


def prop(name, label, value=""):
    return f"<Row N='{name}'>" + cell("Value", escape(value, {"'": "&apos;"}), unit="STR") + cell("Prompt", "") + cell("Label", label) + cell("Format", "") + cell("SortKey", "") + cell("Type", "0") + cell("Invisible", "0") + cell("Verify", "0") + "</Row>"


def master_xml(name, sku, line, art):
    w, h = art.w, art.h
    q = {"'": "&apos;"}
    xml = f"<Shape ID='{GROUP}' Type='Group' LineStyle='0' FillStyle='0' TextStyle='0'>"
    xml += cell("PinX", num(w / 2)) + cell("PinY", num(h / 2)) + cell("Width", num(w)) + cell("Height", num(h))
    xml += cell("LocPinX", num(w / 2), "Width*0.5") + cell("LocPinY", num(h / 2), "Height*0.5") + cell("Angle", "0")
    xml += cell("LinePattern", "0") + cell("FillPattern", "0") + cell("LockAspect", "1")
    tw = w + 0.9
    xml += cell("TxtPinX", num(w / 2), "Width*0.5") + cell("TxtPinY", "-0.14", "-TxtHeight*0.5") + cell("TxtWidth", num(tw), "Width+0.9") + cell("TxtHeight", "0.28")
    xml += cell("TxtLocPinX", num(tw / 2), "TxtWidth*0.5") + cell("TxtLocPinY", "0.14", "TxtHeight*0.5") + cell("TxtAngle", "0")
    xml += cell("VerticalAlign", "0") + cell("TopMargin", "0.03") + cell("BottomMargin", "0")
    xml += "<Section N='Character'><Row IX='0'>" + cell("Font", "Calibri") + cell("Color", "#1F2937") + cell("Size", "0.1111111111111111", unit="PT") + "</Row></Section>"
    xml += "<Section N='Paragraph'><Row IX='0'>" + cell("HorzAlign", "1") + "</Row></Section>"
    xml += "<Section N='Property'>" + prop("Manufacturer", "Manufacturer", "Ubiquiti") + prop("ProductLine", "Product line", line) + prop("Product", "Product", name) + prop("Model", "Model", sku)
    xml += prop("DeviceName", "Name") + prop("IPAddress", "IP address") + prop("MACAddress", "MAC address") + prop("Location", "Location") + "</Section>"
    xml += "<Section N='Connection'>"
    for index, (x, y) in enumerate([(0.5, 0.0), (1.0, 0.5), (0.5, 1.0), (0.0, 0.5), (0.5, 0.5)]):
        xml += f"<Row T='Connection' IX='{index}'>" + share("X", "Width", x * w, w) + share("Y", "Height", y * h, h) + "</Row>"
    xml += "</Section>"
    xml += f"<Text>{escape(sku, q)}</Text><Shapes>"
    for index, shape in enumerate(art.shapes):
        xml += child_xml(GROUP + 1 + index, shape, art)
    return xml + "</Shapes></Shape>"


def rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def icon(art):
    """The master's picture in the Shapes pane: a 32x32 icon with 16
    colours, as Visio stores them."""
    size, over = 32, 6
    canvas = size * over
    scale = (size - 2) * over / max(art.w, art.h)
    ox, oy = (canvas - art.w * scale) / 2, (canvas - art.h * scale) / 2
    image = Image.new("RGBA", (canvas, canvas), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)

    def at(x, y):
        return (ox + x * scale, canvas - oy - y * scale)

    for shape in art.shapes:
        fill = rgb(shape["fill"]) + (255,) if shape["fill"] else None
        line = rgb(shape["line"]) + (255,) if shape["line"] else None
        width = max(over // 2, round(shape["lw"] / 72 * scale)) if line else 0
        for path in shape["paths"]:
            if path[0] == "E":
                _, cx, cy, rx, ry = path
                (xa, ya), (xb, yb) = at(cx - rx, cy + ry), at(cx + rx, cy - ry)
                draw.ellipse([xa, ya, max(xb, xa + 1), max(yb, ya + 1)], fill=fill, outline=line, width=width)
            elif path[2]:
                points = [at(*p) for p in path[1]]
                if shape["rad"] and len(points) == 4:
                    (xa, yb), (xb, ya) = points[0], points[2]
                    radius = min(shape["rad"] * scale, (xb - xa) / 2, (yb - ya) / 2)
                    draw.rounded_rectangle([xa, ya, max(xb, xa + 1), max(yb, ya + 1)], radius=radius, fill=fill, outline=line, width=width)
                else:
                    draw.polygon(points, fill=fill)
                    if line:
                        draw.line(points + points[:1], fill=line, width=width)
            elif line:
                draw.line([at(*p) for p in path[1]], fill=line, width=max(width, over))
    image = image.resize((size, size), Image.LANCZOS)
    flat = Image.new("RGB", (size, size), (255, 255, 255))
    flat.paste(image, mask=image.getchannel("A"))
    pal = flat.quantize(colors=16, method=Image.MEDIANCUT, dither=Image.NONE)
    colours = (pal.getpalette() or [])[:48]
    colours += [0] * (48 - len(colours))
    pixels, alpha = pal.load(), image.getchannel("A").load()
    xor, mask = b"", b""
    for y in range(size - 1, -1, -1):
        xor += bytes((pixels[x, y] << 4) | pixels[x + 1, y] for x in range(0, size, 2))
        mask += bytes(sum((0 if alpha[x + bit, y] > 96 else 1) << (7 - bit) for bit in range(8)) for x in range(0, size, 8))
    table = b"".join(bytes((colours[i * 3 + 2], colours[i * 3 + 1], colours[i * 3], 0)) for i in range(16))
    bitmap = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 4, 0, len(xor) + len(mask), 0, 0, 0, 0) + table + xor + mask
    data = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", size, size, 16, 0, 0, 0, len(bitmap), 22) + bitmap
    text = base64.b64encode(data).decode()
    return "\n".join(text[i:i + 76] for i in range(0, len(text), 76))


def guid(name):
    d = hashlib.md5(("plano-unifi:" + name).encode()).hexdigest().upper()
    return "{%s-%s-%s-%s-%s}" % (d[:8], d[8:12], d[12:16], d[16:20], d[20:32])


def rels(entries):
    items = "".join(f'<Relationship Id="{i}" Type="{t}" Target="{target}"/>' for i, t, target in entries)
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{items}</Relationships>'


def document_xml():
    return (
        f"{HEAD}<VisioDocument {MAIN}>"
        "<DocumentSettings TopPage='0' DefaultTextStyle='0' DefaultLineStyle='0' DefaultFillStyle='0' DefaultGuideStyle='0'>"
        "<GlueSettings>9</GlueSettings><SnapSettings>295</SnapSettings><SnapExtensions>34</SnapExtensions><SnapAngles/>"
        "<DynamicGridEnabled>1</DynamicGridEnabled><ProtectStyles>0</ProtectStyles><ProtectShapes>0</ProtectShapes>"
        "<ProtectMasters>0</ProtectMasters><ProtectBkgnds>0</ProtectBkgnds></DocumentSettings>"
        "<Colors><ColorEntry IX='0' RGB='#000000'/><ColorEntry IX='1' RGB='#FFFFFF'/></Colors>"
        "<FaceNames><FaceName NameU='Calibri' UnicodeRanges='-536859905 -1073732485 9 0' CharSets='536871423 0' Panose='2 15 5 2 2 2 4 3 2 4' Flags='325'/></FaceNames>"
        "<StyleSheets><StyleSheet ID='0' NameU='No Style' IsCustomNameU='1' Name='No Style' IsCustomName='1'>"
        "<Cell N='EnableLineProps' V='1'/><Cell N='EnableFillProps' V='1'/><Cell N='EnableTextProps' V='1'/>"
        "<Cell N='HideForApply' V='0'/><Cell N='LineWeight' V='0.01041666666666667'/><Cell N='LineColor' V='0'/><Cell N='LinePattern' V='1'/>"
        "<Cell N='Rounding' V='0'/><Cell N='EndArrowSize' V='2'/><Cell N='BeginArrow' V='0'/><Cell N='EndArrow' V='0'/>"
        "<Cell N='LineCap' V='0'/><Cell N='BeginArrowSize' V='2'/><Cell N='LineColorTrans' V='0'/>"
        "<Cell N='FillForegnd' V='1'/><Cell N='FillBkgnd' V='0'/><Cell N='FillPattern' V='1'/>"
        "<Cell N='ShdwForegnd' V='0'/><Cell N='ShdwPattern' V='0'/>"
        "<Cell N='FillForegndTrans' V='0'/><Cell N='FillBkgndTrans' V='0'/>"
        "<Cell N='LeftMargin' V='0.05555555555555555' U='PT'/><Cell N='RightMargin' V='0.05555555555555555' U='PT'/>"
        "<Cell N='TopMargin' V='0.05555555555555555' U='PT'/><Cell N='BottomMargin' V='0.05555555555555555' U='PT'/>"
        "<Cell N='VerticalAlign' V='1'/><Cell N='TextBkgnd' V='0'/><Cell N='DefaultTabStop' V='0.5'/><Cell N='TextDirection' V='0'/>"
        "<Section N='Character'><Row IX='0'><Cell N='Font' V='Calibri'/><Cell N='Color' V='0'/><Cell N='Style' V='0'/>"
        "<Cell N='Case' V='0'/><Cell N='Pos' V='0'/><Cell N='FontScale' V='1'/><Cell N='Size' V='0.1666666666666667' U='PT'/>"
        "<Cell N='Strikethru' V='0'/></Row></Section>"
        "<Section N='Paragraph'><Row IX='0'><Cell N='IndFirst' V='0'/><Cell N='IndLeft' V='0'/><Cell N='IndRight' V='0'/>"
        "<Cell N='SpLine' V='-1.2'/><Cell N='SpBefore' V='0'/><Cell N='SpAfter' V='0'/><Cell N='HorzAlign' V='1'/>"
        "<Cell N='Bullet' V='0'/></Row></Section>"
        "</StyleSheet></StyleSheets>"
        "<DocumentSheet NameU='TheDoc' IsCustomNameU='1' Name='TheDoc' IsCustomName='1' LineStyle='0' FillStyle='0' TextStyle='0'>"
        "<Cell N='OutputFormat' V='0'/><Cell N='LockPreview' V='0'/><Cell N='AddMarkup' V='0'/><Cell N='ViewMarkup' V='0'/>"
        "<Cell N='DocLangID' V='1033' U='STR'/></DocumentSheet></VisioDocument>"
    )


def build(path, title, masters, kind="stencil", pages=None):
    """Writes a stencil of `masters`, each (name, sku, line, art), or with
    `pages` a drawing that shows them."""
    q = {"'": "&apos;"}
    types = [("/visio/document.xml", f"application/vnd.ms-visio.{kind}.main+xml"), ("/visio/masters/masters.xml", "application/vnd.ms-visio.masters+xml"), ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"), ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml")]
    parts, entries, master_rels = {}, "", []
    for index, (name, sku, line, art) in enumerate(masters, 1):
        n = escape(name, q)
        prompt = escape(f"Ubiquiti {line}: {name} ({sku})", q)
        keywords = escape(f"Ubiquiti,UniFi,{line},{name},{sku}", q)
        entries += (
            f"<Master ID='{index}' NameU='{n}' IsCustomNameU='1' Name='{n}' IsCustomName='1' Prompt='{prompt}' IconSize='1' AlignName='2' MatchByName='0' IconUpdate='0' UniqueID='{guid(name)}' BaseID='{guid('base:' + name)}' PatternFlags='0' Hidden='0' MasterType='2'>"
            f"<PageSheet LineStyle='0' FillStyle='0' TextStyle='0'>{cell('PageWidth', num(art.w))}{cell('PageHeight', num(art.h))}{cell('ShdwOffsetX', '0.125')}{cell('ShdwOffsetY', '-0.125')}"
            f"{cell('PageScale', '1', unit='IN_F')}{cell('DrawingScale', '1', unit='IN_F')}{cell('DrawingSizeType', '4')}{cell('DrawingScaleType', '0')}{cell('InhibitSnap', '0')}{cell('ShapeKeywords', keywords)}</PageSheet>"
            f"<Icon>\n{icon(art)}</Icon><Rel r:id='rId{index}'/></Master>"
        )
        parts[f"visio/masters/master{index}.xml"] = f"{HEAD}<MasterContents {MAIN}><Shapes>{master_xml(name, sku, line, art)}</Shapes></MasterContents>"
        master_rels.append((f"rId{index}", REL + "master", f"master{index}.xml"))
        types.append((f"/visio/masters/master{index}.xml", "application/vnd.ms-visio.master+xml"))
    parts["visio/masters/masters.xml"] = f"{HEAD}<Masters {MAIN}>{entries}</Masters>"
    parts["visio/masters/_rels/masters.xml.rels"] = rels(master_rels)
    doc_rels = [("rId1", REL + "masters", "masters/masters.xml")]
    if pages:
        listing, page_rels = "", []
        for index, (page_name, pw, ph, shapes, used) in enumerate(pages, 1):
            listing += (
                f"<Page ID='{index - 1}' NameU='{escape(page_name, q)}' Name='{escape(page_name, q)}' ViewScale='-1' ViewCenterX='{num(pw / 2)}' ViewCenterY='{num(ph / 2)}'>"
                f"<PageSheet LineStyle='0' FillStyle='0' TextStyle='0'>{cell('PageWidth', num(pw))}{cell('PageHeight', num(ph))}{cell('ShdwOffsetX', '0.125')}{cell('ShdwOffsetY', '-0.125')}"
                f"{cell('PageScale', '1', unit='IN_F')}{cell('DrawingScale', '1', unit='IN_F')}{cell('DrawingSizeType', '3')}{cell('DrawingScaleType', '0')}{cell('InhibitSnap', '0')}</PageSheet><Rel r:id='rId{index}'/></Page>"
            )
            parts[f"visio/pages/page{index}.xml"] = f"{HEAD}<PageContents {MAIN}><Shapes>{shapes}</Shapes></PageContents>"
            parts[f"visio/pages/_rels/page{index}.xml.rels"] = rels([(f"rId{m}", REL + "master", f"../masters/master{m}.xml") for m in used])
            page_rels.append((f"rId{index}", REL + "page", f"page{index}.xml"))
            types.append((f"/visio/pages/page{index}.xml", "application/vnd.ms-visio.page+xml"))
        parts["visio/pages/pages.xml"] = f"{HEAD}<Pages {MAIN}>{listing}</Pages>"
        parts["visio/pages/_rels/pages.xml.rels"] = rels(page_rels)
        types.append(("/visio/pages/pages.xml", "application/vnd.ms-visio.pages+xml"))
        doc_rels.append(("rId2", REL + "pages", "pages/pages.xml"))
    parts["visio/document.xml"] = document_xml()
    parts["visio/_rels/document.xml.rels"] = rels(doc_rels)
    parts["_rels/.rels"] = rels([
        ("rId1", REL + "document", "visio/document.xml"),
        ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
        ("rId3", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties", "docProps/app.xml"),
    ])
    parts["docProps/core.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{escape(title)}</dc:title><dc:subject>Ubiquiti UniFi network shapes</dc:subject><dc:creator>{AUTHOR}</dc:creator><cp:keywords>Ubiquiti, UniFi, network</cp:keywords>"
        f"<dc:description>Schematic shapes of Ubiquiti UniFi products. © 2026 {AUTHOR}. Not made or endorsed by Ubiquiti Inc.</dc:description><cp:lastModifiedBy>{AUTHOR}</cp:lastModifiedBy></cp:coreProperties>"
    )
    parts["docProps/app.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        f"<Application>Microsoft Visio</Application><Manager>{AUTHOR}</Manager><Company></Company></Properties>"
    )
    content = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
    content += "".join(f'<Override PartName="{p}" ContentType="{t}"/>' for p, t in types) + "</Types>"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content)
        for name, data in parts.items():
            z.writestr(name, data)


def overview_pages(sets, numbering):
    """One page for each stencil, with every shape laid out in rows."""
    pages = []
    for title, _, items in sets:
        width, x, rows, row = 16.5, 0.6, [], []
        for name, sku, art in items:
            cellw = max(art.w, 1.3) + 0.5
            if x + cellw > width - 0.4 and row:
                rows.append(row)
                row, x = [], 0.6
            row.append((x + cellw / 2, name, art))
            x += cellw
        rows.append(row)
        height = 1.4 + sum(max(a.h for _, _, a in r) + 0.75 for r in rows)
        sid, shapes, used, y = 1, "", [], height - 1.2
        shapes += (
            f"<Shape ID='{sid}' Type='Shape' LineStyle='0' FillStyle='0' TextStyle='0'>{cell('PinX', num(width / 2))}{cell('PinY', num(height - 0.5))}{cell('Width', num(width - 1.2))}{cell('Height', '0.5')}"
            f"{cell('LocPinX', num((width - 1.2) / 2), 'Width*0.5')}{cell('LocPinY', '0.25', 'Height*0.5')}{cell('LinePattern', '0')}{cell('FillPattern', '0')}"
            f"<Section N='Character'><Row IX='0'>{cell('Color', '#1F2937')}{cell('Size', '0.25', unit='PT')}{cell('Style', '1')}</Row></Section><Section N='Paragraph'><Row IX='0'>{cell('HorzAlign', '0')}</Row></Section>"
            f"<Text>{escape(title)}</Text></Shape>"
        )
        for r in rows:
            tall = max(a.h for _, _, a in r)
            for cx, name, art in r:
                sid += 1
                master = numbering[name]
                used.append(master)
                kids = "".join(f"<Shape ID='{sid + 1 + k}' Type='Shape' MasterShape='{GROUP + 1 + k}'/>" for k in range(len(art.shapes)))
                shapes += f"<Shape ID='{sid}' Type='Group' Master='{master}'>{cell('PinX', num(cx))}{cell('PinY', num(y - tall + art.h / 2))}<Shapes>{kids}</Shapes></Shape>"
                sid += len(art.shapes)
            y -= tall + 0.75
        pages.append((title.replace("UniFi - ", ""), width, height, shapes, sorted(set(used))))
    return pages


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out, exist_ok=True)
    everything, seen = [], set()
    for title, line, items in STENCILS:
        masters = [(name, sku, line, art) for name, sku, art in items]
        for name, *_ in masters:
            assert name not in seen, f"two shapes are called {name}"
            seen.add(name)
        build(os.path.join(out, title + ".vssx"), title, masters)
        everything += masters
        print(f"{title}.vssx: {len(masters)} shapes")
    build(os.path.join(out, "UniFi - All Products.vssx"), "UniFi - All Products", everything)
    numbering = {name: index for index, (name, *_) in enumerate(everything, 1)}
    build(os.path.join(out, "UniFi - Overview.vsdx"), "UniFi - Overview", everything, kind="drawing", pages=overview_pages(STENCILS, numbering))
    print(f"UniFi - All Products.vssx and UniFi - Overview.vsdx: {len(everything)} shapes")


if __name__ == "__main__":
    main()
