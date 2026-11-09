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


def test_cache_dir_defaults_to_cache_inside_the_atlas_folder_not_the_cwd(tmp_path, monkeypatch):
    """The cache lives in <AtlasA0 folder>/cache whatever folder Python was started from (was: relative 'cache',
    which gave [WinError 5] Access is denied in protected folders)."""
    import os
    from atlasa0 import config
    protected = tmp_path / "System32"
    protected.mkdir()
    monkeypatch.chdir(protected)
    root = tmp_path / "AtlasAO"
    root.mkdir()
    d = config.cache_dir(env={}, root=str(root), platform="win32")
    assert d == str(root / "cache") and os.path.isdir(d)
    assert not os.path.exists(protected / "cache")


def test_cache_dir_falls_back_when_the_atlas_folder_is_read_only(tmp_path, monkeypatch):
    import os
    from atlasa0 import config
    root = tmp_path / "ro"
    root.mkdir()
    real = config._writable_dir
    monkeypatch.setattr(config, "_writable_dir", lambda p: False if p.startswith(str(root)) else real(p))
    env = {"LOCALAPPDATA": str(tmp_path / "local")}
    d = config.cache_dir(env=env, root=str(root), platform="win32")
    assert d == str(tmp_path / "local" / "AtlasA0" / "cache") and os.path.isabs(d)


def test_cache_dir_order_env_first_and_user_folder_when_installed_as_package(tmp_path, monkeypatch):
    import os
    from atlasa0 import config
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    env = {"ATLASA0_CACHE": str(tmp_path / "mine")}
    assert config.cache_dir(env=env, root=str(tmp_path), platform="linux") == str(tmp_path / "mine")
    got = config.cache_dir(env={"XDG_CACHE_HOME": str(tmp_path / "xdg")}, root=None, platform="linux")
    assert got == str(tmp_path / "xdg" / "atlasa0")
    assert os.path.isabs(config.cache_dir(env={}, root=None, platform="darwin"))


def test_project_dir_is_the_folder_with_run_gui():
    import os
    from atlasa0 import config
    root = config.project_dir()
    assert root and os.path.isfile(os.path.join(root, "run_gui.py"))


def test_diagnostics_line_names_version_cache_and_code_folder():
    from atlasa0 import __version__, config
    line = config.diagnostics()
    assert __version__ in line and "cache:" in line and "code:" in line
