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

#include "pitivi-drawing.h"

// default Dashes
static char gdefault_dash [2] = {5, 4};

void
pitivi_send_expose_event (GtkWidget * widget)
{
  GdkEventExpose ev;
  gboolean retval;
  
  gtk_signal_emit_by_name (GTK_OBJECT (widget), "expose_event", &ev, &retval);
}

void
pitivi_drawing_set_pixmap_bg (GtkWidget *widget, GdkPixmap *pixmap)
{
  GtkStyle  *style;

  style = gtk_widget_get_style (widget);
  style = gtk_style_copy (style);
  if (pixmap && pixmap != (GdkPixmap*)GDK_PARENT_RELATIVE) gdk_pixmap_ref (pixmap);
  if (style->bg_pixmap[0] && style->bg_pixmap[0] != (GdkPixmap*)GDK_PARENT_RELATIVE) 
    gdk_pixmap_unref (style->bg_pixmap[0]);
  style->bg_pixmap[0] = pixmap;
  gtk_widget_set_style (GTK_WIDGET(widget), style);
  gtk_style_unref (style);
}


GdkPixmap *
pitivi_drawing_getpixmap (GtkWidget *widget, char **xpm)
{
  GdkPixmap   *pixmap;
  GdkColormap *colormap;
  GdkBitmap   *mask;
  GdkColor    trans;

  colormap = gtk_widget_get_colormap (widget);
  pixmap = gdk_pixmap_colormap_create_from_xpm_d (widget->window, 
						  colormap, 
						  &mask,  
						  &trans,
						  xpm);
  return (pixmap);
}


GdkWindow *
pitivi_drawing_getgdkwindow (GtkWidget *widget)
{
  GdkWindow *window;
    
  if (GTK_IS_LAYOUT (widget))
    window = GDK_WINDOW (GTK_LAYOUT (widget)->bin_window);
  else
    window = GDK_WINDOW (widget->window);
  return ( window );
}

void 
pitivi_drawing_gcslide (GtkWidget *widget, 
			GdkGC *gc, 
			int x, 
			int y, 
			int width)
{
  GdkWindow *window;
  
  window = pitivi_drawing_getgdkwindow (widget);
  gtk_paint_box (widget->style, window,
		 GTK_STATE_NORMAL, GTK_SHADOW_OUT,
		 NULL, widget, "slidedefault",
		 x, y, width, widget->allocation.height);
  
  if (!gc)
    gc = pitivi_drawing_graygc();
  gdk_draw_rectangle (window, gc,
		      TRUE,
		      x+1, y+1,
		      width-2, widget->allocation.height-2);
}

void
pitivi_drawing_pixslide (GtkWidget *widget, 
		      char *file, 
		      int x, 
		      int y, 
		      int width)
{
  GdkWindow *window;
  GdkPixbuf *pix;

  window = pitivi_drawing_getgdkwindow (widget);
  if (!file)
    pix = gdk_pixbuf_new_from_file_at_size ("../pixmaps/blank.xpm", 
					    width-1, 
					    widget->allocation.height-1, 
					    NULL);
  else
    pix = gdk_pixbuf_new_from_file_at_size (file, 
					    width-1, 
					    widget->allocation.height-1, 
					    NULL);
  gtk_paint_box (widget->style, window,
		 GTK_STATE_NORMAL, GTK_SHADOW_OUT,
		 NULL, widget, "slidedefault",
		 x, y, width, widget->allocation.height);
  
  gdk_pixbuf_render_to_drawable (pix, 
				 window, 
				 widget->style->fg_gc[0], 0, 0, x+1, 1, 
				 width-1, widget->allocation.height-1, 
				 GDK_RGB_DITHER_NONE, 0, 0);
}


GdkGC *
pitivi_drawing_GdkGCcolor_new(guint8 red, guint8 green, guint8 blue)
{
  static GdkPixmap *window=NULL;
  GdkColor *color;
  GdkGC *gc;

  if (!window)
    window=gdk_pixmap_new(NULL, 1, 1,
			  gdk_visual_get_system()->depth);
  gc = gdk_gc_new(window);
  color = (GdkColor *) g_new(GdkColor, 1);

  color->red = red * (65535 / 255);
  color->green = green * (65535 / 255);
  color->blue = blue * (65535 / 255);
  color->pixel = (gulong) (red * 65536 + green * 256 + blue);
  gdk_color_alloc(gdk_colormap_get_system(), color);
  gdk_gc_set_foreground(gc, color);
  return gc;
}

void
pitivi_widget_changefont (GtkWidget *widget, const char *fontname)
{
  PangoFontDescription *font_desc = pango_font_description_new ();
  font_desc = pango_font_description_from_string (fontname);
  gtk_widget_modify_font (widget, font_desc);
  pango_font_description_free (font_desc);
}

