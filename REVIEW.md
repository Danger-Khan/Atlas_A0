Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# Review: security, quality and release readiness (v1.1.0)

Self-review by the author with an AI assistant. **It is not an independent audit and not a penetration test.**
Items marked *untested here* need a run on a real PC (the build sandbox has no internet, geopandas, osmnx,
rasterio or tkinter).

## 1. Security review

| Area | Check | Result |
|---|---|---|
| Secrets | No API keys, tokens, passwords or accounts anywhere | Pass |
| Code execution | grep for `eval`, `exec`, `pickle`, `os.system`, `shell=True`, `yaml.load`, `__import__` | None found |
| Subprocess | Only `open` / `xdg-open` with a list argument on a path that exists (GUI "open file") | Pass |
| Network | OSM services and optional tile servers over HTTPS; no telemetry; hosts listed in `policy.json` | Pass |
| TLS | No `verify=False` anywhere | Pass |
| User files | Layers, batch JSON, CSV/XLSX tables, GeoTIFF rasters are parsed with data readers only, never executed | Pass |
| File names | Template characters `\ / : * ? " < > |` removed; empty names rejected | Pass |
| Name template | `{region.__class__}`-style lookups were accepted by `str.format_map` | **Fixed**: only plain `{field}` allowed (`config.file_stem`) |
| Image bomb limit | `Image.MAX_IMAGE_PIXELS = None` was set for the whole process | **Fixed**: lifted only while writing our own GeoTIFF, then restored |
| Silent failures | Georeference embedding failed with a bare `except: pass` | **Fixed**: now logged |
| Input limits | Paper 100-3000 mm, dpi 50-500, size and RAM estimates shown before a run | Pass |
| Path writes | Output goes to the chosen output folder; installed app uses the user's Documents/cache folders | Pass |
| Supply chain | Dependencies are not pinned (no internet to resolve hashes here); Dependabot is configured | **Open** |
| Installer | PyInstaller + Inno Setup: statically tested, never built here; not code-signed | **Open** |
| Real run | Real OSM download, rasterio reader, GUI window, Windows installer | **Untested here** |

## 2. Quality
- 340+ automated tests (offline, stubs for the heavy GIS packages); CI matrix: Ubuntu / Windows / macOS, Python 3.10-3.12.
- Tests keep `policy.json`, SECURITY.md, the wiki and the version number in step, enforce the design rules in
  `DESIGN.md`, and (new) check that every file carries the author line and the legal files exist.
- Known limits: see `milestone.md` and the wiki "Troubleshooting".

## 3. Legal and protection
- Licence: PolyForm Noncommercial 1.0.0. The text was typed from memory: **compare `LICENSE` with
  https://polyformproject.org/licenses/noncommercial/1.0.0/ before publishing.**
- `TERMS.md`, `PRIVACY.md`, `NOTICE`, `CODE_OF_CONDUCT.md` are drafts, **not lawyer-reviewed**. The governing law
  (Pakistan / Peshawar) in `TERMS.md` is for the author to confirm.
- Sale protection is by licence and copyright: it forbids selling, but a licence cannot stop a bad actor from
  copying; it gives you a legal claim (DMCA / court) when it happens.
- Patent protection is **not** automatic. A patent must be filed with IPO-Pakistan (or PCT). Until then the
  NOTICE only reserves rights. Ideas that are already public (OSM map rendering, choropleths) are unlikely to
  be patentable; ask a patent attorney before spending money.
- Copyright is automatic. Keeping dated commits and signed tags is useful proof of authorship.

## 4. Release checklist
1. Compare `LICENSE` with the official text.
2. Run `pytest` on Windows, macOS and Linux (CI does it).
3. Run one real map per level, a choropleth and a GeoTIFF layer; send screenshots for review.
4. Build the installer with `installer\build_windows.bat`; sign it if you have a certificate.
5. Tag `v1.1.0`, upload the zip and the installer, publish the wiki.
