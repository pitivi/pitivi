m4_define([gi_req_version], [1.31.1])
m4_define([glib_req_version], [2.30.0])
m4_define([gstreamer_req_version], [1.4.0])
m4_define([gtk_req_version], [3.10.0])

AC_PREREQ(2.52)

dnl Note for packagers: see pitivi/check.py for the dependencies

dnl initialize autoconf
dnl when going to/from release please set the nano (fourth number) right !
dnl releases only do Wall, cvs and prerelease does Werror too
AC_INIT(Pitivi, 0.94,
    https://bugzilla.gnome.org/browse.cgi?product=pitivi,
    pitivi)

LT_INIT()

dnl initialize automake
AM_INIT_AUTOMAKE

dnl define PACKAGE_VERSION_* variables
AS_VERSION

dnl can autoconf find the source ?
AC_CONFIG_SRCDIR([pitivi/application.py])

AC_SUBST_FILE(AUTHORS)
AUTHORS=$srcdir/AUTHORS

AM_INIT_AUTOMAKE([foreign])
AC_SUBST(ACLOCAL_AMFLAGS, "-I m4 -I common/m4")
AC_CONFIG_MACRO_DIR([m4])

AS_AC_EXPAND(LIBDIR, $libdir)
AC_MSG_NOTICE(Storing library files in $LIBDIR)

AS_AC_EXPAND(DATADIR, $datadir)
AC_MSG_NOTICE(Storing data files in $DATADIR)

AS_AC_EXPAND(SYSCONFDIR, $sysconfdir)
AC_MSG_NOTICE(Storing configuration files in $SYSCONFDIR)

AS_AC_EXPAND(LOCALSTATEDIR, $localstatedir)
AC_MSG_NOTICE(Using localstatedir $LOCALSTATEDIR)

# python checks

# you can change the required python version bellow
AM_PATH_PYTHON([3])

AM_CHECK_PYTHON_HEADERS(, AC_MSG_ERROR([Python headers not found]))

# - 'SO' for PyPy, CPython 2.7-3.2
# - 'EXT_SUFFIX' for CPython3.3+ (http://bugs.python.org/issue16754)
# - fallback to '.so'
PYTHON_SO=`$PYTHON -c "import distutils.sysconfig, sys; get = distutils.sysconfig.get_config_var; sys.stdout.write(get('EXT_SUFFIX') or get('SO') or '.so');"`
AC_SUBST(PYTHON_SO)

dnl ALL_LINGUAS="fr"
GETTEXT_PACKAGE="pitivi"
AC_SUBST([GETTEXT_PACKAGE])
AC_DEFINE_UNQUOTED([GETTEXT_PACKAGE], "$GETTEXT_PACKAGE", [Gettext package])
AM_GLIB_GNU_GETTEXT
m4_ifdef([IT_PROG_INTLTOOL],
         [IT_PROG_INTLTOOL([0.35.0])],
         [AC_MSG_ERROR("The IT_PROG_INTLTOOL m4 macro is not available. Install intltool.")])

CONFIGURED_PYTHONPATH=$PYTHONPATH
AC_SUBST(CONFIGURED_PYTHONPATH)

CONFIGURED_LD_LIBRARY_PATH=$LD_LIBRARY_PATH
AC_SUBST(CONFIGURED_LD_LIBRARY_PATH)

CONFIGURED_GST_PLUGIN_PATH=$GST_PLUGIN_PATH
AC_SUBST(CONFIGURED_GST_PLUGIN_PATH)

CONFIGURED_GI_TYPELIB_PATH=$GI_TYPELIB_PATH
AC_SUBST(CONFIGURED_GI_TYPELIB_PATH)

AC_CONFIG_FILES([bin/pitivi], [chmod +x bin/pitivi])

dnl === GObject introspection =================================================

GOBJECT_INTROSPECTION_CHECK([gi_req_version])

PKG_CHECK_MODULES(GTK, [gtk+-3.0 >= gtk_req_version],
                        [HAVE_GTK=yes],
                        [HAVE_GTK=no])

AS_IF([test "x$HAVE_GTK" = xno],
      [AC_MSG_ERROR([GTK+ >= $gtk_req_version is required])])

PKG_CHECK_MODULES(GTK_X11, gtk+-x11-3.0 >= gtk_req_version, HAVE_GTK_X11=yes, HAVE_GTK_X11=no)
PKG_CHECK_MODULES(GTK_QUARTZ, gtk+-quartz-3.0 >= gtk_req_version, HAVE_GTK_QUARTZ=yes, HAVE_GTK_QUARTZ=no)
AM_CONDITIONAL(HAVE_GTK_X11, test "x$HAVE_GTK_X11" = "xyes")
AM_CONDITIONAL(HAVE_GTK_QUARTZ, test "x$HAVE_GTK_QUARTZ" = "xyes")

PKG_CHECK_MODULES(GSTREAMER, [gstreamer-1.0 >= gstreamer_req_version gstreamer-video-1.0 >= gstreamer_req_version],
                  [HAVE_GSTREAMER=yes],
                  [HAVE_GSTREAMER=no])
AC_SUBST(GTK_LIBS)


AS_IF([test "x$HAVE_GSTREAMER" = xno],
      [AC_MSG_ERROR([GStreamer >= $gstreamer_req_version is required])])

PKG_CHECK_MODULES([cairo], [cairo])
PKG_CHECK_MODULES([py3cairo], [py3cairo])
PKG_CHECK_MODULES([python3], [python3])

AC_ARG_ENABLE(help,
  AS_HELP_STRING([--disable-help],[disable help]),
  [
    case "${enableval}" in
      yes) BUILD_HELP=yes ;;
      no)  BUILD_HELP=no ;;
      *)   AC_MSG_ERROR(bad value ${enableval} for --disable-help) ;;
    esac
  ],
[BUILD_HELP=yes]) dnl Default value
AM_CONDITIONAL(BUILD_HELP, test "x$BUILD_HELP" = "xyes")

if test x$BUILD_HELP = xyes; then
  YELP_HELP_INIT
fi

PITIVI_CFLAGS="$GTK_CFLAGS $GSTREAMER_CFLAGS $GSTREAMER_VIDEO_CFLAGS"
PITIVI_LIBS="$LIBM $GTK_LIBS $GSTREAMER_LIBS $GSTREAMER_VIDEO_CFLAGS"

AC_SUBST(PITIVI_CFLAGS)
AC_SUBST(PITIVI_LIBS)

dnl output stuff
AC_OUTPUT(
Makefile
bin/Makefile
common/Makefile
common/m4/Makefile
help/Makefile
pitivi/Makefile
pitivi/configure.py
pitivi/dialogs/Makefile
pitivi/undo/Makefile
pitivi/utils/Makefile
pitivi/timeline/Makefile
pitivi/coptimizations/Makefile
po/Makefile.in
tests/Makefile
data/Makefile
data/pitivi.desktop.in
data/icons/Makefile
data/icons/16x16/Makefile
data/icons/22x22/Makefile
data/icons/24x24/Makefile
data/icons/32x32/Makefile
data/icons/48x48/Makefile
data/icons/256x256/Makefile
data/icons/512x512/Makefile
data/pixmaps/Makefile
data/ui/Makefile
data/renderpresets/Makefile
data/audiopresets/Makefile
data/videopresets/Makefile
)
