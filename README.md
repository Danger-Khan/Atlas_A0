Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# AtlasA0

A0 print-ready and GIS-ready maps of Pakistan from OpenStreetMap: **country, provinces, districts, cities**,
in several map styles, as PNG and georeferenced TIFF (ArcMap / QGIS).

See `requirements.md` (what it must do), `architecture.md` (how it is built) and `milestone.md` (what is done and next).
AI coding agents: read `agent.md` first.

## Layout
```
atlasa0_project/
  atlasa0/
    config.py   themes, map types, province catalogue, line widths
    osm.py      OSM downloads (roads, features, districts) + cache
    render.py   drawing: city/district (all map types), province, country
    export.py   PNG, georeferenced TIFF (.tif + .tfw + .prj), POI GeoJSON/CSV
    api.py      generate_map(), run_batch(), list_districts()   <- use from your viewer
    cli.py      command line
  examples/jobs.json   sample batch file
  output/      generated maps (created on first run)
  cache/       OSM download cache (set ATLASA0_CACHE to move it)
  requirements.md  architecture.md  milestone.md  agent.md  requirements.txt
```

## Install
```
pip install -r requirements.txt
```

## Command line (everything can be mixed in one run)
```
python -m atlasa0 --list-types
python -m atlasa0 Peshawar                                  # one city, A0 PNG
python -m atlasa0 Peshawar --type landuse water --format png tiff
python -m atlasa0 --country --format png tiff               # whole Pakistan
python -m atlasa0 --province kpk sindh                      # province overviews
python -m atlasa0 --district Swat Peshawar --in kpk --type satellite --format tiff
python -m atlasa0 --districts-of kpk --dpi 200 --skip-existing
python -m atlasa0 Lahore --country --province kpk --district Swat --in kpk --format png tiff --dry-run
```
Put city names **before** `--province` / `--district` (those options take several values).

Useful options: `--dpi 200`, `--landscape`, `--theme dark`, `--outdir DIR`, `--skip-existing`
(resume), `--dry-run` (count jobs only), `--manifest files.json`, `--radius-km 10`.

### Batch file (`--batch jobs.json`)
```json
[
  {"level": "country", "formats": ["png", "tiff"]},
  {"level": "province", "region": "kpk"},
  {"level": "district", "region": "Swat", "province": "kpk", "types": ["street", "landuse"]},
  {"level": "city", "region": "Peshawar", "types": ["street", "water"], "dpi": 200}
]
```
Anything a job doesn't set comes from the command-line options.

## Receptors / points of interest (hospitals, schools, ...)
Overlay them on any city or district map, or use the dedicated `receptors` map type:
```
python -m atlasa0 --list-poi                                  # categories and presets
python -m atlasa0 Peshawar --type receptors                   # preset: hospitals, clinics, schools, colleges, worship, water
python -m atlasa0 Peshawar --type landuse --poi hospitals schools --poi-labels
python -m atlasa0 --district Swat --in kpk --poi health --poi-data --format png tiff
python -m atlasa0 Peshawar --district Swat --in kpk --poi-only --poi receptors     # data only, no map
```
- Categories: hospitals, clinics, pharmacies, schools, colleges, worship, water_sources, markets, police, fire, fuel, industry.
- Presets: `receptors`, `health`, `education`, `emergency`, `all`.
- `--poi-data` / `--poi-only` save `*_poi.geojson` (WGS84) and `*_poi.csv` (lon/lat + UTM x/y) for ArcMap/QGIS.
- Choose the file type with `--poi-format`: `csv` (table), `geojson`, `xlsx` (Excel workbook: Receptors + Summary sheets), `summary` (small CSV, one row per category with its count). Default is csv + geojson; you can list several, e.g. `python -m atlasa0 Peshawar --poi-only --poi receptors --poi-format csv xlsx summary`.
  CSV columns: category, name, lon, lat, x_utm, y_utm (UTF-8 with BOM so Urdu/Pashto names open correctly in Excel).
- Points come from OpenStreetMap; coverage of small facilities (BHUs, village schools) varies - check against local records.
- POI maps are for cities and districts. Province/country maps ignore `--poi`.

## From your viewer (Python)

