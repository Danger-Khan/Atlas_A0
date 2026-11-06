Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# AtlasA0 - Architecture

## 1. What it is
A Python library with a command line that turns OpenStreetMap data into **A0 print posters** and
**georeferenced rasters** for **country, province, district and city**, in several map styles, with
optional **receptor / point-of-interest** layers. It is built to be called from a project viewer.

Style: layered library (config -> data access -> map elements -> rendering -> export -> API -> CLI / GUI), plus tests, tools and Claude skills around it. No server, no database;
files on disk are the output and the cache.

## 2. System context
```
 You (CLI)  ----\                                   OpenStreetMap services
 Project viewer --> [ AtlasA0 ] --- internet --->   - Nominatim (place -> boundary)
 (Python call)  /       |                           - Overpass   (roads, water, POIs, boundaries)
                        |                           Tile servers (satellite / topo, optional)
                        v
              output/  *.png   *.tif + .tfw + .prj   *_poi.geojson / .csv / .xlsx / _summary.csv
              cache/   (OSM responses, reused on re-runs)
 Claude skills (skills/) --> drive the CLI / API on the user's behalf
```
Consumers of the files: ArcMap / QGIS (TIFF, GeoJSON, CSV) and the printer (PNG).

## 3. Modules and dependencies
```
 gui_tk.py ──> gui_core.py ──┐
 (window)       (form logic)  │
 cli.py ─────────────────────>┴─> api.py ──> render.py ──> osm.py ──> config.py
                                    │           │  │
                                    │           │  └──────> furniture.py ──> config.py
                                    │           └─────────> export.py ──> config.py
                                    └──> furniture.py (Layout validation), osm.py, export.py, config.py
 runtime.py (log / cancel / JobRunner) is used by api, render, osm, export and the GUI; it imports nothing heavy.
```
| Module | Responsibility | Knows about |
|--------|----------------|-------------|
| `config.py` | Themes, line widths, A0 size, `AXES_RECT` (drawing area), map types, province catalogue, POI categories and presets, name matching. No heavy imports. | nothing |
| `osm.py` | All network access: place boundaries, features, road networks, district lists, POIs. Wraps failures (empty result instead of crash). Disk cache. | config |
| `furniture.py` | **Map elements.** `Layout` (validated options, position-conflict check), `apply_layout`, and the drawers: title block, legend (4 styles, 8 positions; land use + your layers + custom items + receptor legend), scale (bar / line / double / ratio; km / mi / m), north arrow (arrow / classic / compass / circle), UTM grid, free text labels at lon/lat, note, logo, credit. Registers its artists so the TIFF can leave them out. No network. | config, runtime |
| `layers.py` | **Your own data.** `LayerSpec` (colour, alpha, marker, line style, hatch, labels, legend, fit), spec-string parser, `load_layer` (geopandas: shp/geojson/gpkg/kml/csv -> UTM), `Prepared` features, `draw_layers` (matplotlib collections; returns legend handles). Only `load_layer` needs geopandas. | runtime |
| `icons.py` | GUI icon loader (PNG files in `assets/icons`; missing file = no icon). | nothing |
| `render.py` | Map drawing (draws your layers after the base map, before the elements). `make_map` (city/district, all map types + POI overlay), `make_province_map`, `make_country_map`. Decides extent (`axes_aspect`, `fit_extent`), layers, marker size; hands elements to `furniture.apply_layout`. | osm, furniture, export, config |
| `export.py` | Writing results: poster PNG, georeferenced TIFF (+ world file, projection; furniture hidden unless asked), POI csv/geojson/xlsx/summary. | config |
| `api.py` | Public entry points: `generate_map(..., layout=)`, `run_batch`, `find_receptors`, `export_receptors`, `list_districts`. File naming, skip-existing, failure isolation, early validation of `layout`. | all |
| `runtime.py` | **Run-time plumbing for GUIs.** `log()` (progress line + listeners + cancel point), `say()` (no cancel), `Cancelled`, `JobRunner` (background thread, events, cancel). No toolkit imports. | nothing |
| `gui_core.py` | **GUI logic without a toolkit** (now also layers, labels, styles, marker preview shapes, transparency preview colours). `FormState` -> `validate` -> `build_jobs`; `estimate` (pixels, RAM, warnings); `describe_options` (choices for building forms); presets; batch-file export; async district loading. | api, config, furniture |
| `gui_tk.py` | **Tkinter window / embeddable `AtlasPanel`.** Seven tabs with icons (Where, Map, Your data, Receptors, Elements, Styles & labels, Output), `LayerDialog` with live style preview, `LabelDialog`, estimate, progress, log, results list, Cancel. Only lays out widgets; calls `gui_core` and `JobRunner`. `on_files` hands finished files to the viewer. | gui_core, runtime |
| `cli.py` | Turns flags (incl. map-element flags and `ATLASA0_*` variables) into a list of jobs and calls `run_batch`. | api, furniture, config |

