# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""A permissive stand-in for tkinter so the GUI panel's code can be exercised without a display.
It stores variable values and text, and accepts any widget call. It checks wiring (no NameErrors, state
round-trip, event handling), not appearance."""
import sys
import types


class _Var:
    def __init__(self, value=None, **kw):
        self._v = value

    def get(self):
        return self._v

    def set(self, v):
        self._v = v

    def trace_add(self, *a, **k):
        pass


class _W:
    def __init__(self, *a, **kw):
        self._items, self._stub_text, self._sel, self._val = [], "", (), kw.get("value", 0)
        self._cfg = dict(kw)
        self._after = []

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: None

    # Text / Listbox / Combobox / Progressbar behaviour used by the panel
    def insert(self, pos, text):
        if isinstance(self._items, list) and not isinstance(text, str) or pos == "end" and self._is_list:
            self._items.append(text)
        else:
            self._stub_text += text

    _is_list = False

    def delete(self, *a):
        self._items, self._stub_text = [], ""

    def get(self, *a):
        if self._is_list:
            return self._items[a[0]]
        return (self._stub_text + "\n") if a and a[0] == "1.0" else self._cfg.get("_cb", "")

    def set(self, v):
        self._cfg["_cb"] = v

    def curselection(self):
        return self._sel

    def config(self, **kw):
        self._cfg.update(kw)

    configure = config

    def __setitem__(self, k, v):
        self._cfg[k] = v

    def __getitem__(self, k):
        return self._cfg.get(k, 0)

    def after(self, *a, **k):
        pass


class _Scale(_W):
    """Like real Tk 8.6.13+: set() runs the slider's command straight away (this exposed a build-order bug)."""

    def set(self, v):
        self._val = v
        cmd = self._cfg.get("command")
        if cmd:
            cmd(v)


class _Listbox(_W):
    _is_list = True

    def insert(self, pos, text):
        self._items.append(text)


def install():
    tk = types.ModuleType("tkinter")
    ttk = types.ModuleType("tkinter.ttk")
    fd = types.ModuleType("tkinter.filedialog")
    mb = types.ModuleType("tkinter.messagebox")
    for n in ("StringVar", "BooleanVar", "IntVar", "DoubleVar"):
        setattr(tk, n, _Var)
    tk.Toplevel = type("Toplevel", (_W,), {})
    tk.Canvas = tk.Label = _W
    tk.TclError = Exception
    cc = types.ModuleType("tkinter.colorchooser")
    cc.askcolor = lambda **k: (None, "#123456")
    tk.Text, tk.Listbox, tk.Tk = _W, _Listbox, _W
    for n in ("Frame", "LabelFrame", "Label", "Button", "Checkbutton", "Radiobutton", "Entry", "Combobox", "Notebook",
              "Progressbar", "PanedWindow"):
        setattr(ttk, n, _W)
    ttk.Scale = _Scale
    fd.askdirectory = fd.askopenfilename = fd.asksaveasfilename = lambda **k: ""
    mb.showinfo = mb.showwarning = mb.showerror = lambda *a, **k: None
    mb.calls = []
    tk.ttk, tk.filedialog, tk.messagebox, tk.colorchooser = ttk, fd, mb, cc
    sys.modules.update({"tkinter.colorchooser": cc, "tkinter": tk, "tkinter.ttk": ttk, "tkinter.filedialog": fd, "tkinter.messagebox": mb})
    return tk
