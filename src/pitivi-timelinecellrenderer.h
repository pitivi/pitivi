/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      Guillaume Casanova <casano_g@epita.fr>
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

#ifndef PITIVI_TIMELINECELLRENDERER_H
#define PITIVI_TIMELINECELLRENDERER_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include <gtk/gtk.h>
#include "pitivi-types.h"
#include "pitivi-timelinewindow.h"
#include "pitivi-cursor.h"
#include "pitivi-trackenum.h"
#include "pitivi-units.h"


/*
 * Type macros.
 */

#define EVENT_METHOD(i, x) GTK_WIDGET_GET_CLASS(i)->x

#define FIXED_WIDTH   7200
#define FIXED_HEIGHT  50

// Move on graphic source
#define MY_MAX 100000000


//Mouse Clicks

#define PITIVI_MOUSE_LEFT_CLICK   1
#define PITIVI_MOUSE_CENTER_CLICK 2
#define PITIVI_MOUSE_RIGHT_CLICK  3


#define PITIVI_TIMELINECELLRENDERER_TYPE (pitivi_timelinecellrenderer_get_type ())
#define PITIVI_TIMELINECELLRENDERER(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_TIMELINECELLRENDERER_TYPE, PitiviTimelineCellRenderer))
#define PITIVI_TIMELINECELLRENDERER_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_TIMELINECELLRENDERER_TYPE, PitiviTimelineCellRendererClass))
#define PITIVI_IS_TIMELINECELLRENDERER(obj) (GTK_CHECK_TYPE ((obj), PITIVI_TIMELINECELLRENDERER_TYPE))
#define PITIVI_IS_TIMELINECELLRENDERER_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_TIMELINECELLRENDERER_TYPE))
#define PITIVI_TIMELINECELLRENDERER_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_TIMELINECELLRENDERER_TYPE, PitiviTimelineCellRendererClass))

typedef struct _PitiviTimelineCellRendererPrivate PitiviTimelineCellRendererPrivate;
typedef struct _PitiviTimelineMediaChild PitiviTimelineMediaChild;

struct _PitiviTimelineCellRenderer
{
  GtkLayout parent;
  
  /* public members */
  PitiviLayerType	track_type;
  guint			track_nb;
  GtkWidget		*linked_track;
  GtkWidget		*effects_track;
  GList			*children;
  
  /* nb elemnts added no use for */
  
  gint64	        *nb_added;


  /* private */
  PitiviTimelineCellRendererPrivate	*private;
};

struct _PitiviTimelineCellRendererClass
{
  GtkLayoutClass parent;

  /* class members */
  
  void (* activate)	     (PitiviTimelineCellRenderer *cell);
  void (* deactivate)	     (PitiviTimelineCellRenderer *cell);
  void (* select)	     (PitiviTimelineCellRenderer *cell);
  void (* deselect)	     (PitiviTimelineCellRenderer *cell);
  void (* key_delete)	     (PitiviTimelineCellRenderer *cell);
  void (* delete)	     (PitiviTimelineCellRenderer *cell, gpointer data);
  void (* drag_source_begin) (PitiviTimelineCellRenderer *cell, gpointer data);
  void (* drag_source_end)   (PitiviTimelineCellRenderer *cell, gpointer data);
  void (* dbk_source)	     (PitiviTimelineCellRenderer *cell, gpointer data);
  void (* cut_source)	     (PitiviTimelineCellRenderer *cell, guint x, gpointer data);
  void (* zoom_changed)	     (PitiviTimelineCellRenderer *cell);
  void (* rendering)	     (PitiviTimelineCellRenderer *cell);
};


guint
convert_time_pix (PitiviTimelineCellRenderer *self, gint64 timelength);
gint64
convert_pix_time (PitiviTimelineCellRenderer *self, guint pos);

/* used by PITIVI_TIMELINECELLRENDERER_TYPE */
GType pitivi_timelinecellrenderer_get_type (void);

/*
 * Method definitions.
 */

GtkWidget	*pitivi_timelinecellrenderer_new (guint track_nb, PitiviLayerType track_type, PitiviTimelineWindow *tw);
PitiviCursor    *pitivi_getcursor_id (GtkWidget *widget);
gboolean	pitivi_add_to_layout (GtkWidget *self, GtkWidget *widget, gint x, gint y);

PitiviLayerType	pitivi_check_media_type (PitiviSourceFile *sf);

/* Deactivation of signals */

void		pitivi_timelinecellrenderer_activate (PitiviTimelineCellRenderer *self);
void		pitivi_timelinecellrenderer_deactivate (PitiviTimelineCellRenderer *self);

void		pitivi_timelinecellrenderer_zoom_changed (PitiviTimelineCellRenderer *self);
GtkWidget *	pitivi_timelinecellrenderer_media_selected_ontrack  ( PitiviTimelineCellRenderer *cell );
void		pitivi_setback_tracktype ( PitiviTimelineCellRenderer *self );
void		pitivi_layout_put (GtkLayout *layout, GtkWidget *widget, gint x, gint y);
void		pitivi_calculate_priorities ( GtkWidget *widget );
void		pitivi_layout_add_to_composition (PitiviTimelineCellRenderer *self, PitiviTimelineMedia *media);
void		pitivi_layout_remove_from_composition (PitiviTimelineCellRenderer *self, PitiviTimelineMedia *media);
void		pitivi_timelinecellrenderer_drag_on_track (PitiviTimelineCellRenderer *self, 
							   GtkWidget *source,
							   int x,
							   int y);

/* Resizing */

void pitivi_timelinecellrenderer_resize (PitiviTimelineCellRenderer *self, PitiviTimelineMedia *media);
void pitivi_timelinecellrenderer_resizing_media (PitiviTimelineMedia *source, PitiviTimelineCellRenderer *self, guint decrement, guint x);

/* Moving / Adding */

GtkWidget **layout_intersection_widget (GtkWidget *self, GtkWidget *widget, gint x, gboolean move);
void	  assign_next_prev (PitiviTimelineCellRenderer *self);
void	  link_widgets ( PitiviTimelineMedia *media1, PitiviTimelineMedia *media2);
void	  move_attached_effects (GtkWidget *widget, int x);
void	  move_media (GtkWidget *cell, GtkWidget *widget, guint x, gboolean move);
void	  move_child_on_layout (GtkWidget *self, GtkWidget *widget, gint x);
gboolean  pitivi_add_to_layout (GtkWidget *self, GtkWidget *widget, gint x, gint y);
gint	  compare_track (gconstpointer a, gconstpointer b);
void	  pitivi_calculate_priorities ( GtkWidget *widget );
gint	  compare_littlechild (gconstpointer a, gconstpointer b);
gint	  compare_bigchild (gconstpointer a, gconstpointer b);
void	  pitivi_layout_move (GtkLayout *layout, GtkWidget *widget, gint x, gint y);
void	  pitivi_media_set_size (GtkWidget *widget, guint width);

#endif
