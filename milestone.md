Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# AtlasA0 - Milestones

**Status key:** ✅ done and checked in a sandbox · 🔶 coded, needs a real run on your machine · ⬜ planned

Last updated: 2026-11-05. No dates are committed yet - set them once M5 is complete.

## M1 - City map prototype ✅
- [x] A0 PNG for any Pakistani city from OpenStreetMap (roads, water, parks)
- [x] Title block, coordinates, scale bar, attribution
- [x] Light and dark themes, portrait/landscape, dpi option

## M2 - Regions: province and district 🔶
- [x] Province overview map (districts, highways, rivers)
- [x] Province catalogue with short names (kpk, gb, ajk, ict) and preset cities
- [x] District maps clipped to the district boundary; `--list-districts`
- [ ] Confirm district names/boundaries for every province against real OSM data

## M3 - Map types 🔶
- [x] street, transport, landuse, water, buildings
- [x] satellite and topo (optional `contextily`)
- [ ] Review colours and legend on a real printed sheet

## M4 - GIS export ✅ / 🔶
- [x] Georeferenced TIFF: map area only, `.tfw` + `.prj`, optional embedded CRS
- [x] RGB, LZW compression, square pixels (tested with a small figure)
- [ ] Open the TIFF in ArcMap and QGIS: check position, scale and measured distances

## M5 - Country and one-go downloads 🔶
- [x] Country map (provinces, motorways/trunk, rivers)
- [x] Batch runner for mixed levels, JSON job file, `--skip-existing`, `--dry-run`, manifest
- [x] Failure isolation (one failed job does not stop the batch)
- [ ] **First real run** of country + one province + one district + one city together
- [ ] Record actual run times and RAM use at 200 and 300 dpi

## M5b - Receptors / points of interest 🔶
- [x] 12 categories + presets (`receptors`, `health`, `education`, `emergency`, `all`)
- [x] Overlay on city/district maps with counted legend; `--poi-labels`
- [x] `receptors` map type; `--poi-data` / `--poi-only` (GeoJSON + CSV); `find_receptors()` API
- [ ] Run on a real district and compare counts with known facilities (Peshawar hospitals, Swat schools)
- [ ] Tune marker size / label clutter for very dense cities

## M6 - Project structure and documentation ✅
- [x] Package layout (`config`, `osm`, `render`, `export`, `api`, `cli`)
- [x] `README.md`, `requirements.md`, `milestone.md`, `requirements.txt`, example job file

## M7 - Project viewer integration ⬜
- [ ] Decide the viewer framework (Flask / Django / Streamlit / other)
- [ ] Background job queue (A0 maps take minutes) + progress
- [ ] Download buttons for PNG / TIFF; cache finished maps
- [ ] Low-dpi preview (about 100 dpi) for on-screen display

## M8 - Hardening ⬜
- [ ] Automated tests with a saved OSM sample (offline)
- [ ] Retry/backoff for Overpass timeouts
- [ ] Clear error messages for name mismatches ("did you mean...")

## M9 - Nice to have ⬜
- [ ] Vector exports (GeoPackage / Shapefile of boundaries and roads) for GIS analysis
- [ ] Tehsil / union council level
- [ ] Urdu / Pashto titles
- [ ] North arrow and legend box on printed sheets
- [ ] Overlay your own layers (e.g. KP Marble Slurry Risk Portal results)
- [ ] Distance rings: receptors within X km of a site (nearest hospital/school, counts per ring)

## Next actions
1. Install requirements and run: `python -m atlasa0 --country --province kpk --district Swat --in kpk Peshawar --format png tiff --dpi 200`
2. Open the TIFFs in ArcMap/QGIS and tell me what looks wrong.
3. Pick the viewer framework so M7 can start.

## M10 - Tests and calibration
- ✅ Offline pytest suite (94 tests), `tools/calibrate.py`, layout fix (map fills the frame), scale-bar and receptor-marker calibration - sandbox-checked
- 🔶 `tests/test_live.py` written, needs a real run with internet

## M11 - Map elements and skills
- ✅ `furniture.py`: legend (+custom items), segmented scale bar with print scale, north arrow, UTM grid, title/subtitle override, note, logo, clean GeoTIFF option; CLI flags; `layout` in API/batch; env defaults - sandbox-checked with synthetic A0 figure
- 🔶 Appearance on real OSM maps (overlaps with dense roads, long legends) needs a live look
- ✅ Three Claude skills in `skills/`

## M12 - GUI for the project viewer
- ✅ `runtime.py` (progress events, cancel, background runner), `gui_core.py` (form -> validated jobs, estimates, presets, batch export), tests incl. cancel behaviour
- ✅ `gui_tk.py` panel + `run_gui.py` / `--gui`; wiring tested through a stub toolkit (state round-trip, events, run/validate)
- 🔶 Real window: never displayed (no Tk/display in the build environment) - layout, sizes and look need a first look on your PC
- ⬜ Qt/PySide version if your viewer is Qt (controller is ready; widgets not written)
- ⬜ Map preview inside the window (needs a tile/preview render at low dpi)

## M13 - Your data, styles, icons
- ✅ `layers.py`: shapefile / GeoJSON / GPKG / KML / CSV layers with colour, transparency, marker, line, hatch, labels, legend entry; drawn in all four map levels; ring-direction fix verified by pixel test
- ✅ Legend (4 styles, 8 positions), north arrow (4 styles), scale (4 styles, km/mi/m), free text labels, position-conflict check
- ✅ GUI: icons, "Your data" tab with style preview, "Styles & labels" tab; author notice in every file
- 🔶 Reading real shapefiles/CSV (`load_layer`) needs geopandas - tests written (`tests/test_live.py`), not run here
- 🔶 Look of layers/labels/legends on a dense real map not yet seen; real GUI window not yet displayed
- ⬜ Layer-level filters (e.g. only features where TYPE = 'school'); symbol from an image/icon file

## M14 - File names and Settings tab
- ✅ `file_stem` template names (CLI `--name`, API `filename`, batch, GUI), overwrite protection, live example in the GUI, Settings tab with gear icon, auto-save and open-folder switches, reset to defaults
- 🔶 Tab not yet seen in a real Tk window; opening the folder uses the OS opener (untested here)

## M15 - 500 dpi, slider, size estimates
- ✅ DPI 50-500 (CLI, API, GUI), slider + quick buttons, download / file size / RAM estimates that learn from real runs, `--dry-run` estimate line
- ✅ Measured: synthetic A0 line map at 100/300/500 dpi -> PNG 6/28/55 MB, peak 0.2/0.7/1.6 GB RAM
- ✅ Removed the tiny stray axis titles seen on the first real Peshawar maps
- 🔶 500 dpi on a real OSM map (with GeoTIFF) not yet run; first estimates are guesses until your runs calibrate them

## M16 - Province/country overview fix (first real KP map)
- ✅ Admin areas filtered to one level (osmnx ORs tags) - districts list, province map, country map
- ✅ Label collision avoidance (test: 36 crowded KP names -> 35 placed, none overlapping); "District" suffix removed
- ✅ `--orientation auto` (default) / GUI Sheet choice; OSM failures logged; river counts logged
- 🔶 Needs a real KP rerun to confirm district count and rivers

## M17 - Draw order
- ✅ 11 draw groups with a configurable order (GUI list top-first, CLI `--draw-order`, layout/batch `draw_order`); map elements always on top; order logged on every run
- ✅ "Your data" list shown top-first and numbered; Move up now really brings a layer forward
- 🔶 Look on a real map with a changed order not yet seen
