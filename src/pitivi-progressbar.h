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

#ifndef PITIVI_PROGRESSBAR_H
#define PITIVI_PROGRESSBAR_H

#include <gtk/gtk.h>
#include <gst/gst.h>

#include "pitivi-windows.h"

/*
 * Potentially, include other headers on which this header depends.
 */

/*
 * Type macros.
 */

#define PITIVI_PROGRESSBAR_TYPE (pitivi_progressbar_get_type ())
#define PITIVI_PROGRESSBAR(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_PROGRESSBAR_TYPE, PitiviProgressBar))
#define PITIVI_PROGRESSBAR_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_PROGRESSBAR_TYPE, PitiviProgressBarClass))
#define PITIVI_IS_PROGRESSBAR(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_PROGRESSBAR_TYPE))
#define PITIVI_IS_PROGRESSBAR_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_PROGRESSBAR_TYPE))
#define PITIVI_PROGRESSBAR_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_PROGRESSBAR_TYPE, PitiviProgressBarClass))

typedef struct _PitiviProgressBar PitiviProgressBar;
typedef struct _PitiviProgressBarClass PitiviProgressBarClass;
typedef struct _PitiviProgressBarPrivate PitiviProgressBarPrivate;

struct _PitiviProgressBar
{
  PitiviWindows parent;
  
  /* instance public members */
  GtkWidget	*infos;
  GtkWidget	*label;
  GtkWidget	*bar;
  
  /* close boolean */
  gboolean	close;
  
  /* private */
  PitiviProgressBarPrivate *private;
};

struct _PitiviProgressBarClass
{
  PitiviWindowsClass parent;
  /* class members */
};

/* used by PITIVI_PROGRESSBAR_TYPE */
GType pitivi_progressbar_get_type (void);

/*
 * Method definitions.
 */

PitiviProgressBar	*pitivi_progressbar_new(void);
void			 pitivi_progressbar_set_info (PitiviProgressBar *self, gchar *label);
void			 pitivi_progressbar_set_fraction (PitiviProgressBar *self, gdouble val);

#endif
