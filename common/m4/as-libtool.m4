dnl as-libtool.m4 0.1.3
dnl autostars m4 macro for libtool versioning
dnl thomas@apestaart.org
dnl
dnl AS_LIBTOOL(PREFIX, CURRENT, REVISION, AGE, RELEASE)
dnl example
dnl AS_VERSION(GST, 2, 0, 0)
dnl
dnl this macro
dnl - defines [$PREFIX]_CURRENT, REVISION AND AGE
dnl - defines [$PREFIX]_LIBVERSION
dnl - defines [$PREFIX]_LT_LDFLAGS to set versioning
dnl - AC_SUBST's them all
dnl
dnl if USE_RELEASE is used, then add a -release option to the LDFLAGS
dnl with the given release version
dnl then use [$PREFIX]_LT_LDFLAGS in the relevant Makefile.am's

AC_DEFUN([AS_LIBTOOL],
[
  [$1]_CURRENT=[$2]
  [$1]_REVISION=[$3]
  [$1]_AGE=[$4]
  [$1]_LIBVERSION=[$2]:[$3]:[$4]
  AC_SUBST([$1]_CURRENT)
  AC_SUBST([$1]_REVISION)
  AC_SUBST([$1]_AGE)
  AC_SUBST([$1]_LIBVERSION)

dnl  [$1]_LT_LDFLAGS="$[$1]_LT_LDFLAGS -version-info $[$1]_LIBVERSION"
  if test ! -z "[$5]"
  then
    [$1]_LT_LDFLAGS="$[$1]_LT_LDFLAGS -release [$5]"
  fi
  AC_SUBST([$1]_LT_LDFLAGS)

  AC_LIBTOOL_DLOPEN
  AM_PROG_LIBTOOL

  case "$host" in
    *-*-mingw*)
      as_libtool_win32=yes
      enable_static=no
      enable_shared=yes
      ;;
    *)
      as_libtool_win32=no
      ;;
  esac
  AM_CONDITIONAL(AS_LIBTOOL_WIN32, [test "$as_libtool_win32" = "yes"])

  m4_pattern_allow([AS_LIBTOOL_WIN32])
  m4_pattern_allow([AS_LIBTOOL_WIN32_TRUE])
  m4_pattern_allow([AS_LIBTOOL_WIN32_FALSE])
])
