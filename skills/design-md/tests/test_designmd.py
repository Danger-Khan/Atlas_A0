# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Test suite for the design-md tools. Run from the skill folder:

    python -m unittest discover -s tests -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)

import check_adherence as ca  # noqa: E402
import designmd as dm  # noqa: E402
import extract_tokens as et  # noqa: E402
import lint_design as ld  # noqa: E402

EXAMPLE = os.path.join(ROOT, "examples", "geo-portal")
EXAMPLE_DESIGN = os.path.join(EXAMPLE, "DESIGN.md")
TEMPLATE = os.path.join(ROOT, "templates", "DESIGN.template.md")
BROKEN = os.path.join(ROOT, "tests", "fixtures", "DESIGN.broken.md")


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def run_tool(script, *args):
    proc = subprocess.run([sys.executable, os.path.join(TOOLS, script)] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return proc.returncode, proc.stdout, proc.stderr


class ColourMaths(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(dm.contrast("#000000", "#ffffff"), 21.0, places=2)

    def test_same_colour_is_1(self):
        self.assertAlmostEqual(dm.contrast("#336699", "#336699"), 1.0, places=6)

    def test_contrast_is_symmetric(self):
        self.assertAlmostEqual(dm.contrast("#0b6674", "#ffffff"), dm.contrast("#ffffff", "#0b6674"))

    def test_known_value_grey_777_on_white(self):
        # widely published reference value: #777 on white is 4.48:1 (just under AA)
        self.assertAlmostEqual(dm.contrast("#777777", "#ffffff"), 4.48, places=2)

    def test_normalize_hex(self):
        self.assertEqual(dm.normalize_hex("#ABC"), "#aabbcc")
        self.assertEqual(dm.normalize_hex("#AABBCCDD"), "#aabbcc")

    def test_font_names_drop_generics_and_quotes(self):
        self.assertEqual(dm.font_names('"Source Sans 3", system-ui, sans-serif'), ["source sans 3"])


class SpecParsing(unittest.TestCase):
    def test_example_parses_cleanly(self):
        spec = dm.load_spec(EXAMPLE_DESIGN)
        self.assertTrue(spec.has_block)
        self.assertEqual(spec.problems, [])
        self.assertEqual(spec.space_base, 4)
        self.assertEqual(spec.radii, {4, 8, 12})
        self.assertIn("color.primary", spec.colors)
        self.assertEqual(len(spec.pairs), 8)
        self.assertEqual(spec.fonts, {"source sans 3", "ibm plex mono"})

    def test_bad_lines_are_reported(self):
        text = "```design-tokens\ncolor.bg = red\nnonsense\nspace.base = zero\npair = a on b\n```"
        spec = dm.parse_spec(text)
        self.assertEqual(len(spec.problems), 4)

    def test_duplicate_token_reported(self):
        text = "```design-tokens\ncolor.bg = #fff\ncolor.bg = #000\n```"
        self.assertTrue(any("duplicate" in p for p in dm.parse_spec(text).problems))

    def test_headings_inside_code_fences_are_ignored(self):
        text = "# Real\n```\n# not a heading\n```\n## Also real\n"
        self.assertEqual([s["title"] for s in dm.parse_sections(text)], ["Real", "Also real"])


class Linter(unittest.TestCase):
    def test_example_passes_with_no_warnings(self):
        result = ld.lint(read(EXAMPLE_DESIGN), EXAMPLE_DESIGN)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])

    def test_template_has_no_errors_but_warns_about_todo(self):
        result = ld.lint(read(TEMPLATE), TEMPLATE)
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("TODO" in w for w in result["warnings"]))

    def test_broken_fixture_reports_each_defect(self):
        result = ld.lint(read(BROKEN), BROKEN)
        joined = "\n".join(result["errors"])
        self.assertIn("missing section: components", joined)
        self.assertIn("missing section: agent prompt guide", joined)
        self.assertIn("color.primary is not a #rgb/#rrggbb colour", joined)
        self.assertIn("contrast color.text on color.bg", joined)
        self.assertIn("unknown token", joined)
        self.assertIn("space.base token missing", joined)

    def test_removing_a_section_is_an_error(self):
        text = read(EXAMPLE_DESIGN).replace("## 8. Responsive behavior", "## 8. Something else")
        result = ld.lint(text)
        self.assertEqual(result["errors"], ["missing section: responsive behavior"])

    def test_duplicate_colours_warn_only_within_one_family(self):
        head = ("## Theme\n## Colors\n## Typography\n## Components\n## Layout\n## Elevation\n"
                "## Do's and don'ts\n## Responsive\n## Agent prompt\n")
        base = "color.bg = #FFFFFF\ncolor.text = #111111\ncolor.primary = #0B6674\nfont.sans = Foo\nspace.base = 4\n"
        same_family = head + "```design-tokens\n" + base + "color.risk-a = #AA0000\ncolor.risk-b = #AA0000\n```"
        cross_family = head + "```design-tokens\n" + base + "color.risk-a = #AA0000\ncolor.gui-a = #AA0000\n```"
        warned = [w for w in ld.lint(same_family)["warnings"] if "same colour" in w]
        self.assertEqual(len(warned), 1)
        self.assertIn("risk tokens", warned[0])
        self.assertEqual([w for w in ld.lint(cross_family)["warnings"] if "same colour" in w], [])

    def test_per_pair_minimum_overrides_default(self):
        base = ("## Theme\n## Colors\n## Typography\n## Components\n## Layout\n## Elevation\n"
                "## Do's and don'ts\n## Responsive\n## Agent prompt\n")
        tokens = ("```design-tokens\ncolor.bg = #FFFFFF\ncolor.text = #777777\ncolor.primary = #0B6674\n"
                  "font.sans = Foo\nspace.base = 4\npair = color.text on color.bg min 3\n```\n")
        result = ld.lint(base + tokens)
        self.assertEqual(result["errors"], [])  # 4.48 >= 3
        result = ld.lint(base + tokens.replace(" min 3", ""))
        self.assertEqual(len(result["errors"]), 1)  # 4.48 < 4.5

    def test_cli_exit_codes(self):
        self.assertEqual(run_tool("lint_design.py", EXAMPLE_DESIGN)[0], 0)
        self.assertEqual(run_tool("lint_design.py", BROKEN)[0], 1)
        self.assertEqual(run_tool("lint_design.py", TEMPLATE)[0], 0)
        self.assertEqual(run_tool("lint_design.py", TEMPLATE, "--strict")[0], 1)
        self.assertEqual(run_tool("lint_design.py", "no-such-file.md")[0], 2)

    def test_cli_json_output_is_valid(self):
        code, out, _ = run_tool("lint_design.py", EXAMPLE_DESIGN, "--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "PASS")


class Adherence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = dm.load_spec(EXAMPLE_DESIGN)

    def scan(self, text, **kw):
        return ca.scan_text(text, self.spec, "t.css", **kw)

    def test_good_site_has_no_findings(self):
        result = ca.scan([os.path.join(EXAMPLE, "site-good")], self.spec)
        self.assertEqual(result["files"], 2)
        self.assertEqual(result["findings"], [])

    def test_bad_site_findings(self):
        result = ca.scan([os.path.join(EXAMPLE, "site-bad")], self.spec)
        kinds = {}
        for f in result["findings"]:
            kinds.setdefault((f["kind"], f["severity"]), []).append(f["message"])
        colour_msgs = " ".join(kinds[("color", "error")])
        for expected in ("#123", "#ff00aa", "#7928ca", "#eee", "#bada55", "#00ff00", "#FFD700", "#FF0000"):
            self.assertIn(expected, colour_msgs)
        self.assertIn("rgb(10, 200, 30)", colour_msgs)
        font_msgs = " ".join(kinds[("font", "error")])
        for expected in ("comic sans ms", "papyrus", "inter"):
            self.assertIn(expected, font_msgs)
        spacing_msgs = " ".join(kinds[("spacing", "warning")])
        for expected in ("13px", "22px", "10px", "18px"):
            self.assertIn(expected, spacing_msgs)
        self.assertIn("7px", " ".join(kinds[("radius", "warning")]))

    def test_token_colours_pass_in_any_notation(self):
        css = "a{color:#0B6674} b{color:#0b6674} c{color:rgb(11,102,116)} d{color:#FFF} e{color:#ffffffff}"
        self.assertEqual(self.scan(css), [])

    def test_unknown_colour_suggests_nearest_token(self):
        findings = self.scan("a { color: #0c6775; }")
        self.assertEqual(len(findings), 1)
        self.assertIn("nearest color.primary", findings[0]["message"])

    def test_tolerance_accepts_near_miss(self):
        self.assertEqual(len(self.scan("a { color: #0c6775; }")), 1)
        self.assertEqual(self.scan("a { color: #0c6775; }", tolerance=3), [])

    def test_allow_lists(self):
        css = "a { color: #123456; font-family: Papyrus, fantasy; }"
        self.assertEqual(len(self.scan(css)), 2)
        self.assertEqual(self.scan(css, allow_colors=["#123456"], allow_fonts=["papyrus"]), [])

    def test_anchors_urls_and_line_starts_are_not_colours(self):
        html = '<a href="#add">x</a>\n<div id="bed"></div>\n.x { background: url(img.svg#fade); }\n#abc { margin: 0; }'
        self.assertEqual(self.scan(html), [])

    def test_var_and_generic_fonts_are_allowed(self):
        css = "a { font-family: var(--font-sans), sans-serif; } b { font-family: system-ui, monospace; }"
        self.assertEqual(self.scan(css), [])

    def test_small_and_zero_spacing_tolerated(self):
        css = "a { margin: 0 1px 2px 4px; padding: 16px 24px; gap: 8px; }"
        self.assertEqual(self.scan(css), [])

    def test_skips_node_modules_and_design_md_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "node_modules", "pkg"))
            with open(os.path.join(tmp, "node_modules", "pkg", "x.css"), "w") as fh:
                fh.write("a{color:#123456}")
            with open(os.path.join(tmp, "DESIGN.md"), "w") as fh:
                fh.write("color: #123456")
            with open(os.path.join(tmp, "ok.css"), "w") as fh:
                fh.write("a{color:#FFFFFF}")
            result = ca.scan([tmp], self.spec)
            self.assertEqual(result["files"], 1)
            self.assertEqual(result["findings"], [])

    def test_cli_exit_codes(self):
        good = os.path.join(EXAMPLE, "site-good")
        bad = os.path.join(EXAMPLE, "site-bad")
        self.assertEqual(run_tool("check_adherence.py", good, "--design", EXAMPLE_DESIGN)[0], 0)
        self.assertEqual(run_tool("check_adherence.py", bad, "--design", EXAMPLE_DESIGN)[0], 1)
        self.assertEqual(run_tool("check_adherence.py", good, "--design", "missing.md")[0], 2)
        self.assertEqual(run_tool("check_adherence.py", good, "--design", BROKEN.replace("DESIGN.broken", "nope"))[0], 2)

    def test_strict_fails_on_warnings_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "w.css"), "w") as fh:
                fh.write("a { padding: 13px; }")
            args = (tmp, "--design", EXAMPLE_DESIGN)
            self.assertEqual(run_tool("check_adherence.py", *args)[0], 0)
            self.assertEqual(run_tool("check_adherence.py", *(args + ("--strict",)))[0], 1)


