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
#include "pitivi-cursor.h"
#include "pitivi-trackenum.h"

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

typedef struct _PitiviTimelineCellRenderer PitiviTimelineCellRenderer;
typedef struct _PitiviTimelineCellRendererClass PitiviTimelineCellRendererClass;
typedef struct _PitiviTimelineCellRendererPrivate PitiviTimelineCellRendererPrivate;
typedef struct _PitiviTimelineMediaChild PitiviTimelineMediaChild;

struct _PitiviTimelineCellRenderer
{
  GtkLayout parent;
  
  /* public members */
  PitiviLayerType	track_type;
  guint			track_nb;
  GList			*children;
  GtkWidget		*linked_track;
  GdkRectangle		*motion_area;
  
  /* private */
  PitiviTimelineCellRendererPrivate	*private;
};

struct _PitiviTimelineCellRendererClass
{
  GtkLayoutClass parent;

  /* class members */
  
  void (* activate)	    (PitiviTimelineCellRenderer *cell);
  void (* deactivate)	    (PitiviTimelineCellRenderer *cell);
  void (* select)	    (PitiviTimelineCellRenderer *cell);
  void (* deselect)	    (PitiviTimelineCellRenderer *cell);
  void (* delete)	    (PitiviTimelineCellRenderer *cell, gpointer data);
  void (*drag_source_begin) (PitiviTimelineCellRenderer *cell, gpointer data);
};

/* Conversion */

typedef enum {
  
  PITIVI_SECONDS = 1,
  PITIVI_NANOSECONDS,
  PITIVI_FRAMES
} PitiviConvert;


guint
convert_time_pix (gint64 length, PitiviConvert type);


/* used by PITIVI_TIMELINECELLRENDERER_TYPE */
GType pitivi_timelinecellrenderer_get_type (void);

/*
 * Method definitions.
 */

GtkWidget	*pitivi_timelinecellrenderer_new ();

void		pitivi_timelinecellrenderer_remove (GtkContainer *container, GtkWidget *child);

void		pitivi_timelinecellrenderer_deselection_ontracks (GtkWidget *widget, gboolean self_deselected);

PitiviCursor    *pitivi_getcursor_id (GtkWidget *widget);

int		add_to_layout (GtkWidget *self, GtkWidget *widget, gint x, gint y);


/* Deactivation of signals */

void		pitivi_timelinecellrenderer_activate (PitiviTimelineCellRenderer *self);
void		pitivi_timelinecellrenderer_deactivate (PitiviTimelineCellRenderer *self);
void		pitivi_timelinecellrenderer_deselection_ontracks (GtkWidget *widget, gboolean self_deselected);
void		pitivi_setback_tracktype ( PitiviTimelineCellRenderer *self );

#endif
