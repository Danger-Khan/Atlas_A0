<!--
Author: Imaad Ullah Khan Yameen
Email: yameenimaad@gmail.com
This code is not for sale.
-->
# Building the Windows app and installer

| File | What it is |
| ---- | ---------- |
| `app_main.py` | Entry point of `AtlasA0.exe`. Chooses safe folders for maps and cache when installed, then opens the window. |
| `atlasa0.spec` | PyInstaller recipe (one folder, no console window, icon, data files, hidden imports). |
| `atlasa0.iss` | Inno Setup script: wizard with the licence, Start-menu entry, optional desktop icon, uninstaller. |
| `build_windows.bat` | Runs the tests, PyInstaller, then Inno Setup, and prints the result. |
| `requirements-build.txt` | Extra packages for the build PC (pyinstaller, rasterio, contextily, openpyxl). |

## Steps (on Windows 10/11 with Python 3.10-3.12 on PATH)
1. Install [Inno Setup 6](https://jrsoftware.org/isdl.php) (only needed for `Setup.exe`; without it you still get the program folder).
2. Double-click `installer\build_windows.bat` (or run it in a terminal from anywhere). It creates `.build-venv`, installs the packages, runs `pytest`, builds `dist\AtlasA0\AtlasA0.exe` and `Output\AtlasA0-Setup-<version>.exe`.
3. Test before sharing: install it on a PC (or a clean user account), open it, make a **small** map (a city at 100 dpi, or *Preview*), then try a satellite map and a GeoTIFF layer.

## What to expect
- **Size:** several hundred MB (geopandas, GDAL/PROJ, matplotlib, rasterio). The installer compresses it to roughly half.
- **Windows SmartScreen / antivirus:** an unsigned program triggers "Windows protected your PC" and sometimes false alarms. Signing needs a code-signing certificate (not included). Until then, tell people to choose *More info -> Run anyway*, or share the source instead.
- **Where files go:** maps in `Documents\AtlasA0\output`, OpenStreetMap cache in `%LOCALAPPDATA%\AtlasA0\cache` (safe to delete), settings in your user folder (`.atlasa0_preset.json`). Set `ATLASA0_OUTDIR` / `ATLASA0_CACHE` first to use other folders. Uninstalling removes the program only, never your maps.
- **Licence:** the wizard shows `LICENSE` (PolyForm Noncommercial 1.0.0) and the user must accept it. It does not by itself stop someone from copying the installer; it only tells them the terms. Handing the installer to a client for paid work needs your separate written licence.
- **No command line in the exe:** it opens the window only. Use `python -m atlasa0 ...` from source for scripts and batches.

## Status
Written and statically checked (`tests/test_installer.py`: paths exist, versions and licence agree, folder logic). **Not built or run** - this needs Windows. The most likely snags are missing GDAL/PROJ data (add the package to the loop in `atlasa0.spec` or set `PROJ_DATA`) and an antivirus quarantine; send the build log if it fails.
