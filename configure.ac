dnl ************************************************************
dnl Autotools For Pitivi-GUI
dnl 
dnl Made By Casaxno <casano_g@epita.fr>
dnl See also : autogen.sh, src/Makefile.am
dnl
dnl ============Modifications===================================
dnl Author  Date	Version	Description
dnl ------------------------------------------------------------
dnl GC	   20/02/2004	0.1.1	Upgrading Version of GLIB to 2.3
dnl GC	   20/03/2004	0.1.1	Upgrading Version of GLIB to 2.4
dnl EH	   26/04/2004	0.1.1	Uses the common/ macros
dnl GC	   02/05/2004	0.1.1	erasing comment line libglade
dnl				+ adding dependence AC_OUTPUT (Pixmaps)
dnl*************************************************************

AC_INIT
AC_CANONICAL_TARGET([])
AM_MAINTAINER_MODE

dnl Fill in your package name and version here

AS_VERSION(pitivi, PITIVI_VERSION, 0, 1, 1, 4, GST_CVS="no", GST_CVS="yes")

dnl AUTOMAKE initialisation
AM_INIT_AUTOMAKE($PACKAGE, $VERSION)

dnl =========================
dnl Dispatching Sources
dnl ========================

dnl Check Libtool
AC_PROG_LIBTOOL()

AC_CONFIG_SRCDIR(src/main.c)
AM_CONFIG_HEADER(config.h)

dnl Add parameters for aclocal
dnl (This must come after AM_INIT_AUTOMAKE, since it modifies ACLOCAL)
ACLOCAL="$ACLOCAL -I common/m4 $ACLOCAL_FLAGS"

dnl =========================
dnl Cheching Programs
dnl =========================

AC_PROG_CC
AC_STDC_HEADERS
AM_PROG_CC_STDC
AC_ISC_POSIX

dnl Check for Presence of Lex And Yacc for later
dnl AC_PROG_YACC
dnl AM_PROG_LEX

dnl stuff found by autoscan
AC_CHECK_FUNCS([strstr])
AC_CHECK_HEADERS([unistd.h])
AC_C_CONST
AC_FUNC_STAT

dnl allow different autotools
AS_AUTOTOOLS_ALTERNATE()

GST_DEBUGINFO

dnl modify pkg-config path
AC_ARG_WITH(pkg-config-path, 
   AC_HELP_STRING([--with-pkg-config-path],[colon-separated list of pkg-config(1) dirs]),
   [export PKG_CONFIG_PATH=${withval}])

dnl decide on error flags
AS_COMPILER_FLAG(-Wall, GST_WALL="yes", GST_WALL="no")

if test "x$GST_WALL" = "xyes"; then
   GST_ERROR="$GST_ERROR -Wall -g3"

   if test "x$GST_CVS" = "xyes"; then
	AS_COMPILER_FLAG(-Werror,GST_ERROR="$GST_ERROR -Werror",GST_ERROR="$GST_ERROR")
   fi
fi

dnl Now we're ready to ask for gstreamer libs and cflags
dnl And we can also ask for the right version of gstreamer
HAVE_GST=no
GST_REQUIRED=0.8.7
AC_SUBST(GST_REQUIRED)

dnl fail back to 0.8
if test "x$HAVE_GST" = "xno"; then
  GST_MAJORMINOR=0.8
  PKG_CHECK_MODULES(GST, \
    gstreamer-$GST_MAJORMINOR >= $GST_REQUIRED \
    gstreamer-interfaces-$GST_MAJORMINOR >= $GST_REQUIRED \
    gstreamer-control-$GST_MAJORMINOR >= $GST_REQUIRED \
    gstreamer-gconf-$GST_MAJORMINOR >= $GST_REQUIRED,
    HAVE_GST=yes,HAVE_GST=no)
fi
                                                                                
dnl Give error and exit if we don't have gstreamer
if test "x$HAVE_GST" = "xno"; then
  AC_MSG_ERROR(you need gstreamer development packages installed !)
fi

dnl make GST_CFLAGS and GST_LIBS available
AC_SUBST(GST_CFLAGS)
AC_SUBST(GST_LIBS)

dnl If we need them, we can also use the plugin libraries
PKG_CHECK_MODULES(GST_LIBS, gstreamer-libs-$GST_MAJORMINOR >= $GST_REQUIRED,
                  HAVE_GST_LIBS=yes, HAVE_GST_LIBS=no)

dnl Give a warning if we don't have gstreamer libs
if test "x$HAVE_GST_LIBS" = "xno"; then
  AC_MSG_NOTICE(no GStreamer plugin libs found)
fi

dnl check for GTK
GTK2_REQ="2.4"
AC_SUBST(GTK2_REQ)

PKG_CHECK_MODULES(GTK, gtk+-2.0 >= $GTK2_REQ gconf-2.0 gdk-2.0 >= $GTK2_REQ libxml-2.0, ,exit)
AC_SUBST(GTK_LIBS)
AC_SUBST(GTK_CFLAGS)

dnl check for gnonlin
dnl PKG_CHECK_MODULES(GNL, gnonlin, ,exit)
dnl AC_SUBST(GNL_LIBS)
dnl AC_SUBST(GNL_CFLAGS)
GNL_CFLAGS="-I\$(top_srcdir)"
GNL_LIBS="\$(top_builddir)/gnl/libgnl.la"
AC_SUBST(GNL_CFLAGS)
AC_SUBST(GNL_LIBS)

GST_DOC()

dnl i18n stuff and gettext stuff
dnl AC_PROG_INTLTOOL([0.21])
dnl GETTEXT_PACKAGE=gst-player
dnl AC_SUBST(GETTEXT_PACKAGE)
dnl AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE,"$GETTEXT_PACKAGE",[Define gettext package])
dnl ALL_LINGUAS="nl no"
dnl AM_GLIB_GNU_GETTEXT

dnl Outputs
AC_OUTPUT(Makefile
	pitivi.spec
         src/Makefile
	 pixmaps/Makefile
	 ui/Makefile
	 gnl/Makefile
	 conf/Makefile
	 docs/Makefile
	 docs/gnl/Makefile
	 )
