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

#ifndef PITIVI_TIMELINEMEDIA_H
#define PITIVI_TIMELINEMEDIA_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include <gtk/gtk.h>
#include "pitivi-projectwindows.h"
#include "pitivi-sourceitem.h"

/*
 * Type macros.
 */


#define DEFAULT_WIDTH   50
#define DEFAULT_HEIGHT  50

#define REDUCE_CURSOR_AREA_SIZE	6


#define PITIVI_TIMELINEMEDIA_TYPE (pitivi_timelinemedia_get_type ())
#define PITIVI_TIMELINEMEDIA(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_TIMELINEMEDIA_TYPE, PitiviTimelineMedia))
#define PITIVI_TIMELINEMEDIA_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_TIMELINEMEDIA_TYPE, PitiviTimelineMediaClass))
#define PITIVI_IS_TIMELINEMEDIA(obj) (GTK_CHECK_TYPE ((obj), PITIVI_TIMELINEMEDIA_TYPE))
#define PITIVI_IS_TIMELINEMEDIA_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_TIMELINEMEDIA_TYPE))
#define PITIVI_TIMELINEMEDIA_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_TIMELINEMEDIA_TYPE, PitiviTimelineMediaClass))

typedef struct _PitiviTimelineMedia PitiviTimelineMedia;
typedef struct _PitiviTimelineMediaClass PitiviTimelineMediaClass;
typedef struct _PitiviTimelineMediaPrivate PitiviTimelineMediaPrivate;

struct _PitiviTimelineMedia
{
  GtkWidget parent;
  GdkWindow *event_window;
  
  /* instance public members */
  
  PitiviSourceItem *sourceitem;
  GtkWidget        *linked;
  GtkWidget	   *track;
  gboolean	   selected;
  gboolean	   copied;
  
  /* private */
  
  PitiviTimelineMediaPrivate *private;
};

struct _PitiviTimelineMediaClass
{
  GtkWidgetClass parent;
  /* class members */
  void (* select)   (PitiviTimelineMedia *cell);
  void (* deselect) (PitiviTimelineMedia *cell);
  void (* dissociate) (PitiviTimelineMedia *self, gpointer data);
};

/* used by PITIVI_TIMELINEMEDIA_TYPE */
GType pitivi_timelinemedia_get_type (void);

/*
 * Method definitions.
 */

PitiviTimelineMedia	*pitivi_timelinemedia_new ();

void	draw_selection (GtkWidget *widget, int width, char **dash);
void	draw_slide (GtkWidget *widget, int start, int end);

void
pitivi_timelinemedia_set_start_stop (PitiviTimelineMedia *media, gint64 start, gint64 stop);
void
pitivi_timelinemedia_set_media_start_stop (PitiviTimelineMedia *media, gint64 start, gint64 stop);
void
pitivi_timelinemedia_set_priority (PitiviTimelineMedia *media, gint priority);
void
pitivi_timelinemedia_put (PitiviTimelineMedia *media, gint64 start);


/*
 **********************************************************
 * Callbacks  					          *
 *							  *
 **********************************************************
*/

void	pitivi_timelinemedia_callb_destroy (PitiviTimelineMedia *self, gpointer data);

/* Menu */

void	pitivi_timelinemedia_callb_cut (PitiviTimelineMedia *self, gpointer data);
void	pitivi_timelinemedia_callb_copied (PitiviTimelineMedia *self, gpointer data);
void	pitivi_timelinemedia_callb_dissociate (PitiviTimelineMedia *self, gpointer data);


#endif
