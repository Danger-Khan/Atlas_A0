Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# design-md skill

Gives a coding agent a design system it can read, and gives you scripts that check it was followed.
You keep a `DESIGN.md` in your project root; the agent builds UI from its tokens; two scripts verify
the result (spec quality and code adherence).

This is an original implementation of the "DESIGN.md" idea (a markdown design spec for agents). It
contains no content copied from other collections, and the example is not based on any real brand.

## Contents

```
design-md/
  SKILL.md                      agent instructions (the skill itself)
  README.md                     this file
  templates/DESIGN.template.md  blank spec, all nine sections
  examples/geo-portal/
    DESIGN.md                   worked example (geospatial risk dashboard)
    site-good/                  sample code that follows it
    site-bad/                   sample code that breaks it on purpose
  tools/
    designmd.py                 shared parser and colour maths
    lint_design.py              checks the DESIGN.md itself
    check_adherence.py          checks your source files against it
    extract_tokens.py           proposes tokens from an existing codebase
    generate_evidence.py        regenerates evidence/
  tests/                        32 unit tests plus a broken-spec fixture
  evidence/                     recorded outputs, MANIFEST.json, EVIDENCE.md
```

## Install

Requires Python 3.8+. No packages.

| Scope | Copy the `design-md` folder to |
|---|---|
| One project (shareable via git) | `<project>/.claude/skills/design-md/` |
| All your projects | `~/.claude/skills/design-md/` (Windows: `%USERPROFILE%\.claude\skills\design-md\`) |

Then, in the project:

1. Copy `templates/DESIGN.template.md` to `DESIGN.md` in the project root (or ask Claude to do it).
2. Fill it in. For an existing codebase start from `python .claude/skills/design-md/tools/extract_tokens.py src`.
3. Run the lint until it passes.
4. Ask Claude to build or restyle UI "using DESIGN.md". The skill's description also lets it trigger by itself.

## DESIGN.md format

Nine sections, matched by heading keyword (numbering and exact wording are free):

1. Visual theme & atmosphere
2. Color palette & roles
3. Typography
4. Component styling
5. Layout principles & spacing
6. Depth & elevation
7. Do's and don'ts (the linter wants four or more bullets)
8. Responsive behavior
9. Agent prompt guide (a short brief the agent can follow without reading the rest)

Plus one fenced block that the tools read:

````
```design-tokens
// comment
color.bg = #F4F7F8
color.text = #13242B
color.primary = #0B6674
color.primary-contrast = #FFFFFF
font.sans = Source Sans 3, system-ui, sans-serif
space.base = 4
radius.md = 8
pair = color.text on color.bg
pair = color.primary-contrast on color.primary min 4.5
```
````

| Key | Rule |
|---|---|
| `color.*` | `#rgb` or `#rrggbb`. Required: `color.bg`, `color.text`, `color.primary`. |
| `font.*` | Comma list; at least one concrete (non-generic) family. At least one `font.*` required. |
| `space.base` | Positive integer in px. Required. Spacing should be a multiple of it. |
| `radius.*` | Integer px. Optional; if present, border-radius values are checked. |
| `pair = fg on bg [min N]` | WCAG contrast the two colours must meet (default 4.5, set `min 3` for large text). |

Tokens whose name contains `contrast` (the text colour that sits on a fill) may repeat another colour
without a duplicate warning.

## The tools

All print a text report (`--json` where noted) and use exit codes you can gate CI on.

```bash
# 1. Is the spec itself sound?
python tools/lint_design.py DESIGN.md [--min-contrast 4.5] [--strict] [--json]
#    exit 0 ok | 1 errors (or warnings with --strict) | 2 file unreadable

# 2. Does the code follow the spec?
python tools/check_adherence.py src --design DESIGN.md \
       [--tolerance 0] [--allow-color #hex] [--allow-font name] [--strict] [--json]
#    exit 0 ok | 1 unknown colour/font (or any finding with --strict) | 2 spec missing or has no tokens

# 3. Bootstrap tokens from an existing project
python tools/extract_tokens.py src [--top 12]
```

What `check_adherence.py` reports:

| Kind | Severity | Trigger |
|---|---|---|
| color | error | hex or `rgb()/rgba()` not equal to a `color.*` token (shows the nearest token) |
| font | error | `font-family` / `fontFamily` name not in `font.*` (generics and `var()` allowed) |
| spacing | warning | margin/padding/gap px not a multiple of `space.base` (0, 1, 2px tolerated) |
| radius | warning | border-radius px not in `radius.*` (0 and 999px+ pills tolerated) |

Scanned: `.css .scss .sass .less .html .htm .jsx .tsx .js .ts .vue .svelte .astro`. Skipped:
`node_modules`, `.git`, `dist`, `build`, `.next`, `.nuxt`, `coverage`, virtualenvs, `.claude`, and `DESIGN.md`.

### Limits and false positives

- Regex based. It does not understand Tailwind classes, hsl()/named colours, CSS-in-JS expressions,
  images, or what actually renders. Open the page and look at it too.
- A hex-like string such as an element id (`#add`, `#fade`) can be mistaken for a colour when it appears
  in JS, for example `querySelector('#add')`. `href="#add"`, `id="..."`, `url(...)` and a `#id {` selector at
  the start of a line are already ignored. Use `--allow-color` for the rest.
- Fonts in `font:` shorthand are not read.
- Contrast is checked only for pairs you declare. Declare the pairs that matter.

## Tests

```bash
python -m unittest discover -s tests -v
```

32 tests cover colour maths (including the published 4.48:1 value for #777 on white), token parsing,
every lint rule, scanning behaviour, tolerance and allow-lists, ignore rules, CLI exit codes and the extractor.

## Evidence

`evidence/` holds the recorded output of the test suite and of each tool against the shipped fixtures,
including runs that are expected to fail. `EVIDENCE.md` explains each file, `MANIFEST.json` has the command,
expected and actual exit code, and SHA-256 of every file. Re-create it with:

```bash
python tools/generate_evidence.py     # exits non-zero if any run stops matching expectations
```

## Using it in CI

GitHub Actions:

```yaml
- uses: actions/setup-python@v5
  with: { python-version: "3.12" }
- run: python .claude/skills/design-md/tools/lint_design.py DESIGN.md --strict
- run: python .claude/skills/design-md/tools/check_adherence.py src --design DESIGN.md
```

Pre-commit hook (`.git/hooks/pre-commit`, make executable):

```bash
#!/bin/sh
python .claude/skills/design-md/tools/check_adherence.py src --design DESIGN.md || exit 1
```

## Using a real brand's look

You can study how a company's product is styled, but copying its colours, type and component details
closely for a public product can read as imitation and may raise trademark or trade-dress problems.
Derive your own palette, type and components, and keep the example in this folder as a model of a
spec, not a style to reuse.

## Known gaps

- Verified on Linux with Python 3.13 only. The code is standard library and uses `os.path`, so Windows and
  macOS should work, but run the tests there before relying on it.
- The example is a small fixture. It shows the method, not that the tools scale to a large monorepo.
