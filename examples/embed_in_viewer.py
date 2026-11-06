# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""How to put AtlasA0 inside your Python project viewer.

--- Tkinter viewer (tested through a stub toolkit; try it on your machine) -------------------------------
    import tkinter as tk
    from tkinter import ttk
    from atlasa0.gui_tk import AtlasPanel

    def load_layers(paths):                  # called on the GUI thread after a run
        for p in paths:
            if p.endswith(".tif"):           # georeferenced raster: add as a layer (the .tfw/.prj sit beside it)
                viewer.add_raster(p)
            elif p.endswith(".geojson"):
                viewer.add_vector(p)

    root = tk.Tk()
    nb = ttk.Notebook(root); nb.pack(fill="both", expand=True)
    nb.add(AtlasPanel(nb, on_files=load_layers), text="Maps (AtlasA0)")
    root.mainloop()

--- PyQt / PySide viewer (NOT tested here; same controller, your own widgets) ------------------------------
    from atlasa0 import gui_core as core
    from atlasa0.runtime import JobRunner
    from PySide6.QtCore import QObject, Signal

    class Bridge(QObject):
        event = Signal(dict)                  # emit from the worker thread; Qt delivers it on the GUI thread

    bridge = Bridge(); bridge.event.connect(my_slot)
    runner = JobRunner(on_event=bridge.event.emit)

    state = core.FormState(cities=["Peshawar"], map_types=["street"], formats=["png", "tiff"], dpi=100)
    problems = core.validate(state)           # show these next to the form fields
    jobs, kw = core.build_jobs(state)
    runner.start(jobs, **kw)                  # runner.cancel() from a Cancel button
    # core.describe_options() gives choices/defaults to build the form; core.estimate(state) the size/RAM hint.

--- No GUI toolkit at all (script / web backend) ------------------------------------------------------------
    from atlasa0 import generate_map, run_batch
"""
