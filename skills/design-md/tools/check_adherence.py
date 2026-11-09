# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Check that UI source files only use the colours, fonts and spacing declared in DESIGN.md.

Usage:
    python check_adherence.py [PATH ...] [--design DESIGN.md] [--tolerance 0]
                              [--allow-color #hex ...] [--allow-font NAME ...]
                              [--strict] [--json]

PATH may be files or folders (default: current folder). Exit codes:
    0 = pass, 1 = colour/font violations (or any finding with --strict),
    2 = DESIGN.md missing/unreadable or has no token block.

Scope and limits: web files are scanned with regexes. They are read for hex colours and
rgb()/rgba() literals, font-family declarations, margin/padding/gap px values and border-radius
px values. It does not evaluate CSS-in-JS expressions, Tailwind classes, hsl() or named colours.
Python files (.py) are parsed with `ast`: only string literals that are entirely a hex colour
("#d62728"), font names passed as fontfamily=/family=/font=("Name", n), and integer
padx/pady/pad/NAME_PAD values are checked. Colours built at run time, ttk style names and
system colours are not seen.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import designmd as dm  # noqa: E402

EXTENSIONS = {".css", ".scss", ".sass", ".less", ".html", ".htm", ".jsx", ".tsx",
              ".js", ".ts", ".vue", ".svelte", ".astro", ".py"}

# Python (Tkinter / matplotlib / PyQt style code) is read with the ast module, not regexes.
PY_HEX_FULL = re.compile(r"^#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")
PY_FONT_KWARGS = {"fontfamily", "font_family", "family", "fontname"}
PY_PAD_KWARGS = {"padx", "pady", "ipadx", "ipady", "pad"}


def _const_ints(node):
    """Integer literals in a node: 6, (6, 0), [4, 8]. Anything else yields nothing."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        yield node.value
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            for v in _const_ints(elt):
                yield v


def py_literals(text):
    """Yield (lineno, kind, value) for design-relevant literals in Python source.

    kinds: 'color'  a string that is entirely a hex colour ("#d62728"), so docstrings and help
                    text that merely mention a colour are ignored
           'font'   family names from fontfamily=/family=/font=("Name", size) keyword arguments
           'pad'    integer padding from padx=/pady=/pad= keywords and NAME_PAD = <int> assignments
    Raises SyntaxError if the source does not parse.
    """
    tree = ast.parse(text)
    # literal chunks of f-strings (f"{a}#abc") are fragments, not colour values
    fstring_parts = set(id(v) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr)
                        for v in n.values if isinstance(v, ast.Constant))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in fstring_parts and PY_HEX_FULL.match(node.value.strip()):
                yield node.lineno, "color", node.value.strip()
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg in PY_FONT_KWARGS and isinstance(kw.value, ast.Constant) \
                        and isinstance(kw.value.value, str):
                    yield kw.value.lineno, "font", kw.value.value
                elif kw.arg == "font" and isinstance(kw.value, (ast.Tuple, ast.List)) and kw.value.elts \
                        and isinstance(kw.value.elts[0], ast.Constant) and isinstance(kw.value.elts[0].value, str):
                    yield kw.value.lineno, "font", kw.value.elts[0].value
                elif kw.arg in PY_PAD_KWARGS:
                    for n in _const_ints(kw.value):
                        yield kw.value.lineno, "pad", n
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and (node.targets[0].id == "PAD" or node.targets[0].id.endswith("_PAD")):
            for n in _const_ints(node.value):
                yield node.value.lineno, "pad", n
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__", ".venv", "venv",
             ".next", ".nuxt", "coverage", ".claude"}

HEX = re.compile(r"(?<![\w&#])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![\w-])")
RGB = re.compile(r"rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})", re.I)
FONT_CSS = re.compile(r"font-family\s*:\s*([^;{}]+)", re.I)
FONT_JS = re.compile(r"""fontFamily\s*:\s*(["'`])(.*?)\1""")
SPACING = re.compile(r"(?:^|[\s;{\"'])(?:margin|padding|gap|row-gap|column-gap)(?:-[a-z]+)*\s*:\s*([^;{}\"']+)", re.I)
RADIUS = re.compile(r"border-radius\s*:\s*([^;{}\"']+)", re.I)
PX = re.compile(r"(-?\d+(?:\.\d+)?)px")
ANCHOR_CTX = re.compile(r"""(?:href|id|for|name|to|data-target)\s*=\s*["']?$""", re.I)


def iter_files(paths):
    for root in paths:
        if os.path.isfile(root):
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                if os.path.splitext(name)[1].lower() in EXTENSIONS:
                    yield os.path.join(dirpath, name)


def _in_url(prefix: str) -> bool:
    return re.search(r"""url\(\s*["']?[^)]*$""", prefix) is not None


def _nearest(color: str, spec: dm.Spec):
    best = None
    for name, value in spec.colors.items():
        d = dm.rgb_distance(color, value)
        if best is None or d < best[0]:
            best = (d, name, value)
    return best


def scan_text(text, spec, filename, tolerance=0, allow_colors=(), allow_fonts=()):
    findings = []
    allowed_colors = set(dm.normalize_hex(c) for c in allow_colors)
    allowed_colors.update(spec.colors.values())
    allowed_fonts = set(f.lower() for f in allow_fonts) | spec.fonts

    if filename.lower().endswith(".py"):
        return _scan_python(text, spec, filename, tolerance, allowed_colors, allowed_fonts)

    def check_color(hexval, lineno, literal):
        color = dm.normalize_hex(hexval)
        if color in allowed_colors:
            return
        near = _nearest(color, spec)
        if near and near[0] <= tolerance:
            return
        hint = " (nearest %s %s)" % (near[1], near[2]) if near else ""
        findings.append({"file": filename, "line": lineno, "severity": "error", "kind": "color",
                         "message": "%s is not in DESIGN.md%s" % (literal, hint)})

    for lineno, line in enumerate(text.splitlines(), 1):
        for m in HEX.finditer(line):
            prefix = line[:m.start()]
            if prefix.strip() == "" or ANCHOR_CTX.search(prefix) or _in_url(prefix):
                continue
            check_color("#" + m.group(1)[:6] if len(m.group(1)) == 8 else "#" + m.group(1),
                        lineno, "#" + m.group(1))
        for m in RGB.finditer(line):
            r, g, b = (min(255, int(m.group(i))) for i in (1, 2, 3))
            check_color(dm.rgb_to_hex(r, g, b), lineno, "rgb(%d, %d, %d)" % (r, g, b))

        families = [m.group(1) for m in FONT_CSS.finditer(line)] + \
                   [m.group(2) for m in FONT_JS.finditer(line)]
        for value in families:
            if "var(" in value or "$" in value or "@" in value or "{" in value:
                continue
            for name in dm.font_names(value):
                if name not in allowed_fonts:
                    findings.append({"file": filename, "line": lineno, "severity": "error",
                                     "kind": "font",
                                     "message": "font '%s' is not in DESIGN.md (allowed: %s)"
                                                % (name, ", ".join(sorted(spec.fonts)) or "none")})

        if spec.space_base:
            for m in SPACING.finditer(line):
                value = m.group(1)
                if "calc" in value or "var(" in value:
                    continue
                for px in PX.findall(value):
                    n = abs(float(px))
                    if n in (0, 1, 2) or n % spec.space_base == 0:
                        continue
                    findings.append({"file": filename, "line": lineno, "severity": "warning",
                                     "kind": "spacing",
                                     "message": "%spx is not a multiple of space.base (%dpx)"
                                                % (px, spec.space_base)})
        if spec.radii:
            for m in RADIUS.finditer(line):
                value = m.group(1)
                if "var(" in value or "calc" in value:
                    continue
                for px in PX.findall(value):
                    n = int(float(px))
                    if n == 0 or n >= 999 or n in spec.radii:
                        continue
                    findings.append({"file": filename, "line": lineno, "severity": "warning",
                                     "kind": "radius",
                                     "message": "border-radius %spx is not in radius.* tokens (%s)"
                                                % (px, ", ".join(str(r) for r in sorted(spec.radii)))})
    return findings


def _scan_python(text, spec, filename, tolerance, allowed_colors, allowed_fonts):
    findings = []
    try:
        literals = list(py_literals(text))
    except SyntaxError as exc:
        return [{"file": filename, "line": exc.lineno or 1, "severity": "warning", "kind": "parse",
                 "message": "could not parse Python file, skipped (%s)" % exc.msg}]
    for lineno, kind, value in literals:
        if kind == "color":
            color = dm.normalize_hex(value)
            if color in allowed_colors:
                continue
            near = _nearest(color, spec)
            if near and near[0] <= tolerance:
                continue
            hint = " (nearest %s %s)" % (near[1], near[2]) if near else ""
            findings.append({"file": filename, "line": lineno, "severity": "error", "kind": "color",
                             "message": "%s is not in DESIGN.md%s" % (value, hint)})
        elif kind == "font":
            for name in dm.font_names(value):
                if name not in allowed_fonts:
                    findings.append({"file": filename, "line": lineno, "severity": "error", "kind": "font",
                                     "message": "font '%s' is not in DESIGN.md (allowed: %s)"
                                                % (name, ", ".join(sorted(spec.fonts)) or "none")})
        elif kind == "pad" and spec.space_base:
            n = abs(value)
            if n in (0, 1, 2) or n % spec.space_base == 0:
                continue
            findings.append({"file": filename, "line": lineno, "severity": "warning", "kind": "spacing",
                             "message": "%dpx padding is not a multiple of space.base (%dpx)"
                                        % (value, spec.space_base)})
    return findings


def scan(paths, spec, tolerance=0, allow_colors=(), allow_fonts=()):
    files, findings = 0, []
    for path in iter_files(paths):
        if os.path.basename(path).lower() == "design.md":
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        files += 1
        findings.extend(scan_text(text, spec, path, tolerance, allow_colors, allow_fonts))
    return {"files": files, "findings": findings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check UI files against DESIGN.md tokens")
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--design", default=None, help="path to DESIGN.md (default: ./DESIGN.md)")
    ap.add_argument("--tolerance", type=float, default=0.0,
                    help="max RGB distance still treated as a token colour (default 0 = exact)")
    ap.add_argument("--allow-color", action="append", default=[], metavar="HEX")
    ap.add_argument("--allow-font", action="append", default=[], metavar="NAME")
    ap.add_argument("--strict", action="store_true", help="warnings also fail the run")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    design = args.design or "DESIGN.md"
    try:
        spec = dm.load_spec(design)
    except OSError as exc:
        print("cannot read %s: %s" % (design, exc), file=sys.stderr)
        return 2
    if not spec.has_block:
        print("%s has no ```design-tokens``` block; run lint_design.py first" % design, file=sys.stderr)
        return 2

    result = scan(args.paths, spec, args.tolerance, args.allow_color, args.allow_font)
    errors = [f for f in result["findings"] if f["severity"] == "error"]
    warnings = [f for f in result["findings"] if f["severity"] == "warning"]
    failed = bool(errors) or (args.strict and bool(warnings))
    status = "FAIL" if failed else "PASS"

    if args.json:
        print(json.dumps({"design": design, "files": result["files"], "status": status,
                          "errors": len(errors), "warnings": len(warnings),
                          "findings": result["findings"]}, indent=2))
    else:
        print("design-md adherence report")
        print("  spec   : %s (%d colours, %d fonts, base %s px)"
              % (design, len(spec.colors), len(spec.fonts), spec.space_base))
        print("  scanned: %d file(s)" % result["files"])
        for f in result["findings"]:
            print("  %-7s %s:%d [%s] %s" % (f["severity"].upper(), f["file"], f["line"], f["kind"], f["message"]))
        print("result: %s (%d error(s), %d warning(s))" % (status, len(errors), len(warnings)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
