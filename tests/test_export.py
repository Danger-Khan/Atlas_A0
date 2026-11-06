# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
import os

import matplotlib.pyplot as plt
import pytest
from PIL import Image

from atlasa0.config import A0_INCHES, AXES_RECT
from atlasa0.export import _save_geotiff, save_outputs, write_poi_files
from atlasa0.render import axes_aspect, fit_extent

DPI = 20  # A0 at 20 dpi = 662 x 936 px: real matplotlib code path, tiny files


def _a0_figure(bounds=(700000, 3700000, 710000, 3715000)):
    aspect = axes_aspect(A0_INCHES)
    ext = fit_extent(bounds, aspect, pad=1.08)
    fig = plt.figure(figsize=A0_INCHES, dpi=DPI, facecolor="white")
    ax = fig.add_axes(list(AXES_RECT))
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_aspect("equal")
    ax.plot([bounds[0], bounds[2]], [bounds[1], bounds[3]], lw=2)
    return fig, ax, ext


def _read_tfw(path):
    return [float(v) for v in open(path).read().split()]


def test_map_fills_the_frame_after_fit_extent():
    """Calibration: with the extent fitted to the drawing area there are no blank bands inside the frame."""
    fig, ax, ext = _a0_figure()
    ax.apply_aspect()
    pos = ax.get_position()
    assert pos.width == pytest.approx(AXES_RECT[2], rel=1e-6)
    assert pos.height == pytest.approx(AXES_RECT[3], rel=1e-6)
    plt.close(fig)


def test_geotiff_is_georeferenced_with_square_pixels(tmp_path, fake_crs):
    fig, ax, ext = _a0_figure()
    path = str(tmp_path / "t.tif")
    _save_geotiff(fig, ax, path, DPI, fake_crs, ext, "white")
    plt.close(fig)

    with Image.open(path) as im:
        w, h = im.size
        assert im.mode == "RGB"
    # size = map area only (no title/margins): 92% x 86% of the sheet
    assert w == pytest.approx(AXES_RECT[2] * A0_INCHES[0] * DPI, abs=2)
    assert h == pytest.approx(AXES_RECT[3] * A0_INCHES[1] * DPI, abs=2)

    px, rot1, rot2, neg_py, x_ul, y_ul = _read_tfw(str(tmp_path / "t.tfw"))
    assert rot1 == 0 and rot2 == 0 and neg_py < 0
    assert px == pytest.approx(-neg_py, rel=0.01)                      # square pixels
    assert w * px == pytest.approx(ext[1] - ext[0], rel=0.01)          # raster width = ground width
    assert h * -neg_py == pytest.approx(ext[3] - ext[2], rel=0.01)
    assert x_ul == pytest.approx(ext[0] + px / 2, abs=px)              # upper-left pixel centre
    assert y_ul == pytest.approx(ext[3] + neg_py / 2, abs=-neg_py)
    assert open(str(tmp_path / "t.prj")).read().startswith("PROJCS")


def test_geotiff_pixel_size_matches_dpi_and_scale(tmp_path, fake_crs):
    """10 km wide city on A0 at 20 dpi: metres per pixel must equal ground width / pixel width."""
    fig, ax, ext = _a0_figure()
    path = str(tmp_path / "t.tif")
    _save_geotiff(fig, ax, path, DPI, fake_crs, ext, "white")
    plt.close(fig)
    px = _read_tfw(str(tmp_path / "t.tfw"))[0]
    expected = (ext[1] - ext[0]) / (AXES_RECT[2] * A0_INCHES[0] * DPI)
    assert px == pytest.approx(expected, rel=0.01)


def test_save_outputs_png_and_tiff(tmp_path, fake_crs):
    fig, ax, ext = _a0_figure()
    out = str(tmp_path / "city_A0.png")
    paths = save_outputs(fig, ax, out, DPI, ("png", "tiff"), fake_crs, ext, "white", "test")
    assert sorted(os.path.basename(p) for p in paths) == ["city_A0.png", "city_A0.tif"]
    for ext_ in (".png", ".tif", ".tfw", ".prj"):
        assert (tmp_path / f"city_A0{ext_}").exists()
    with Image.open(out) as im:  # full poster is the whole sheet
        assert im.size == (round(A0_INCHES[0] * DPI), round(A0_INCHES[1] * DPI))


def test_save_outputs_accepts_aliases_and_png_only(tmp_path, fake_crs):
    fig, ax, ext = _a0_figure()
    paths = save_outputs(fig, ax, str(tmp_path / "a.png"), DPI, ("PNG",), fake_crs, ext, "white", "t")
    assert [os.path.basename(p) for p in paths] == ["a.png"]
    assert not (tmp_path / "a.tif").exists()
    fig, ax, ext = _a0_figure()
    paths = save_outputs(fig, ax, str(tmp_path / "b.png"), DPI, ("geotiff",), fake_crs, ext, "white", "t")
    assert [os.path.basename(p) for p in paths] == ["b.tif"]


# ------------------------------------------------------------------ receptor files
def test_poi_csv_and_geojson(tmp_path, fake_poi):
    out = write_poi_files(fake_poi, str(tmp_path / "x"), ("csv", "geojson"))
    assert sorted(os.path.basename(p) for p in out) == ["x_poi.csv", "x_poi.geojson"]
    text = open(out[0] if out[0].endswith(".csv") else out[1], encoding="utf-8-sig").read()
    assert text.splitlines()[0] == "category,name,lon,lat,x_utm,y_utm"
    assert "Lady Reading Hospital" in text and "اسکول" in text  # Urdu survives
    raw = open(str(tmp_path / "x_poi.csv"), "rb").read()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM so Excel opens UTF-8


def test_poi_summary_includes_zero_counts_and_total(tmp_path, fake_poi):
    out = write_poi_files(fake_poi, str(tmp_path / "x"), ("summary",),
                          counts={"hospitals": 1, "schools": 2, "worship": 0})
    assert [os.path.basename(p) for p in out] == ["x_poi_summary.csv"]
    lines = open(out[0], encoding="utf-8-sig").read().splitlines()
    assert lines[0] == "category,label,count"
    assert "worship,Places of worship,0" in lines
    assert lines[-1] == "TOTAL,,3"


def test_poi_xlsx_has_two_sheets(tmp_path, fake_poi):
    openpyxl = pytest.importorskip("openpyxl")
    out = write_poi_files(fake_poi, str(tmp_path / "x"), ("xlsx",))
    wb = openpyxl.load_workbook(out[0])
    assert wb.sheetnames == ["Receptors", "Summary"]
    assert wb["Receptors"].max_row == 4 and wb["Summary"].max_row == 4  # header + 3 / header + 2 + total
    assert wb["Receptors"].freeze_panes == "A2"


def test_poi_unknown_format_and_empty(tmp_path, fake_poi):
    with pytest.raises(ValueError):
        write_poi_files(fake_poi, str(tmp_path / "x"), ("pdf",))
    assert write_poi_files(None, str(tmp_path / "x")) == []
    assert write_poi_files(fake_poi, str(tmp_path / "x"), ()) == []


def test_stray_axis_titles_are_removed(tmp_path, fake_crs):
    fig, ax, ext = _a0_figure()
    ax.set_xlabel("Easting (metre)")
    ax.set_ylabel("Northing (metre)")
    save_outputs(fig, ax, str(tmp_path / "c.png"), DPI, ("png",), fake_crs, ext, "white", "t")
    assert ax.get_xlabel() == "" and ax.get_ylabel() == ""
