# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Toolkit-free logic behind the AtlasA0 GUI (form state -> validated jobs, estimates, presets).

The Tkinter panel (gui_tk.py) is a thin view over this module; a PyQt/PySide or web front end can use the
same functions, so behaviour is identical whatever the viewer is built with.
"""
import json
import os
import threading
from dataclasses import asdict, dataclass, field, fields

from .choropleth import SCHEMES as CHORO_SCHEMES, ChoroplethSpec
from .config import (file_stem, PAPER_NAMES, parse_paper, A0_INCHES, FORMAT_ALIASES, MAP_TYPES, POI_CATEGORIES, POI_PRESETS, PROVINCES, THEMES,
                     match_province, resolve_pois)
from matplotlib import colors as _mc

from .furniture import (DEFAULT_DRAW_ORDER, DRAW_GROUPS, parse_draw_order, CORNERS, DEFAULT_ELEMENTS, ELEMENTS, LEGEND_STYLES, NORTH_STYLES, POSITIONS, SCALE_STYLES,
                        SCALE_UNITS, Layout, normalise_label)
from . import estimates as est
from .layers import HATCHES, LINE_STYLES, MARKERS, layers_to_dicts, parse_layers

AUTHOR, EMAIL, NOTICE = "Imaad Ullah Khan Yameen", "yameenimaad@gmail.com", "This code is not for sale"
DPI_PRESETS = {"Preview (100 dpi, fast)": 100, "Draft (200 dpi)": 200, "Print (300 dpi)": 300,
               "High detail (400 dpi)": 400, "Maximum (500 dpi)": 500}
POI_FORMATS = ("csv", "geojson", "xlsx", "summary")


class FormError(ValueError):
    """Raised with a list of human-readable problems (one per line in the GUI)."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("\n".join(self.problems))


@dataclass
class FormState:
    # what to map
    country: bool = False
    provinces: list = field(default_factory=list)        # names / aliases, or ["all"]
    cities: list = field(default_factory=list)
    district_province: str = ""
    districts: list = field(default_factory=list)
    # how
    map_types: list = field(default_factory=lambda: ["street"])
    formats: list = field(default_factory=lambda: ["png"])
    dpi: int = 100
    paper: str = "A0"                     # "A0".."A4" or "WxH" in mm
    choropleth: dict = None               # {"file", "name_col", "value_col", "scheme", "classes", "palette", ...}
    theme: str = "light"
    landscape: object = "auto"            # "auto" | "portrait" | "landscape" (True/False still accepted)
    buildings: bool = False
    radius_km: float = None
    # receptors
    pois: list = field(default_factory=list)
    poi_labels: bool = False
    poi_data: bool = False
    poi_formats: list = field(default_factory=lambda: ["csv", "geojson"])
    # map elements
    elements: list = field(default_factory=lambda: list(DEFAULT_ELEMENTS))
    title: str = ""
    subtitle: str = ""
    legend_items: list = field(default_factory=list)     # "Label=#hex"
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
    labels: list = field(default_factory=list)           # free text labels: dicts with text, lon, lat, size...
    note_pos: str = "lower center"
    note: str = ""
    logo: str = ""
    grid_km: float = None
    tiff_furniture: bool = False
    draw_order: list = field(default_factory=lambda: list(DEFAULT_DRAW_ORDER))   # bottom -> top
    # your own data (shapefiles, GeoJSON, CSV points...): list of LayerSpec dicts
    layers: list = field(default_factory=list)
    # output
    outdir: str = field(default_factory=lambda: os.environ.get("ATLASA0_OUTDIR", "output"))
    skip_existing: bool = True
    # settings tab: file names and automatic behaviour
    name_mode: str = "auto"                  # "auto" = atlasa0 chooses | "custom" = your template
    name_template: str = "{region}_{type}"   # fields: region level type province dpi date
    auto_save: bool = True                   # remember the form automatically when a run starts
    open_folder: bool = False                # open the output folder when a run finishes

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})


