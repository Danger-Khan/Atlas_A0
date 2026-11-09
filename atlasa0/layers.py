# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Your own data on the map: points, lines and polygons from shapefiles / GeoJSON / GeoPackage / KML / CSV.

Each layer has its own colour, transparency, marker / line / fill style, optional labels and a legend entry.

    layers=[{"path": "sites.shp", "name": "Proposed sites", "color": "#d62728", "alpha": 0.8,
             "marker": "triangle", "size_mm": 8, "label_field": "NAME"},
            {"path": "canal.geojson", "color": "#1f77b4", "line_style": "dashed", "width_mm": 1.2},
            {"path": "zones.shp", "color": "#2ca02c", "alpha": 0.35, "hatch": "diagonal"}]

CLI spec string:  "sites.shp;name=Proposed sites;color=#d62728;alpha=0.8;marker=triangle;size_mm=8"

Structure: spec parsing / validation and drawing are plain Python + matplotlib (testable anywhere); only
load_layer() needs geopandas (it reads the file and reprojects to the map's UTM zone).
"""
import os
from dataclasses import dataclass, field, fields

import numpy as np
from matplotlib import colors as mcolors
from matplotlib import patheffects
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.lines import Line2D
from matplotlib.patches import PathPatch, Patch
from matplotlib.path import Path

from .runtime import log

# name -> (matplotlib marker, hollow?)
MARKERS = {
    "circle": ("o", False), "square": ("s", False), "triangle": ("^", False), "triangle down": ("v", False),
    "diamond": ("D", False), "star": ("*", False), "plus": ("P", False), "cross": ("X", False),
    "pentagon": ("p", False), "hexagon": ("h", False), "ring": ("o", True), "hollow square": ("s", True),
    "hollow triangle": ("^", True), "dot": (".", False),
}
LINE_STYLES = {"solid": "-", "dashed": "--", "dotted": ":", "dash-dot": "-."}
HATCHES = {"none": None, "diagonal": "///", "reverse diagonal": "\\\\\\", "cross-hatch": "xxx", "dots": "...",
           "grid": "+++", "horizontal": "---", "vertical": "|||"}
from .rasters import RASTER_TYPES, check_options, draw_raster, is_raster

FILE_TYPES = (".shp", ".geojson", ".json", ".gpkg", ".kml", ".gml", ".csv") + RASTER_TYPES
LON_NAMES = ("lon", "lng", "long", "longitude", "x", "easting")
LAT_NAMES = ("lat", "latitude", "y", "northing")
MM = 72 / 25.4  # points per millimetre


@dataclass
class LayerSpec:
    path: str
    name: str = ""                 # legend text (default: file name)
    color: str = "#d62728"         # fill / point / line colour
    alpha: float = None            # fill transparency 0 (invisible) .. 1 (solid); default by type
    edge_color: str = None         # outline colour (default: white for points, same as colour otherwise)
    edge_alpha: float = 1.0
    marker: str = "circle"
    size_mm: float = 6.0           # point diameter on the A0 sheet
    edge_width_mm: float = 0.35
    line_style: str = "solid"
    width_mm: float = 0.8          # line width on the sheet
    hatch: str = "none"
    label_field: str = ""          # attribute shown as label
    label_size: float = 24.0       # points
    label_color: str = ""          # default: theme text colour
    label_halo: bool = True
    legend: bool = True
    crs: str = "EPSG:4326"         # used when the file has no CRS (CSV and some KML/GeoJSON)
    x_col: str = ""                # CSV longitude/easting column (auto-detected)
    y_col: str = ""
    fit: bool = False              # include this layer when choosing the map extent
    # raster layers (GeoTIFF) only - see rasters.py; `alpha` is the opacity
    cmap: str = ""                 # colour map for a single band (default viridis)
    vmin: float = None             # value shown as the first colour (default: 2nd percentile)
    vmax: float = None             # value shown as the last colour (default: 98th percentile)
    band: int = 1
    placement: str = "overlay"     # "overlay" (Your layers step) or "basemap" (under land use / roads)
    resample: str = "bilinear"     # nearest (classes, land cover) | bilinear | cubic

    def __post_init__(self):
        if not self.edge_color:
            self.edge_color = None   # blank = automatic
        self.validate()

    def validate(self):
        if not self.path:
            raise ValueError("layer needs a file path")
        ext = os.path.splitext(self.path)[1].lower()
        if ext not in FILE_TYPES:
            raise ValueError(f"layer '{self.path}': unsupported file type '{ext}'. Use: {', '.join(FILE_TYPES)}")
        if not os.path.isfile(self.path):
            raise ValueError(f"layer file not found: {self.path}")
        for f in ("color", "edge_color", "label_color"):
            v = getattr(self, f)
            if v and not mcolors.is_color_like(v):
                raise ValueError(f"layer '{self.path}': {f} '{v}' is not a colour (use e.g. #d62728)")
        for f in ("alpha", "edge_alpha"):
            v = getattr(self, f)
            if v is not None and not 0 <= float(v) <= 1:
                raise ValueError(f"layer '{self.path}': {f} must be between 0 and 1")
        if self.marker not in MARKERS:
            raise ValueError(f"layer '{self.path}': marker must be one of: {', '.join(MARKERS)}")
        if self.line_style not in LINE_STYLES:
            raise ValueError(f"layer '{self.path}': line_style must be one of: {', '.join(LINE_STYLES)}")
        if self.hatch not in HATCHES:
            raise ValueError(f"layer '{self.path}': hatch must be one of: {', '.join(HATCHES)}")
        for f in ("size_mm", "width_mm", "label_size"):
            if float(getattr(self, f)) <= 0:
                raise ValueError(f"layer '{self.path}': {f} must be > 0")
        if float(self.edge_width_mm) < 0:
            raise ValueError(f"layer '{self.path}': edge_width_mm must be >= 0")
        check_options(self)

    @property
    def label(self):
        return self.name or os.path.splitext(os.path.basename(self.path))[0]

    @classmethod
    def from_any(cls, spec):
        if isinstance(spec, cls):
            return spec
        if isinstance(spec, str):
            return parse_layer_spec(spec)
        d = dict(spec)
        known = {f.name for f in fields(cls)}
        bad = set(d) - known
        if bad:
            raise ValueError(f"unknown layer option(s): {', '.join(sorted(bad))}")
        for k in ("alpha", "edge_alpha", "size_mm", "edge_width_mm", "width_mm", "label_size", "vmin", "vmax"):
            if d.get(k) in ("", None):
                d.pop(k, None)
            elif k in d:
                d[k] = float(d[k])
        for k in ("label_halo", "legend", "fit"):
            if k in d:
                d[k] = _bool(d[k])
        if "band" in d:
            d["band"] = int(d["band"]) if str(d["band"]).strip() else 1
        return cls(**d)


def _bool(v):
    return v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def parse_layer_spec(text):
    """'file.shp;color=#d62728;alpha=0.5;marker=star' -> LayerSpec (first item is the path)."""
    parts = [p.strip() for p in str(text).split(";") if p.strip()]
    if not parts:
        raise ValueError("empty layer specification")
    d = {"path": parts[0]}
    for p in parts[1:]:
        k, sep, v = p.partition("=")
        if not sep:
            raise ValueError(f"layer option must look like key=value, got '{p}'")
        d[k.strip().replace("-", "_")] = v.strip()
    return LayerSpec.from_any(d)


def parse_layers(specs):
    return [LayerSpec.from_any(s) for s in (specs or [])]


def layers_to_dicts(specs):
    """Plain dicts (JSON-friendly) with only the non-default values."""
    out = []
    base = {f.name: f.default for f in fields(LayerSpec) if f.name != "path"}
    for s in parse_layers(specs):
        d = {"path": s.path}
        d.update({k: getattr(s, k) for k in base if getattr(s, k) != base[k]})
        out.append(d)
    return out


# ------------------------------------------------------------------------------------------ prepared data
@dataclass
class Feature:
    kind: str                # "point" | "line" | "polygon"
    parts: list              # point: [(x, y)]; line: [Nx2 array]; polygon: [(exterior Nx2, [hole Nx2...])]
    label_xy: tuple = None
    label: str = ""


@dataclass
class Prepared:
    spec: LayerSpec
    features: list = field(default_factory=list)
    raster: bool = False           # GeoTIFF layer: read and drawn at draw time, for the final map extent
    utm: object = None             # map CRS (raster layers)
    rbounds: tuple = None          # raster bounds in UTM (only kept when spec.fit)

    @property
    def count(self):
        return 1 if self.raster else len(self.features)

    def kinds(self):
        if self.raster:
            return {"raster": 1}
        out = {}
        for f in self.features:
            out[f.kind] = out.get(f.kind, 0) + 1
        return out

    @property
    def bounds(self):
        if self.raster:
            return self.rbounds
        xs, ys = [], []
        for f in self.features:
            for a in _all_arrays(f):
                xs += [a[:, 0].min(), a[:, 0].max()]
                ys += [a[:, 1].min(), a[:, 1].max()]
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def _all_arrays(f):
    if f.kind == "point":
        return [np.array([p]) for p in f.parts]
    if f.kind == "line":
        return list(f.parts)
    return [e for e, _ in f.parts]


def _ring_centroid(a):
    x, y = a[:, 0], a[:, 1]
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cr = x * y1 - x1 * y
    area = cr.sum() / 2
    if abs(area) < 1e-9:
        return float(x.mean()), float(y.mean())
    return float(((x + x1) * cr).sum() / (6 * area)), float(((y + y1) * cr).sum() / (6 * area))


def flatten(geom, label=""):
    """Duck-typed shapely geometry -> list of Feature (multi-part geometries are split)."""
    gt = geom.geom_type
    if gt in ("Point",):
        c = geom.coords[0]
        return [Feature("point", [(float(c[0]), float(c[1]))], (float(c[0]), float(c[1])), label)]
    if gt in ("LineString", "LinearRing"):
        a = np.asarray([(c[0], c[1]) for c in geom.coords], float)
        mid = a[len(a) // 2]
        return [Feature("line", [a], (float(mid[0]), float(mid[1])), label)]
    if gt == "Polygon":
        ext = np.asarray([(c[0], c[1]) for c in geom.exterior.coords], float)
        holes = [np.asarray([(c[0], c[1]) for c in r.coords], float) for r in geom.interiors]
        return [Feature("polygon", [(ext, holes)], _ring_centroid(ext), label)]
    if gt.startswith("Multi") or gt == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out += flatten(g, label)
        return out
    return []


def prepare_features(geoms, labels, spec):
    feats = []
    for g, lab in zip(geoms, labels):
        if g is None or getattr(g, "is_empty", False):
            continue
        feats += flatten(g, "" if lab is None else str(lab))
    return Prepared(spec, feats)


def load_layer(spec, utm):
    """Read the file, reproject to the map's UTM zone and return Prepared. Needs geopandas (not at import time)."""
    ext = os.path.splitext(spec.path)[1].lower()
    if is_raster(spec.path):
        from .rasters import bounds_utm
        rb = bounds_utm(spec.path, utm)          # also checks rasterio and the CRS now, before any download
        log(f"[layers] {spec.label}: raster layer ({spec.placement})")
        return Prepared(spec, [], raster=True, utm=utm, rbounds=rb if spec.fit else None)
    import geopandas as gpd
    import pandas as pd

    if ext == ".csv":
        df = pd.read_csv(spec.path, encoding="utf-8-sig")
        low = {c.lower().strip(): c for c in df.columns}
        xc = spec.x_col or next((low[n] for n in LON_NAMES if n in low), None)
        yc = spec.y_col or next((low[n] for n in LAT_NAMES if n in low), None)
        if not xc or not yc:
            raise ValueError(f"{spec.path}: could not find longitude/latitude columns "
                             f"(looked for {', '.join(LON_NAMES)} / {', '.join(LAT_NAMES)}); set x_col and y_col")
        df = df.dropna(subset=[xc, yc])
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[xc], df[yc]), crs=spec.crs)
    else:
        gdf = gpd.read_file(spec.path)
        if gdf.crs is None:
            gdf = gdf.set_crs(spec.crs)
    if spec.label_field and spec.label_field not in gdf.columns:
        raise ValueError(f"{spec.path}: no attribute '{spec.label_field}' (available: "
                         f"{', '.join(c for c in gdf.columns if c != 'geometry')})")
    gdf = gdf.to_crs(utm)
    labels = list(gdf[spec.label_field]) if spec.label_field else [""] * len(gdf)
    prep = prepare_features(list(gdf.geometry), labels, spec)
    log(f"[layers] {spec.label}: {prep.count} feature(s) {prep.kinds()}")
    return prep


