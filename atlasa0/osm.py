# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""OpenStreetMap access: features, road networks and district boundaries (cached)."""
import os

import geopandas as gpd
import osmnx as ox

import pandas as pd

from .config import POI_CATEGORIES, PROVINCE_QUERY
from .runtime import log

ox.settings.use_cache = True
ox.settings.log_console = False
ox.settings.cache_folder = os.environ.get("ATLASA0_CACHE", "cache")


def overview_query_polygon(geom, tol=0.005):
    """Simplified polygon + settings so province/country-wide queries run as ONE Overpass request
    (a full-resolution national boundary is too big to send, and splitting it takes hundreds of calls)."""
    ox.settings.requests_timeout = 900
    ox.settings.max_query_area_size = 5e13
    return geom.simplify(tol, preserve_topology=True)


def first(v):
    return v[0] if isinstance(v, list) else v


def get_features(poly, tags):
    """OSM features matching ANY of `tags` (osmnx semantics). A failed request is logged (it used to be silent,
    which made e.g. missing rivers impossible to diagnose) and gives an empty frame."""
    try:
        return ox.features_from_polygon(poly, tags)
    except Exception as e:
        msg = str(e).splitlines()[0][:160] if str(e) else type(e).__name__
        log(f"  OpenStreetMap request for {tags} gave nothing: {msg}")
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")


def admin_areas(poly, level, label=""):
    """Administrative areas of exactly one admin_level (4 = province, 6 = district in Pakistan).
    Only `admin_level` is requested, then the result is filtered - see overview.filter_admin for why."""
    from .overview import filter_admin
    d = get_features(poly, {"admin_level": str(level)})
    kept, dropped = filter_admin(d, level)
    if dropped:
        log(f"  {label or 'areas'}: kept {len(kept)} at admin_level {level}, ignored {dropped} other features")
    return kept


def _roads(poly, utm, major):
    try:
        if major:
            G = ox.graph_from_polygon(
                poly, simplify=True, retain_all=True,
                custom_filter='["highway"~"motorway|trunk|primary|secondary|tertiary"]')
        else:
            G = ox.graph_from_polygon(poly, network_type="all", simplify=True, retain_all=True)
        e = ox.graph_to_gdfs(G, nodes=False).to_crs(utm)
        e["cls"] = e["highway"].apply(first)
        return e
    except Exception:
        return gpd.GeoDataFrame({"cls": []}, geometry=[], crs=utm)


_DISTRICT_CACHE = {}


def get_districts(prov):
    """All districts (OSM admin_level 6) of a province as a GeoDataFrame in EPSG:4326."""
    if prov in _DISTRICT_CACHE:
        return _DISTRICT_CACHE[prov]
    ox.settings.requests_timeout = 600
    pb = ox.geocode_to_gdf(PROVINCE_QUERY[prov])
    d = admin_areas(overview_query_polygon(pb.geometry.iloc[0]), 6, f"{prov} districts").copy()
    if d.empty:
        raise SystemExit(f"No districts found for {prov} (OpenStreetMap may be busy; try again).")
    pu = pb.to_crs(pb.estimate_utm_crs()).geometry.iloc[0]
    du = d.to_crs(pb.estimate_utm_crs())
    d = d[du.geometry.representative_point().within(pu).values]

    def nm(r):
        v = r.get("name:en")
        return v if isinstance(v, str) else r.get("name")

    d["dname"] = d.apply(nm, axis=1)
    d = d[d["dname"].notna()].sort_values("dname")
    _DISTRICT_CACHE[prov] = d
    return d


def get_pois(poly, keys, utm):
    """Points of interest inside `poly` for the given category keys, as a point GeoDataFrame (UTM).

    Polygons (e.g. a hospital building) become one point. Columns: category, name, geometry."""
    parts = []
    for k in keys:
        log(f"    - {POI_CATEGORIES[k]['label']}...")
        g = get_features(poly, POI_CATEGORIES[k]["tags"])
        if g.empty:
            continue
        g = g[g.geom_type.isin(["Point", "Polygon", "MultiPolygon"])].copy()
        if g.empty:
            continue

        def nm(r):
            for c in ("name:en", "name"):
                v = r.get(c)
                if isinstance(v, str) and v:
                    return v
            return ""

        pts = [x if x.geom_type == "Point" else x.representative_point() for x in g.geometry]
        parts.append(gpd.GeoDataFrame({"category": k, "name": [nm(r) for _, r in g.iterrows()]},
                                      geometry=pts, crs=g.crs))
    if not parts:
        return gpd.GeoDataFrame({"category": [], "name": []}, geometry=[], crs=utm)
    return gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=parts[0].crs).to_crs(utm)