class PythonScanning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = dm.load_spec(EXAMPLE_DESIGN)

    def scan(self, code):
        return ca.scan_text(code, self.spec, "m.py")

    def test_token_colours_pass(self):
        self.assertEqual(self.scan('a = dict(bg="#F4F7F8", fg="#13242b")\nlabel(fg="#fff")'), [])

    def test_unknown_colour_literal_is_flagged_with_nearest(self):
        findings = self.scan('color = "#d62728"')
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["kind"], "color")
        self.assertIn("nearest", findings[0]["message"])

    def test_docstrings_help_text_and_partial_strings_are_ignored(self):
        code = ('"""Example: color=#d62728 and #900 in prose."""\n'
                'HELP = "Proposed site=#d62728 Canal=#1f77b4"\n'
                'x = f"{a}#abc"\n')
        self.assertEqual(self.scan(code), [])

    def test_font_keywords_checked(self):
        code = ('ax.text(0, 0, "x", fontfamily="Papyrus")\n'
                'tk.Label(font=("Comic Sans MS", 10))\n'
                'ok.Label(font=("Source Sans 3", 10), family="IBM Plex Mono")\n'
                'fine = dict(fontfamily="sans-serif")\n')
        findings = self.scan(code)
        self.assertEqual(sorted(f["message"].split("'")[1] for f in findings), ["comic sans ms", "papyrus"])

    def test_padding_keywords_and_constants(self):
        code = "PAD = 6\nw.pack(padx=PAD, pady=13)\nw.grid(padx=(12, 5), pady=2)\n"
        findings = self.scan(code)
        self.assertEqual(sorted(f["message"].split("px")[0] for f in findings), ["13", "5", "6"])
        self.assertTrue(all(f["severity"] == "warning" for f in findings))

    def test_syntax_error_is_a_warning_not_a_crash(self):
        findings = self.scan("def broken(:\n")
        self.assertEqual([f["kind"] for f in findings], ["parse"])
        self.assertEqual(findings[0]["severity"], "warning")

    def test_extractor_reads_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "a.py"), "w") as fh:
                fh.write('A = "#112233"\nB = "#112233"\nC = "#abcdef"\n'
                         'w.pack(padx=8, pady=16)\nlabel(font=("Foo Sans", 9))\n')
            out = et.render(et.extract([tmp]))
            self.assertIn("color.c1 = #112233   // used 2 time(s)", out)
            self.assertIn("font.f1 = Foo Sans", out)
            self.assertIn("space.base = 4", out)  # only 2 pad values, below the 3 needed to pick 8


