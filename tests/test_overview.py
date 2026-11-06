# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Province/country overview fixes: the Khyber Pakhtunkhwa map that labelled divisions + districts + tehsils."""
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from atlasa0.config import A0_INCHES, AXES_RECT
from atlasa0.overview import clean_label, filter_admin, pick_landscape, place_labels, wrap_label


def _osm_like():
    """What osmnx returned for {"boundary": "administrative", "admin_level": "6"} (tags are OR-ed)."""
    return pd.DataFrame({
        "name": ["Peshawar District", "Malakand Division", "Chitral Tehsil", "Swat District", "Mardan",
                 "Kohat Tehsil", "Bannu District", "Khyber Pakhtunkhwa", "Peshawar"],
        "admin_level": ["6", "5", "7", "6", "6", "6", None, "4", "6"],
        "boundary": ["administrative"] * 8 + ["political"],
        "geom_type": ["MultiPolygon", "Polygon", "Polygon", "Polygon", "Polygon", "Polygon", "Polygon",
                      "Polygon", "Polygon"]})


def test_filter_admin_keeps_only_districts():
    kept, dropped = filter_admin(_osm_like(), 6)
    # tehsil mistagged as level 6 is caught by its name; untagged and level 5/7/4 are dropped
    assert list(kept["name"]) == ["Peshawar District", "Swat District", "Mardan"]
    assert dropped == 6


def test_filter_admin_provinces_and_empty():
    kept, _ = filter_admin(_osm_like(), 4)
    assert list(kept["name"]) == ["Khyber Pakhtunkhwa"]
    empty = pd.DataFrame({"geom_type": []})
    assert filter_admin(empty, 6)[1] == 0


def test_clean_and_wrap_labels():
    assert clean_label("Lower South Waziristan District") == "Lower South Waziristan"
    assert clean_label("Punjab", drop=()) == "Punjab" and clean_label(None) is None
    assert wrap_label("Lower South Waziristan") == "Lower South\nWaziristan"
    assert wrap_label("Swat") == "Swat"


def _sheet(dpi=20):
    fig = plt.figure(figsize=A0_INCHES[::-1], dpi=dpi)
    ax = fig.add_axes(list(AXES_RECT))
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 700)
    return fig, ax


def test_place_labels_never_overlap():
    fig, ax = _sheet()
    # 40 names crowded into one corner, like the Peshawar valley districts
    items = [(f"District number {i}", 500 + (i % 5) * 6, 400 + (i // 5) * 5, 100 - i) for i in range(40)]
    placed, skipped = place_labels(ax, items, pad_px=0)
    r = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(r) for t in placed]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a.x1 <= b.x0 or b.x1 <= a.x0 or a.y1 <= b.y0 or b.y1 <= a.y0
    assert placed and skipped and len(placed) + len(skipped) == 40
    plt.close(fig)


def test_place_labels_biggest_area_wins_and_spread_labels_all_fit():
    fig, ax = _sheet()
    placed, skipped = place_labels(ax, [("Small", 500, 400, 1), ("Big", 500, 400, 99)])
    assert [t.get_text() for t in placed] == ["Big"] and skipped == ["Small"]
    plt.close(fig)
    fig, ax = _sheet()
    items = [(f"D{i}", 100 + (i % 6) * 150, 100 + (i // 6) * 120, 1) for i in range(30)]
    assert place_labels(ax, items)[1] == []
    plt.close(fig)


@pytest.mark.parametrize("value,bounds,expected", [
    ("auto", (520e3, 3440e3, 990e3, 4100e3), False),   # Khyber Pakhtunkhwa: tall -> portrait
    ("auto", (700e3, 3750e3, 745e3, 3775e3), True),    # Peshawar city: wide -> landscape
    (True, (0, 0, 1, 9), True), (False, (0, 0, 9, 1), False),
    ("portrait", (0, 0, 9, 1), False), ("landscape", (0, 0, 1, 9), True)])
def test_pick_landscape(value, bounds, expected):
    assert pick_landscape(value, bounds) is expected
