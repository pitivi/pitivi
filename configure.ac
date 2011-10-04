AC_PREREQ(2.52)

dnl initialize autoconf
dnl when going to/from release please set the nano (fourth number) right !
dnl releases only do Wall, cvs and prerelease does Werror too
AC_INIT(PiTiVi, 0.15.1,
    https://bugzilla.gnome.org/browse.cgi?product=pitivi,
    pitivi)

dnl initialize automake
AM_INIT_AUTOMAKE

dnl define PACKAGE_VERSION_* variables
AS_VERSION

dnl check if this is a release version
AS_NANO(PITIVI_CVS="no", PITIVI_CVS="yes")

dnl can autoconf find the source ?
AC_CONFIG_SRCDIR([pitivi/application.py])


AC_SUBST_FILE(AUTHORS)
AUTHORS=$srcdir/AUTHORS

dnl Note for packagers
dnl The following requirements are run-time requirements,
dnl make sure you don't forget them, even though you're able to
dnl build pitivi without them.
dnl
dnl For a more exhaustive list of checks, you can have a look at
dnl the runtime checks in pitivi/check.py

AC_SUBST(GTK_REQ, 2.24.0)
AC_SUBST(PYGTK_REQ, 2.17.0)
AC_SUBST(PYGST_REQ, 0.10.19)
AC_SUBST(GST_REQ, 0.10.28)
AC_SUBST(GNONLIN_REQ, 0.10.16)
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
AS_PATH_PYTHON(2.5)

dnl ALL_LINGUAS="fr"
GETTEXT_PACKAGE="pitivi"
AC_SUBST([GETTEXT_PACKAGE])
AC_DEFINE_UNQUOTED([GETTEXT_PACKAGE], "$GETTEXT_PACKAGE", [Gettext package])
AM_GLIB_GNU_GETTEXT
IT_PROG_INTLTOOL([0.35.0])

CONFIGURED_PYTHONPATH=$PYTHONPATH
AC_SUBST(CONFIGURED_PYTHONPATH)

CONFIGURED_LD_LIBRARY_PATH=$LD_LIBRARY_PATH
AC_SUBST(CONFIGURED_LD_LIBRARY_PATH)

CONFIGURED_GST_PLUGIN_PATH=$GST_PLUGIN_PATH
AC_SUBST(CONFIGURED_GST_PLUGIN_PATH)

AC_CONFIG_FILES([bin/pitivi], [chmod +x bin/pitivi])

GNOME_DOC_INIT([0.18.0])

dnl output stuff
AC_OUTPUT(
Makefile
bin/Makefile
common/Makefile
common/m4/Makefile
help/Makefile
pitivi/Makefile
pitivi/configure.py
pitivi/ui/Makefile
pitivi/log/Makefile
pitivi/timeline/Makefile
pitivi.spec
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
data/icons/scalable/Makefile
data/pixmaps/Makefile
data/ui/Makefile
data/renderpresets/Makefile
data/audiopresets/Makefile
data/videopresets/Makefile
)
