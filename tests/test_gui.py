# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""GUI logic (toolkit-free controller + runner) and the Tk panel's wiring through a stub toolkit."""
import json
import threading
import time

import pytest

from atlasa0 import api, gui_core as core, runtime


# ------------------------------------------------------------------ controller
def S(**kw):
    return core.FormState(**kw)


def test_validate_requires_something_to_map():
    assert any("Choose something" in p for p in core.validate(S()))
    assert core.validate(S(cities=["Peshawar"])) == []


@pytest.mark.parametrize("kw,text", [
    (dict(cities=["A"], map_types=[]), "map type"),
    (dict(cities=["A"], formats=[]), "PNG"),
    (dict(cities=["A"], dpi=10), "dpi"),
    (dict(cities=["A"], pois=["zoo"]), "zoo"),
    (dict(cities=["A"], poi_data=True), "Receptor"),
    (dict(districts=["Swat"]), "province"),
    (dict(provinces=["narnia"]), "narnia"),
    (dict(cities=["A"], radius_km=-1), "Radius"),
    (dict(cities=["A"], legend_items=["nocolour"]), "legend item"),
    (dict(cities=["A"], elements=["legned"]), "legned"),
    (dict(cities=["A"], outdir=""), "folder"),
])
def test_validate_messages(kw, text):
    assert any(text in p for p in core.validate(S(**kw))), core.validate(S(**kw))


def test_build_jobs_mixed_levels():
    jobs, kw = core.build_jobs(S(country=True, provinces=["kpk"], cities=["Peshawar", "Quetta"],
                                 district_province="kpk", districts=["Swat"], map_types=["street", "water"],
                                 formats=["png", "tiff"], dpi=200, pois=["health"], poi_data=True))
    assert [j["level"] for j in jobs] == ["country", "province", "city", "city", "district"]
    assert jobs[1]["region"] == "Khyber Pakhtunkhwa" and jobs[4]["province"] == "Khyber Pakhtunkhwa"
    assert kw["types"] == ["street", "water"] and kw["dpi"] == 200 and kw["pois"] == ["health"]
    assert kw["layout"] is None  # defaults produce no layout dict


def test_build_jobs_all_provinces_and_layout():
    jobs, kw = core.build_jobs(S(provinces=["all"], elements=["scale", "north"], title="T", note="N",
                                 legend_items=["Site=#d62728"], legend_pos="center right", grid_km=5))
    assert len(jobs) == 7
    assert kw["layout"] == {"elements": ["scale", "north"], "title": "T", "note": "N",
                            "legend_items": ["Site=#d62728"], "legend_pos": "center right", "grid_km": 5}


def test_build_jobs_raises_formerror():
    with pytest.raises(core.FormError) as e:
        core.build_jobs(S())
    assert e.value.problems


def test_estimate_and_counts():
    e = core.estimate(S(cities=["A", "B"], map_types=["street", "water"], formats=["png", "tiff"], dpi=300))
    assert e["maps"] == 4 and e["files"] == 8 and e["pixels"] == (9933, 14043)
    assert 2 < e["ram_gb"] < 4 and e["download_mb"] > 0 and e["files_mb"] > 0
    e2 = core.estimate(S(cities=["A"], dpi=100, landscape=True))
    assert e2["pixels"] == (4681, 3311) and not e2["warnings"]
    assert core.estimate(S(provinces=["all"]))["maps"] == 7
    assert any("long run" in w for w in core.estimate(S(provinces=["all"], cities=[f"c{i}" for i in range(30)]))["warnings"])


def test_presets_roundtrip_and_unknown_keys(tmp_path):
    s = S(cities=["Peshawar"], dpi=200, elements=["scale"], note="x")
    p = str(tmp_path / "sub" / "p.json")
    core.save_preset(s, p)
    assert core.load_preset(p) == s
    json.dump({"cities": ["A"], "from_the_future": 1}, open(p, "w"))
    assert core.load_preset(p).cities == ["A"]


