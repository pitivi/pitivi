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

#ifndef PITIVI_SETTINGS_H
#define PITIVI_SETTINGS_H

/*
 * Potentially, include other headers on which this header depends.
 */
#include <gst/gst.h>
#include <string.h>



/*
 * Type macros.
 */

#define PITIVI_SETTINGS_TYPE (pitivi_settings_get_type ())
#define PITIVI_SETTINGS(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_SETTINGS_TYPE, PitiviSettings))
#define PITIVI_SETTINGS_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_SETTINGS_TYPE, PitiviSettingsClass))
#define PITIVI_IS_SETTINGS(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_SETTINGS_TYPE))
#define PITIVI_IS_SETTINGS_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_SETTINGS_TYPE))
#define PITIVI_SETTINGS_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_SETTINGS_TYPE, PitiviSettingsClass))

typedef struct _PitiviSettings PitiviSettings;
typedef struct _PitiviSettingsClass PitiviSettingsClass;
typedef struct _PitiviSettingsPrivate PitiviSettingsPrivate;

typedef struct _PitiviSettingsMimeType PitiviSettingsMimeType;

enum {
  ENC_LIST,
  DEC_LIST
};


struct _PitiviSettingsMimeType
{
  GstCaps	*flux;
  GList		*encoder;
  GList		*decoder;
};


struct _PitiviSettings
{
  GObject parent;

  /* instance public members */

  GList		*container;
  GList		*codec;
  GList		*parser;
  GList		*element;
  
  /* private */
  PitiviSettingsPrivate *private;
};

struct _PitiviSettingsClass
{
  GObjectClass parent;
  /* class members */
};

/* used by PITIVI_SETTINGS_TYPE */
GType pitivi_settings_get_type (void);

/*
 * Method definitions.
 */

PitiviSettings	*pitivi_settings_new(void);

GList			*pitivi_settings_get_flux_codec_list (GObject *object, 
							      GstCaps *flux, 
							      gboolean LIST);
GList			*pitivi_settings_get_flux_container_list (GObject *object, 
								  GstCaps *flux, 
								  gboolean LIST);
GList			*pitivi_settings_get_flux_parser_list (GObject *object, 
								  GstCaps *flux, 
								  gboolean LIST);
PitiviSettings		*pitivi_settings_load_from_file(const gchar	*filename);
gboolean		pitivi_settings_save_to_file(PitiviSettings	*settings,
						      const gchar	*filename);

#endif
