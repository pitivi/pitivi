##
## Makefile.am
## 
## Made by guillaume casanova
## Email   <casano_g@epita.fr>
## 
##
##


#AUTOMAKE_OPTIONS	= foreign
#INCLUDES		= -I$(top_srcdir)/src/include

bin_PROGRAMS		= pitivi

pitivi_SOURCES		= \
	pitivi-mainapp.c \
	pitivi-windows.c \
	pitivi-projectwindows.c \
	pitivi-project.c \
	pitivi-toolbox.c \
	pitivi-effectswindow.c\
	pitivi-timelinewindow.c\
	pitivi-timelinecellrenderer.c\
	pitivi-timelinemedia.c\
	pitivi-toolboxwindow.c	\
	pitivi-sourcelistwindow.c \
	pitivi-checkbox.c\
	pitivi-projectsourcelist.c \
	pitivi-newprojectwindow.c  \
	pitivi-codecconfwindow.c  \
	pitivi-viewerwindow.c \
	pitivi-projectsettings.c \
	pitivi-projectsettingswindow.c \
	pitivi-stockicons.c \
	pitivi-menu-actions.c \
	pitivi-menu.c \
	pitivi-settings.c \
	pitivi-settingswindow.c \
	pitivi-splashscreenwindow.c \
	main.c

# our CFLAGS and LDFLAGS used for compiling and linking
# make sure you prefix these with the name of your binary

pitivi_CFLAGS  = $(GTK_CFLAGS) $(GLIB2_CFLAGS) $(GST_CFLAGS) $(GNL_CFLAGS)
pitivi_LDFLAGS = $(GTK_LIBS) $(GLIB2_LIBS) $(GST_LIBS) $(GNL_LIBS)

LEX_OUTPUT_ROOT	= lex.$*
YFLAGS		= -d -p request_lex

depend			:
			 makedepend -I../include/
