# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
import numpy as np
import matplotlib.pyplot as plt
import pytest
from matplotlib.collections import LineCollection, PatchCollection

from atlasa0 import layers as L
from atlasa0.config import THEMES

T = THEMES["light"]


# --- duck-typed stand-ins for shapely geometries (shapely is not needed to test drawing)
class Pt:
    geom_type, is_empty = "Point", False
    def __init__(self, x, y): self.coords = [(x, y)]

class Ln:
    geom_type, is_empty = "LineString", False
    def __init__(self, pts): self.coords = pts

class Ring:
    def __init__(self, pts): self.coords = pts

class Poly:
    geom_type, is_empty = "Polygon", False
    def __init__(self, ext, holes=()): self.exterior, self.interiors = Ring(ext), [Ring(h) for h in holes]

class Multi:
    is_empty = False
    def __init__(self, kind, geoms): self.geom_type, self.geoms = kind, geoms


@pytest.fixture
def shp(tmp_path):
    p = tmp_path / "sites.shp"
    p.write_bytes(b"x")
    return str(p)


def spec(shp, **kw):
    return L.LayerSpec.from_any({"path": shp, **kw})


# ------------------------------------------------------------------ spec
def test_spec_defaults_and_label(shp):
    s = spec(shp)
    assert s.label == "sites" and s.marker == "circle" and s.alpha is None
    assert spec(shp, name="Proposed sites").label == "Proposed sites"


@pytest.mark.parametrize("kw", [
    {"color": "not-a-colour"}, {"alpha": 1.5}, {"alpha": -0.1}, {"marker": "banana"}, {"line_style": "wavy"},
    {"hatch": "zebra"}, {"size_mm": 0}, {"width_mm": -1}, {"bogus": 1}, {"edge_color": "zzz"},
])
def test_spec_rejects_bad_values(shp, kw):
    with pytest.raises(ValueError):
        spec(shp, **kw)


