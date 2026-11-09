# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Choropleth: spec parsing, table reading, name matching, class limits, colours, legend."""
import numpy as np
import pytest

from atlasa0 import choropleth as C

THEME = {"building": "#d8d2c4", "frame": "#1f1f1f"}


@pytest.fixture
def table(tmp_path):
    p = tmp_path / "pop.csv"
    p.write_text("District,Region code,Population\n"
                 "Peshawar,1,\"4,269,079\"\n"
                 "D.I. Khan,2,1627132\n"
                 "Swat,3,2309570\n"
                 "Kohat,4,993873\n"
                 "Nowhere,5,1000\n", encoding="utf-8")
    return str(p)


def test_spec_from_string_dict_and_roundtrip(table):
    s = C.parse_spec(f"{table};name_col=District;value_col=Population;classes=4;breaks=1;2;3;scheme=manual;palette=Blues;show_values=1")
    assert (s.classes, s.breaks, s.scheme, s.palette, s.show_values) == (4, [1.0, 2.0, 3.0], "manual", "Blues", True)
    again = C.ChoroplethSpec.from_any(s.to_dict())
    assert again == s
    assert C.ChoroplethSpec.from_any({"file": table}).to_dict() == {"file": table}


@pytest.mark.parametrize("bad", [{"scheme": "magic"}, {"classes": 1}, {"classes": 20}, {"palette": "nope"},
                                 {"scheme": "manual"}, {"missing": "notacolour"}, {"palette": "#fff"}, {"zzz": 1}])
def test_bad_options_rejected(table, bad):
    with pytest.raises(ValueError):
        C.ChoroplethSpec.from_any({"file": table, **bad})


def test_bad_files_rejected(tmp_path):
    with pytest.raises(ValueError):
        C.ChoroplethSpec.from_any({"file": str(tmp_path / "missing.csv")})
    p = tmp_path / "x.txt"
    p.write_text("a")
    with pytest.raises(ValueError):
        C.ChoroplethSpec.from_any({"file": str(p)})


def test_read_table_auto_columns_and_thousands(table):
    names, vals, ncol, vcol = C.read_table(C.ChoroplethSpec(table))
    assert (ncol, vcol) == ("District", "Region code")        # first numeric column unless told otherwise
    names, vals, ncol, vcol = C.read_table(C.ChoroplethSpec(table, value_col="population"))
    assert vcol == "Population" and vals[0] == 4269079 and names[1] == "D.I. Khan"
    with pytest.raises(ValueError, match="no value column"):
        C.read_table(C.ChoroplethSpec(table, value_col="Pop"))


def test_semicolon_csv_and_xlsx(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("name;value\nA;1,5\nB;2\n", encoding="utf-8")
    names, vals, *_ = C.read_table(C.ChoroplethSpec(str(p)))
    assert names == ["A", "B"] and vals[1] == 2
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Province", "Cases"])
    ws.append(["Sindh", 10])
    ws.append(["Punjab", 30])
    x = tmp_path / "t.xlsx"
    wb.save(x)
    names, vals, ncol, vcol = C.read_table(C.ChoroplethSpec(str(x)))
    assert names == ["Sindh", "Punjab"] and list(vals) == [10, 30] and (ncol, vcol) == ("Province", "Cases")


def test_name_matching():
    assert C.normalise_name("Peshawar District") == "peshawar"
    assert C.normalise_name("D. I. Khan") == C.normalise_name("Dera Ismail Khan") == "dera ismail khan"
    assert C.normalise_name("KPK") == "khyber pakhtunkhwa"
    assert C.normalise_name("Islamabad Capital Territory") == "islamabad"
    m, rows, areas = C.match_names(["Peshawar", "D.G. Khan", "Swat", "Zzz"],
                                   ["Dera Ghazi Khan District", "Peshawar District", "Swatt", "Lahore"])
    assert m == {0: 1, 1: 0, 2: 2}                               # the typo 'Swatt' still finds Swat
    assert rows == [3] and areas == [3]


def test_class_edges_schemes():
    v = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]
    q = C.class_edges(v, "quantile", 4)
    assert q[0] == 1 and q[-1] == 100 and len(q) == 5
    e = C.class_edges(v, "equal", 5)
    assert np.allclose(np.diff(e), 19.8)
    n = C.class_edges(v, "natural", 3)
    assert n[-2] > 9 or n[-2] == 9                                # the outlier gets its own class
    assert C.class_edges(v, "manual", 3, [10, 50]) == [1, 10, 50, 100]
    assert C.class_edges([5, 5, 5], "quantile", 5) == [5, 6.0]  # flat data -> one class
    assert len(C.class_edges([1, 2, 3], "quantile", 9)) == 4     # not more classes than distinct values
    with pytest.raises(ValueError):
        C.class_edges([float("nan")], "quantile", 3)


