#!/usr/bin/env python3
# Python entry point for the Pitivi AppImage.
#
# All filesystem-fragile fixups (path rewrites, override re-injection,
# loader fallbacks) live HERE rather than in patched-on-disk files, so the
# bundled flatpak deployment (which is hardlinked into the AppDir at build
# time) is never modified in place.
import gettext
import glob
import os
import signal
import sys

try:
    from ctypes import cdll
    cdll.LoadLibrary("libX11.so").XInitThreads()
except OSError:
    pass

APPDIR = os.environ["APPDIR"]
APP = os.path.join(APPDIR, "app")
RUNTIME = os.path.join(APPDIR, "runtime")


def _runtime_python_lib():
    """Return the runtime's `lib/python3.X` directory (whichever Python
    version this AppImage was built against)."""
    matches = sorted(glob.glob(os.path.join(RUNTIME, "lib", "python3.*")))
    if not matches:
        raise RuntimeError("No python3.* under {RUNTIME}/lib")
    # Filter out site-packages style entries; we want the bare "python3.X".
    return next(m for m in matches if os.path.basename(m).count(".") == 1)


PY_LIB = _runtime_python_lib()
PY_VER = os.path.basename(PY_LIB)  # e.g. "python3.13"

# Make Pitivi importable. The bundled flatpak app installs Pitivi under
# $APP/lib/pitivi/python.
sys.path.insert(0, os.path.join(APP, "lib", "pitivi", "python"))


# --- gi.overrides ---------------------------------------------------------
# The runtime ships a newer PyGObject than the app's site-packages. Its
# overrides require a `gi.module` API that doesn't exist in the older copy
# the app bundles. We use the APP's `gi` (older but matched to the app's
# overrides) by NOT putting the runtime's site-packages on PYTHONPATH (the
# AppRun arranges that). Re-inject the app's overrides path here defensively.
import gi.overrides  # noqa: E402

_app_overrides = os.path.join(APP, "lib", PY_VER, "site-packages",
                              "gi", "overrides")
if os.path.isdir(_app_overrides) and _app_overrides not in gi.overrides.__path__:
    gi.overrides.__path__.insert(0, _app_overrides)


# --- pitivi.configure relocation -----------------------------------------
# `configure.py` is generated at flatpak build time with /app and /usr paths
# baked in. We can't sed-patch it because it's hardlinked back to the user's
# flatpak install — so monkey-patch in memory before any pitivi import that
# captures the values.
import pitivi.configure as _cfg  # noqa: E402

_cfg.LIBDIR = os.path.join(APP, "lib")
_cfg.PKGDATADIR = os.path.join(APP, "share", "pitivi")


# --- i18n ---------------------------------------------------------------
gettext.bindtextdomain("pitivi", os.path.join(APP, "share", "locale"))
gettext.textdomain("pitivi")


# --- GdkPixbuf SVG fallback ---------------------------------------------
# AppRun replaces the runtime's libgdk_pixbuf with the host's (no glycin),
# but if the host happens to lack librsvg2-common, SVG loads will fail.
# Many Pitivi pixmaps are SVG; we ship pre-rendered .png siblings (built by
# build.sh) and silently fall back to the PNG when an SVG load throws.
import gi  # noqa: E402
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402

_orig_new_from_file_at_size = GdkPixbuf.Pixbuf.new_from_file_at_size


def _png_fallback_load(filename, *args, **kwargs):
    if isinstance(filename, str) and filename.endswith(".svg"):
        try:
            return _orig_new_from_file_at_size(filename, *args, **kwargs)
        except Exception:
            png = filename[:-4] + ".png"
            if os.path.exists(png):
                return _orig_new_from_file_at_size(png, *args, **kwargs)
            raise
    return _orig_new_from_file_at_size(filename, *args, **kwargs)


GdkPixbuf.Pixbuf.new_from_file_at_size = staticmethod(_png_fallback_load)


# --- Boot Pitivi --------------------------------------------------------
from pitivi.check import check_requirements, initialize_modules  # noqa: E402

initialize_modules()
if not check_requirements():
    sys.exit(2)

signal.signal(signal.SIGINT, signal.SIG_DFL)

from pitivi import application  # noqa: E402

application.Pitivi().run(sys.argv)
