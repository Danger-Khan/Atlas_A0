# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Saving: poster PNG and georeferenced TIFF (+ .tfw/.prj) for ArcMap / QGIS."""
import os

import matplotlib.pyplot as plt

from .config import FORMAT_ALIASES
from .runtime import log


def _save_geotiff(fig, ax, path, dpi, utm, ext, facecolor):
    """Save ONLY the map area (no title/margins) as a georeferenced TIFF for ArcMap/QGIS.

    Georeferencing = world file (.tfw) + projection (.prj) next to the .tif, which ArcMap reads
    automatically. If `rasterio` is installed, the CRS/transform are also embedded in the TIFF.
    CRS is the UTM zone of the region (metres)."""
    from matplotlib.transforms import Bbox
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    ax.apply_aspect()
    pos = ax.get_position()
    W, H = fig.get_size_inches()
    bbox = Bbox.from_bounds(pos.x0 * W, pos.y0 * H, pos.width * W, pos.height * H)
    fig.savefig(path, dpi=dpi, facecolor=facecolor, bbox_inches=bbox, pad_inches=0,
                format="tiff", pil_kwargs={"compression": "tiff_lzw"})

    with Image.open(path) as im:  # drop the alpha band -> plain 3-band RGB (cleaner in ArcMap)
        rgb = im.convert("RGB")
    rgb.save(path, compression="tiff_lzw", dpi=(dpi, dpi))
    w, h = rgb.size
    del rgb
    px, py =(ext[1] - ext[0]) / w, (ext[3] - ext[2]) / h
    base = os.path.splitext(path)[0]
    with open(base + ".tfw", "w") as f:  # world file: pixel size, rotation, upper-left pixel centre
        f.write(f"{px}\n0\n0\n{-py}\n{ext[0] + px / 2}\n{ext[3] - py / 2}\n")
    try:
        wkt = utm.to_wkt(version="WKT1_ESRI")
    except Exception:
        wkt = utm.to_wkt()
    with open(base + ".prj", "w") as f:
        f.write(wkt)

    try:  # optional: embed georeferencing inside the TIFF itself
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        with Image.open(path) as im:
            arr = np.array(im.convert("RGB"))
        with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=3, dtype="uint8",
                           crs=utm.to_wkt(), transform=from_origin(ext[0], ext[3], px, py),
                           compress="lzw", photometric="RGB", BIGTIFF="IF_SAFER") as dst:
            dst.write(arr.transpose(2, 0, 1))
    except Exception:
        pass  # sidecar files still georeference it
    return path


def save_outputs(fig, ax, out, dpi, formats, utm, ext, facecolor, tag, tiff_furniture=False):
    """Write the requested formats; returns the list of files created (png and/or tif)."""
    base = os.path.splitext(out)[0]
    fmts = {FORMAT_ALIASES[f.lower()] for f in formats}
    paths = []
    # Some libraries (geopandas/pyproj) add CRS axis titles like "Easting (metre)" in tiny default type; the
    # grid footer already explains the km labels, so drop them (they showed as specks at A0 size).
    ax.set_xlabel("")
    ax.set_ylabel("")
    if "png" in fmts:
        fig.savefig(base + ".png", dpi=dpi, facecolor=facecolor)
        paths.append(base + ".png")
    if "tiff" in fmts:
        if not tiff_furniture:  # keep the GIS raster clean: no legends / scale / north / grid burnt in
            for art in getattr(fig, "_atlasa0_furniture", []):
                art.set_visible(False)
        paths.append(_save_geotiff(fig, ax, base + ".tif", dpi, utm, ext, facecolor))
    plt.close(fig)
    for pth in paths:
        log(f"[{tag}] done -> {pth}")
    return paths


def write_poi_files(poi, base, formats=("geojson", "csv"), counts=None):
    """Write points of interest for GIS / reports.

    formats: "csv" (table), "geojson" (WGS84 points), "xlsx" (Excel: Receptors + Summary sheets),
             "summary" (small CSV: one row per category with its count).
    counts : optional {category: n} (include zero counts in the summary)."""
    import pandas as pd
    from .config import POI_CATEGORIES, POI_FILE_SUFFIX
    fmts = [f.lower() for f in formats]
    bad = [f for f in fmts if f not in POI_FILE_SUFFIX]
    if bad:
        raise ValueError(f"unknown receptor format(s): {', '.join(bad)}. Use: {', '.join(POI_FILE_SUFFIX)}")
    if poi is None or poi.empty or not fmts:
        return []
    w = poi.to_crs(4326)
    df = pd.DataFrame({"category": poi["category"].values, "name": poi["name"].values,
                       "lon": w.geometry.x.values, "lat": w.geometry.y.values,
                       "x_utm": poi.geometry.x.values, "y_utm": poi.geometry.y.values})
    if counts is None:
        counts = df["category"].value_counts().to_dict()
    summ = pd.DataFrame([{"category": k, "label": POI_CATEGORIES[k]["label"], "count": int(n)}
                         for k, n in counts.items()])
    summ.loc[len(summ)] = ["TOTAL", "", int(summ["count"].sum())]

    out = []
    if "geojson" in fmts:
        with open(base + POI_FILE_SUFFIX["geojson"], "w", encoding="utf-8") as f:
            f.write(w.to_json())
        out.append(base + POI_FILE_SUFFIX["geojson"])
    if "csv" in fmts:
        df.to_csv(base + POI_FILE_SUFFIX["csv"], index=False, encoding="utf-8-sig")  # BOM: Excel shows Urdu
        out.append(base + POI_FILE_SUFFIX["csv"])
    if "summary" in fmts:
        summ.to_csv(base + POI_FILE_SUFFIX["summary"], index=False, encoding="utf-8-sig")
        out.append(base + POI_FILE_SUFFIX["summary"])
    if "xlsx" in fmts:
        try:
            with pd.ExcelWriter(base + POI_FILE_SUFFIX["xlsx"], engine="openpyxl") as xw:
                df.to_excel(xw, sheet_name="Receptors", index=False)
                summ.to_excel(xw, sheet_name="Summary", index=False)
                for name, frame in (("Receptors", df), ("Summary", summ)):
                    ws = xw.sheets[name]
                    ws.freeze_panes = "A2"
                    for i, col in enumerate(frame.columns, 1):
                        width = max([len(str(col))] + [len(str(v)) for v in frame[col].head(500)]) + 2
                        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = min(width, 60)
            out.append(base + POI_FILE_SUFFIX["xlsx"])
        except ImportError:
            log("    (xlsx skipped: install openpyxl -> pip install openpyxl)")
    return out
