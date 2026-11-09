# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Raster layers: option checks, number -> colour conversion, drawing (reader replaced), clear error without rasterio."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from atlasa0 import layers as L
from atlasa0 import rasters as R


@pytest.fixture
def tif(tmp_path):
    p = tmp_path / "ndvi.tif"
    p.write_bytes(b"not a real tiff - only the name matters for spec checks")
    return str(p)


def test_spec_accepts_raster_and_parses_options(tif):
    s = L.parse_layer_spec(f"{tif};name=NDVI;cmap=RdYlGn;vmin=0;vmax=0.8;alpha=0.7;placement=basemap;band=2;resample=nearest")
    assert (s.cmap, s.vmin, s.vmax, s.alpha, s.placement, s.band, s.resample) == ("RdYlGn", 0.0, 0.8, 0.7, "basemap", 2, "nearest")
    assert L.layers_to_dicts([s])[0]["cmap"] == "RdYlGn"
    assert L.layers_to_dicts([{"path": tif}]) == [{"path": tif}]       # defaults are not repeated


@pytest.mark.parametrize("bad", ["cmap=notacolourmap", "band=0", "placement=middle", "resample=magic", "vmin=5;vmax=1"])
def test_bad_raster_options_rejected(tif, bad):
    with pytest.raises(ValueError):
        L.parse_layer_spec(f"{tif};{bad}")


def test_single_band_colour_map_and_nodata(tif):
    s = L.parse_layer_spec(f"{tif};cmap=gray;vmin=0;vmax=10")
    data = np.array([[[0.0, 5.0, 10.0, np.nan]]])
    img, lim = R.to_rgba(data, s, 0.5)
    assert lim == (0.0, 10.0)
    assert img.shape == (1, 4, 4)
    assert img[0, 0, 0] < 0.05 and img[0, 2, 0] > 0.95                     # gray: dark -> light
    assert list(img[0, :, 3]) == [0.5, 0.5, 0.5, 0.0]                      # nodata transparent, others at opacity


def test_default_limits_use_percentiles_and_flat_image(tif):
    s = L.parse_layer_spec(tif)
    data = np.arange(100, dtype=float).reshape(1, 10, 10)
    _, lim = R.to_rgba(data, s)
    assert 0 < lim[0] < 5 and 94 < lim[1] < 99
    _, lim2 = R.to_rgba(np.full((1, 3, 3), 7.0), s)
    assert lim2[1] > lim2[0]


def test_rgb_8bit_kept_and_alpha_band(tif):
    s = L.parse_layer_spec(tif)
    rgb = np.zeros((4, 1, 2))
    rgb[0], rgb[3] = 255, [[255, 0]]                                       # red, second pixel fully transparent
    img, lim = R.to_rgba(rgb, s)
    assert lim is None and list(img[0, 0]) == [1, 0, 0, 1.0] and img[0, 1, 3] == 0


def test_draw_raster_puts_picture_under_given_zorder_and_keeps_limits(tif):
    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(1000, 2000)
    ax.set_ylim(5000, 6000)
    s = L.parse_layer_spec(f"{tif};cmap=viridis;vmin=0;vmax=1;name=Test")
    prep = L.Prepared(s, [], raster=True, utm=object())
    seen = {}

    def fake_reader(spec, utm, ext):
        seen["ext"] = ext
        return np.random.default_rng(0).random((1, 20, 30)), ext

    h = R.draw_raster(ax, prep, 1.5, reader=fake_reader)
    assert seen["ext"] == (1000, 2000, 5000, 6000)
    assert ax.images and ax.images[0].get_zorder() == 1.5
    assert ax.get_xlim() == (1000, 2000) and ax.get_ylim() == (5000, 6000)       # imshow must not move the map
    assert h.get_label().startswith("Test (")
    plt.close(fig)


def test_basemap_placement_uses_base_zorder(tif, monkeypatch):
    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    monkeypatch.setattr(R, "read_window", lambda spec, utm, ext, **k: (np.ones((1, 4, 4)), ext))
    base = L.Prepared(L.parse_layer_spec(f"{tif};placement=basemap"), [], raster=True, utm=1)
    over = L.Prepared(L.parse_layer_spec(f"{tif}"), [], raster=True, utm=1)
    L.draw_layers(ax, [base, over], {"text": "k", "bg": "w"}, zorder=9.0, base_zorder=1.5)
    zs = sorted(im.get_zorder() for im in ax.images)
    assert zs[0] < 2 and zs[1] >= 9.0
    plt.close(fig)


def test_clear_error_without_rasterio(tif, monkeypatch):
    import builtins
    real = builtins.__import__

    def no_rasterio(name, *a, **k):
        if name.startswith("rasterio"):
            raise ImportError(name)
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_rasterio)
    with pytest.raises(ValueError, match="pip install rasterio"):
        L.load_layer(L.parse_layer_spec(tif), object())


def test_raster_counts_as_one_feature(tif):
    prep = L.Prepared(L.parse_layer_spec(tif), [], raster=True)
    assert prep.count == 1 and prep.kinds() == {"raster": 1} and prep.bounds is None
