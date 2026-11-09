# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Shared helpers for the design-md tools. Standard library only (Python 3.8+)."""
from __future__ import annotations

import re

HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
TOKENS_RE = re.compile(r"```design-tokens[ \t]*\r?\n(.*?)```", re.S)
PAIR_RE = re.compile(
    r"^(color\.[\w.-]+)\s+on\s+(color\.[\w.-]+)(?:\s+min\s+([\d.]+))?$"
)

GENERIC_FONTS = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
    "ui-sans-serif", "ui-serif", "ui-monospace", "ui-rounded", "emoji", "math",
    "fangsong", "-apple-system", "blinkmacsystemfont", "inherit", "initial",
    "unset", "revert", "default",
}


# ---------------------------------------------------------------- colour maths
def normalize_hex(value: str) -> str:
    """'#ABC' -> '#aabbcc'; '#AABBCC' -> '#aabbcc'. 8-digit hex keeps RGB only."""
    v = value.strip().lower()
    if len(v) == 9:  # #rrggbbaa -> drop alpha
        v = v[:7]
    if len(v) == 4:
        v = "#" + "".join(c * 2 for c in v[1:])
    return v


def hex_to_rgb(value: str):
    v = normalize_hex(value)
    return tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#%02x%02x%02x" % (r, g, b)


def _lin(channel: int) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(value: str) -> float:
    r, g, b = hex_to_rgb(value)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a: str, b: str) -> float:
    """WCAG 2.x contrast ratio between two hex colours (1.0 .. 21.0)."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def rgb_distance(a: str, b: str) -> float:
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    return sum((x - y) ** 2 for x, y in zip(ra, rb)) ** 0.5


# --------------------------------------------------------------------- fonts
def font_names(value: str, keep_case: bool = False):
    """Split a font-family list into names (lowercase unless keep_case), generics removed."""
    names = []
    for part in value.split(","):
        name = part.strip().strip("'\"`").strip()
        name = re.sub(r"\s*!important$", "", name)
        if name and name.lower() not in GENERIC_FONTS:
            names.append(name if keep_case else name.lower())
    return names


# ------------------------------------------------------------------ sections
def norm_title(title: str) -> str:
    return title.lower().replace("’", "'").replace("`", "").strip()


def parse_sections(text: str):
    """Return [{'level','title','line','body':[lines]}] ignoring fenced code."""
    sections, cur, in_fence = [], None, False
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            if cur is not None:
                cur["body"].append(line)
            continue
        m = None if in_fence else HEADING_RE.match(line)
        if m:
            cur = {"level": len(m.group(1)), "title": m.group(2), "line": i, "body": []}
            sections.append(cur)
        elif cur is not None:
            cur["body"].append(line)
    return sections


# -------------------------------------------------------------------- tokens
class Spec(object):
    """Parsed ```design-tokens``` block of a DESIGN.md."""

    def __init__(self, path: str = ""):
        self.path = path
        self.has_block = False
        self.colors = {}        # 'color.bg' -> '#f4f7f8'
        self.font_tokens = {}   # 'font.sans' -> 'Source Sans 3, system-ui, sans-serif'
        self.fonts = set()      # lowercase non-generic names
        self.space_base = None  # int px
        self.radii = set()      # int px
        self.pairs = []         # (fg, bg, min_ratio, lineno)
        self.other = {}
        self.keys = {}
        self.problems = []      # token-level errors (strings)


def parse_spec(text: str, path: str = "") -> Spec:
    spec = Spec(path)
    m = TOKENS_RE.search(text)
    if not m:
        return spec
    spec.has_block = True
    first_line = text[:m.start(1)].count("\n") + 1
    for offset, raw in enumerate(m.group(1).splitlines()):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        lineno = first_line + offset
        if "=" not in line:
            spec.problems.append("line %d: expected 'key = value', got %r" % (lineno, line))
            continue
        key, value = [p.strip() for p in line.split("=", 1)]
        value = re.sub(r"\s+//.*$", "", value).strip()
        if key == "pair":
            pm = PAIR_RE.match(value)
            if not pm:
                spec.problems.append(
                    "line %d: bad pair %r (use: pair = color.a on color.b [min 4.5])" % (lineno, value))
            else:
                minimum = float(pm.group(3)) if pm.group(3) else None
                spec.pairs.append((pm.group(1), pm.group(2), minimum, lineno))
            continue
        if key in spec.keys:
            spec.problems.append("line %d: duplicate token %s" % (lineno, key))
        spec.keys[key] = value
        if key.startswith("color."):
            if HEX_RE.match(value):
                spec.colors[key] = normalize_hex(value)
            else:
                spec.problems.append("line %d: %s is not a #rgb/#rrggbb colour: %r" % (lineno, key, value))
        elif key.startswith("font."):
            names = font_names(value)
            if names:
                spec.font_tokens[key] = value
                spec.fonts.update(names)
            else:
                spec.problems.append("line %d: %s names no concrete font: %r" % (lineno, key, value))
        elif key == "space.base":
            try:
                base = int(re.sub(r"px$", "", value))
                if base <= 0:
                    raise ValueError
                spec.space_base = base
            except ValueError:
                spec.problems.append("line %d: space.base must be a positive integer (px): %r" % (lineno, value))
        elif key.startswith("radius."):
            try:
                spec.radii.add(int(re.sub(r"px$", "", value)))
            except ValueError:
                spec.problems.append("line %d: %s must be an integer (px): %r" % (lineno, key, value))
        else:
            spec.other[key] = value
    return spec


def load_spec(path) -> Spec:
    with open(str(path), "r", encoding="utf-8") as fh:
        return parse_spec(fh.read(), str(path))
