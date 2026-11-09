Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# DESIGN.md: AtlasA0

The visual rules for AtlasA0 in one place: how its maps look on paper and in GIS, and how its Tk
window looks. Code is the source of truth for the map palettes (`atlasa0/config.py`); this file names
every colour so tools can check them. `tests/test_design_sync.py` fails if the two drift apart.

## 1. Visual theme & atmosphere

Two surfaces with different jobs.

- **Maps (A0 print, GIS):** quiet, cartographic, legible from a metre away. Pale paper-like base
  (`light`) or a night base (`dark`); the data is the colour. Land-use tints are soft so roads, labels
  and your own layers sit on top. Nothing decorative: no gradients, shadows or clip-art on the map.
- **GUI (Tk panel):** a plain, native-looking work tool. System fonts and system colours, one teal
  accent, small icons. It must embed cleanly in the owner's project viewer, so it never imposes its own
  window chrome or fixed theme.

## 2. Color palette & roles

| Family | Tokens | Use |
|---|---|---|
| GUI | `color.bg`, `color.text`, `color.text-muted`, `color.primary`, `color.primary-text` | Window, text, helper text, brand teal, teal as text |
| Map themes | `color.map-light-*`, `color.map-dark-*` | Base map: bg, road, water, green, building, text, frame |
| Land use | `color.landuse-*` | Land-use map fills, legend swatches |
| Provinces | `color.province-tint-1..7` | Country map province fills |
| Transport and basemap overlays | `color.rail`, `color.buildings-light`, `color.roads-topo` | Map-type specific strokes and fills |
| Receptors | `color.poi-*` | Point-of-interest markers and legend |

Rules: map colours come from `config.py` (themes, land use, POI) and are never invented in a renderer;
`color.white` is only for marker edges, halos and roads over satellite imagery.

```design-tokens
// Generated from atlasa0/config.py and render.py; tests/test_design_sync.py keeps it honest.
color.bg = #F0F0F0   // GUI background: Windows default grey; Tk draws it, code does not set it
color.text = #000000   // GUI text: system default
color.text-muted = #555555   // GUI helper text
color.primary = #1F7A8C   // brand teal: icons and fills (not used for small text)
color.primary-text = #1A6B7B   // brand teal darkened to pass AA as text on the GUI grey
color.white = #FFFFFF   // marker edges, halos, satellite roads
color.map-light-bg = #F7F4EC
color.map-light-road = #3A3A3A
color.map-light-water = #9CCBE8
color.map-light-green = #CFE3BD
color.map-light-building = #D8D2C4
color.map-light-text = #1F1F1F   // also: map-light-frame
color.map-dark-bg = #0F1419
color.map-dark-road = #E8E8E8
color.map-dark-water = #1D3B5A
color.map-dark-green = #1C2F22
color.map-dark-building = #2A3139
color.map-dark-text = #F0F0F0   // also: map-dark-frame
color.landuse-residential = #E3CFA9
color.landuse-commercial = #F2A9A2   // also: landuse-retail
color.landuse-industrial = #C9B8DC
color.landuse-farmland = #ECE9A9   // also: landuse-farmyard
color.landuse-orchard = #D6E3A0
color.landuse-meadow = #D3E6BF
color.landuse-grass = #CFE3BD   // also: landuse-recreation-ground
color.landuse-park = #BFE0A8
color.landuse-forest = #9CCB8A   // also: landuse-wood
color.landuse-cemetery = #BCD0C0
color.landuse-military = #DBA3A3
color.landuse-construction = #D2C4B2   // also: landuse-brownfield
color.landuse-quarry = #C4B8A8
color.landuse-education = #F0DCA0
color.landuse-religious = #D8C0D8
color.landuse-other = #E6E3DC
color.province-tint-1 = #D6E6C4
color.province-tint-2 = #EBE2B8
color.province-tint-3 = #D3E3D9
color.province-tint-4 = #E8D6C4
color.province-tint-5 = #DCD8EA
color.province-tint-6 = #EAD3D3
color.province-tint-7 = #D3E3EA
color.rail = #8A3B3B   // railways on the transport map
color.buildings-light = #B9B09C   // buildings map, light theme
color.roads-topo = #7A2E2E   // roads over topo basemap
color.poi-hospitals = #D62728
color.poi-clinics = #FF7F0E
color.poi-pharmacies = #E377C2
color.poi-schools = #1F77B4
color.poi-colleges = #17BECF
color.poi-worship = #7F4F9F
color.poi-water-sources = #0A6EBD
color.poi-markets = #BCBD22
color.poi-police = #2F4F4F
color.poi-fire = #8C1C13
color.poi-fuel = #8C564B
color.poi-industry = #555555

// Typography
font.sans = DejaVu Sans, sans-serif   // matplotlib default, used for all map text
font.gui = Segoe UI, system-ui, sans-serif   // Tk default on Windows; code does not set a family

// Spacing: the GUI uses PAD = 6 px, so the grid is 2 px
space.base = 2

// Contrast pairs that must always pass (WCAG 2.x AA, 4.5:1)
pair = color.text on color.bg
pair = color.text-muted on color.bg
pair = color.primary-text on color.bg
pair = color.map-light-text on color.map-light-bg
pair = color.map-light-text on color.map-light-water
pair = color.map-light-text on color.map-light-green
pair = color.map-light-text on color.map-light-building
pair = color.map-dark-text on color.map-dark-bg
pair = color.map-dark-text on color.map-dark-water
pair = color.map-dark-text on color.map-dark-green
pair = color.map-dark-text on color.map-dark-building
```

