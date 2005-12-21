AC_INIT(AUTHORS)

AS_VERSION(pitivi, PITIVI, 0, 2, 0, 1)
AC_SUBST(RELEASE, $PITIVI_RELEASE)

AC_SUBST_FILE(AUTHORS)
AUTHORS=$srcdir/AUTHORS

AC_SUBST(PYGTK_REQ, 2.8.0)
AC_SUBST(PYGST_REQ, 0.10.0)
AC_SUBST(PYGNOME_REQ, 2.10.0)
AC_SUBST(GST_REQ, 0.10.0)
dnl AC_SUBST(GNONLIN_REQ, 0.3.0)

AM_INIT_AUTOMAKE($PACKAGE, $VERSION)
AC_SUBST(ACLOCAL_AMFLAGS, "-I m4")

AS_AC_EXPAND(LIBDIR, $libdir)
AC_MSG_NOTICE(Storing library files in $LIBDIR)

AS_AC_EXPAND(DATADIR, $datadir)
AC_MSG_NOTICE(Storing data files in $DATADIR)

AS_AC_EXPAND(SYSCONFDIR, $sysconfdir)
AC_MSG_NOTICE(Storing configuration files in $SYSCONFDIR)

AS_AC_EXPAND(LOCALSTATEDIR, $localstatedir)
AC_MSG_NOTICE(Using localstatedir $LOCALSTATEDIR)

AC_DISABLE_STATIC
AC_PROG_LIBTOOL

dnl check for python
AS_PATH_PYTHON(2.3)
dnl useful when we compile our own python modules
dnl AM_CHECK_PYTHON_HEADERS(,[AC_MSG_ERROR(could not find Python headers)])

AS_AC_EXPAND(PYTHONDIR, $pythondir)
AC_MSG_NOTICE(Using pythondir $PYTHONDIR)

dnl check for GStreamer
PKG_CHECK_MODULES(GST, gstreamer-0.10 >= $GST_REQ)

dnl check for GNonlin
dnl PKG_CHECK_MODULES(GNONLIN, gnonlin >= $GNONLIN_REQ)

dnl check for pygtk
PKG_CHECK_MODULES(PYGTK, pygtk-2.0 >= $PYGTK_REQ)
PYGTK_DIR="`$PKG_CONFIG --variable=pyexecdir pygtk-2.0`"
AC_SUBST(PYGTK_DIR)
AC_MSG_NOTICE(Using pygtk installed in $PYGTK_DIR)
PYGTK_VERSION="`$PKG_CONFIG --modversion pygtk-2.0`"
if test "x$PYGTK_VERSION" = "x2.5.2"
then
  AC_MSG_ERROR([PyGTK 2.5.2 contains known bugs, please install other version])
fi

export PYTHONPATH=$PYGTK_DIR:$PYTHONPATH

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

dnl checks for gnome-python
PKG_CHECK_MODULES(PYGNOME, gnome-python-2.0 >= $PYGNOME_REQ)


dnl checks for gst-python
PKG_CHECK_MODULES(PYGST, gst-python-0.10 >= $PYGST_REQ)
PYGST_DIR="`$PKG_CONFIG --variable=pyexecdir gst-python-0.10`"
AC_SUBST(PYGST_DIR)
AC_MSG_NOTICE(Using gstreamer-python installed in $PYGST_DIR)

export PYTHONPATH=$PYGST_DIR:$PYTHONPATH
dnl AS_PYTHON_IMPORT([gst],,
dnl                  AC_MSG_ERROR([Maybe you forgot to set your PYTHONPATH?]))

dnl AS_PYTHON_IMPORT([gst, gst.interfaces],,
dnl                  AC_MSG_ERROR([You need to recompile gst-python with gst.interfaces support]))

dnl the gettext stuff needed
AM_GNU_GETTEXT_VERSION(0.11.5)
AM_GNU_GETTEXT([external])

dnl output stuff
AC_OUTPUT(
Makefile
bin/pitivi
bin/Makefile
common/Makefile
common/m4/Makefile
pitivi/Makefile
pitivi/configure.py
pitivi/ui/Makefile
pitivi/pixmaps/Makefile
pitivi.spec
)
