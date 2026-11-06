---
name: atlasa0-receptors
description: Find and export receptors / points of interest (hospitals, schools, worship, water sources, fuel, etc.) for a Pakistani region with AtlasA0, as map overlays and CSV/GeoJSON/Excel/summary files.
---
Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# AtlasA0 receptors

## Tools
- Data only: `python -m atlasa0 Peshawar --poi-only --poi hospitals schools --poi-format csv xlsx summary`
- On a map: `--type receptors` or `--poi receptors --poi-labels --poi-data`
- API: `find_receptors(region, level, province, pois)` -> counts + table + gdf; `export_receptors(...)`
- Names: `--list-poi` (12 categories; presets receptors, health, education, emergency, all)

## Local variables
`ATLASA0_OUTDIR` (output folder), `ATLASA0_CACHE` (OSM cache). Receptor files are named `<map>_poi.csv|.geojson|.xlsx` and `_poi_summary.csv`.

## Procedure
1. Choose categories/preset; choose formats (csv for Excel with Urdu names, geojson for GIS, xlsx for reports, summary for counts).
2. Run the data-only command first when the user wants numbers, not a poster.
3. Quote counts with the caveat: OSM completeness varies, positions are as mapped (building centroid for polygons), so receptors are indicative, not a survey.
4. Never invent a missing facility; zero counts are reported as zero.
