# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Public API for a project viewer / web backend.

    from atlasa0 import generate_map, run_batch, list_districts

    generate_map("Swat", level="district", province="kpk", map_type="landuse",
                 formats=("png", "tiff"), outdir="static/maps")
    generate_map(level="country", formats=("png", "tiff"))          # whole of Pakistan
    run_batch([{"level": "province", "region": "kpk"}, {"level": "city", "region": "Peshawar"}])
"""
import os

import osmnx as ox
import pandas as pd

from . import estimates as est
from .config import (file_stem, FORMAT_ALIASES, MAP_TYPES, POI_FILE_SUFFIX, PROVINCE_QUERY, match_province,
                     resolve_pois)
from .export import write_poi_files
from .osm import get_districts, get_pois, overview_query_polygon
from .furniture import Layout
from .layers import parse_layers
from .render import make_country_map, make_map, make_province_map
from .runtime import Cancelled, log, say

LEVELS = ("country", "province", "district", "city")


def list_districts(province):
    """District names (as used by --district / generate_map) for a province."""
    return list(get_districts(match_province(province))["dname"])


def _find_district(prov, district):
    d = get_districts(prov)
    q = district.strip().lower()
    hit = d[d["dname"].str.lower() == q]
    if hit.empty:
        hit = d[d["dname"].str.lower().str.contains(q, regex=False)]
    if hit.empty:
        raise ValueError(f"district '{district}' not found in {prov}. Use --list-districts {prov}")
    return hit.iloc[[0]]


def make_district_map(district, prov, dpi, landscape, buildings, theme_name, out,
                      map_type="street", zoom=None, formats=("png",),
                      pois=None, poi_labels=False, poi_data=False, poi_formats=("geojson", "csv"), layout=None, layers=None):
    row = _find_district(prov, district)
    name = row["dname"].iloc[0]
    return make_map(f"{name} District", dpi, landscape, buildings, theme_name, None, out,
                    boundary=row[["geometry"]], mask=True, sub=f"{prov.upper()}",
                    map_type=map_type, zoom=zoom, formats=formats,
                    pois=pois, poi_labels=poi_labels, poi_data=poi_data, poi_formats=poi_formats, layout=layout, layers=layers)


def _slug(s):
    return s.lower().replace(" ", "_").replace("-", "_")


def generate_map(region=None, level="city", province=None, map_type="street", formats=("png",),
                 dpi=300, landscape=False, buildings=False, theme="light", radius_km=None,
                 zoom=None, outdir=".", skip_existing=False,
                 pois=None, poi_labels=False, poi_data=False, poi_formats=("geojson", "csv"), layout=None, layers=None, filename=None):
    """Make one map (in one or more file formats).

    level    : "country" | "province" | "district" | "city"
    region   : city / district / province name (country: optional, default "Pakistan")
    province : required for level="district" (e.g. "Khyber Pakhtunkhwa" or "kpk")
    map_type : one of MAP_TYPES (city/district only; province/country have a fixed layout)
    formats  : "png" and/or "tiff" (tiff = georeferenced, for ArcMap/QGIS)
    skip_existing : reuse files that already exist (lets you resume an interrupted bulk run)
    pois     : points of interest to overlay on city/district maps: category and/or preset names,
               e.g. ["hospitals", "schools"] or "receptors" (see config.POI_CATEGORIES / POI_PRESETS)
    poi_labels : write the name next to each point
    poi_data : also save the points next to the map
    poi_formats : "csv", "geojson", "xlsx" (Excel, needs openpyxl), "summary" (category counts); default csv+geojson
    layers   : your own data drawn on the map - list of dicts / 'file.shp;color=..;alpha=..' strings / LayerSpec
               (points, lines, polygons from shp, geojson, gpkg, kml, csv); see layers.py
    filename : None = automatic names (e.g. peshawar_A0_300dpi.png) or a template like 'Map_{region}_{type}_{date}'
               (fields {region} {level} {type} {province} {dpi} {date}; no extension - it is added per file type)
    landscape: False / "portrait", True / "landscape", or "auto" (wide area -> landscape, tall area -> portrait)
    layout   : map elements/legends - dict or furniture.Layout: elements (title legend scale north grid credit),
               title, subtitle, legend_items [[label, colour]], legend_pos, note, logo, grid_km, tiff_furniture
    Returns a list of {"path","format","level","region","map_type","skipped"}.
    """
    if level not in LEVELS:
        raise ValueError(f"level must be one of {', '.join(LEVELS)}")
    if not est.DPI_MIN <= int(dpi) <= est.DPI_MAX:
        raise ValueError(f"dpi must be between {est.DPI_MIN} and {est.DPI_MAX}")
    mt = (map_type or "street").lower()
    if level in ("city", "district") and mt not in MAP_TYPES:
        raise ValueError(f"unknown map type '{map_type}'. Options: {', '.join(MAP_TYPES)}")
    Layout.from_any(layout)  # validate early (before any download)
    layers = [s for s in parse_layers(layers)] or None  # LayerSpec objects; files checked now
    fmts = sorted({FORMAT_ALIASES[f.lower()] for f in formats})
    os.makedirs(outdir, exist_ok=True)
    suffix = "" if mt == "street" else f"_{mt}"
    if pois and level in ("city", "district"):
        names = [pois] if isinstance(pois, str) else list(pois)
        resolve_pois(names)  # validate early
        suffix += "_poi_" + "+".join(_slug(n) for n in names)

    if level == "country":
        region, mt = region or "Pakistan", "country"
        stem = f"country_{_slug(region)}_A0_{dpi}dpi"
    elif level == "province":
        region, mt = match_province(region), "province"
        stem = f"province_{_slug(region)}_A0_{dpi}dpi"
    elif level == "district":
        if not province or not region:
            raise ValueError("level='district' needs region (district) and province")
        province = match_province(province)
        stem = f"district_{_slug(province)}_{_slug(region)}{suffix}_A0_{dpi}dpi"
    else:
        if not region:
            raise ValueError("level='city' needs a region (city name)")
        stem = f"{_slug(region)}{suffix}_A0_{dpi}dpi"

    if filename:
        stem = file_stem(filename, region=_slug(region) if region else "", level=level, province=_slug(province) if province else "",
                         type=mt if level in ("city", "district") else level, dpi=dpi)
    out = os.path.join(outdir, stem + ".png")
    expected = [os.path.join(outdir, stem + (".png" if f == "png" else ".tif")) for f in fmts]
    want_poi_files = poi_data and level in ("city", "district") and (pois or mt == "receptors")
    if want_poi_files:
        expected += [os.path.join(outdir, stem + POI_FILE_SUFFIX[f.lower()]) for f in poi_formats]

    def result(paths, skipped):
        fmt_of = lambda p: ("tiff" if p.endswith(".tif") else "geojson" if p.endswith(".geojson")
                            else "xlsx" if p.endswith(".xlsx") else "csv" if p.endswith(".csv") else "png")
        return [{"path": p, "format": fmt_of(p), "level": level,
                 "region": region, "map_type": mt, "skipped": skipped} for p in paths]

    if skip_existing and all(os.path.exists(p) for p in expected):
        log(f"[{region}] already exists, skipping")
        return result(expected, True)

    cache_dir = getattr(getattr(ox, "settings", None), "cache_folder", None)
    cache_before = est.folder_mb(cache_dir) if cache_dir and os.path.isdir(cache_dir) else None
    if level == "country":
        paths = make_country_map(dpi, landscape, theme, out, formats=fmts, country=region, layout=layout, layers=layers)
    elif level == "province":
        paths = make_province_map(region, dpi, landscape, theme, out, formats=fmts, layout=layout, layers=layers)
    elif level == "district":
        paths = make_district_map(region, province, dpi, landscape, buildings, theme, out,
                                  map_type=mt, zoom=zoom, formats=fmts,
                                  pois=pois, poi_labels=poi_labels, poi_data=poi_data,
                                  poi_formats=poi_formats, layout=layout, layers=layers)
    else:
        paths = make_map(region, dpi, landscape, buildings, theme, radius_km, out,
                         map_type=mt, zoom=zoom, formats=fmts,
                         pois=pois, poi_labels=poi_labels, poi_data=poi_data,
                         poi_formats=poi_formats, layout=layout, layers=layers)
    _learn_sizes(paths, level, mt, dpi, landscape, cache_dir, cache_before)
    return result(paths, False)


def _learn_sizes(paths, level, mt, dpi, landscape, cache_dir, cache_before):
    """Remember real file sizes and download size so later estimates are measured, not guessed."""
    try:
        for p in paths or []:
            if p.endswith(".png"):
                est.record_file(mt, "png", p, dpi, landscape)
            elif p.endswith(".tif"):
                est.record_file(mt, "tiff", p, dpi, landscape)
        if cache_before is not None:
            est.record_download(level, mt, est.folder_mb(cache_dir) - cache_before)
    except Exception:
        pass


def _region_boundary(region, level, province):
    if level == "city":
        return ox.geocode_to_gdf(f"{region}, Pakistan")
    if level == "district":
        return _find_district(match_province(province), region)[["geometry"]]
    if level == "province":
        return ox.geocode_to_gdf(PROVINCE_QUERY[match_province(region)])
    if level == "country":
        return ox.geocode_to_gdf(region or "Pakistan")
    raise ValueError(f"level must be one of {', '.join(LEVELS)}")


def find_receptors(region=None, level="city", province=None, pois="receptors"):
    """Points of interest / sensitive receptors inside a region - data only, no map.

    pois: category and/or preset names (default: the "receptors" preset = hospitals, clinics,
          schools, colleges, places of worship, water sources).
    Returns {"counts": {category: n}, "table": DataFrame(category, name, lon, lat), "gdf": GeoDataFrame}.
    """
    keys = resolve_pois(pois)
    b = _region_boundary(region, level, province)
    utm = b.to_crs(32642).crs if level == "country" else b.estimate_utm_crs()
    geom = b.geometry.iloc[0]
    poly = overview_query_polygon(geom) if level in ("province", "country") else geom
    g = get_pois(poly, keys, utm)
    if not g.empty:
        g = g[g.within(b.to_crs(utm).geometry.iloc[0])]
    w = g.to_crs(4326)
    table = pd.DataFrame({"category": g["category"].values, "name": g["name"].values,
                          "lon": w.geometry.x.values, "lat": w.geometry.y.values})
    counts = {k: int((table["category"] == k).sum()) for k in keys}
    return {"counts": counts, "table": table, "gdf": g}


def export_receptors(region=None, level="city", province=None, pois="receptors", outdir="output",
                     formats=("csv", "geojson")):
    """find_receptors + save <name>_receptors_poi.csv and/or .geojson for GIS. Returns {"files", "counts"}."""
    res = find_receptors(region, level, province, pois)
    os.makedirs(outdir, exist_ok=True)
    nm = _slug(region or "pakistan") if level != "district" else \
        f"{_slug(match_province(province))}_{_slug(region)}"
    base = os.path.join(outdir, f"{level}_{nm}_receptors")
    return {"files": write_poi_files(res["gdf"], base, formats, counts=res["counts"]),
            "counts": res["counts"]}


def run_batch(jobs, outdir="output", skip_existing=False, dry_run=False, on_event=None, **defaults):
    """Run many maps in one go (any mix of country / province / district / city).

    jobs     : list of dicts with the generate_map arguments; "types": [..] makes one file per
               map type. Anything not given in a job comes from **defaults (dpi, theme, formats,
               types, landscape, ...).
    on_event : optional callback receiving progress dicts (job_start / job_done / job_failed / cancelled) for GUIs;
               see runtime.py. Call runtime.request_cancel() (or JobRunner.cancel()) to stop at the next stage.
    Returns {"files": [...], "failed": [{"job", "error"}]} (+ "cancelled": True if stopped). One failure never stops the batch.
    """
    calls = []
    for j in jobs:
        kw = {**defaults, **j}
        types = kw.pop("types", None)
        mt = kw.pop("map_type", None)
        types = list(types) if types else [mt or "street"]
        if kw.get("level") in ("country", "province"):
            types = types[:1]  # fixed layout: map type does not apply
        for t in types:
            calls.append({**kw, "map_type": t})

    files, failed, cancelled = [], [], False

    def emit(ev):
        if on_event:
            on_event(ev)

    for i, c in enumerate(calls, 1):
        kind = "" if c.get("level") in ("country", "province") else c.get("map_type")
        label = f"{c.get('level')} {c.get('region') or ''} {kind}".replace("  ", " ").strip()
        say(f"\n=== [{i}/{len(calls)}] {label} ===")
        if dry_run:
            continue
        emit({"type": "job_start", "index": i, "total": len(calls), "label": label})
        try:
            got = generate_map(outdir=outdir, skip_existing=skip_existing, **c)
            files += got
            emit({"type": "job_done", "index": i, "total": len(calls), "label": label, "files": got})
        except Cancelled:
            print(f"[{label}] cancelled")
            emit({"type": "cancelled"})
            cancelled = True
            break
        except (Exception, SystemExit) as e:  # SystemExit: e.g. contextily missing
            say(f"[{label}] FAILED: {e}")
            failed.append({"job": c, "error": str(e)})
            emit({"type": "job_failed", "index": i, "total": len(calls), "label": label, "error": str(e)})
    if dry_run:
        say(f"\n{len(calls)} map job(s) planned (dry run, nothing downloaded).")
    else:
        say(f"\nDone: {len(files)} file(s), {len(failed)} failed job(s).")
    out = {"files": files, "failed": failed}
    if cancelled:
        out["cancelled"] = True
    return out
