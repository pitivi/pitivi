##
## configure.in
## 
## Made by guillaume casanova
## Email   <casano_g@epita.fr>
## 
##

SUBDIRS			= gnl src pixmaps docs ui conf

EXTRA_DIST = \
	pitivi.spec \
	NEWS \
	NORME \
	README \
	AUTHORS

noinst_HEADERS = \
	pitivi-mainapp.h \
	pitivi-windows.h \
	pitivi-projectwindows.h \
	pitivi-project.h \
	pitivi-toolbox.h \
	pitivi-effectswindow.h\
	pitivi-progressbar.h \
	pitivi-file-utils.h\
	pitivi-effectswindowproperties.h\
	pitivi-sourcefile.h\
	pitivi-sourcefilebin.h\
	pitivi-timelinewindow.h\
	pitivi-timelinecellrenderer.h\
	pitivi-timelinemedia.h\
	pitivi-sourcelistwindow.h \
	pitivi-checkbox.h\
	pitivi-projectsourcelist.h \
	pitivi-newprojectwindow.h  \
	pitivi-viewerwindow.h \
	pitivi-projectsettings.h \
	pitivi-projectsettingswindow.h \
	pitivi-stockicons.h \
	pitivi-menu-actions.h \
	pitivi-menu.h \
	pitivi-settings.h \
	pitivi-settingswindow.h \
	pitivi-splashscreenwindow.h \
	pitivi-gstelementsettings.h \
	pitivi-drawing.h \
	pitivi-mediatrackinfo.h \
	pitivi-controller.h \
	pitivi-debug.h \
	pitivi-ruler.h \
	pitivi-lplayerwindow.h \
	pitivi.h\
	pitivi-cursor.h\
	pitivi-cursorbits.h\
	pitivi-dragdrop.h\
	pitivi-effects_cat.h\
	pitivi-trackenum.h\
	pitivi-types.h\
	pitivi-units.h	

gnldir = $(includedir)/gnl
gnl_HEADERS = gnl.h gnlcomposition.h gnlgroup.h gnlmarshal.h gnlobject.h \
			gnloperation.h gnlsource.h gnltimeline.h gnltypes.h gnlversion.h

AUTOMAKE_OPTIONS = dist-bzip2

MMdir = $(datadir)/applications

release: dist
	make @PACKAGE@-@VERSION@.tar.gz.md5
	make @PACKAGE@-@VERSION@.tar.bz2.md5

# generate md5 sum files
%.md5: %
	md5sum $< > $@

rpm: dist
	rpm -ta $(distdir).tar.gz
