AC_DEFUN([GST_DOC], [
AC_ARG_WITH(html-dir, AC_HELP_STRING([--with-html-dir=PATH], [path to installed docs]))

if test "x$with_html_dir" = "x" ; then
  HTML_DIR='${datadir}/gtk-doc/html'
else
  HTML_DIR=$with_html_dir
fi

AC_SUBST(HTML_DIR)

dnl check for gtk-doc
AC_CHECK_PROG(HAVE_GTK_DOC, gtkdoc-scangobj, true, false)
gtk_doc_min_version=1.0
if $HAVE_GTK_DOC ; then
    gtk_doc_version=`gtkdoc-mkdb --version`
    AC_MSG_CHECKING([gtk-doc version ($gtk_doc_version) >= $gtk_doc_min_version])
    if perl -w <<EOF
      (\$min_version_major, \$min_version_minor ) = "$gtk_doc_min_version" =~ /^(\d)+\.(\d+)$/;
      (\$gtk_doc_version_major, \$gtk_doc_version_minor ) = "$gtk_doc_version" =~ /^(\d)+\.(\d+)$/;
      exit (("$gtk_doc_version" =~ /^[[0-9]]+\.[[0-9]]+$/) &&
            ((\$gtk_doc_version_major > \$min_version_major) ||
	     (\$gtk_doc_version_major == \$min_version_major) &&
	     (\$gtk_doc_version_minor >= \$min_version_minor))  ? 0 : 1);
EOF
   then
      AC_MSG_RESULT(yes)
   else
      AC_MSG_RESULT(no)
      HAVE_GTK_DOC=false
   fi
fi

# don't you love undocumented command line options?
GTK_DOC_SCANOBJ="gtkdoc-scangobj --nogtkinit"
AC_SUBST(HAVE_GTK_DOC)
AC_SUBST(GTK_DOC_SCANOBJ)

dnl check for docbook tools
AC_CHECK_PROG(HAVE_DOCBOOK2PS, docbook2ps, true, false)
AC_CHECK_PROG(HAVE_DOCBOOK2HTML, docbook2html, true, false)
AC_CHECK_PROG(HAVE_JADETEX, jadetex, true, false)
AC_CHECK_PROG(HAVE_PS2PDF, ps2pdf, true, false)

dnl check if we can process docbook stuff
AS_DOCBOOK(HAVE_DOCBOOK=true, HAVE_DOCBOOK=false)

dnl check for extra tools
AC_CHECK_PROG(HAVE_DVIPS, dvips, true, false)

dnl check for image conversion tools
AC_CHECK_PROG(HAVE_FIG2DEV, fig2dev, true, false)
if test "x$HAVE_FIG2DEV" = "xfalse" ; then
  AC_MSG_WARN([Did not find fig2dev (from xfig), images will not be generated.])
fi

dnl The following is a hack: if fig2dev doesn't display an error message
dnl for the desired type, we assume it supports it.
HAVE_FIG2DEV_EPS=false
if test "x$HAVE_FIG2DEV" = "xtrue" ; then
  fig2dev_quiet=`fig2dev -L pdf </dev/null 2>&1 >/dev/null`
  if test "x$fig2dev_quiet" = "x" ; then
    HAVE_FIG2DEV_EPS=true
  fi
fi
HAVE_FIG2DEV_PNG=false
if test "x$HAVE_FIG2DEV" = "xtrue" ; then
  fig2dev_quiet=`fig2dev -L png </dev/null 2>&1 >/dev/null`
  if test "x$fig2dev_quiet" = "x" ; then
    HAVE_FIG2DEV_PNG=true
  fi
fi
HAVE_FIG2DEV_PDF=false
if test "x$HAVE_FIG2DEV" = "xtrue" ; then
  fig2dev_quiet=`fig2dev -L pdf </dev/null 2>&1 >/dev/null`
  if test "x$fig2dev_quiet" = "x" ; then
    HAVE_FIG2DEV_PDF=true
  fi
fi

AC_CHECK_PROG(HAVE_PNGTOPNM, pngtopnm, true, false)
AC_CHECK_PROG(HAVE_PNMTOPS,  pnmtops,  true, false)
AC_CHECK_PROG(HAVE_EPSTOPDF, epstopdf, true, false)

dnl check if we can generate HTML
if test "x$HAVE_DOCBOOK2HTML" = "xtrue" && \
   test "x$HAVE_DOCBOOK" = "xtrue" && \
   test "x$HAVE_FIG2DEV_PNG" = "xtrue"; then
  DOC_HTML=true
  AC_MSG_NOTICE(Will output HTML documentation)
else
  DOC_HTML=false
  AC_MSG_NOTICE(Will not output HTML documentation)
fi

dnl check if we can generate PS
if test "x$HAVE_DOCBOOK2PS" = "xtrue" && \
   test "x$HAVE_DOCBOOK" = "xtrue" && \
   test "x$HAVE_JADETEX" = "xtrue" && \
   test "x$HAVE_FIG2DEV_EPS" = "xtrue" && \
   test "x$HAVE_DVIPS" = "xtrue" && \
   test "x$HAVE_PNGTOPNM" = "xtrue" && \
   test "x$HAVE_PNMTOPS" = "xtrue"; then
  DOC_PS=true
  AC_MSG_NOTICE(Will output PS documentation)
else
  DOC_PS=false
  AC_MSG_NOTICE(Will not output PS documentation)
fi

dnl check if we can generate PDF - using only ps2pdf
if test "x$DOC_PS" = "xtrue" && \
   test "x$HAVE_DOCBOOK" = "xtrue" && \
   test "x$HAVE_PS2PDF" = "xtrue"; then
  DOC_PDF=true
  AC_MSG_NOTICE(Will output PDF documentation)
else
  DOC_PDF=false
  AC_MSG_NOTICE(Will not output PDF documentation)
fi

AS_PATH_PYTHON(2.1)
AC_SUBST(PYTHON)

AC_ARG_ENABLE(docs-build,
AC_HELP_STRING([--disable-docs-build],[disable building of documentation]),
[case "${enableval}" in
  yes)
    if test "x$HAVE_GTK_DOC" = "xtrue" && \
       test "x$HAVE_DOCBOOK" = "xtrue"; then
      BUILD_DOCS=yes
    else
      BUILD_DOCS=no
    fi ;;
  no)  BUILD_DOCS=no ;;
  *) AC_MSG_ERROR(bad value ${enableval} for --disable-docs-build) ;;
esac],
[BUILD_DOCS=yes]) dnl Default value

