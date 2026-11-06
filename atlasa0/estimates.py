# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Size estimates shown before a run: pixels, RAM, OpenStreetMap download and output file sizes.

The first numbers are rough starting guesses. After each real run AtlasA0 records what actually happened
(file bytes per pixel for each map type, megabytes downloaded into the OSM cache per level/map type) in a
small JSON file (~/.atlasa0_stats.json, or $ATLASA0_STATS) and later estimates use those measurements.
Nothing here touches the network.
"""
import json
import os

from .config import A0_INCHES, AXES_RECT

DPI_MIN, DPI_MAX = 50, 500
MAP_AREA_FRACTION = AXES_RECT[2] * AXES_RECT[3]   # GeoTIFF = map area only (no title/margins)

# --- starting guesses (replaced by your own measurements after the first runs) -----------------
# PNG size in MB for the whole A0 sheet at 300 dpi. Line maps compress better as dpi rises, so size grows
# about as dpi^1.4 (measured on a dense synthetic A0 line map: 6 / 28 / 55 MB at 100 / 300 / 500 dpi);
# photo-like basemaps (satellite, topo) grow with the pixel count (dpi^2).
PNG_MB_300 = {"street": 40, "transport": 15, "landuse": 28, "water": 10, "buildings": 45,
              "satellite": 200, "topo": 150, "receptors": 40, "province": 20, "country": 18}
PHOTO_TYPES = ("satellite", "topo")
TIFF_VS_PNG = 1.6   # LZW TIFF is usually larger than PNG for the same pixels (TIFF = map area only)
# First-time OpenStreetMap download in MB (cached runs download almost nothing).
DOWNLOAD_MB = {"street": 45, "transport": 12, "landuse": 25, "water": 8, "buildings": 120,
               "satellite": 60, "topo": 40, "receptors": 30}
LEVEL_FACTOR = {"city": 1.0, "district": 2.5}       # a district covers more ground than a city
DOWNLOAD_MB_FIXED = {"province": 150, "country": 450}


# ------------------------------------------------------------------------------- stats file
def stats_path():
    return os.environ.get("ATLASA0_STATS") or os.path.join(os.path.expanduser("~"), ".atlasa0_stats.json")


def load_stats():
    try:
        with open(stats_path(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _remember(section, key, value, keep=10):
    """Append a measurement (last `keep` kept). Never raises: estimates are a convenience."""
    try:
        d = load_stats()
        vals = d.setdefault(section, {}).setdefault(key, [])
        vals.append(round(float(value), 5))
        del vals[:-keep]
        with open(stats_path(), "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
    except Exception:
        pass


def _measured(section, key):
    vals = sorted(load_stats().get(section, {}).get(key, []))
    return vals[len(vals) // 2] if vals else None      # median: one odd run does not skew it


def _growth(map_type, dpi):
    return (dpi / 300.0) ** (2.0 if map_type in PHOTO_TYPES else 1.4)


def record_file(map_type, fmt, path, dpi, landscape=False):
    """After a real run: remember the file size (normalised to 300 dpi) of a PNG/TIFF just written."""
    try:
        _remember("mb_at_300dpi", f"{fmt}:{map_type}", os.path.getsize(path) / 1e6 / _growth(map_type, dpi))
    except Exception:
        pass


def record_download(level, map_type, mb):
    """After a real run: remember MB newly added to the OSM cache (skip if everything came from cache)."""
    if mb and mb > 0.05:
        _remember("download_mb", f"{level}:{map_type}", mb)


def folder_mb(path):
    total = 0
    for root, _, files in os.walk(path or "."):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total / 1e6


# ------------------------------------------------------------------------------- estimates
def sheet_pixels(dpi, landscape=False):
    land = landscape is True or (isinstance(landscape, str) and landscape.lower() == "landscape")
    w, h = (A0_INCHES[::-1] if land else A0_INCHES)       # "auto": decided per map; same pixel count
    return round(w * dpi), round(h * dpi)


def file_mb(map_type, fmt, dpi, landscape=False):
    """(megabytes, measured?) for one output file."""
    m = _measured("mb_at_300dpi", f"{fmt}:{map_type}")
    if m is not None:
        return m * _growth(map_type, dpi), True
    base = PNG_MB_300.get(map_type, 30) * (MAP_AREA_FRACTION * TIFF_VS_PNG if fmt == "tiff" else 1)
    return base * _growth(map_type, dpi), False


def download_mb(level, map_type):
    """(megabytes, measured?) downloaded the first time a place is mapped (cached places: about 0)."""
    m = _measured("download_mb", f"{level}:{map_type}")
    if m is not None:
        return m, True
    if level in DOWNLOAD_MB_FIXED:
        return float(DOWNLOAD_MB_FIXED[level]), False
    return DOWNLOAD_MB.get(map_type, 30) * LEVEL_FACTOR.get(level, 1.0), False


def ram_gb(dpi, landscape=False, tiff=False):
    """Peak memory estimate. Drawing + saving a PNG measured ~4.2 bytes/pixel (1.6 GB at 500 dpi, synthetic map);
    a GeoTIFF adds copies of the image (RGBA -> RGB -> optional rasterio array) -> ~12 bytes/pixel;
    plus ~1.5 GB for the OpenStreetMap data and Python itself (more for building footprints of big areas)."""
    w, h = sheet_pixels(dpi, landscape)
    return w * h / 1e6 * (12.0 if tiff else 4.5) / 1000 + 1.5


def estimate_calls(calls, dpi, formats, landscape=False):
    """calls: list of (level, map_type). Totals for a whole run."""
    fmts = sorted({"tiff" if f.lower() in ("tif", "tiff", "geotiff") else "png" for f in formats}) or ["png"]
    dl = files = 0.0
    measured_dl = measured_files = True
    per = []
    for level, mt in calls:
        key = mt if level in ("city", "district") else level
        d, m1 = download_mb(level, key)
        sizes = {f: file_mb(key, f, dpi, landscape) for f in fmts}
        dl += d
        files += sum(s for s, _ in sizes.values())
        measured_dl &= m1
        measured_files &= all(m for _, m in sizes.values())
        per.append({"level": level, "map_type": key, "download_mb": round(d, 1),
                    "files_mb": {f: round(s, 1) for f, (s, _) in sizes.items()}})
    return {"download_mb": round(dl, 1), "files_mb": round(files, 1), "download_measured": measured_dl,
            "files_measured": measured_files, "per_map": per}


def fmt_mb(mb):
    return f"{mb / 1000:.1f} GB" if mb >= 1000 else f"{mb:.0f} MB" if mb >= 10 else f"{mb:.1f} MB"


def dpi_label(dpi):
    """Plain words for a resolution (used next to the GUI slider)."""
    d = int(dpi)
    kind = ("screen preview" if d < 150 else "draft print" if d < 250 else "print quality" if d < 350
            else "high detail" if d < 450 else "maximum detail")
    return f"{d} dpi - {kind}"
