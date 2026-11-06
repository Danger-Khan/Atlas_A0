# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""CLI behaviour, job building, batch failure isolation and the file-naming contract (no network)."""
import json
import os

import pytest

import atlasa0.api as api
from atlasa0 import cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------ CLI
@pytest.mark.parametrize("flag", ["--list", "--list-types", "--list-poi"])
def test_cli_list_commands(flag, capsys):
    assert cli.main([flag]) == 0
    assert capsys.readouterr().out.strip()


def test_cli_list_types_shows_every_type(capsys):
    cli.main(["--list-types"])
    out = capsys.readouterr().out
    for t in ("street", "transport", "landuse", "water", "buildings", "receptors", "satellite", "topo"):
        assert t in out


@pytest.mark.parametrize("argv", [
    ["Peshawar", "--type", "bogus"],
    ["Peshawar", "--format", "jpg"],
    ["Peshawar", "--poi", "zoo"],
    ["Peshawar", "--poi-format", "xls"],
    ["--district", "Swat"],          # needs --in
    [],                              # nothing to make
])
def test_cli_rejects_bad_input(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(argv)
    assert e.value.code == 2


def _planned(capsys):
    return [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("=== [")]


def test_cli_dry_run_mixed_levels(capsys):
    rc = cli.main(["Peshawar", "--country", "--province", "kpk", "sindh", "--type", "street", "water",
                   "--dry-run"])
    assert rc == 0
    plan = _planned(capsys)
    # country(1) + 2 provinces(1 each, type ignored) + Peshawar x 2 types
    assert len(plan) == 5
    assert any("country" in p for p in plan) and sum("province" in p for p in plan) == 2


def test_cli_province_all_expands_to_seven(capsys):
    cli.main(["--province", "all", "--dry-run"])
    assert len(_planned(capsys)) == 7


def test_cli_province_cities_expands_presets(capsys):
    cli.main(["--province-cities", "sindh", "--dry-run"])
    assert len(_planned(capsys)) == 5  # Karachi, Hyderabad, Sukkur, Larkana, Mirpur Khas


def test_cli_type_all_makes_one_file_per_type(capsys):
    cli.main(["Quetta", "--type", "all", "--dry-run"])
    assert len(_planned(capsys)) == 8


def test_cli_batch_file(capsys):
    cli.main(["--batch", os.path.join(ROOT, "examples", "jobs.json"), "--dry-run"])
    # country, province, district x3 types, city x3 types
    assert len(_planned(capsys)) == 8


def test_cli_poi_format_implies_poi_data(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "run_batch", lambda jobs, **kw: seen.update(kw) or {"files": [], "failed": []})
    cli.main(["Peshawar", "--poi", "health", "--poi-format", "csv", "summary"])
    assert seen["poi_data"] is True and seen["poi_formats"] == ["csv", "summary"]
    cli.main(["Peshawar", "--poi", "health"])
    assert seen["poi_data"] is False and tuple(seen["poi_formats"]) == ("geojson", "csv")


def test_cli_exit_code_reflects_failures(monkeypatch):
    monkeypatch.setattr(cli, "run_batch", lambda jobs, **kw: {"files": [], "failed": [{"job": {}, "error": "x"}]})
    assert cli.main(["Peshawar"]) == 1


def test_cli_manifest_written(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "run_batch", lambda jobs, **kw: {"files": [{"path": "a.png"}], "failed": []})
    m = tmp_path / "sub" / "m.json"
    cli.main(["Peshawar", "--manifest", str(m)])
    assert json.load(open(m))["files"][0]["path"] == "a.png"


# ------------------------------------------------------------------ run_batch
def test_run_batch_isolates_failures_and_expands_types(monkeypatch, tmp_path):
    calls = []

    def fake(**kw):
        calls.append(kw)
        if kw["region"] == "Bad":
            raise ValueError("boom")
        return [{"path": "x", "format": "png", "level": kw["level"], "region": kw["region"],
                 "map_type": kw["map_type"], "skipped": False}]

    monkeypatch.setattr(api, "generate_map", fake)
    res = api.run_batch([{"level": "city", "region": "Bad"},
                         {"level": "city", "region": "Ok", "types": ["street", "water"]},
                         {"level": "province", "region": "kpk", "types": ["street", "water"]}],
                        outdir=str(tmp_path), dpi=100)
    assert len(res["files"]) == 3 and len(res["failed"]) == 1
    assert res["failed"][0]["error"] == "boom"
    assert [c["map_type"] for c in calls if c["region"] == "Ok"] == ["street", "water"]
    assert sum(c["region"] == "kpk" for c in calls) == 1   # province: map type does not apply
    assert all(c["dpi"] == 100 for c in calls)              # defaults flow into every job


def test_run_batch_job_values_override_defaults(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(api, "generate_map", lambda **kw: seen.append(kw) or [])
    api.run_batch([{"level": "city", "region": "A", "dpi": 200}, {"level": "city", "region": "B"}],
                  outdir=str(tmp_path), dpi=100)
    assert [s["dpi"] for s in seen] == [200, 100]


def test_run_batch_dry_run_calls_nothing(monkeypatch, capsys):
    monkeypatch.setattr(api, "generate_map", lambda **kw: pytest.fail("must not run"))
    r = api.run_batch([{"level": "city", "region": "A"}], dry_run=True)
    assert r == {"files": [], "failed": []}


# ------------------------------------------------------------------ file-naming contract
@pytest.fixture
def makers(monkeypatch):
    """Replace the heavy drawing functions with fakes that just report the file they would write."""
    log = []

    def make(kind):
        def fn(*a, **kw):
            out = next(x for x in list(a) + list(kw.values()) if isinstance(x, str) and x.endswith(".png"))
            log.append((kind, kw))
            base = out[:-4]
            fm = kw.get("formats") or ("png",)
            files = [base + (".png" if f == "png" else ".tif") for f in fm]
            if kw.get("poi_data"):
                files += [base + api.POI_FILE_SUFFIX[f] for f in kw.get("poi_formats", ("geojson", "csv"))]
            return files
        return fn

    for name, kind in (("make_map", "city"), ("make_district_map", "district"),
                       ("make_province_map", "province"), ("make_country_map", "country")):
        monkeypatch.setattr(api, name, make(kind))
    return log


def names(res):
    return [os.path.basename(r["path"]) for r in res]


def test_name_city(makers, tmp_path):
    assert names(api.generate_map("Dera Ismail Khan", outdir=str(tmp_path), dpi=300)) == \
        ["dera_ismail_khan_A0_300dpi.png"]
    assert names(api.generate_map("Peshawar", map_type="landuse", dpi=200, outdir=str(tmp_path),
                                  formats=("png", "tiff"))) == \
        ["peshawar_landuse_A0_200dpi.png", "peshawar_landuse_A0_200dpi.tif"]


def test_name_district_province_country(makers, tmp_path):
    r = api.generate_map("Swat", level="district", province="kpk", map_type="water", outdir=str(tmp_path))
    assert names(r) == ["district_khyber_pakhtunkhwa_swat_water_A0_300dpi.png"]
    assert names(api.generate_map("kpk", level="province", outdir=str(tmp_path))) == \
        ["province_khyber_pakhtunkhwa_A0_300dpi.png"]
    assert names(api.generate_map(level="country", outdir=str(tmp_path), formats=("tiff",))) == \
        ["country_pakistan_A0_300dpi.tif"]


def test_name_with_poi_overlay_and_data(makers, tmp_path):
    r = api.generate_map("Peshawar", map_type="receptors", pois=["hospitals", "schools"], poi_data=True,
                         poi_formats=("csv", "xlsx"), outdir=str(tmp_path))
    assert names(r) == ["peshawar_receptors_poi_hospitals+schools_A0_300dpi.png",
                        "peshawar_receptors_poi_hospitals+schools_A0_300dpi_poi.csv",
                        "peshawar_receptors_poi_hospitals+schools_A0_300dpi_poi.xlsx"]
    assert [x["format"] for x in r] == ["png", "csv", "xlsx"]


def test_poi_overlay_does_not_clash_with_plain_map(makers, tmp_path):
    a = names(api.generate_map("Peshawar", outdir=str(tmp_path)))
    b = names(api.generate_map("Peshawar", pois="receptors", outdir=str(tmp_path)))
    assert a != b


def test_province_and_country_ignore_pois(makers, tmp_path):
    r = api.generate_map("sindh", level="province", pois=["hospitals"], outdir=str(tmp_path))
    assert names(r) == ["province_sindh_A0_300dpi.png"]


def test_skip_existing_reuses_files_and_includes_poi_files(makers, tmp_path):
    kw = dict(region="Peshawar", pois="health", poi_data=True, poi_formats=("csv",),
              formats=("png", "tiff"), outdir=str(tmp_path), skip_existing=True)
    first = api.generate_map(**kw)
    assert not any(r["skipped"] for r in first) and len(makers) == 1
    for r in first:                          # create the files the fake makers only reported
        open(r["path"], "w").close()
    again = api.generate_map(**kw)
    assert all(r["skipped"] for r in again) and len(makers) == 1     # nothing re-made
    os.remove(first[-1]["path"])             # a missing receptor file triggers a re-make
    api.generate_map(**kw)
    assert len(makers) == 2


@pytest.mark.parametrize("kw,msg", [
    (dict(region="X", level="town"), "level"),
    (dict(region="X", map_type="bogus"), "map type"),
    (dict(region="Swat", level="district"), "province"),
    (dict(level="city"), "city name"),
])
def test_generate_map_validates_input(kw, msg, makers, tmp_path):
    with pytest.raises(ValueError) as e:
        api.generate_map(outdir=str(tmp_path), **kw)
    assert msg in str(e.value)


def test_env_defaults_for_outdir_dpi_theme(monkeypatch):
    monkeypatch.setenv("ATLASA0_OUTDIR", "/data/maps")
    monkeypatch.setenv("ATLASA0_DPI", "200")
    monkeypatch.setenv("ATLASA0_THEME", "dark")
    a = cli.build_parser().parse_args(["Peshawar"])
    assert (a.outdir, a.dpi, a.theme) == ("/data/maps", 200, "dark")
    monkeypatch.setenv("ATLASA0_THEME", "nonsense")
    assert cli.build_parser().parse_args(["Peshawar"]).theme == "light"


def test_cli_layout_flags_reach_the_batch(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "run_batch", lambda jobs, **kw: seen.update(kw) or {"files": [], "failed": []})
    cli.main(["Peshawar", "--elements", "legend", "scale", "--legend-item", "Site=#d62728", "--title", "X",
              "--note", "Draft"])
    lay = seen["layout"]
    assert lay["elements"] == ["legend", "scale"] and lay["title"] == "X" and lay["legend_items"] == ["Site=#d62728"]
    cli.main(["Peshawar"])
    assert seen["layout"] is None


@pytest.mark.parametrize("argv", [["Peshawar", "--elements", "legned"], ["Peshawar", "--legend-item", "nocolour"],
                                  ["Peshawar", "--logo", "/no/such.png"]])
def test_cli_rejects_bad_layout(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(argv)
    assert e.value.code == 2


def test_cli_list_elements(capsys):
    assert cli.main(["--list-elements"]) == 0
    out = capsys.readouterr().out
    assert "scale" in out and "north" in out and "legend" in out


# ------------------------------------------------------------------ layers and styles on the command line / API
@pytest.fixture
def shpfile(tmp_path):
    p = tmp_path / "sites.shp"
    p.write_bytes(b"x")
    return str(p)


def test_cli_layer_and_style_flags_reach_the_batch(monkeypatch, shpfile):
    seen = {}
    monkeypatch.setattr(cli, "run_batch", lambda jobs, **kw: seen.update(kw) or {"files": [], "failed": []})
    cli.main(["Peshawar", "--layer", f"{shpfile};name=Sites;color=#2ca02c;alpha=0.5;marker=star", "--layer", shpfile,
              "--legend-style", "horizontal", "--legend-pos", "lower center", "--legend-title", "Key",
              "--north-style", "compass", "--north-pos", "upper right", "--north-size", "1.5",
              "--scale-style", "double", "--scale-units", "mi", "--scale-pos", "lower left", "--scale-divisions", "6",
              "--text-label", "Hayatabad@71.43,33.98;size=50", "--note", "x", "--note-pos", "upper center"])
    assert seen["layers"] == [f"{shpfile};name=Sites;color=#2ca02c;alpha=0.5;marker=star", shpfile]
    lay = seen["layout"]
    assert lay["legend_style"] == "horizontal" and lay["north_style"] == "compass" and lay["scale_units"] == "mi"
    assert lay["labels"] == ["Hayatabad@71.43,33.98;size=50"] and lay["note_pos"] == "upper center"
    cli.main(["Peshawar"])
    assert seen["layers"] is None


@pytest.mark.parametrize("argv", [
    ["Peshawar", "--layer", "/no/such/file.shp"], ["Peshawar", "--layer", "x.txt"],
    ["Peshawar", "--text-label", "nocoords"], ["Peshawar", "--north-style", "fancy"],
    ["Peshawar", "--north-pos", "upper left", "--scale-pos", "upper left"],
])
def test_cli_rejects_bad_layer_and_style_input(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(argv)
    assert e.value.code == 2


def test_cli_bad_layer_option_is_reported(shpfile):
    with pytest.raises(SystemExit):
        cli.main(["Peshawar", "--layer", f"{shpfile};alpha=2"])
    with pytest.raises(SystemExit):
        cli.main(["Peshawar", "--layer", f"{shpfile};marker=banana"])


def test_cli_list_styles(capsys):
    assert cli.main(["--list-styles"]) == 0
    out = capsys.readouterr().out
    for word in ("star", "dashed", "diagonal", "compass", "double", "horizontal", "lower center"):
        assert word in out


def test_generate_map_passes_validated_layers(makers, tmp_path, shpfile):
    api.generate_map("Peshawar", outdir=str(tmp_path), layers=[{"path": shpfile, "color": "#ff0000"}, f"{shpfile};alpha=0.3"])
    kw = makers[-1][1]
    assert [l.color for l in kw["layers"]] == ["#ff0000", "#d62728"] and kw["layers"][1].alpha == 0.3
    api.generate_map("kpk", level="province", outdir=str(tmp_path), layers=[shpfile])
    assert makers[-1][1]["layers"][0].path == shpfile
    api.generate_map(level="country", outdir=str(tmp_path))
    assert makers[-1][1]["layers"] is None


def test_generate_map_rejects_bad_layers_before_any_work(makers, tmp_path):
    with pytest.raises(ValueError, match="not found"):
        api.generate_map("Peshawar", outdir=str(tmp_path), layers=[{"path": str(tmp_path / "gone.shp")}])
    assert makers == []


def test_cli_name_flag_validation(capsys):
    from atlasa0 import cli
    with pytest.raises(SystemExit):
        cli.main(["Peshawar", "Lahore", "--name", "same", "--dry-run"])
    assert "{region}" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        cli.main(["Peshawar", "--name", "{bogus}", "--dry-run"])
    assert cli.main(["Peshawar", "Lahore", "--name", "Map_{region}", "--dry-run"]) == 0


def test_custom_file_name_applies_to_every_level(makers, tmp_path):
    t = str(tmp_path)
    assert names(api.generate_map("Peshawar", outdir=t, filename="Site map {region} {dpi}", dpi=200,
                                  formats=("png", "tiff"))) == ["Site_map_peshawar_200.png", "Site_map_peshawar_200.tif"]
    assert names(api.generate_map("Swat", level="district", province="kpk", map_type="water", outdir=t,
                                  filename="{level}_{type}")) == ["district_water.png"]
    assert names(api.generate_map(level="country", outdir=t, filename="Pakistan overview.png")) == ["Pakistan_overview.png"]
    with pytest.raises(ValueError):
        api.generate_map("Peshawar", outdir=t, filename="{bogus}")


def test_dpi_limits_cli_and_api(makers, tmp_path, capsys):
    from atlasa0 import cli
    with pytest.raises(SystemExit):
        cli.main(["Peshawar", "--dpi", "600", "--dry-run"])
    with pytest.raises(ValueError):
        api.generate_map("Peshawar", dpi=600, outdir=str(tmp_path))
    assert cli.main(["Peshawar", "--dpi", "500", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "16555 x 23405" in out and "download about" in out
