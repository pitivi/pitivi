/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      Bloch Stephan <bloch_s@epita.fr>
 *                      Carbon Julien <carbon_j@epita.fr>
 *                      Dubart Loic <dubart_l@epita.fr>
 *
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

#ifndef PITIVI_MAINAPP_H
#define PITIVI_MAINAPP_H

typedef struct _PitiviMainApp PitiviMainApp;

/*
 * Potentially, include other headers on which this header depends.
 */

#include	"pitivi-project.h"
#include	"pitivi-projectsettings.h"
#include	"pitivi-settings.h"

/*
 * Type macros.
 */

#define PITIVI_MAINAPP_TYPE (pitivi_mainapp_get_type ())
#define PITIVI_MAINAPP(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_MAINAPP_TYPE, PitiviMainApp))
#define PITIVI_MAINAPP_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_MAINAPP_TYPE, PitiviMainAppClass))
#define PITIVI_IS_MAINAPP(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_MAINAPP_TYPE))
#define PITIVI_IS_MAINAPP_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_MAINAPP_TYPE))
#define PITIVI_MAINAPP_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_MAINAPP_TYPE, PitiviMainAppClass))

typedef struct _PitiviMainAppClass PitiviMainAppClass;
typedef struct _PitiviMainAppPrivate PitiviMainAppPrivate;

struct _PitiviMainApp
{
  GObject parent;

  /* instance public members */
  GList	*projects;	/* List of PitiviProject loaded */
  PitiviProject	*project;	/* project used */

  PitiviSettings	*global_settings;
  /* private */
  PitiviMainAppPrivate	*private;
};

struct _PitiviMainAppClass
{
  GObjectClass parent;
  /* class members */
};

/* used by PITIVI_MAINAPP_TYPE */
GType		pitivi_mainapp_get_type (void);

/*
 * Method definitions.
 */

PitiviMainApp		*pitivi_mainapp_new			(void);
void			pitivi_mainapp_activate_effectswindow	( PitiviMainApp *self, gboolean activate);
void			pitivi_mainapp_create_wintools		( PitiviMainApp *self, PitiviProject *project);
gboolean		pitivi_mainapp_add_project		( PitiviMainApp *self, PitiviProject *project);
#endif
