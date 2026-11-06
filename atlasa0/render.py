# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Drawing: city/district maps (all map types) and province overview maps."""
import math
import os

import geopandas as gpd
import matplotlib.pyplot as plt
import osmnx as ox
from matplotlib.patches import Patch, Rectangle
from shapely.geometry import box

from .config import (AXES_RECT, POI_CATEGORIES, POI_PRESETS, resolve_pois, A0_INCHES, LANDUSE_COLORS, LANDUSE_OTHER, MAP_TYPES, PROVINCE_QUERY,
                     ROAD_WIDTH, THEMES)
from .export import save_outputs, write_poi_files
from .furniture import Layout, apply_layout, draw_zorders, nice_scale_km  # noqa: F401 (nice_scale_km re-exported)
from .osm import _roads, admin_areas, first, get_features, get_pois, overview_query_polygon
from .overview import clean_label, pick_landscape, place_labels
from .layers import draw_layers, layers_bounds, load_layers
from .runtime import log


def axes_aspect(size):
    """Width/height of the drawing area (not the whole sheet) - the map extent must match THIS
    shape or the map leaves blank bands inside the frame."""
    return (AXES_RECT[2] * size[0]) / (AXES_RECT[3] * size[1])


def fit_extent(bounds, aspect, pad=1.08, radius_km=None):
    """Expand `bounds` (minx, miny, maxx, maxy in metres) by `pad` and grow one side so the
    extent has exactly `aspect` (width/height), centred. Returns (x0, x1, y0, y1)."""
    minx, miny, maxx, maxy = bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    w, h = maxx - minx, maxy - miny
    if radius_km:  # fixed radius around the centre instead of the whole boundary
        w = h = radius_km * 2000
    w, h = max(w, 1.0) * pad, max(h, 1.0) * pad
    if w / h > aspect:
        h = w / aspect
    else:
        w = h * aspect
    return (cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)


def poi_marker_size(span_km):
    """Marker for receptors, sized for an A0 sheet: 11 mm across on maps up to 10 km wide,
    shrinking (log scale) to 5 mm at 100 km and wider. Returns (scatter area in pt^2, diameter mm)."""
    lo, hi = math.log10(10), math.log10(100)
    f = min(1.0, max(0.0, (math.log10(max(span_km, 1e-6)) - lo) / (hi - lo)))
    d_mm = 11.0 - 6.0 * f
    return (d_mm * 72 / 25.4) ** 2, d_mm


def _basemap_zoom(width_m, lat, zoom):
    if zoom:
        return int(zoom)
    res = width_m / 10000.0  # aim for ~10,000 px across the map
    z = math.log2(156543.03 * math.cos(math.radians(lat)) / max(res, 0.01))
    return int(max(8, min(17, round(z))))