def describe_options():
    """Everything a form needs to build its widgets (choices, defaults, help). JSON-serialisable."""
    return {
        "levels": ["country", "province", "district", "city"],
        "provinces": list(PROVINCES),
        "preset_cities": PROVINCES,
        "map_types": MAP_TYPES,
        "formats": ["png", "tiff"],
        "dpi_presets": DPI_PRESETS,
        "papers": list(PAPER_NAMES),
        "themes": list(THEMES),
        "poi_categories": {k: v["label"] for k, v in POI_CATEGORIES.items()},
        "poi_presets": POI_PRESETS,
        "poi_formats": list(POI_FORMATS),
        "elements": ELEMENTS,
        "default_elements": list(DEFAULT_ELEMENTS),
        "legend_positions": list(POSITIONS),
        "legend_styles": LEGEND_STYLES,
        "north_styles": NORTH_STYLES,
        "scale_styles": SCALE_STYLES,
        "scale_units": list(SCALE_UNITS),
        "corners": list(CORNERS),
        "markers": list(MARKERS),
        "line_styles": list(LINE_STYLES),
        "hatches": list(HATCHES),
        "draw_groups": DRAW_GROUPS,
        "default_draw_order": list(DEFAULT_DRAW_ORDER),
        "layer_file_types": ["shp", "geojson", "json", "gpkg", "kml", "gml", "csv", "tif", "tiff"],
        "raster_cmaps": ["viridis", "gray", "terrain", "RdYlGn", "Spectral", "YlOrRd", "Blues", "magma", "coolwarm", "cividis"],
        "choropleth_schemes": list(CHORO_SCHEMES),
        "choropleth_palettes": ["YlOrRd", "Blues", "Greens", "Purples", "Oranges", "viridis", "cividis", "RdBu", "Spectral"],
        "raster_placements": ["overlay", "basemap"],
        "raster_resamples": ["bilinear", "nearest", "cubic"],
        "defaults": FormState().to_dict(),
    }


_LAYOUT_KEYS = ("legend_style", "legend_title", "legend_cols", "north_style", "north_pos", "north_size",
                "scale_style", "scale_units", "scale_pos", "scale_divisions", "note_pos", "legend_pos", "grid_km")


def layout_from_state(s):
    """Only the settings that differ from the defaults (so an untouched form gives layout=None)."""
    base = FormState()
    d = {"elements": s.elements, "title": s.title or None, "subtitle": s.subtitle if s.subtitle else None,
         "legend_items": s.legend_items, "note": s.note or None, "logo": s.logo or None,
         "tiff_furniture": s.tiff_furniture, "labels": s.labels}
    for k in _LAYOUT_KEYS:
        if getattr(s, k) != getattr(base, k):
            d[k] = getattr(s, k)
    d = {k: v for k, v in d.items() if v not in (None, "", [], False)}
    if list(s.elements) == list(DEFAULT_ELEMENTS):
        d.pop("elements", None)
    if list(s.draw_order or DEFAULT_DRAW_ORDER) != list(DEFAULT_DRAW_ORDER):
        d["draw_order"] = list(s.draw_order)
    if (s.paper or "A0").strip().upper() != "A0":
        d["paper"] = s.paper.strip()
    if s.choropleth and s.choropleth.get("file"):
        d["choropleth"] = dict(s.choropleth)
    if s.legend_title == "" and "legend_title" not in d:
        d["legend_title"] = ""
    return d or None


def _regions(s):
    """(number of distinct places, map types that apply to city/district maps)."""
    provs = len(PROVINCES) if [x.lower() for x in s.provinces] == ["all"] else len(s.provinces)
    return int(s.country) + provs + len(s.cities) + len(s.districts)


def name_problems(s):
    """Problems with a custom file-name template, including names that would overwrite each other."""
    t = (s.name_template or "").strip()
    try:
        file_stem(t, region="sample", level="city", type="street", dpi=100)
    except ValueError as e:
        return [str(e)]
    out = []
    if _regions(s) > 1 and "{region}" not in t:
        out.append("Your file name makes several maps, so it needs {region} - otherwise they would overwrite each other.")
    if len(s.map_types) > 1 and (s.cities or s.districts) and "{type}" not in t:
        out.append("You chose several map types, so the file name needs {type}.")
    if "tiff" in [f.lower() for f in s.formats] and "png" in [f.lower() for f in s.formats]:
        pass  # PNG and TIFF differ by extension
    return out


