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

/*
 * Type macros.
 */

#define FIXED_WIDTH   6000
#define FIXED_HEIGHT  50


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
  guint	cell_type;
  GList	*children;
  
  /* private */
  PitiviTimelineCellRendererPrivate	*private;
};

struct _PitiviTimelineCellRendererClass
{
  GtkLayoutClass parent;
  /* class members */
};

/* used by PITIVI_TIMELINECELLRENDERER_TYPE */
GType pitivi_timelinecellrenderer_get_type (void);

/*
 * Method definitions.
 */

GtkWidget	*pitivi_timelinecellrenderer_new(void);

#endif
