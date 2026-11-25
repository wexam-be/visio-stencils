#!/usr/bin/env python3
"""Builds a Visio stencil (.vssx) of ADVA FSP 3000R7 shelves and modules.

    python3 make_fsp3000_stencils.py [output-folder]

Every shape is a master: a group of plain vector shapes drawn here from
scratch, seen from the front, labelled with its model and carrying shape
data. The drawings follow the faceplate figures in ADVA's own manuals
(FSP 3000R7 High-Density Subshelf Guide R17.2, Installation and
Commissioning Manual, Hardware Description R13.3); what those figures do
not show is drawn schematically and said so in the shape's prompt.

All shapes share one scale: a 19-inch rack front is 2.8 in wide and 1 HU
is 0.28 in high, the same as the Ubiquiti UniFi stencils beside this one,
so modules drop exactly into the slots of their shelves.

Developer: Eric De Pessemier. Licence: GPL-3.0-or-later.
ADVA, FSP and Adtran are trademarks of their owners; these stencils are not
made or endorsed by Adtran Networks.
"""

import importlib.util
import os
import sys
import zipfile
import hashlib
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("unifi", os.path.join(HERE, "..", "Ubiquiti UniFi", "make_unifi_stencils.py"))
U = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(U)
Art, cell, num, share, prop, child_xml, icon, rels, document_xml = U.Art, U.cell, U.num, U.share, U.prop, U.child_xml, U.icon, U.rels, U.document_xml
GROUP, HEAD, MAIN, REL = U.GROUP, U.HEAD, U.MAIN, U.REL

AUTHOR = "Eric De Pessemier"
MAKER = "ADVA (Adtran Networks)"

# Colours
FACE, FACE_EDGE = "#D9DCE0", "#8E96A3"   # light grey HD faceplates
SILVER, EAR, EDGE = "#E3E6EA", "#C5CAD1", "#8E96A3"
CAGE, CAGE_EDGE, HOLE = "#AEB5BF", "#6B7280", "#2B3038"
LED, LABEL, SCREW = "#3FB97A", "#FFFFFF", "#B8BEC6"
CEM_BLUE, LCD = "#1E4E9C", "#DCE8F7"
SLOT, SLOT_EDGE = "#4A5058", "#30353C"   # an empty slot opening
LC_BLUE = "#2F6FD0"                      # single-mode LC adapters

HU, RACK = 0.28, 2.8                     # inches per HU, width of a 19-inch front
MM = RACK / 482.6                        # inches per millimetre across the front


def screw(a, cx, cy, r=0.014):
    a.e(cx, cy, r, r, SCREW, CAGE_EDGE, 0.4)


def cage(a, x, y, w, h):
    """A QSFP/SFP cage: metal frame around a dark opening."""
    a.r(x, y, w, h, CAGE, CAGE_EDGE, 0.0, 0.4)
    a.r(x + w * 0.12, y + h * 0.2, w * 0.76, h * 0.6, HOLE, None)


def ears(a, w, h):
    a.rs([(0, 0, 0.13, h), (w - 0.13, 0, 0.13, h)], EAR, EDGE)
    ys = [0.07, h - 0.07] if h < 0.6 else [0.07, h / 2, h - 0.07]
    a.es([(x, y) for x in (0.065, w - 0.065) for y in ys], 0.022, "#6B7280")


# ------------------------------------------------- high-density (HD) family
# SH1R: from the left the CEM-3 (slot 3), the two traffic slots (slot 2 above
# slot 1), fibre management guides, and the fibre tray with the air inlet and
# filter (Subshelf Guide, figures 17 and 19).

CARD_W, CARD_H = 1.36, 0.125            # an HD traffic module in an SH1R slot
SH1R_SLOT_X = 0.70
SH1R_SLOT_Y = (0.012, 0.143)            # slot 1 (lower), slot 2 (upper)