Rule: lower layers never import upper ones; only `osm.py` touches the network.

Outside the package:
| Folder | Purpose |
|--------|---------|
| `tests/` | Offline pytest suite (config, geometry/calibration, export, furniture, CLI/API) and opt-in live tests. |
| `run_gui.py` | Double-click launcher for the window. |
| `tools/calibrate.py` | Prints A0 pixel sizes, scale bars, marker sizes, tile zoom, map fill and TIFF pixel check. |
| `skills/` | Three Claude skills: `atlasa0-maps`, `atlasa0-receptors`, `atlasa0-qa` (tools, variables, procedure). |
| `examples/` | Sample batch file (jobs may carry a `layout` dict). |

## 4. How one map is made
1. **Job** - `{level, region, province, map_type, formats, pois, layout, dpi...}` from CLI flags, a batch file or the API. `layout` is validated before any download.
2. **Boundary** - Nominatim gives the city/province/country polygon; districts come from OSM admin level 6.
3. **Extent** - boundary fitted to the **drawing area** (not the sheet) aspect in the region's **UTM zone** (metres; country uses UTM 42N), so the map fills the frame.
4. **Download** - only the layers the map type needs (roads, water, land use, buildings, rail, POIs). District maps download inside the district only.
5. **Draw data** - layers in a fixed order; district maps blank everything outside the boundary; receptor markers sized from the map span (11 mm -> 5 mm on the sheet).
6. **Draw elements** - `furniture.apply_layout` adds the enabled elements (title, legend, scale, north, grid, note, logo, credit); each artist is registered.
7. **Export** - PNG (full poster) and/or TIFF (map area only, square pixels, world file + `.prj`, registered elements hidden unless `tiff_furniture`); optional receptor files.
8. **Result** - list of files; a failed job is recorded and the batch continues.

### Your data (layers) flow
```
 file.shp/.geojson/.gpkg/.kml/.csv --load_layer(geopandas, to UTM)--> Prepared features --draw_layers--> map (zorder above base, below elements)
                                                                                       └--> legend handles --> furniture legend
```
Extent can include layers (`fit`). Markers/lines are sized in mm on the sheet. Layers stay in the GeoTIFF (they are data); legend/scale/north/grid do not.

### Map elements data flow
```
 CLI flags / API layout={} / batch JSON "layout"
              │  Layout.from_any()  (validate: elements, legend items, position, logo file, grid km)
              v
        Layout ──> apply_layout(fig, ax, ext, theme, size, utm, layout, defaults from the map)
                      ├─ grid    (ticks + lines, UTM km labels, adds grid note to credit)
                      ├─ scale   (nice 1/2/5 km bar, 0 / half / full, "1:N at A0")
                      ├─ north   ├─ legend (land use + custom items; receptors legend top-right)
                      ├─ note    ├─ logo   ├─ title (override or map default)   └─ credit
                      v
              fig._atlasa0_furniture  ── hidden by export when saving the TIFF (default)
```
Fixed placement: north top-left, scale bottom-left, receptor legend top-right, main legend lower/centre right (`legend_pos`), note bottom-centre.