def example_name(s):
    """A sample of the file name the current settings will give (first place chosen)."""
    if s.country:
        lvl, region, prov = "country", "Pakistan", ""
    elif s.provinces:
        lvl, region, prov = "province", match_province(s.provinces[0]) if s.provinces[0].lower() != "all" else "Punjab", ""
    elif s.cities:
        lvl, region, prov = "city", s.cities[0], ""
    elif s.districts:
        lvl, region, prov = "district", s.districts[0], s.district_province
    else:
        return ""
    slug = lambda x: str(x).lower().replace(" ", "_").replace("-", "_")
    mt = (s.map_types[0] if s.map_types else "street")
    if s.name_mode == "custom":
        try:
            return file_stem(s.name_template, region=slug(region), level=lvl, province=slug(prov) if prov else "",
                             type=mt if lvl in ("city", "district") else lvl, dpi=s.dpi) + ".png"
        except ValueError as e:
            return f"({e})"
    suffix = "" if mt == "street" else f"_{mt}"
    if lvl == "city":
        return f"{slug(region)}{suffix}_A0_{s.dpi}dpi.png"
    if lvl == "district":
        return f"district_{slug(prov)}_{slug(region)}{suffix}_A0_{s.dpi}dpi.png"
    return f"{lvl}_{slug(region)}_A0_{s.dpi}dpi.png"


def validate(s):
    """List of problems (empty = ready to run)."""
    p = []
    if not (s.country or s.provinces or s.cities or s.districts):
        p.append("Choose something to map: country, province, city or district.")
    if s.districts and not s.district_province:
        p.append("Districts need their province (e.g. Khyber Pakhtunkhwa).")
    try:
        for pv in s.provinces:
            if pv.lower() != "all":
                match_province(pv)
        if s.district_province:
            match_province(s.district_province)
    except SystemExit as e:
        p.append(str(e))
    if not s.map_types:
        p.append("Choose at least one map type.")
    bad = [m for m in s.map_types if m not in MAP_TYPES]
    if bad:
        p.append(f"Unknown map type(s): {', '.join(bad)}.")
    if not s.formats or any(f.lower() not in FORMAT_ALIASES for f in s.formats):
        p.append("Choose PNG and/or GeoTIFF.")
    if not est.DPI_MIN <= int(s.dpi) <= est.DPI_MAX:
        p.append(f"Resolution must be between {est.DPI_MIN} and {est.DPI_MAX} dpi.")
    if s.landscape not in (True, False, "auto", "portrait", "landscape"):
        p.append("Orientation must be auto, portrait or landscape.")
    try:
        parse_paper(s.paper)
    except ValueError as e:
        p.append(str(e))
    if s.choropleth and s.choropleth.get("file"):
        try:
            ChoroplethSpec.from_any(s.choropleth)
            if not s.provinces and not s.country:
                p.append("A choropleth shades districts of a province map or provinces of the country map: tick "
                         "'Whole country' or a province on the Where tab.")
        except ValueError as e:
            p.append(str(e))
    if s.theme not in THEMES:
        p.append("Unknown theme.")
    try:
        resolve_pois(s.pois)
    except ValueError as e:
        p.append(str(e))
    if (s.poi_data or s.poi_labels) and not s.pois and "receptors" not in s.map_types:
        p.append("Receptor files/labels need receptor categories (or the 'receptors' map type).")
    if s.radius_km is not None and s.radius_km <= 0:
        p.append("Radius must be greater than 0.")
    if not s.outdir:
        p.append("Choose an output folder.")
    if s.name_mode not in ("auto", "custom"):
        p.append("File naming must be 'auto' or 'custom'.")
    elif s.name_mode == "custom":
        p += name_problems(s)
    try:
        Layout.from_any(layout_from_state(s))
    except ValueError as e:
        p.append(str(e))
    try:
        parse_layers(s.layers)
    except ValueError as e:
        p.append(str(e))
    try:
        parse_draw_order(s.draw_order)
    except ValueError as e:
        p.append(str(e))
    return p