def cem3(a, x, y, w, h):
    """CEM-3 display panel (Subshelf Guide, figure 24)."""
    a.r(x, y, w, h, CEM_BLUE, "#163A75", 0.015)
    screw(a, x + 0.035, y + h - 0.045, 0.02)
    a.e(x + 0.075, y + h * 0.48, 0.03, 0.03, "#F2F4F7", "#9AA3AF", 0.5)          # lamp test
    a.r(x + 0.03, y + 0.02, 0.09, 0.035, LABEL, None, 0.004)                     # CEM-3 label
    a.r(x + w * 0.38, y + h * 0.5, w * 0.3, h * 0.33, LCD, "#9AB6DE", 0.01)      # shelf info LCD
    a.r(x + w * 0.74, y + h * 0.52, w * 0.17, h * 0.22, LABEL, None, 0.004)      # barcode
    a.es([(x + w * (0.3 + 0.075 * i), y + h * 0.27) for i in range(6)], 0.011, "#E9EDF2")  # Alarm State Mod Critical Major Minor


def ma2c5lt(x=0.0, y=0.0, a=None):
    """MA-2C5LT faceplate (Subshelf Guide, figure 39): module LEDs, client
    QSFP cages C17-C20, C13-C16, C9-C12, C5-C8, C1-C4, network QSFP28 N2, N1."""
    own = a is None
    a = a or Art(CARD_W, CARD_H)
    w, h = CARD_W, CARD_H
    a.r(x, y, w, h, FACE, FACE_EDGE, 0.006)
    screw(a, x + w * 0.025, y + h / 2)
    screw(a, x + w * 0.958, y + h * 0.7)
    a.r(x + w * 0.045, y + h * 0.18, w * 0.028, h * 0.64, LABEL, "#B8BEC6", 0.0, 0.3)
    a.es([(x + w * 0.088, y + h * f) for f in (0.7, 0.45, 0.22)], 0.007, LED)
    for left in (0.118, 0.22, 0.322, 0.455, 0.557, 0.686, 0.79):
        cage(a, x + w * left, y + h * 0.3, w * 0.082, h * 0.6)
        a.r(x + w * (left + 0.01), y + h * 0.1, w * 0.02, h * 0.08, LED, None)
    a.r(x + w * 0.888, y + h * 0.12, w * 0.09, h * 0.36, LABEL, "#B8BEC6", 0.0, 0.3)
    return a


def mp2b4ct(x=0.0, y=0.0, a=None):
    """MP-2B4CT faceplate (Subshelf Guide, figure 40): module LEDs, client
    QSFP28 cages C4, C3, C2, C1, network ports N2 and N1, each an LC pair
    with R above T."""
    a = a or Art(CARD_W, CARD_H)
    w, h = CARD_W, CARD_H
    a.r(x, y, w, h, FACE, FACE_EDGE, 0.006)
    screw(a, x + w * 0.022, y + h * 0.62)
    a.r(x + w * 0.045, y + h * 0.18, w * 0.028, h * 0.64, LABEL, "#B8BEC6", 0.0, 0.3)
    a.es([(x + w * 0.088, y + h * f) for f in (0.7, 0.45, 0.22)], 0.007, LED)
    for left in (0.335, 0.44, 0.548, 0.652):
        cage(a, x + w * left, y + h * 0.3, w * 0.078, h * 0.6)
        a.r(x + w * (left + 0.01), y + h * 0.1, w * 0.02, h * 0.08, LED, None)
    for left in (0.775, 0.83):                       # N2, N1
        for f in (0.55, 0.22):                       # R above T
            a.r(x + w * left, y + h * f, w * 0.03, h * 0.28, CAGE, CAGE_EDGE, 0.0, 0.4)
            a.r(x + w * (left + 0.008), y + h * (f + 0.07), w * 0.014, h * 0.14, HOLE, None)
    a.r(x + w * 0.885, y + h * 0.1, w * 0.105, h * 0.8, "#EEF0F3", "#B8BEC6", 0.004, 0.3)
    a.p([(x + w * 0.97, y + h * 0.5), (x + w * 0.955, y + h * 0.62), (x + w * 0.955, y + h * 0.38)], "#2F6FD0", None)
    a.r(x + w * 0.895, y + h * 0.2, w * 0.05, h * 0.6, LABEL, None)
    return a


