# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Your own raster layers (GeoTIFF): NDVI, land cover, elevation, hillshade, satellite composites...

    layers=[{"path": "ndvi.tif", "name": "NDVI 2025", "cmap": "RdYlGn", "vmin": 0, "vmax": 0.8, "alpha": 0.8},
            {"path": "hillshade.tif", "cmap": "gray", "placement": "basemap"}]

CLI:  --layer "ndvi.tif;name=NDVI;cmap=RdYlGn;vmin=0;vmax=0.8;alpha=0.8"

* 1 band  -> colour-mapped with `cmap` between `vmin` and `vmax` (default: 2nd..98th percentile of the visible area).
* 3-4 bands -> shown as an RGB(A) picture (8-bit stays as is; other types are stretched like a single band).
* nodata cells (and NaN) are transparent.
* placement "overlay" (default) sits in the "Your layers" step of the draw order; "basemap" sits under land use,
  water and roads (the "Satellite / topo image" step) so a hillshade or imagery shows through the street map.
* Any coordinate system works: only the part under the map is read and re-projected to the map's UTM zone.

Structure: converting numbers to colours (`to_rgba`) and drawing are plain numpy / matplotlib (tested anywhere).
Reading the file (`read_window`, `bounds_utm`) needs rasterio - `pip install rasterio` - and is only imported when
a raster layer is really used.
"""
import numpy as np
from matplotlib import colormaps
from matplotlib import colors as mcolors
from matplotlib.patches import Patch

from .runtime import log

RASTER_TYPES = (".tif", ".tiff")
PLACEMENTS = ("overlay", "basemap")
RESAMPLING = ("nearest", "bilinear", "cubic")
MAX_PX = 6000          # longest side of the picture read for the map (a bigger raster is averaged down)
MIN_PX = 600


def is_raster(path):
    import os
    return os.path.splitext(str(path))[1].lower() in RASTER_TYPES


def check_options(spec):
    """Validate the raster-only options of a LayerSpec (raises ValueError)."""
    if spec.cmap and spec.cmap not in colormaps:
        raise ValueError(f"layer '{spec.path}': cmap '{spec.cmap}' is not a matplotlib colour map (try viridis, gray, "
                         f"terrain, RdYlGn, Spectral, YlOrRd, Blues)")
    if int(spec.band) < 1:
        raise ValueError(f"layer '{spec.path}': band must be 1 or more")
    if spec.placement not in PLACEMENTS:
        raise ValueError(f"layer '{spec.path}': placement must be one of: {', '.join(PLACEMENTS)}")
    if spec.resample not in RESAMPLING:
        raise ValueError(f"layer '{spec.path}': resample must be one of: {', '.join(RESAMPLING)}")
    if spec.vmin is not None and spec.vmax is not None and float(spec.vmin) >= float(spec.vmax):
        raise ValueError(f"layer '{spec.path}': vmin must be smaller than vmax")


# ------------------------------------------------------------------------------------------ numbers -> colours
def _stretch(a, vmin, vmax):
    return np.clip((a - vmin) / (vmax - vmin), 0.0, 1.0)


def _limits(values, vmin, vmax):
    """Fill in missing limits with the 2nd / 98th percentile of the valid values."""
    v = values[np.isfinite(values)]
    if v.size == 0:
        return 0.0, 1.0
    lo = float(np.percentile(v, 2)) if vmin is None else float(vmin)
    hi = float(np.percentile(v, 98)) if vmax is None else float(vmax)
    if hi <= lo:                       # flat image: avoid dividing by zero
        hi = lo + 1.0
    return lo, hi


def to_rgba(data, spec, alpha=None):
    """data: float array (bands, h, w) with NaN for no-data -> (RGBA float array h x w x 4, (vmin, vmax) or None).

    alpha: overall opacity 0..1 (default 1). Single band -> colour map; 3 / 4 bands -> RGB(A)."""
    data = np.asarray(data, dtype="float64")
    op = 1.0 if alpha is None else float(alpha)
    nb = data.shape[0]
    if nb >= 3:
        rgb = data[:3]
        valid = np.all(np.isfinite(rgb), axis=0)
        if nb >= 4:
            valid &= np.nan_to_num(data[3], nan=0.0) > 0
        is8 = np.nanmax(rgb) <= 255 and np.nanmin(rgb) >= 0 and spec.vmin is None and spec.vmax is None
        if is8:
            out = rgb / 255.0 if np.nanmax(rgb) > 1.0 else rgb
            limits = None
        else:
            lo, hi = _limits(rgb, spec.vmin, spec.vmax)
            out = _stretch(rgb, lo, hi)
            limits = (lo, hi)
        img = np.zeros(rgb.shape[1:] + (4,))
        img[..., :3] = np.clip(np.nan_to_num(np.moveaxis(out, 0, -1), nan=0.0), 0, 1)
        img[..., 3] = np.where(valid, op, 0.0)
        return img, limits
    band = data[min(max(int(spec.band), 1), nb) - 1] if nb else data[0]
    lo, hi = _limits(band, spec.vmin, spec.vmax)
    cmap = colormaps[spec.cmap or "viridis"]
    valid = np.isfinite(band)
    img = cmap(_stretch(np.where(valid, band, lo), lo, hi))
    img[..., 3] = np.where(valid, op, 0.0)
    return img, (lo, hi)


# ------------------------------------------------------------------------------------------ reading (rasterio)
def _rasterio():
    try:
        import rasterio
        from rasterio import warp
        from rasterio.enums import Resampling
        return rasterio, warp, Resampling
    except ImportError:
        raise ValueError("raster layers (GeoTIFF) need rasterio:  pip install rasterio") from None


def bounds_utm(path, utm):
    """(minx, miny, maxx, maxy) of the raster in the map's UTM zone."""
    rasterio, warp, _ = _rasterio()
    with rasterio.open(path) as src:
        if src.crs is None:
            raise ValueError(f"{path}: the GeoTIFF has no coordinate system (CRS), so it cannot be placed on the map")
        return tuple(warp.transform_bounds(src.crs, utm.to_wkt(), *src.bounds, densify_pts=21))