def build_jobs(s, preview=False):
    """FormState -> (jobs, run_kwargs) for api.run_batch / JobRunner. Raises FormError."""
    probs = validate(s)
    if probs:
        raise FormError(probs)
    jobs = []
    if s.country:
        jobs.append({"level": "country"})
    provs = list(PROVINCES) if [x.lower() for x in s.provinces] == ["all"] else [match_province(x) for x in s.provinces]
    jobs += [{"level": "province", "region": pv} for pv in provs]
    jobs += [{"level": "city", "region": c} for c in s.cities]
    if s.districts:
        pv = match_province(s.district_province)
        jobs += [{"level": "district", "region": d, "province": pv} for d in s.districts]
    kw = dict(outdir=s.outdir, skip_existing=s.skip_existing, types=list(s.map_types), formats=list(s.formats),
              dpi=int(s.dpi), landscape=s.landscape, buildings=s.buildings, theme=s.theme,
              radius_km=s.radius_km, pois=list(s.pois) or None, poi_labels=s.poi_labels,
              poi_data=s.poi_data, poi_formats=list(s.poi_formats), layout=layout_from_state(s),
              layers=layers_to_dicts(s.layers) or None,
              filename=(s.name_template.strip() if s.name_mode == "custom" else None))
    if preview:
        kw.update(preview=True, dpi=est.PREVIEW_DPI, formats=["png"], poi_data=False, skip_existing=False)
    return jobs, kw


def choropleth_from_fields(file="", name_col="", value_col="", scheme="quantile", classes="5", palette="YlOrRd",
                           title="", show_values=False):
    """Form fields -> choropleth dict (None when no table is chosen). Blank / default values are left out."""
    if not str(file or "").strip():
        return None
    d = {"file": str(file).strip(), "name_col": str(name_col).strip(), "value_col": str(value_col).strip(),
         "scheme": scheme, "classes": int(str(classes).strip() or 5), "palette": palette,
         "title": str(title).strip(), "show_values": bool(show_values)}
    out = {k: v for k, v in d.items() if v not in ("", False) and not (k == "scheme" and v == "quantile")
           and not (k == "classes" and v == 5) and not (k == "palette" and v == "YlOrRd")}
    out["file"] = d["file"]
    return out


def count_maps(s):
    """(number of map jobs, number of image files) without validating or touching the network."""
    jobs = 0
    n_types = max(1, len(s.map_types))
    provs = len(PROVINCES) if [x.lower() for x in s.provinces] == ["all"] else len(s.provinces)
    jobs += int(s.country) + provs + (len(s.cities) + len(s.districts)) * n_types
    return jobs, jobs * max(1, len(s.formats))


def map_calls(s):
    """(level, map_type) for every map the form will make (no validation, no network)."""
    types = list(s.map_types) or ["street"]
    provs = len(PROVINCES) if [x.lower() for x in s.provinces] == ["all"] else len(s.provinces)
    calls = [("country", "country")] * int(s.country) + [("province", "province")] * provs
    calls += [("city", t) for _ in s.cities for t in types]
    calls += [("district", t) for _ in s.districts for t in types]
    return calls