def load_layers(specs, utm):
    return [load_layer(s, utm) for s in parse_layers(specs)]


def layers_bounds(prepared, fit_only=True):
    bs = [p.bounds for p in prepared if p.bounds and (p.spec.fit or not fit_only)]
    if not bs:
        return None
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


# ------------------------------------------------------------------------------------------ drawing
def _rgba(color, alpha):
    return mcolors.to_rgba(color, alpha)


def _signed_area(a):
    x, y = a[:, 0], a[:, 1]
    return float((x * np.roll(y, -1) - np.roll(x, -1) * y).sum() / 2)


def _oriented(ring, ccw):
    """Shapefiles, GeoJSON and shapely disagree on ring direction; matplotlib only cuts a hole when the hole
    runs the opposite way to the outline, so force: outline counter-clockwise, holes clockwise."""
    return ring if (_signed_area(ring) > 0) == ccw else ring[::-1]


def _poly_path(ext, holes):
    verts, codes = [], []
    for k, ring in enumerate([_oriented(ext, True)] + [_oriented(h, False) for h in holes]):
        n = len(ring)
        verts += [tuple(p) for p in ring]
        codes += [Path.MOVETO] + [Path.LINETO] * (n - 2) + [Path.CLOSEPOLY]
    return Path(verts, codes)


