# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Choropleth maps: shade provinces (country map) or districts (province map) from a table of numbers.

    layout={"choropleth": {"file": "population.csv", "name_col": "District", "value_col": "Population",
                           "scheme": "quantile", "classes": 5, "palette": "YlOrRd", "title": "Population (2023)",
                           "show_values": True}}

CLI:  --choropleth "population.csv;name_col=District;value_col=Population;classes=5;palette=YlOrRd;title=Population"

* The table is a CSV or Excel (.xlsx) file: one column with place names, one with numbers. If you do not name the
  columns, the first text column and the first numeric column are used.
* Names are matched to the map's areas ignoring case, accents, punctuation and words like "District"; common short
  forms (D.I. Khan, DG Khan, KPK, ICT, AJK, GB ...) are understood, and a close spelling is accepted. Rows that
  match nothing, and areas without a row, are listed in the log so nothing is silently lost.
* Class limits: quantile (same number of areas per class), equal (equal value steps), natural (Jenks natural breaks)
  or manual (`breaks=10;50;100`).

Everything here is plain python / numpy / matplotlib (no geopandas), so it is tested without internet.
"""
import csv
import difflib
import os
import re
import unicodedata
from dataclasses import dataclass, field, fields

import numpy as np
from matplotlib import colormaps
from matplotlib import colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch

SCHEMES = ("quantile", "equal", "natural", "manual")
TABLE_TYPES = (".csv", ".xlsx")
MAX_CLASSES = 9
DROP_WORDS = r"\b(?:district|division|tehsil|city|province|region|agency|capital territory)\b"
ALIASES = {      # normalised short form (spaces removed) -> normalised full name
    "dikhan": "dera ismail khan", "dikhn": "dera ismail khan", "dgkhan": "dera ghazi khan", "dghazikhan": "dera ghazi khan",
    "kpk": "khyber pakhtunkhwa", "kp": "khyber pakhtunkhwa", "nwfp": "khyber pakhtunkhwa", "pakhtunkhwa": "khyber pakhtunkhwa",
    "khyberpakhtunkhwa": "khyber pakhtunkhwa", "baluchistan": "balochistan", "gb": "gilgit baltistan",
    "gilgitbaltistan": "gilgit baltistan", "ajk": "azad kashmir", "azadjammuandkashmir": "azad kashmir",
    "azadjammukashmir": "azad kashmir", "ict": "islamabad", "islamabadcapital": "islamabad", "sind": "sindh",
    "rawalpindi": "rawalpindi", "nowshera": "nowshera", "peshawer": "peshawar", "lowerdir": "lower dir",
    "upperdir": "upper dir", "shaheedbenazirabad": "shaheed benazirabad", "nawabshah": "shaheed benazirabad",
    "bhakkar": "bhakkar", "tank": "tank", "kohat": "kohat",
}


# ------------------------------------------------------------------------------------------ spec
@dataclass
class ChoroplethSpec:
    file: str
    name_col: str = ""             # column with place names (default: first text column)
    value_col: str = ""            # column with numbers (default: first numeric column)
    scheme: str = "quantile"
    classes: int = 5
    breaks: list = field(default_factory=list)      # scheme "manual": inner class limits, e.g. [10, 50, 100]
    palette: str = "YlOrRd"        # any matplotlib colour map, or two or more colours "#fee8c8,#e34a33"
    reverse: bool = False
    title: str = ""                # legend heading (default: the value column name)
    missing: str = ""              # colour for areas without a number (default: theme building colour)
    show_values: bool = False      # print the number under each area name
    decimals: int = None           # digits after the point in legend / labels (default: automatic)

    def __post_init__(self):
        self.validate()

    def validate(self):
        if not self.file:
            raise ValueError("choropleth needs a data file (.csv or .xlsx)")
        if os.path.splitext(self.file)[1].lower() not in TABLE_TYPES:
            raise ValueError(f"choropleth file '{self.file}': use .csv or .xlsx")
        if not os.path.isfile(self.file):
            raise ValueError(f"choropleth file not found: {self.file}")
        if self.scheme not in SCHEMES:
            raise ValueError(f"choropleth scheme must be one of: {', '.join(SCHEMES)}")
        if not 2 <= int(self.classes) <= MAX_CLASSES:
            raise ValueError(f"choropleth classes must be 2-{MAX_CLASSES}")
        if self.scheme == "manual":
            b = [float(x) for x in self.breaks]
            if not b or b != sorted(set(b)):
                raise ValueError("choropleth manual breaks must be increasing numbers, e.g. breaks=10;50;100")
        palette_colors(self.palette, 2)          # raises ValueError if unknown
        if self.missing and not mcolors.is_color_like(self.missing):
            raise ValueError(f"choropleth missing colour '{self.missing}' is not a colour")
        if self.decimals is not None and not 0 <= int(self.decimals) <= 6:
            raise ValueError("choropleth decimals must be 0-6")

    @classmethod
    def from_any(cls, spec):
        if isinstance(spec, cls):
            return spec
        if isinstance(spec, str):
            return parse_spec(spec)
        d = dict(spec)
        known = {f.name for f in fields(cls)}
        bad = set(d) - known
        if bad:
            raise ValueError(f"unknown choropleth option(s): {', '.join(sorted(bad))}")
        if "file" not in d and "path" in d:
            d["file"] = d.pop("path")
        for k in ("classes", "decimals"):
            if d.get(k) in ("", None):
                d.pop(k, None)
            else:
                d[k] = int(d[k])
        for k in ("reverse", "show_values"):
            if k in d:
                d[k] = d[k] if isinstance(d[k], bool) else str(d[k]).strip().lower() in ("1", "true", "yes", "y", "on")
        if "breaks" in d:
            b = d["breaks"]
            d["breaks"] = [float(x) for x in (re.split(r"[;,\s]+", b.strip()) if isinstance(b, str) else b) if str(x).strip()]
        return cls(**d)

    def to_dict(self):
        base = {f.name: f.default for f in fields(self) if f.name != "file"}
        out = {"file": self.file}
        for k in base:
            v = getattr(self, k)
            if v != base[k] and v not in ([], ""):
                out[k] = v
        return out


def parse_spec(text):
    """'data.csv;name_col=District;value_col=Pop;classes=5;breaks=10;50;100' -> ChoroplethSpec."""
    parts = [p.strip() for p in str(text).split(";") if p.strip()]
    if not parts:
        raise ValueError("empty choropleth specification")
    d = {"file": parts[0]}
    last = None
    for p in parts[1:]:
        k, sep, v = p.partition("=")
        if sep:
            last = k.strip().replace("-", "_")
            d[last] = v.strip()
        elif last == "breaks":                       # breaks=10;50;100 -> the ';' split the numbers apart
            d["breaks"] = f"{d['breaks']};{p}"
        else:
            raise ValueError(f"choropleth option must look like key=value, got '{p}'")
    return ChoroplethSpec.from_any(d)


# ------------------------------------------------------------------------------------------ reading the table
def _to_float(x):
    if x is None:
        return float("nan")
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip().replace(",", "").replace("%", "").replace(" ", "")
    if s in ("", "-", "--", "n/a", "na", "nan", "null", "none"):
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _rows(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xlsx":
        try:
            import openpyxl
        except ImportError:
            raise ValueError("reading .xlsx needs openpyxl:  pip install openpyxl  (or save the table as .csv)") from None
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        rows = [["" if c is None else c for c in r] for r in ws.iter_rows(values_only=True)]
        wb.close()
        return rows
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        return [r for r in csv.reader(f, dialect)]


def read_table(spec):
    """-> (names, values (float array, NaN = no number), name_col, value_col)."""
    rows = [r for r in _rows(spec.file) if any(str(c).strip() for c in r)]
    if len(rows) < 2:
        raise ValueError(f"{spec.file}: the table needs a header row and at least one data row")
    header = [str(c).strip() for c in rows[0]]
    body = rows[1:]

    def col_index(name, what):
        low = [h.lower() for h in header]
        if name.lower() in low:
            return low.index(name.lower())
        raise ValueError(f"{spec.file}: no {what} column '{name}' (columns: {', '.join(header)})")

    ncols = len(header)
    if spec.value_col:
        vi = col_index(spec.value_col, "value")
    else:
        vi = next((i for i in range(ncols) if sum(not np.isnan(_to_float(r[i] if i < len(r) else None)) for r in body)
                   >= max(1, len(body) // 2) and i != (col_index(spec.name_col, "name") if spec.name_col else -1)), None)
        if vi is None:
            raise ValueError(f"{spec.file}: could not find a column of numbers; set value_col (columns: {', '.join(header)})")
    if spec.name_col:
        ni = col_index(spec.name_col, "name")
    else:
        ni = next((i for i in range(ncols) if i != vi and sum(bool(str(r[i] if i < len(r) else "").strip())
                                                          and np.isnan(_to_float(r[i] if i < len(r) else None))
                                                          for r in body) >= max(1, len(body) // 2)), None)
        if ni is None:
            raise ValueError(f"{spec.file}: could not find a column of place names; set name_col (columns: {', '.join(header)})")
    names = [str(r[ni]).strip() if ni < len(r) else "" for r in body]
    values = np.array([_to_float(r[vi] if vi < len(r) else None) for r in body], dtype="float64")
    keep = [i for i, n in enumerate(names) if n]
    return [names[i] for i in keep], values[keep], header[ni], header[vi]


# ------------------------------------------------------------------------------------------ name matching
def normalise_name(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[.'`’]", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(DROP_WORDS, " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    key = s.replace(" ", "")
    return ALIASES.get(key, s)


def match_names(table_names, area_names, cutoff=0.84):
    """Match map areas to table rows. Returns ({area index: row index}, unmatched row indices, unmatched area indices)."""
    t_norm = [normalise_name(n) for n in table_names]
    a_norm = [normalise_name(n) for n in area_names]
    t_flat = [n.replace(" ", "") for n in t_norm]
    used, out = set(), {}
    for ai, an in enumerate(a_norm):                   # 1. same after cleaning
        for ti, tn in enumerate(t_norm):
            if ti not in used and an and (an == tn or an.replace(" ", "") == t_flat[ti]):
                out[ai] = ti
                used.add(ti)
                break
    t_sorted = [" ".join(sorted(n.split())) for n in t_norm]        # 1b. same words in another order (Lower Dir / Dir Lower)
    for ai, an in enumerate(a_norm):
        if ai in out or not an:
            continue
        key = " ".join(sorted(an.split()))
        for ti in range(len(t_norm)):
            if ti not in used and t_sorted[ti] == key:
                out[ai] = ti
                used.add(ti)
                break
    scored = []                                         # 2. close spelling, best pairs first, each row used once
    for ai, an in enumerate(a_norm):
        if ai in out or not an:
            continue
        for ti, tn in enumerate(t_norm):
            if ti in used or not tn:
                continue
            r = difflib.SequenceMatcher(None, an, tn).ratio()
            if r >= cutoff:
                scored.append((r, ai, ti))
    for r, ai, ti in sorted(scored, reverse=True):
        if ai not in out and ti not in used:
            out[ai] = ti
            used.add(ti)
    return (out, [i for i in range(len(table_names)) if i not in used],
            [i for i in range(len(area_names)) if i not in out])


# ------------------------------------------------------------------------------------------ classes
def _jenks(values, k):
    """Fisher-Jenks natural breaks -> k+1 edges (min ... max)."""
    v = np.sort(np.asarray(values, dtype=float))
    n = len(v)
    k = min(k, n)
    lower = np.zeros((n + 1, k + 1), dtype=int)
    var = np.full((n + 1, k + 1), np.inf)
    lower[1, 1:] = 1
    var[1, 1:] = 0
    for l in range(2, n + 1):
        s1 = s2 = w = 0.0
        for m in range(1, l + 1):
            i3 = l - m + 1
            val = v[i3 - 1]
            s2 += val * val
            s1 += val
            w += 1
            variance = s2 - (s1 * s1) / w
            i4 = i3 - 1
            if i4:
                for j in range(2, k + 1):
                    if var[l, j] >= variance + var[i4, j - 1]:
                        lower[l, j] = i3
                        var[l, j] = variance + var[i4, j - 1]
        lower[l, 1] = 1
        var[l, 1] = s2 - (s1 * s1) / w
    edges = [0.0] * (k + 1)
    edges[k] = v[-1]
    edges[0] = v[0]
    kk, idx = k, n
    while kk > 1:
        idx = lower[idx, kk] - 1
        edges[kk - 1] = v[idx - 1]
        kk -= 1
    return edges


def class_edges(values, scheme="quantile", classes=5, breaks=()):
    """Edges of the classes (len = classes + 1, strictly increasing; fewer classes when the data has fewer
    distinct values). Raises ValueError when there are no numbers."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        raise ValueError("choropleth: the table has no numbers that match the map")
    lo, hi = float(v.min()), float(v.max())
    if scheme == "manual":
        edges = [min(lo, float(breaks[0]))] + [float(b) for b in breaks] + [max(hi, float(breaks[-1]))]
    else:
        k = max(2, min(int(classes), len(np.unique(v))))
        if lo == hi:
            return [lo, hi + 1.0]
        if scheme == "equal":
            edges = list(np.linspace(lo, hi, k + 1))
        elif scheme == "natural":
            edges = _jenks(v, k)
        else:
            edges = list(np.quantile(v, np.linspace(0, 1, k + 1)))
    out = [edges[0]]
    for e in edges[1:]:
        if e > out[-1] + 1e-12:
            out.append(float(e))
    if len(out) < 2:
        out = [lo, hi + 1.0]
    return out