dnl AC_ARG_ENABLE(plugin-docs,
dnl [  --enable-plugin-docs         enable the building of plugin documentation
dnl                                (this is currently broken, so off by default)],
dnl [case "${enableval}" in
dnl   yes) BUILD_PLUGIN_DOCS=yes ;;
dnl   no)  BUILD_PLUGIN_DOCS=no ;;
dnl   *) AC_MSG_ERROR(bad value ${enableval} for --enable-plugin-docs) ;;
dnl esac], 
dnl [BUILD_PLUGIN_DOCS=yes]) dnl Default value
BUILD_PLUGIN_DOCS=no

AM_CONDITIONAL(HAVE_GTK_DOC,        $HAVE_GTK_DOC)
AM_CONDITIONAL(HAVE_DOCBOOK,        $HAVE_DOCBOOK)
AM_CONDITIONAL(BUILD_DOCS,          test "x$BUILD_DOCS" = "xyes")
AM_CONDITIONAL(BUILD_PLUGIN_DOCS,   test "x$BUILD_PLUGIN_DOCS" = "xyes")
AM_CONDITIONAL(DOC_HTML,            $DOC_HTML)
AM_CONDITIONAL(DOC_PDF,             $DOC_PDF)
AM_CONDITIONAL(DOC_PS,              $DOC_PS)
])

