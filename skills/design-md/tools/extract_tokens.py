# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Propose a ```design-tokens``` block from an existing project, by frequency.

Use this to bootstrap a DESIGN.md for a codebase that already has a look. Output is a
starting point: rename colour tokens to roles (bg, surface, text, primary ...) by hand.

Usage:
    python extract_tokens.py [PATH ...] [--top 12]
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import designmd as dm  # noqa: E402
import check_adherence as ca  # noqa: E402


def extract(paths, top=12):
    colors, fonts, px_values = collections.Counter(), collections.Counter(), collections.Counter()
    display = {}  # lowercase font name -> first spelling seen
    files = 0
    for path in ca.iter_files(paths):
        if os.path.basename(path).lower() == "design.md":
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        files += 1
        if path.lower().endswith(".py"):
            try:
                for _lineno, kind, value in ca.py_literals(text):
                    if kind == "color":
                        colors[dm.normalize_hex(value)] += 1
                    elif kind == "font":
                        for name in dm.font_names(value, keep_case=True):
                            display.setdefault(name.lower(), name)
                            fonts[name.lower()] += 1
                    elif kind == "pad" and abs(value) > 2:
                        px_values[abs(value)] += 1
            except SyntaxError:
                pass
            continue
        for line in text.splitlines():
            for m in ca.HEX.finditer(line):
                prefix = line[:m.start()]
                if prefix.strip() == "" or ca.ANCHOR_CTX.search(prefix) or ca._in_url(prefix):
                    continue
                colors[dm.normalize_hex("#" + m.group(1))] += 1
            for m in ca.RGB.finditer(line):
                r, g, b = (min(255, int(m.group(i))) for i in (1, 2, 3))
                colors[dm.rgb_to_hex(r, g, b)] += 1
            for value in [m.group(1) for m in ca.FONT_CSS.finditer(line)] + \
                         [m.group(2) for m in ca.FONT_JS.finditer(line)]:
                if "var(" in value:
                    continue
                for name in dm.font_names(value, keep_case=True):
                    display.setdefault(name.lower(), name)
                    fonts[name.lower()] += 1
            for m in ca.SPACING.finditer(line):
                for px in ca.PX.findall(m.group(1)):
                    n = abs(float(px))
                    if n > 2:
                        px_values[int(n)] += 1
    return {"files": files, "colors": colors.most_common(top),
            "fonts": [(display[n], c) for n, c in fonts.most_common(4)], "px": px_values}


def guess_base(px_values) -> int:
    """8 only when every spacing value sits on an 8px grid; otherwise the safer 4."""
    total = sum(px_values.values())
    if total >= 3 and all(v % 8 == 0 for v in px_values):
        return 8
    return 4


def render(result) -> str:
    out = ["```design-tokens",
           "// Proposed by extract_tokens.py from %d file(s). Rename colours to roles by hand." % result["files"]]
    for i, (value, count) in enumerate(result["colors"], 1):
        out.append("color.c%d = %s   // used %d time(s)" % (i, value.upper(), count))
    for i, (name, count) in enumerate(result["fonts"], 1):
        out.append("font.f%d = %s   // used %d time(s)" % (i, name, count))
    out.append("space.base = %d" % guess_base(result["px"]))
    out.append("```")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Propose design tokens from existing code")
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--top", type=int, default=12, help="max colours to list")
    args = ap.parse_args(argv)
    print(render(extract(args.paths, args.top)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
