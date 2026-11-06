# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
import os

import matplotlib.pyplot as plt
import pytest
from PIL import Image

from atlasa0.config import A0_INCHES, AXES_RECT, THEMES
from atlasa0.export import save_outputs
from atlasa0.furniture import (DEFAULT_ELEMENTS, ELEMENTS, Layout, apply_layout, nice_grid_step_km,
                               parse_legend_item, print_scale_ratio, resolve_elements)
from atlasa0.render import axes_aspect, fit_extent

DPI = 20
T = THEMES["light"]


def test_resolve_elements():
    assert resolve_elements(None) == list(DEFAULT_ELEMENTS)
    assert resolve_elements("none") == [] and resolve_elements(["ALL"]) == list(ELEMENTS)
    assert resolve_elements(["scale", "scale", "north"]) == ["scale", "north"]
    with pytest.raises(ValueError):
        resolve_elements(["legned"])


def test_parse_legend_item():
    assert parse_legend_item("Proposed site=#d62728") == ("Proposed site", "#d62728")
    assert parse_legend_item("a=b=red") == ("a=b", "red")
    for bad in ("nocolour", "=#fff", "x=#12"):
        with pytest.raises(ValueError):
            parse_legend_item(bad)


def test_layout_from_dict_validates(tmp_path):
    lay = Layout.from_any({"elements": ["scale"], "legend_items": ["A=#fff", ["B", "#000"]], "grid_km": 5})
    assert lay.elements == ["scale"] and lay.legend_items == [("A", "#fff"), ("B", "#000")] and lay.grid_km == 5
    assert Layout.from_any(None).elements == list(DEFAULT_ELEMENTS)
    for bad in ({"bogus": 1}, {"legend_pos": "nowhere"}, {"logo": str(tmp_path / "no.png")}, {"grid_km": 0}):
        with pytest.raises(ValueError):
            Layout.from_any(bad)


def test_print_scale_ratio_and_grid_step():
    # 10 km city extent across the 92%-wide drawing area of A0 (about 0.77 m) -> about 1:13,000
    r = print_scale_ratio(10_000, A0_INCHES[0])
    assert 12_000 < r < 14_000 and r % 100 == 0
    assert nice_grid_step_km(30) == 5 and nice_grid_step_km(10) == 2 and nice_grid_step_km(1000) == 200


def _fig(bounds=(700000, 3700000, 710000, 3715000)):
    ext = fit_extent(bounds, axes_aspect(A0_INCHES), 1.08)
    fig = plt.figure(figsize=A0_INCHES, dpi=DPI, facecolor=T["bg"])
    ax = fig.add_axes(list(AXES_RECT))
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal")
    return fig, ax, ext


def _draw(lay, fig, ax, ext, land=(("residential", "#ccc"),)):
    apply_layout(fig, ax, ext, T, A0_INCHES, None, Layout.from_any(lay), title="TOWN", subtitle="SUB",
                 credit="credit", y_title=0.95, y_sub=0.9, y_credit=0.02, land_entries=land)


def test_all_elements_draw_and_save(tmp_path, fake_crs):
    logo = tmp_path / "logo.png"
    Image.new("RGB", (200, 100), "red").save(logo)
    fig, ax, ext = _fig()
    _draw({"elements": "all", "legend_items": ["Site=#d62728"], "note": "Draft - for discussion " * 5,
           "logo": str(logo), "grid_km": 2}, fig, ax, ext)
    texts = [t.get_text() for t in fig.findobj(plt.Text)]
    assert {"TOWN", "N", "0", "credit"} <= {t.split("  |  ")[0] for t in texts}
    assert any(t.startswith("Scale 1:") for t in texts)
    assert any("Grid" in t for t in texts)
    assert any("Draft" in t for t in texts)
    out = str(tmp_path / "m.png")
    paths = save_outputs(fig, ax, out, DPI, ("png", "tiff"), fake_crs, ext, T["bg"], "t")
    assert all(os.path.getsize(p) > 0 for p in paths)


def test_none_draws_nothing_but_extras(fake_crs):
    fig, ax, ext = _fig()
    _draw({"elements": "none"}, fig, ax, ext)
    texts = [t.get_text() for t in fig.findobj(plt.Text) if t.get_text()]
    assert texts == []
    assert getattr(fig, "_atlasa0_furniture", []) == []


def test_title_and_subtitle_override():
    fig, ax, ext = _fig()
    _draw({"elements": ["title"], "title": "My Title", "subtitle": ""}, fig, ax, ext)
    texts = [t.get_text() for t in fig.findobj(plt.Text)]
    assert "My Title" in texts and "TOWN" not in texts and "SUB" not in texts


def test_custom_legend_items_listed_with_land_use():
    fig, ax, ext = _fig()
    _draw({"elements": ["legend"], "legend_items": ["Proposed site=#d62728"]}, fig, ax, ext)
    texts = [t.get_text() for t in fig.findobj(plt.Text)]
    assert "Residential" in texts and "Proposed site" in texts and "LEGEND" in texts


