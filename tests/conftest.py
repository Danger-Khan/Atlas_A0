# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Shared test setup.

If osmnx / geopandas / shapely are not installed (e.g. a sandbox with no internet), light stand-ins are
registered so the pure logic (CLI, naming, geometry helpers, exports) can still be tested. Tests that need the
real libraries use the `real_gis` fixture and are skipped when stand-ins are active.
Live tests (real OpenStreetMap downloads) run only when ATLASA0_LIVE=1.
"""
import importlib.util
import os
import sys
import types

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _have(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


STUBBED = not (_have("osmnx") and _have("geopandas") and _have("shapely"))

if STUBBED:
    for m in ("osmnx", "geopandas", "shapely", "shapely.geometry"):
        sys.modules[m] = types.ModuleType(m)
    sys.modules["shapely.geometry"].box = lambda *a: None
    sys.modules["osmnx"].settings = types.SimpleNamespace()


@pytest.fixture
def real_gis():
    if STUBBED:
        pytest.skip("needs osmnx / geopandas / shapely (stand-ins active)")


@pytest.fixture
def live():
    if STUBBED or os.environ.get("ATLASA0_LIVE") != "1":
        pytest.skip("live test: set ATLASA0_LIVE=1 with osmnx/geopandas installed and internet access")


class FakeCRS:
    """Minimal stand-in for a pyproj CRS."""

    def to_wkt(self, version=None):
        return 'PROJCS["Test_UTM"]'


class _Geom:
    def __init__(self, x, y):
        self.x, self.y = pd.Series(x), pd.Series(y)


class FakePoiFrame:
    """Tiny stand-in for the GeoDataFrame of points returned by osm.get_pois (UTM metres)."""
    empty = False

    def __init__(self, x, y, category, name):
        self.geometry = _Geom(x, y)
        self._d = {"category": pd.Series(category), "name": pd.Series(name)}

    def __getitem__(self, k):
        return self._d[k]

    def to_crs(self, _):
        return FakePoiFrame(self.geometry.x / 1e5, self.geometry.y / 1e5,
                            self._d["category"], self._d["name"])

    def to_json(self):
        return '{"type": "FeatureCollection", "features": []}'


@pytest.fixture
def fake_poi():
    return FakePoiFrame([700000, 700500, 700900], [3700000, 3700100, 3700300],
                        ["hospitals", "schools", "schools"],
                        ["Lady Reading Hospital", "اسکول", "GHS 1"])


@pytest.fixture
def fake_crs():
    return FakeCRS()


@pytest.fixture(autouse=True)
def _private_stats(tmp_path, monkeypatch):
    """Size measurements go to a temp file during tests, never to the real ~/.atlasa0_stats.json."""
    monkeypatch.setenv("ATLASA0_STATS", str(tmp_path / "stats.json"))
