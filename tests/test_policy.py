# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""policy.json must stay valid and agree with the code and SECURITY.md."""
import json
import os

from atlasa0 import __version__
from atlasa0 import estimates as est

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY = json.load(open(os.path.join(ROOT, "policy.json"), encoding="utf-8"))


def test_notice_and_version():
    assert POLICY["author"] == "Imaad Ullah Khan Yameen" and POLICY["email"] == "yameenimaad@gmail.com"
    assert POLICY["license"] == "This code is not for sale."
    assert POLICY["project"]["version"] == __version__
    mm = ".".join(__version__.split(".")[:2])
    assert POLICY["security"]["supported_versions"][0] == {"version": f"{mm}.x", "supported": True}


def test_limits_match_code():
    assert (POLICY["limits"]["dpi_min"], POLICY["limits"]["dpi_max"]) == (est.DPI_MIN, est.DPI_MAX)


def test_security_matches_security_md():
    text = open(os.path.join(ROOT, "SECURITY.md"), encoding="utf-8").read()
    s = POLICY["security"]
    assert s["report_to"] in text and not s["public_issues_for_vulnerabilities"]
    for key, days in s["response_days"].items():
        assert f"**{days} days**" in text, key


def test_credits_match_what_maps_print():
    src = open(os.path.join(ROOT, "atlasa0", "render.py"), encoding="utf-8").read()
    for ds in POLICY["data_sources"]:
        credit = ds["required_credit"].replace("©", "\\u00a9")
        assert credit in src or ds["required_credit"] in src, ds["name"]


def test_local_files_match_code():
    paths = " ".join(f["path"] for f in POLICY["local_files"])
    assert ".atlasa0_preset.json" in paths and ".atlasa0_stats.json" in paths and "ATLASA0_CACHE" in paths


def test_license_file_matches_policy():
    text = open(os.path.join(ROOT, "LICENSE"), encoding="utf-8").read()
    assert POLICY["usage"]["license_file"] == "LICENSE"
    assert POLICY["usage"]["license_id"] == "PolyForm-Noncommercial-1.0.0" in text or POLICY["usage"]["license_id"] in text
    assert "PolyForm Noncommercial License 1.0.0" in text
    assert "Required Notice: Copyright (c) 2026 Imaad Ullah Khan Yameen" in text
    assert "Noncommercial Purposes" in text and "Violations" in text