def test_batch_export_runs_through_cli_parser(tmp_path):
    p = str(tmp_path / "jobs.json")
    core.to_batch_json(S(country=True, cities=["Peshawar"], map_types=["street", "water"], dpi=200,
                         elements=["scale"]), p)
    doc = json.load(open(p))
    assert doc["author"] == "Imaad Ullah Khan Yameen" and doc["email"] == "yameenimaad@gmail.com"
    jobs = doc["jobs"]
    assert jobs[0] == {"level": "country", "dpi": 200, "formats": ["png"], "theme": "light", "landscape": "auto",
                       "buildings": False, "poi_labels": False, "poi_data": False,
                       "poi_formats": ["csv", "geojson"], "layout": {"elements": ["scale"]}}
    assert jobs[1]["types"] == ["street", "water"] and jobs[1]["region"] == "Peshawar"
    from atlasa0 import cli
    assert cli.main(["--batch", p, "--dry-run"]) == 0


def test_describe_options_is_json_serialisable_and_complete():
    o = core.describe_options()
    json.dumps(o)
    assert "street" in o["map_types"] and "hospitals" in o["poi_categories"] and "north" in o["elements"]
    assert o["defaults"]["dpi"] == 100


def test_parse_names():
    assert core.parse_names("Peshawar, Quetta\nPeshawar;  Dera Ismail Khan\n") == ["Peshawar", "Quetta", "Dera Ismail Khan"]


def test_districts_async_reports_error(monkeypatch):
    monkeypatch.setattr(api, "list_districts", lambda p: (_ for _ in ()).throw(RuntimeError("offline")))
    got = []
    core.load_districts_async("kpk", lambda n, e: got.append((n, e))).join(2)
    assert got == [([], "offline")]
    monkeypatch.setattr(api, "list_districts", lambda p: ["Swat", "Dir"])
    got.clear()
    core.load_districts_async("kpk", lambda n, e: got.append((n, e))).join(2)
    assert got == [(["Swat", "Dir"], None)]


# ------------------------------------------------------------------ runtime: events, cancel, runner
def test_run_batch_emits_events(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "generate_map", lambda **kw: [{"path": "x.png", "format": "png"}]
                        if kw["region"] != "Bad" else (_ for _ in ()).throw(ValueError("boom")))
    ev = []
    api.run_batch([{"level": "city", "region": "A"}, {"level": "city", "region": "Bad"}], outdir=str(tmp_path),
                  on_event=ev.append)
    assert [e["type"] for e in ev] == ["job_start", "job_done", "job_start", "job_failed"]
    assert ev[3]["error"] == "boom" and ev[1]["files"][0]["path"] == "x.png"


def test_cancel_stops_at_next_stage_and_keeps_finished_files(monkeypatch, tmp_path):
    started = threading.Event()

    def fake(**kw):
        runtime.log("stage 1")
        if kw["region"] == "B":
            started.set()
            for _ in range(200):   # a long job: every log() is a cancel point
                time.sleep(0.01)
                runtime.log("working")
        return [{"path": kw["region"] + ".png", "format": "png"}]

    monkeypatch.setattr(api, "generate_map", fake)
    events = []
    r = runtime.JobRunner(on_event=events.append)
    r.start([{"level": "city", "region": x} for x in "ABC"], outdir=str(tmp_path))
    assert started.wait(5)
    r.cancel()
    r.join(5)
    fin = [e for e in events if e["type"] == "finished"][0]["result"]
    assert fin["cancelled"] is True and [f["path"] for f in fin["files"]] == ["A.png"]
    assert any(e["type"] == "cancelled" for e in events)
    assert any(e["type"] == "log" for e in events)
    assert not r.running


def test_cancel_is_not_swallowed_by_except_exception():
    runtime.request_cancel()
    try:
        with pytest.raises(runtime.Cancelled):
            try:
                runtime.log("x")
            except Exception:   # what osm.get_features does
                pytest.fail("Cancelled must not be an Exception")
    finally:
        runtime.reset_cancel()


def test_runner_rejects_second_batch_and_reports_crash(monkeypatch, tmp_path):
    gate = threading.Event()
    monkeypatch.setattr(api, "generate_map", lambda **kw: (gate.wait(5), [])[1])
    ev = []
    r = runtime.JobRunner(on_event=ev.append)
    r.start([{"level": "city", "region": "A"}], outdir=str(tmp_path))
    with pytest.raises(RuntimeError):
        r.start([], outdir=str(tmp_path))
    gate.set()
    r.join(5)
    monkeypatch.setattr(api, "run_batch", lambda *a, **k: (_ for _ in ()).throw(KeyError("bad")))
    r2 = runtime.JobRunner(on_event=ev.append)
    r2.start([], outdir=str(tmp_path))
    r2.join(5)
    assert "bad" in ev[-1]["result"]["failed"][0]["error"]