def estimate(s):
    """Size/memory/download figures to show before running (A0 sheet at the chosen dpi)."""
    try:
        paper = parse_paper(s.paper)[0]
    except ValueError:
        paper = "A0"          # validate() reports the real problem
    px = est.sheet_pixels(s.dpi, s.landscape, paper)
    mp = px[0] * px[1] / 1e6
    n_jobs, n_files = count_maps(s)
    ram = est.ram_gb(s.dpi, s.landscape, tiff=any(f.lower() in ("tif", "tiff", "geotiff") for f in s.formats), paper=paper)
    sizes = est.estimate_calls(map_calls(s), s.dpi, s.formats or ["png"], s.landscape, paper)
    warn = []
    if ram > 6:
        warn.append(f"About {ram:.0f} GB free RAM needed (estimate) - close other programs, or lower the dpi / skip GeoTIFF.")
    elif ram > 3:
        warn.append(f"{s.dpi} dpi needs about {ram:.0f} GB free RAM (estimate).")
    if n_jobs > 20:
        warn.append(f"{n_jobs} maps is a long run (minutes each at A0); 'skip existing' lets you resume.")
    return {"pixels": px, "paper": paper, "megapixels": round(mp), "ram_gb": round(ram, 1), "maps": n_jobs,
            "files": n_files, "warnings": warn, "download_mb": sizes["download_mb"], "files_mb": sizes["files_mb"],
            "download_measured": sizes["download_measured"], "files_measured": sizes["files_measured"],
            "per_map": sizes["per_map"],
            "assumed_defaults": not s.map_types or not s.formats}


def estimate_text(e):
    """Two short lines for the GUI / CLI."""
    if not e["maps"]:
        return "Choose something to map to see sizes."
    guess = lambda m: "measured on your PC" if m else "rough guess until your first run"
    note = "  [nothing ticked on the Map tab: assuming street map + PNG]" if e.get("assumed_defaults") else ""
    return (f"{e['maps']} map(s), {e['files']} image file(s){note}  |  {e.get('paper', 'A0')} {e['pixels'][0]} x {e['pixels'][1]} px "
            f"({e['megapixels']} MP), about {e['ram_gb']} GB RAM\n"
            f"Download about {est.fmt_mb(e['download_mb'])} ({guess(e['download_measured'])}; much less if already cached)"
            f"  |  Files about {est.fmt_mb(e['files_mb'])} ({guess(e['files_measured'])})")


# ---------------------------------------------------------------- presets (remember settings)
def save_preset(s, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(s.to_dict(), f, indent=2)


def load_preset(path):
    with open(path, encoding="utf-8") as f:
        return FormState.from_dict(json.load(f))


def to_batch_json(s, path):
    """Write the jobs (with the chosen options) as a batch file usable with `python -m atlasa0 --batch`."""
    jobs, kw = build_jobs(s)
    types = kw["types"]
    keep = {k: v for k, v in kw.items() if k not in ("outdir", "skip_existing", "types") and v not in (None, [])}
    out = []
    for j in jobs:
        j = dict(j)
        if j["level"] in ("city", "district"):
            j["types"] = types
        j.update(keep)
        out.append(j)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"author": AUTHOR, "email": EMAIL, "license": NOTICE, "jobs": out}, f, indent=2)
    return path


# ---------------------------------------------------------------- background helpers
def load_districts_async(province, callback):
    """Fetch district names without freezing the GUI. callback(names, error) runs in the worker thread."""
    def work():
        try:
            from .api import list_districts
            callback(list_districts(province), None)
        except (Exception, SystemExit) as e:
            callback([], str(e))
    t = threading.Thread(target=work, daemon=True, name="atlasa0-districts")
    t.start()
    return t


def parse_names(text):
    """Multi-line / comma separated text box -> clean list of names."""
    out = []
    for part in str(text).replace(";", "\n").replace(",", "\n").split("\n"):
        part = part.strip()
        if part and part not in out:
            out.append(part)
    return out


# ---------------------------------------------------------------- helpers for the layer/label dialogs
def blend_hex(color, alpha, bg="#ffffff"):
    """Colour as it looks at `alpha` over `bg` - used to preview transparency in the GUI."""
    a = 1.0 if alpha is None else float(alpha)
    fg, bgc = _mc.to_rgb(color), _mc.to_rgb(bg)
    return _mc.to_hex(tuple(a * f + (1 - a) * b for f, b in zip(fg, bgc)))


def layer_summary(d):
    """One line for the layers list: 'sites.shp  |  triangle  |  #d62728  |  80% opaque'."""
    s = parse_layers([d])[0]
    a = "auto" if s.alpha is None else f"{round(s.alpha * 100)}% opaque"
    return f"{s.label}  |  {os.path.basename(s.path)}  |  {s.color}  |  {a}  |  {s.marker}/{s.line_style}"


