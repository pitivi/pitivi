dnl check for gstreamer
dnl check for installed gstreamer first
dnl if necessary, check for uninstalled gstreamer
dnl AC_SUBST GST_CFLAGS and GST_LIBS
AC_DEFUN([GST_GSTREAMER],[
  PKG_CHECK_MODULES(GST, gstreamer, HAVE_GST=yes, HAVE_GST=no)
  if test "x$HAVE_GST" = "xno";
  then
    PKG_CHECK_MODULES(GST, gstreamer-uninstalled, HAVE_GST=yes, exit)
  fi
  AC_SUBST(GST_CFLAGS)
  AC_SUBST(GST_LIBS)
])

