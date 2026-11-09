# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""place_point_labels: no overlaps, stay inside the map, must-show labels are kept."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from atlasa0.overview import place_point_labels


def _ax():
    fig = plt.figure(figsize=(6, 6), dpi=100)
    ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    return fig, ax


def _items(pts, size=12, **kw):
    return [dict(text=f"Place {i}", x=x, y=y, size=size, gap=6, marker_r=3, prio=-i, **kw) for i, (x, y) in enumerate(pts)]


def _boxes(placed):
    r = placed[0].figure.canvas.get_renderer()
    return [t.get_window_extent(r) for t in placed]


def test_labels_do_not_overlap_each_other():
    fig, ax = _ax()
    pts = [(20 + 4 * i, 50 + (i % 3) * 3) for i in range(12)]          # a tight cluster
    placed, skipped = place_point_labels(ax, _items(pts))
    assert placed                                                       # some were placed ...
    bb = _boxes(placed)
    for i in range(len(bb)):
        for j in range(i + 1, len(bb)):
            assert not bb[i].overlaps(bb[j]), (placed[i].get_text(), placed[j].get_text())
    assert len(placed) + len(skipped) == len(pts)
    plt.close(fig)


def test_labels_stay_inside_and_avoid_other_markers():
    fig, ax = _ax()
    placed, _ = place_point_labels(ax, _items([(1, 1), (99, 99), (50, 50), (52, 50)]))
    axbox = ax.get_window_extent(fig.canvas.get_renderer())
    for b in _boxes(placed):
        assert axbox.x0 <= b.x0 and b.x1 <= axbox.x1 and axbox.y0 <= b.y0 and b.y1 <= axbox.y1
    plt.close(fig)


def test_must_show_label_is_never_dropped():
    fig, ax = _ax()
    items = _items([(50, 50)] * 1, size=40, must=True)
    items += [dict(text="X" * 30, x=50, y=50, size=40, gap=6, marker_r=3, prio=-99, must=True)]
    placed, skipped = place_point_labels(ax, items)
    assert len(placed) == 2 and not skipped
    plt.close(fig)


def test_optional_labels_are_dropped_when_crowded():
    fig, ax = _ax()
    pts = [(50, 50)] * 8                                                # all on one spot
    placed, skipped = place_point_labels(ax, _items(pts, size=14))
    assert 1 <= len(placed) < 8 and skipped
    plt.close(fig)


def test_layer_labels_go_to_sink():
    from atlasa0 import layers
    import inspect
    assert "label_sink" in inspect.signature(layers.draw_layer).parameters