## 5. Map types (strategy by name)
`street`, `transport`, `landuse`, `water`, `buildings`, `receptors`, `satellite`, `topo`.
Each is a branch in `make_map` that chooses which data to fetch and how to draw it. Province and country maps have one fixed layout.

## 6. Key design decisions
| Decision | Why |
|----------|-----|
| Projected CRS (UTM) for drawing | Equal x/y scale, true metres, scale bar and GIS rasters are correct. |
| TIFF = axes area only, georeferenced by world file (+ embedded CRS if `rasterio` exists) | Clean overlay in ArcMap/QGIS; no title text inside the raster. |
| Province/country queries use a simplified polygon, one request | The full national boundary is too large to send and splitting it needs hundreds of calls. |
| Features are fetched per layer, not all at once | Faster, smaller downloads, easy to add a layer. |
| POIs are an overlay and also a map type | Same receptors on any base map, or a dedicated clean receptor sheet. |
| Batch is the only execution path | CLI, API and viewer all produce jobs, so behaviour is identical. |
| Failure isolation + `skip-existing` + cache | Long bulk runs (hundreds of A0 files) can be resumed. |
| Heavy libraries imported where used | `config` stays importable without GIS libraries. |
| Extent fitted to the drawing area (`AXES_RECT`) | Measured: paper-aspect fit left ~25 mm blank each side; axes-aspect fit fills 100%. |
| One `Layout` object for all map elements | CLI, API and batch JSON share one validated description; renderers stay small. |
| Elements registered and hidden for the TIFF | GIS rasters stay clean for overlay; PNG keeps the full poster. |
| Scale bar and markers computed from the span | Bars use 1/2/5 steps; markers shrink on large areas so they stay readable. |
| Settings via flags, then `ATLASA0_*` variables | Same defaults for CLI, viewer and skills without editing code. |

## 7. Extension points
- **New map type**: add to `MAP_TYPES`, add a data + draw branch in `make_map`.
- **New POI category**: add an entry (OSM tags, colour, marker) to `POI_CATEGORIES`; optionally to a preset.
- **New region level** (e.g. tehsil): add a lookup in `osm.py`, a `level` in `api.generate_map`.
- **New form field**: add to `FormState`, validate in `gui_core.validate`, map in `build_jobs`, add a widget in `gui_tk` (`get_state` / `set_state`), a test.
- **New marker / line / hatch style**: add to `MARKERS` / `LINE_STYLES` / `HATCHES` in `layers.py` (GUI and CLI pick it up) and a preview shape in `gui_core.marker_shape`.
- **New north/scale/legend style**: add to the style dict and drawer in `furniture.py`, with a test.
- **New map element**: add to `ELEMENTS`, a drawer + call in `furniture.apply_layout`, `_register` its artists, a CLI flag, a test.
- **New output** (GeoPackage, Shapefile): add a writer in `export.py`, a format in `FORMAT_ALIASES`.
- **Your own data** (verified receptor list, risk portal results): merge a GeoDataFrame before drawing.

## 8. Viewer (GUI) architecture
The project viewer is a Python GUI, so AtlasA0 runs **in the same process** as a panel, with the work on a background thread.
```
 Viewer window (main thread)                         worker thread
 ┌───────────────────────────────┐   start(jobs)    ┌──────────────────────────────┐
 │ AtlasPanel (gui_tk)           │ ───────────────> │ JobRunner -> api.run_batch   │
 │  form widgets <-> FormState   │                  │   generate_map -> render ... │
 │  gui_core: validate/build/est.│ <── queue ────── │   runtime.log() events       │
 │  progress bar, log, file list │   (polled with   │   (every stage = cancel pt)  │
 │  Cancel -> runtime.request_cancel               │                              │
 └──────────────┬────────────────┘   after())       └──────────────────────────────┘
                │ on_files(paths)
                v
        viewer.load_layers(...)   GeoTIFF + .tfw/.prj as raster layer, GeoJSON as vector layer
```
- **Events** (dicts): `log`, `job_start`, `job_done` (with files), `job_failed`, `cancelled`, `finished`. They arrive on the worker thread; the panel puts them in a `queue` and handles them on the Tk main thread (Qt: use a signal).
- **Cancel**: takes effect at the next stage message (downloads, drawing, saving steps), not instantly; finished files of earlier jobs are kept. `Cancelled` is a `BaseException` so the OSM wrappers' `except Exception` cannot swallow it.
- **One batch at a time**; the form shows RAM, download and file-size estimates (`estimates.py`, learning from real runs) and a 50-500 dpi slider.
- **Reuse**: "skip existing" resumes a run; settings are saved to `~/.atlasa0_preset.json`; "Export as batch file" turns the form into a `--batch` JSON.
- **Other toolkits / web**: build your own widgets on `gui_core` + `JobRunner` (see `examples/embed_in_viewer.py`); for a web backend run `run_batch` in a worker process and poll a manifest.

