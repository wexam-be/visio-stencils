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

## Author and licence

© 2026 Eric De Pessemier. Licence: GPL-3.0-or-later.

Ubiquiti and UniFi are trademarks of Ubiquiti Inc. These stencils are not
made or endorsed by Ubiquiti.
