# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""GUI icons (PNG files in atlasa0/assets/icons, drawn by tools/make_icons.py). Safe if a file is missing."""
import os

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")
NAMES = ("where", "map", "layers", "receptors", "elements", "styles", "output", "settings", "run", "cancel", "save", "load",
         "export", "add", "remove", "edit", "up", "down", "browse", "refresh", "label", "app")
_cache = {}


def path(name):
    p = os.path.join(DIR, f"{name}.png")
    return p if os.path.isfile(p) else None


def get(name, master=None):
    """tk.PhotoImage for the icon (kept alive in a cache), or None if it is missing."""
    if name in _cache:
        return _cache[name]
    p = path(name)
    img = None
    if p:
        try:
            import tkinter as tk
            img = tk.PhotoImage(file=p, master=master)
        except Exception:
            img = None
    _cache[name] = img
    return img


def app_ico():
    p = os.path.join(DIR, "app.ico")
    return p if os.path.isfile(p) else None