# ------------------------------------------------------------------ Tk panel wired to a stub toolkit
@pytest.fixture
def panel(monkeypatch, tmp_path):
    import importlib
    import sys

    from tests import tk_stub
    saved = {k: sys.modules.get(k) for k in ("tkinter", "tkinter.ttk", "tkinter.filedialog", "tkinter.messagebox", "tkinter.colorchooser")}
    tk_stub.install()
    sys.modules.pop("atlasa0.gui_tk", None)
    mod = importlib.import_module("atlasa0.gui_tk")
    p = mod.AtlasPanel(None, preset_path=str(tmp_path / "none.json"))
    yield mod, p
    sys.modules.pop("atlasa0.gui_tk", None)
    for k, v in saved.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v


def test_panel_state_roundtrip(panel):
    mod, p = panel
    s = core.FormState(country=True, provinces=["Sindh"], cities=["Peshawar", "Quetta"], map_types=["landuse"],
                       formats=["png", "tiff"], dpi=200, elements=["scale", "legend"], note="Draft",
                       legend_items=["Site=#d62728"], pois=["hospitals"], poi_data=True, grid_km=2.0,
                       radius_km=5.0, outdir="out", skip_existing=False)
    p.set_state(s)
    back = p.get_state()
    for f in ("country", "provinces", "cities", "map_types", "formats", "dpi", "note", "legend_items", "pois",
              "poi_data", "grid_km", "radius_km", "outdir", "skip_existing"):
        assert getattr(back, f) == getattr(s, f), f
    assert sorted(back.elements) == ["legend", "scale"]


def test_panel_events_update_widgets_and_hand_files_to_viewer(panel):
    mod, p = panel
    got = []
    p.on_files = got.append
    for ev in ({"type": "log", "message": "hello"},
               {"type": "job_start", "index": 1, "total": 2, "label": "city Peshawar"},
               {"type": "job_done", "index": 1, "total": 2, "label": "x", "files": [{"path": "a.png"}, {"path": "a.tif"}]},
               {"type": "job_failed", "index": 2, "total": 2, "label": "y", "error": "boom"},
               {"type": "districts", "names": ["Swat", "Dir"], "error": None},
               {"type": "finished", "result": {"files": [1, 2], "failed": [1]}}):
        p._handle(ev)
    assert got == [["a.png", "a.tif"]]
    assert p.files._items == ["a.png", "a.tif"] and p.dist_list._items == ["Swat", "Dir"]


def test_panel_run_validates_then_starts_runner(panel, monkeypatch):
    mod, p = panel
    shown = []
    monkeypatch.setattr(mod.messagebox, "showwarning", lambda t, m: shown.append(m))
    p._run()
    assert shown and "Choose something" in shown[0]
    started = {}
    p.runner.start = lambda jobs, **kw: started.update(jobs=jobs, kw=kw)
    p.cities_txt.insert("1.0", "Peshawar")
    p.v["type:street"].set(True)
    p.v["fmt:png"].set(True)
    p._run()
    assert started["jobs"] == [{"level": "city", "region": "Peshawar"}]
    assert started["kw"]["types"] == ["street"] and started["kw"]["dpi"] == 100


def test_cli_gui_flag_without_tk_is_a_clean_error(monkeypatch):
    import sys
    from atlasa0 import cli
    monkeypatch.setitem(sys.modules, "atlasa0.gui_tk", None)  # import raises ImportError
    with pytest.raises(SystemExit) as e:
        cli.main(["--gui"])
    assert e.value.code == 2


def test_cli_gui_flag_launches(monkeypatch):
    import sys
    import types
    from atlasa0 import cli
    called = []
    fake = types.ModuleType("atlasa0.gui_tk")
    fake.launch = lambda: called.append(1)
    monkeypatch.setitem(sys.modules, "atlasa0.gui_tk", fake)
    assert cli.main(["--gui"]) == 0 and called == [1]


# ------------------------------------------------------------------ layers, styles, icons (controller)
@pytest.fixture
def shp(tmp_path):
    p = tmp_path / "sites.shp"
    p.write_bytes(b"x")
    return str(p)


