# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Calibration report: what AtlasA0 will produce on A0, from the layout/number helpers (no network).

    python tools/calibrate.py
Draws a synthetic A0 sheet with real matplotlib at low dpi and checks fill, GeoTIFF pixel size and world file.
"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import osmnx, geopandas, shapely  # noqa
except ImportError:  # layout maths do not need them; stand-ins let the helpers import
    import types
    for m in ("osmnx", "geopandas", "shapely", "shapely.geometry"):
        sys.modules[m] = types.ModuleType(m)
    sys.modules["shapely.geometry"].box = lambda *a: None
    sys.modules["osmnx"].settings = types.SimpleNamespace()
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from atlasa0.config import A0_INCHES, AXES_RECT
from atlasa0.render import axes_aspect, fit_extent, nice_scale_km, poi_marker_size, _basemap_zoom
from atlasa0.export import _save_geotiff


class CRS:
    def to_wkt(self, version=None): return 'PROJCS["Test"]'


print("A0: %.0f x %.0f mm" % (A0_INCHES[0] * 25.4, A0_INCHES[1] * 25.4))
for dpi in (200, 300):
    w, h = round(A0_INCHES[0] * dpi), round(A0_INCHES[1] * dpi)
    print(f"  {dpi} dpi: {w} x {h} px = {w*h/1e6:.0f} MP, RGB buffer ~{w*h*4/1e9:.1f} GB (x2-3 while saving)")
print("\nSpan(km) -> scale bar km | marker mm | basemap zoom (lat 34)")
for span in (3, 10, 30, 100, 300, 1500):
    print(f"  {span:5} -> {nice_scale_km(span):6g} | {poi_marker_size(span)[1]:4.1f} | {_basemap_zoom(span*1000, 34, None)}")

b = (700000, 3700000, 710000, 3715000)
ext = fit_extent(b, axes_aspect(A0_INCHES), 1.08)
fig = plt.figure(figsize=A0_INCHES, dpi=20)
ax = fig.add_axes(list(AXES_RECT)); ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal")
ax.apply_aspect(); p = ax.get_position()
print(f"\nAxes fill: width {p.width/AXES_RECT[2]*100:.1f}%  height {p.height/AXES_RECT[3]*100:.1f}%  (100% = no blank bands)")
with tempfile.TemporaryDirectory() as d:
    f = os.path.join(d, "t.tif"); _save_geotiff(fig, ax, f, 20, CRS(), ext, "white")
    px, _, _, npy = [float(v) for v in open(f[:-4] + ".tfw").read().split()[:4]]
    print(f"GeoTIFF pixel: {px:.3f} x {-npy:.3f} m  (square: {abs(px + npy) < 0.01 * px})")