def test_geotiff_stays_clean_by_default_and_pixels_differ_when_requested(tmp_path, fake_crs):
    def make(tiff_furniture, name):
        fig, ax, ext = _fig()
        _draw({"elements": ["legend", "scale", "north"], "tiff_furniture": tiff_furniture}, fig, ax, ext)
        p = save_outputs(fig, ax, str(tmp_path / name), DPI, ("tiff",), fake_crs, ext, T["bg"], "t",
                         tiff_furniture=tiff_furniture)[0]
        return Image.open(p).convert("L").tobytes()
    clean, full = make(False, "a.png"), make(True, "b.png")
    flat = lambda b: max(b.count(v) for v in set(b)) / len(b)
    assert flat(clean) > 0.98             # nothing drawn: one flat background value (bar the frame line)
    assert flat(full) < flat(clean) and clean != full   # with furniture the raster has content


# ------------------------------------------------------------------ styles, positions, labels
@pytest.mark.parametrize("style", ["bar", "line", "double", "ratio"])
@pytest.mark.parametrize("units", ["km", "mi", "m"])
def test_scale_styles_and_units(style, units):
    fig, ax, ext = _fig()
    _draw({"elements": ["scale"], "scale_style": style, "scale_units": units, "scale_pos": "upper right"}, fig, ax, ext)
    texts = [t.get_text() for t in fig.findobj(plt.Text)]
    assert any(t.startswith("Scale 1:") for t in texts)
    if style != "ratio":
        assert any(t.endswith(units) for t in texts)
    if style == "double":
        other = "mi" if units != "mi" else "km"
        assert any(t.endswith(other) for t in texts)
    plt.close(fig)


def test_scale_length_in_miles_is_right():
    from atlasa0.furniture import SCALE_UNITS, draw_scale
    fig, ax, ext = _fig()
    bar_u, ratio = draw_scale(fig, ax, ext, T, A0_INCHES, "bar", "mi", "lower left")
    span_mi = (ext[1] - ext[0]) / SCALE_UNITS["mi"]
    assert bar_u <= span_mi / 4 and bar_u * 2 > span_mi / 4 - 1e-9 or bar_u in (1, 2, 5, 10)
    plt.close(fig)


@pytest.mark.parametrize("style", ["arrow", "classic", "compass", "circle"])
@pytest.mark.parametrize("pos", ["upper left", "upper right", "lower left", "lower right"])
def test_north_styles_and_corners(style, pos):
    fig, ax, ext = _fig()
    _draw({"elements": ["north"], "north_style": style, "north_pos": pos, "north_size": 1.5}, fig, ax, ext)
    assert "N" in [t.get_text() for t in fig.findobj(plt.Text)]
    # the symbol lies inside the map in the requested corner
    from matplotlib.patches import Polygon
    xs = [p.get_xy() for p in ax.patches if isinstance(p, Polygon) and p.get_facecolor()[3] > 0.99 or isinstance(p, Polygon)]
    assert xs
    cx = (ext[0] + ext[1]) / 2; cy = (ext[2] + ext[3]) / 2
    pts = [pt for arr in xs for pt in arr]
    mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
    assert ("left" in pos) == (mx < cx) and ("upper" in pos) == (my > cy)
    plt.close(fig)


def test_compass_has_all_directions():
    fig, ax, ext = _fig()
    _draw({"elements": ["north"], "north_style": "compass"}, fig, ax, ext)
    assert {"N", "E", "S", "W"} <= {t.get_text() for t in fig.findobj(plt.Text)}
    plt.close(fig)


@pytest.mark.parametrize("style", ["box", "compact", "minimal", "horizontal"])
def test_legend_styles(style):
    fig, ax, ext = _fig()
    _draw({"elements": ["legend"], "legend_style": style, "legend_title": "KEY", "legend_cols": 2,
           "legend_pos": "lower center", "legend_items": ["A=#f00", "B=#0f0"]}, fig, ax, ext,
          land=(("residential", "#ccc"),))
    lg = fig._atlasa0_furniture[0]
    assert lg.get_title().get_text() == "KEY"
    assert lg.get_frame_on() == (style != "minimal")
    assert lg._ncols == (3 if style == "horizontal" else 2)
    plt.close(fig)


def test_legend_without_title_and_with_user_handles():
    from matplotlib.lines import Line2D
    fig, ax, ext = _fig()
    h = Line2D([0], [0], marker="o", linestyle="", label="My sites")
    apply_layout(fig, ax, ext, T, A0_INCHES, None, Layout.from_any({"elements": ["legend"], "legend_title": ""}),
                 title="", subtitle="", credit="", y_title=.9, y_sub=.9, y_credit=.1, user_handles=[h])
    lg = fig._atlasa0_furniture[0]
    assert "My sites" in [t.get_text() for t in lg.get_texts()] and lg.get_title().get_text() == ""
    plt.close(fig)


def test_position_conflicts_are_rejected():
    with pytest.raises(ValueError, match="both at"):
        Layout.from_any({"north_pos": "lower left", "scale_pos": "lower left"})
    with pytest.raises(ValueError, match="both at"):
        Layout.from_any({"legend_pos": "lower right", "scale_pos": "lower right"})
    Layout.from_any({"elements": ["scale"], "scale_pos": "upper left"})          # north is off -> fine
    Layout.from_any({"legend_pos": "lower center", "note": "x", "note_pos": "upper center"})
    with pytest.raises(ValueError, match="both at"):
        Layout.from_any({"legend_pos": "lower center", "note": "x"})