def test_build_jobs_with_layers_styles_and_labels(shp):
    s = S(cities=["Peshawar"], layers=[{"path": shp, "color": "#2ca02c", "alpha": 0.5, "marker": "star"}],
          legend_style="horizontal", legend_pos="lower center", north_style="compass", north_pos="upper right",
          north_size=1.5, scale_style="double", scale_units="mi", scale_divisions=6,
          labels=[{"text": "Hayatabad", "lon": 71.43, "lat": 33.98, "size": 50}], legend_title="")
    jobs, kw = core.build_jobs(s)
    assert kw["layers"] == [{"path": shp, "color": "#2ca02c", "alpha": 0.5, "marker": "star"}]
    lay = kw["layout"]
    assert lay["legend_style"] == "horizontal" and lay["north_style"] == "compass" and lay["scale_units"] == "mi"
    assert lay["north_pos"] == "upper right" and lay["scale_divisions"] == 6 and lay["legend_title"] == ""
    assert lay["labels"][0]["text"] == "Hayatabad"


def test_untouched_form_has_no_layout_or_layers():
    jobs, kw = core.build_jobs(S(cities=["Peshawar"]))
    assert kw["layout"] is None and kw["layers"] is None


def test_validate_layers_and_positions(shp, tmp_path):
    assert any("not found" in p for p in core.validate(S(cities=["A"], layers=[{"path": str(tmp_path / "no.shp")}])))
    assert any("alpha" in p for p in core.validate(S(cities=["A"], layers=[{"path": shp, "alpha": 2}])))
    assert any("both at" in p for p in core.validate(S(cities=["A"], north_pos="lower left")))
    assert any("lon" in p for p in core.validate(S(cities=["A"], labels=[{"text": "x", "lon": 500, "lat": 1}])))


def test_layer_and_label_summaries(shp):
    assert "sites.shp" in core.layer_summary({"path": shp, "alpha": 0.8, "color": "#ff0000"})
    assert "80% opaque" in core.layer_summary({"path": shp, "alpha": 0.8})
    assert "auto" in core.layer_summary({"path": shp})
    assert "Hayatabad" in core.label_summary(core.check_label({"text": "Hayatabad", "lon": 71.4, "lat": 34}))


def test_blend_hex():
    assert core.blend_hex("#ff0000", 1.0) == "#ff0000"
    assert core.blend_hex("#ff0000", 0.0) == "#ffffff"
    assert core.blend_hex("#000000", 0.5) == "#808080"
    assert core.blend_hex("#ff0000", None) == "#ff0000"


def test_every_marker_has_preview_shape():
    from atlasa0.layers import MARKERS
    for m in MARKERS:
        kind, pts, hollow = core.marker_shape(m, 50, 50, 10)
        assert kind in ("oval", "poly") and hollow == MARKERS[m][1]
        assert len(pts) == 4 if kind == "oval" else len(pts) >= 6 and len(pts) % 2 == 0


def test_describe_options_lists_the_styles():
    o = core.describe_options()
    assert "star" in o["markers"] and "dashed" in o["line_styles"] and "diagonal" in o["hatches"]
    assert "compass" in o["north_styles"] and "double" in o["scale_styles"] and "horizontal" in o["legend_styles"]
    assert "lower center" in o["legend_positions"] and set(o["corners"]) == {"upper left", "upper right", "lower left", "lower right"}
    json.dumps(o)


def test_icons_exist_and_are_valid_png():
    import os
    from PIL import Image
    from atlasa0 import icons
    for n in icons.NAMES:
        p = icons.path(n)
        assert p and os.path.isfile(p), n
        with Image.open(p) as im:
            assert im.size == ((64, 64) if n == "app" else (24, 24)) and im.mode == "RGBA"
    assert icons.app_ico()
    assert icons.get("no-such-icon") is None


def test_preset_roundtrip_keeps_layers_and_labels(tmp_path, shp):
    s = S(cities=["A"], layers=[{"path": shp, "color": "#000000"}], labels=[{"text": "T", "lon": 1, "lat": 2}],
          north_style="circle")
    p = str(tmp_path / "p.json")
    core.save_preset(s, p)
    assert core.load_preset(p) == s