```python
from atlasa0 import generate_map, run_batch, list_districts, find_receptors, export_receptors

list_districts("kpk")
generate_map("Swat", level="district", province="kpk", map_type="landuse",
             formats=("png", "tiff"), outdir="static/maps")
generate_map(level="country", formats=("png", "tiff"), outdir="static/maps")
result = run_batch(jobs, outdir="static/maps", skip_existing=True, formats=("png", "tiff"))
# result = {"files": [{path, format, level, region, map_type, skipped}], "failed": [...]}

generate_map("Peshawar", map_type="receptors", pois=["hospitals", "schools"], poi_data=True)
r = find_receptors("Swat", level="district", province="kpk", pois="receptors")   # data only
r["counts"]   # {"hospitals": 12, "schools": 640, ...}
r["table"]    # pandas DataFrame: category, name, lon, lat
export_receptors("Swat", "district", "kpk", "receptors", outdir="static/data")  # GeoJSON + CSV
```
A0 at 300 dpi takes minutes: run it as a background job and cache the output; use `dpi=100` for previews.

## Outputs
- `*.png` - full poster with title, coordinates, scale bar, attribution.
- `*.tif` + `*.tfw` + `*.prj` - map area only, georeferenced (UTM zone of the region, metres; country map UTM 42N).
  Add the `.tif` in ArcMap/QGIS; keep the three files together.

## Notes
- Map data (c) OpenStreetMap contributors. Satellite: Esri imagery. Topo: OpenTopoMap.
- Boundaries are as mapped in OpenStreetMap; verify against Survey of Pakistan for official use.

## Tests and calibration

```
pip install -r requirements-dev.txt
pytest                      # offline: 94 tests (config, layout maths, GeoTIFF/world file, receptor exports, CLI, batch, file naming)
ATLASA0_LIVE=1 pytest tests/test_live.py -v -s   # real OSM downloads, small area, low dpi (needs internet)
python tools/calibrate.py   # prints A0 pixel sizes, scale bars, marker sizes, tile zoom, map fill, TIFF pixel check
```
Offline tests use stand-ins for osmnx/geopandas/shapely when they are not installed; the live tests are the only ones that touch OpenStreetMap.

## Map elements (legends, scale, north arrow, grid, title, note, logo)
```
python -m atlasa0 Peshawar --elements title legend scale north grid credit \
    --legend-item "Proposed site=#d62728" "Canal=#1f77b4" --legend-pos center right \
    --title "Peshawar - site selection" --subtitle "PCSIR" --note "Draft - for discussion" --logo logo.png --grid-km 5
```
`--list-elements` shows them; default: title legend scale north credit (grid is opt-in). The scale bar shows 0/half/full km and the print scale (e.g. 1:17,000 at A0).
Python: `generate_map("Peshawar", layout={"elements": ["scale","north"], "legend_items": [["Site","#d62728"]]})`; in batch JSON put the same dict under `"layout"`.
The georeferenced TIFF stays clean (no legend/scale/north/grid) unless `--tiff-furniture`.

## Local variables
`ATLASA0_OUTDIR`, `ATLASA0_DPI`, `ATLASA0_THEME` (defaults for the flags), `ATLASA0_CACHE` (OSM cache), `ATLASA0_LIVE=1` (live tests).

## Skills
`skills/` holds three Claude skills (atlasa0-maps, atlasa0-receptors, atlasa0-qa) describing the tools, variables and procedure for each job.

## Window (GUI) - for your Python project viewer
```
python -m atlasa0 --gui          # or: python run_gui.py
```
Five tabs: Where (country / provinces / cities / districts), Map (types, formats, quality, theme), Receptors, Elements (legend, scale, north, grid, title, note, logo), Output (folder, skip-existing, save/load settings, export as batch file). Below: estimate (pixels, RAM), progress bar, log, list of produced files (double-click to open), Cancel.
Embed in your viewer: `AtlasPanel(parent, on_files=viewer.load_layers)` - `on_files` receives the new files (GeoTIFF/GeoJSON) so the viewer can add them as layers. See `examples/embed_in_viewer.py` (also a PyQt/PySide sketch).
Quality presets: Preview 100 dpi (fast), Draft 200, Print 300. Settings are remembered in `~/.atlasa0_preset.json`.

