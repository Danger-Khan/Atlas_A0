# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Map furniture: title block, legends, scale bar, north arrow, coordinate grid, text labels, note, logo, credit.

Pure drawing helpers on a matplotlib figure/axes (no network). Everything the user can switch on or off or
customise is described by one `Layout` object; the API/CLI/batch-JSON/GUI all build it from a plain dict:

    layout = {"elements": ["title", "legend", "scale", "north", "grid"],
              "title": "Peshawar - flood exposure", "subtitle": "Prepared for PCSIR",
              "legend_items": [["Proposed site", "#d62728"]], "legend_style": "horizontal",
              "legend_pos": "lower center", "legend_title": "Key",
              "north_style": "compass", "north_pos": "upper right", "north_size": 1.5,
              "scale_style": "double", "scale_units": "km", "scale_pos": "lower left",
              "labels": [{"text": "Hayatabad", "lon": 71.43, "lat": 33.98, "size": 50, "color": "#900"}],
              "note": "Draft - for discussion", "logo": "logo.png", "grid_km": 5}

Styles:  legend  box | compact | minimal | horizontal       north  arrow | classic | compass | circle
         scale   bar | line | double | ratio                 units  km | mi | m
"""
import math
import os
import textwrap
from dataclasses import dataclass, field

from matplotlib import colors as mcolors
from matplotlib.patches import Circle, Patch, Polygon, Rectangle

from .config import AXES_RECT
from .runtime import log

ELEMENTS = {
    "title": "title + subtitle block above the map",
    "legend": "legend of land-use colours, your layers and any custom legend items",
    "scale": "scale bar with the print scale, e.g. 1:25,000 at A0",
    "north": "north arrow",
    "grid": "coordinate grid with UTM labels (km) on the map edges",
    "credit": "data credit line at the bottom",
}
# ------------------------------------------------------------------ draw order (what is printed on top of what)
DRAW_GROUPS = {   # key: plain description; DEFAULT_DRAW_ORDER is bottom -> top
    "basemap": "Satellite / topo image",
    "landuse": "Land fill, parks, land use, province colours",
    "buildings": "Building footprints",
    "water": "Water areas, rivers, canals",
    "boundaries": "District / province boundary lines",
    "roads": "Roads and railways",
    "grid": "UTM grid lines",
    "mask": "Blank area outside a district + its outline",
    "your_data": "Your layers (shapefile, GeoJSON, CSV...)",
    "receptors": "Receptor / point-of-interest markers",
    "labels": "Names (districts, receptors, your text labels)",
}
DEFAULT_DRAW_ORDER = tuple(DRAW_GROUPS)
FURNITURE_Z = 30   # title, legend, scale, north arrow, note: always above the map content


def parse_draw_order(value):
    """List or comma text of group names, bottom -> top. Groups you leave out keep their default place
    (just above the default group below them). Returns the full list."""
    if value in (None, "", []):
        return list(DEFAULT_DRAW_ORDER)
    given = [v.strip().lower().replace(" ", "_").replace("-", "_") for v in
             (value.split(",") if isinstance(value, str) else value) if str(v).strip()]
    bad = [g for g in given if g not in DRAW_GROUPS]
    if bad:
        raise ValueError(f"unknown draw-order group(s): {', '.join(bad)}. Use: {', '.join(DRAW_GROUPS)}")
    if len(set(given)) != len(given):
        raise ValueError("a draw-order group is listed twice")
    order = list(given)
    for i, g in enumerate(DEFAULT_DRAW_ORDER):
        if g in order:
            continue
        below = [b for b in DEFAULT_DRAW_ORDER[:i] if b in order]
        order.insert(order.index(below[-1]) + 1 if below else 0, g)
    return order


def draw_zorders(order):
    """group -> matplotlib zorder base (1, 2, 3...; each group may use base .. base + 0.9)."""
    return {g: 1.0 + i for i, g in enumerate(parse_draw_order(order))}


DEFAULT_ELEMENTS = ("title", "legend", "scale", "north", "credit")

POSITIONS = ("upper left", "upper center", "upper right", "center left", "center right",
             "lower left", "lower center", "lower right")
CORNERS = ("upper left", "upper right", "lower left", "lower right")
LEGEND_POSITIONS = POSITIONS
LEGEND_STYLES = {"box": "framed list with a title", "compact": "smaller framed list",
                 "minimal": "no frame, just the entries", "horizontal": "entries in one row"}
NORTH_STYLES = {"arrow": "line arrow with N", "classic": "half-filled kite arrow", "compass": "4-point compass star",
                "circle": "arrow inside a circle"}
SCALE_STYLES = {"bar": "alternating segmented bar", "line": "simple line with ticks",
                "double": "two bars (km and miles)", "ratio": "text only, 1:N"}
SCALE_UNITS = {"km": 1000.0, "mi": 1609.344, "m": 1.0}
DEFAULT_POS = {"north": "upper left", "scale": "lower left", "legend": "lower right", "note": "lower center"}


def resolve_elements(spec):
    """None -> defaults; 'all' -> everything; 'none' -> nothing; otherwise a list of names (validated)."""
    if spec is None:
        return list(DEFAULT_ELEMENTS)
    names = [spec] if isinstance(spec, str) else list(spec)
    low = [n.lower() for n in names]
    if low == ["none"]:
        return []
    if low == ["all"]:
        return list(ELEMENTS)
    bad = [n for n in low if n not in ELEMENTS]
    if bad:
        raise ValueError(f"unknown map element(s): {', '.join(bad)}. Options: {', '.join(ELEMENTS)}, all, none")
    return list(dict.fromkeys(low))


def parse_legend_item(text):
    """'Proposed site=#d62728' -> ('Proposed site', '#d62728')."""
    label, sep, color = str(text).rpartition("=")
    color = color.strip()
    if not sep or not label.strip() or not mcolors.is_color_like(color):
        raise ValueError(f"legend item must look like 'Label=#rrggbb', got '{text}'")
    return label.strip(), color


def parse_label_spec(text):
    """'Hayatabad@71.43,33.98;size=50;color=#990000;bold=1' -> label dict."""
    parts = [p.strip() for p in str(text).split(";") if p.strip()]
    head, sep, coords = parts[0].rpartition("@")
    if not sep or not head.strip() or "," not in coords:
        raise ValueError(f"label must look like 'Text@lon,lat[;size=..;color=..]', got '{text}'")
    lon, lat = coords.split(",", 1)
    d = {"text": head.strip(), "lon": lon.strip(), "lat": lat.strip()}
    for p in parts[1:]:
        k, s, v = p.partition("=")
        if not s:
            raise ValueError(f"label option must look like key=value, got '{p}'")
        d[k.strip()] = v.strip()
    return normalise_label(d)


_LABEL_KEYS = {"text", "lon", "lat", "size", "color", "bold", "italic", "halo", "rotation", "box"}


def normalise_label(d):
    d = dict(d)
    bad = set(d) - _LABEL_KEYS
    if bad:
        raise ValueError(f"unknown label option(s): {', '.join(sorted(bad))}")
    if not str(d.get("text", "")).strip():
        raise ValueError("label needs text")
    try:
        lon, lat = float(d["lon"]), float(d["lat"])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"label '{d.get('text')}' needs numeric lon and lat")
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError(f"label '{d['text']}': lon/lat out of range")
    size = float(d.get("size") or 40)
    if size <= 0:
        raise ValueError("label size must be > 0")
    color = d.get("color") or ""
    if color and not mcolors.is_color_like(color):
        raise ValueError(f"label '{d['text']}': '{color}' is not a colour")
    b = lambda v, default: default if v in (None, "") else (v if isinstance(v, bool) else
                                                             str(v).strip().lower() in ("1", "true", "yes", "on"))
    return {"text": str(d["text"]).strip(), "lon": lon, "lat": lat, "size": size, "color": color,
            "bold": b(d.get("bold"), False), "italic": b(d.get("italic"), False), "halo": b(d.get("halo"), True),
            "box": b(d.get("box"), False), "rotation": float(d.get("rotation") or 0)}


def _choice(d, key, options, default):
    v = (d.get(key) or default)
    v = v.lower() if isinstance(v, str) else v
    if v not in options:
        raise ValueError(f"{key} must be one of: {', '.join(options)}")
    return v


@dataclass
class Layout:
    elements: list = field(default_factory=lambda: list(DEFAULT_ELEMENTS))
    title: str = None
    subtitle: str = None
    legend_items: list = field(default_factory=list)   # [(label, colour)]
    legend_pos: str = "lower right"
    legend_style: str = "box"
    legend_title: str = "LEGEND"
    legend_cols: int = 1
    north_style: str = "arrow"
    north_pos: str = "upper left"
    north_size: float = 1.0
    scale_style: str = "bar"
    scale_units: str = "km"
    scale_pos: str = "lower left"
    scale_divisions: int = 4
    labels: list = field(default_factory=list)         # free text labels at lon/lat
    note: str = None
    note_pos: str = "lower center"
    logo: str = None
    grid_km: float = None
    tiff_furniture: bool = False   # False: keep legends/scale/north/grid OUT of the georeferenced TIFF
    draw_order: list = field(default_factory=lambda: list(DEFAULT_DRAW_ORDER))   # bottom -> top

    def z(self, group):
        """zorder base of a map-content group (see DRAW_GROUPS)."""
        return draw_zorders(self.draw_order)[group]

    @classmethod
    def from_any(cls, spec):
        """Accepts None, a Layout or a dict (as in batch JSON); validates everything."""
        if isinstance(spec, cls):
            return spec
        d = dict(spec or {})
        known = {"elements", "title", "subtitle", "legend_items", "legend_pos", "legend_style", "legend_title",
                 "legend_cols", "north_style", "north_pos", "north_size", "scale_style", "scale_units", "scale_pos",
                 "scale_divisions", "labels", "note", "note_pos", "logo", "grid_km", "tiff_furniture", "draw_order"}
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"unknown layout option(s): {', '.join(sorted(unknown))}")
        items = [parse_legend_item(i) if isinstance(i, str) else (str(i[0]), str(i[1]))
                 for i in d.get("legend_items") or []]
        for _, c in items:
            if not mcolors.is_color_like(c):
                raise ValueError(f"legend colour '{c}' is not a colour")
        if d.get("logo") and not os.path.isfile(d["logo"]):
            raise ValueError(f"logo file not found: {d['logo']}")
        gk = d.get("grid_km")
        if gk is not None and float(gk) <= 0:
            raise ValueError("grid_km must be > 0")
        dflt = lambda k, v: v if d.get(k) is None else d[k]
        cols, div, nsize = int(dflt("legend_cols", 1)), int(dflt("scale_divisions", 4)), float(dflt("north_size", 1.0))
        if cols < 1 or not 1 <= div <= 10 or not 0.3 <= nsize <= 4:
            raise ValueError("legend_cols must be >= 1, scale_divisions 1-10, north_size 0.3-4")
        lay = cls(
            elements=resolve_elements(d.get("elements")), title=d.get("title"), subtitle=d.get("subtitle"),
            legend_items=items, legend_pos=_choice(d, "legend_pos", POSITIONS, DEFAULT_POS["legend"]),
            legend_style=_choice(d, "legend_style", LEGEND_STYLES, "box"), legend_title=d.get("legend_title")
            if d.get("legend_title") is not None else "LEGEND", legend_cols=cols,
            north_style=_choice(d, "north_style", NORTH_STYLES, "arrow"),
            north_pos=_choice(d, "north_pos", CORNERS, DEFAULT_POS["north"]), north_size=nsize,
            scale_style=_choice(d, "scale_style", SCALE_STYLES, "bar"),
            scale_units=_choice(d, "scale_units", SCALE_UNITS, "km"),
            scale_pos=_choice(d, "scale_pos", CORNERS, DEFAULT_POS["scale"]), scale_divisions=div,
            labels=[normalise_label(x) if not isinstance(x, str) else parse_label_spec(x) for x in d.get("labels") or []],
            note=d.get("note"), note_pos=_choice(d, "note_pos", ("lower center", "upper center"), "lower center"),
            logo=d.get("logo"), grid_km=float(gk) if gk is not None else None,
            tiff_furniture=bool(d.get("tiff_furniture", False)),
            draw_order=parse_draw_order(d.get("draw_order")))
        lay.check_positions()
        return lay

    def has(self, name):
        return name in self.elements

    def used_positions(self):
        used = {}
        if self.has("north"):
            used["north arrow"] = self.north_pos
        if self.has("scale"):
            used["scale"] = self.scale_pos
        if self.has("legend"):
            used["legend"] = self.legend_pos
        if self.note:
            used["note"] = self.note_pos
        return used

    def check_positions(self):
        seen = {}
        for name, pos in self.used_positions().items():
            if pos in seen:
                raise ValueError(f"{seen[pos]} and {name} are both at '{pos}'; choose different positions")
            seen[pos] = name


def free_slot(used, order=("upper right", "center right", "upper left", "center left", "lower right",
                           "lower left", "upper center")):
    """First free place for the receptor legend."""
    return next((p for p in order if p not in used), "upper right")


# --------------------------------------------------------------------------- numbers
def nice_scale_km(span):
    """Scale-bar length (1, 2 or 5 x 10^n) of about a quarter of `span` (any unit), never longer."""
    target = span / 4
    mag = 10 ** math.floor(math.log10(target))
    for m in (5, 2, 1):
        if m * mag <= target:
            return m * mag
    return mag


def print_scale_ratio(width_m, sheet_w_in):
    """1:N when the map (width_m of ground across the drawing area) is printed at 100% on this sheet.
    Rounded to 2 significant figures."""
    sheet_m = AXES_RECT[2] * sheet_w_in * 0.0254
    n = width_m / sheet_m
    mag = 10 ** (math.floor(math.log10(n)) - 1)
    return int(round(n / mag) * mag)


def nice_grid_step_km(span_km, target_lines=6):
    raw = span_km / target_lines
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if m * mag >= raw:
            return m * mag
    return 10 * mag


def corner_origin(ext, pos, bw, bh, margin=0.03):
    """Lower-left (x, y) of a bw x bh block placed in a corner of the map extent."""
    w, h = ext[1] - ext[0], ext[3] - ext[2]
    x = ext[0] + w * margin if "left" in pos else ext[1] - w * margin - bw
    y = ext[2] + h * margin if "lower" in pos else ext[3] - h * margin - bh
    return x, y


def project_lonlat(utm, lon, lat):
    """lon/lat (WGS84) -> map CRS metres. Needs pyproj (installed with geopandas)."""
    from pyproj import Transformer
    return Transformer.from_crs(4326, utm, always_xy=True).transform(lon, lat)


def _register(fig, artists):
    """Remember furniture artists so the TIFF can be saved without them."""
    lst = getattr(fig, "_atlasa0_furniture", None)
    if lst is None:
        lst = fig._atlasa0_furniture = []
    for a in (artists if isinstance(artists, (list, tuple)) else [artists]):
        if a is not None:
            lst.append(a)


# --------------------------------------------------------------------------- scale
def _segmented_bar(ax, art, t, x0, y, length, bh, divisions, zorder=None):
    zorder = FURNITURE_Z if zorder is None else zorder
    seg = length / divisions
    for i in range(divisions):
        art.append(ax.add_patch(Rectangle((x0 + i * seg, y), seg, bh, facecolor=t["frame"] if i % 2 == 0 else t["bg"],
                                          edgecolor=t["frame"], linewidth=3, zorder=zorder)))


def _tick_labels(ax, art, t, x0, y, length, divisions, bar_u, unit, fs=36):
    n = divisions if divisions <= 5 else 2
    for k in range(n + 1):
        frac = k / n
        txt = "0" if k == 0 else (f"{bar_u * frac:g} {unit}" if k == n else f"{bar_u * frac:g}")
        art.append(ax.text(x0 + frac * length, y, txt, ha="center", va="bottom", fontsize=fs, fontweight="bold",
                           color=t["text"], zorder=FURNITURE_Z))


def draw_scale(fig, ax, ext, t, size, style="bar", units="km", pos="lower left", divisions=4):
    """Scale bar in a corner. styles: bar, line, double (km + miles), ratio (text only). Returns (bar_units, ratio)."""
    w, h = ext[1] - ext[0], ext[3] - ext[2]
    unit_m = SCALE_UNITS[units]
    bar_u = nice_scale_km(w / unit_m)
    bar_m = bar_u * unit_m
    ratio = print_scale_ratio(w, size[0])
    ratio_txt = f"Scale 1:{ratio:,} when printed at A0"
    other = "mi" if units != "mi" else "km"
    bar2_u = nice_scale_km(w / SCALE_UNITS[other]) if style == "double" else None
    bar2_m = bar2_u * SCALE_UNITS[other] if style == "double" else 0
    block_w = max(bar_m, bar2_m) + w * 0.05
    block_h = {"bar": 0.056, "line": 0.052, "double": 0.092, "ratio": 0.028}[style] * h
    x0, yb = corner_origin(ext, pos, block_w, block_h)
    art = [ax.add_patch(Rectangle((x0, yb), block_w, block_h, facecolor=t["bg"], edgecolor="none", alpha=0.75,
                                  zorder=FURNITURE_Z - 1))]
    bx = x0 + w * 0.02
    if style == "ratio":
        art.append(ax.text(bx, yb + block_h / 2, ratio_txt, ha="left", va="center", fontsize=38, fontweight="bold",
                           color=t["text"], zorder=FURNITURE_Z))
        _register(fig, art)
        return bar_u, ratio
    art.append(ax.text(bx, yb + h * 0.004, ratio_txt, ha="left", va="bottom", fontsize=26, color=t["text"], zorder=FURNITURE_Z))
    y1 = yb + h * 0.018
    bh = h * 0.004
    if style == "line":
        art.append(ax.plot([bx, bx + bar_m], [y1 + bh / 2] * 2, color=t["frame"], lw=6, solid_capstyle="butt", zorder=FURNITURE_Z)[0])
        for k in range(divisions + 1):
            xk = bx + k * bar_m / divisions
            art.append(ax.plot([xk, xk], [y1 - bh, y1 + 2 * bh], color=t["frame"], lw=5, zorder=FURNITURE_Z)[0])
    else:
        _segmented_bar(ax, art, t, bx, y1, bar_m, bh, divisions)
    _tick_labels(ax, art, t, bx, y1 + bh + h * 0.003, bar_m, divisions, bar_u, units)
    if style == "double":
        y2 = y1 + h * 0.040
        _segmented_bar(ax, art, t, bx, y2, bar2_m, bh, divisions)
        _tick_labels(ax, art, t, bx, y2 + bh + h * 0.003, bar2_m, divisions, bar2_u, other)
    _register(fig, art)
    return bar_u, ratio


# --------------------------------------------------------------------------- north arrow
def draw_north(fig, ax, ext, t, style="arrow", pos="upper left", scale=1.0):
    """North arrow in a corner (grid north; UTM convergence is small at city scale)."""
    w, h = ext[1] - ext[0], ext[3] - ext[2]
    r = h * 0.032 * scale            # half-height of the symbol
    bw, bh = 2.6 * r, 3.6 * r        # block incl. the N letter
    x0, y0 = corner_origin(ext, pos, bw, bh)
    cx, base = x0 + bw / 2, y0 + 0.15 * r
    fs = 70 * scale
    fc, bg, tx = t["frame"], t["bg"], t["text"]
    art = [ax.add_patch(Rectangle((x0, y0), bw, bh, facecolor=bg, edgecolor="none", alpha=0.7, zorder=FURNITURE_Z - 1))]

    def poly(pts, face, edge=fc, lw=3):
        art.append(ax.add_patch(Polygon(pts, closed=True, facecolor=face, edgecolor=edge, linewidth=lw, zorder=FURNITURE_Z)))

    if style == "arrow":
        top = base + 2.3 * r
        art.append(ax.plot([cx, cx], [base, top - 0.8 * r], color=fc, lw=9 * scale, solid_capstyle="butt", zorder=FURNITURE_Z)[0])
        poly([(cx, top), (cx - 0.55 * r, top - 1.0 * r), (cx + 0.55 * r, top - 1.0 * r)], fc)
        ny = top + 0.2 * r
    elif style == "classic":
        top, bot, mid = base + 2.3 * r, base, base + 0.7 * r
        poly([(cx, top), (cx, mid), (cx - 0.7 * r, bot)], fc)        # left half filled
        poly([(cx, top), (cx, mid), (cx + 0.7 * r, bot)], bg)        # right half open
        ny = top + 0.2 * r
    elif style == "compass":
        cy, a, b = base + 1.2 * r, 1.2 * r, 0.32 * r
        poly([(cx, cy + a), (cx - b, cy), (cx + b, cy)], fc)                       # N filled
        poly([(cx, cy - a), (cx - b, cy), (cx + b, cy)], bg)                       # S open
        poly([(cx + a, cy), (cx, cy + b), (cx, cy - b)], bg)                       # E open
        poly([(cx - a, cy), (cx, cy + b), (cx, cy - b)], bg)                       # W open
        for lbl, dx, dy in (("E", a + 0.35 * r, 0), ("W", -a - 0.35 * r, 0), ("S", 0, -a - 0.45 * r)):
            art.append(ax.text(cx + dx, cy + dy, lbl, ha="center", va="center", fontsize=fs * 0.4, color=tx, zorder=FURNITURE_Z))
        ny = cy + a + 0.15 * r
    else:  # circle
        cy = base + 1.2 * r
        art.append(ax.add_patch(Circle((cx, cy), 1.15 * r, facecolor=bg, edgecolor=fc, linewidth=5, zorder=FURNITURE_Z)))
        poly([(cx, cy + 0.95 * r), (cx - 0.4 * r, cy - 0.6 * r), (cx, cy - 0.25 * r), (cx + 0.4 * r, cy - 0.6 * r)], fc)
        ny = cy + 1.15 * r + 0.15 * r
    art.append(ax.text(cx, ny, "N", ha="center", va="bottom", fontsize=fs, fontweight="bold", color=tx, zorder=FURNITURE_Z))
    _register(fig, art)


# --------------------------------------------------------------------------- grid
def draw_grid(fig, ax, ext, t, utm, grid_km=None, zorder=7.0):
    """UTM grid lines every grid_km (auto if None) with km labels on the left and bottom edges."""
    step = (grid_km or nice_grid_step_km((ext[1] - ext[0]) / 1000)) * 1000
    xs = [math.ceil(ext[0] / step) * step + i * step for i in range(int((ext[1] - ext[0]) // step) + 1)]
    ys = [math.ceil(ext[2] / step) * step + i * step for i in range(int((ext[3] - ext[2]) // step) + 1)]
    xs = [x for x in xs if ext[0] < x < ext[1]]
    ys = [y for y in ys if ext[2] < y < ext[3]]
    art = []
    for x in xs:
        art.append(ax.axvline(x, color=t["text"], lw=1.5, alpha=0.35, zorder=zorder))
    for y in ys:
        art.append(ax.axhline(y, color=t["text"], lw=1.5, alpha=0.35, zorder=zorder))
    _register(fig, art)
    ax.set_xticks(xs)
    ax.set_yticks(ys)
    km = lambda v: f"{v / 1000:g}"
    ax.set_xticklabels([km(x) for x in xs])
    ax.set_yticklabels([km(y) for y in ys], rotation=90, va="center")
    ax.tick_params(labelsize=30, colors=t["text"], length=14, width=3)
    return step / 1000


# --------------------------------------------------------------------------- legends
_LEGEND_LOOK = {   # fontsize, title size, framed
    "box": (34, 36, True), "compact": (26, 28, True), "minimal": (32, 34, False), "horizontal": (30, 32, True)}


def _make_legend(ax, t, handles, title, pos, style, cols):
    fs, tfs, framed = _LEGEND_LOOK[style]
    ncol = len(handles) if style == "horizontal" else max(1, cols)
    kw = dict(handles=handles, loc=pos, fontsize=fs, title=title or None, title_fontsize=tfs, ncol=ncol,
              frameon=framed, labelcolor=t["text"])
    if framed:
        kw.update(facecolor=t["bg"], edgecolor=t["frame"], framealpha=0.9)
    lg = ax.legend(**kw)
    if title:
        lg.get_title().set_color(t["text"])
        lg.get_title().set_fontweight("bold")
    lg.set_zorder(FURNITURE_Z)
    return lg


def draw_legends(fig, ax, t, land_entries, poi_handles, custom_items, pos="lower right", style="box",
                 title="LEGEND", cols=1, user_handles=(), poi_pos="upper right"):
    """Main legend (land use + your layers + custom items) at `pos`; receptor legend at `poi_pos`."""
    handles = [Patch(facecolor=c, label=k.replace("_", " ").title()) for k, c in land_entries]
    handles += list(user_handles)
    handles += [Patch(facecolor=c, edgecolor=t["frame"], label=lbl) for lbl, c in custom_items]
    art = []
    if handles:
        lg = _make_legend(ax, t, handles, title, pos, style, cols)
        ax.add_artist(lg)  # keep it when the POI legend is added
        art.append(lg)
    if poi_handles:
        art.append(_make_legend(ax, t, poi_handles, "POINTS OF INTEREST", poi_pos,
                                "box" if style == "horizontal" else style, 1))
    _register(fig, art)


# --------------------------------------------------------------------------- labels, note, logo, title
def draw_labels(fig, ax, ext, t, utm, labels, projector=None, zorder=11.5):
    """Free text labels at lon/lat. Labels outside the map are skipped with a message."""
    from matplotlib import patheffects
    proj = projector or project_lonlat
    art = []
    for lb in labels:
        x, y = proj(utm, lb["lon"], lb["lat"])
        if not (ext[0] <= x <= ext[1] and ext[2] <= y <= ext[3]):
            log(f"[labels] '{lb['text']}' is outside the map - skipped")
            continue
        kw = {}
        if lb["box"]:
            kw["bbox"] = dict(facecolor=t["bg"], edgecolor=t["frame"], alpha=0.85, pad=8)
        elif lb["halo"]:
            kw["path_effects"] = [patheffects.withStroke(linewidth=8, foreground=t["bg"])]
        art.append(ax.text(x, y, lb["text"], ha="center", va="center", fontsize=lb["size"], color=lb["color"] or t["text"],
                           fontweight="bold" if lb["bold"] else "normal", fontstyle="italic" if lb["italic"] else "normal",
                           rotation=lb["rotation"], zorder=zorder, **kw))
    _register(fig, art)


def draw_note(fig, ax, t, text, pos="lower center"):
    y, va = (0.02, "bottom") if pos.startswith("lower") else (0.98, "top")
    tx = ax.text(0.5, y, "\n".join(textwrap.wrap(text, 70)), transform=ax.transAxes, ha="center", va=va,
                 fontsize=34, color=t["text"], zorder=FURNITURE_Z,
                 bbox=dict(facecolor=t["bg"], edgecolor=t["frame"], alpha=0.9, pad=14))
    _register(fig, tx)


def draw_logo(fig, path, size):
    """Logo in the top-left corner of the sheet (in the title margin), height about 6% of the sheet."""
    from PIL import Image
    img = Image.open(path).convert("RGBA")
    h_frac = 0.055
    w_frac = h_frac * (img.width / img.height) * (size[1] / size[0])
    lax = fig.add_axes([0.04, 0.99 - h_frac - 0.005, min(w_frac, 0.25), h_frac])
    lax.imshow(img)
    lax.axis("off")


def draw_title(fig, title, subtitle, t, y_title, y_sub, fs_title, fs_sub):
    fig.text(0.5, y_title, title, ha="center", va="center", fontsize=fs_title, fontweight="bold", color=t["text"])
    fig.text(0.5, y_sub, subtitle, ha="center", va="center", fontsize=fs_sub, color=t["text"])


def draw_credit(fig, text, t, y=0.02, fs=26):
    fig.text(0.5, y, text, ha="center", va="center", fontsize=fs, color=t["text"])


def apply_layout(fig, ax, ext, t, size, utm, lay, *, title, subtitle, credit, y_title, y_sub, y_credit,
                 fs_title=130, fs_sub=40, fs_credit=26, land_entries=(), poi_handles=(), user_handles=(),
                 projector=None):
    """Draw every enabled element. `title`/`subtitle`/`credit` are the defaults of the map; the layout overrides."""
    if lay.has("grid"):
        step = draw_grid(fig, ax, ext, t, utm, lay.grid_km, zorder=lay.z("grid"))
        zone = getattr(utm, "name", "UTM")
        credit = f"{credit}  |  Grid: {zone}, every {step:g} km (labels in km)"
    if lay.has("scale"):
        draw_scale(fig, ax, ext, t, size, lay.scale_style, lay.scale_units, lay.scale_pos, lay.scale_divisions)
    if lay.has("north"):
        draw_north(fig, ax, ext, t, lay.north_style, lay.north_pos, lay.north_size)
    if lay.has("legend") or poi_handles:
        poi_pos = free_slot(set(lay.used_positions().values()))
        draw_legends(fig, ax, t, list(land_entries) if lay.has("legend") else [], poi_handles,
                     lay.legend_items if lay.has("legend") else [], lay.legend_pos, lay.legend_style,
                     lay.legend_title, lay.legend_cols, user_handles if lay.has("legend") else (), poi_pos)
    if lay.labels:
        draw_labels(fig, ax, ext, t, utm, lay.labels, projector, zorder=lay.z("labels") + 0.5)
    if lay.note:
        draw_note(fig, ax, t, lay.note, lay.note_pos)
    if lay.logo:
        draw_logo(fig, lay.logo, size)
    if lay.has("title"):
        draw_title(fig, lay.title or title, lay.subtitle if lay.subtitle is not None else subtitle, t,
                   y_title, y_sub, fs_title, fs_sub)
    if lay.has("credit"):
        draw_credit(fig, credit, t, y_credit - (0.009 if lay.has("grid") else 0), fs_credit)
