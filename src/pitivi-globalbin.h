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

#ifndef PITIVI_GLOBALBIN_H
#define PITIVI_GLOBALBIN_H

#include <gst/gst.h>

/*
 * Potentially, include other headers on which this header depends.
 */

/*
 * Type macros.
 */

#define PITIVI_GLOBALBIN_TYPE (pitivi_globalbin_get_type ())
#define PITIVI_GLOBALBIN(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_GLOBALBIN_TYPE, PitiviGlobalBin))
#define PITIVI_GLOBALBIN_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_GLOBALBIN_TYPE, PitiviGlobalBinClass))
#define PITIVI_IS_GLOBALBIN(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_GLOBALBIN_TYPE))
#define PITIVI_IS_GLOBALBIN_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_GLOBALBIN_TYPE))
#define PITIVI_GLOBALBIN_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_GLOBALBIN_TYPE, PitiviGlobalBinClass))

typedef struct _PitiviGlobalBin PitiviGlobalBin;
typedef struct _PitiviGlobalBinClass PitiviGlobalBinClass;
typedef struct _PitiviGlobalBinPrivate PitiviGlobalBinPrivate;

struct _PitiviGlobalBin
{
  GstBin parent;

  /* instance public members */
  gboolean	preview;
  gboolean	render;

  GstElement	*vtee;
  GstElement	*atee;

  GstElement	*source;
  gchar		*encodedfile;
  
  GstElement	*videoout;
  GstElement	*audioout;

  GstElement	*vencoder;
  GstElement	*aencoder;

  GstElement	*muxer;

  /* private */
  PitiviGlobalBinPrivate *private;
};

struct _PitiviGlobalBinClass
{
  GstBinClass parent;
  /* class members */

  gboolean	(*connect_source) (PitiviGlobalBin *gbin);
  gboolean	(*disconnect_source) (PitiviGlobalBin *gbin);
};

/* used by PITIVI_GLOBALBIN_TYPE */
GType pitivi_globalbin_get_type (void);

/*
 * Method definitions.
 */
/* no _new() function, shouldn't be used directly */
/* PitiviGlobalBin	*pitivi_globalbin_new(void); */

void	pitivi_globalbin_set_video_output (PitiviGlobalBin *gbin, GstElement *videoout);
void	pitivi_globalbin_set_audio_output (PitiviGlobalBin *gbin, GstElement *audioout);
void	pitivi_globalbin_set_encoded_file (PitiviGlobalBin *gbin, const gchar *filename);

#endif
