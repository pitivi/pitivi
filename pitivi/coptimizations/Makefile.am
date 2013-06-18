pyexecdir=$(PWD)

pyexec_LTLIBRARIES = renderer.la

renderer_la_SOURCES = renderer.c
AM_CFLAGS = $(cairo_CFLAGS)
LIBS = $(cairo_LIBS)
renderer_la_CFLAGS = $(PYTHON_CFLAGS) $(AM_CFLAGS)
renderer_la_LDFLAGS = -module -avoid-version -export-symbols-regex initrenderer $(LIBS)
