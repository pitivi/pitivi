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

#ifndef PITIVI_PROJECTSETTINGS_H
#define PITIVI_PROJECTSETTINGS_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include <glib.h>
#include <gst/gst.h>

/*
 * Type macros.
 */

#define PITIVI_PROJECTSETTINGS_TYPE (pitivi_projectsettings_get_type ())
#define PITIVI_PROJECTSETTINGS(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_PROJECTSETTINGS_TYPE, PitiviProjectSettings))
#define PITIVI_PROJECTSETTINGS_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_PROJECTSETTINGS_TYPE, PitiviProjectSettingsClass))
#define PITIVI_IS_PROJECTSETTINGS(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_PROJECTSETTINGS_TYPE))
#define PITIVI_IS_PROJECTSETTINGS_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_PROJECTSETTINGS_TYPE))
#define PITIVI_PROJECTSETTINGS_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_PROJECTSETTINGS_TYPE, PitiviProjectSettingsClass))

typedef struct _PitiviProjectSettings PitiviProjectSettings;
typedef struct _PitiviProjectSettingsClass PitiviProjectSettingsClass;
typedef struct _PitiviProjectSettingsPrivate PitiviProjectSettingsPrivate;

typedef struct _PitiviMediaSettings PitiviMediaSettings;

struct _PitiviProjectSettings
{
  GObject parent;

  /* instance public members */
  gchar		*name;
  char		*description;
  GSList	*media_settings;

  /* private */
  PitiviProjectSettingsPrivate *private;
};

struct _PitiviProjectSettingsClass
{
  GObjectClass parent;
  /* class members */
};

struct _PitiviSettingsValue
{
  gchar		*name;
  GValue	value;
};

struct _PitiviMediaSettings
{
  gchar		*codec_factory_name;
  GSList	*codec_props;
  GstCaps	*caps;
};

/* used by PITIVI_PROJECTSETTINGS_TYPE */

GType pitivi_projectsettings_get_type (void);

/*
 * Method definitions.
 */

PitiviProjectSettings	*pitivi_projectsettings_new(void);

#endif