class Extractor(unittest.TestCase):
    def test_extracts_frequency_ordered_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "a.css"), "w") as fh:
                fh.write("a{color:#112233;margin:16px}b{color:#112233;padding:24px}c{color:#abcdef;gap:8px}"
                         "d{font-family:'Foo Sans',sans-serif}")
            out = et.render(et.extract([tmp]))
            self.assertIn("```design-tokens", out)
            self.assertIn("color.c1 = #112233   // used 2 time(s)", out)
            self.assertIn("color.c2 = #ABCDEF", out)
            self.assertIn("font.f1 = Foo Sans", out)
            self.assertIn("space.base = 8", out)

    def test_font_case_preserved_and_base_stays_4_on_4px_grid(self):
        out = et.render(et.extract([os.path.join(EXAMPLE, "site-good")]))
        self.assertIn("font.f2 = IBM Plex Mono", out)
        self.assertIn("space.base = 4", out)

    def test_extracted_block_parses_back(self):
        out = et.render(et.extract([os.path.join(EXAMPLE, "site-good")]))
        spec = dm.parse_spec(out)
        self.assertTrue(spec.has_block)
        self.assertEqual(spec.problems, [])
        self.assertIn("#0b6674", spec.colors.values())


if __name__ == "__main__":
    unittest.main()
