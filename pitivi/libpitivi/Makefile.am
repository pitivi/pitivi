CLEANFILES =

if HAVE_GTK_QUARTZ
  AM_CPPFLAGS = '-xobjective-c'
endif

source_h = \
  pitiviviewer.h \
  pitivi.h

source_c = \
  pitiviviewer.c

noinst_HEADERS = $(source_h)

libpitivi_1_0_la_CFLAGS = $(AM_CFLAGS) $(PITIVI_CFLAGS)
libpitivi_1_0_la_LIBADD = $(shared_libadd) $(PITIVI_LIBS)
libpitivi_1_0_la_LDFLAGS = -module -avoid-version $(LIBS) 
libpitivi_1_0_la_SOURCES = $(source_c)

lib_LTLIBRARIES = libpitivi-1.0.la

INTROSPECTION_GIRS = Pitivi-1.0.gir

introspection_source_h = $(source_h)
introspection_source_c = $(source_c)
Pitivi-1.0.gir: $(INTROSPECTION_SCANNER) libpitivi-1.0.la
		$(INTROSPECTION_SCANNER) -v --namespace Pitivi \
		--nsversion=1.0 \
		--identifier-prefix=Pitivi \
		--symbol-prefix=pitivi \
		-DIN_GOBJECT_INTROSPECTION=1 \
		--library=libpitivi-1.0.la \
		--include=GLib-2.0 \
		--include=GObject-2.0 \
		--include=Gst-1.0 \
		--include=GstVideo-1.0 \
		--include=Gtk-3.0 \
		--libtool="${LIBTOOL}" \
		--pkg glib-2.0 \
		--pkg gobject-2.0 \
		--pkg gstreamer-1.0 \
		--pkg gtk+-3.0 \
		--output $@ \
		$(introspection_source_h) \
		$(introspection_source_c)

girdir = $(datadir)/gir-1.0
nodist_gir_DATA = $(INTROSPECTION_GIRS)
CLEANFILES += $(nodist_gir_DATA)

typelibdir = $(libdir)/girepository-1.0
nodist_typelib_DATA = $(INTROSPECTION_GIRS:.gir=.typelib)
CLEANFILES += $(nodist_typelib_DATA)

%.typelib: %.gir $(INTROSPECTION_COMPILER)
	$(AM_V_GEN)$(INTROSPECTION_COMPILER) \
	--includedir='/home/thiblahute/devel/pitivi/1.0-uninstalled/pitivi/pitivi/libpitivi' \
	--includedir=`$(PKG_CONFIG) --variable=girdir gstreamer-1.0` \
	--includedir=`$(PKG_CONFIG) --variable=girdir gstreamer-video-1.0` \
	--includedir=`$(PKG_CONFIG) --variable=girdir gtk+-3.0` \
   $(INTROSPECTION_COMPILER_OPTS) $< -o $(@F)