## 3. Typography

- Map text uses matplotlib's default family (`font.sans`). Sizes are points on the A0 sheet and live in
  `furniture.py` and `render.py` (labels 62/48/36/26 pt, scale and ratio text, title and subtitle).
  Do not scale them by eye: check the A0 print and the calibration table (`tools/calibrate.py`).
- Title and place labels are bold; subtitle, note and credit are regular. No italics except user label
  styles.
- GUI text uses Tk's default font (`font.gui` on Windows). Do not hard-code a family; let the viewer's
  theme decide.

## 4. Component styling

- **Legend:** lists every land-use class and layer drawn, plus user items; styles are in
  `furniture.LEGEND_STYLES`. Swatches use the exact map colour.
- **Scale bar:** shows the print scale (for example 1:25,000 at A0) and kilometres. **North arrow:** styles in
  `furniture.NORTH_STYLES`.
- **Credit line:** always present (see do's and don'ts). **Note box** and **logo** are optional.
- **Receptor markers:** category colour fill, white edge, marker shape from `POI_CATEGORIES`; sizes are
  millimetres on the sheet.
- **GUI:** ttk widgets, labelled tabs with icons (`atlasa0/assets/icons`), groups as labelled frames,
  one primary action ("Make maps") at the bottom right.

## 5. Layout principles & spacing

- Sheet: A0 portrait, 33.11 x 46.81 in. Drawing area `config.AXES_RECT` (left 0.04, bottom 0.04, width
  0.92, height 0.86): title block above, credit line below.
- Draw in the region's UTM zone so pixels are square and the TIFF world file is correct.
- Furniture sits at the named positions in `furniture.POSITIONS`; map content uses `draw_zorders`, furniture
  uses `FURNITURE_Z`.
- GUI spacing is `PAD = 6` px, `space.base = 2` px grid. Keep new widgets on that grid.

## 6. Depth & elevation

Flat. Maps use fill, stroke and alpha only, ordered by the draw order (basemap, land use, water, roads,
buildings, your data, labels, furniture). No drop shadows. The GUI uses native ttk relief.

## 7. Do's and don'ts

- Do keep attribution on every map: "Map data (c) OpenStreetMap contributors" (plus Esri or OpenTopoMap for
  satellite and topo), and the boundary disclaimer on country and province maps.
- Do add a new colour to `config.py` and to this file together; run the design-md checks.
- Do keep the GeoTIFF clean (map area only) unless `--tiff-furniture` is set.
- Do keep a legible contrast between text and its background (the pairs above).
- Don't hard-code a hex colour, font family or zorder in a renderer; use the theme dict and `draw_zorders`.
- Don't put a gradient, shadow or decorative image on a map.
- Don't use colour alone to separate receptor categories; the marker shape differs too.
- Don't overstate accuracy; OSM data is indicative (see `agent.md`).

## 8. Responsive behavior

- Output sizes: A0 at 300 dpi (about 6 to 8 GB RAM) or 200 dpi on low-memory machines; the layout is
  proportional so both look the same.
- The GUI opens at 1020 x 900 and must work in any Tk container (frame, notebook tab, Toplevel), so it
  must not assume it owns the window.

## 9. Agent prompt guide

AtlasA0 maps are pale, flat and cartographic; the GUI is native and plain. Colours come from
`atlasa0/config.py` and are mirrored in the token block above; never type a raw hex in a renderer. After a
change that touches colour, font or padding, run
`python skills/design-md/tools/lint_design.py DESIGN.md` and
`python skills/design-md/tools/check_adherence.py atlasa0 --design DESIGN.md`, then `pytest`.
