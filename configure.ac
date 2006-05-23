AC_PREREQ(2.52)

dnl initialize autoconf
dnl when going to/from release please set the nano (fourth number) right !
dnl releases only do Wall, cvs and prerelease does Werror too
AC_INIT(PiTiVi, 0.10.1,
    http://www.pitivi.org/,
    pitivi)

dnl initialize automake
AM_INIT_AUTOMAKE

dnl define PACKAGE_VERSION_* variables
AS_VERSION

dnl check if this is a release version
AS_NANO(PITIVI_CVS="no", PITIVI_CVS="yes")

dnl can autoconf find the source ?
AC_CONFIG_SRCDIR([pitivi/pitivi.py])


AC_SUBST_FILE(AUTHORS)
AUTHORS=$srcdir/AUTHORS

AC_SUBST(PYGTK_REQ, 2.8.0)
AC_SUBST(PYGST_REQ, 0.10.0)
AC_SUBST(GST_REQ, 0.10.4)
AC_SUBST(GNONLIN_REQ, 0.10.2)
AC_SUBST(PYCAIRO_REQ, 1.0.0)

AM_INIT_AUTOMAKE($PACKAGE, $VERSION)
AC_SUBST(ACLOCAL_AMFLAGS, "-I common/m4")

AS_AC_EXPAND(LIBDIR, $libdir)
AC_MSG_NOTICE(Storing library files in $LIBDIR)

AS_AC_EXPAND(DATADIR, $datadir)
AC_MSG_NOTICE(Storing data files in $DATADIR)

AS_AC_EXPAND(SYSCONFDIR, $sysconfdir)
AC_MSG_NOTICE(Storing configuration files in $SYSCONFDIR)

AS_AC_EXPAND(LOCALSTATEDIR, $localstatedir)
AC_MSG_NOTICE(Using localstatedir $LOCALSTATEDIR)

dnl check for python
AS_PATH_PYTHON(2.3)

dnl check for GStreamer
PKG_CHECK_MODULES(GST, gstreamer-0.10 >= $GST_REQ)

dnl check for pygtk
PKG_CHECK_MODULES(PYGTK, pygtk-2.0 >= $PYGTK_REQ)
PYGTK_DIR="`$PKG_CONFIG --variable=pyexecdir pygtk-2.0`"
AC_SUBST(PYGTK_DIR)
AC_MSG_NOTICE(Using pygtk installed in $PYGTK_DIR)

export PYTHONPATH=$PYGTK_DIR:$PYTHONPATH

dnl check for pycairo
AC_MSG_CHECKING(for pycairo)
prog="
import sys
try:
  import cairo
except ImportError:
  sys.exit(1)
if cairo.version < '$PYCAIRO_REQ':
  sys.exit(1)
else:
  sys.exit(0)
"
if $PYTHON -c "$prog"
then
  AC_MSG_RESULT(found)
else
  AC_MSG_RESULT(not found)
  AC_MSG_ERROR(
    [You need to have python cairo bindings >= $PYCAIRO_REQ installed])
fi

dnl check for libglade
AC_MSG_CHECKING(for gtk.glade)
prog="
import sys
try:
  import pygtk
  pygtk.require('2.0')
  import gtk.glade
except RuntimeError:
  sys.exit(0)
except ImportError:
  sys.exit(1)
sys.exit(0)
"
if $PYTHON -c "$prog" 1>&AC_FD_CC 2>&AC_FD_CC
then
  AC_MSG_RESULT(found)
else
  AC_MSG_RESULT(not found)
  AC_MSG_ERROR([You need to have python libglade bindings installed])
fi

dnl check for cairo support in pygtk
AC_MSG_CHECKING(for cairo support in PyGTK)
prog="
import sys
try:
  import pygtk
  pygtk.require('2.0')
  import gtk
except RuntimeError:
  sys.exit(0)
if not hasattr(gtk.gdk.Window, 'cairo_create'):
  sys.exit(1)
sys.exit(0)
"
if $PYTHON -c "$prog" 1>&AC_FD_CC 2>&AC_FD_CC
then
  AC_MSG_RESULT(found)
else
  AC_MSG_RESULT(not found)
  AC_MSG_ERROR([You need a version of PyGTK (Python bindings for GTK+) with cairo support enabled])
fi


dnl checks for gst-python
PKG_CHECK_MODULES(PYGST, gst-python-0.10 >= $PYGST_REQ)
PYGST_DIR="`$PKG_CONFIG --variable=pyexecdir gst-python-0.10`"
AC_SUBST(PYGST_DIR)
AC_MSG_NOTICE(Using gstreamer-python installed in $PYGST_DIR)

export PYTHONPATH=$PYGST_DIR:$PYTHONPATH

dnl check for GNonlin
prog="
import sys
import pygst; pygst.require('0.10')
import gst
plugin = gst.registry_get_default().find_plugin('gnonlin')
if plugin and plugin.get_version() >= '$GNONLIN_REQ':
  sys.exit(0)
sys.exit(1)
"
AC_MSG_CHECKING([for gnonlin >= $GNONLIN_REQ])
if $PYTHON -c "$prog" 1>&AC_FD_CC 2>&AC_FD_CC
then
  AC_MSG_RESULT(found)
else
  AC_MSG_RESULT(not found)
  AC_MSG_ERROR([You need to install the gnonlin plugins and make sure
 they are in your \$GST_PLUGIN_PATH.])
fi

dnl the gettext stuff needed
dnl AM_GNU_GETTEXT_VERSION(0.11.5)
dnl AM_GNU_GETTEXT([external])

CONFIGURED_PYTHONPATH=$PYTHONPATH
AC_SUBST(CONFIGURED_PYTHONPATH)

AC_CONFIG_FILES([bin/pitivi], [chmod +x bin/pitivi])

dnl output stuff
AC_OUTPUT(
Makefile
bin/Makefile
common/Makefile
common/m4/Makefile
pitivi/Makefile
pitivi/configure.py
pitivi/ui/Makefile
pitivi/pixmaps/Makefile
pitivi.spec
pitivi.desktop
)
