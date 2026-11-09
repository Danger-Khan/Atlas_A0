<!--
Author: Imaad Ullah Khan Yameen
Email: yameenimaad@gmail.com
This code is not for sale.
-->
# Security Policy

AtlasA0 is a desktop/command-line tool. It runs on your own computer, has no server, opens no network ports, has no user accounts and sends no telemetry. This policy explains which versions get security fixes, how to report a problem privately, and what happens after you report it.

## Supported Versions

| Version | Supported | Notes |
| ------- | --------- | ----- |
| 1.1.x   | :white_check_mark: | Current release (`python -m atlasa0 --about` shows your version) |
| 1.0.x and older (including unversioned snapshots shared before November 2026) | :x: | Please update to 1.1.x |

Only the latest 1.1.x release gets fixes. When a 1.2 or 2.0 line comes out, this table will say how long 1.1.x stays supported.

## Security review
What was checked, fixed and is still open is listed in [REVIEW.md](REVIEW.md).

## Reporting a Vulnerability

**Please do not report security problems in a public issue, chat group or post.**

Email **yameenimaad@gmail.com** with the subject line `AtlasA0 security: <short title>` and include:

- the AtlasA0 version (`python -m atlasa0 --about`), Python version and operating system;
- what the problem is and what an attacker could do with it;
- steps or a small file that shows it (a batch JSON, layer file, image...) - **sample data only, never real personal data or passwords**;
- whether you want to be credited, and under which name.

### What happens next

| Step | When |
| ---- | ---- |
| Reply confirming the report arrived | within **7 days** |
| First assessment: accepted, needs more information, or declined (with the reason) | within **14 days** |
| Progress updates while it is open | at least every **14 days** |
| Fix released for accepted reports | normally within **30 days**; up to **90 days** for hard cases (you will be told why) |

- **Accepted:** a fixed version is released, the change is noted in `milestone.md`, and you are credited if you want to be. Please keep the details private until the fix is out (or 90 days have passed, whichever comes first) so users can update.
- **Declined:** you get an explanation, e.g. it is outside the scope below, it needs the attacker to already control your computer, or it belongs to another project (then you will be told where to report it).

This is a one-person project maintained alongside other work, so the times above are targets, not guarantees.

## Scope

### In scope (report these)

- **Files AtlasA0 reads that someone else could give you:** batch JSON files (`--batch`), saved GUI settings (`~/.atlasa0_preset.json`), layer files (shapefile, GeoJSON, GeoPackage, KML, GML, CSV), logo images, and the size-statistics file (`~/.atlasa0_stats.json`). A crafted file must never run code, delete or overwrite files outside the chosen output folder, or crash the program in a way that harms your system.
- **Where files are written:** custom file-name templates (`--name`, GUI *Settings*) are cleaned of path separators and forbidden characters; any way to escape the output folder is a bug.
- **Network use:** AtlasA0 only contacts OpenStreetMap services through osmnx (Nominatim geocoding and the Overpass API) and, for `satellite` / `topo` maps, tile servers through contextily (Esri World Imagery, OpenTopoMap), all over HTTPS. Report anything that sends your data elsewhere, uses plain HTTP, or turns off certificate checks.
- **Local data:** downloads are cached in the `cache` folder inside the AtlasA0 folder (or `$ATLASA0_CACHE`; if that folder is read-only, your user cache folder). Report any case where AtlasA0 stores or sends something that is not map data or your own settings.

### Out of scope (not security bugs)

- Wrong, missing or outdated map data. That is OpenStreetMap content; fix it at openstreetmap.org, or report it as a normal bug if AtlasA0 draws correct data wrongly.
- Vulnerabilities inside dependencies (GDAL/pyogrio, Pillow, matplotlib, osmnx, geopandas, pandas, openpyxl, Tk). Report those to the project concerned and keep your packages updated (`pip install -U -r requirements.txt`). Do tell us if AtlasA0 uses a library in an unsafe way, or needs a minimum version to avoid a known problem.
- Running out of memory or disk on very large jobs (e.g. 500 dpi with GeoTIFF). The GUI and `--dry-run` show estimates; this is a resource limit, not a vulnerability.
- Problems that need someone to already control your computer or your Python environment.

## Safe use

- Only run batch files and open layer or logo files from people you trust, just as you would with any document.
- Keep Python and the packages in `requirements.txt` up to date. They parse the shapefiles, images and Excel files, so their fixes matter.
- Choose an output folder for AtlasA0 instead of your home folder or system folders.
- The cache and the `*_poi.csv` / `.geojson` / `.xlsx` exports contain OpenStreetMap data only. Your own layer files are read, never copied or uploaded.

## License note

AtlasA0 is by Imaad Ullah Khan Yameen and is licensed under the PolyForm Noncommercial License 1.0.0 (see `LICENSE`). This code is not for sale. Reporting a vulnerability does not transfer any rights in the code.
