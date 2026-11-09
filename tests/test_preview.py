# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Preview first: 50 dpi PNG only, _preview names, never skipped, does not train the size estimates."""
import pytest

from atlasa0 import api, cli
from atlasa0 import estimates as est
from atlasa0 import gui_core as core


def test_form_preview_overrides_quality_settings():
    s = core.FormState(cities=["Peshawar"], dpi=400, formats=["png", "tiff"], pois=["hospitals"], poi_data=True, skip_existing=True)
    jobs, kw = core.build_jobs(s, preview=True)
    assert kw["preview"] and kw["dpi"] == est.PREVIEW_DPI and kw["formats"] == ["png"]
    assert kw["poi_data"] is False and kw["skip_existing"] is False
    _, kw2 = core.build_jobs(s)
    assert "preview" not in kw2 and kw2["dpi"] == 400 and kw2["formats"] == ["png", "tiff"]


def test_generate_map_preview_uses_low_dpi_and_name(monkeypatch, tmp_path):
    seen = {}

    def fake_make_map(region, dpi, landscape, buildings, theme, radius, out, **kw):
        seen.update(dpi=dpi, out=out, formats=kw["formats"], poi_data=kw["poi_data"])
        open(out, "wb").write(b"x")
        return [out]

    monkeypatch.setattr(api, "make_map", fake_make_map)
    learned = []
    monkeypatch.setattr(api.est, "record_file", lambda *a, **k: learned.append(a))
    res = api.generate_map("Peshawar", dpi=400, formats=("png", "tiff"), poi_data=True, outdir=str(tmp_path),
                           preview=True, skip_existing=True)
    assert seen["dpi"] == 50 and seen["formats"] == ["png"] and seen["poi_data"] is False
    assert seen["out"].endswith("peshawar_A0_50dpi_preview.png")
    assert res[0]["skipped"] is False and not learned
    # a second preview is redone, not skipped
    res2 = api.generate_map("Peshawar", outdir=str(tmp_path), preview=True, skip_existing=True)
    assert res2[0]["skipped"] is False


def test_cli_preview_flag_is_passed(monkeypatch, capsys):
    got = {}
    monkeypatch.setattr(cli, "run_batch", lambda jobs, **kw: got.update(kw) or {"files": [], "failed": []})
    cli.main(["Peshawar", "--preview", "--dpi", "400"])
    assert got["preview"] is True