def sh1r(cards=()):
    """SH1R front with empty traffic slots, or with `cards` as
    [(slot, drawing function)]."""
    w, h = RACK, HU
    a = Art(w, h)
    ears(a, w, h)
    a.r(0.13, 0, w - 0.26, h, SILVER, EDGE)
    cem3(a, 0.15, 0.012, 0.52, h - 0.024)
    filled = dict(cards)
    for slot, y in zip((1, 2), SH1R_SLOT_Y):
        if slot in filled:
            filled[slot](SH1R_SLOT_X, y, a)
        else:
            a.r(SH1R_SLOT_X, y, CARD_W, CARD_H, SLOT, SLOT_EDGE)
    gx = SH1R_SLOT_X + CARD_W + 0.02             # fibre management guides
    for y in SH1R_SLOT_Y:
        a.r(gx, y + 0.02, 0.07, CARD_H - 0.04, "#C9CED5", EDGE, 0.01)
    tx = gx + 0.1                                # fibre tray, air inlet and filter
    a.r(tx, 0.012, w - 0.15 - tx, h - 0.024, "#EDEFF2", EDGE, 0.01)
    a.es([(tx + 0.04 + i * 0.035, 0.05 + j * 0.045) for i in range(int((w - 0.2 - tx) / 0.035)) for j in range(5)], 0.008, "#AEB5BF")
    return a


# ------------------------------------------------------------ SH7HU family
# SH7HU (Hardware Description R13.3): 7 HU, 22 slots; slots 1-20 are 4 HP
# wide and 5 HU high; the two left-most slots A and B are half height and
# hold the NCU (A) and SCU (B); the fan unit with the shelf LEDs is above
# the slots and the air filter below. PSUs take slots 1+2 and 19+20.

SLOT_W = 4 * 5.08 * MM                  # 4 HP
SLOTS_H = 5 * HU
SLOTS_Y = HU                            # bottom of the module slots
SH7_X0 = (RACK - 21 * SLOT_W) / 2   # left edge of the A/B column


def slot_x(n):
    """Left edge of slot n (1-20); 0 is the A/B column."""
    return SH7_X0 + n * SLOT_W


def ncu2(x=0.0, y=0.0, a=None):
    """NCU-II, half height. Its ports (2 x RJ-45, RS-232, USB, CompactFlash)
    are known, their place on the faceplate is not: drawn schematically."""
    w, h = SLOT_W, SLOTS_H / 2
    a = a or Art(w, h)
    a.r(x, y, w, h, FACE, FACE_EDGE, 0.004, 0.4)
    screw(a, x + w / 2, y + h - 0.03, 0.012)
    screw(a, x + w / 2, y + 0.03, 0.012)
    a.es([(x + w * 0.3, y + h - 0.08), (x + w * 0.7, y + h - 0.08)], 0.008, LED)
    for k in range(2):                                      # RJ-45
        a.r(x + w * 0.18, y + h - 0.2 - k * 0.1, w * 0.64, 0.075, HOLE, CAGE_EDGE, 0.0, 0.3)
    a.r(x + w * 0.22, y + h * 0.36, w * 0.56, 0.1, "#9AA1AB", CAGE_EDGE, 0.01, 0.3)   # RS-232
    a.r(x + w * 0.32, y + h * 0.26, w * 0.36, 0.03, HOLE, None)                       # USB
    a.r(x + w * 0.15, y + 0.07, w * 0.7, 0.06, "#C9CED5", CAGE_EDGE, 0.0, 0.3)       # CF card
    return a


def scu(x=0.0, y=0.0, a=None):
    """SCU, half height (Installation Manual, figure 79): LEDs F and Mod,
    SFP ports U (uplink), D (downlink) and a third, unused one."""
    w, h = SLOT_W, SLOTS_H / 2
    a = a or Art(w, h)
    a.r(x, y, w, h, FACE, FACE_EDGE, 0.004, 0.4)
    screw(a, x + w / 2, y + h - 0.03, 0.012)
    screw(a, x + w / 2, y + 0.03, 0.012)
    a.es([(x + w * 0.3, y + h - 0.1), (x + w * 0.7, y + h - 0.1)], 0.008, LED)
    for k in range(3):
        cy = y + h - 0.22 - k * 0.13
        cage(a, x + w * 0.15, cy, w * 0.55, 0.1)
        a.es([(x + w * 0.82, cy + 0.07), (x + w * 0.82, cy + 0.03)], 0.006, LED)
    return a


