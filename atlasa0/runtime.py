# Author: Imaad Ullah Khan Yameen
# Email: yameenimaad@gmail.com
# This code is not for sale.
"""Run-time plumbing for GUIs and other callers: progress messages, cancellation, background runner.

No GUI toolkit is imported here. A GUI (Tkinter, PyQt, PySide, a web backend...) does:

    runner = JobRunner(on_event=my_callback)      # my_callback runs in the worker thread
    runner.start(jobs, outdir="maps", dpi=100)
    ...
    runner.cancel()                               # stops at the next stage (downloads/drawing step)

Events are plain dicts:  {"type": "log", "message"} | {"type": "job_start", "index", "total", "label"} |
{"type": "job_done", "index", "total", "files"} | {"type": "job_failed", "index", "total", "label", "error"} |
{"type": "cancelled"} | {"type": "finished", "result"}.
Because callbacks arrive on a worker thread, a GUI must hand them to its main thread (Tk: queue + after(),
Qt: signals).
"""
import threading

_listeners = []
_cancel = threading.Event()


class Cancelled(BaseException):
    """Raised at a checkpoint after cancel(). BaseException on purpose: OSM wrappers use
    `except Exception` to survive network failures and must not swallow a cancel."""


def add_listener(fn):
    _listeners.append(fn)


def remove_listener(fn):
    if fn in _listeners:
        _listeners.remove(fn)


def checkpoint():
    if _cancel.is_set():
        raise Cancelled()


def say(message):
    """Print a line and pass it to listeners (never cancels)."""
    print(message)
    for fn in list(_listeners):
        try:
            fn({"type": "log", "message": str(message)})
        except Exception:
            pass


def log(message):
    """say() + cancel point: every stage message of a map is a place where cancel() takes effect."""
    say(message)
    checkpoint()


def request_cancel():
    _cancel.set()


def reset_cancel():
    _cancel.clear()


class JobRunner:
    """Runs run_batch in a background thread; one batch at a time."""

    def __init__(self, on_event=None):
        self.on_event = on_event or (lambda e: None)
        self._thread = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, jobs, **kwargs):
        if self.running:
            raise RuntimeError("a batch is already running")
        from .api import run_batch  # late import keeps this module light
        reset_cancel()

        def work():
            add_listener(self.on_event)
            try:
                res = run_batch(jobs, on_event=self.on_event, **kwargs)
            except Cancelled:
                res = {"files": [], "failed": [], "cancelled": True}
            except BaseException as e:  # never let the thread die silently
                res = {"files": [], "failed": [{"job": {}, "error": str(e)}]}
            finally:
                remove_listener(self.on_event)
            self.on_event({"type": "finished", "result": res})

        self._thread = threading.Thread(target=work, daemon=True, name="atlasa0-batch")
        self._thread.start()
        return self._thread

    def cancel(self):
        request_cancel()

    def join(self, timeout=None):
        if self._thread:
            self._thread.join(timeout)
