AC_DEFUN([GST_GLIB2_CHECK], [
dnl === GLib 2 ===
dnl Minimum required version of GLib2
GLIB2_REQ="1.3.12"
AC_SUBST(GLIB2_REQ)

dnl Check for glib2
PKG_CHECK_MODULES(GLIB2, glib-2.0 >= $GLIB2_REQ gobject-2.0 gthread-2.0 gmodule-2.0,
  HAVE_GLIB2=yes,HAVE_GLIB2=no)
GLIB_LIBS=$GLIB2_LIBS
GLIB_CFLAGS=$GLIB2_CFLAGS
AC_SUBST(GLIB_LIBS)
AC_SUBST(GLIB_CFLAGS)

if test "x$HAVE_GLIB2" = "xno"; then
  AC_MSG_ERROR([This package requires GLib 2.0 to compile.])
fi
])
