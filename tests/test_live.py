# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""LIVE tests: real OpenStreetMap downloads. Skipped unless  ATLASA0_LIVE=1  and osmnx/geopandas are installed.

    ATLASA0_LIVE=1 pytest tests/test_live.py -v -s

They use a 1 km radius and 40 dpi so they stay small and quick (still several Overpass requests).
"""
import os

import pytest
from PIL import Image

from atlasa0 import find_receptors, generate_map
from atlasa0.config import A0_INCHES, AXES_RECT

DPI = 40


def _tfw(path):
    return [float(v) for v in open(path).read().split()]


def test_city_png_and_geotiff(live, tmp_path):
    res = generate_map("Peshawar", radius_km=1, dpi=DPI, formats=("png", "tiff"), outdir=str(tmp_path))
    paths = {r["format"]: r["path"] for r in res}
    with Image.open(paths["png"]) as im:
        assert im.size == (round(A0_INCHES[0] * DPI), round(A0_INCHES[1] * DPI))
    with Image.open(paths["tiff"]) as im:
        assert im.size[0] == pytest.approx(AXES_RECT[2] * A0_INCHES[0] * DPI, abs=2)
    px, _, _, neg_py, *_ = _tfw(paths["tiff"].replace(".tif", ".tfw"))
    assert px == pytest.approx(-neg_py, rel=0.01)                     # square pixels
    # ~2.2 km wide map (1 km radius + padding) over ~1.0 m of sheet => metres per pixel is small
    assert 0.5 < px < 10


@pytest.mark.parametrize("map_type", ["street", "transport", "landuse", "water", "buildings", "receptors"])
def test_every_osm_map_type_renders(live, tmp_path, map_type):
    res = generate_map("Peshawar", map_type=map_type, radius_km=1, dpi=20, outdir=str(tmp_path))
    assert os.path.getsize(res[0]["path"]) > 10_000


def test_receptors_overlay_and_exports(live, tmp_path):
    res = generate_map("Peshawar", map_type="receptors", pois="receptors", poi_data=True,
                       poi_formats=("csv", "summary"), radius_km=3, dpi=20, outdir=str(tmp_path))
    assert {r["format"] for r in res} >= {"png", "csv"}
    out = find_receptors("Peshawar", level="city", pois=["hospitals"])
    assert out["counts"]["hospitals"] > 0          # a city this size has mapped hospitals
    assert set(out["table"].columns) >= {"category", "name", "lon", "lat"}
    # coordinates must be near Peshawar (about 34.0N 71.5E)
    assert out["table"]["lat"].between(33.8, 34.2).all() and out["table"]["lon"].between(71.2, 71.8).all()


def test_district_is_clipped(live, tmp_path):
    res = generate_map("Peshawar", level="district", province="kpk", dpi=20, outdir=str(tmp_path))
    assert os.path.getsize(res[0]["path"]) > 10_000


def test_user_layers_geojson_and_csv(live, tmp_path):
    """Your own data: GeoJSON (point + line + polygon) and a CSV of points, with styles, drawn on a real map."""
    import json
    gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"NAME": "Site A"}, "geometry": {"type": "Point", "coordinates": [71.52, 34.01]}},
        {"type": "Feature", "properties": {"NAME": "Canal"}, "geometry": {"type": "LineString", "coordinates": [[71.50, 34.00], [71.55, 34.03]]}},
        {"type": "Feature", "properties": {"NAME": "Zone"}, "geometry": {"type": "Polygon", "coordinates": [[[71.50, 33.99], [71.54, 33.99], [71.54, 34.02], [71.50, 34.02], [71.50, 33.99]]]}}]}
    (tmp_path / "data.geojson").write_text(json.dumps(gj))
    (tmp_path / "pts.csv").write_text("name,lat,lon\nP1,34.005,71.51\nP2,34.012,71.53\n")
    res = generate_map("Peshawar", radius_km=3, dpi=20, outdir=str(tmp_path),
                       layers=[{"path": str(tmp_path / "data.geojson"), "color": "#1f77b4", "alpha": 0.4, "label_field": "NAME"},
                               {"path": str(tmp_path / "pts.csv"), "marker": "star", "size_mm": 9, "color": "#d62728"}],
                       layout={"elements": "all", "north_style": "compass", "scale_style": "double", "legend_style": "compact",
                               "labels": ["Peshawar centre@71.52,34.01;size=40;box=1"]})
    assert os.path.getsize(res[0]["path"]) > 10_000


def test_shapefile_roundtrip(live, tmp_path):
    import geopandas as gpd
    from shapely.geometry import Point
    gpd.GeoDataFrame({"NAME": ["a", "b"]}, geometry=[Point(71.5, 34.0), Point(71.52, 34.01)], crs=4326).to_file(tmp_path / "s.shp")
    res = generate_map("Peshawar", radius_km=3, dpi=20, outdir=str(tmp_path),
                       layers=[f"{tmp_path / 's.shp'};label_field=NAME;marker=triangle;color=#ff7f0e"])
    assert os.path.getsize(res[0]["path"]) > 10_000
