# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Settings, themes, map types and the province catalogue (no heavy imports)."""

A0_INCHES = (33.11, 46.81)  # portrait (width, height)
# drawing area inside the sheet as a fraction of the figure: left, bottom, width, height
# (top margin 0.10 holds the title, bottom 0.04 the credit line)
AXES_RECT = (0.04, 0.04, 0.92, 0.86)

# --- paper sizes ------------------------------------------------------------------------------------------
# Every element (fonts, line widths, markers) is sized for an A0 figure. Other papers are made by drawing the same
# A0-proportioned figure and saving it at dpi x k (k = short side / A0 short side), so the picture is an exact
# scaled copy: same layout, and the file has paper_size x dpi pixels.
PAPER_SIZES_MM = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420), "A4": (210, 297)}
PAPER_NAMES = tuple(PAPER_SIZES_MM)
PAPER_MM_LIMITS = (100, 3000)


def parse_paper(paper):
    """"A3" / "a3" / "500x700" (mm, also "500 x 700 mm") -> (label, short_mm, long_mm). Raises ValueError."""
    import re
    if paper is None or str(paper).strip() == "":
        paper = "A0"
    txt = str(paper).strip()
    if txt.upper() in PAPER_SIZES_MM:
        w, h = PAPER_SIZES_MM[txt.upper()]
        return txt.upper(), w, h
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*[x\u00d7*]\s*(\d+(?:\.\d+)?)\s*(?:mm)?", txt, re.I)
    if not m:
        raise ValueError(f"paper must be one of {', '.join(PAPER_NAMES)} or a size in mm like 500x700 (got '{paper}')")
    a, b = float(m.group(1)), float(m.group(2))
    lo, hi = PAPER_MM_LIMITS
    if not (lo <= a <= hi and lo <= b <= hi):
        raise ValueError(f"custom paper sides must be {lo}-{hi} mm (got {a:g} x {b:g})")
    short, long_ = sorted((a, b))
    return f"{short:g}x{long_:g}mm", short, long_


def sheet_geometry(paper="A0", landscape=False):
    """-> (figure size in inches (w, h), k, label). Figure short side is always the A0 short side."""
    label, short, long_ = parse_paper(paper)
    k = short / PAPER_SIZES_MM["A0"][0]
    if label == "A0":
        size = A0_INCHES
    else:
        size = (A0_INCHES[0], A0_INCHES[0] * long_ / short)
    return (size[::-1] if landscape else size), k, label


def paper_k(paper="A0"):
    return parse_paper(paper)[1] / PAPER_SIZES_MM["A0"][0]


def paper_area_ratio(paper="A0"):
    """Pixels of this paper / pixels of A0 at the same dpi."""
    _, short, long_ = parse_paper(paper)
    return short * long_ / (PAPER_SIZES_MM["A0"][0] * PAPER_SIZES_MM["A0"][1])


THEMES = {
    "light": dict(bg="#f7f4ec", road="#3a3a3a", water="#9ccbe8", green="#cfe3bd",
                  building="#d8d2c4", text="#1f1f1f", frame="#1f1f1f"),
    "dark": dict(bg="#0f1419", road="#e8e8e8", water="#1d3b5a", green="#1c2f22",
                 building="#2a3139", text="#f0f0f0", frame="#f0f0f0"),
}


# line width (points) per road class, sized for A0
ROAD_WIDTH = {
    "motorway": 7, "motorway_link": 4, "trunk": 6, "trunk_link": 3.5,
    "primary": 5, "primary_link": 3, "secondary": 3.8, "secondary_link": 2.5,
    "tertiary": 2.8, "tertiary_link": 2, "residential": 1.6,
    "unclassified": 1.4, "living_street": 1.2, "service": 0.8,
}


FORMAT_ALIASES = {"png": "png", "tif": "tiff", "tiff": "tiff", "geotiff": "tiff"}


MAP_TYPES = {
    "street": "Full street network + water + parks (default)",
    "transport": "Major roads (motorway to tertiary) + railways only",
    "landuse": "Land-use zones coloured by type (residential, industrial, farmland...)",
    "water": "Rivers, canals, lakes and wetlands emphasised",
    "buildings": "Building footprints + road network",
    "satellite": "Satellite imagery (Esri) with major-road overlay  [needs: pip install contextily]",
    "topo": "Topographic basemap (OpenTopoMap)  [needs: pip install contextily]",
    "receptors": "Sensitive receptors (hospitals, clinics, schools, worship, water...) on a light base",
}


