# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Settings, themes, map types and the province catalogue (no heavy imports)."""

A0_INCHES = (33.11, 46.81)  # portrait (width, height)
# drawing area inside the sheet as a fraction of the figure: left, bottom, width, height
# (top margin 0.10 holds the title, bottom 0.04 the credit line)
AXES_RECT = (0.04, 0.04, 0.92, 0.86)


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
