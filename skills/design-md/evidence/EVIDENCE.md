Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# Evidence

Recorded outputs showing the tools behave as documented. Regenerate with `python tools/generate_evidence.py`; it overwrites this folder and exits non-zero if any run stops matching its expected exit code.

- Generated: 2026-11-06 18:18:48Z
- Python: 3.13.18 on Linux-6.18.44-fc-v242-x86_64-with-glibc2.39
- Result: **all 9 runs matched expectations**

| File | What was run | Exit (expected / actual) | What it shows |
|---|---|---|---|
| `test_results.txt` | `python -m unittest discover -s tests -v` | 0 / 0 ok | All tool behaviours (contrast maths, parsing, lint rules, scanning, CLI exit codes) pass. |
| `lint_example.txt` | `python tools/lint_design.py examples/geo-portal/DESIGN.md` | 0 / 0 ok | A complete DESIGN.md passes with zero warnings and every contrast pair verified. |
| `lint_template.txt` | `python tools/lint_design.py templates/DESIGN.template.md` | 0 / 0 ok | The template is structurally valid; TODO placeholders surface as warnings. |
| `lint_template_strict.txt` | `python tools/lint_design.py templates/DESIGN.template.md --strict` | 1 / 1 ok | --strict turns placeholder warnings into a failing exit code (use in CI). |
| `lint_broken.txt` | `python tools/lint_design.py tests/fixtures/DESIGN.broken.md` | 1 / 1 ok | Missing sections, invalid hex, unknown pair token and low contrast are all caught. |
| `adherence_good.txt` | `python tools/check_adherence.py examples/geo-portal/site-good --design examples/geo-portal/DESIGN.md` | 0 / 0 ok | Code that uses only token colours, fonts and on-grid spacing passes (case and notation differences allowed). |
| `adherence_bad.txt` | `python tools/check_adherence.py examples/geo-portal/site-bad --design examples/geo-portal/DESIGN.md` | 1 / 1 ok | Off-palette colours, rgb() literals, foreign fonts, off-grid spacing and odd radii are reported with file and line. |
| `adherence_bad.json` | `python tools/check_adherence.py examples/geo-portal/site-bad --design examples/geo-portal/DESIGN.md --json` | 1 / 1 ok | Machine-readable findings for CI annotations. |
| `extract_good.txt` | `python tools/extract_tokens.py examples/geo-portal/site-good` | 0 / 0 ok | Bootstrapping a token block from existing code works and lists colours by frequency. |

## How to read the failures

`lint_broken.txt`, `lint_template_strict.txt`, `adherence_bad.txt` and `adherence_bad.json` are **expected to fail**. Their value is showing that the checks catch real defects with usable messages. `MANIFEST.json` holds a SHA-256 for every file so tampering or drift is detectable.

## What this evidence does not show

- It does not judge visual quality; the tools check tokens, not rendered pixels.
- It was produced on one OS and Python version (see above). The tools use only the standard library and `os.path`, but they have not been run on every platform.
- The sample sites are small fixtures, not a real production codebase.
