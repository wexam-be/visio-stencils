# Visio stencils

Stencils (`.vssx`) for Microsoft Visio and other programs that read Visio
files, such as Plano.

## Ubiquiti UniFi

342 shapes of the UniFi product range, in `Ubiquiti UniFi/`:

| Stencil | Shapes |
|---|---|
| UniFi - Gateways and Consoles | 34 |
| UniFi - Switches | 76 |
| UniFi - WiFi and Bridges | 64 |
| UniFi - Protect Cameras | 57 |
| UniFi - Protect Recorders and Sensors | 36 |
| UniFi - Access, Talk and Connect | 51 |
| UniFi - Storage, Power and Mobility | 24 |
| UniFi - All Products | 342 |

`UniFi - Overview.vsdx` is a drawing that shows every shape, one page for
each stencil.

![Preview](Ubiquiti%20UniFi/preview.png)

Every shape is a group of plain vector shapes, labelled with its model
number, with connection points and shape data: manufacturer, product line,
product, model, and empty fields for a name, an IP address, a MAC address
and a location.

The drawings are schematic. They follow Ubiquiti's public device catalogue,
its product pictures and its port diagrams, but they are drawn from scratch
and are not exact likenesses.

To build the stencils again, for instance after adding a product to the
lists in the script (needs Python 3 and Pillow):

```bash
python3 "Ubiquiti UniFi/make_unifi_stencils.py"
```

## ADVA FSP 3000R7

11 shapes in `ADVA FSP 3000/ADVA FSP 3000R7.vssx`, seen from the front:

| Shape | What it shows |
|---|---|
| SH1R | 1 HU high-density shelf: CEM-3, traffic slots 1 (lower) and 2 (upper), fibre tray |
| SH1R with MP-2B4CT and MA-2C5LT | The same shelf with both cards fitted |
| MA-2C5LT | Client QSFP C17–C20, C13–C16, C9–C12, C5–C8, C1–C4, network QSFP28 N2, N1 |
| MP-2B4CT | Client QSFP28 C4–C1, network ports N2 and N1 (LC, R above T) |
| SH7HU | 7 HU shelf: fan unit with shelf LEDs, slots A, B and 1–20, air filter |
| SH7HU with NCU-II, SCU and PSUs | Master shelf: NCU-II in A, SCU in B, PSU/7HU-AC in 1+2 and 19+20 |
| NCU-II, SCU, PSU/7HU-AC | The modules on their own, to place in an SH7HU |
| LC patch panel 12, LC patch panel 24 | Generic 1 HU panels with duplex single-mode LC adapters |

![Preview](ADVA%20FSP%203000/preview.png)

The faceplates follow the figures in ADVA's manuals: the FSP 3000R7
High-Density Subshelf Guide (R17.2), the Installation and Commissioning
Manual and the Hardware Description (R13.3). Two things are not shown in
those figures and are drawn schematically: where the NCU-II has its ports,
and whether slot A of the SH7HU is above slot B (drawn as on the SH9HU).
All shapes share the scale of the UniFi shapes (a 19-inch front is 2.8 in,
1 HU is 0.28 in), so a module drops exactly into its slot.

To build the stencil again (needs Python 3 and Pillow, and uses the writer
in the UniFi script):

```bash
python3 "ADVA FSP 3000/make_fsp3000_stencils.py"
```

## Author and licence

© 2026 Eric De Pessemier. Licence: GPL-3.0-or-later.

Ubiquiti and UniFi are trademarks of Ubiquiti Inc. These stencils are not
made or endorsed by Ubiquiti. ADVA and FSP are trademarks of Adtran
Networks SE; the ADVA stencil is not made or endorsed by Adtran.
