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

#ifndef PITIVI_SOURCEFILE_H
#define PITIVI_SOURCEFILE_H

/*
 * Potentially, include other headers on which this header depends.
 */
#include <gst/gst.h>
#include <gtk/gtk.h>


/*
 * Type macros.
 */

#define PITIVI_SOURCEFILE_TYPE (pitivi_sourcefile_get_type ())
#define PITIVI_SOURCEFILE(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_SOURCEFILE_TYPE, PitiviSourceFile))
#define PITIVI_SOURCEFILE_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_SOURCEFILE_TYPE, PitiviSourceFileClass))
#define PITIVI_IS_SOURCEFILE(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_SOURCEFILE_TYPE))
#define PITIVI_IS_SOURCEFILE_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_SOURCEFILE_TYPE))
#define PITIVI_SOURCEFILE_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_SOURCEFILE_TYPE, PitiviSourceFileClass))

typedef struct _PitiviSourceFile PitiviSourceFile;
typedef struct _PitiviSourceFileClass PitiviSourceFileClass;
typedef struct _PitiviSourceFilePrivate PitiviSourceFilePrivate;

struct _PitiviSourceFile
{
  GObject parent;
  
  /* instance public members */
  
  gchar	*filename;
  gchar *mediatype;
  gchar *infovideo;
  gchar *infoaudio;
  gint64 length;
  
  GdkPixbuf  *thumbs_audio;
  GdkPixbuf  *thumbs_video;
  GdkPixbuf  *thumbs_effect;
  GstElement *pipeline;		// audio/video and effect pipeline
  GstElement *pipeline_video;	// video only pipeline
  GstElement *pipeline_audio;	// audio only pipeline
  
  /* private */
  
  gboolean    haveaudio;
  gboolean    havevideo;

  PitiviSourceFilePrivate *private;
};

struct _PitiviSourceFileClass
{
  GObjectClass parent;
  /* class members */
};

/* used by PITIVI_SOURCEFILE_TYPE */
GType pitivi_sourcefile_get_type (void);

/*
 * Method definitions.
 */

PitiviSourceFile	*pitivi_sourcefile_new ();

#endif