### Configuration (local variables)
| Variable | Used by | Default |
|----------|---------|---------|
| `ATLASA0_OUTDIR` | CLI `--outdir` | `output` |
| `ATLASA0_DPI` | CLI `--dpi` | 300 |
| `ATLASA0_THEME` | CLI `--theme` | `light` |
| `ATLASA0_CACHE` | `osm.py` OSM cache folder | `cache` |
| `ATLASA0_LIVE` | live tests | unset |
Flags always override variables.

## 9. Constraints and risks
| Risk | Mitigation |
|------|------------|
| Overpass timeouts on large areas | One request for overviews, 900 s timeout, cache, rerun; later: retry/backoff. |
| OSM completeness (small facilities, district names) | Treat counts as indicative; add own verified list; check against official sources. |
| Disputed / official boundaries | Credit line on country/province maps; verify with Survey of Pakistan. |
| Memory at A0 300 dpi | 200 dpi option; one job at a time. |
| Tile imagery terms (satellite/topo) | Credits printed on the map; check provider terms before publishing. |
| Shapefile/CSV reading never run in the build environment (no geopandas) | `tests/test_live.py` has GeoJSON, CSV and shapefile round-trips; first real run on your PC. |
| Layer files without a CRS | Assumed EPSG:4326 (`crs=` to override); a wrong CRS puts features in the wrong place - check the first map. |
| Elements may collide with dense map content on real cities | Fixed corners, semi-opaque boxes; check one real city, adjust `legend_pos`, or switch elements off. |
| Layout changes do not change file names | Delete old files or use a new `--outdir` when only layout changes with `--skip-existing`. |
| Cancel is not instant | Stage-level cancel points; a single long Overpass request finishes before the stop is seen. |
| GUI never displayed in the build environment | Wiring tested with a stub; check layout/sizes on first launch. |
| Not yet run against live data in the build environment | First real run is the top item in `milestone.md`. |

## 10. Testing approach
- **GUI**: controller, events, cancel and runner are tested directly; the Tk panel is exercised through a stub toolkit (`tests/tk_stub.py`: state round-trip, event handling, run/validate). The real window has not been displayed in the build environment.
- **Layers and styles**: drawing tested through duck-typed geometries (colour, alpha, marker, size, line style, hatch, holes by pixel check, legend order, labels); styles/positions/labels tested on a synthetic A0 figure. Reading real files (`load_layer`) is covered only by the live tests.
- **Offline suite** (`pytest`, about 270 tests, no network): config and presets, layout maths (extent fit, scale bar, markers, tile zoom, A0 pixels), GeoTIFF + world file (square pixels, ground width), receptor files (csv/geojson/xlsx/summary), map elements (all drawn, none drawn, overrides, clean TIFF), CLI (lists, dry run, bad input, env variables, layout flags), batch failure isolation, file-naming contract. Stand-ins replace osmnx/geopandas/shapely when absent.
- **Calibration**: `python tools/calibrate.py`.
- **Live suite** (`ATLASA0_LIVE=1 pytest tests/test_live.py`): real city per map type, receptor counts and coordinates, district clipping, TIFF pixel size. Not yet run.
- **Still needed**: one live run per level, TIFF opened in ArcMap and QGIS, receptor counts compared with known facilities, a look at elements on a dense real map.