def class_index(values, edges):
    """Class number of each value (0 .. n-1); -1 for NaN. A value on a limit goes to the higher class, the maximum to the last."""
    v = np.asarray(values, dtype=float)
    idx = np.searchsorted(np.asarray(edges[1:-1], dtype=float), v, side="right")
    return np.where(np.isfinite(v), idx, -1)


def palette_colors(palette, n, reverse=False):
    """n hex colours for a matplotlib colour map name or 'colour,colour,...'."""
    p = str(palette).strip()
    if "," in p or p.startswith("#"):
        cols = [c.strip() for c in p.split(",") if c.strip()]
        if len(cols) < 2 or not all(mcolors.is_color_like(c) for c in cols):
            raise ValueError(f"choropleth palette '{palette}': give a colour map name (YlOrRd, Blues, viridis...) "
                             f"or two or more colours like #fee8c8,#e34a33")
        cmap = LinearSegmentedColormap.from_list("custom", cols)
        pts = np.linspace(0, 1, n)
    else:
        if p not in colormaps:
            raise ValueError(f"choropleth palette '{palette}' is not a matplotlib colour map (try YlOrRd, Blues, "
                             f"Greens, viridis, cividis, RdBu)")
        cmap = colormaps[p]
        pts = np.linspace(0.12, 0.95, n) if n > 1 else [0.6]
    cols = [mcolors.to_hex(cmap(x)) for x in pts]
    return cols[::-1] if reverse else cols


