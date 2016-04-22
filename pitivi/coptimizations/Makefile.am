pyexec_LTLIBRARIES = renderer.la

renderer_la_SOURCES = renderer.c
pyexecdir = $(libdir)/pitivi/python/pitivi/timeline/
AM_CFLAGS = $(cairo_CFLAGS) $(py3cairo_CFLAGS) $(GST_ALL_CFLAGS) $(GSTREAMER_CFLAGS)
LIBS = $(cairo_LIBS) $(py3cairo_LIBS)$(GST_ALL_LIBS) $(GSTREAMER_LIBS)
renderer_la_CFLAGS = $(PYTHON_CFLAGS) $(AM_CFLAGS)
renderer_la_LDFLAGS = -module -avoid-version $(LIBS)
