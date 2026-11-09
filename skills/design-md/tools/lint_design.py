# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Lint a DESIGN.md: required sections, token block, colour validity, WCAG contrast.

Usage:
    python lint_design.py [DESIGN.md] [--min-contrast 4.5] [--strict] [--json]

Exit codes: 0 = no errors, 1 = errors (or warnings with --strict), 2 = file unreadable.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import designmd as dm  # noqa: E402

REQUIRED_SECTIONS = [
    ("theme & atmosphere", r"theme|atmosphere|overview|mood"),
    ("color palette", r"colou?r|palette"),
    ("typography", r"typograph|\bfonts?\b"),
    ("components", r"component"),
    ("layout & spacing", r"layout|spacing|grid"),
    ("depth & elevation", r"depth|elevation|shadow"),
    ("do's and don'ts", r"do'?s\s*(?:and|&|/)\s*don'?ts?"),
    ("responsive behavior", r"responsive|breakpoint"),
    ("agent prompt guide", r"agent|prompt"),
]
REQUIRED_TOKENS = ["color.bg", "color.text", "color.primary"]


def lint(text: str, path: str = "", min_contrast: float = 4.5) -> dict:
    errors, warnings, info = [], [], []

    # 1. sections -----------------------------------------------------------
    sections = dm.parse_sections(text)
    titled = [(dm.norm_title(s["title"]), s) for s in sections]
    for label, pattern in REQUIRED_SECTIONS:
        hits = [s for t, s in titled if re.search(pattern, t)]
        if not hits:
            errors.append("missing section: %s" % label)
            continue
        if label == "do's and don'ts":
            bullets = sum(1 for s in hits for ln in s["body"] if re.match(r"\s*[-*]\s+\S", ln))
            if bullets < 4:
                warnings.append("do's and don'ts has only %d bullet(s); aim for 4+ concrete rules" % bullets)
    info.append("sections found: %d headings" % len(sections))

    # 2. tokens -------------------------------------------------------------
    spec = dm.parse_spec(text, path)
    if not spec.has_block:
        errors.append("no ```design-tokens``` block found (machine-readable tokens are required)")
    else:
        errors.extend(spec.problems)
        for key in REQUIRED_TOKENS:
            if key not in spec.colors:
                errors.append("required token missing or invalid: %s" % key)
        if not spec.font_tokens:
            errors.append("no font.* token declared (e.g. font.sans = Source Sans 3, system-ui, sans-serif)")
        if spec.space_base is None:
            errors.append("space.base token missing (e.g. space.base = 4)")
        info.append("tokens: %d colours, %d font stacks, space.base=%s, %d radii"
                    % (len(spec.colors), len(spec.font_tokens), spec.space_base, len(spec.radii)))

        # 3. duplicate colour values ---------------------------------------
        # '*-contrast' tokens (the text colour that sits on a fill) legitimately repeat
        # another colour, e.g. white on the primary button, so they are not flagged.
        # Only duplicates inside one token family are flagged (color.landuse-retail vs
        # color.landuse-commercial). Different families may share a value on purpose: a GUI
        # background and a dark-theme text colour are different roles.
        seen = {}
        for name, value in spec.colors.items():
            if "contrast" in name:
                continue
            family = name[len("color."):].split("-")[0]
            seen.setdefault((family, value), []).append(name)
        for (family, value), names in seen.items():
            if len(names) > 1:
                warnings.append("same colour %s used by several %s tokens: %s" % (value, family, ", ".join(names)))

        # 4. contrast pairs ---------------------------------------------------
        if not spec.pairs:
            warnings.append("no 'pair = color.fg on color.bg' lines; contrast is not being verified")
        for fg, bg, minimum, lineno in spec.pairs:
            if fg not in spec.colors or bg not in spec.colors:
                missing = [n for n in (fg, bg) if n not in spec.colors]
                errors.append("line %d: pair references unknown token(s): %s" % (lineno, ", ".join(missing)))
                continue
            need = minimum if minimum is not None else min_contrast
            ratio = dm.contrast(spec.colors[fg], spec.colors[bg])
            if ratio + 1e-9 < need:
                errors.append("line %d: contrast %s on %s = %.2f:1, needs %.1f:1"
                              % (lineno, fg, bg, ratio, need))
            else:
                info.append("contrast ok: %s on %s = %.2f:1 (min %.1f)" % (fg, bg, ratio, need))

    # 5. leftovers --------------------------------------------------------------
    todo = len(re.findall(r"\bTODO\b", text))
    if todo:
        warnings.append("%d TODO placeholder(s) still in the file" % todo)

    return {"path": path, "errors": errors, "warnings": warnings, "info": info}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Lint a DESIGN.md")
    ap.add_argument("path", nargs="?", default="DESIGN.md")
    ap.add_argument("--min-contrast", type=float, default=4.5,
                    help="default WCAG ratio for pairs without 'min' (4.5 = AA body text)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)

    try:
        with open(args.path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print("cannot read %s: %s" % (args.path, exc), file=sys.stderr)
        return 2

    result = lint(text, args.path, args.min_contrast)
    failed = bool(result["errors"]) or (args.strict and bool(result["warnings"]))
    result["status"] = "FAIL" if failed else "PASS"

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("design-md lint: %s" % args.path)
        for line in result["info"]:
            print("  info    %s" % line)
        for line in result["warnings"]:
            print("  WARN    %s" % line)
        for line in result["errors"]:
            print("  ERROR   %s" % line)
        print("result: %s (%d error(s), %d warning(s))"
              % (result["status"], len(result["errors"]), len(result["warnings"])))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