def _union_bounds(a, b):
    if b is None:
        return a
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def make_map(city, dpi, landscape, buildings, theme_name, radius_km, out,
             boundary=None, mask=False, sub="PAKISTAN", map_type="street", zoom=None,
             formats=("png",), pois=None, poi_labels=False, poi_data=False,
             poi_formats=("geojson", "csv"), layout=None, layers=None):
    """boundary/mask are used by district maps: draw only inside the given boundary.
    pois: category/preset names to overlay (see config.POI_CATEGORIES); map_type "receptors"
    defaults to the 'receptors' preset. poi_data also writes <name>_poi.geojson/.csv."""
    lay = Layout.from_any(layout)
    pois = resolve_pois(pois)
    if map_type == "receptors" and not pois:
        pois = list(POI_PRESETS["receptors"])
    t = THEMES[theme_name]
    tag = f"{city}/{map_type}"

    # 1. Boundary -> map extent matched to paper aspect ratio
    if boundary is None:
        boundary = ox.geocode_to_gdf(f"{city}, Pakistan")
    utm = boundary.estimate_utm_crs()
    bp = boundary.to_crs(utm)
    size = A0_INCHES[::-1] if pick_landscape(landscape, bp.total_bounds if not radius_km else (0, 0, 1, 1)) else A0_INCHES
    aspect = axes_aspect(size)
    user_layers = load_layers(layers, utm) if layers else []
    ext = fit_extent(_union_bounds(bp.total_bounds, layers_bounds(user_layers)), aspect, pad=1.08,
                     radius_km=radius_km)
    span_km = (ext[1] - ext[0]) / 1000
    poly = gpd.GeoSeries([box(ext[0], ext[2], ext[1], ext[3])], crs=utm).to_crs(4326).iloc[0]
    if mask:  # district: only download what lies inside the district (+ small buffer)
        poly = bp.buffer(300).to_crs(4326).iloc[0]

    # 2. Download only what this map type needs
    polys = ("Polygon", "MultiPolygon")
    lines = ("LineString", "MultiLineString")
    empty = gpd.GeoDataFrame(geometry=[], crs=utm)
    water = green = blds = lu = rail = empty

    log(f"[{tag}] downloading roads...")
    edges = _roads(poly, utm, major=map_type in ("transport", "water", "satellite", "topo"))

    if map_type in ("street", "water", "landuse", "receptors"):
        log(f"[{tag}] downloading water...")
        water = get_features(poly, {"natural": ["water", "wetland"],
                                    "waterway": ["river", "canal", "stream"],
                                    "landuse": ["reservoir"]}).to_crs(utm)
    if map_type == "street":
        log(f"[{tag}] downloading green areas...")
        green = get_features(poly, {"leisure": ["park", "garden"],
                                    "landuse": ["forest", "grass", "farmland"],
                                    "natural": ["wood"]}).to_crs(utm)
    if map_type == "landuse":
        log(f"[{tag}] downloading land use...")
        lu = get_features(poly, {"landuse": True, "leisure": ["park", "garden"],
                                 "natural": ["wood"]}).to_crs(utm)
    if map_type == "buildings" or (map_type == "street" and buildings):
        log(f"[{tag}] downloading buildings (slow for big cities)...")
        blds = get_features(poly, {"building": True}).to_crs(utm)
    if map_type == "transport":
        rail = get_features(poly, {"railway": ["rail", "light_rail", "subway"]}).to_crs(utm)

    poi_gdf = None
    if pois:
        log(f"[{tag}] downloading points of interest...")
        poi_gdf = get_pois(poly, pois, utm)
        if not poi_gdf.empty:
            inside = bp.geometry.iloc[0] if mask else box(ext[0], ext[2], ext[1], ext[3])
            poi_gdf = poi_gdf[poi_gdf.within(inside)]
        log(f"[{tag}] {len(poi_gdf)} points of interest found")

    # 3. Draw
    fig = plt.figure(figsize=size, dpi=dpi, facecolor=t["bg"])
    margin_x, margin_top, margin_bot = 0.04, 0.10, 0.04
    ax = fig.add_axes(list(AXES_RECT))
    ax.set_facecolor(t["bg"])
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_aspect("equal")

    Z = draw_zorders(lay.draw_order)   # group -> zorder (what is printed on top of what)
    log(f"[{tag}] draw order (bottom -> top): {' < '.join(lay.draw_order)}")

    def fill(gdf, color, group="water"):
        g = gdf[gdf.geom_type.isin(polys)] if not gdf.empty else gdf
        if not g.empty:
            g.plot(ax=ax, color=color, linewidth=0, zorder=Z[group])

    def stroke(gdf, color, lw, group="water", **kw):
        g = gdf[gdf.geom_type.isin(lines)] if not gdf.empty else gdf
        if not g.empty:
            g.plot(ax=ax, color=color, linewidth=lw, zorder=Z[group] + 0.2, **kw)

    def draw_roads(scale=1.0, color=None, alpha=1.0):
        for i, cls in enumerate(list(ROAD_WIDTH.keys())[::-1]):  # small first, big on top
            seg = edges[edges["cls"] == cls] if not edges.empty else edges
            if not seg.empty:
                seg.plot(ax=ax, color=color or t["road"], linewidth=ROAD_WIDTH[cls] * scale,
                         alpha=alpha, capstyle="round", zorder=Z["roads"] + i * 0.05)

    legend = []
    if map_type == "street":
        fill(green, t["green"], "landuse")
        fill(blds, t["building"], "buildings")
        fill(water, t["water"])
        stroke(water, t["water"], 3)
        draw_roads()
    elif map_type == "transport":
        draw_roads(scale=1.3)
        stroke(rail, "#8a3b3b", 4, group="roads", linestyle=(0, (6, 3)))
    elif map_type == "landuse":
        if not lu.empty:
            lp = lu[lu.geom_type.isin(polys)].copy()

            def _kind(r):
                for col_ in ("landuse", "leisure", "natural"):
                    v = r.get(col_)
                    if isinstance(v, str):
                        return v
                return "other"

            lp["_k"] = lp.apply(_kind, axis=1)
            for k, grp in lp.groupby("_k"):  # one plot call per category (fast)
                col = LANDUSE_COLORS.get(k, LANDUSE_OTHER)
                grp.plot(ax=ax, color=col, linewidth=0, zorder=Z["landuse"])
                if k in LANDUSE_COLORS:
                    legend.append((k, col))
        fill(water, t["water"])
        stroke(water, t["water"], 3)
        draw_roads(scale=0.45, alpha=0.8)
    elif map_type == "water":
        fill(water, t["water"])
        stroke(water, t["water"], 6)
        draw_roads(scale=0.4, alpha=0.45)
    elif map_type == "receptors":
        fill(water, t["water"])
        stroke(water, t["water"], 4)
        draw_roads(scale=0.4, alpha=0.5)
    elif map_type == "buildings":
        fill(blds, t["building"] if theme_name == "dark" else "#b9b09c", "buildings")
        draw_roads(scale=0.6, alpha=0.85)
    elif map_type in ("satellite", "topo"):
        try:
            import contextily as cx_
        except ImportError:
            raise SystemExit("satellite/topo maps need contextily:  pip install contextily")
        src = (cx_.providers.Esri.WorldImagery if map_type == "satellite"
               else cx_.providers.OpenTopoMap)
        lat = boundary.geometry.iloc[0].centroid.y
        z = _basemap_zoom(ext[1] - ext[0], lat, zoom)
        log(f"[{tag}] downloading basemap tiles at zoom {z}...")
        cx_.add_basemap(ax, crs=utm.to_string(), source=src, zoom=z, attribution=False, zorder=Z["basemap"])
        draw_roads(scale=0.5, color="#ffffff" if map_type == "satellite" else "#7a2e2e", alpha=0.9)
    else:
        raise ValueError(f"unknown map type '{map_type}'")

    poi_handles = []
    poi_s, poi_mm = poi_marker_size(span_km)
    if poi_gdf is not None and not poi_gdf.empty:
        log(f"[{tag}] receptor markers {poi_mm:.1f} mm on the sheet "
              f"(about {poi_mm / (AXES_RECT[2] * size[0] * 25.4) * (ext[1] - ext[0]):.0f} m on the ground)")
        from matplotlib import patheffects
        from matplotlib.lines import Line2D
        for k in pois:
            sub_ = poi_gdf[poi_gdf["category"] == k]
            if sub_.empty:
                continue
            c_ = POI_CATEGORIES[k]
            ax.scatter(sub_.geometry.x, sub_.geometry.y, s=poi_s, marker=c_["marker"], c=c_["color"],
                       edgecolors="white", linewidths=3, zorder=Z["receptors"])
            poi_handles.append(Line2D([0], [0], marker=c_["marker"], linestyle="", markersize=36,
                                      markerfacecolor=c_["color"], markeredgecolor="white",
                                      markeredgewidth=2, label=f"{c_['label']} ({len(sub_)})"))
            if poi_labels:
                for _, r_ in sub_.iterrows():
                    if r_["name"]:
                        ax.annotate(r_["name"], (r_.geometry.x, r_.geometry.y), xytext=(0, 30),
                                    textcoords="offset points", fontsize=22, ha="center",
                                    color=t["text"], zorder=Z["labels"],
                                    path_effects=[patheffects.withStroke(linewidth=6, foreground=t["bg"])])

    user_handles = draw_layers(ax, user_layers, t, zorder=Z["your_data"], label_zorder=Z["labels"] + 0.3)

    if mask:  # blank everything outside the district and outline it
        outside = box(ext[0], ext[2], ext[1], ext[3]).difference(bp.geometry.iloc[0])
        gpd.GeoSeries([outside], crs=utm).plot(ax=ax, color=t["bg"], linewidth=0, zorder=Z["mask"])
        bp.boundary.plot(ax=ax, color=t["frame"], linewidth=7, zorder=Z["mask"] + 0.5)

    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(t["frame"])
        s.set_linewidth(4)

    c = boundary.geometry.iloc[0].centroid
    kind = "" if map_type == "street" else f"   |   {map_type.upper()} MAP"
    credit = "Map data \u00a9 OpenStreetMap contributors"
    if map_type == "satellite":
        credit += "  |  Imagery \u00a9 Esri, Maxar, Earthstar Geographics"
    elif map_type == "topo":
        credit += "  |  Style \u00a9 OpenTopoMap (CC-BY-SA)"
    apply_layout(fig, ax, ext, t, size, utm, lay,
                 title=city.upper(), subtitle=f"{sub}   |   {abs(c.y):.4f}\u00b0N  {abs(c.x):.4f}\u00b0E{kind}",
                 credit=credit, y_title=1 - margin_top / 2 + 0.008, y_sub=1 - margin_top + 0.02,
                 y_credit=margin_bot / 2, land_entries=legend, poi_handles=poi_handles, user_handles=user_handles)

    log(f"[{tag}] saving (this can take a few minutes)...")
    paths = save_outputs(fig, ax, out, dpi, formats, utm, ext, t["bg"], tag, tiff_furniture=lay.tiff_furniture)
    if poi_data and poi_gdf is not None:
        paths += write_poi_files(poi_gdf, os.path.splitext(out)[0], poi_formats,
                                 counts={k: int((poi_gdf["category"] == k).sum()) for k in pois})
    return paths