void 
pitivi_drawing_selection_area (GtkWidget *widget, GdkRectangle *area, int width, char **dash)
{
  GdkGC *style = gdk_gc_new ( widget->window );
  GdkWindow *window;
  
  if (width == 0)
    width = DEFAULT_WIDTH_DASHES;
  if (dash == NULL)
    gdk_gc_set_dashes ( style, 0, (gint8*)gdefault_dash, sizeof (gdefault_dash) / 2);
  else
    gdk_gc_set_dashes ( style, 0, (gint8*)dash, sizeof (dash) / 2); 
  gdk_gc_set_line_attributes ( style, width, GDK_LINE_ON_OFF_DASH, GDK_CAP_BUTT, GDK_JOIN_MITER);
  if (GTK_IS_LAYOUT (widget))
    window = GDK_WINDOW (GTK_LAYOUT (widget)->bin_window);
  else
    window = GDK_WINDOW (widget->window);
  gdk_draw_rectangle ( window, style, 
		       FALSE, 
		       area->x, area->y,
		       area->width, 
		       area->height);
  if (GTK_IS_LAYOUT (widget))
    gtk_paint_hline (widget->style,
		     window, 
		     GTK_STATE_NORMAL,
		     NULL, widget, "middle-line",
		     0, widget->allocation.width, widget->allocation.height/2);
}

void 
pitivi_drawing_selection (GtkWidget *widget, int width, char **dash)
{
  GdkGC *style = gdk_gc_new ( widget->window );
  GdkWindow *window;
  
  if (width == 0)
    width = DEFAULT_WIDTH_DASHES;
  if (dash == NULL)
    gdk_gc_set_dashes ( style, 0, (gint8*)gdefault_dash, sizeof (gdefault_dash) / 2);
  else
    gdk_gc_set_dashes ( style, 0, (gint8*)dash, sizeof (dash) / 2); 
  gdk_gc_set_line_attributes ( style, width, GDK_LINE_ON_OFF_DASH, GDK_CAP_BUTT, GDK_JOIN_MITER);
  if (GTK_IS_LAYOUT (widget))
    window = GDK_WINDOW (GTK_LAYOUT (widget)->bin_window);
  else
    window = GDK_WINDOW (widget->window);
  gdk_draw_rectangle ( window, style, 
		       FALSE, 
		       widget->allocation.x, 0, 
		       widget->allocation.width, widget->allocation.height);
}

void
draw_selection_dash (GtkWidget *widget, GdkColor *color, int width)
{
  char dash [2] = {1, 1};
  GdkGC *style = gdk_gc_new ( widget->window );
  GdkWindow *window;
  
  GdkColormap *cmap = gdk_colormap_get_system ();
  gdk_gc_copy (style, widget->style->black_gc);
  gdk_colormap_alloc_color (cmap, color, FALSE, TRUE);
  gdk_gc_set_foreground (style, color);
  gdk_gc_set_dashes ( style, 0, (gint8*)dash, sizeof (dash) / 2); 
  gdk_gc_set_line_attributes ( style, width, GDK_LINE_ON_OFF_DASH, GDK_CAP_BUTT, GDK_JOIN_MITER);
  gdk_draw_rectangle ( GDK_WINDOW (widget->window), style, FALSE, 0, 1, widget->allocation.width-3, widget->allocation.height-3);
  gdk_gc_unref (style);
}

void 
draw_gdk_text_centered (GdkDrawable *drawable, GdkFont *font, GdkGC *gc,
			gint x, gint y, gint width, gint height,
			const gchar *text, gint text_length)
{
  gint text_width = gdk_text_width(font, text, text_length);
  gint text_height = gdk_text_height(font, text, text_length);
  
  gdk_draw_text (drawable, font, gc,
		 x+width/2-text_width/2, y+height/2+text_height/2,
		 text, text_length);
}

void
send_signal_to_childs_direct (GtkWidget *container, const gchar *signame, gpointer data)
{
  GList	*childlist;
  
  childlist = gtk_container_get_children (GTK_CONTAINER (container));
   for (; childlist; childlist = childlist->next)
     if (GTK_IS_LAYOUT (childlist->data) || (GTK_IS_LAYOUT (container)))
       g_signal_emit_by_name (GTK_OBJECT (childlist->data), signame, data);
   g_list_free ( childlist );   
}

gint 
compare_littlechild (gconstpointer a, gconstpointer b)
{
  GtkWidget *wa, *wb;
  
  wa = GTK_WIDGET (a);
  wb = GTK_WIDGET (b);
  
  if (wa->allocation.x > wb->allocation.x)
    return 1;
  else if (wa->allocation.x < wb->allocation.x)
    return -1;
  return 0;
}

gint 
compare_bigchild (gconstpointer a, gconstpointer b)
{
  GtkWidget *wa, *wb;
  
  wa = GTK_WIDGET (a);
  wb = GTK_WIDGET (b);
  
  if (wa->allocation.x > wb->allocation.x)
    return -1;
  else if (wa->allocation.x < wb->allocation.x)
    return 1;
  return 0;
}
