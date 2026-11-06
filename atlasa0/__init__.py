# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""AtlasA0 - A0 print-ready / GIS-ready maps of Pakistan (country, provinces, districts, cities)."""
from .api import export_receptors, find_receptors, generate_map, list_districts, run_batch
from .config import MAP_TYPES, POI_CATEGORIES, POI_PRESETS, PROVINCES

__all__ = ["generate_map", "run_batch", "list_districts", "find_receptors", "export_receptors",
           "MAP_TYPES", "POI_CATEGORIES", "POI_PRESETS", "PROVINCES"]

__author__ = "Imaad Ullah Khan Yameen"
__email__ = "yameenimaad@gmail.com"
__license__ = "This code is not for sale"