def psu7hu_ac(x=0.0, y=0.0, a=None):
    """PSU/7HU-AC: 8 HP (two slots), AC appliance coupler, LED "P"."""
    w, h = 2 * SLOT_W, SLOTS_H
    a = a or Art(w, h)
    a.r(x, y, w, h, FACE, FACE_EDGE, 0.004, 0.4)
    screw(a, x + w / 2, y + h - 0.035)
    screw(a, x + w / 2, y + 0.035)
    a.e(x + w / 2, y + h - 0.12, 0.012, 0.012, LED, None)
    a.p([(x + w * 0.22, y + h * 0.42), (x + w * 0.78, y + h * 0.42), (x + w * 0.78, y + h * 0.58), (x + w * 0.66, y + h * 0.62), (x + w * 0.34, y + h * 0.62), (x + w * 0.22, y + h * 0.58)], HOLE, CAGE_EDGE, 0.4)
    a.rs([(x + w * f - 0.008, y + h * 0.48, 0.016, 0.05) for f in (0.35, 0.5, 0.65)], "#C9CED5", None)
    return a


def fan7hu(a, x, y, w, h):
    """Fan unit front (Installation Manual, figure 88): NE LEDs, display,
    buttons, fan LED, and one status LED per slot along its lower edge."""
    a.r(x, y, w, h, "#C7D3E3", EDGE, 0.01)
    a.r(x + 0.08, y + h * 0.45, 0.42, h * 0.32, "#F7F8FA", None, 0.01)       # name plate
    a.r(x + w * 0.5, y + h * 0.4, 0.3, h * 0.42, "#E5EBF3", "#9AA3AF", 0.01)  # NE LEDs
    a.es([(x + w * 0.5 + 0.06 + i * 0.09, y + h * 0.6) for i in range(3)], 0.012, LED)
    a.r(x + w * 0.66, y + h * 0.36, 0.22, h * 0.5, "#7FA35A", "#4E6B33", 0.01)  # display
    a.es([(x + w * 0.79, y + h * 0.7), (x + w * 0.79, y + h * 0.46)], 0.018, "#2F6FD0")
    a.e(x + w * 0.86, y + h * 0.6, 0.014, 0.014, LED, None)                    # fan LED
    centres = [SH7_X0 + SLOT_W * 0.3, SH7_X0 + SLOT_W * 0.7] + [slot_x(n) + SLOT_W / 2 for n in range(1, 21)]
    a.es([(cx, y + 0.05) for cx in centres], 0.009, LED)


def sh7hu(modules=()):
    """SH7HU front, empty, or with `modules` as [(slot, drawing function)]
    where slot is "A", "B" or 1-20."""
    w, h = RACK, 7 * HU
    a = Art(w, h)
    ears(a, w, h)
    a.r(0.13, 0, w - 0.26, h, SILVER, EDGE)
    fan7hu(a, 0.15, SLOTS_Y + SLOTS_H + 0.01, w - 0.3, HU - 0.02)
    # air filter and fibre tray below the slots
    a.r(0.15, 0.01, w - 0.3, HU - 0.02, "#EDEFF2", EDGE, 0.01)
    a.es([(0.2 + i * 0.04, 0.06 + j * 0.05) for i in range(int((w - 0.4) / 0.04)) for j in range(4)], 0.009, "#AEB5BF")
    filled = dict(modules)
    half = SLOTS_H / 2
    for key, y in (("A", SLOTS_Y + half), ("B", SLOTS_Y)):
        if key in filled:
            filled[key](SH7_X0, y, a)
        else:
            a.r(SH7_X0, y, SLOT_W, half, SLOT, SLOT_EDGE)
    taken = set()
    for n in range(1, 21):
        if n in taken:
            continue
        if n in filled:
            filled[n](slot_x(n), SLOTS_Y, a)
            if filled[n] is psu7hu_ac:
                taken.add(n + 1)
        else:
            a.r(slot_x(n), SLOTS_Y, SLOT_W, SLOTS_H, SLOT, SLOT_EDGE)
    return a