LANDUSE_COLORS = {
    "residential": "#e3cfa9", "commercial": "#f2a9a2", "retail": "#f2a9a2",
    "industrial": "#c9b8dc", "farmland": "#ece9a9", "farmyard": "#ece9a9",
    "orchard": "#d6e3a0", "meadow": "#d3e6bf", "grass": "#cfe3bd",
    "recreation_ground": "#cfe3bd", "park": "#bfe0a8", "forest": "#9ccb8a",
    "wood": "#9ccb8a", "cemetery": "#bcd0c0", "military": "#dba3a3",
    "construction": "#d2c4b2", "brownfield": "#d2c4b2", "quarry": "#c4b8a8",
    "education": "#f0dca0", "religious": "#d8c0d8",
}


LANDUSE_OTHER = "#e6e3dc"


PROVINCES = {
    "Punjab": ["Lahore", "Faisalabad", "Rawalpindi", "Multan", "Gujranwala",
               "Sialkot", "Bahawalpur", "Sargodha"],
    "Sindh": ["Karachi", "Hyderabad", "Sukkur", "Larkana", "Mirpur Khas"],
    "Khyber Pakhtunkhwa": ["Peshawar", "Mardan", "Abbottabad", "Mingora", "Kohat",
                           "Dera Ismail Khan", "Bannu"],
    "Balochistan": ["Quetta", "Gwadar", "Turbat", "Khuzdar", "Sibi"],
    "Gilgit-Baltistan": ["Gilgit", "Skardu"],
    "Azad Kashmir": ["Muzaffarabad", "Mirpur"],
    "Islamabad": ["Islamabad"],
}


# Nominatim search names that resolve correctly
PROVINCE_QUERY = {
    "Punjab": "Punjab, Pakistan",
    "Sindh": "Sindh, Pakistan",
    "Khyber Pakhtunkhwa": "Khyber Pakhtunkhwa, Pakistan",
    "Balochistan": "Balochistan, Pakistan",
    "Gilgit-Baltistan": "Gilgit-Baltistan, Pakistan",
    "Azad Kashmir": "Azad Jammu and Kashmir, Pakistan",
    "Islamabad": "Islamabad Capital Territory, Pakistan",
}


def match_province(name):
    n = name.strip().lower().replace("-", " ")
    aliases = {"kpk": "Khyber Pakhtunkhwa", "kp": "Khyber Pakhtunkhwa", "gb": "Gilgit-Baltistan",
               "ajk": "Azad Kashmir", "ict": "Islamabad", "baluchistan": "Balochistan"}
    if n in aliases:
        return aliases[n]
    for k in PROVINCES:
        if k.lower().replace("-", " ") == n:
            return k
    raise SystemExit(f"Unknown province '{name}'. Use --list to see options.")


# ---- points of interest / sensitive receptors (OSM tags) -------------------------------------
POI_CATEGORIES = {
    "hospitals": dict(label="Hospitals", tags={"amenity": ["hospital"]}, color="#d62728", marker="P"),
    "clinics": dict(label="Clinics / health centres", color="#ff7f0e", marker="P",
                    tags={"amenity": ["clinic", "doctors"], "healthcare": ["clinic", "centre"]}),
    "pharmacies": dict(label="Pharmacies", tags={"amenity": ["pharmacy"]}, color="#e377c2", marker="o"),
    "schools": dict(label="Schools", tags={"amenity": ["school", "kindergarten"]},
                    color="#1f77b4", marker="s"),
    "colleges": dict(label="Colleges / universities", tags={"amenity": ["college", "university"]},
                     color="#17becf", marker="D"),
    "worship": dict(label="Places of worship", tags={"amenity": ["place_of_worship"]},
                    color="#7f4f9f", marker="^"),
    "water_sources": dict(label="Water sources", color="#0a6ebd", marker="o",
                          tags={"amenity": ["drinking_water"],
                                "man_made": ["water_well", "water_tower", "water_works"]}),
    "markets": dict(label="Markets", tags={"amenity": ["marketplace"]}, color="#bcbd22", marker="h"),
    "police": dict(label="Police", tags={"amenity": ["police"]}, color="#2f4f4f", marker="*"),
    "fire": dict(label="Fire stations", tags={"amenity": ["fire_station"]}, color="#8c1c13", marker="*"),
    "fuel": dict(label="Fuel stations", tags={"amenity": ["fuel"]}, color="#8c564b", marker="v"),
    "industry": dict(label="Industry / works", tags={"man_made": ["works"], "industrial": True},
                     color="#555555", marker="X"),
}

# receptor file types -> file name suffix (used for naming and for --skip-existing)
POI_FILE_SUFFIX = {"csv": "_poi.csv", "geojson": "_poi.geojson", "xlsx": "_poi.xlsx",
                   "summary": "_poi_summary.csv"}

POI_PRESETS = {
    "receptors": ["hospitals", "clinics", "schools", "colleges", "worship", "water_sources"],
    "health": ["hospitals", "clinics", "pharmacies"],
    "education": ["schools", "colleges"],
    "emergency": ["hospitals", "police", "fire"],
    "all": list(POI_CATEGORIES),
}