def test_batch_json_contains_layers(tmp_path, shp):
    p = str(tmp_path / "jobs.json")
    core.to_batch_json(S(cities=["Peshawar"], layers=[{"path": shp, "color": "#ff0000"}], scale_style="line"), p)
    j = json.load(open(p))["jobs"][0]
    assert j["layers"] == [{"path": shp, "color": "#ff0000"}] and j["layout"] == {"scale_style": "line"}
    from atlasa0 import cli
    assert cli.main(["--batch", p, "--dry-run"]) == 0


# ------------------------------------------------------------------ Tk panel: layers, labels, styles
def test_panel_roundtrip_with_layers_labels_styles(panel, shp):
    mod, p = panel
    s = core.FormState(cities=["Peshawar"], layers=[{"path": shp, "color": "#2ca02c"}],
                       labels=[{"text": "X", "lon": 71.0, "lat": 34.0, "size": 40.0}], legend_style="minimal",
                       north_style="circle", north_size=2.0, scale_style="line", scale_units="m", scale_divisions=5,
                       legend_cols=2, legend_title="Key", note_pos="upper center")
    p.set_state(s)
    b = p.get_state()
    for f in ("layers", "labels", "legend_style", "north_style", "north_size", "scale_style", "scale_units",
              "scale_divisions", "legend_cols", "legend_title", "note_pos"):
        assert getattr(b, f) == getattr(s, f), f
    assert p.layer_list._items and p.label_list._items


def test_layer_dialog_builds_a_valid_layer(panel, shp):
    mod, p = panel
    dlg = mod.LayerDialog(p, p.opts)
    dlg.v["path"].set(shp)
    dlg.v["color"].set("#0000ff")
    dlg.v["alpha_auto"].set(False)
    dlg.v["alpha_pct"].set(35.0)
    dlg.v["marker"].set("diamond")
    dlg.v["size_mm"].set("9")
    dlg.v["label_field"].set("NAME")
    dlg._ok()
    assert dlg.result == {"path": shp, "color": "#0000ff", "alpha": 0.35, "marker": "diamond", "size_mm": 9.0,
                          "label_field": "NAME"}


def test_layer_dialog_rejects_bad_input(panel, shp, monkeypatch):
    mod, p = panel
    shown = []
    monkeypatch.setattr(mod.messagebox, "showwarning", lambda t, m: shown.append(m))
    dlg = mod.LayerDialog(p, p.opts)
    dlg._ok()                                     # no file chosen
    assert dlg.result is None and shown
    dlg.v["path"].set(shp)
    dlg.v["size_mm"].set("abc")
    with pytest.raises(ValueError):
        dlg.collect()


def test_layer_dialog_edit_keeps_values(panel, shp):
    mod, p = panel
    dlg = mod.LayerDialog(p, p.opts, {"path": shp, "alpha": 0.2, "hatch": "dots", "line_style": "dotted"})
    assert dlg.v["alpha_auto"].get() is False and dlg.v["alpha_pct"].get() == pytest.approx(20)
    dlg._ok()
    assert dlg.result["alpha"] == 0.2 and dlg.result["hatch"] == "dots" and dlg.result["line_style"] == "dotted"


def test_label_dialog(panel):
    mod, p = panel
    d = mod.LabelDialog(p)
    d.v["text"].set("Hayatabad"); d.v["lon"].set("71.43"); d.v["lat"].set("33.98"); d.v["bold"].set(True)
    d._ok()
    assert d.result["text"] == "Hayatabad" and d.result["bold"] and d.result["lon"] == 71.43
    bad = mod.LabelDialog(p)
    bad._ok()
    assert bad.result is None


def test_panel_add_move_remove_layers(panel, shp, monkeypatch):
    mod, p = panel
    results = iter([{"path": shp, "name": "A"}, {"path": shp, "name": "B"}])

    class FakeDlg:
        def __init__(self, *a, **k): self.result = next(results)
        def show(self): pass

    monkeypatch.setattr(mod, "LayerDialog", FakeDlg)
    p._add_layer(); p._add_layer()
    assert [d["name"] for d in p.layers] == ["A", "B"]
    # list is shown top-first: row 0 = B (printed last, on top), row 1 = A (bottom)
    assert p.layer_list._items[0].startswith("2. (top)") and "B" in p.layer_list._items[0]
    assert p.layer_list._items[1].startswith("1. (bottom)")
    p.layer_list._sel = (1,)          # A
    p._move_layer(-1)                 # "Move up" = bring forward
    assert [d["name"] for d in p.layers] == ["B", "A"]     # A is now drawn last (on top)
    assert "A" in p.layer_list._items[0]
    p.layer_list._sel = (0,)          # top row = A
    p._remove_layer()
    assert [d["name"] for d in p.layers] == ["B"]