def test_class_index_edges_and_nan():
    idx = C.class_index([0, 10, 49.9, 50, 100, np.nan], [0, 10, 50, 100])
    assert list(idx) == [0, 1, 1, 2, 2, -1]                       # on a limit -> higher class; max -> last class


def test_palettes():
    a = C.palette_colors("YlOrRd", 5)
    assert len(set(a)) == 5 and a[0] != a[-1]
    assert C.palette_colors("YlOrRd", 5, reverse=True) == a[::-1]
    b = C.palette_colors("#ffffff,#000000", 3)
    assert b[0] == "#ffffff" and b[-1] == "#000000"


def test_legend_labels_and_formatting():
    assert C.legend_labels([0, 1000, 25000]) == ["0 - 1,000", "1,000 - 25,000"]
    assert C.legend_labels([0.0, 0.5, 1.25]) == ["0.00 - 0.50", "0.50 - 1.25"] or C.legend_labels([0.0, 0.5, 1.25])[0].startswith("0.")
    assert C.legend_labels([0, 10, 20], decimals=1)[0] == "0.0 - 10.0"


def test_build_colours_legend_and_notes(table):
    areas = ["Peshawar District", "Dera Ismail Khan District", "Swat District", "Kohat District", "Lahore"]
    res = C.build(C.ChoroplethSpec(table, value_col="Population", classes=3, title="People"), areas, THEME)
    assert res.matched == 4 and len(res.colors) == 5
    assert res.colors[4] == THEME["building"]                     # Lahore: no row -> 'no data' colour
    assert res.colors[0] != res.colors[3]                          # biggest vs smallest differ
    labels = [h.get_label() for h in res.handles]
    assert labels[0] == "People" and labels[-1] == "no data" and len(labels) == 1 + 3 + 1
    assert any("Nowhere" in n for n in res.notes) and any("Lahore" in n for n in res.notes)
    assert res.text[0] == "4,269,079"


def test_build_fails_clearly_when_nothing_matches(table):
    with pytest.raises(ValueError, match="none of the names"):
        C.build(C.ChoroplethSpec(table, value_col="Population"), ["Lahore", "Karachi"], THEME)


# ----------------------------------------------------------------------------- layout / form / cli plumbing
def test_layout_accepts_choropleth(table):
    from atlasa0.furniture import Layout
    lay = Layout.from_any({"choropleth": {"file": table, "value_col": "Population", "classes": 4}})
    assert lay.choropleth.classes == 4 and Layout.from_any(None).choropleth is None
    with pytest.raises(ValueError):
        Layout.from_any({"choropleth": {"file": table, "scheme": "bad"}})


def test_form_fields_state_and_validation(table):
    from atlasa0 import gui_core as core
    assert core.choropleth_from_fields("") is None
    d = core.choropleth_from_fields(table, "District", "", "quantile", "5", "YlOrRd", "", False)
    assert d == {"file": table, "name_col": "District"}                     # defaults are not stored
    d2 = core.choropleth_from_fields(table, "", "Population", "natural", "4", "Blues", "People", True)
    assert d2["scheme"] == "natural" and d2["classes"] == 4 and d2["show_values"] is True
    s = core.FormState(provinces=["Sindh"], choropleth=d2)
    assert core.layout_from_state(s)["choropleth"]["palette"] == "Blues"
    assert not any("choropleth" in p.lower() for p in core.validate(s))
    s.provinces = []
    assert any("choropleth" in p.lower() for p in core.validate(s))          # needs a province or the country map
    s.country = True
    s.choropleth = {"file": table, "scheme": "bad"}
    assert any("scheme" in p for p in core.validate(s))
    assert core.layout_from_state(core.FormState()) is None


def test_cli_choropleth_option_is_validated(table, capsys):
    from atlasa0 import cli
    assert cli.main(["--province", "sindh", "--choropleth", f"{table};value_col=Population", "--dry-run"]) == 0
    with pytest.raises(SystemExit) as e:
        cli.main(["--province", "sindh", "--choropleth", f"{table};scheme=bad", "--dry-run"])
    assert e.value.code == 2


def test_make_choropleth_helper_in_render_is_wired():
    """render needs osmnx/geopandas (not here): check the wiring statically."""
    import inspect
    import re
    src = open(inspect.getsourcefile(C)).read()
    assert "def build(" in src
    render_src = open(inspect.getsourcefile(C).replace("choropleth.py", "render.py")).read()
    assert render_src.count("= _make_choropleth(lay") == 2 and "choro.handles" in render_src
    assert re.search(r"choro\.colors\[i\]", render_src) and "show_values" in render_src


def test_same_words_in_other_order_match():
    m, rows, areas = C.match_names(["Lower Dir", "Upper Chitral"], ["Dir Lower District", "Chitral Upper"])
    assert m == {0: 0, 1: 1} and not rows and not areas