def make_province_map(prov, dpi, landscape, theme_name, out, formats=("png",), layout=None, layers=None):
    """Province map: boundary, district boundaries + labels, major highways, rivers."""
    lay = Layout.from_any(layout)
    t = THEMES[theme_name]

    boundary = ox.geocode_to_gdf(PROVINCE_QUERY[prov])
    utm = boundary.estimate_utm_crs()
    bp = boundary.to_crs(utm)
    user_layers = load_layers(layers, utm) if layers else []
    size = A0_INCHES[::-1] if pick_landscape(landscape, bp.total_bounds) else A0_INCHES
    aspect = axes_aspect(size)
    ext = fit_extent(_union_bounds(bp.total_bounds, layers_bounds(user_layers)), aspect, pad=1.06)
    prov_poly_wgs = overview_query_polygon(boundary.geometry.iloc[0])

    log(f"[{prov}] downloading districts...")
    d = admin_areas(prov_poly_wgs, 6, f"{prov} districts")
    d = d.to_crs(utm) if not d.empty else d
    if not d.empty:
        d = d[d.geometry.representative_point().within(bp.geometry.iloc[0])]

    log(f"[{prov}] downloading highways (motorway/trunk/primary)...")
    try:
        G = ox.graph_from_polygon(prov_poly_wgs, network_type="drive", simplify=True,
                                  custom_filter='["highway"~"motorway|trunk|primary"]',
                                  retain_all=True)
        edges = ox.graph_to_gdfs(G, nodes=False).to_crs(utm)
        edges["cls"] = edges["highway"].apply(first)
    except Exception:
        edges = gpd.GeoDataFrame(columns=["cls", "geometry"], geometry="geometry", crs=utm)

    log(f"[{prov}] downloading rivers...")
    rivers = get_features(prov_poly_wgs, {"waterway": ["river"]})
    rivers = rivers.to_crs(utm) if not rivers.empty else gpd.GeoDataFrame(geometry=[], crs=utm)
    log(f"[{prov}] {len(d)} districts, {len(edges)} highway segments, {len(rivers)} river features")
    if rivers.empty:
        log(f"[{prov}] WARNING: no rivers came back from OpenStreetMap (busy server?) - run again to retry")

    fig = plt.figure(figsize=size, dpi=dpi, facecolor=t["bg"])
    ax = fig.add_axes(list(AXES_RECT))
    ax.set_facecolor(t["bg"])
    Z = draw_zorders(lay.draw_order)
    log(f"[{prov}] draw order (bottom -> top): {' < '.join(lay.draw_order)}")
    bp.plot(ax=ax, color=t["green"], linewidth=0, zorder=Z["landuse"])
    if not d.empty:
        d.boundary.plot(ax=ax, color=t["frame"], linewidth=2, linestyle="--", alpha=0.7, zorder=Z["boundaries"])
    if not rivers.empty:
        rivers[rivers.geom_type.isin(["LineString", "MultiLineString"])].plot(
            ax=ax, color=t["water"], linewidth=5, zorder=Z["water"] + 0.2)
    for i, (cls, wd) in enumerate((("primary", 2.5), ("trunk", 4), ("motorway", 5))):
        sub = edges[edges["cls"] == cls]
        if not sub.empty:
            sub.plot(ax=ax, color=t["road"], linewidth=wd, zorder=Z["roads"] + i * 0.1)
    bp.boundary.plot(ax=ax, color=t["frame"], linewidth=8, zorder=Z["boundaries"] + 0.5)

    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    user_handles = draw_layers(ax, user_layers, t, zorder=Z["your_data"], label_zorder=Z["labels"] + 0.3)
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    if not d.empty:   # district names last, after the extent is final, so collisions are measured correctly
        items = []
        for _, r in d.iterrows():
            nm = clean_label(r.get("name:en") if isinstance(r.get("name:en"), str) else r.get("name"))
            if nm:
                pt = r.geometry.representative_point()
                items.append((nm, pt.x, pt.y, r.geometry.area))
        _, skipped = place_labels(ax, items, color=t["text"], alpha=0.9, zorder=Z["labels"],
                                  bbox=dict(boxstyle="round,pad=0.15", fc=t["bg"], ec="none", alpha=0.55))
        if skipped:
            log(f"[{prov}] {len(skipped)} district name(s) left out (no room): {', '.join(skipped)}")
    apply_layout(fig, ax, ext, t, size, utm, lay, title=prov.upper(), user_handles=user_handles,
                 subtitle="DISTRICTS, HIGHWAYS & RIVERS   |   PAKISTAN",
                 credit="Map data \u00a9 OpenStreetMap contributors", y_title=0.955, y_sub=0.915, y_credit=0.02)
    log(f"[{prov}] saving...")
    return save_outputs(fig, ax, out, dpi, formats, utm, ext, t["bg"], prov, tiff_furniture=lay.tiff_furniture)