# ------------------------------------------------------------------ file names and automatic settings
def test_custom_file_name_template_and_defaults():
    from atlasa0 import gui_core as c
    s = c.FormState(cities=["Peshawar"], name_mode="custom", name_template="Map {region} {date}")
    assert c.validate(s) == []
    jobs, kw = c.build_jobs(s)
    assert kw["filename"] == "Map {region} {date}"
    assert c.build_jobs(c.FormState(cities=["Peshawar"]))[1]["filename"] is None      # automatic by default
    assert c.example_name(c.FormState(cities=["Peshawar"])) == f"peshawar_A0_{c.FormState().dpi}dpi.png"
    ex = c.example_name(s)
    assert ex.startswith("Map_peshawar_20") and ex.endswith(".png")


def test_custom_name_must_not_overwrite_itself():
    from atlasa0 import gui_core as c
    two = c.FormState(cities=["Peshawar", "Lahore"], name_mode="custom", name_template="my_map")
    assert any("{region}" in p for p in c.validate(two))
    types = c.FormState(cities=["Peshawar"], map_types=["street", "water"], name_mode="custom", name_template="{region}")
    assert any("{type}" in p for p in c.validate(types))
    assert c.validate(c.FormState(cities=["Peshawar"], map_types=["street", "water"], name_mode="custom",
                                  name_template="{region}_{type}")) == []
    bad = c.FormState(cities=["Peshawar"], name_mode="custom", name_template="{nope}")
    assert any("Unknown field" in p for p in c.validate(bad))


def test_file_stem_cleaning():
    from atlasa0.config import file_stem
    assert file_stem("A/B: map?.PNG") == "AB_map"
    assert file_stem("{region}_{dpi}", region="peshawar", dpi=200) == "peshawar_200"
    for bad in ("", "   ", "{", "{x}"):
        with pytest.raises(ValueError):
            file_stem(bad)


def test_settings_roundtrip_in_preset(tmp_path):
    from atlasa0 import gui_core as c
    s = c.FormState(cities=["Peshawar"], name_mode="custom", name_template="x_{region}", auto_save=False, open_folder=True)
    c.save_preset(s, str(tmp_path / "p.json"))
    t = c.load_preset(str(tmp_path / "p.json"))
    assert (t.name_mode, t.name_template, t.auto_save, t.open_folder) == ("custom", "x_{region}", False, True)



# ------------------------------------------------------------------ draw order
def test_draw_order_rows_and_moves():
    from atlasa0 import gui_core as c
    from atlasa0.furniture import DEFAULT_DRAW_ORDER
    rows = c.draw_order_rows(None)
    assert rows[0][0] == "labels" and rows[0][1].endswith("(top)")
    assert rows[-1][0] == "basemap" and rows[-1][1].endswith("(bottom)")
    o = c.move_in_order(DEFAULT_DRAW_ORDER, "water", +1)       # water above district lines
    assert o.index("water") == o.index("boundaries") + 1
    assert c.move_in_order(DEFAULT_DRAW_ORDER, "labels", +1) == list(DEFAULT_DRAW_ORDER)   # already on top


def test_draw_order_reaches_layout_only_when_changed():
    from atlasa0 import gui_core as c
    assert c.layout_from_state(c.FormState(cities=["A"])) is None
    order = c.move_in_order(None, "roads", -1)
    lay = c.layout_from_state(c.FormState(cities=["A"], draw_order=order))
    assert lay["draw_order"] == order
    assert any("draw-order" in p for p in c.validate(c.FormState(cities=["A"], draw_order=["nope"])))


def test_panel_draw_order_buttons(panel):
    mod, p = panel
    keys = [k for k, _ in mod.core.draw_order_rows(None)]
    p.order_list._sel = (keys.index("water"),)
    p._move_order(True)
    assert p.get_state().draw_order.index("water") > p.get_state().draw_order.index("boundaries")
    p._reset_order()
    assert p.get_state().draw_order == list(mod.core.describe_options()["default_draw_order"])
