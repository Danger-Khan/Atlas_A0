# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Release files exist, carry the author line, and stay in step (version, licence, name-template safety)."""
import os
import re
import tomllib

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTHOR = "Imaad Ullah Khan Yameen"
REQUIRED = ["LICENSE", "NOTICE", "TERMS.md", "PRIVACY.md", "SECURITY.md", "REVIEW.md", "CONTRIBUTING.md",
            "CODE_OF_CONDUCT.md", "README.md", "architecture.md", "requirements.md", "requirements.txt",
            "requirements-dev.txt", "pyproject.toml", "policy.json", "launch.sh", "launch.bat",
            ".github/workflows/ci.yml", ".github/PULL_REQUEST_TEMPLATE.md", ".github/dependabot.yml"]
EXT = (".py", ".md", ".bat", ".sh", ".iss", ".spec", ".yml", ".yaml", ".txt", ".toml")
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", "assets", ".venv", "build", "dist"}


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


@pytest.mark.parametrize("rel", REQUIRED)
def test_required_file_exists(rel):
    assert os.path.isfile(os.path.join(ROOT, rel)), rel


def test_every_code_and_doc_file_names_the_author():
    missing = []
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for n in files:
            if n.endswith(EXT) and n != "LICENSE" and not n.endswith(".egg-info"):
                p = os.path.join(d, n)
                with open(p, encoding="utf-8", errors="ignore") as f:
                    if AUTHOR not in f.read(800):
                        missing.append(os.path.relpath(p, ROOT))
    assert not missing, missing


def test_pyproject_version_matches_package():
    cfg = tomllib.loads(_read("pyproject.toml"))
    pkg = re.search(r'__version__ = "([^"]+)"', _read("atlasa0/__init__.py")).group(1)
    assert cfg["project"]["version"] == pkg
    assert cfg["project"]["authors"][0]["name"] == AUTHOR
    assert cfg["project"]["scripts"]["atlasa0"] == "atlasa0.cli:main"


def test_entry_points_exist():
    import atlasa0.cli
    assert callable(atlasa0.cli.main)
    assert "def launch" in _read("atlasa0/gui_tk.py")


def test_legal_files_state_noncommercial_and_not_for_sale():
    for rel in ("TERMS.md", "NOTICE", "README.md"):
        t = _read(rel).lower()
        assert "not for sale" in t, rel
    assert "noncommercial" in _read("TERMS.md").lower()
    assert "patent" in _read("NOTICE").lower()


def test_launchers_are_cross_platform():
    sh = _read("launch.sh")
    assert sh.startswith("#!/usr/bin/env bash") and "set -euo pipefail" in sh
    assert os.access(os.path.join(ROOT, "launch.sh"), os.X_OK)
    assert "run_gui.py" in _read("launch.bat")


def test_ci_covers_three_systems():
    ci = _read(".github/workflows/ci.yml")
    for osn in ("ubuntu-latest", "windows-latest", "macos-latest"):
        assert osn in ci
    assert "permissions:" in ci


@pytest.mark.parametrize("bad", ["{region.__class__}", "{region[0]}", "{region!r}", "{region:>20}"])
def test_name_template_rejects_attribute_and_format_tricks(bad):
    from atlasa0.config import file_stem
    with pytest.raises(ValueError):
        file_stem(bad, region="x")


def test_name_template_still_works():
    from atlasa0.config import file_stem
    assert file_stem("Map_{region}_{dpi}", region="Peshawar", dpi=300) == "Map_Peshawar_300"


def test_decompression_limit_restored_after_geotiff():
    from PIL import Image
    before = Image.MAX_IMAGE_PIXELS
    from atlasa0 import export
    class Boom(Exception):
        pass
    def inner(*a, **k):
        assert Image.MAX_IMAGE_PIXELS is None
        raise Boom
    orig = export._save_geotiff_inner
    export._save_geotiff_inner = inner
    try:
        with pytest.raises(Boom):
            export._save_geotiff(None, None, "x.tif", 100, None, None, "w")
    finally:
        export._save_geotiff_inner = orig
    assert Image.MAX_IMAGE_PIXELS == before
