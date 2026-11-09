# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Command line:  python -m atlasa0 Peshawar --type landuse --format png tiff

Everything is turned into a list of jobs and run in one go, so you can mix levels:
    python -m atlasa0 --country --province kpk sindh --district Swat --in kpk Peshawar --format png tiff
"""
import argparse
import json
import os
import sys

from . import estimates as est
from .api import export_receptors, run_batch
from .config import (file_stem, FORMAT_ALIASES, MAP_TYPES, POI_CATEGORIES, POI_PRESETS, PROVINCES, THEMES,
                     match_province, resolve_pois)
from .furniture import (CORNERS, DEFAULT_ELEMENTS, ELEMENTS, LEGEND_POSITIONS, LEGEND_STYLES, NORTH_STYLES,
                        SCALE_STYLES, SCALE_UNITS, Layout)
from .layers import parse_layers
from .osm import get_districts


def build_parser():
    p = argparse.ArgumentParser(
        prog="atlasa0",
        description="A0 print-ready / GIS-ready maps of Pakistan: country, provinces, districts, cities")
    p.add_argument("cities", nargs="*", help='City names, e.g. Peshawar Lahore "Dera Ismail Khan"')
    p.add_argument("--country", action="store_true", help="Whole-country map (provinces, motorways, rivers)")
    p.add_argument("--province", nargs="+", metavar="NAME",
                   help="Province overview map(s), e.g. kpk sindh, or 'all'")
    p.add_argument("--province-cities", nargs="+", metavar="NAME",
                   help="City maps for the preset main cities of these provinces (or 'all')")
    p.add_argument("--district", nargs="+", metavar="NAME",
                   help="District map(s), clipped to the district boundary. Needs --in PROVINCE")
    p.add_argument("--in", dest="in_prov", metavar="PROVINCE",
                   help="Province the --district names belong to (e.g. kpk)")
    p.add_argument("--districts-of", nargs="+", metavar="PROVINCE",
                   help="Map EVERY district of these provinces (or 'all'; can be hundreds of files)")
    p.add_argument("--batch", metavar="FILE.json",
                   help="Run a JSON list of jobs (see README), mixed levels allowed")
    p.add_argument("--type", nargs="+", metavar="TYPE", default=["street"],
                   help="Map type(s) for cities/districts: " + ", ".join(MAP_TYPES) +
                        ", or 'all' (one file per type). Default: street")
    p.add_argument("--poi", nargs="+", metavar="NAME",
                   help="Overlay points of interest on city/district maps: categories and/or presets, "
                        "e.g. hospitals schools, or 'receptors' (see --list-poi)")
    p.add_argument("--poi-labels", action="store_true", help="Write the name next to each point")
    p.add_argument("--poi-data", action="store_true",
                   help="Also save the points as <map>_poi.geojson and .csv for GIS")
    p.add_argument("--poi-format", nargs="+", choices=["csv", "geojson", "xlsx", "summary"], metavar="FMT",
                   help="Receptor file format(s): csv, geojson, xlsx (Excel), summary (category counts). "
                        "Default: csv + geojson. Giving this implies --poi-data")
    p.add_argument("--poi-only", action="store_true",
                   help="Data only: save GeoJSON/CSV of the points for each region, draw no maps "
                        "(default categories: the 'receptors' preset)")
    p.add_argument("--list-poi", action="store_true", help="List point-of-interest categories and presets")
    p.add_argument("--format", nargs="+", default=["png"], metavar="FMT",
                   help="png and/or tiff (tiff = georeferenced for ArcMap/QGIS). Default: png")
    p.add_argument("--outdir", default=os.environ.get("ATLASA0_OUTDIR", "output"), help="Folder to save files in (created if missing). Default: $ATLASA0_OUTDIR or output")
    p.add_argument("--name", metavar="TEMPLATE", default=None,
                   help="Your own file name instead of the automatic one, e.g. 'Map_{region}_{type}_{date}' "
                        "(fields: {region} {level} {type} {province} {dpi} {date}; no extension). Default: automatic names")
    p.add_argument("--skip-existing", action="store_true",
                   help="Don't redo maps whose files already exist (resume a long bulk run)")
    p.add_argument("--preview", action="store_true",
                   help="Quick look: 50 dpi PNG only, files end with _preview (ignores --dpi / --format / --skip-existing)")
    p.add_argument("--dry-run", action="store_true", help="Show what would be made, download nothing")
    p.add_argument("--manifest", metavar="FILE", help="Write a JSON list of files produced/failed")
    p.add_argument("--zoom", type=int, default=None,
                   help="tile zoom for satellite/topo (default: auto, ~10,000 px wide; max 17)")
    p.add_argument("--dpi", type=int, default=int(os.environ.get("ATLASA0_DPI", 300)),
                   help="Resolution 50-500; default $ATLASA0_DPI or 300 (200 on low-memory PCs; 400-500 needs a lot of RAM)")
    p.add_argument("--paper", default=None, metavar="SIZE",
                   help="Paper size: A0 (default), A1, A2, A3, A4 or WxH in mm, e.g. 500x700. --dpi is the print resolution on that paper")
    p.add_argument("--choropleth", default=None, metavar="SPEC",
                   help='Shade provinces (country map) or districts (province map) from a table: "data.csv;name_col=District;'
                        'value_col=Population;classes=5;palette=YlOrRd;title=Population;show_values=1"')
    p.add_argument("--landscape", action="store_true", help="Same as --orientation landscape")
    p.add_argument("--orientation", choices=["auto", "portrait", "landscape"], default=None,
                   help="Sheet orientation. auto (default) = landscape for wide areas, portrait for tall ones "
                        "(e.g. Khyber Pakhtunkhwa)")
    p.add_argument("--buildings", action="store_true", help="include building footprints (street maps)")
    p.add_argument("--theme", choices=THEMES.keys(),
                   default=os.environ.get("ATLASA0_THEME", "light") if os.environ.get("ATLASA0_THEME", "light") in THEMES else "light")
    p.add_argument("--radius-km", type=float, default=None,
                   help="map a fixed radius around the centre instead of the whole boundary")
    g = p.add_argument_group("map elements (legend, scale, north arrow, grid, title, note, logo)")
    g.add_argument("--elements", nargs="+", metavar="NAME",
                   help="Elements to draw: " + ", ".join(ELEMENTS) + ", or all / none. Default: "
                        + " ".join(DEFAULT_ELEMENTS) + ". See --list-elements")
    g.add_argument("--title", help="Replace the map title")
    g.add_argument("--subtitle", help="Replace the subtitle line")
    g.add_argument("--legend-item", nargs="+", metavar="LABEL=COLOUR",
                   help='Extra legend entries, e.g. "Proposed site=#d62728" "Canal=#1f77b4"')
    g.add_argument("--legend-pos", choices=LEGEND_POSITIONS, help="Legend position (default: lower right)")
    g.add_argument("--note", help="Text box on the map (e.g. 'Draft - for discussion')")
    g.add_argument("--logo", metavar="FILE", help="Logo image placed top-left on the sheet")
    g.add_argument("--grid-km", type=float, help="Grid spacing in km for the 'grid' element (default: automatic)")
    g.add_argument("--legend-style", choices=list(LEGEND_STYLES), help="Legend look: " + ", ".join(LEGEND_STYLES))
    g.add_argument("--legend-title", help="Legend heading (default LEGEND; empty string = none)")
    g.add_argument("--legend-cols", type=int, help="Legend columns (default 1)")
    g.add_argument("--north-style", choices=list(NORTH_STYLES), help="North arrow: " + ", ".join(NORTH_STYLES))
    g.add_argument("--north-pos", choices=CORNERS, help="North arrow corner (default upper left)")
    g.add_argument("--north-size", type=float, help="North arrow size factor (default 1)")
    g.add_argument("--scale-style", choices=list(SCALE_STYLES), help="Scale: " + ", ".join(SCALE_STYLES))
    g.add_argument("--scale-units", choices=list(SCALE_UNITS), help="Scale units (default km)")
    g.add_argument("--scale-pos", choices=CORNERS, help="Scale corner (default lower left)")
    g.add_argument("--scale-divisions", type=int, help="Segments in the scale bar (default 4)")
    g.add_argument("--text-label", action="append", metavar="SPEC",
                   help='Free label: "Text@lon,lat;size=50;color=#900;bold=1;box=1;rotation=30". Repeat for more')
    g.add_argument("--note-pos", choices=["lower center", "upper center"], help="Where the note box goes")
    d = p.add_argument_group("your own data (points, lines, polygons)")
    d.add_argument("--layer", action="append", metavar="SPEC",
                   help='Add a shapefile/GeoJSON/GPKG/KML/CSV: "file.shp;name=Sites;color=#d62728;alpha=0.6;'
                        'marker=triangle;size_mm=8;line_style=dashed;width_mm=1;hatch=diagonal;label_field=NAME;fit=1". '
                        'Repeat --layer for more files. Markers/line styles/hatches: see --list-styles')
    p.add_argument("--draw-order", metavar="GROUPS", default=None,
                   help="What is printed on top of what, bottom -> top, comma separated, e.g. "
                        "'landuse,buildings,boundaries,roads,water' puts water above roads. Groups left out keep "
                        "their default place. See --list-styles for the groups")
    p.add_argument("--list-styles", action="store_true", help="List marker, line, hatch, legend, north and scale styles")
    g.add_argument("--tiff-furniture", action="store_true",
                   help="Also burn legends/scale/north/grid into the GeoTIFF (default: GeoTIFF stays clean)")
    p.add_argument("--list-elements", action="store_true", help="List the map elements and exit")
    p.add_argument("--about", action="store_true", help="Show author and licence notice")
    p.add_argument("--gui", action="store_true", help="Open the graphical window (Tkinter) instead of using flags")
    p.add_argument("--list", action="store_true", help="List provinces and preset cities")
    p.add_argument("--list-types", action="store_true", help="Describe the available map types")
    p.add_argument("--list-districts", nargs="+", metavar="PROVINCE",
                   help="Print the district names of these provinces and exit")
    return p


def main(argv=None):
    p = build_parser()
    a = p.parse_args(argv)

    def resolve(names):
        return list(PROVINCES) if [n.lower() for n in names] == ["all"] else [match_province(n) for n in names]

    if a.list:
        for k, v in PROVINCES.items():
            print(f"{k}: {', '.join(v)}")
        return 0
    if a.list_types:
        for k, v in MAP_TYPES.items():
            print(f"{k:10s} {v}")
        return 0
    if a.about:
        from . import __version__
        print(f"AtlasA0 {__version__}\nAuthor: Imaad Ullah Khan Yameen\nEmail: yameenimaad@gmail.com\nThis code is not for sale.\n"
              "Licence: PolyForm Noncommercial 1.0.0 (see LICENSE) - commercial use needs written permission.\n"
              "Security issues: see SECURITY.md (report privately by email).")
        from .config import diagnostics
        print(diagnostics())
        return 0
    if a.gui:
        try:
            from .gui_tk import launch
        except ImportError as e:
            p.error(f"the GUI needs Tkinter ({e}). Install Python with Tk support (python.org installers include it).")
        launch()
        return 0
    if a.list_styles:
        from .layers import HATCHES, LINE_STYLES, MARKERS
        print("markers    :", ", ".join(MARKERS))
        print("line styles:", ", ".join(LINE_STYLES))
        print("hatches    :", ", ".join(HATCHES))
        for title, d in (("legend", LEGEND_STYLES), ("north", NORTH_STYLES), ("scale", SCALE_STYLES)):
            print(f"{title:11s}:", ", ".join(f"{k} ({v})" for k, v in d.items()))
        print("scale units:", ", ".join(SCALE_UNITS))
        print("positions  :", ", ".join(LEGEND_POSITIONS), "(north/scale: corners only)")
        from .furniture import DRAW_GROUPS
        print("\ndraw order (default, bottom -> top; legend/scale/north/title are always above):")
        for i, (k, v) in enumerate(DRAW_GROUPS.items(), 1):
            print(f"  {i:2d}. {k:11s} {v}")
        return 0
    if a.list_elements:
        for k, v in ELEMENTS.items():
            print(f"{k:8s} {v}{'  (default)' if k in DEFAULT_ELEMENTS else ''}")
        return 0
    if a.list_poi:
        for k, v in POI_CATEGORIES.items():
            print(f"{k:14s} {v['label']}")
        print()
        for k, v in POI_PRESETS.items():
            print(f"preset {k:10s} {', '.join(v) if k != 'all' else 'every category above'}")
        return 0
    if a.list_districts:
        for pv in resolve(a.list_districts):
            print(f"\n{pv}:")
            print(", ".join(get_districts(pv)["dname"]))
        return 0

    try:
        resolve_pois(a.poi)
    except ValueError as e:
        p.error(str(e))
    types = list(MAP_TYPES) if [x.lower() for x in a.type] == ["all"] else [x.lower() for x in a.type]
    bad = [x for x in types if x not in MAP_TYPES]
    if bad:
        p.error(f"unknown map type(s): {', '.join(bad)}. Use --list-types")
    badf = [x for x in a.format if x.lower() not in FORMAT_ALIASES]
    if badf:
        p.error(f"unknown format(s): {', '.join(badf)}. Use png and/or tiff")
    if a.district and not a.in_prov:
        p.error("--district needs --in PROVINCE (e.g. --district Swat --in kpk)")

    layout = {"elements": a.elements, "title": a.title, "subtitle": a.subtitle, "legend_items": a.legend_item,
              "legend_pos": a.legend_pos, "note": a.note, "logo": a.logo, "grid_km": a.grid_km,
              "tiff_furniture": a.tiff_furniture, "legend_style": a.legend_style, "legend_title": a.legend_title,
              "legend_cols": a.legend_cols, "north_style": a.north_style, "north_pos": a.north_pos,
              "north_size": a.north_size, "scale_style": a.scale_style, "scale_units": a.scale_units,
              "scale_pos": a.scale_pos, "scale_divisions": a.scale_divisions, "labels": a.text_label,
              "note_pos": a.note_pos, "draw_order": a.draw_order, "paper": a.paper, "choropleth": a.choropleth}
    layout = {k: v for k, v in layout.items() if v not in (None, False)}
    try:
        layers = a.layer or None
        parse_layers(layers)
    except ValueError as e:
        p.error(str(e))
    try:
        Layout.from_any(layout)
    except ValueError as e:
        p.error(str(e))

    # ---- collect jobs (any mix of levels)
    jobs = []
    if a.country:
        jobs.append({"level": "country"})
    for pv in (resolve(a.province) if a.province else []):
        jobs.append({"level": "province", "region": pv})
    cities = list(a.cities)
    for pv in (resolve(a.province_cities) if a.province_cities else []):
        cities += [c for c in PROVINCES[pv] if c not in cities]
    jobs += [{"level": "city", "region": c} for c in cities]
    if a.district:
        pv = match_province(a.in_prov)
        jobs += [{"level": "district", "region": d, "province": pv} for d in a.district]
    for pv in (resolve(a.districts_of) if a.districts_of else []):
        jobs += [{"level": "district", "region": d, "province": pv} for d in get_districts(pv)["dname"]]
    if a.batch:
        with open(a.batch, encoding="utf-8") as f:
            data = json.load(f)
        # a plain list of jobs, or {"author": ..., "email": ..., "jobs": [...]} (JSON has no comments)
        jobs += data["jobs"] if isinstance(data, dict) else data

    if not jobs:
        p.error("nothing to make: give a city, or --country / --province / --district / "
                "--districts-of / --batch")

    a.landscape = "landscape" if a.landscape else (a.orientation or "auto")
    if not est.DPI_MIN <= a.dpi <= est.DPI_MAX:
        p.error(f"--dpi must be between {est.DPI_MIN} and {est.DPI_MAX}")
    if a.name:
        try:
            file_stem(a.name, region="sample", level="city", type="street", dpi=100)
        except ValueError as e:
            p.error(str(e))
        if len(jobs) * max(1, len(types or [])) > 1 and "{region}" not in a.name:
            p.error("--name makes several maps here, so it must contain {region} (and {type} if you give several map types), "
                    "otherwise the files would overwrite each other.")

    if a.poi_only:
        counts_all, files = {}, []
        for j in jobs:
            label = f"{j['level']} {j.get('region') or 'Pakistan'}"
            print(f"\n=== {label}: points of interest ===")
            try:
                r = export_receptors(j.get("region"), j["level"], j.get("province"),
                                     a.poi or "receptors", a.outdir, a.poi_format or ("csv", "geojson"))
                counts_all[label] = r["counts"]
                files += r["files"]
                print(f"[{label}] " + ", ".join(f"{k}: {n}" for k, n in r["counts"].items()))
            except (Exception, SystemExit) as e:
                print(f"[{label}] FAILED: {e}")
        print(f"\nDone: {len(files)} file(s).")
        return 0

    res = run_batch(jobs, outdir=a.outdir, skip_existing=a.skip_existing, dry_run=a.dry_run,
                    types=types, formats=a.format, dpi=a.dpi, landscape=a.landscape,
                    buildings=a.buildings, theme=a.theme, radius_km=a.radius_km, zoom=a.zoom,
                    pois=a.poi, poi_labels=a.poi_labels,
                    poi_data=a.poi_data or bool(a.poi_format),
                    poi_formats=a.poi_format or ("geojson", "csv"), layout=layout or None, layers=layers,
                    filename=a.name, preview=a.preview)

    if a.dry_run:
        calls = []
        for j in jobs:
            lv = j.get("level", "city")
            ts = j.get("types") or types or ["street"]
            calls += [(lv, lv)] if lv in ("country", "province") else [(lv, t) for t in ts]
        paper = Layout.from_any(layout).paper
        e = est.estimate_calls(calls, a.dpi, a.format, a.landscape, paper)
        w, h = est.sheet_pixels(a.dpi, a.landscape, paper)
        g = lambda m: "measured" if m else "rough guess"
        print(f"Estimate: {paper} {w} x {h} px, about {est.ram_gb(a.dpi, a.landscape, 'tiff' in [f.lower() for f in a.format], paper):.1f} GB RAM | "
              f"download about {est.fmt_mb(e['download_mb'])} ({g(e['download_measured'])}, less if cached) | "
              f"files about {est.fmt_mb(e['files_mb'])} ({g(e['files_measured'])})")

    if a.manifest and not a.dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(a.manifest)), exist_ok=True)
        with open(a.manifest, "w") as f:
            json.dump(res, f, indent=2, default=str)
        print(f"manifest -> {a.manifest}")
    return 1 if res["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
