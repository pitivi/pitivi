##
## Makefile.am
## 
## Made by guillaume casanova
## Email   <casano_g@epita.fr>
## 
##
##


INCLUDES		= -I$(top_srcdir)/src/include\
			-I$(top_srcdir)/gnl/\
			-DDATADIR=\""$(datadir)"\"

bin_PROGRAMS		= pitivi

pitivi_SOURCES		= \
	pitivi-mainapp.c \
	pitivi-windows.c \
	pitivi-projectwindows.c \
	pitivi-project.c \
	pitivi-toolbox.c \
	pitivi-effectswindow.c\
	pitivi-progressbar.c \
	pitivi-file-utils.c\
	pitivi-effectswindowproperties.c\
	pitivi-sourcefile.c\
	pitivi-sourcefilebin.c\
	pitivi-timelinewindow.c\
	pitivi-timelinecellrenderer.c\
	pitivi-timelinecellrenderer-resizing.c\
	pitivi-timelinecellrenderer-moving.c\
	pitivi-timelinemedia.c\
	pitivi-sourcelistwindow.c \
	pitivi-checkbox.c\
	pitivi-projectsourcelist.c \
	pitivi-newprojectwindow.c  \
	pitivi-viewerwindow.c \
	pitivi-projectsettings.c \
	pitivi-projectsettingswindow.c \
	pitivi-stockicons.c \
	pitivi-menu-actions.c \
	pitivi-menu.c \
	pitivi-settings.c \
	pitivi-settingswindow.c \
	pitivi-splashscreenwindow.c \
	pitivi-gstelementsettings.c \
	pitivi-drawing.c \
	pitivi-mediatrackinfo.c \
	pitivi-controller.c \
	pitivi-debug.c \
	pitivi-ruler.c \
	pitivi-lplayerwindow.c \
	main.c

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
	pitivi-sourceitem.h\
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

# our CFLAGS and LDFLAGS used for compiling and linking
# make sure you prefix these with the name of your binary

pitivi_CFLAGS  = -Wall -Werror -O3 -fno-strict-aliasing $(GTK_CFLAGS) $(GLIB2_CFLAGS) $(GST_CFLAGS) $(GNL_CFLAGS)
pitivi_LDFLAGS = -Wall -Werror -O3 $(GTK_LIBS) $(GLIB2_LIBS) $(GST_LIBS) $(GNL_LIBS)

LEX_OUTPUT_ROOT	= lex.$*
YFLAGS		= -d -p request_lex

depend			:
			 makedepend -I../include/