PROVINCE_TINTS = ["#d6e6c4", "#ebe2b8", "#d3e3d9", "#e8d6c4", "#dcd8ea", "#ead3d3", "#d3e3ea"]


def make_country_map(dpi, landscape, theme_name, out, formats=("png",), country="Pakistan", layout=None,
                     layers=None):
    """Country overview: provinces/territories, motorways + trunk roads, major rivers."""
    lay = Layout.from_any(layout)
    t = THEMES[theme_name]
    tag = country

    boundary = ox.geocode_to_gdf(country)
    bp = boundary.to_crs(32642)  # UTM 42N: central zone for Pakistan (country spans zones 41-43)
    utm = bp.crs
    size = A0_INCHES[::-1] if pick_landscape(landscape, bp.total_bounds) else A0_INCHES
    aspect = axes_aspect(size)
    user_layers = load_layers(layers, utm) if layers else []
    ext = fit_extent(_union_bounds(bp.total_bounds, layers_bounds(user_layers)), aspect, pad=1.05)
    poly = overview_query_polygon(boundary.geometry.iloc[0], tol=0.02)

    log(f"[{tag}] downloading provinces...")
    pr = admin_areas(poly, 4, "provinces")
    pr = pr.to_crs(utm) if not pr.empty else pr
    if not pr.empty:
        pr = pr[pr.geometry.representative_point().within(bp.geometry.iloc[0])]

    log(f"[{tag}] downloading motorways / trunk roads (can take a while)...")
    try:
        G = ox.graph_from_polygon(poly, simplify=True, retain_all=True,
                                  custom_filter='["highway"~"motorway|trunk"]')
        edges = ox.graph_to_gdfs(G, nodes=False).to_crs(utm)
        edges["cls"] = edges["highway"].apply(first)
    except Exception as e:
        log(f"[{tag}] roads skipped: {e}")
        edges = gpd.GeoDataFrame({"cls": []}, geometry=[], crs=utm)

    log(f"[{tag}] downloading rivers...")
    rivers = get_features(poly, {"waterway": ["river"]})
    rivers = rivers.to_crs(utm) if not rivers.empty else gpd.GeoDataFrame(geometry=[], crs=utm)
    log(f"[{tag}] {len(pr)} provinces/territories, {len(edges)} road segments, {len(rivers)} river features")

    fig = plt.figure(figsize=size, dpi=dpi, facecolor=t["bg"])
    ax = fig.add_axes(list(AXES_RECT))
    ax.set_facecolor(t["bg"])
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_aspect("equal")
    Z = draw_zorders(lay.draw_order)
    log(f"[{tag}] draw order (bottom -> top): {' < '.join(lay.draw_order)}")
    bp.plot(ax=ax, color=t["green"], linewidth=0, zorder=Z["landuse"])
    if not pr.empty:
        pr = pr.reset_index(drop=True)
        for i, r_ in pr.iterrows():
            gpd.GeoSeries([r_.geometry], crs=utm).plot(
                ax=ax, color=PROVINCE_TINTS[i % len(PROVINCE_TINTS)], alpha=0.6, linewidth=0, zorder=Z["landuse"] + 0.1)
        pr.boundary.plot(ax=ax, color=t["frame"], linewidth=3, linestyle="--", zorder=Z["boundaries"])
        items = []
        for _, r_ in pr.iterrows():
            nm = clean_label(r_.get("name:en") if isinstance(r_.get("name:en"), str) else r_.get("name"), drop=())
            if nm:
                pt = r_.geometry.representative_point()
                items.append((nm, pt.x, pt.y, r_.geometry.area))
        _, skipped = place_labels(ax, items, sizes=(62, 48, 36, 26), fontweight="bold", color=t["text"],
                                  alpha=0.85, zorder=Z["labels"])
        if skipped:
            log(f"[{tag}] left out (no room): {', '.join(skipped)}")
    if not rivers.empty:
        rivers[rivers.geom_type.isin(["LineString", "MultiLineString"])].plot(
            ax=ax, color=t["water"], linewidth=2.5, zorder=Z["water"] + 0.2)
    for i, (cls, wd) in enumerate((("trunk", 2.5), ("motorway", 4))):
        seg = edges[edges["cls"] == cls] if not edges.empty else edges
        if not seg.empty:
            seg.plot(ax=ax, color=t["road"], linewidth=wd, zorder=Z["roads"] + i * 0.1)
    bp.boundary.plot(ax=ax, color=t["frame"], linewidth=10, zorder=Z["boundaries"] + 0.5)

    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    user_handles = draw_layers(ax, user_layers, t, zorder=Z["your_data"], label_zorder=Z["labels"] + 0.3)
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    apply_layout(fig, ax, ext, t, size, utm, lay, user_handles=user_handles, title=country.upper(), subtitle="PROVINCES, MOTORWAYS & RIVERS",
                 credit="Map data \u00a9 OpenStreetMap contributors  |  Boundaries as mapped in OpenStreetMap; "
                        "verify against official sources (Survey of Pakistan) for official use",
                 y_title=0.955, y_sub=0.915, y_credit=0.02, fs_title=150, fs_sub=44, fs_credit=24)
    log(f"[{tag}] saving...")
    return save_outputs(fig, ax, out, dpi, formats, utm, ext, t["bg"], tag, tiff_furniture=lay.tiff_furniture)
