Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# agent.md - instructions for AI coding agents working on AtlasA0

Read this first. It tells you what the project is for, how it is laid out, how to run and check it,
and what not to break. Details live in `architecture.md`, `requirements.md` and `milestone.md`.

## Purpose
Generate maps of Pakistan (country, province, district, city) from OpenStreetMap for two uses:
1. **GIS applications** (ArcMap, QGIS, the owner's project viewer): georeferenced TIFF, GeoJSON, CSV/Excel.
2. **Physical prints**: A0 (841 x 1189 mm) PNG posters, sharp at 200-300 dpi.

Optional layers: receptors / points of interest (hospitals, schools, etc.). Everything can be requested in one go
(batch of mixed levels).

## Layout
```
atlasa0/config.py   settings only: themes, MAP_TYPES, PROVINCES, POI_CATEGORIES/PRESETS, POI_FILE_SUFFIX, match_province, resolve_pois
atlasa0/osm.py      ONLY module that touches the network: boundaries, features, roads, districts, POIs, cache
atlasa0/render.py   drawing: make_map (city/district, all map types + POI overlay), make_province_map, make_country_map
atlasa0/export.py   PNG, georeferenced TIFF (+ .tfw/.prj), POI files (csv, geojson, xlsx, summary)
atlasa0/api.py      generate_map, run_batch, find_receptors, export_receptors, list_districts
atlasa0/cli.py      flags -> jobs -> run_batch
examples/jobs.json  sample batch file
```
Dependency direction: `cli -> api -> render -> osm/export -> config`. Never import upward.

## Run
```
pip install -r requirements.txt
python -m atlasa0 --list-types | --list-poi | --list
python -m atlasa0 Peshawar --type receptors --format png tiff
python -m atlasa0 --country --province kpk --district Swat --in kpk --dry-run
```
`--dry-run` lists the planned jobs without downloading anything. Outputs go to `output/`, cache to `cache/`.

## Rules (do not break)
1. **Network only in `osm.py`** (plus tile download inside the satellite/topo branch of `make_map`). Wrap failures so one
   bad layer returns an empty result instead of crashing the map.
2. **One failed job must never stop a batch.** Keep the try/except in `run_batch`; report failures at the end.
3. **Draw in the region's UTM zone** (country: EPSG:32642). Do not draw in lat/lon; pixels must be square so the TIFF
   world file is correct.
4. **TIFF = map area only** (axes bbox, no title). Keep `.tfw` + `.prj` writing; embedding the CRS with `rasterio` is optional.
5. **File names are a contract** (the viewer and `--skip-existing` rely on them). Pattern:
   `city: <city>[_<type>][_poi_<names>]_A0_<dpi>dpi.png`,
   `district_<province>_<district>...`, `province_<province>_A0_...`, `country_<name>_A0_...`.
   Receptor files: suffixes in `config.POI_FILE_SUFFIX`.
6. **Keep `config.py` free of heavy imports** (no geopandas/osmnx) so it can be imported anywhere.
7. **Attribution is mandatory** on every map: "Map data (c) OpenStreetMap contributors" (+ Esri / OpenTopoMap credits for
   satellite / topo). Keep the boundary disclaimer on country/province maps.
8. **Do not overstate accuracy.** OSM completeness varies (small clinics, village schools, some districts). Counts are
   indicative, not an official inventory.
9. Province/country queries must use `overview_query_polygon` (simplified polygon, one request).

## Conventions
- Python 3.9+, plain functions, no classes needed. Keep functions small; reuse `get_features`, `_roads`, `save_outputs`.
- Parameters flow CLI flag -> job dict key -> `generate_map` argument -> `make_*` argument. When you add an option, add it
  at all four places and to `README.md`.
- Print one progress line per step as `[<region>/<type>] ...`.
- CLI gotcha: options such as `--province` and `--district` take several values, so city names go **before** them.

## How to add things
| Task | Do this |
|------|---------|
| New map type | add to `MAP_TYPES` (config), add a data branch and a draw branch in `make_map` |
| New receptor category | add to `POI_CATEGORIES` (OSM tags, colour, marker); add to a preset if useful |
| New receptor file type | add to `POI_FILE_SUFFIX` and `write_poi_files`; add to `--poi-format` choices |
| New region level | lookup in `osm.py`, `LEVELS` + branch in `api.generate_map`, jobs in `cli.py` |
| New raster/vector output | writer in `export.py`, alias in `FORMAT_ALIASES` |

## Check your work
Live OSM downloads may be unavailable in the agent sandbox (no network, `osmnx`/`geopandas` not installed). Then:
1. Syntax: `python -m py_compile atlasa0/*.py`.
2. Undefined names: walk each module's AST for names that are used but never defined or imported.
3. Logic without the GIS libraries: stub `osmnx`, `geopandas`, `shapely` in `sys.modules`, then test the CLI
   (`--list*`, `--dry-run`, bad arguments), `run_batch` (failure isolation), `write_poi_files` (fake frame) and
   `_save_geotiff` (a small matplotlib figure; check the `.tfw` pixel size is square).
4. Say clearly what was **not** tested. The first real run (country + province + district + city, TIFF in ArcMap/QGIS,
   receptor counts vs known facilities) is the top item in `milestone.md`; never claim it was done unless it was.

## Documentation to keep in sync
- New or changed feature -> `README.md` (usage), `requirements.md` (FR row + status), `milestone.md` (checkbox).
- Structural change -> `architecture.md`.
- Status wording: done and checked in sandbox / coded but needs a real run / planned. Do not mark something verified
  that you could not run.

## Owner context
Owner works in GIS and remote sensing in Khyber Pakhtunkhwa and wants to integrate this into a project viewer. Prefers short,
practical answers; give copy-paste commands. Framework of the viewer is not decided (Flask / Django / Streamlit / other) -
ask before building viewer code.

## Open items (see `milestone.md`)
First live run and timings; verify district names for all provinces; viewer integration (background job queue);
merge the owner's own verified receptor list (CSV: name, category, lat, lon) with duplicate removal; distance rings
around a site (nearest receptor, counts within X km); vector exports (GeoPackage/Shapefile).

## Tests
Run `pytest` after any change (must stay green). Layout numbers live in `config.AXES_RECT` and the helpers `axes_aspect`, `fit_extent`, `nice_scale_km`, `poi_marker_size` in `render.py`; they are covered by `tests/test_geometry.py` - change tests and code together. `tools/calibrate.py` prints the calibration table. Live OSM behaviour is only tested by `tests/test_live.py` (ATLASA0_LIVE=1).

## Map elements
All furniture (legend, scale, north, grid, title, note, logo, credit) is in `atlasa0/furniture.py`; renderers call `apply_layout(...)` once. New element = add to `ELEMENTS`, draw in `apply_layout`, register artists with `_register` (so the TIFF can hide them), add a CLI flag and a test. Skills for Claude live in `skills/`.

## GUI
Keep all GUI logic in `gui_core.py` (no toolkit imports) and progress/cancel in `runtime.py`; `gui_tk.py` only lays out widgets. Use `runtime.log()` (cancel point) for stage messages and `say()` for messages that must not cancel. `Cancelled` is a BaseException so OSM wrappers' `except Exception` cannot swallow it. GUI callbacks arrive on a worker thread: marshal to the main thread. `tests/tk_stub.py` lets the panel run without a display; it does not check appearance.

## Your data layers and styles
- `layers.py`: `LayerSpec` (validated options) -> `load_layer` (geopandas; reprojects to the map UTM) -> `Prepared` features -> `draw_layers` (matplotlib only, testable without geopandas via duck-typed geometries). Keep reading and drawing separate.
- Sizes of markers/lines are millimetres on the A0 sheet; ring direction is forced (outline CCW, holes CW) because file formats disagree.
- Furniture styles live in `furniture.py` (`LEGEND_STYLES`, `NORTH_STYLES`, `SCALE_STYLES`, `POSITIONS`); add a style in the dict, the drawer, a test, and the GUI picks it up through `describe_options()`.
- Icons: edit `tools/make_icons.py`, run it, commit the PNGs. Every new file needs the author header (Author / Email / This code is not for sale).

## osmnx tag semantics (bug fixed Nov 2026)
`features_from_polygon(poly, {"a": x, "b": y})` returns features with a=x **OR** b=y. Never rely on two tags to narrow a query: request the most specific tag and filter the GeoDataFrame afterwards (see `osm.admin_areas`). Map labels go through `overview.place_labels`.

## Draw order (zorder)
Never hard-code a zorder for map content. Use `Z = draw_zorders(lay.draw_order)` and `zorder=Z["<group>"] (+ up to 0.9)`; groups are in `furniture.DRAW_GROUPS`. Map elements use `FURNITURE_Z` (30). User layers share the `your_data` band (`draw_layers(..., zorder=Z["your_data"], label_zorder=Z["labels"] + 0.3)`). GUI lists are shown top-first; data lists stay bottom-first.