## Your own points, lines and polygons (shapefiles etc.)
Add any number of layers on top of the map: shapefile (`.shp`), GeoJSON, GeoPackage, KML, GML, or a CSV with lon/lat columns.
```
python -m atlasa0 Peshawar --layer "sites.shp;name=Proposed sites;color=#d62728;alpha=0.8;marker=triangle;size_mm=8;label_field=NAME" \
                           --layer "canal.geojson;color=#1f77b4;line_style=dashed;width_mm=1.2" \
                           --layer "zones.shp;color=#2ca02c;alpha=0.35;hatch=diagonal;fit=1"
```
| Option | Meaning |
|---|---|
| `color`, `edge_color` | fill / point / line colour and outline colour (`#rrggbb` or a colour name) |
| `alpha` | transparency: 0 = invisible ... 1 = solid (default: polygons 0.4, points and lines 1) |
| `marker` | circle, square, triangle, triangle down, diamond, star, plus, cross, pentagon, hexagon, ring, hollow square, hollow triangle, dot |
| `size_mm`, `width_mm`, `edge_width_mm` | marker size, line width, outline width in **millimetres on the printed sheet** |
| `line_style` | solid, dashed, dotted, dash-dot |
| `hatch` | none, diagonal, reverse diagonal, cross-hatch, dots, grid, horizontal, vertical |
| `label_field`, `label_size`, `label_halo` | write an attribute next to each feature |
| `name`, `legend` | legend text, and whether to list the layer |
| `fit` | include the layer when choosing the map extent |
| `crs`, `x_col`, `y_col` | for files without a CRS (default EPSG:4326) and CSV column names (auto-detected: lon/lat/x/y...) |
Layers are drawn in the order given (last on top), in the map's UTM zone, so they line up with the base map and the GeoTIFF. `python -m atlasa0 --list-styles` lists all styles. Python: `generate_map(..., layers=[{...}])`; batch JSON: `"layers": [...]` per job.

## Legends, north arrows, scales and labels
```
python -m atlasa0 Peshawar --legend-style horizontal --legend-pos "lower center" --legend-title "Key" \
    --north-style compass --north-pos "upper right" --north-size 1.5 \
    --scale-style double --scale-units km --scale-pos "lower left" --scale-divisions 6 \
    --text-label "Hayatabad@71.43,33.98;size=50;bold=1;box=1" --text-label "Canal@71.5,34.0;rotation=30;color=#1f77b4"
```
- **Legend** styles: box, compact, minimal, horizontal; any of 8 positions; own heading and columns; your layers and `--legend-item` entries are listed.
- **North arrow** styles: arrow, classic, compass, circle; any corner; size factor.
- **Scale** styles: bar, line, double (km + miles), ratio (text only, 1:N); units km / mi / m; any corner; 1-10 segments.
- **Labels**: free text at lon/lat with size, colour, bold, italic, halo or box, rotation. Labels outside the map are skipped with a message.
- Two elements cannot share a position (you get a clear error); the receptor legend automatically takes a free slot.

## GUI icons
Icons are PNG files in `atlasa0/assets/icons` (drawn by `python tools/make_icons.py`). The window now has seven tabs: Where, Map, **Your data** (add/edit/remove/reorder layers with a live style preview), Receptors, Elements, **Styles & labels**, Output.

## Author
Author: Imaad Ullah Khan Yameen - yameenimaad@gmail.com - *This code is not for sale*. Every source and document file carries this notice; JSON files carry it as `author` / `email` / `license` fields (batch files may be `{"author":..., "jobs":[...]}`); `python -m atlasa0 --about` prints it.

## File names and the Settings tab
By default files get automatic names (`peshawar_A0_300dpi.png`). To choose your own, use a template:
```
python -m atlasa0 Peshawar Lahore --name "Map_{region}_{date}"      # -> Map_peshawar_2026-11-06.png, Map_lahore_2026-11-06.png
```
Fields: `{region} {level} {type} {province} {dpi} {date}`. No extension (`.png` / `.tif` is added). Spaces become `_` and characters Windows forbids are removed. Several maps in one run need `{region}` (and `{type}` for several map types) or AtlasA0 refuses, so files can never overwrite each other. Python: `generate_map(..., filename="Map_{region}")`; batch JSON: `"filename": "..."` per job.

GUI tab **7 Settings**: *File names* (Automatic / My own name, with a live example), output folder, skip existing, **remember my choices automatically when I press Run**, **open the output folder when finished**, Save/Load settings, **Reset to automatic defaults**, export batch file.

