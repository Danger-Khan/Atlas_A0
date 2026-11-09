# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
# PyInstaller build file for the Windows app.  Run from the project folder:
#     pyinstaller installer/atlasa0.spec --noconfirm
# Result: dist/AtlasA0/AtlasA0.exe (a folder - keep it together; installer/atlasa0.iss turns it into Setup.exe)
import os

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

ROOT = os.path.abspath(os.getcwd())
datas, binaries, hiddenimports = [], [], []

# Packages with data files / compiled parts that PyInstaller does not always find on its own. Packages that are
# not installed in the build environment (rasterio, contextily, openpyxl are optional) are skipped.
for pkg in ("pyproj", "pyogrio", "shapely", "geopandas", "osmnx", "rasterio", "contextily", "openpyxl", "xyzservices",
            "geographiclib"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        print(f"[atlasa0.spec] {pkg} not installed - skipped")

hiddenimports += collect_submodules("atlasa0")        # rasters, choropleth ... are imported only when used
hiddenimports += ["matplotlib.backends.backend_tkagg", "PIL._tkinter_finder", "tkinter", "tkinter.ttk",
                  "tkinter.filedialog", "tkinter.messagebox"]
datas += collect_data_files("matplotlib")
datas += [(os.path.join(ROOT, "atlasa0", "assets"), os.path.join("atlasa0", "assets")),
          (os.path.join(ROOT, "LICENSE"), "."), (os.path.join(ROOT, "README.md"), "."),
          (os.path.join(ROOT, "SECURITY.md"), "."), (os.path.join(ROOT, "policy.json"), ".")]

a = Analysis([os.path.join(ROOT, "installer", "app_main.py")], pathex=[ROOT], binaries=binaries, datas=datas,
             hiddenimports=hiddenimports, excludes=["pytest", "IPython", "PyQt5", "PyQt6", "PySide2", "PySide6", "notebook"],
             noarchive=False)
pyz = PYZ(a.pure)
icon = os.path.join(ROOT, "atlasa0", "assets", "icons", "app.ico")
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="AtlasA0", console=False,
          icon=icon if os.path.isfile(icon) else None, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="AtlasA0", upx=False)