@pytest.mark.parametrize("bad", [{"north_style": "fancy"}, {"scale_style": "x"}, {"scale_units": "ft"},
                                 {"legend_style": "x"}, {"north_pos": "center left"}, {"legend_cols": 0},
                                 {"scale_divisions": 20}, {"north_size": 9}, {"legend_items": ["A=notacolour"]}])
def test_style_validation(bad):
    with pytest.raises(ValueError):
        Layout.from_any(bad)


def test_receptor_legend_takes_a_free_slot():
    from atlasa0.furniture import free_slot
    assert free_slot({"lower right", "upper left", "lower left"}) == "upper right"
    assert free_slot({"upper right", "lower right"}) == "center right"
    assert free_slot({"upper right", "center right", "upper left"}) == "center left"


def test_parse_label_spec():
    from atlasa0.furniture import parse_label_spec
    d = parse_label_spec("Hayatabad Phase 3@71.43,33.98;size=50;color=#990000;bold=1;box=yes;rotation=15")
    assert d["text"] == "Hayatabad Phase 3" and (d["lon"], d["lat"]) == (71.43, 33.98)
    assert d["size"] == 50 and d["bold"] and d["box"] and d["rotation"] == 15 and d["halo"]
    for bad in ("nocoords", "T@1", "T@x,y", "T@200,10", "T@71,34;size=-1", "T@71,34;color=zzz", "T@71,34;weird=1", "@71,34"):
        with pytest.raises(ValueError):
            parse_label_spec(bad)


def test_free_labels_drawn_inside_and_skipped_outside(capsys):
    fig, ax, ext = _fig()
    cx, cy = (ext[0] + ext[1]) / 2, (ext[2] + ext[3]) / 2
    # fake projector: lon/lat are treated as offsets from the map centre (km)
    proj = lambda utm, lon, lat: (cx + lon * 1000, cy + lat * 1000)
    lay = Layout.from_any({"elements": [], "labels": [
        {"text": "In", "lon": 1, "lat": 1, "size": 30, "color": "#900", "bold": True, "rotation": 20},
        {"text": "Out", "lon": 90, "lat": 1}, "Boxed@2,2;box=1"]})
    apply_layout(fig, ax, ext, T, A0_INCHES, None, lay, title="", subtitle="", credit="", y_title=.9, y_sub=.9,
                 y_credit=.1, projector=proj)
    names = {t.get_text(): t for t in ax.texts}
    assert set(names) == {"In", "Boxed"} and names["In"].get_rotation() == 20 and names["In"].get_fontweight() == "bold"
    assert names["Boxed"].get_bbox_patch() is not None
    assert "outside the map" in capsys.readouterr().out
    plt.close(fig)


def test_tiff_hides_new_furniture_too(tmp_path, fake_crs):
    fig, ax, ext = _fig()
    _draw({"elements": ["legend", "scale", "north"], "scale_style": "double", "north_style": "compass",
           }, fig, ax, ext)
    n = len(fig._atlasa0_furniture)
    assert n > 10



# ------------------------------------------------------------------ draw order
def test_parse_draw_order_partial_and_errors():
    from atlasa0.furniture import DEFAULT_DRAW_ORDER, draw_zorders, parse_draw_order
    assert parse_draw_order(None) == list(DEFAULT_DRAW_ORDER)
    o = parse_draw_order("roads, water")                 # only these two given: roads below water
    assert o.index("roads") < o.index("water") and sorted(o) == sorted(DEFAULT_DRAW_ORDER)
    assert o.index("landuse") < o.index("roads")         # others keep their default neighbours
    with pytest.raises(ValueError):
        parse_draw_order("water,lakes")
    with pytest.raises(ValueError):
        parse_draw_order("water,water")
    z = draw_zorders(o)
    assert z["water"] > z["roads"] and max(z.values()) < 30   # map elements (zorder 30) stay above


def test_layout_carries_draw_order():
    lay = Layout.from_any({"draw_order": ["receptors", "your_data"]})
    assert lay.z("your_data") > lay.z("receptors")


def test_user_layers_follow_draw_order_band(tmp_path):
    import matplotlib.pyplot as plt
    from atlasa0.layers import LayerSpec, Prepared, Feature, draw_layers
    fig, ax = plt.subplots()
    preps = []
    for n in ("a", "b"):
        (tmp_path / f"{n}.geojson").write_text("{}")
        preps.append(Prepared(LayerSpec(path=str(tmp_path / f"{n}.geojson"), color="#ff0000"), [Feature("point", [(0, 0)])]))
    draw_layers(ax, preps, {"text": "k", "bg": "w"}, zorder=5.0)
    zs = sorted(c.get_zorder() for c in ax.collections)
    assert 5.0 <= zs[0] < zs[-1] < 6.0                    # second layer above first, inside its band
    plt.close(fig)