def effective_alpha(spec, kinds):
    if spec.alpha is not None:
        return float(spec.alpha)
    return 0.4 if kinds.get("polygon") and len(kinds) == 1 else 1.0


def draw_layer(ax, prep, theme, zorder=9.0, label_zorder=None, label_sink=None):
    """Draw one prepared layer; returns (legend handle or None)."""
    s = prep.spec
    if prep.raster:
        return draw_raster(ax, prep, zorder)
    kinds = prep.kinds()
    a = effective_alpha(s, kinds)
    edge_w = s.edge_width_mm * MM
    polys = [f for f in prep.features if f.kind == "polygon"]
    lines = [f for f in prep.features if f.kind == "line"]
    pts = [f for f in prep.features if f.kind == "point"]

    if polys:
        patches = [PathPatch(_poly_path(e, h)) for f in polys for (e, h) in f.parts]
        edge = s.edge_color or s.color
        pc = PatchCollection(patches, facecolor=_rgba(s.color, a), edgecolor=_rgba(edge, s.edge_alpha),
                             linewidth=edge_w if edge_w > 0 else 0, zorder=zorder)
        if HATCHES[s.hatch]:
            pc.set_hatch(HATCHES[s.hatch])
        ax.add_collection(pc)
    if lines:
        segs = [p for f in lines for p in f.parts]
        lc = LineCollection(segs, colors=[_rgba(s.color, a)], linewidths=s.width_mm * MM,
                            linestyles=LINE_STYLES[s.line_style], zorder=zorder + 0.1)
        ax.add_collection(lc)
    if pts:
        mk, hollow = MARKERS[s.marker]
        xs = [p[0] for f in pts for p in f.parts]
        ys = [p[1] for f in pts for p in f.parts]
        edge = s.edge_color or ("#ffffff" if not hollow else s.color)
        face = "none" if hollow else _rgba(s.color, a)
        ax.scatter(xs, ys, s=(s.size_mm * MM) ** 2, marker=mk, facecolors=face,
                   edgecolors=[_rgba(s.color if hollow else edge, s.edge_alpha)],
                   linewidths=max(edge_w, 1.5 if hollow else 0), zorder=zorder + 0.2)

    if s.label_field:
        col = s.label_color or theme["text"]
        fx = [patheffects.withStroke(linewidth=6, foreground=theme["bg"])] if s.label_halo else []
        dy = (s.size_mm * MM * 0.7 + 4) if pts and not polys and not lines else 0
        for f in prep.features:
            if f.label and f.label_xy and label_sink is not None:
                # placed later, once the axes limits are known, so labels can avoid each other (overview.place_point_labels)
                label_sink.append(dict(text=str(f.label), x=f.label_xy[0], y=f.label_xy[1], size=s.label_size, gap=dy,
                                       marker_r=(s.size_mm * MM * 0.5) if dy else 0, prio=1,
                                       kw=dict(color=col, zorder=zorder + 0.3 if label_zorder is None else label_zorder,
                                               path_effects=fx)))
            elif f.label and f.label_xy:
                ax.annotate(f.label, f.label_xy, xytext=(0, dy), textcoords="offset points", fontsize=s.label_size,
                            ha="center", va="bottom" if dy else "center", color=col, zorder=zorder + 0.3 if label_zorder is None else label_zorder,
                            path_effects=fx, clip_on=True)

    return legend_handle(prep, a) if s.legend and prep.count else None