def test_spec_file_checks(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        L.LayerSpec.from_any({"path": str(tmp_path / "missing.shp")})
    (tmp_path / "a.xyz").write_text("x")
    with pytest.raises(ValueError, match="unsupported"):
        L.LayerSpec.from_any({"path": str(tmp_path / "a.xyz")})


def test_parse_layer_spec_string(shp):
    s = L.parse_layer_spec(f"{shp};name=My sites;color=#2ca02c;alpha=0.5;marker=star;size_mm=9;label_field=NAME;fit=1;label-halo=0")
    assert (s.name, s.color, s.alpha, s.marker, s.size_mm, s.label_field, s.fit, s.label_halo) == \
           ("My sites", "#2ca02c", 0.5, "star", 9.0, "NAME", True, False)
    with pytest.raises(ValueError):
        L.parse_layer_spec(f"{shp};colour")
    with pytest.raises(ValueError):
        L.parse_layer_spec("")


def test_layers_to_dicts_keeps_only_changes(shp):
    d = L.layers_to_dicts([spec(shp, color="#000000", alpha=0.3)])
    assert d == [{"path": shp, "color": "#000000", "alpha": 0.3}]
    assert L.parse_layers(d)[0].alpha == 0.3


# ------------------------------------------------------------------ features
def test_flatten_all_geometry_types():
    f = L.flatten(Pt(1, 2), "a")[0]
    assert f.kind == "point" and f.parts == [(1.0, 2.0)] and f.label == "a"
    f = L.flatten(Ln([(0, 0), (2, 0), (4, 0)]))[0]
    assert f.kind == "line" and f.label_xy == (2.0, 0.0)
    f = L.flatten(Poly([(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)], holes=[[(1, 1), (2, 1), (2, 2), (1, 1)]]))[0]
    assert f.kind == "polygon" and len(f.parts[0][1]) == 1
    assert f.label_xy == pytest.approx((2.0, 2.0))
    mp = L.flatten(Multi("MultiPoint", [Pt(0, 0), Pt(1, 1)]), "m")
    assert len(mp) == 2 and all(x.label == "m" for x in mp)
    assert L.flatten(Multi("GeometryCollection", [Pt(0, 0), Ln([(0, 0), (1, 1)])]))[1].kind == "line"


def test_prepare_skips_empty_and_counts(shp):
    class Empty: is_empty, geom_type = True, "Point"
    p = L.prepare_features([Pt(0, 0), None, Empty(), Ln([(0, 0), (1, 1)])], ["a", "b", "c", None], spec(shp))
    assert p.count == 2 and p.kinds() == {"point": 1, "line": 1} and p.bounds == (0, 0, 1, 1)


def test_layers_bounds_only_fit_layers(shp):
    a = L.prepare_features([Pt(0, 0)], [""], spec(shp, fit=True))
    b = L.prepare_features([Pt(100, 100)], [""], spec(shp))
    assert L.layers_bounds([a, b]) == (0, 0, 0, 0)
    assert L.layers_bounds([a, b], fit_only=False) == (0, 0, 100, 100)
    assert L.layers_bounds([b]) is None


# ------------------------------------------------------------------ drawing
def fig_ax():
    fig, ax = plt.subplots(figsize=(4, 4), dpi=50)
    ax.set_xlim(-5, 15); ax.set_ylim(-5, 15)
    return fig, ax


def test_points_use_colour_alpha_marker_and_size(shp):
    fig, ax = fig_ax()
    p = L.prepare_features([Pt(1, 1), Pt(2, 2)], ["A", "B"], spec(shp, color="#ff0000", alpha=0.4, marker="triangle",
                                                                    size_mm=10, label_field="NAME"))
    h = L.draw_layers(ax, [p], T)
    sc = ax.collections[0]
    assert tuple(sc.get_facecolor()[0]) == pytest.approx((1, 0, 0, 0.4))
    assert sc.get_sizes()[0] == pytest.approx((10 * L.MM) ** 2)
    assert len(h) == 1 and h[0].get_marker() == "^" and h[0].get_label() == "sites"
    assert sorted(t.get_text() for t in ax.texts) == ["A", "B"]
    plt.close(fig)


def test_hollow_marker_has_no_fill(shp):
    fig, ax = fig_ax()
    L.draw_layers(ax, [L.prepare_features([Pt(1, 1)], [""], spec(shp, marker="ring", color="#0000ff"))], T)
    assert ax.collections[0].get_facecolor().shape[0] == 0 or ax.collections[0].get_facecolor()[0][3] == 0
    plt.close(fig)


def test_lines_style_width_alpha(shp):
    fig, ax = fig_ax()
    p = L.prepare_features([Ln([(0, 0), (5, 5)])], [""], spec(shp, color="#00ff00", alpha=0.5, line_style="dashed", width_mm=2))
    h = L.draw_layers(ax, [p], T)
    lc = [c for c in ax.collections if isinstance(c, LineCollection)][0]
    assert lc.get_linewidths()[0] == pytest.approx(2 * L.MM)
    assert tuple(lc.get_colors()[0]) == pytest.approx((0, 1, 0, 0.5))
    assert h[0].get_linestyle() == "--"
    plt.close(fig)


def test_polygons_default_transparent_hatch_and_holes(shp):
    fig, ax = fig_ax()
    sq = Poly([(0, 0), (8, 0), (8, 8), (0, 8), (0, 0)], holes=[[(2, 2), (4, 2), (4, 4), (2, 4), (2, 2)]])
    p = L.prepare_features([sq], [""], spec(shp, color="#0000ff", hatch="diagonal"))
    h = L.draw_layers(ax, [p], T)
    pc = [c for c in ax.collections if isinstance(c, PatchCollection)][0]
    assert pc.get_facecolor()[0][3] == pytest.approx(0.4)          # polygons are see-through by default
    assert pc.get_hatch() == "///" and h[0].get_hatch() == "///"
    plt.close(fig)


@pytest.mark.parametrize("flip", [False, True])
def test_hole_is_really_empty_whatever_the_ring_direction(shp, flip):
    """Rasterise and look at pixels: shapefiles and GeoJSON disagree on ring direction, the hole must still show."""
    outer = [(0, 0), (8, 0), (8, 8), (0, 8), (0, 0)]
    hole = [(2, 2), (6, 2), (6, 6), (2, 6), (2, 2)]
    if flip:
        outer, hole = outer[::-1], hole[::-1]
    fig, ax = fig_ax()
    ax.set_xlim(-1, 9); ax.set_ylim(-1, 9)
    L.draw_layers(ax, [L.prepare_features([Poly(outer, [hole])], [""], spec(shp, color="#ff0000", alpha=1.0))], T)
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())
    def px(x, y):
        X, Y = ax.transData.transform((x, y))
        return img[img.shape[0] - 1 - int(Y), int(X)][:3]
    assert tuple(px(1, 1)) == (255, 0, 0)             # inside the ring: solid
    assert tuple(px(4, 4)) == (255, 255, 255)         # inside the hole: background
    plt.close(fig)


def test_explicit_alpha_and_zero_alpha(shp):
    fig, ax = fig_ax()
    sq = Poly([(0, 0), (8, 0), (8, 8), (0, 0)])
    L.draw_layers(ax, [L.prepare_features([sq], [""], spec(shp, alpha=0.0))], T)
    assert [c for c in ax.collections if isinstance(c, PatchCollection)][0].get_facecolor()[0][3] == 0
    plt.close(fig)


def test_legend_flag_and_order(shp):
    fig, ax = fig_ax()
    a = L.prepare_features([Pt(0, 0)], [""], spec(shp, name="A"))
    b = L.prepare_features([Pt(1, 1)], [""], spec(shp, name="B", legend=False))
    c = L.prepare_features([Ln([(0, 0), (1, 1)])], [""], spec(shp, name="C"))
    assert [h.get_label() for h in L.draw_layers(ax, [a, b, c], T)] == ["A", "C"]
    assert ax.collections[0].get_zorder() < ax.collections[-1].get_zorder()    # later layers on top
    plt.close(fig)


def test_mixed_layer_legend_uses_dominant_kind(shp):
    fig, ax = fig_ax()
    p = L.prepare_features([Pt(0, 0), Pt(1, 1), Ln([(0, 0), (1, 1)])], ["", "", ""], spec(shp))
    assert L.draw_layers(ax, [p], T)[0].get_marker() == "o"
    plt.close(fig)


def test_loader_needs_geopandas_or_works(shp, real_gis):
    pass  # live behaviour is covered in tests/test_live.py (needs geopandas)
