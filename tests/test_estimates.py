# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Download / file-size estimates, DPI range and learning from real runs."""
import pytest

from atlasa0 import estimates as est
from atlasa0 import gui_core as core


def test_dpi_range_is_50_to_500():
    assert (est.DPI_MIN, est.DPI_MAX) == (50, 500)
    assert core.validate(core.FormState(cities=["A"], dpi=500)) == []
    assert any("500" in p for p in core.validate(core.FormState(cities=["A"], dpi=550)))
    assert est.sheet_pixels(500) == (16555, 23405)


def test_file_size_grows_slower_than_pixels_for_line_maps():
    png100, m = est.file_mb("street", "png", 100)
    png500, _ = est.file_mb("street", "png", 500)
    assert not m and png500 / png100 == pytest.approx(5 ** 1.4, rel=0.01)        # not 25x
    sat = est.file_mb("satellite", "png", 500)[0] / est.file_mb("satellite", "png", 100)[0]
    assert sat == pytest.approx(25, rel=0.01)                                    # photos: pixel count
    tif, png = est.file_mb("street", "tiff", 300)[0], est.file_mb("street", "png", 300)[0]
    assert tif == pytest.approx(png * est.MAP_AREA_FRACTION * est.TIFF_VS_PNG, rel=0.01)
    assert est.file_mb("water", "png", 300)[0] < png                             # sparse maps are smaller


def test_measurements_replace_guesses(tmp_path):
    f = tmp_path / "a.png"
    f.write_bytes(b"x" * 20_000_000)                       # a real 20 MB street PNG at 300 dpi
    est.record_file("street", "png", str(f), 300)
    mb, measured = est.file_mb("street", "png", 300)
    assert measured and mb == pytest.approx(20, rel=0.01)
    assert est.file_mb("street", "png", 500)[0] == pytest.approx(20 * (5 / 3) ** 1.4, rel=0.01)
    est.record_download("city", "street", 0.0)              # cached run: ignored
    assert est.download_mb("city", "street")[1] is False
    for v in (10, 12, 300):                                  # median ignores the odd one
        est.record_download("city", "street", v)
    assert est.download_mb("city", "street") == (12, True)


def test_run_totals_and_text():
    s = core.FormState(cities=["Peshawar"], map_types=["street", "water"], formats=["png", "tiff"], dpi=300)
    e = core.estimate(s)
    assert e["maps"] == 2 and e["download_mb"] == est.DOWNLOAD_MB["street"] + est.DOWNLOAD_MB["water"]
    assert e["files_mb"] > 0 and not e["files_measured"]
    t = core.estimate_text(e)
    assert "Download about" in t and "rough guess" in t
    p = core.estimate(core.FormState(provinces=["kpk"], country=True))
    assert p["download_mb"] == est.DOWNLOAD_MB_FIXED["province"] + est.DOWNLOAD_MB_FIXED["country"]
    assert "Choose something" in core.estimate_text(core.estimate(core.FormState()))


def test_high_dpi_warns_about_ram():
    png_only = core.estimate(core.FormState(cities=["A"], dpi=500))
    with_tiff = core.estimate(core.FormState(cities=["A"], dpi=500, formats=["png", "tiff"]))
    assert 2.5 < png_only["ram_gb"] < 4 and with_tiff["ram_gb"] > 6
    assert any("RAM" in w for w in with_tiff["warnings"])
    assert not core.estimate(core.FormState(cities=["A"], dpi=100))["warnings"]


def test_dpi_label():
    assert est.dpi_label(100).endswith("screen preview") and est.dpi_label(500).endswith("maximum detail")