def format_number(x, decimals=None, span=None):
    if decimals is None:
        decimals = 0 if (span is None or span >= 20) else 1 if span >= 2 else 2 if span >= 0.2 else 3
    return f"{x:,.{decimals}f}"


def _decimals(decimals, edges):
    """Chosen digits, or 0 when every class limit is a whole number, or None (= decide from the value range)."""
    if decimals is None and all(abs(e - round(e)) < 1e-9 for e in edges):
        return 0
    return decimals


def legend_labels(edges, decimals=None):
    span = edges[-1] - edges[0]
    decimals = _decimals(decimals, edges)
    return [f"{format_number(edges[i], decimals, span)} - {format_number(edges[i + 1], decimals, span)}"
            for i in range(len(edges) - 1)]


# ------------------------------------------------------------------------------------------ putting it together
@dataclass
class Choropleth:
    colors: list               # one hex colour per map area (the 'missing' colour when there is no number)
    values: list               # one float (NaN = none) per map area
    edges: list
    handles: list              # legend: a heading and one Patch per class (+ "no data")
    text: dict                 # area index -> formatted number (for show_values)
    matched: int
    notes: list                # human-readable log lines (unmatched rows / areas)


def build(spec, area_names, theme):
    """Colour every map area. area_names: names of the polygons in drawing order."""
    spec = ChoroplethSpec.from_any(spec)
    names, vals, ncol, vcol = read_table(spec)
    m, rows_left, areas_left = match_names(names, area_names)
    values = np.full(len(area_names), np.nan)
    for ai, ti in m.items():
        values[ai] = vals[ti]
    if not np.isfinite(values).any():
        raise ValueError(f"choropleth: none of the names in '{os.path.basename(spec.file)}' matched a map area "
                         f"(map areas: {', '.join(n for n in area_names if n)})")
    edges = class_edges(values, spec.scheme, spec.classes, spec.breaks)
    n = len(edges) - 1
    cols = palette_colors(spec.palette, n, spec.reverse)
    idx = class_index(values, edges)
    miss = spec.missing or theme["building"]
    colors = [cols[i] if i >= 0 else miss for i in idx]
    labels = legend_labels(edges, spec.decimals)
    title = spec.title or vcol
    handles = [Patch(facecolor="none", edgecolor="none", label=title)]
    handles += [Patch(facecolor=c, edgecolor=theme["frame"], linewidth=1, label=lb) for c, lb in zip(cols, labels)]
    if (idx < 0).any():
        handles.append(Patch(facecolor=miss, edgecolor=theme["frame"], linewidth=1, label="no data"))
    dec = _decimals(spec.decimals, edges)
    span = edges[-1] - edges[0]
    text = {i: format_number(v, dec, span) for i, v in enumerate(values) if np.isfinite(v)}
    notes = [f"[choropleth] {len(m)} of {len(area_names)} areas matched '{vcol}' ({spec.scheme}, {n} classes)"]
    if rows_left:
        notes.append("[choropleth] table rows with no map area: " + ", ".join(names[i] for i in rows_left))
    if areas_left:
        notes.append("[choropleth] map areas with no table row (shown as 'no data'): "
                     + ", ".join(area_names[i] for i in areas_left if area_names[i]))
    return Choropleth(colors, list(values), edges, handles, text, len(m), notes)
