pyexec_LTLIBRARIES = renderer.la

renderer_la_SOURCES = renderer.c
pyexecdir = $(libdir)/pitivi/python/pitivi/timeline/
renderer_la_CFLAGS = $(cairo_CFLAGS) $(py3cairo_CFLAGS) $(python3_CFLAGS)
renderer_la_LDFLAGS = -module -avoid-version $(LIBS) $(cairo_LIBS) $(py3cairo_LIBS) $(python3_LIBS)
