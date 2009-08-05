AC_PREREQ(2.52)

dnl initialize autoconf
dnl when going to/from release please set the nano (fourth number) right !
dnl releases only do Wall, cvs and prerelease does Werror too
AC_INIT(PiTiVi, 0.13.1.2,
    http://www.pitivi.org/,
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

AC_SUBST(PYGTK_REQ, 2.14.0)
AC_SUBST(PYGST_REQ, 0.10.16)
AC_SUBST(GST_REQ, 0.10.24)
AC_SUBST(GNONLIN_REQ, 0.10.11.3)
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
pitivi/elements/Makefile
pitivi/factories/Makefile
pitivi/log/Makefile
pitivi/formatters/Makefile
pitivi/pixmaps/Makefile
pitivi/timeline/Makefile
pitivi.spec
pitivi.desktop
po/Makefile.in
tests/Makefile
icons/Makefile
icons/16x16/Makefile
icons/22x22/Makefile
icons/24x24/Makefile
icons/32x32/Makefile
icons/48x48/Makefile
)