## Resolution and size estimates
DPI goes from 50 to 500 (`--dpi 500`; GUI: slider in tab 2 with quick buttons 100-500). Before running, the GUI (bottom bar and next to the slider) and `--dry-run` show pixels, RAM, OpenStreetMap download and total file size.
- First estimates are rough guesses; after each real run AtlasA0 records the real file sizes and the MB added to the OSM cache in `~/.atlasa0_stats.json` (or `$ATLASA0_STATS`) and later estimates say "measured on your PC".
- Line maps grow about as dpi^1.4 (a dense synthetic A0 line map measured 6 / 28 / 55 MB PNG at 100 / 300 / 500 dpi); satellite/topo grow with the pixel count.
- RAM: saving the PNG measured 1.6 GB at 500 dpi on that synthetic map; GeoTIFF adds image copies. The estimate adds ~1.5 GB for OSM data - building footprints of a big district can need more.
- Downloads are counted per map; places already in the cache download almost nothing.

## Known problem fixed: province map full of overlapping names (Khyber Pakhtunkhwa, Nov 2026)
**What went wrong.** The first real KP province map showed hundreds of jumbled labels ("... Tehsil", "... Division", "... District" on top of each other), the map used only half of a landscape sheet, and no rivers were visible.

**Why.**
1. *Wrong OSM query.* The code asked osmnx for `{"boundary": "administrative", "admin_level": "6"}`. osmnx returns features matching **any** of the tags, not all of them, so every administrative area came back: divisions (level 5), districts (6), tehsils (7) and more. All of them were drawn and labelled. The same mistake affected the district list (GUI / `--districts-of`) and the provinces on the country map (`admin_level 4`).
2. *No label collision check.* Every name was written at 26 pt in the middle of its area, so small districts around Peshawar overlapped even with correct data.
3. *Orientation.* KP is taller than wide; on a landscape sheet half the paper is empty.
4. *Silent failures.* A failed OSM request (e.g. rivers for a whole province on a busy server) returned an empty result with no message.

**Fix.**
1. Only `admin_level` is requested and the result is filtered to exactly that level (`osm.admin_areas`, `overview.filter_admin`); names containing "Tehsil", "Division", "Union Council" are dropped at district level as a safety net. The log says how many features were ignored. The download is also much smaller.
2. District names are placed biggest-area first, without the word "District", wrapped onto two lines or made smaller when they collide, and left out only if there is still no room (the log lists them) (`overview.place_labels`). Country-map province names use the same placement.
3. New orientation option: `--orientation auto|portrait|landscape` (GUI: *Sheet* in tab 2). **auto is the new default**: wide areas -> landscape, tall areas such as KP -> portrait. `--landscape` still works.
4. Failed OSM requests are logged, and province/country maps log counts ("36 districts, 2400 highway segments, 0 river features") with a warning when rivers are missing; rivers are drawn thicker and above the district lines.

**If it happens again:** read the log lines for the province; if rivers or districts are 0, run again (OSM servers are sometimes busy, and the cache keeps what already downloaded). If a district name is missing, it was left out for lack of room - see the log.

## Draw order - what is printed on top of what
Everything on the map belongs to one of these groups. They are printed bottom -> top in this order (default):

| # | Group | What it contains |
|---|---|---|
| 1 | `basemap` | Satellite / topo image |
| 2 | `landuse` | Land fill, parks, land use, province colours |
| 3 | `buildings` | Building footprints |
| 4 | `water` | Water areas, rivers, canals |
| 5 | `boundaries` | District / province boundary lines |
| 6 | `roads` | Roads and railways |
| 7 | `grid` | UTM grid lines |
| 8 | `mask` | Blank area outside a district + its outline |
| 9 | `your_data` | Your layers (shapefile, GeoJSON, CSV...) |
| 10 | `receptors` | Receptor / point-of-interest markers |
| 11 | `labels` | Names (districts, receptors, your layer labels and text labels) |

Title, legend, scale bar, north arrow and note are always above all of these.

- **GUI:** tab *6 Styles & labels* -> *Draw order*. The list is shown **top first** with numbers, "(top)" and "(bottom)"; *Move up (more on top)*, *Move down*, *Default order*. The run log prints the order used.
- **Your layers:** tab *3 Your data* is also shown top first and numbered ("2. (top)", "1. (bottom)"); *Move up* brings a layer forward. All your layers sit together at the `your_data` step. (Before this change the list ran bottom-to-top without numbers, so *Move up* actually pushed a layer down - fixed.)
- **CLI:** `--draw-order "landuse,boundaries,roads,water"` (bottom -> top). Groups you leave out keep their default place. `--list-styles` lists the groups. Python / batch JSON: `layout={"draw_order": [...]}`.
- Typical changes: rivers over roads -> move `water` above `roads`; your polygons under the roads -> move `your_data` below `roads` (and lower their opacity); receptor markers above your layers is the default.
