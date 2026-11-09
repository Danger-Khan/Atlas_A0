Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# AtlasA0 - Requirements

**Status key:** ✅ implemented and checked in a sandbox · 🔶 implemented, needs a real run (live OpenStreetMap download) · ⬜ not built

## 1. Purpose
Let the owner download maps of any area of Pakistan that interests them - the whole country, a
province, a district or a city - and use them in two ways:

1. **GIS applications** (ArcMap, QGIS and the project viewer): georeferenced rasters.
2. **Physical prints**: A0 (841 x 1189 mm) posters at print resolution.

## 2. Users and use cases
| ID | Use case |
|----|----------|
| UC-1 | Download one map of one place (e.g. Peshawar, street map) as an A0 PNG. |
| UC-2 | Download the same place in several styles (street, land use, water, satellite...). |
| UC-3 | Download a georeferenced TIFF to load into ArcMap/QGIS at the correct location and scale. |
| UC-4 | Download country, province, district and city maps **in one go** from a single command or job file. |
| UC-5 | Call the generator from the project viewer and offer the files for download. |
| UC-6 | Resume a long bulk run after an interruption without redoing finished maps. |

## 3. Functional requirements
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-1 | Region levels: **country** (Pakistan), **province/territory** (7), **district**, **city**. | Must | 🔶 |
| FR-2 | Choose any region by name; accept short province names (kpk, gb, ajk, ict). | Must | ✅ |
| FR-3 | List available provinces, preset cities, district names and map types. | Should | ✅ (districts 🔶) |
| FR-4 | District maps clipped to the district boundary. | Must | 🔶 |
| FR-5 | Map types for city/district: street, transport, landuse, water, buildings, satellite, topo. | Must | 🔶 |
| FR-6 | Country and province overview maps with fixed layout (boundaries, labels, highways, rivers). | Must | 🔶 |
| FR-7 | Output **PNG** sized for A0 (portrait or landscape) with title, coordinates, scale bar, attribution. | Must | 🔶 |
| FR-8 | Output **georeferenced TIFF** (map area only; `.tfw` + `.prj`; embedded CRS if rasterio is present). | Must | ✅ (writing and world file) · 🔶 (opening in ArcMap) |
| FR-9 | Choose several map types and formats in one command (one file per combination). | Must | ✅ |
| FR-10 | **Batch**: any mix of country/province/district/city in one run, from flags or a JSON job file. | Must | ✅ (logic) · 🔶 (full run) |
| FR-11 | One failed job never stops the batch; failures are listed at the end and in the manifest. | Must | ✅ |
| FR-12 | `--skip-existing` to resume; `--dry-run` to preview the job count. | Should | ✅ |
| FR-13 | JSON manifest of produced files for the viewer. | Should | ✅ |
| FR-14 | Python API: `generate_map`, `run_batch`, `list_districts`. | Must | ✅ |
| FR-15 | Options: dpi, landscape, light/dark theme, building footprints, fixed radius, tile zoom. | Should | ✅ |
| FR-16 | Predictable file names, e.g. `district_khyber_pakhtunkhwa_swat_landuse_A0_300dpi.png`. | Must | ✅ |
| FR-20 | **Receptors / points of interest**: hospitals, clinics, pharmacies, schools, colleges, places of worship, water sources, markets, police, fire, fuel, industry. | Must | 🔶 |
| FR-21 | Overlay chosen categories (or a preset such as `receptors`) on city/district maps with a counted legend; optional name labels. | Must | 🔶 |
| FR-22 | Dedicated `receptors` map type (light base + receptor symbols). | Should | 🔶 |
| FR-23 | Export receptors as GeoJSON (WGS84) and CSV (lon/lat + UTM) for ArcMap/QGIS; data-only mode without drawing a map. | Must | ✅ (file writing) · 🔶 (live data) |
| FR-25 | Receptor export formats: CSV, GeoJSON, Excel workbook (Receptors + Summary sheets) and a category-count summary CSV; user chooses one or several. | Should | ✅ (file writing) |
| FR-24 | API: `find_receptors()` (counts + table) and `export_receptors()`. | Should | 🔶 |
| FR-17 | Vector exports (GeoPackage/Shapefile of boundaries and roads) for GIS analysis. | Could | ⬜ |
| FR-18 | Tehsil/UC level and Urdu/Pashto titles. | Could | ⬜ |
| FR-19 | Viewer UI (download buttons, job queue, progress). | Should | ⬜ (needs framework choice) |

## 4. Non-functional requirements
| ID | Requirement |
|----|-------------|
| NFR-1 | **Print quality:** A0 at 300 dpi is about 9,930 x 14,040 px (~140 MP). 200 dpi must be available for machines with less memory. |
| NFR-2 | **Memory:** A0 at 300 dpi needs about 2-3 GB RAM, 500 dpi with GeoTIFF about 6 GB (estimate from a measured synthetic render plus data allowance; the GUI and --dry-run show it). DPI range 50-500. TIFFs are LZW-compressed RGB (well under 4 GB). |
| NFR-3 | **Time:** A0 maps take minutes each; large provinces and the country take longest. Results are cached so a rerun is fast. |
| NFR-4 | **Reliability:** network/Overpass errors on one job are reported, not fatal; cache allows retry. |
| NFR-5 | **Georeferencing:** TIFFs use the UTM zone of the region in metres (country map: UTM 42N). Pixels are square. |
| NFR-6 | **Portability:** Python 3.9+, Windows/macOS/Linux; no GUI needed. |
| NFR-7 | **Licensing:** every map carries "Map data (c) OpenStreetMap contributors". Satellite adds Esri credit, topo adds OpenTopoMap credit. Check provider terms before publishing or selling prints. |
| NFR-8 | **Data accuracy:** boundaries and names are as mapped in OpenStreetMap. For official use (disputed areas, legal boundaries) verify against Survey of Pakistan. |