# ------------------------------------------------------ fibre accessories

def lc_panel(n=12, u=1):
    """A generic 19-inch LC patch panel with n duplex single-mode adapters."""
    w, h = RACK, u * HU
    a = Art(w, h)
    ears(a, w, h)
    a.r(0.13, 0, w - 0.26, h, "#3A3F47", EDGE)
    rows = 1 if n <= 24 else 2
    per = (n + rows - 1) // rows
    pitch = min(0.1, (w - 0.5) / per)
    x0 = (w - per * pitch) / 2
    for r in range(rows):
        y = h / 2 - 0.045 if rows == 1 else (h * 0.55 if r == 0 else h * 0.12)
        for i in range(min(per, n - r * per)):
            x = x0 + i * pitch + pitch * 0.12
            a.r(x, y, pitch * 0.76, 0.09, LC_BLUE, "#1D4E9E", 0.008, 0.3)
            a.rs([(x + pitch * 0.12, y + 0.025, pitch * 0.2, 0.04), (x + pitch * 0.44, y + 0.025, pitch * 0.2, 0.04)], HOLE, None)
    return a


# ------------------------------------------------------------------ shapes

SHAPES = [
    # name, model, product line, art, note
    ("SH1R", "SH1R", "FSP 3000R7 HD shelves", sh1r(), "1 HU high-density shelf, front: CEM-3, traffic slots 1 (lower) and 2 (upper), fibre tray"),
    ("MA-2C5LT", "MA-2C5LT", "FSP 3000R7 HD traffic modules", ma2c5lt(), "Add-drop muxponder: 5 client QSFP (C1-C20), 2 network QSFP28 (N1, N2)"),
    ("MP-2B4CT", "MP-2B4CT", "FSP 3000R7 HD traffic modules", mp2b4ct(), "Muxponder: 4 client QSFP28 (C1-C4), 2 network ports N1, N2 (LC)"),
    ("SH1R with MP-2B4CT and MA-2C5LT", "SH1R", "FSP 3000R7 HD shelves", sh1r([(1, mp2b4ct), (2, ma2c5lt)]), "SH1R with MP-2B4CT in slot 1 and MA-2C5LT in slot 2"),
    ("SH7HU", "SH7HU", "FSP 3000R7 shelves", sh7hu(), "7 HU shelf, front: fan unit, slots A, B and 1-20, air filter"),
    ("SH7HU with NCU-II, SCU and PSUs", "SH7HU", "FSP 3000R7 shelves", sh7hu([("A", ncu2), ("B", scu), (1, psu7hu_ac), (19, psu7hu_ac)]), "SH7HU master shelf: NCU-II in A, SCU in B, PSU/7HU-AC in 1+2 and 19+20"),
    ("NCU-II", "NCU-II", "FSP 3000R7 management", ncu2(), "Network control unit, half height (port layout schematic)"),
    ("SCU", "SCU", "FSP 3000R7 management", scu(), "Shelf control unit, half height: SFP ports U and D"),
    ("PSU/7HU-AC", "PSU/7HU-AC", "FSP 3000R7 power", psu7hu_ac(), "AC power supply for the SH7HU, two slots wide"),
    ("LC patch panel 12", "LC 12 x duplex", "Fibre patch panels", lc_panel(12), "Generic 1 HU panel with 12 duplex LC adapters"),
    ("LC patch panel 24", "LC 24 x duplex", "Fibre patch panels", lc_panel(24), "Generic 1 HU panel with 24 duplex LC adapters"),
]

# --------------------------------------------------------------- the file


def guid(name):
    d = hashlib.md5(("plano-adva-fsp3000:" + name).encode()).hexdigest().upper()
    return "{%s-%s-%s-%s-%s}" % (d[:8], d[8:12], d[12:16], d[16:20], d[20:32])