def read_window(spec, utm, ext, max_px=MAX_PX):
    """Read the part of the raster under the map extent `ext` = (minx, maxx, miny, maxy) in UTM metres, re-projected
    to the map's UTM zone. Returns (data float (bands, h, w) with NaN for no-data, (left, right, bottom, top))."""
    rasterio, warp, Resampling = _rasterio()
    from rasterio.transform import from_bounds
    with rasterio.open(spec.path) as src:
        if src.crs is None:
            raise ValueError(f"{spec.path}: the GeoTIFF has no coordinate system (CRS), so it cannot be placed on the map")
        w_m, h_m = ext[1] - ext[0], ext[3] - ext[2]
        res = min(abs(src.res[0]), abs(src.res[1]))
        try:                                  # native pixel size in metres (degrees -> metres, roughly)
            if src.crs.is_geographic:
                res *= 111_000
        except Exception:
            pass
        nx = int(min(max_px, max(MIN_PX, w_m / max(res, 1e-6))))
        ny = max(1, int(round(nx * h_m / w_m)))
        dst_tr = from_bounds(ext[0], ext[2], ext[1], ext[3], nx, ny)
        nb = src.count
        want = [1, 2, 3, 4][:nb] if nb >= 3 else [min(int(spec.band), nb)]
        dst = np.full((len(want), ny, nx), np.nan, dtype="float64")
        method = {"nearest": Resampling.nearest, "bilinear": Resampling.bilinear, "cubic": Resampling.cubic}[spec.resample]
        nod = src.nodata
        for k, b in enumerate(want):
            warp.reproject(source=rasterio.band(src, b), destination=dst[k], src_transform=src.transform,
                           src_crs=src.crs, src_nodata=nod, dst_transform=dst_tr, dst_crs=utm.to_wkt(),
                           dst_nodata=np.nan, resampling=method)
        if nod is not None:
            dst[dst == nod] = np.nan
    return dst, (ext[0], ext[1], ext[2], ext[3])


# ------------------------------------------------------------------------------------------ drawing
def draw_raster(ax, prep, zorder, utm=None, reader=None):
    """Draw one raster layer on the map axes (limits must already be set). Returns a legend handle or None.
    `reader(spec, utm, ext) -> (data, extent)` can be replaced in tests."""
    s = prep.spec
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    ext = (min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1))
    data, extent = (reader or read_window)(s, prep.utm if utm is None else utm, ext)
    img, limits = to_rgba(data, s, s.alpha if s.alpha is not None else 1.0)
    interp = "nearest" if s.resample == "nearest" else "bilinear"
    ax.imshow(img, extent=(extent[0], extent[1], extent[2], extent[3]), origin="upper", interpolation=interp,
              zorder=zorder, aspect="auto")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    log(f"[layers] {s.label}: raster drawn" + (f", {limits[0]:g} to {limits[1]:g}" if limits else ""))
    if not s.legend:
        return None
    if limits:
        face = colormaps[s.cmap or "viridis"](0.75)
        text = f"{s.label} ({limits[0]:g} - {limits[1]:g})"
    else:
        face, text = mcolors.to_rgba("#b9b09c"), s.label
    return Patch(facecolor=face, edgecolor="#555555", linewidth=1, alpha=1.0, label=text)
