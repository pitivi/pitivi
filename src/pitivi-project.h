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

#ifndef PITIVI_PROJECT_H
#define PITIVI_PROJECT_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include <gst/gst.h>
#include <gnl/gnltimeline.h>
#include "pitivi-projectsettings.h"
#include "pitivi-projectsourcelist.h"

/*
 * Type macros.
 */

#define PITIVI_PROJECT_TYPE (pitivi_project_get_type ())
#define PITIVI_PROJECT(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_PROJECT_TYPE, PitiviProject))
#define PITIVI_PROJECT_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_PROJECT_TYPE, PitiviProjectClass))
#define PITIVI_IS_PROJECT(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_PROJECT_TYPE))
#define PITIVI_IS_PROJECT_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_PROJECT_TYPE))
#define PITIVI_PROJECT_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_PROJECT_TYPE, PitiviProjectClass))

typedef struct _PitiviProject PitiviProject;
typedef struct _PitiviProjectClass PitiviProjectClass;
typedef struct _PitiviProjectPrivate PitiviProjectPrivate;

struct _PitiviProject
{
  GObject parent;

  /* instance public members */
  PitiviProjectSettings		*settings;
  PitiviProjectSourceList	*sources;
  gchar				*filename;

  GstElement			*pipeline;
  GnlTimeline			*timeline;
  
  /* private */
  PitiviProjectPrivate *private;
};

struct _PitiviProjectClass
{
  GObjectClass parent;
  /* class members */
};

/* used by PITIVI_PROJECT_TYPE */
GType pitivi_project_get_type (void);

/*
 * Method definitions.
 */

PitiviProject	*pitivi_project_new (PitiviProjectSettings *settings);
PitiviProject	*pitivi_project_new_from_file (const gchar *filename);
gboolean	pitivi_project_save_to_file(PitiviProject *project, const gchar *filename);
void		pitivi_project_restore_thyself(PitiviProject *project, xmlNodePtr self);
xmlDocPtr	pitivi_project_save_thyself(PitiviProject *project);
void		pitivi_project_set_sources(PitiviProject *project, PitiviProjectSourceList *sources);
gboolean	pitivi_project_set_source_element(PitiviProject *project, GstElement *source);
void		pitivi_project_blank_source(PitiviProject *project);
void		pitivi_project_set_video_output(PitiviProject *project, GstElement *output);
void		pitivi_project_set_audio_output(PitiviProject *project, GstElement *output);

#endif