def draw_order_rows(order):
    """Lines for the GUI draw-order list, TOP FIRST (what you see on top of the printed map is at the top).
    Returns [(group_key, text)]."""
    order = parse_draw_order(order)
    n = len(order)
    rows = []
    for pos, g in enumerate(reversed(order)):
        num = n - pos
        tag = "  (top)" if pos == 0 else "  (bottom)" if pos == n - 1 else ""
        rows.append((g, f"{num:2d}. {DRAW_GROUPS[g]}{tag}"))
    return rows


def move_in_order(order, group, step):
    """Raise (step=+1, printed later = more on top) or lower (step=-1) a group. Returns a new list."""
    order = parse_draw_order(order)
    i = order.index(group)
    j = i + step
    if 0 <= j < len(order):
        order[i], order[j] = order[j], order[i]
    return order


def layer_rows(layers):
    """Lines for the 'Your data' list, TOP FIRST, numbered as printed: the last layer is drawn last (on top)."""
    n = len(layers)
    out = []
    for pos, d in enumerate(reversed(layers)):
        num = n - pos
        tag = " (top)" if pos == 0 and n > 1 else " (bottom)" if pos == n - 1 and n > 1 else ""
        try:
            text = layer_summary(d)
        except ValueError:
            text = f"{d.get('path', '?')}  (file missing or invalid)"
        out.append(f"{num}.{tag}  {text}")
    return out


def label_summary(d):
    return f"{d['text']}  @ {d['lon']:g}, {d['lat']:g}  ({d.get('size', 40):g} pt)"


def check_layer(d):
    """Validate one layer dict; returns the cleaned dict (raises ValueError with a readable message)."""
    return layers_to_dicts([d])[0]


def check_label(d):
    return normalise_label(d)


def marker_shape(name, cx, cy, r):
    """Drawing instructions for the GUI preview: (kind, coords, hollow) with kind 'oval' (x0,y0,x1,y1) or
    'poly' (flat x,y list). Mirrors layers.MARKERS."""
    import math
    hollow = MARKERS[name][1]
    base = name.replace("hollow ", "")
    ngon = lambda n, rot=-90: [v for k in range(n) for v in (cx + r * math.cos(math.radians(rot + 360 * k / n)),
                                                              cy + r * math.sin(math.radians(rot + 360 * k / n)))]
    if base in ("circle", "ring", "dot"):
        rr = r * (0.45 if base == "dot" else 1)
        return "oval", (cx - rr, cy - rr, cx + rr, cy + rr), hollow
    if base == "square":
        return "poly", [cx - r, cy - r, cx + r, cy - r, cx + r, cy + r, cx - r, cy + r], hollow
    if base == "triangle":
        return "poly", ngon(3), hollow
    if base == "triangle down":
        return "poly", ngon(3, 90), hollow
    if base == "diamond":
        return "poly", [cx, cy - r, cx + r, cy, cx, cy + r, cx - r, cy], hollow
    if base == "pentagon":
        return "poly", ngon(5), hollow
    if base == "hexagon":
        return "poly", ngon(6, 0), hollow
    if base == "star":
        pts = []
        for k in range(10):
            rad = r if k % 2 == 0 else r * 0.42
            a = math.radians(-90 + 36 * k)
            pts += [cx + rad * math.cos(a), cy + rad * math.sin(a)]
        return "poly", pts, hollow
    t = r * 0.32   # plus / cross
    plus = [cx - t, cy - r, cx + t, cy - r, cx + t, cy - t, cx + r, cy - t, cx + r, cy + t, cx + t, cy + t,
            cx + t, cy + r, cx - t, cy + r, cx - t, cy + t, cx - r, cy + t, cx - r, cy - t, cx - t, cy - t]
    if base == "plus":
        return "poly", plus, hollow
    s, c_ = math.sin(math.pi / 4), math.cos(math.pi / 4)
    rot = []
    for x, y in zip(plus[0::2], plus[1::2]):
        dx, dy = x - cx, y - cy
        rot += [cx + dx * c_ - dy * s, cy + dx * s + dy * c_]
    return "poly", rot, hollow