def legend_handle(prep, alpha):
    s = prep.spec
    kinds = prep.kinds()
    main = max(kinds, key=kinds.get)
    if main == "polygon":
        return Patch(facecolor=_rgba(s.color, alpha), edgecolor=_rgba(s.edge_color or s.color, s.edge_alpha),
                     hatch=HATCHES[s.hatch], label=s.label)
    if main == "line":
        return Line2D([0], [0], color=_rgba(s.color, alpha), linewidth=max(s.width_mm * MM, 3),
                      linestyle=LINE_STYLES[s.line_style], label=s.label)
    mk, hollow = MARKERS[s.marker]
    return Line2D([0], [0], marker=mk, linestyle="", markersize=36,
                  markerfacecolor="none" if hollow else _rgba(s.color, alpha),
                  markeredgecolor=_rgba(s.color if hollow else (s.edge_color or "#ffffff"), s.edge_alpha),
                  markeredgewidth=2, label=s.label)


def draw_layers(ax, prepared, theme, zorder=9.0, label_zorder=None, label_sink=None, base_zorder=None):
    """Draw all layers in list order: the first is at the bottom, the last on top. They share the band
    zorder .. zorder + 0.9 (the "your_data" place in the draw order); their names go to label_zorder."""
    handles = []
    step = 0.85 / max(1, len(prepared))
    for i, prep in enumerate(prepared):
        z = zorder + i * step
        if prep.raster and prep.spec.placement == "basemap" and base_zorder is not None:
            z = base_zorder + i * 0.001            # under land use, water and roads
        h = draw_layer(ax, prep, theme, zorder=z,
                       label_zorder=None if label_zorder is None else label_zorder + i * 0.01, label_sink=label_sink)
        if h is not None:
            handles.append(h)
    return handles
