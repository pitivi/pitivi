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

#ifndef PITIVI_MEDIATRACKINFO_H
#define PITIVI_MEDIATRACKINFO_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include <gtk/gtk.h>
#include "pitivi-types.h"
#include "pitivi-timelinecellrenderer.h"

/*
 * Type macros.
 */

#define PITIVI_DEFAULT_FONT_DESC  "helvetica 9"
#define PITIVI_DEFAULT_MEDIA_NAME "Media"

#define MEDIA_TRACK_DEFAULT_WIDTH 120

#define PITIVI_MEDIATRACKINFO_TYPE (pitivi_mediatrackinfo_get_type ())
#define PITIVI_MEDIATRACKINFO(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_MEDIATRACKINFO_TYPE, PitiviMediaTrackInfo))
#define PITIVI_MEDIATRACKINFO_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_MEDIATRACKINFO_TYPE, PitiviMediaTrackInfoClass))
#define PITIVI_IS_MEDIATRACKINFO(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_MEDIATRACKINFO_TYPE))
#define PITIVI_IS_MEDIATRACKINFO_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_MEDIATRACKINFO_TYPE))
#define PITIVI_MEDIATRACKINFO_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_MEDIATRACKINFO_TYPE, PitiviMediaTrackInfoClass))

typedef struct _PitiviMediaTrackInfoPrivate PitiviMediaTrackInfoPrivate;

struct _PitiviMediaTrackInfo
{
  GtkVBox parent;

  /* instance public members */

  /* private */
  PitiviMediaTrackInfoPrivate *private;
};

struct _PitiviMediaTrackInfoClass
{
  GtkVBoxClass parent;
  /* class members */
};

/* used by PITIVI_MEDIATRACKINFO_TYPE */
GType pitivi_mediatrackinfo_get_type (void);

/*
 * Method definitions.
 */

GtkWidget	*pitivi_mediatrackinfo_new (PitiviTimelineCellRenderer *cell, gchar *label);

#endif
