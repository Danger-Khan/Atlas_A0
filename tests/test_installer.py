# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Installer files: cannot be built on this PC, so check what can be checked - paths exist, versions and the licence
agree, installed-app folders are chosen so nothing is written under Program Files."""
import ast
import importlib.util
import os
import re

import pytest

from atlasa0 import __version__

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INST = os.path.join(ROOT, "installer")


def _read(*p):
    return open(os.path.join(*p), encoding="utf-8").read()


def _app_main():
    spec = importlib.util.spec_from_file_location("app_main", os.path.join(INST, "app_main.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_spec_is_valid_python_and_points_at_real_files():
    src = _read(INST, "atlasa0.spec")
    ast.parse(src)
    for rel in re.findall(r'os\.path\.join\(ROOT, ((?:"[^"]+"(?:, )?)+)\)', src):
        parts = re.findall(r'"([^"]+)"', rel)
        assert os.path.exists(os.path.join(ROOT, *parts)), parts
    assert "installer" in src and "app_main.py" in src and "console=False" in src
    assert os.path.isfile(os.path.join(ROOT, "atlasa0", "assets", "icons", "app.ico"))


def test_inno_script_shows_the_licence_and_matches_files():
    iss = _read(INST, "atlasa0.iss")
    assert "LicenseFile=..\\LICENSE" in iss and os.path.isfile(os.path.join(ROOT, "LICENSE"))
    assert "PolyForm" in _read(ROOT, "LICENSE")
    assert "PrivilegesRequired=lowest" in iss                       # no admin rights needed
    assert re.search(r'#define MyAppVersion "([\d.]+)"', iss).group(1) == __version__
    assert "dist\\AtlasA0" in iss and "AtlasA0.exe" in iss
    assert os.path.isfile(os.path.join(ROOT, "atlasa0", "assets", "icons", "app.ico"))


def test_build_script_runs_tests_then_pyinstaller_then_inno():
    bat = _read(INST, "build_windows.bat")
    assert bat.index("pytest") < bat.index("pyinstaller") < bat.index("ISCC")
    assert "installer\\atlasa0.spec" in bat and "installer\\atlasa0.iss" in bat
    assert os.path.isfile(os.path.join(INST, "requirements-build.txt"))
    assert "pyinstaller" in _read(INST, "requirements-build.txt").lower()


def test_installed_app_keeps_files_out_of_program_files(tmp_path):
    m = _app_main()
    env = {"LOCALAPPDATA": str(tmp_path / "Local")}
    got = m.default_dirs(env, home=str(tmp_path / "me"), frozen=True)
    assert got["ATLASA0_OUTDIR"] == os.path.join(str(tmp_path / "me"), "Documents", "AtlasA0", "output")
    assert got["ATLASA0_CACHE"] == os.path.join(str(tmp_path / "Local"), "AtlasA0", "cache")
    assert m.default_dirs(env, home="x", frozen=False) == {}              # from source: nothing changes
    env2 = {"ATLASA0_OUTDIR": "D:/maps"}
    assert "ATLASA0_OUTDIR" not in m.default_dirs(env2, home="x", frozen=True)   # your own setting wins
    m.apply_defaults(env2, home=str(tmp_path / "me"), frozen=True)
    assert env2["ATLASA0_OUTDIR"] == "D:/maps" and env2["ATLASA0_CACHE"]


def test_entry_sets_environment_before_importing_the_program():
    src = _read(INST, "app_main.py")
    body = src[src.index("def main"):]
    assert body.index("apply_defaults()") < body.index("from atlasa0.gui_tk import launch")
    assert "import atlasa0" not in src.split("def main")[0]                # nothing imports atlasa0 at module level
