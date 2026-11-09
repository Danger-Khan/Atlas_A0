# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Paper sizes: geometry, estimates, form state, CLI, layout."""
import pytest

from atlasa0 import config as cfg
from atlasa0 import estimates as est
from atlasa0 import gui_core as core
from atlasa0.furniture import Layout


def test_parse_paper():
    assert cfg.parse_paper("a3") == ("A3", 297, 420)
    assert cfg.parse_paper(None)[0] == "A0"
    assert cfg.parse_paper("700 x 500 mm") == ("500x700mm", 500.0, 700.0)
    for bad in ("A5", "10x10", "banana", "5000x5000"):
        with pytest.raises(ValueError):
            cfg.parse_paper(bad)


def test_geometry_scales_like_the_paper():
    size, k, label = cfg.sheet_geometry("A0")
    assert size == cfg.A0_INCHES and k == 1 and label == "A0"
    size3, k3, _ = cfg.sheet_geometry("A3", landscape=True)
    assert size3[0] > size3[1]                               # landscape
    assert abs(k3 - 297 / 841) < 1e-9
    # real sheet = figure x k : 420 x 297 mm
    assert abs(size3[0] * k3 * 25.4 - 420) < 1.5 and abs(size3[1] * k3 * 25.4 - 297) < 1.5
    # same aspect as the paper, so the map fits the sheet the way it does on A0
    assert abs(size3[0] / size3[1] - 420 / 297) < 0.01


def test_pixels_follow_paper_and_dpi():
    assert est.sheet_pixels(100) == (3311, 4681)
    w, h = est.sheet_pixels(300, False, "A4")
    assert abs(w - 210 / 25.4 * 300) < 3 and abs(h - 297 / 25.4 * 300) < 3
    assert est.ram_gb(300, False, False, "A4") < est.ram_gb(300, False, False, "A0")
    assert est.file_mb("street", "png", 300, False, "A3")[0] < est.file_mb("street", "png", 300, False, "A0")[0] / 7


def test_layout_and_form():
    assert Layout.from_any({"paper": "A2"}).paper == "A2"
    assert Layout.from_any(None).paper == "A0"
    with pytest.raises(ValueError):
        Layout.from_any({"paper": "A9"})
    s = core.FormState(cities=["Peshawar"])
    assert core.layout_from_state(s) is None                      # default paper -> untouched layout
    s.paper = "A3"
    assert core.layout_from_state(s)["paper"] == "A3"
    assert core.estimate(s)["paper"] == "A3" and "A3" in core.estimate_text(core.estimate(s))
    s.paper = "nonsense"
    assert any("paper" in p.lower() for p in core.validate(s))
    assert "A4" in core.describe_options()["papers"]


def test_save_scales_dpi(tmp_path):
    """A0-proportioned figure saved at dpi x k gives paper_size x dpi pixels."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    from atlasa0.export import save_outputs
    size, k, _ = cfg.sheet_geometry("A4", False)
    fig = plt.figure(figsize=size, dpi=100)
    ax = fig.add_axes(list(cfg.AXES_RECT))
    out = save_outputs(fig, ax, str(tmp_path / "a4.png"), 100, ["png"], None, None, "white", "t", sheet_k=k)
    with Image.open(out[0]) as im:
        assert abs(im.size[0] - 210 / 25.4 * 100) < 3 and abs(im.size[1] - 297 / 25.4 * 100) < 3
        assert round(im.info["dpi"][0]) == 100
