# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Helpers for province / country overview maps (no network, no geopandas needed - unit tested).

Why this exists (bug seen on the first real Khyber Pakhtunkhwa map):
  osmnx `features_from_polygon(poly, {"boundary": "administrative", "admin_level": "6"})` returns features
  matching ANY of the tags, not all of them. That brought back every administrative area in the province -
  divisions (level 5), districts (6), tehsils (7)... - and the map drew and labelled all of them on top of
  each other. `filter_admin` keeps exactly one level; `place_labels` stops labels from overlapping.
"""
import re

ADMIN_WORDS = {   # names that betray a wrongly tagged unit at a given level
    4: r"\b(?:District|Tehsil|Division|Union Council)\b",
    6: r"\b(?:Tehsil|Division|Union Council|Subdivision|Sub-Division)\b",
}


def _name(row):
    for k in ("name:en", "name"):
        v = row.get(k) if hasattr(row, "get") else None
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def filter_admin(d, level):
    """Keep only polygons tagged admin_level == level (and boundary=administrative when the tag is present).
    Returns (kept, dropped_count)."""
    if d is None or len(d) == 0:
        return d, 0
    gt = d.geom_type if hasattr(d, "geom_type") else d["geom_type"]
    keep = gt.isin(["Polygon", "MultiPolygon"])
    if "admin_level" in d:
        keep &= d["admin_level"].astype(str).str.strip() == str(level)
    else:
        keep &= False      # without the tag we cannot trust anything
    if "boundary" in d:
        keep &= d["boundary"].fillna("administrative").astype(str) == "administrative"
    words = ADMIN_WORDS.get(int(level))
    if words:
        names = d.apply(_name, axis=1)
        keep &= ~names.fillna("").str.contains(words, flags=re.I, regex=True)
    kept = d[keep]
    return kept, int(len(d) - len(kept))


def clean_label(name, drop=("District",)):
    """'Lower South Waziristan District' -> 'Lower South Waziristan' (the subtitle already says districts)."""
    if not isinstance(name, str):
        return None
    out = name.strip()
    for w in drop:
        out = re.sub(rf"\s+{w}$", "", out, flags=re.I)
    return out or None


def wrap_label(text):
    """Split a long name over two lines at the space nearest the middle."""
    if " " not in text or len(text) < 12:
        return text
    mid = len(text) / 2
    i = min((i for i, c in enumerate(text) if c == " "), key=lambda i: abs(i - mid))
    return text[:i] + "\n" + text[i + 1:]


def _overlaps(a, b, pad):
    return not (a.x1 + pad < b.x0 or b.x1 + pad < a.x0 or a.y1 + pad < b.y0 or b.y1 + pad < a.y0)


def place_labels(ax, items, sizes=(34, 28, 22, 17), pad_px=None, **text_kw):
    """Draw labels largest-area first; shrink / wrap a label that collides, skip it if it still does.

    items: list of (text, x, y, area) in data coordinates. Returns (placed_texts, skipped_names)."""
    fig = ax.figure
    renderer = fig.canvas.get_renderer()
    pad = pad_px if pad_px is not None else fig.dpi * 0.04        # ~1 mm gap between labels
    axbox = ax.get_window_extent(renderer)
    placed, boxes, skipped = [], [], []
    for text, x, y, _area in sorted(items, key=lambda it: -(it[3] or 0)):
        done = False
        for s in sizes:
            for variant in dict.fromkeys((text, wrap_label(text))):
                t = ax.text(x, y, variant, ha="center", va="center", fontsize=s, **text_kw)
                bb = t.get_window_extent(renderer)
                inside = bb.x0 >= axbox.x0 and bb.x1 <= axbox.x1 and bb.y0 >= axbox.y0 and bb.y1 <= axbox.y1
                if inside and not any(_overlaps(bb, o, pad) for o in boxes):
                    placed.append(t)
                    boxes.append(bb)
                    done = True
                    break
                t.remove()
            if done:
                break
        if not done:
            skipped.append(text)
    return placed, skipped


def pick_landscape(landscape, bounds):
    """landscape True/False, or "auto": landscape when the area is wider than tall (bounds = minx, miny, maxx, maxy)."""
    if isinstance(landscape, str):
        v = landscape.lower()
        if v == "auto":
            w, h = bounds[2] - bounds[0], bounds[3] - bounds[1]
            return w > h
        return v == "landscape"
    return bool(landscape)


# ----------------------------------------------------------------------------------- point / feature labels
_DIRS = ((0, 1), (1, 0), (-1, 0), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))   # above first, then around


def _box(cx, cy, r):
    from matplotlib.transforms import Bbox
    return Bbox.from_extents(cx - r, cy - r, cx + r, cy + r)


def place_point_labels(ax, items, shrink=(1.0, 0.85, 0.7), avoid=(), pad_px=None, max_labels=600):
    """Place labels next to points / features without printing them on top of each other or on markers.

    The axes limits must already be set. For each label (most important first) it tries 8 positions around the
    anchor (above, right, left, below, then the diagonals) at full size, then slightly smaller, and keeps the first
    one that stays inside the map, does not touch a label already placed and does not cover another marker.
    A label with must=True is never dropped: it takes the position that overlaps least.

    items : list of dicts - text, x, y (data coords), size (pt), gap (pt from the anchor; 0 = centred on it),
            prio (bigger = placed first), must (bool), kw (extra Text kwargs: color, zorder, path_effects ...)
    avoid : extra (x, y, radius_pt) markers labels must not cover (e.g. every receptor point)
    Returns (placed_text_objects, skipped_texts)."""
    fig = ax.figure
    ax.apply_aspect()
    renderer = fig.canvas.get_renderer()
    dpi = fig.dpi
    pad = pad_px if pad_px is not None else dpi * 0.03
    axbox = ax.get_window_extent(renderer)
    to_px = ax.transData.transform

    def marker_box(x, y, r_pt):
        px, py = to_px((x, y))
        return _box(px, py, max(r_pt, 1) * dpi / 72)

    marks = [(marker_box(x, y, r), None) for x, y, r in avoid]
    own = {}
    for i, it in enumerate(items):
        own[i] = len(marks)
        marks.append((marker_box(it["x"], it["y"], it.get("marker_r", it.get("gap", 0) * 0.6)), i))

    order = sorted(range(len(items)), key=lambda i: (-(items[i].get("prio") or 0), i))
    placed, boxes, skipped = [], [], []

    def clash(bb, me):
        if any(_overlaps(bb, o, pad) for o in boxes):
            return True
        return any(m is not None and who != me and _overlaps(bb, m, 0) for m, who in marks)

    for rank, i in enumerate(order):
        it = items[i]
        if rank >= max_labels and not it.get("must"):
            skipped.append(it["text"])
            continue
        gap = float(it.get("gap", 0))
        dirs = _DIRS if gap else ((0, 0),) + tuple((dx, dy) for dx, dy in _DIRS[:4])
        g = gap if gap else it["size"] * 0.7
        best = None            # (overlap area, text artist) for must-show fallback
        done = False
        for f in shrink:
            for dx, dy in dirs:
                kw = dict(it.get("kw") or {})
                ha = "left" if dx > 0 else "right" if dx < 0 else "center"
                va = "bottom" if dy > 0 else "top" if dy < 0 else "center"
                t = ax.annotate(it["text"], (it["x"], it["y"]), xytext=(dx * g, dy * g), textcoords="offset points",
                                fontsize=it["size"] * f, ha=ha, va=va, annotation_clip=False, **kw)
                bb = t.get_window_extent(renderer)
                inside = bb.x0 >= axbox.x0 and bb.x1 <= axbox.x1 and bb.y0 >= axbox.y0 and bb.y1 <= axbox.y1
                if inside and not clash(bb, i):
                    placed.append(t)
                    boxes.append(bb)
                    done = True
                    if best is not None:
                        best[1].remove()
                    break
                if it.get("must"):
                    area = sum(max(0, min(bb.x1, o.x1) - max(bb.x0, o.x0)) * max(0, min(bb.y1, o.y1) - max(bb.y0, o.y0))
                               for o in boxes) + (0 if inside else 1e12)
                    if best is None or area < best[0]:
                        if best is not None:
                            best[1].remove()
                        best = (area, t, bb)
                        continue
                t.remove()
            if done:
                break
        if not done:
            if best is not None:
                placed.append(best[1])
                boxes.append(best[2])
            else:
                skipped.append(it["text"])
    return placed, skipped
