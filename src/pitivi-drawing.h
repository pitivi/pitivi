/* 
 * PiTiVi
 * Copyright (C) <2004>	 Guillaume Casanova <casano_g@epita.fr>
 *
 * This software has been written in EPITECH <http://www.epitech.net>
 * EPITECH is a computer science school in Paris - FRANCE -
 * under the direction of Flavien Astraud and Jerome Landrieu.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#ifndef PITIVI_DRAWING_H
#define PITIVI_DRAWING_H

#include <gtk/gtk.h>

/* Pixmap used by drawing */

/* #include "../pixmaps/blank.xpm" */

void
pitivi_drawing_set_pixmap_bg (GtkWidget *widget, GdkPixmap *pixmap);


GdkPixmap *
pitivi_drawing_getpixmap (GtkWidget *widget, char **xpm);


/* Defining Slides functions */

#define pitivi_draw_slide(widget, x, width) pitivi_drawing_gcslide (widget, NULL, x, 0, width)
#define pitivi_draw_pixslide(widget, x, width) pitivi_drawing_pixslide (widget, NULL, x, 0, width)

void 
pitivi_drawing_gcslide (GtkWidget *widget, 
			GdkGC *gc, 
			int x, 
			int y, 
			int width);

void
pitivi_drawing_pixslide (GtkWidget *widget, 
			 char *file, 
			 int x, 
			 int y, 
			 int width);

void 
draw_gdk_text_centered (GdkDrawable *drawable, GdkFont *font, GdkGC *gc,
			gint x, gint y, gint width, gint height,
			const gchar *text, gint text_length);

GdkWindow *
pitivi_drawing_getgdkwindow (GtkWidget *widget);


/* Defining GCs for graphical debug */

#define DEFAULT_WIDTH_DASHES 4
#define DEFAULT_MEDIA_SIZE 100


#define pitivi_drawing_bluegc() pitivi_drawing_GdkGCcolor_new (0, 0, 255)
#define pitivi_drawing_redgc() pitivi_drawing_GdkGCcolor_new (255, 0, 0)
#define pitivi_drawing_greengc() pitivi_drawing_GdkGCcolor_new (0, 255, 0)
#define pitivi_drawing_graygc() pitivi_drawing_GdkGCcolor_new (220, 220, 220)

GdkGC *
pitivi_drawing_GdkGCcolor_new ( guint8 red, 
			       guint8 green, 
			       guint8 blue);
void
pitivi_send_expose_event (GtkWidget * widget);

void
send_signal_to_childs_direct (GtkWidget *container, const gchar *signame, gpointer data);

void
pitivi_widget_changefont (GtkWidget *widget, const char *fontname);

void 
pitivi_drawing_selection_area (GtkWidget *widget, GdkRectangle *area, int width, char **dash);

void
draw_selection_dash (GtkWidget *widget, gpointer window, GdkColor *color, int width);

#endif /* PITIVI_DRAWING_H */