def resolve_pois(names):
    """Category names and/or preset names -> ordered list of category keys."""
    if not names:
        return []
    if isinstance(names, str):
        names = [names]
    keys = []
    for n in names:
        n = n.strip().lower()
        if n in POI_PRESETS:
            add = POI_PRESETS[n]
        elif n in POI_CATEGORIES:
            add = [n]
        else:
            raise ValueError(f"unknown point-of-interest '{n}'. Categories: {', '.join(POI_CATEGORIES)}; "
                             f"presets: {', '.join(POI_PRESETS)}")
        keys += [k for k in add if k not in keys]
    return keys


# ---------------------------------------------------------------- output file names
NAME_FIELDS = ("region", "level", "type", "province", "dpi", "date")


def file_stem(template, **values):
    """Custom output name from a template such as 'Map_{region}_{type}_{date}' (no extension).
    Fields: {region} {level} {type} {province} {dpi} {date}. Spaces become '_', characters Windows forbids are removed.
    Raises ValueError for an empty name or an unknown {field}."""
    import datetime
    import re
    import string
    for _lit, field, spec, conv in string.Formatter().parse(str(template)):
        # only plain {name} fields: no attribute/index lookups, no format specs or conversions
        if field is not None and (not field.isidentifier() or spec or conv):
            raise ValueError("Use plain fields like {region} only (no dots, brackets or format codes).")
    vals = {k: "" for k in NAME_FIELDS}
    vals.update({k: ("" if v is None else str(v)) for k, v in values.items()})
    vals["date"] = vals.get("date") or datetime.date.today().isoformat()
    try:
        name = str(template).format_map(vals)
    except KeyError as e:
        raise ValueError(f"Unknown field {{{e.args[0]}}} in the file name. Use: "
                         + ", ".join("{%s}" % f for f in NAME_FIELDS)) from None
    except (ValueError, IndexError):
        raise ValueError("The file name has a stray { or } - use fields like {region} only.") from None
    name = re.sub(r"\.(png|tiff?|csv|geojson|xlsx)$", "", name.strip(), flags=re.I)
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    name = re.sub(r"\s+", "_", name).strip("._ ")
    if not name:
        raise ValueError("The file name is empty.")
    return name


def project_dir():
    """The AtlasA0 folder (the one holding run_gui.py), or None when installed as a package elsewhere."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return root if os.path.isfile(os.path.join(root, "run_gui.py")) else None


def cache_dir(env=None, root="auto", platform=None):
    """Folder for the OpenStreetMap download cache. It is ALWAYS an absolute, writable folder.

    Order: $ATLASA0_CACHE; the `cache` folder inside the AtlasA0 folder (next to run_gui.py, whatever folder Python
    was started from); the user's own cache folder (Windows %LOCALAPPDATA%/AtlasA0/cache, macOS
    ~/Library/Caches/AtlasA0, Linux $XDG_CACHE_HOME or ~/.cache/atlasa0); the system temp folder. A relative 'cache'
    used to fail with [WinError 5] when Python was started from a protected folder (Program Files, System32)."""
    import os
    import sys
    import tempfile
    env = os.environ if env is None else env
    root = project_dir() if root == "auto" else root
    platform = sys.platform if platform is None else platform
    home = os.path.expanduser("~")
    if platform.startswith("win"):
        user = os.path.join(env.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local"), "AtlasA0", "cache")
    elif platform == "darwin":
        user = os.path.join(home, "Library", "Caches", "AtlasA0")
    else:
        user = os.path.join(env.get("XDG_CACHE_HOME") or os.path.join(home, ".cache"), "atlasa0")
    candidates = []
    if env.get("ATLASA0_CACHE"):
        candidates.append(os.path.abspath(env["ATLASA0_CACHE"]))
    if root:
        candidates.append(os.path.join(root, "cache"))
    candidates += [user, os.path.join(tempfile.gettempdir(), "atlasa0_cache")]
    for c in candidates:
        if _writable_dir(c):
            return c
    return candidates[-1]


def _writable_dir(path):
    """True if the folder exists (or can be created) and a file can be written in it."""
    import os
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".atlasa0_write_test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def diagnostics():
    """One line saying which AtlasA0 is running and where it keeps its cache (shown at the start of every GUI run
    and by --about), so a support question can be answered from a screenshot."""
    import os
    import sys
    from . import __version__
    cache = None
    ox = sys.modules.get("osmnx")
    if ox is not None:
        cache = getattr(getattr(ox, "settings", None), "cache_folder", None)
    return (f"AtlasA0 {__version__} | Python {sys.version.split()[0]} | cache: {cache or cache_dir()} | "
            f"started in: {os.getcwd()} | code: {os.path.dirname(os.path.abspath(__file__))}")
