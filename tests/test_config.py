# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
import os
import re

import pytest

from atlasa0 import config
from atlasa0.config import (FORMAT_ALIASES, MAP_TYPES, POI_CATEGORIES, POI_FILE_SUFFIX, POI_PRESETS,
                            PROVINCES, match_province, resolve_pois)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_resolve_pois_categories_and_presets_dedupe():
    keys = resolve_pois(["receptors", "fuel", "hospitals"])
    assert keys == POI_PRESETS["receptors"] + ["fuel"]
    assert len(keys) == len(set(keys))


def test_resolve_pois_accepts_string_and_empty():
    assert resolve_pois("health") == POI_PRESETS["health"]
    assert resolve_pois(None) == []
    assert resolve_pois([]) == []


def test_resolve_pois_all_covers_every_category():
    assert set(resolve_pois("all")) == set(POI_CATEGORIES)


def test_resolve_pois_unknown_lists_options():
    with pytest.raises(ValueError) as e:
        resolve_pois(["zoo"])
    assert "hospitals" in str(e.value) and "receptors" in str(e.value)


def test_presets_only_reference_valid_categories():
    for name, keys in POI_PRESETS.items():
        assert set(keys) <= set(POI_CATEGORIES), name


def test_every_category_is_complete():
    for k, c in POI_CATEGORIES.items():
        assert c["label"] and isinstance(c["tags"], dict) and c["tags"], k
        assert re.fullmatch(r"#[0-9a-fA-F]{6}", c["color"]), k
        assert c["marker"], k


@pytest.mark.parametrize("alias,expected", [
    ("kpk", "Khyber Pakhtunkhwa"), ("KP", "Khyber Pakhtunkhwa"), ("gb", "Gilgit-Baltistan"),
    ("ajk", "Azad Kashmir"), ("ict", "Islamabad"), ("Baluchistan", "Balochistan"),
    ("punjab", "Punjab"), ("Gilgit Baltistan", "Gilgit-Baltistan"),
])
def test_match_province(alias, expected):
    assert match_province(alias) == expected


def test_match_province_unknown_exits_with_hint():
    with pytest.raises(SystemExit) as e:
        match_province("narnia")
    assert "--list" in str(e.value)


def test_provinces_and_queries_are_consistent():
    assert set(PROVINCES) == set(config.PROVINCE_QUERY)
    assert all(PROVINCES[p] for p in PROVINCES)  # each has preset cities


def test_formats_and_poi_file_types():
    assert set(FORMAT_ALIASES.values()) == {"png", "tiff"}
    assert set(POI_FILE_SUFFIX) == {"csv", "geojson", "xlsx", "summary"}


def test_every_map_type_has_a_render_branch():
    src = open(os.path.join(ROOT, "atlasa0", "render.py"), encoding="utf-8").read()
    for mt in MAP_TYPES:
        assert f'"{mt}"' in src, f"map type '{mt}' is not handled in render.py"
