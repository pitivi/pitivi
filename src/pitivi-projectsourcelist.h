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


#ifndef PITIVI_PROJECTSOURCELIST_H
#define PITIVI_PROJECTSOURCELIST_H

/*
 * Potentially, include other headers on which this header depends.
 */
#include <gst/gst.h>
/*
 * Type macros.
 */

#define PITIVI_PROJECTSOURCELIST_TYPE (pitivi_projectsourcelist_get_type ())
#define PITIVI_PROJECTSOURCELIST(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_PROJECTSOURCELIST_TYPE, PitiviProjectSourceList))
#define PITIVI_PROJECTSOURCELIST_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_PROJECTSOURCELIST_TYPE, PitiviProjectSourceListClass))
#define PITIVI_IS_PROJECTSOURCELIST(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_PROJECTSOURCELIST_TYPE))
#define PITIVI_IS_PROJECTSOURCELIST_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_PROJECTSOURCELIST_TYPE))
#define PITIVI_PROJECTSOURCELIST_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_PROJECTSOURCELIST_TYPE, PitiviProjectSourceListClass))

typedef struct _PitiviProjectSourceList PitiviProjectSourceList;
typedef struct _PitiviProjectSourceListClass PitiviProjectSourceListClass;
typedef struct _PitiviProjectSourceListPrivate PitiviProjectSourceListPrivate;
typedef struct _PitiviSourceBin PitiviSourceBin;
typedef struct _PitiviSourceFile PitiviSourceFile;

struct _PitiviSourceFile
{
  gchar	*filename;
  gchar *mediatype;
  gchar *infovideo;
  gchar *infoaudio;
  gint64 length;
  GstElement *pipeline;
};

struct _PitiviProjectSourceList
{
  GObject parent;

  /* instance public members */

  /* private */
  PitiviProjectSourceListPrivate *private;
};

struct _PitiviProjectSourceListClass
{
  GObjectClass parent;
  /* class members */

};

/* used by PITIVI_PROJECTSOURCELIST_TYPE */
GType pitivi_projectsourcelist_get_type (void);

/*
 * Method definitions.
 */

PitiviProjectSourceList	*pitivi_projectsourcelist_new(void);
gboolean 
pitivi_projectsourcelist_add_file_to_bin(PitiviProjectSourceList *self, 
					 gchar *treepath, gchar *filename,
					 gchar *mediatype, gchar *infovideo,
					 gchar *infoaudio, gint64 length,
					 GstElement *pipeline);
void 
pitivi_projectsourcelist_new_bin(PitiviProjectSourceList *self, 
				 gchar *bin_name);
gpointer 
pitivi_projectsourcelist_get_file_info(PitiviProjectSourceList *self, 
				       gchar *treepath, guint next_file);
void 
pitivi_projectsourcelist_remove_file_from_bin(PitiviProjectSourceList *self,
					      gchar *treepath, guint file_pos);
void
pitivi_projectsourcelist_remove_bin(PitiviProjectSourceList *self,
				    gchar *treepath);
void
pitivi_projectsourcelist_add_folder_to_bin(PitiviProjectSourceList *self, 
					   gchar *treepath,
					   gchar *folder_name);

PitiviSourceFile *
pitivi_projectsourcelist_get_sourcefile(PitiviProjectSourceList *self,
					gchar *treepath, gint file_pos);

/* only for debug */
void	pitivi_projectsourcelist_showfile(PitiviProjectSourceList *self, 
					  gchar *treepath);

#endif
