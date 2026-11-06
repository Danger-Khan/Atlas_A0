---
name: atlasa0-maps
description: Make A0 print-ready or georeferenced maps of Pakistan (country, province, district, city) with AtlasA0, including legends, scale bar, north arrow, grid, title, note and logo. Use when the user says AtlasA0 or asks for a map of a Pakistani place.
---
Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# AtlasA0 maps

## Tools (pick the lowest that works)
- CLI: `python -m atlasa0 <cities> [--country] [--province kpk ...] [--district X --in kpk] [--type ...] [--format png tiff] [--dry-run]`
- Python API: `from atlasa0 import generate_map, run_batch` (`generate_map(region, level, province, map_type, formats, layout={...})`)
- Inspect: `--list`, `--list-types`, `--list-districts kpk`, `--list-elements`, `--list-poi`

## Local variables (set before running; all optional)
| Variable | Meaning | Default |
|---|---|---|
| `ATLASA0_OUTDIR` | where files are written | `output` |
| `ATLASA0_DPI` | resolution (200 on low-RAM PCs, 300 for print) | 300 |
| `ATLASA0_THEME` | `light` / `dark` / ... | `light` |
| `ATLASA0_CACHE` | OSM download cache folder | `cache` |
| `ATLASA0_LIVE` | `1` enables live tests | unset |
Command-line flags override variables.

## Procedure
1. Resolve what is asked into jobs (level, region, province for districts, map types, formats). Put city names BEFORE `--province`/`--district`.
2. Always `--dry-run` first for more than one job; show the planned count.
3. Map elements: `--elements title legend scale north grid credit` (default all but grid; `none`/`all`), `--legend-item "Label=#hex"`, `--legend-pos`, `--title`, `--subtitle`, `--note`, `--logo FILE`, `--grid-km N`. In Python the same go in `layout={...}`.
4. GIS use: `--format tiff`. The TIFF is clean (no legend/scale/north/grid) unless `--tiff-furniture`; keep `.tfw` and `.prj` beside it.
5. DPI 50-500. `--dry-run` prints pixels, RAM, download and file-size estimates; fall back to a lower dpi if memory runs out. Use `--skip-existing` to resume; changing layout options needs the old files deleted (names do not include layout).
6. Report file names, sizes and any FAILED jobs from the manifest (`--manifest`).

## Honesty
OSM data is indicative; boundaries must be verified against Survey of Pakistan for official use. Say what was not run live.

## Your data and styles
- Layers: `--layer "file.shp;name=Sites;color=#d62728;alpha=0.6;marker=triangle;size_mm=8;label_field=NAME;fit=1"` (repeat). Types: shp, geojson, gpkg, kml, gml, csv (lon/lat). Python: `layers=[{...}]`.
- Styles: `--legend-style box|compact|minimal|horizontal`, `--north-style arrow|classic|compass|circle`, `--scale-style bar|line|double|ratio`, `--scale-units km|mi|m`, positions `--legend-pos/--north-pos/--scale-pos` (no two at the same place), `--text-label "Text@lon,lat;size=50"`. `--list-styles` shows everything.
- Own file name: `--name "Map_{region}_{date}"` (default is automatic).
- Check a layer's CRS if features land in the wrong place (default EPSG:4326, set `crs=` otherwise).
- Header on every file: Author Imaad Ullah Khan Yameen, yameenimaad@gmail.com, not for sale.
