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
	pitivi-project.c \
	pitivi-toolbox.c \
	pitivi-effectswindow.c\
	pitivi-timelinewindow.c\
	pitivi-toolboxwindow.c	\
	pitivi-sourcelistwindow.c \
	pitivi-projectsourcelist.c \
	pitivi-newprojectwindow.c  \
	pitivi-viewerwindow.c \
	pitivi-projectsettings.c \
	pitivi-stockicons.c \
	pitivi-menu-actions.c \
	pitivi-menu.c \
	main.c

# our CFLAGS and LDFLAGS used for compiling and linking
# make sure you prefix these with the name of your binary

pitivi_CFLAGS  = $(GTK_CFLAGS) $(GLIB2_CFLAGS) $(GST_CFLAGS)
pitivi_LDFLAGS = $(GTK_LIBS) $(GLIB2_LIBS) $(GST_LIBS)

LEX_OUTPUT_ROOT	= lex.$*
YFLAGS		= -d -p request_lex

depend			:
			 makedepend -I../include/
