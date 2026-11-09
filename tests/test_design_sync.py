# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Keeps DESIGN.md and the code in step.

- Every colour in config.py (themes, land use, receptors) and the province tints in render.py must be a
  token in DESIGN.md, and every map token must still exist in the code (no stale tokens).
- DESIGN.md itself must lint clean (sections, valid hex, WCAG contrast of the declared pairs).
- The shipped package must not use a colour, font or padding that DESIGN.md does not describe.

Loads files by path, so it needs none of osmnx / geopandas / shapely and runs in the sandbox.
Fix a failure by changing config.py and DESIGN.md together (see skills/design-md/README.md).
"""
import importlib.util
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "skills", "design-md", "tools")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = mod            # designmd is imported by the other two tools
    spec.loader.exec_module(mod)
    return mod


dm = _load("designmd", os.path.join(TOOLS, "designmd.py"))
lint_design = _load("lint_design", os.path.join(TOOLS, "lint_design.py"))
check_adherence = _load("check_adherence", os.path.join(TOOLS, "check_adherence.py"))
config = _load("atlas_config_for_design_sync", os.path.join(ROOT, "atlasa0", "config.py"))

DESIGN = os.path.join(ROOT, "DESIGN.md")
SPEC = dm.load_spec(DESIGN)


def _hex(value):
    return dm.normalize_hex(value)


def _tokens(prefix):
    return {name: value for name, value in SPEC.colors.items() if name.startswith(prefix)}


def test_design_md_lints_clean():
    with open(DESIGN, encoding="utf-8") as fh:
        result = lint_design.lint(fh.read(), DESIGN)
    assert result["errors"] == []
    assert result["warnings"] == []


def test_theme_colours_match_tokens():
    for theme, values in config.THEMES.items():
        for key, value in values.items():
            token = "color.map-%s-%s" % (theme, key)
            if token not in SPEC.colors:                     # frame is an alias of text in both themes
                token = "color.map-%s-text" % theme
                assert key == "frame" and values["frame"] == values["text"], "missing token for %s.%s" % (theme, key)
            assert SPEC.colors[token] == _hex(value), "%s differs from config.THEMES[%r][%r]" % (token, theme, key)
    themes = {name.split("-")[1] for name in _tokens("color.map-")}
    assert themes == set(config.THEMES), "DESIGN.md has theme tokens the code does not (or the reverse)"


def test_landuse_colours_match_tokens():
    code = set(_hex(v) for v in config.LANDUSE_COLORS.values()) | {_hex(config.LANDUSE_OTHER)}
    tokens = set(_tokens("color.landuse-").values())
    assert code == tokens, "land-use colours differ: only in code %s, only in DESIGN.md %s" % (
        sorted(code - tokens), sorted(tokens - code))


def test_receptor_colours_match_tokens():
    code = {"color.poi-" + key.replace("_", "-"): _hex(d["color"]) for key, d in config.POI_CATEGORIES.items()}
    assert code == _tokens("color.poi-"), "receptor colours differ between config.POI_CATEGORIES and DESIGN.md"


def test_province_tints_match_tokens():
    with open(os.path.join(ROOT, "atlasa0", "render.py"), encoding="utf-8") as fh:
        text = fh.read()
    tints = re.findall(r'"(#[0-9a-fA-F]{6})"', re.search(r"PROVINCE_TINTS = \[(.*?)\]", text).group(1))
    assert [_hex(t) for t in tints] == [v for _, v in sorted(_tokens("color.province-tint-").items())]


def test_package_uses_only_documented_colours_fonts_and_padding():
    result = check_adherence.scan([os.path.join(ROOT, "atlasa0")], SPEC)
    assert result["files"] > 10
    assert result["findings"] == [], "\n".join(
        "%s:%s [%s] %s" % (f["file"], f["line"], f["kind"], f["message"]) for f in result["findings"])
