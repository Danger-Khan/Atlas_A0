# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""AtlasA0 GUI panel (Tkinter). Standalone:  python -m atlasa0 --gui   or   python -m atlasa0.gui_tk

Embed in your project viewer (any Tk container: a frame, a Notebook tab, a Toplevel):

    from atlasa0.gui_tk import AtlasPanel
    panel = AtlasPanel(parent, on_files=viewer.load_layers)   # on_files(list_of_paths) after a run
    panel.pack(fill="both", expand=True)

Long work runs in a background thread; the window stays responsive and Cancel works.
All logic (validation, jobs, estimates, presets) lives in gui_core.py; this file only lays out widgets.
"""
import os
import queue
import subprocess
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from . import config
from . import estimates as est
from . import gui_core as core
from . import icons
from .runtime import JobRunner

PAD = 6


class AtlasPanel(ttk.Frame):
    def __init__(self, parent, on_files=None, preset_path=None):
        super().__init__(parent)
        self.on_files = on_files
        self.preset_path = preset_path or os.path.join(os.path.expanduser("~"), ".atlasa0_preset.json")
        self.opts = core.describe_options()
        self.events = queue.Queue()
        self.runner = JobRunner(on_event=self.events.put)
        self.produced = []
        self.v = {}  # tk variables by name
        self.layers, self.labels = [], []   # your own data layers / free text labels (lists of dicts)
        self.draw_order = list(core.describe_options()["default_draw_order"])   # bottom -> top
        self._build()
        self._load_preset(silent=True)
        if not self._chosen("type"):
            self._set_chosen("type", ["street"])      # sensible start: street map as PNG (no preset yet, or empty one)
        if not self._chosen("fmt"):
            self._set_chosen("fmt", ["png"])
        self._name_changed()
        self._update_estimate()
        self.after(150, self._poll)

    # ------------------------------------------------------------------ helpers
    def _ic(self, name):
        return icons.get(name, self)

    def _add_tab(self, nb, frame, text, icon):
        img = self._ic(icon)
        if img:
            nb.add(frame, text=" " + text, image=img, compound="left")
        else:
            nb.add(frame, text=text)

    def _btn(self, parent, text, command, icon=None, **kw):
        img = self._ic(icon) if icon else None
        b = ttk.Button(parent, text=text, command=command, **({"image": img, "compound": "left"} if img else {}), **kw)
        return b

    def _var(self, name, kind, value):
        var = {"s": tk.StringVar, "b": tk.BooleanVar, "i": tk.IntVar}[kind](value=value)
        var.trace_add("write", lambda *_: self._update_estimate())
        self.v[name] = var
        return var

    def _checks(self, parent, title, items, prefix, cols=3):
        box = ttk.LabelFrame(parent, text=title)
        box.pack(fill="x", padx=PAD, pady=PAD)
        for i, (key, label) in enumerate(items):
            var = self._var(f"{prefix}:{key}", "b", False)
            ttk.Checkbutton(box, text=label, variable=var).grid(row=i // cols, column=i % cols, sticky="w",
                                                                padx=PAD, pady=2)
        return box

    def _chosen(self, prefix):
        return [k.split(":", 1)[1] for k, var in self.v.items() if k.startswith(prefix + ":") and var.get()]

    def _set_chosen(self, prefix, values):
        for k, var in self.v.items():
            if k.startswith(prefix + ":"):
                var.set(k.split(":", 1)[1] in values)

    @staticmethod
    def _textbox(parent, height):
        t = tk.Text(parent, height=height, width=40)
        t.pack(fill="x", padx=PAD, pady=2)
        return t

    # ------------------------------------------------------------------ layout
    def _build(self):
        # Pack order matters in Tk: the widgets pinned to the bottom are packed FIRST, so the Make maps /
        # Preview bar is always visible even on a short screen; the tab area then takes whatever room is left.
        out = ttk.PanedWindow(self, orient="horizontal")
        out.pack(side="bottom", fill="x", padx=PAD, pady=PAD)
        self.log = tk.Text(out, height=6, state="disabled", wrap="word")
        out.add(self.log, weight=3)
        right = ttk.Frame(out)
        self.files = tk.Listbox(right, height=6)
        self.files.pack(fill="both", expand=True)
        self.files.bind("<Double-Button-1>", lambda e: self._open_selected())
        btns = ttk.Frame(right)
        btns.pack(fill="x")
        self._btn(btns, "Open file", self._open_selected, "map").pack(side="left")
        self._btn(btns, "Open folder", self._open_folder, "output").pack(side="left", padx=PAD)
        out.add(right, weight=2)

        ttk.Label(self, text="Author: Imaad Ullah Khan Yameen  |  yameenimaad@gmail.com  |  This code is not for sale",
                  foreground="#555555").pack(side="bottom", fill="x", padx=PAD)
        self.status = ttk.Label(self, text="Ready")
        self.status.pack(side="bottom", fill="x", padx=PAD)
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(side="bottom", fill="x", padx=PAD)

        bar = ttk.Frame(self)
        bar.pack(side="bottom", fill="x", padx=PAD, pady=PAD)
        self.estimate_lbl = ttk.Label(bar, text="", justify="left")
        self.estimate_lbl.pack(side="left", fill="x", expand=True)
        self.run_btn = self._btn(bar, "Make maps", self._run, "run")
        self.run_btn.pack(side="right", padx=PAD)
        self.preview_btn = self._btn(bar, "Preview", lambda: self._run(preview=True), "map")
        self.preview_btn.pack(side="right")
        self.cancel_btn = self._btn(bar, "Cancel", self._cancel, "cancel", state="disabled")
        self.cancel_btn.pack(side="right")

        nb = ttk.Notebook(self)
        nb.pack(side="top", fill="both", expand=True)
        self._tab_where(nb)
        self._tab_map(nb)
        self._tab_layers(nb)
        self._tab_receptors(nb)
        self._tab_elements(nb)
        self._tab_styles(nb)
        self._tab_settings(nb)

    def _tab_where(self, nb):
        f = ttk.Frame(nb)
        self._add_tab(nb, f, "1  Where", "where")
        self._var("country", "b", False)
        ttk.Checkbutton(f, text="Whole country (Pakistan)", variable=self.v["country"]).pack(anchor="w", padx=PAD, pady=PAD)
        self._checks(f, "Provinces (overview maps)", [(p, p) for p in self.opts["provinces"]], "prov", cols=3)
        c = ttk.LabelFrame(f, text="Cities (one per line or comma separated)")
        c.pack(fill="x", padx=PAD, pady=PAD)
        self.cities_txt = self._textbox(c, 3)
        self.cities_txt.bind("<KeyRelease>", lambda e: self._update_estimate())
        row = ttk.Frame(c)
        row.pack(fill="x", padx=PAD)
        ttk.Label(row, text="Add preset cities of:").pack(side="left")
        self.preset_cb = ttk.Combobox(row, values=self.opts["provinces"], state="readonly", width=22)
        self.preset_cb.pack(side="left", padx=PAD)
        self._btn(row, "Add", self._add_preset_cities, "add").pack(side="left")

        d = ttk.LabelFrame(f, text="Districts")
        d.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        row = ttk.Frame(d)
        row.pack(fill="x", padx=PAD, pady=2)
        ttk.Label(row, text="Province:").pack(side="left")
        self.dist_prov = ttk.Combobox(row, values=self.opts["provinces"], state="readonly", width=22)
        self.dist_prov.pack(side="left", padx=PAD)
        self._btn(row, "Load districts", self._load_districts, "refresh").pack(side="left")
        self.dist_lbl = ttk.Label(row, text="")
        self.dist_lbl.pack(side="left", padx=PAD)
        self.dist_list = tk.Listbox(d, selectmode="extended", height=6, exportselection=False)
        self.dist_list.pack(fill="both", expand=True, padx=PAD, pady=2)
        self.dist_list.bind("<<ListboxSelect>>", lambda e: self._update_estimate())

    def _tab_map(self, nb):
        f = ttk.Frame(nb)
        self._add_tab(nb, f, "2  Map", "map")
        self._checks(f, "Map types (one file per type)", list(self.opts["map_types"].items()), "type", cols=2)
        self._checks(f, "File formats", [("png", "PNG poster (print)"), ("tiff", "GeoTIFF (ArcMap / QGIS)")], "fmt", cols=2)
        # ---- resolution slider (50-500 dpi, snaps to 25)
        rq = ttk.LabelFrame(f, text="Resolution (dpi)")
        rq.pack(fill="x", padx=PAD, pady=PAD)
        top = ttk.Frame(rq)
        top.pack(fill="x", padx=PAD, pady=(PAD, 0))
        self._var("dpi", "i", 100)
        # the label must exist BEFORE the slider: newer Tk calls the slider command as soon as set() runs
        self.dpi_lbl = ttk.Label(top, text=est.dpi_label(100), width=26)
        self.dpi_scale = ttk.Scale(top, from_=est.DPI_MIN, to=est.DPI_MAX, orient="horizontal",
                                   command=self._dpi_slid, length=360)
        self.dpi_scale.pack(side="left", fill="x", expand=True)
        self.dpi_lbl.pack(side="left", padx=PAD)
        self.dpi_scale.set(100)
        quick = ttk.Frame(rq)
        quick.pack(fill="x", padx=PAD, pady=PAD)
        for d in (100, 200, 300, 400, 500):
            ttk.Button(quick, text=str(d), width=5, command=lambda d=d: self._set_dpi(d)).pack(side="left", padx=2)
        self.size_lbl = ttk.Label(quick, text="", foreground="#1a6b7b")
        self.size_lbl.pack(side="left", padx=PAD)
        q = ttk.LabelFrame(f, text="Look")
        q.pack(fill="x", padx=PAD, pady=PAD)
        ttk.Label(q, text="Paper:").pack(side="left", padx=(PAD, 2))
        self._var("paper", "s", "A0")
        ttk.Combobox(q, values=self.opts["papers"], textvariable=self.v["paper"], width=9).pack(side="left", padx=(0, PAD))
        ttk.Label(q, text="Orientation:").pack(side="left", padx=(PAD, 2))
        self._var("landscape", "s", "auto")
        ttk.Combobox(q, values=["auto", "portrait", "landscape"], textvariable=self.v["landscape"], state="readonly",
                     width=10).pack(side="left", padx=(0, PAD))
        self._var("buildings", "b", False)
        ttk.Checkbutton(q, text="Building footprints", variable=self.v["buildings"]).pack(side="left", padx=PAD)
        ttk.Label(q, text="Theme:").pack(side="left", padx=PAD)
        self._var("theme", "s", "light")
        ttk.Combobox(q, values=self.opts["themes"], textvariable=self.v["theme"], state="readonly", width=10).pack(side="left")
        r = ttk.Frame(f)
        r.pack(fill="x", padx=PAD)
        ttk.Label(r, text="Radius km (blank = whole boundary):").pack(side="left")
        self._var("radius", "s", "")
        ttk.Entry(r, textvariable=self.v["radius"], width=8).pack(side="left", padx=PAD)

    def _tab_receptors(self, nb):
        f = ttk.Frame(nb)
        self._add_tab(nb, f, "4  Receptors", "receptors")
        pre = ttk.LabelFrame(f, text="Quick presets")
        pre.pack(fill="x", padx=PAD, pady=PAD)
        for name in self.opts["poi_presets"]:
            ttk.Button(pre, text=name, command=lambda n=name: self._apply_poi_preset(n)).pack(side="left", padx=PAD, pady=PAD)
        ttk.Button(pre, text="none", command=lambda: self._set_chosen("poi", [])).pack(side="left", padx=PAD)
        self._checks(f, "Categories to show on the map", list(self.opts["poi_categories"].items()), "poi", cols=3)
        o = ttk.LabelFrame(f, text="Options")
        o.pack(fill="x", padx=PAD, pady=PAD)
        self._var("poi_labels", "b", False)
        ttk.Checkbutton(o, text="Write names next to points", variable=self.v["poi_labels"]).pack(anchor="w", padx=PAD)
        self._var("poi_data", "b", False)
        ttk.Checkbutton(o, text="Also save receptor files", variable=self.v["poi_data"]).pack(anchor="w", padx=PAD)
        self._checks(f, "Receptor file formats", [(x, x) for x in self.opts["poi_formats"]], "pfmt", cols=4)
        self._set_chosen("pfmt", ["csv", "geojson"])

    def _tab_elements(self, nb):
        f = ttk.Frame(nb)
        self._add_tab(nb, f, "5  Elements", "elements")
        self._checks(f, "Show on the map", list(self.opts["elements"].items()), "el", cols=1)
        self._set_chosen("el", self.opts["default_elements"])
        t = ttk.LabelFrame(f, text="Text")
        t.pack(fill="x", padx=PAD, pady=PAD)
        for name, label in (("title", "Title (blank = place name)"), ("subtitle", "Subtitle (blank = default)"),
                            ("note", "Note box on the map")):
            r = ttk.Frame(t)
            r.pack(fill="x", padx=PAD, pady=2)
            ttk.Label(r, text=label, width=28).pack(side="left")
            self._var(name, "s", "")
            ttk.Entry(r, textvariable=self.v[name]).pack(side="left", fill="x", expand=True)
        lg = ttk.LabelFrame(f, text="Extra legend items  (one per line:  Label=#rrggbb)")
        lg.pack(fill="x", padx=PAD, pady=PAD)
        self.legend_txt = self._textbox(lg, 3)
        r = ttk.Frame(lg)
        r.pack(fill="x", padx=PAD)
        ttk.Label(r, text="Legend position:").pack(side="left")
        self._var("legend_pos", "s", "lower right")
        ttk.Combobox(r, values=self.opts["legend_positions"], textvariable=self.v["legend_pos"], state="readonly",
                     width=14).pack(side="left", padx=PAD)
        ttk.Label(r, text="Grid every (km):").pack(side="left", padx=PAD)
        self._var("grid_km", "s", "")
        ttk.Entry(r, textvariable=self.v["grid_km"], width=6).pack(side="left")
        lr = ttk.Frame(f)
        lr.pack(fill="x", padx=PAD, pady=PAD)
        ttk.Label(lr, text="Logo image:").pack(side="left")
        self._var("logo", "s", "")
        ttk.Entry(lr, textvariable=self.v["logo"]).pack(side="left", fill="x", expand=True, padx=PAD)
        self._btn(lr, "Browse", lambda: self._browse_file("logo"), "browse").pack(side="left")
        self._var("tiff_furniture", "b", False)
        ttk.Checkbutton(f, text="Also burn legend/scale/north/grid into the GeoTIFF (normally keep it clean)",
                        variable=self.v["tiff_furniture"]).pack(anchor="w", padx=PAD)

    def _tab_settings(self, nb):
        f = ttk.Frame(nb)
        self._add_tab(nb, f, "7  Settings", "settings")
        # ---- file names
        nm = ttk.LabelFrame(f, text=" File names ")
        nm.pack(fill="x", padx=PAD, pady=PAD)
        self._var("name_mode", "s", "auto")
        ttk.Radiobutton(nm, text="Automatic (AtlasA0 chooses, e.g. peshawar_A0_300dpi.png)", value="auto",
                        variable=self.v["name_mode"], command=self._name_changed).pack(anchor="w", padx=PAD)
        r = ttk.Frame(nm)
        r.pack(fill="x", padx=PAD)
        ttk.Radiobutton(r, text="My own name:", value="custom", variable=self.v["name_mode"],
                        command=self._name_changed).pack(side="left")
        self._var("name_template", "s", "{region}_{type}")
        self.name_entry = ttk.Entry(r, textvariable=self.v["name_template"])
        self.name_entry.pack(side="left", fill="x", expand=True, padx=PAD)
        ttk.Label(nm, text="Fields you can use: {region} {level} {type} {province} {dpi} {date}.  No extension needed "
                           "(.png / .tif is added).\nSeveral maps in one run need {region} (and {type} for several map types) "
                           "so files do not overwrite each other.", foreground="#555").pack(anchor="w", padx=PAD)
        self.name_example = ttk.Label(nm, text="", foreground="#1a6b7b")
        self.name_example.pack(anchor="w", padx=PAD, pady=(0, PAD))
        self.v["name_template"].trace_add("write", lambda *_: self._name_changed())
        # ---- folder
        fo = ttk.LabelFrame(f, text=" Folder and automatic behaviour ")
        fo.pack(fill="x", padx=PAD, pady=PAD)
        r = ttk.Frame(fo)
        r.pack(fill="x", padx=PAD, pady=PAD)
        ttk.Label(r, text="Save in folder:").pack(side="left")
        self._var("outdir", "s", core.FormState().outdir)
        ttk.Entry(r, textvariable=self.v["outdir"]).pack(side="left", fill="x", expand=True, padx=PAD)
        self._btn(r, "Browse", self._browse_dir, "browse").pack(side="left")
        self._var("skip", "b", True)
        ttk.Checkbutton(fo, text="Skip maps that already exist (resume a long run)", variable=self.v["skip"]).pack(anchor="w", padx=PAD)
        self._var("auto_save", "b", True)
        ttk.Checkbutton(fo, text="Remember all my choices automatically when I press Make maps",
                        variable=self.v["auto_save"]).pack(anchor="w", padx=PAD)
        self._var("open_folder", "b", False)
        ttk.Checkbutton(fo, text="Open the output folder when the run finishes",
                        variable=self.v["open_folder"]).pack(anchor="w", padx=PAD, pady=(0, PAD))
        # ---- presets
        b = ttk.Frame(f)
        b.pack(fill="x", padx=PAD, pady=PAD)
        self._btn(b, "Save settings", self._save_preset, "save").pack(side="left")
        self._btn(b, "Load settings", self._load_preset, "load").pack(side="left", padx=PAD)
        self._btn(b, "Reset to automatic defaults", self._reset_defaults, "refresh").pack(side="left")
        self._btn(b, "Export as batch file...", self._export_batch, "export").pack(side="left", padx=PAD)

    def _dpi_slid(self, value):
        d = int(round(float(value) / 25.0) * 25)
        d = max(est.DPI_MIN, min(est.DPI_MAX, d))
        if self.v["dpi"].get() != d:
            self.v["dpi"].set(d)          # trace -> _update_estimate
        lbl = getattr(self, "dpi_lbl", None)   # may not exist yet while the window is being built
        if lbl is not None:
            lbl.config(text=est.dpi_label(d))

    def _set_dpi(self, d):
        d = max(est.DPI_MIN, min(est.DPI_MAX, int(d)))
        self.dpi_scale.set(d)
        self.v["dpi"].set(d)
        self.dpi_lbl.config(text=est.dpi_label(d))

    def _name_changed(self):
        try:
            custom = self.v["name_mode"].get() == "custom"
            self.name_entry.config(state="normal" if custom else "disabled")
            self._update_name_example()
        except Exception:
            pass

    def _update_name_example(self):
        try:
            ex = core.example_name(self.get_state())
        except Exception:
            ex = ""
        self.name_example.config(text=("Example file name:  " + ex) if ex else "")

    def _reset_defaults(self):
        if messagebox.askyesno("AtlasA0", "Put every choice back to the automatic defaults?\n(Your saved settings file is not deleted until you press Make maps.)"):
            self.layers, self.labels = [], []
            self.set_state(core.FormState())

    def _tab_layers(self, nb):
        f = ttk.Frame(nb)
        self._add_tab(nb, f, "3  Your data", "layers")
        ttk.Label(f, text="Add your own points, lines and polygons (shapefile, GeoJSON, GeoPackage, KML, CSV with "
                          "lon/lat) or rasters (GeoTIFF: NDVI, elevation, imagery). Each layer gets its own colour, transparency "
                          "and style.",
                  wraplength=700, justify="left").pack(anchor="w", padx=PAD, pady=PAD)
        row = ttk.Frame(f)
        row.pack(fill="both", expand=True, padx=PAD)
        self.layer_list = tk.Listbox(row, height=7, exportselection=False)
        self.layer_list.pack(side="left", fill="both", expand=True)
        self.layer_list.bind("<Double-Button-1>", lambda e: self._edit_layer())
        col = ttk.Frame(row)
        col.pack(side="left", padx=PAD)
        for text, cmd, icon in (("Add layer...", self._add_layer, "add"), ("Edit...", self._edit_layer, "edit"),
                                ("Remove", self._remove_layer, "remove"), ("Move up", lambda: self._move_layer(-1), "up"),
                                ("Move down", lambda: self._move_layer(1), "down")):
            self._btn(col, text, cmd, icon).pack(fill="x", pady=2)
        ttk.Label(f, text="The list shows the printing order: the layer at the TOP of the list is printed on top of the "
                          "ones below it. 'Move up' brings a layer forward. All your layers sit together at the "
                          "'Your layers' step of the map draw order (tab 6) - move that step to put them above or "
                          "below roads, water, receptors... Opaque polygons hide what is under them; lower the opacity "
                          "to see through.", wraplength=700, justify="left").pack(anchor="w", padx=PAD, pady=PAD)
        cp = ttk.LabelFrame(f, text="Choropleth - shade districts (province map) or provinces (country map) from a table")
        cp.pack(fill="x", padx=PAD, pady=PAD)
        r = ttk.Frame(cp)
        r.pack(fill="x", padx=PAD, pady=2)
        ttk.Label(r, text="Table (.csv / .xlsx):", width=20).pack(side="left")
        self._var("chp_file", "s", "")
        ttk.Entry(r, textvariable=self.v["chp_file"], width=40).pack(side="left", fill="x", expand=True)
        ttk.Button(r, text="Browse...", command=self._browse_table).pack(side="left", padx=PAD)
        r = ttk.Frame(cp)
        r.pack(fill="x", padx=PAD, pady=2)
        for label, name, w in (("Name column", "chp_name", 14), ("Value column", "chp_value", 14)):
            ttk.Label(r, text=label + " (blank = auto):" if name == "chp_name" else label + ":").pack(side="left")
            self._var(name, "s", "")
            ttk.Entry(r, textvariable=self.v[name], width=w).pack(side="left", padx=(2, PAD))
        r = ttk.Frame(cp)
        r.pack(fill="x", padx=PAD, pady=2)
        ttk.Label(r, text="Class limits:").pack(side="left")
        self._var("chp_scheme", "s", "quantile")
        ttk.Combobox(r, values=self.opts["choropleth_schemes"], textvariable=self.v["chp_scheme"], state="readonly",
                     width=10).pack(side="left", padx=(2, PAD))
        ttk.Label(r, text="Classes:").pack(side="left")
        self._var("chp_classes", "s", "5")
        ttk.Entry(r, textvariable=self.v["chp_classes"], width=3).pack(side="left", padx=(2, PAD))
        ttk.Label(r, text="Colours:").pack(side="left")
        self._var("chp_palette", "s", "YlOrRd")
        ttk.Combobox(r, values=self.opts["choropleth_palettes"], textvariable=self.v["chp_palette"], width=10).pack(
            side="left", padx=(2, PAD))
        r = ttk.Frame(cp)
        r.pack(fill="x", padx=PAD, pady=(2, PAD))
        ttk.Label(r, text="Legend heading:", width=20).pack(side="left")
        self._var("chp_title", "s", "")
        ttk.Entry(r, textvariable=self.v["chp_title"], width=24).pack(side="left", padx=(0, PAD))
        self._var("chp_show", "b", False)
        ttk.Checkbutton(r, text="Print the numbers on the map", variable=self.v["chp_show"]).pack(side="left")

    def _browse_table(self):
        p = filedialog.askopenfilename(filetypes=[("Tables", "*.csv *.xlsx"), ("All", "*.*")])
        if p:
            self.v["chp_file"].set(p)

    def _tab_styles(self, nb):
        f = ttk.Frame(nb)
        self._add_tab(nb, f, "6  Styles & labels", "styles")
        o = self.opts

        def combo(parent, label, name, values, default, width=14):
            r = ttk.Frame(parent)
            r.pack(fill="x", padx=PAD, pady=2)
            ttk.Label(r, text=label, width=24).pack(side="left")
            self._var(name, "s", default)
            ttk.Combobox(r, values=values, textvariable=self.v[name], state="readonly", width=width).pack(side="left")

        def entry(parent, label, name, default, width=8):
            r = ttk.Frame(parent)
            r.pack(fill="x", padx=PAD, pady=2)
            ttk.Label(r, text=label, width=24).pack(side="left")
            self._var(name, "s", default)
            ttk.Entry(r, textvariable=self.v[name], width=width).pack(side="left")

        lg = ttk.LabelFrame(f, text="Legend")
        lg.pack(fill="x", padx=PAD, pady=PAD)
        combo(lg, "Style", "legend_style", list(o["legend_styles"]), "box")
        entry(lg, "Heading (blank = none)", "legend_title", "LEGEND", 20)
        entry(lg, "Columns", "legend_cols", "1", 4)
        na = ttk.LabelFrame(f, text="North arrow")
        na.pack(fill="x", padx=PAD, pady=PAD)
        combo(na, "Style", "north_style", list(o["north_styles"]), "arrow")
        combo(na, "Corner", "north_pos", o["corners"], "upper left")
        entry(na, "Size (1 = normal)", "north_size", "1", 5)
        sc = ttk.LabelFrame(f, text="Scale bar")
        sc.pack(fill="x", padx=PAD, pady=PAD)
        combo(sc, "Style", "scale_style", list(o["scale_styles"]), "bar")
        combo(sc, "Units", "scale_units", o["scale_units"], "km")
        combo(sc, "Corner", "scale_pos", o["corners"], "lower left")
        entry(sc, "Segments", "scale_divisions", "4", 4)
        lb = ttk.LabelFrame(f, text="Text labels on the map (placed at lon / lat)")
        lb.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        row = ttk.Frame(lb)
        row.pack(fill="both", expand=True)
        self.label_list = tk.Listbox(row, height=4, exportselection=False)
        self.label_list.pack(side="left", fill="both", expand=True, padx=PAD, pady=2)
        self.label_list.bind("<Double-Button-1>", lambda e: self._edit_label())
        col = ttk.Frame(row)
        col.pack(side="left", padx=PAD)
        for text, cmd, icon in (("Add label...", self._add_label, "label"), ("Edit...", self._edit_label, "edit"),
                                ("Remove", self._remove_label, "remove")):
            self._btn(col, text, cmd, icon).pack(fill="x", pady=2)
        combo(lb, "Note box position", "note_pos", ["lower center", "upper center"], "lower center", 16)

        do = ttk.LabelFrame(f, text=" Draw order - what is printed on top of what ")
        do.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        ttk.Label(do, text="Top of the list = printed last = covers everything below it. Title, legend, scale bar "
                           "and north arrow are always on top.", wraplength=700, justify="left").pack(anchor="w", padx=PAD)
        r = ttk.Frame(do)
        r.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self.order_list = tk.Listbox(r, height=11, exportselection=False)
        self.order_list.pack(side="left", fill="both", expand=True)
        c = ttk.Frame(r)
        c.pack(side="left", padx=PAD)
        self._btn(c, "Move up (more on top)", lambda: self._move_order(True), "up").pack(fill="x", pady=2)
        self._btn(c, "Move down", lambda: self._move_order(False), "down").pack(fill="x", pady=2)
        self._btn(c, "Default order", self._reset_order, "refresh").pack(fill="x", pady=2)
        self._refresh_order()

    # ------------------------------------------------------------------ layers and labels (dialogs)
    def _refresh_layers(self):
        self.layer_list.delete(0, "end")
        for row in core.layer_rows(self.layers):      # top of the list = printed on top
            self.layer_list.insert("end", row)

    def _layer_index(self):
        """Selected row -> index in self.layers (the list is shown top-first, self.layers is bottom-first)."""
        j = self._picked(self.layer_list)
        return None if j is None else len(self.layers) - 1 - j

    def _refresh_labels(self):
        self.label_list.delete(0, "end")
        for d in self.labels:
            self.label_list.insert("end", core.label_summary(d))

    @staticmethod
    def _picked(lst):
        sel = lst.curselection()
        return sel[0] if sel else None

    def _add_layer(self):
        dlg = LayerDialog(self, self.opts)
        dlg.show()
        if dlg.result:
            self.layers.append(dlg.result)
            self._refresh_layers()

    def _edit_layer(self):
        i = self._layer_index()
        if i is None:
            return
        dlg = LayerDialog(self, self.opts, self.layers[i])
        dlg.show()
        if dlg.result:
            self.layers[i] = dlg.result
            self._refresh_layers()

    def _remove_layer(self):
        i = self._layer_index()
        if i is not None:
            del self.layers[i]
            self._refresh_layers()

    def _move_layer(self, step):
        """step -1 = 'Move up' in the list = printed later (more on top); +1 = 'Move down'."""
        i = self._layer_index()
        j = None if i is None else i - step
        if j is None or not 0 <= j < len(self.layers):
            return
        self.layers[i], self.layers[j] = self.layers[j], self.layers[i]
        self._refresh_layers()
        self.layer_list.selection_set(len(self.layers) - 1 - j)

    # ------------------------------------------------------------------ draw order
    def _refresh_order(self, keep=None):
        self.order_list.delete(0, "end")
        rows = core.draw_order_rows(self.draw_order)
        self._order_keys = [k for k, _ in rows]
        for _, text in rows:
            self.order_list.insert("end", text)
        if keep in self._order_keys:
            self.order_list.selection_set(self._order_keys.index(keep))

    def _move_order(self, up):
        j = self._picked(self.order_list)
        if j is None:
            return
        g = self._order_keys[j]
        self.draw_order = core.move_in_order(self.draw_order, g, +1 if up else -1)
        self._refresh_order(keep=g)

    def _reset_order(self):
        self.draw_order = list(self.opts["default_draw_order"])
        self._refresh_order()

    def _add_label(self):
        dlg = LabelDialog(self)
        dlg.show()
        if dlg.result:
            self.labels.append(dlg.result)
            self._refresh_labels()

    def _edit_label(self):
        i = self._picked(self.label_list)
        if i is None:
            return
        dlg = LabelDialog(self, self.labels[i])
        dlg.show()
        if dlg.result:
            self.labels[i] = dlg.result
            self._refresh_labels()

    def _remove_label(self):
        i = self._picked(self.label_list)
        if i is not None:
            del self.labels[i]
            self._refresh_labels()

    # ------------------------------------------------------------------ state <-> widgets
    def get_state(self):
        def num(name):
            t = self.v[name].get().strip()
            return float(t) if t else None
        def num_f(name, default):
            t = self.v[name].get().strip()
            return float(t) if t else default

        def num_i(name, default):
            return int(num_f(name, default))
        try:
            radius, grid = num("radius"), num("grid_km")
            num_f("north_size", 1.0), num_i("legend_cols", 1), num_i("scale_divisions", 4)
        except ValueError:
            raise core.FormError(["Radius, grid spacing, north size, legend columns and scale segments must be numbers."])
        dpi = int(self.v["dpi"].get() or 100)
        sel = [self.dist_list.get(i) for i in self.dist_list.curselection()]
        return core.FormState(
            country=self.v["country"].get(), provinces=self._chosen("prov"),
            cities=core.parse_names(self.cities_txt.get("1.0", "end")),
            district_province=self.dist_prov.get(), districts=sel,
            map_types=self._chosen("type"), formats=self._chosen("fmt"), dpi=dpi, paper=self.v["paper"].get().strip() or "A0", theme=self.v["theme"].get(),
            landscape=self.v["landscape"].get(), buildings=self.v["buildings"].get(), radius_km=radius,
            pois=self._chosen("poi"), poi_labels=self.v["poi_labels"].get(), poi_data=self.v["poi_data"].get(),
            poi_formats=self._chosen("pfmt"), elements=self._chosen("el"), title=self.v["title"].get().strip(),
            subtitle=self.v["subtitle"].get().strip(), legend_items=core.parse_names(self.legend_txt.get("1.0", "end")),
            legend_pos=self.v["legend_pos"].get(), note=self.v["note"].get().strip(), logo=self.v["logo"].get().strip(),
            grid_km=grid, tiff_furniture=self.v["tiff_furniture"].get(), outdir=self.v["outdir"].get().strip(),
            skip_existing=self.v["skip"].get(), name_mode=self.v["name_mode"].get(), name_template=self.v["name_template"].get().strip() or "{region}_{type}", auto_save=self.v["auto_save"].get(), open_folder=self.v["open_folder"].get(), layers=list(self.layers), labels=list(self.labels), draw_order=list(self.draw_order),
            choropleth=self._choropleth_dict(),
            legend_style=self.v["legend_style"].get(), legend_title=self.v["legend_title"].get(),
            legend_cols=num_i("legend_cols", 1), north_style=self.v["north_style"].get(),
            north_pos=self.v["north_pos"].get(), north_size=num_f("north_size", 1.0),
            scale_style=self.v["scale_style"].get(), scale_units=self.v["scale_units"].get(),
            scale_pos=self.v["scale_pos"].get(), scale_divisions=num_i("scale_divisions", 4),
            note_pos=self.v["note_pos"].get())

    def _choropleth_dict(self):
        try:
            return core.choropleth_from_fields(
                self.v["chp_file"].get(), self.v["chp_name"].get(), self.v["chp_value"].get(), self.v["chp_scheme"].get(),
                self.v["chp_classes"].get(), self.v["chp_palette"].get(), self.v["chp_title"].get(), self.v["chp_show"].get())
        except ValueError:
            return {"file": self.v["chp_file"].get().strip(), "classes": 0}      # validate() shows the real message

    def set_state(self, s):
        cp = s.choropleth or {}
        for name, key, dflt in (("chp_file", "file", ""), ("chp_name", "name_col", ""), ("chp_value", "value_col", ""),
                                ("chp_scheme", "scheme", "quantile"), ("chp_classes", "classes", 5),
                                ("chp_palette", "palette", "YlOrRd"), ("chp_title", "title", ""),
                                ("chp_show", "show_values", False)):
            val = cp.get(key, dflt)
            self.v[name].set(val if name == "chp_show" else str(val))
        self.draw_order = list(s.draw_order or self.opts["default_draw_order"])
        if hasattr(self, "order_list"):
            self._refresh_order()
        self.v["country"].set(s.country)
        self._set_chosen("prov", s.provinces)
        self.cities_txt.delete("1.0", "end")
        self.cities_txt.insert("1.0", "\n".join(s.cities))
        self._set_chosen("type", s.map_types or ["street"])      # nothing ticked is not a valid run: show the defaults
        self._set_chosen("fmt", s.formats or ["png"])
        self._set_dpi(s.dpi)
        for name, val in (("paper", s.paper or "A0"), ("theme", s.theme), ("landscape", {True: "landscape", False: "portrait"}.get(s.landscape, s.landscape)), ("buildings", s.buildings),
                          ("radius", "" if s.radius_km is None else str(s.radius_km)), ("poi_labels", s.poi_labels),
                          ("poi_data", s.poi_data), ("title", s.title), ("subtitle", s.subtitle), ("note", s.note),
                          ("legend_pos", s.legend_pos), ("logo", s.logo),
                          ("grid_km", "" if s.grid_km is None else str(s.grid_km)),
                          ("tiff_furniture", s.tiff_furniture), ("outdir", s.outdir), ("skip", s.skip_existing),
                          ("name_mode", s.name_mode), ("name_template", s.name_template), ("auto_save", s.auto_save),
                          ("open_folder", s.open_folder)):
            self.v[name].set(val)
        self._set_chosen("poi", s.pois)
        self._set_chosen("pfmt", s.poi_formats)
        self._set_chosen("el", s.elements)
        self.legend_txt.delete("1.0", "end")
        self.legend_txt.insert("1.0", "\n".join(s.legend_items))
        if s.district_province:
            self.dist_prov.set(s.district_province)
        for name in ("legend_style", "legend_title", "north_style", "north_pos", "scale_style", "scale_units",
                     "scale_pos", "note_pos"):
            self.v[name].set(getattr(s, name))
        for name in ("legend_cols", "north_size", "scale_divisions"):
            self.v[name].set(str(getattr(s, name)))
        self.layers, self.labels = list(s.layers), list(s.labels)
        self._refresh_layers()
        self._refresh_labels()

    # ------------------------------------------------------------------ actions
    def _update_estimate(self):
        try:
            s = self.get_state()
        except Exception:
            return
        e = core.estimate(s)
        txt = core.estimate_text(e)
        if e["warnings"]:
            txt += "\n" + "  ".join(e["warnings"])
        if hasattr(self, "size_lbl"):
            per = est.file_mb((s.map_types or ["street"])[0], "png", s.dpi, s.landscape, e["paper"])[0]
            self.size_lbl.config(text=f"{e['paper']} {e['pixels'][0]} x {e['pixels'][1]} px, about {est.fmt_mb(per)} per PNG, "
                                      f"{e['ram_gb']:.1f} GB RAM")
        self.estimate_lbl.config(text=txt)
        if hasattr(self, "name_example"):
            self._update_name_example()

    def _add_preset_cities(self):
        pv = self.preset_cb.get()
        if pv:
            cur = core.parse_names(self.cities_txt.get("1.0", "end"))
            new = cur + [c for c in self.opts["preset_cities"][pv] if c not in cur]
            self.cities_txt.delete("1.0", "end")
            self.cities_txt.insert("1.0", "\n".join(new))
            self._update_estimate()

    def _apply_poi_preset(self, name):
        keys = list(self.opts["poi_categories"]) if name == "all" else self.opts["poi_presets"][name]
        self._set_chosen("poi", keys)

    def _load_districts(self):
        pv = self.dist_prov.get()
        if not pv:
            messagebox.showinfo("AtlasA0", "Choose a province first.")
            return
        self.dist_lbl.config(text="loading (needs internet)...")

        def done(names, err):
            self.events.put({"type": "districts", "names": names, "error": err})
        core.load_districts_async(pv, done)

    def _run(self, preview=False):
        try:
            jobs, kw = core.build_jobs(self.get_state(), preview=preview)
        except core.FormError as e:
            messagebox.showwarning("Check your settings", "\n".join(e.problems))
            return
        if self.v["auto_save"].get():
            self._save_preset(silent=True)
        self.produced, self.progress["value"] = [], 0
        self.files.delete(0, "end")
        self._log("--- run started ---")
        self._log(config.diagnostics())
        self._preview_run = preview
        self.run_btn.config(state="disabled")
        self.preview_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.status.config(text="Starting preview..." if preview else "Starting...")
        self.runner.start(jobs, **kw)

    def _cancel(self):
        self.runner.cancel()
        self.status.config(text="Cancelling at the next step...")

    def _poll(self):
        try:
            while True:
                self._handle(self.events.get_nowait())
        except queue.Empty:
            pass
        self.after(150, self._poll)

    def _handle(self, ev):
        t = ev.get("type")
        if t == "log":
            self._log(ev["message"])
        elif t == "districts":
            self.dist_list.delete(0, "end")
            for n in ev["names"]:
                self.dist_list.insert("end", n)
            self.dist_lbl.config(text=ev["error"] or f"{len(ev['names'])} districts - select one or more")
        elif t == "job_start":
            self.progress.config(maximum=ev["total"], value=ev["index"] - 1)
            self.status.config(text=f"[{ev['index']}/{ev['total']}] {ev['label']}")
        elif t == "job_done":
            self.progress["value"] = ev["index"]
            for r in ev["files"]:
                self.produced.append(r["path"])
                self.files.insert("end", r["path"])
        elif t == "job_failed":
            self.progress["value"] = ev["index"]
            self._log(f"FAILED {ev['label']}: {ev['error']}")
        elif t == "finished":
            res = ev["result"]
            self.run_btn.config(state="normal")
            self.preview_btn.config(state="normal")
            self.cancel_btn.config(state="disabled")
            note = " (cancelled)" if res.get("cancelled") else ""
            self.status.config(text=f"Done{note}: {len(res['files'])} file(s), {len(res['failed'])} failed")
            if self.on_files and self.produced:
                self.on_files(list(self.produced))
            if getattr(self, "_preview_run", False) and self.produced:
                self._open(self.produced[0])          # show the preview straight away
            elif self.v["open_folder"].get() and self.produced:
                self._open_folder()

    def _log(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    # ------------------------------------------------------------------ files
    def _selected_path(self):
        sel = self.files.curselection()
        return self.files.get(sel[0]) if sel else None

    def _open(self, path):
        if not path or not os.path.exists(path):
            return
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _open_selected(self):
        self._open(self._selected_path())

    def _open_folder(self):
        self._open(os.path.abspath(self.v["outdir"].get() or "."))

    def _browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.v["outdir"].set(d)

    def _browse_file(self, name):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif"), ("All", "*.*")])
        if p:
            self.v[name].set(p)

    def _save_preset(self, silent=False):
        try:
            core.save_preset(self.get_state(), self.preset_path)
            if not silent:
                messagebox.showinfo("AtlasA0", f"Settings saved to\n{self.preset_path}")
        except Exception as e:
            if not silent:
                messagebox.showerror("AtlasA0", str(e))

    def _load_preset(self, silent=False):
        try:
            self.set_state(core.load_preset(self.preset_path))
        except FileNotFoundError:
            if not silent:
                messagebox.showinfo("AtlasA0", "No saved settings yet.")
        except Exception as e:
            if not silent:
                messagebox.showerror("AtlasA0", str(e))

    def _export_batch(self):
        try:
            self.get_state()
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Batch file", "*.json")])
            if path:
                core.to_batch_json(self.get_state(), path)
                messagebox.showinfo("AtlasA0", f"Saved. Run it with:\npython -m atlasa0 --batch \"{path}\"")
        except core.FormError as e:
            messagebox.showwarning("Check your settings", "\n".join(e.problems))


# ====================================================================== dialogs
class _Dialog(tk.Toplevel):
    """Modal helper: build in __init__, call show(), read .result (None if cancelled)."""

    def __init__(self, parent, title):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.result = None
        self.v = {}
        self.body = ttk.Frame(self, padding=PAD)
        self.body.pack(fill="both", expand=True)

    def show(self):
        self.transient(self.parent)
        self.grab_set()
        self.wait_window(self)

    def _row(self, label, kind, name, default, widget="entry", values=None, width=22, row=None):
        r = row if row is not None else ttk.Frame(self.body)
        if row is None:
            r.pack(fill="x", pady=2)
        ttk.Label(r, text=label, width=20).pack(side="left")
        var = {"s": tk.StringVar, "b": tk.BooleanVar, "d": tk.DoubleVar}[kind](value=default)
        var.trace_add("write", lambda *_: self._redraw())
        self.v[name] = var
        if widget == "combo":
            ttk.Combobox(r, values=values, textvariable=var, state="readonly", width=width).pack(side="left")
        elif widget == "check":
            ttk.Checkbutton(r, variable=var).pack(side="left")
        elif widget == "scale":
            ttk.Scale(r, from_=0, to=100, variable=var, length=200).pack(side="left")
        else:
            ttk.Entry(r, textvariable=var, width=width).pack(side="left")
        return r

    def _colour_row(self, label, name, default):
        r = self._row(label, "s", name, default, width=10)
        ttk.Button(r, text="Choose...", command=lambda: self._pick(name)).pack(side="left", padx=PAD)
        return r

    def _pick(self, name):
        cur = self.v[name].get() or None
        try:
            _, hexv = colorchooser.askcolor(color=cur, parent=self)
        except Exception:
            hexv = None
        if hexv:
            self.v[name].set(hexv)

    def _buttons(self, ok_text="OK"):
        b = ttk.Frame(self.body)
        b.pack(fill="x", pady=PAD)
        ttk.Button(b, text="Cancel", command=self.destroy).pack(side="right", padx=PAD)
        ttk.Button(b, text=ok_text, command=self._ok).pack(side="right")

    def _redraw(self):
        pass


class LayerDialog(_Dialog):
    """Add / edit one of your own layers: file, colour, transparency, marker / line / fill style, labels."""

    def __init__(self, parent, opts, spec=None):
        super().__init__(parent, "Layer" if spec else "Add layer")
        d = dict(spec or {})
        self.opts = opts
        r = self._row("File", "s", "path", d.get("path", ""), width=48)
        ttk.Button(r, text="Browse...", command=self._browse).pack(side="left", padx=PAD)
        self._row("Legend name", "s", "name", d.get("name", ""))
        self._colour_row("Fill / point colour", "color", d.get("color", "#d62728"))
        self._colour_row("Outline colour (blank = auto)", "edge_color", d.get("edge_color", ""))
        auto = d.get("alpha") is None
        self._row("Opacity: automatic", "b", "alpha_auto", auto, "check")
        self._row("Opacity % (0 = clear, 100 = solid)", "d", "alpha_pct", 100 * (0.6 if auto else d["alpha"]), "scale")
        self._row("Marker (points)", "s", "marker", d.get("marker", "circle"), "combo", opts["markers"])
        self._row("Marker size (mm on sheet)", "s", "size_mm", str(d.get("size_mm", 6.0)), width=8)
        self._row("Line style", "s", "line_style", d.get("line_style", "solid"), "combo", opts["line_styles"])
        self._row("Line width (mm on sheet)", "s", "width_mm", str(d.get("width_mm", 0.8)), width=8)
        self._row("Fill pattern (polygons)", "s", "hatch", d.get("hatch", "none"), "combo", opts["hatches"])
        self._row("Label from attribute", "s", "label_field", d.get("label_field", ""), width=16)
        self._row("Label size (pt)", "s", "label_size", str(d.get("label_size", 24.0)), width=8)
        self._row("Label halo", "b", "label_halo", d.get("label_halo", True), "check")
        self._row("Show in legend", "b", "legend", d.get("legend", True), "check")
        self._row("Fit map extent to layer", "b", "fit", d.get("fit", False), "check")
        ttk.Label(self.body, text="GeoTIFF layers only (NDVI, elevation, imagery...). Opacity above applies too.",
                  foreground="#555").pack(anchor="w", pady=(6, 0))
        self._row("Colour map (1 band)", "s", "cmap", d.get("cmap", "") or "viridis", "combo", opts["raster_cmaps"])
        self._row("Lowest value (blank = auto)", "s", "vmin", "" if d.get("vmin") is None else str(d["vmin"]), width=10)
        self._row("Highest value (blank = auto)", "s", "vmax", "" if d.get("vmax") is None else str(d["vmax"]), width=10)
        self._row("Band", "s", "band", str(d.get("band", 1)), width=4)
        self._row("Placement", "s", "placement", d.get("placement", "overlay"), "combo", opts["raster_placements"])
        self._row("Resampling", "s", "resample", d.get("resample", "bilinear"), "combo", opts["raster_resamples"])
        self.preview = tk.Canvas(self.body, width=300, height=72, background="white", highlightthickness=1)
        self.preview.pack(pady=PAD)
        self._buttons("Add" if not spec else "Save")
        self._redraw()

    def _browse(self):
        p = filedialog.askopenfilename(filetypes=[
            ("Map data", " ".join("*." + e for e in self.opts["layer_file_types"])), ("All files", "*.*")])
        if p:
            self.v["path"].set(p)
            if not self.v["name"].get():
                self.v["name"].set(os.path.splitext(os.path.basename(p))[0])

    def collect(self):
        v = {k: x.get() for k, x in self.v.items()}
        d = {"path": v["path"].strip(), "name": v["name"].strip(), "color": v["color"].strip() or "#d62728",
             "edge_color": v["edge_color"].strip(), "marker": v["marker"], "size_mm": float(v["size_mm"]),
             "line_style": v["line_style"], "width_mm": float(v["width_mm"]), "hatch": v["hatch"],
             "label_field": v["label_field"].strip(), "label_size": float(v["label_size"]),
             "label_halo": bool(v["label_halo"]), "legend": bool(v["legend"]), "fit": bool(v["fit"])}
        if not v["alpha_auto"]:
            d["alpha"] = round(float(v["alpha_pct"]) / 100, 2)
        if os.path.splitext(d["path"])[1].lower() in (".tif", ".tiff"):     # raster-only options
            d.update(cmap=v["cmap"], placement=v["placement"], resample=v["resample"], band=int(v["band"] or 1))
            for k in ("vmin", "vmax"):
                if str(v[k]).strip():
                    d[k] = float(v[k])
        return d

    def _ok(self):
        try:
            self.result = core.check_layer(self.collect())
        except ValueError as e:
            messagebox.showwarning("Layer", str(e))
            return
        self.destroy()

    def _redraw(self):
        cv = getattr(self, "preview", None)
        if cv is None:
            return
        try:
            d = self.collect()
        except (ValueError, tk.TclError):
            return
        cv.delete("all")
        col = d["color"]
        alpha = d.get("alpha")
        if not core._mc.is_color_like(col):
            return
        edge = d["edge_color"] if d["edge_color"] and core._mc.is_color_like(d["edge_color"]) else col
        cv.create_rectangle(10, 10, 100, 62, fill=core.blend_hex(col, 0.4 if alpha is None else alpha), outline=edge, width=2)
        if d["hatch"] != "none":
            for x in range(10, 100, 10):
                cv.create_line(x, 62, min(x + 52, 100), 62 - min(52, 100 - x), fill=edge)
        dash = {"solid": (), "dashed": (8, 4), "dotted": (2, 3), "dash-dot": (8, 3, 2, 3)}[d["line_style"]]
        cv.create_line(112, 54, 190, 18, fill=core.blend_hex(col, 1.0 if alpha is None else alpha), width=max(1, min(8, d["width_mm"] * 2)),
                       dash=dash or None)
        kind, pts, hollow = core.marker_shape(d["marker"], 250, 36, max(5, min(24, d["size_mm"] * 2)))
        fill = "" if hollow else core.blend_hex(col, 1.0 if alpha is None else alpha)
        outline = col if hollow else (edge if d["edge_color"] else "#ffffff")
        (cv.create_oval if kind == "oval" else cv.create_polygon)(*pts, fill=fill, outline=outline, width=2)


class LabelDialog(_Dialog):
    """Add / edit a free text label placed at a longitude / latitude."""

    def __init__(self, parent, spec=None):
        super().__init__(parent, "Edit label" if spec else "Add label")
        d = dict(spec or {})
        self._row("Text", "s", "text", d.get("text", ""), width=30)
        self._row("Longitude (e.g. 71.52)", "s", "lon", str(d.get("lon", "")), width=12)
        self._row("Latitude (e.g. 34.01)", "s", "lat", str(d.get("lat", "")), width=12)
        self._row("Size (pt)", "s", "size", str(d.get("size", 40)), width=8)
        self._colour_row("Colour (blank = theme)", "color", d.get("color", ""))
        self._row("Rotation (degrees)", "s", "rotation", str(d.get("rotation", 0)), width=8)
        for label, name, default in (("Bold", "bold", False), ("Italic", "italic", False),
                                     ("Halo", "halo", True), ("Box behind text", "box", False)):
            self._row(label, "b", name, d.get(name, default), "check")
        self._buttons("Add" if not spec else "Save")

    def _ok(self):
        try:
            self.result = core.check_label({k: x.get() for k, x in self.v.items()})
        except ValueError as e:
            messagebox.showwarning("Label", str(e))
            return
        self.destroy()


def launch():
    root = tk.Tk()
    root.title("AtlasA0 - maps of Pakistan for GIS and A0 print")
    # fit the window to the screen (a fixed 900 px height hid the bottom bar on 768 px laptops)
    w = min(1020, max(640, root.winfo_screenwidth() - 40))
    h = min(900, max(520, root.winfo_screenheight() - 90))
    root.geometry(f"{w}x{h}+20+10")
    root.minsize(640, 520)
    img = icons.get("app", root)
    if img:
        try:
            root.iconphoto(True, img)
        except Exception:
            pass
    panel = AtlasPanel(root)
    panel.pack(fill="both", expand=True)
    root.bind("<Control-Return>", lambda e: panel._run())  # keyboard shortcut for Make maps
    root.mainloop()


if __name__ == "__main__":
    launch()
