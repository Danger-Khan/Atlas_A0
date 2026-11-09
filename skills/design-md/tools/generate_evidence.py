# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Regenerate everything in evidence/ from scratch.

    python tools/generate_evidence.py

Runs the test suite and each tool against the shipped fixtures, records stdout and the exit code
of every run, compares the exit code with what the documentation promises, and writes
evidence/MANIFEST.json (with SHA-256 of every evidence file) and evidence/EVIDENCE.md.
Exit code is 0 only if every recorded run matched its expected result.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "evidence")
PY = sys.executable

EX = "examples/geo-portal"
RUNS = [
    # (output file, description, argv relative to ROOT, expected exit code, what it proves)
    ("test_results.txt", "Unit test suite", ["-m", "unittest", "discover", "-s", "tests", "-v"], 0,
     "All tool behaviours (contrast maths, parsing, lint rules, scanning, CLI exit codes) pass."),
    ("lint_example.txt", "Lint the worked example", ["tools/lint_design.py", EX + "/DESIGN.md"], 0,
     "A complete DESIGN.md passes with zero warnings and every contrast pair verified."),
    ("lint_template.txt", "Lint the blank template", ["tools/lint_design.py", "templates/DESIGN.template.md"], 0,
     "The template is structurally valid; TODO placeholders surface as warnings."),
    ("lint_template_strict.txt", "Lint the template with --strict", ["tools/lint_design.py", "templates/DESIGN.template.md", "--strict"], 1,
     "--strict turns placeholder warnings into a failing exit code (use in CI)."),
    ("lint_broken.txt", "Lint a deliberately broken spec", ["tools/lint_design.py", "tests/fixtures/DESIGN.broken.md"], 1,
     "Missing sections, invalid hex, unknown pair token and low contrast are all caught."),
    ("adherence_good.txt", "Scan the compliant sample site", ["tools/check_adherence.py", EX + "/site-good", "--design", EX + "/DESIGN.md"], 0,
     "Code that uses only token colours, fonts and on-grid spacing passes (case and notation differences allowed)."),
    ("adherence_bad.txt", "Scan the non-compliant sample site", ["tools/check_adherence.py", EX + "/site-bad", "--design", EX + "/DESIGN.md"], 1,
     "Off-palette colours, rgb() literals, foreign fonts, off-grid spacing and odd radii are reported with file and line."),
    ("adherence_bad.json", "Same scan, JSON output", ["tools/check_adherence.py", EX + "/site-bad", "--design", EX + "/DESIGN.md", "--json"], 1,
     "Machine-readable findings for CI annotations."),
    ("extract_good.txt", "Extract tokens from the compliant site", ["tools/extract_tokens.py", EX + "/site-good"], 0,
     "Bootstrapping a token block from existing code works and lists colours by frequency."),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    started = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    records, all_ok = [], True
    for fname, desc, argv, expected, proves in RUNS:
        proc = subprocess.run([PY] + argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True)
        ok = proc.returncode == expected
        all_ok = all_ok and ok
        header = "$ python %s\n# exit code: %d (expected %d)\n\n" % (" ".join(argv), proc.returncode, expected)
        path = os.path.join(OUT, fname)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(header + proc.stdout)
        records.append({"file": "evidence/" + fname, "description": desc, "command": "python " + " ".join(argv),
                        "expected_exit": expected, "actual_exit": proc.returncode, "match": ok, "proves": proves,
                        "sha256": sha256(path)})
        print("%-28s exit %d (expected %d) %s" % (fname, proc.returncode, expected, "OK" if ok else "MISMATCH"))

    manifest = {"generated_utc": started, "python": platform.python_version(), "platform": platform.platform(),
                "all_runs_match_expectation": all_ok, "runs": records}
    with open(os.path.join(OUT, "MANIFEST.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")

    lines = ["# Evidence", "",
             "Recorded outputs showing the tools behave as documented. Regenerate with "
             "`python tools/generate_evidence.py`; it overwrites this folder and exits non-zero if any run "
             "stops matching its expected exit code.", "",
             "- Generated: %s" % started,
             "- Python: %s on %s" % (platform.python_version(), platform.platform()),
             "- Result: **%s**" % ("all %d runs matched expectations" % len(records) if all_ok else "MISMATCH, see table"),
             "", "| File | What was run | Exit (expected / actual) | What it shows |", "|---|---|---|---|"]
    for r in records:
        lines.append("| `%s` | `%s` | %d / %d %s | %s |" % (
            os.path.basename(r["file"]), r["command"], r["expected_exit"], r["actual_exit"],
            "ok" if r["match"] else "MISMATCH", r["proves"]))
    lines += ["", "## How to read the failures", "",
              "`lint_broken.txt`, `lint_template_strict.txt`, `adherence_bad.txt` and `adherence_bad.json` are "
              "**expected to fail**. Their value is showing that the checks catch real defects with usable "
              "messages. `MANIFEST.json` holds a SHA-256 for every file so tampering or drift is detectable.",
              "", "## What this evidence does not show", "",
              "- It does not judge visual quality; the tools check tokens, not rendered pixels.",
              "- It was produced on one OS and Python version (see above). The tools use only the standard library "
              "and `os.path`, but they have not been run on every platform.",
              "- The sample sites are small fixtures, not a real production codebase.", ""]
    with open(os.path.join(OUT, "EVIDENCE.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
