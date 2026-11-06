# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Calibration of the numbers that decide how maps look on A0: extent fit, scale bar, markers, tile zoom."""
import math

import pytest

from atlasa0.config import A0_INCHES, AXES_RECT
from atlasa0.render import _basemap_zoom, axes_aspect, fit_extent, nice_scale_km, poi_marker_size


def test_a0_sheet_size_and_pixels():
    w_mm, h_mm = A0_INCHES[0] * 25.4, A0_INCHES[1] * 25.4
    assert w_mm == pytest.approx(841, abs=0.5) and h_mm == pytest.approx(1189, abs=0.5)
    assert round(A0_INCHES[0] * 300) == 9933 and round(A0_INCHES[1] * 300) == 14043
    assert round(A0_INCHES[0] * 200) == 6622 and round(A0_INCHES[1] * 200) == 9362


def test_axes_aspect_is_drawing_area_not_sheet():
    portrait = axes_aspect(A0_INCHES)
    assert portrait == pytest.approx((AXES_RECT[2] * 33.11) / (AXES_RECT[3] * 46.81))
    assert portrait == pytest.approx(0.7566, abs=1e-3)
    assert portrait > A0_INCHES[0] / A0_INCHES[1]  # wider than the sheet itself
    landscape = axes_aspect(A0_INCHES[::-1])
    assert landscape == pytest.approx((AXES_RECT[2] * 46.81) / (AXES_RECT[3] * 33.11))


@pytest.mark.parametrize("bounds", [(0, 0, 10000, 5000), (0, 0, 5000, 20000), (-300, 900, 700, 1100)])
@pytest.mark.parametrize("aspect", [0.7566, 1.2, 1.0])
def test_fit_extent_has_exact_aspect_is_centred_and_contains_bounds(bounds, aspect):
    x0, x1, y0, y1 = fit_extent(bounds, aspect, pad=1.08)
    assert (x1 - x0) / (y1 - y0) == pytest.approx(aspect, rel=1e-9)
    assert (x0 + x1) / 2 == pytest.approx((bounds[0] + bounds[2]) / 2)
    assert (y0 + y1) / 2 == pytest.approx((bounds[1] + bounds[3]) / 2)
    assert x0 <= bounds[0] and x1 >= bounds[2] and y0 <= bounds[1] and y1 >= bounds[3]


def test_fit_extent_radius_overrides_boundary_size():
    x0, x1, y0, y1 = fit_extent((0, 0, 50000, 50000), 1.0, pad=1.0, radius_km=5)
    assert x1 - x0 == pytest.approx(10000) and y1 - y0 == pytest.approx(10000)


def test_fit_extent_handles_a_single_point():
    x0, x1, y0, y1 = fit_extent((100, 100, 100, 100), 0.75)
    assert x1 > x0 and y1 > y0


@pytest.mark.parametrize("span_km,expected", [
    (2, 0.5), (10, 2), (20, 5), (30, 5), (40, 10), (80, 20), (200, 50), (1000, 200),
])
def test_scale_bar_is_a_nice_number(span_km, expected):
    assert nice_scale_km(span_km) == pytest.approx(expected)


@pytest.mark.parametrize("span_km", [0.5, 1, 3.3, 7, 12, 25, 99, 640, 1500])
def test_scale_bar_never_longer_than_quarter_and_is_1_2_5(span_km):
    bar = nice_scale_km(span_km)
    assert bar <= span_km / 4 + 1e-12
    mant = bar / 10 ** math.floor(math.log10(bar))
    assert round(mant, 6) in (1.0, 2.0, 5.0)


def test_poi_marker_size_calibration():
    _, d_small = poi_marker_size(5)
    _, d_10 = poi_marker_size(10)
    _, d_50 = poi_marker_size(50)
    _, d_100 = poi_marker_size(100)
    _, d_big = poi_marker_size(800)
    assert d_small == d_10 == pytest.approx(11.0)
    assert d_100 == d_big == pytest.approx(5.0)
    assert d_10 > d_50 > d_100  # shrinks as the area grows
    s, d = poi_marker_size(10)
    assert s == pytest.approx((11.0 * 72 / 25.4) ** 2)


def test_poi_marker_ground_size_is_sensible_on_a0():
    """11 mm marker on a 10 km wide city map is ~140 m on the ground (fine for a poster, not for surveying)."""
    map_mm = AXES_RECT[2] * A0_INCHES[0] * 25.4
    ground_m = 11.0 / map_mm * 10_000
    assert 100 < ground_m < 200


@pytest.mark.parametrize("width_m,lat,expected", [(10_000, 34, 17), (80_000, 34, 14), (500_000, 30, 11)])
def test_basemap_zoom_targets_about_10000_px(width_m, lat, expected):
    assert _basemap_zoom(width_m, lat, None) == expected


def test_basemap_zoom_explicit_and_clamped():
    assert _basemap_zoom(10_000, 34, 12) == 12
    assert _basemap_zoom(5_000_000, 30, None) == 8   # never below 8
    assert _basemap_zoom(500, 34, None) == 17        # never above 17
