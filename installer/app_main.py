# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Entry point of the Windows app (AtlasA0.exe). Also works from source:  python installer/app_main.py

An installed program lives in a folder you cannot write to (C:\\Program Files). So when AtlasA0 runs as the
installed app it keeps its files in your own folders instead - unless you already set the variables yourself:

    ATLASA0_OUTDIR   maps          ->  Documents\\AtlasA0\\output
    ATLASA0_CACHE    OSM downloads ->  %LOCALAPPDATA%\\AtlasA0\\cache   (safe to delete)

These must be set before `atlasa0` is imported (the OSM cache folder is read at import time), so this file
sets them first and imports the program afterwards.
"""
import os
import sys


def default_dirs(env=None, home=None, frozen=None):
    """-> {variable: folder} to set for the installed app ({} when running from source or already configured)."""
    env = os.environ if env is None else env
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if not frozen:
        return {}
    home = home or os.path.expanduser("~")
    local = env.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    want = {"ATLASA0_OUTDIR": os.path.join(home, "Documents", "AtlasA0", "output"),
            "ATLASA0_CACHE": os.path.join(local, "AtlasA0", "cache")}
    return {k: v for k, v in want.items() if not env.get(k)}


def apply_defaults(env=None, home=None, frozen=None):
    env = os.environ if env is None else env
    chosen = default_dirs(env, home, frozen)
    for k, v in chosen.items():
        env[k] = v
    return chosen


def main():
    apply_defaults()
    if getattr(sys, "frozen", False):                 # one-folder build: the program files sit next to the exe
        os.chdir(os.path.dirname(sys.executable))
    from atlasa0.gui_tk import launch
    launch()


if __name__ == "__main__":
    main()