def master_xml(name, model, line, art, maker):
    """Like the UniFi master, with this maker's shape data and the label
    below the shape."""
    xml = U.master_xml(name, model, line, art)
    return xml.replace(U.prop("Manufacturer", "Manufacturer", "Ubiquiti"), prop("Manufacturer", "Manufacturer", maker))


def build(path, title, shapes):
    q = {"'": "&apos;"}
    types = [("/visio/document.xml", "application/vnd.ms-visio.stencil.main+xml"), ("/visio/masters/masters.xml", "application/vnd.ms-visio.masters+xml"), ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"), ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml")]
    parts, entries, master_rels = {}, "", []
    for index, (name, model, line, art, note) in enumerate(shapes, 1):
        maker = "Generic" if line == "Fibre patch panels" else MAKER
        n = escape(name, q)
        prompt = escape(f"{maker} {line}: {note}", q)
        keywords = escape(f"ADVA,FSP 3000,FSP 3000R7,DWDM,{line},{name},{model}", q)
        entries += (
            f"<Master ID='{index}' NameU='{n}' IsCustomNameU='1' Name='{n}' IsCustomName='1' Prompt='{prompt}' IconSize='1' AlignName='2' MatchByName='0' IconUpdate='0' UniqueID='{guid(name)}' BaseID='{guid('base:' + name)}' PatternFlags='0' Hidden='0' MasterType='2'>"
            f"<PageSheet LineStyle='0' FillStyle='0' TextStyle='0'>{cell('PageWidth', num(art.w))}{cell('PageHeight', num(art.h))}{cell('ShdwOffsetX', '0.125')}{cell('ShdwOffsetY', '-0.125')}"
            f"{cell('PageScale', '1', unit='IN_F')}{cell('DrawingScale', '1', unit='IN_F')}{cell('DrawingSizeType', '4')}{cell('DrawingScaleType', '0')}{cell('InhibitSnap', '0')}{cell('ShapeKeywords', keywords)}</PageSheet>"
            f"<Icon>\n{icon(art)}</Icon><Rel r:id='rId{index}'/></Master>"
        )
        parts[f"visio/masters/master{index}.xml"] = f"{HEAD}<MasterContents {MAIN}><Shapes>{master_xml(name, model, line, art, maker)}</Shapes></MasterContents>"
        master_rels.append((f"rId{index}", REL + "master", f"master{index}.xml"))
        types.append((f"/visio/masters/master{index}.xml", "application/vnd.ms-visio.master+xml"))
    parts["visio/masters/masters.xml"] = f"{HEAD}<Masters {MAIN}>{entries}</Masters>"
    parts["visio/masters/_rels/masters.xml.rels"] = rels(master_rels)
    parts["visio/document.xml"] = document_xml()
    parts["visio/_rels/document.xml.rels"] = rels([("rId1", REL + "masters", "masters/masters.xml")])
    parts["_rels/.rels"] = rels([
        ("rId1", REL + "document", "visio/document.xml"),
        ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
        ("rId3", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties", "docProps/app.xml"),
    ])
    parts["docProps/core.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{escape(title)}</dc:title><dc:subject>ADVA FSP 3000R7 DWDM shapes</dc:subject><dc:creator>{AUTHOR}</dc:creator><cp:keywords>ADVA, FSP 3000, DWDM, optical</cp:keywords>"
        f"<dc:description>Schematic front views of ADVA FSP 3000R7 shelves and modules. © 2026 {AUTHOR}. Not made or endorsed by Adtran Networks.</dc:description><cp:lastModifiedBy>{AUTHOR}</cp:lastModifiedBy></cp:coreProperties>"
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


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else HERE
    os.makedirs(out, exist_ok=True)
    build(os.path.join(out, "ADVA FSP 3000R7.vssx"), "ADVA FSP 3000R7", SHAPES)
    print(f"ADVA FSP 3000R7.vssx: {len(SHAPES)} shapes")


if __name__ == "__main__":
    main()