## 5. Dependencies
Required: `osmnx`, `geopandas`, `matplotlib`, `shapely`, `pillow`, `numpy`.
Optional: `contextily` (satellite/topo), `rasterio` (embed georeferencing in the TIFF).
Needs internet for downloads (first run); cache is reused afterwards.

## 6. Known limits and assumptions
- Receptor points come from OpenStreetMap volunteers: major hospitals and schools are usually present, small facilities (BHUs, village schools, wells) may be missing. Treat counts as indicative, not an official inventory.
- District boundaries are OSM admin level 6; a few districts may be missing or named differently.
- Country/province queries are simplified and sent as one request; the public Overpass server may time out - retry later.
- TIFF contains only the map area (no title/legend). The scale bar and frame are drawn on the image.
- Satellite/topo are raster tiles: resolution is limited by the provider's maximum zoom.
- `--province a b c` accepts many names, so put city names **before** it, e.g. `Peshawar --province kpk`.

## 7. Acceptance criteria
1. `python -m atlasa0 Peshawar` produces an A0-sized PNG that prints sharply at A0.
2. `--format tiff` output loads in ArcMap and QGIS at the correct location with no manual georeferencing; measured distances match the real world.
3. One command can produce the country, a province, a district and a city together, and the run finishes even if one job fails.
4. A second run with `--skip-existing` makes no new downloads for finished maps.
5. `generate_map(...)` can be called from the viewer and returns the file paths.


## GUI requirements (added)
- FR-26 A window (Tkinter) to choose country / provinces / cities / districts, map types, formats, quality, receptors, map elements and output folder, usable without the command line.
- FR-27 Embeddable panel for the Python project viewer, with a callback that receives the finished files.
- FR-28 Long runs never freeze the window; progress bar, log, and a Cancel that stops at the next stage and keeps finished files.
- FR-29 Validation messages in plain language before anything runs; estimate of pixel size, RAM and number of files.
- FR-30 Quality presets (Preview 100 / Draft 200 / Print 300 dpi); settings saved and restored; export of the form as a batch file.
- FR-31 Same behaviour from CLI, API and GUI (one job path; GUI logic in a toolkit-free module reusable for Qt/web).
Acceptance: a first-time user makes a city PNG from the window without typing a command; Cancel returns the window to ready state within one stage; files appear in the list and reach `on_files`. (Status: logic tested; real window needs a first run.)


## Layers, styles, icons, notice (added)
- FR-32 Add points, lines and polygons from shapefile, GeoJSON, GeoPackage, KML, GML and CSV (lon/lat) to the final output, any number of layers, drawn in the order given.
- FR-33 Per layer: fill/outline colour, transparency, marker shape and size, line style and width, fill pattern, label attribute, legend text and visibility.
- FR-34 Several legend styles and positions; several north-arrow styles; several scale-bar styles and units (km, miles, metres); free text labels at coordinates.
- FR-35 Same options from CLI, API, batch JSON and GUI; invalid values rejected with a readable message before any download.
- FR-36 GUI icons on tabs and buttons; a layers editor with a live preview of the chosen style.
- FR-37 Author / contact / "not for sale" notice in every file and visible in the GUI and `--about`.
Acceptance: a user adds a shapefile of sites, sets red 60 % opaque triangles with names, a dashed blue canal and a 35 % hatched zone, picks a compass north arrow and a double scale, and gets a map where the layers line up with the base map. (Status: drawing tested; real file reading needs a first run.)

- FR-38 Output file names are automatic by default; the user may give a template with fields {region} {level} {type} {province} {dpi} {date}; names that would overwrite each other are rejected before any download.
- FR-39 A Settings tab holds naming, folder, skip-existing, automatic remembering of choices, open-folder-when-done and reset to defaults.

- FR-40 Paper: A0 (default), A1-A4 or a custom size in mm; dpi is the print resolution on that paper; estimates, names, scale text and stored dpi follow the paper.
- FR-41 Preview: a 50 dpi PNG-only quick render, named `_preview`, never skipped, shown automatically in the GUI.
- FR-42 Receptor names and layer labels are placed without overlapping each other or covering markers; labels that cannot fit are counted in the log.
- FR-43 GeoTIFF raster layers (overlay or basemap) with colour map, value limits, opacity, nodata transparency and legend entry; clear error if rasterio is missing.
- FR-44 Choropleth: districts (province map) or provinces (country map) shaded from a CSV/Excel table with quantile/equal/natural/manual classes, palette choice, legend, optional numbers; unmatched names are reported.
- FR-45 Windows app: one-folder exe and an installer showing the licence; installed app writes only to the user's own folders. (Status: files written, not built.)
- FR-46 Release pack: terms, privacy policy, notice, security review, contributing and conduct files, packaging (`pyproject.toml`, console scripts), CI on Windows/macOS/Linux, launchers for each system; every file carries the author line (tested).
- NFR: plain-field-only file-name templates; decompression-bomb limit stays on except while writing our own GeoTIFF.
